"""
refresh_comms_oc_cache.py — Mantiene data/comms_oc_cache.json (historial Comms_OC)
══════════════════════════════════════════════════════════════════════════════════════
Script STANDALONE — NO forma parte del flujo automático de gen_dashboard_v2.py.

╔══════════════════════════════════════════════════════════════════╗
║  CUATRO MODOS DE OPERACIÓN                                       ║
╠══════════════════════════════════════════════════════════════════╣
║  MODO INCREMENTAL (default, ~2 min):                            ║
║    python scripts/refresh_comms_oc_cache.py                     ║
║    → Consulta BQ desde la última fecha del cache hasta D-7.    ║
║    → Purge automático respeta la fecha mínima del metadata.    ║
║                                                                  ║
║  MODO FULL REBUILD (~40 min):                                   ║
║    python scripts/refresh_comms_oc_cache.py --full             ║
║    → Reconstruye desde cero: los 5 meses completos.            ║
║                                                                  ║
║  MODO APPEND HISTÓRICO (para extender cobertura hacia atrás):  ║
║    python scripts/refresh_comms_oc_cache.py                    ║
║         --append --from 2025-06-01 --to 2025-11-01             ║
║    → Consulta SOLO el rango especificado.                       ║
║    → Merge con cache existente (dedup por COMMUNICATION_ID).   ║
║    → Protege oldest_date del purge futuro via metadata.        ║
║    → Tiempo: ~30-50 min en BQ (sujeto a contención ranuras).  ║
║                                                                  ║
║  MODO CLEAN (sin BQ, instantáneo):                             ║
║    python scripts/refresh_comms_oc_cache.py --clean            ║
║    → Elimina registros con SELLER/XT1/ENG/SEV-T3.             ║
║                                                                  ║
║  MODO FIX-EMAIL-DATES (sin BQ, instantáneo):                   ║
║    python scripts/refresh_comms_oc_cache.py --fix-email-dates  ║
║    → Elimina emails con fecha fallback '??-01' del cache.      ║
║    → El próximo --append regenerará esos registros con la      ║
║      fecha real (gracias al HAVING corregido).                  ║
║    → Correr ANTES del --append histórico para limpiar todo.    ║
╚══════════════════════════════════════════════════════════════════╝

ESTRATEGIA RECOMENDADA para extender cobertura + limpiar SELLERs:
  Paso 1 (instantáneo):  python scripts/refresh_comms_oc_cache.py --clean
  Paso 2 (off-peak, BQ): python scripts/refresh_comms_oc_cache.py --append --from 2025-06-01 --to 2025-11-01

Rutina recomendada (una vez por semana, cualquier día, ~2 min):
  cd C:\\Users\\sergibarra\\Documents\\SI_Meli_code1\\MLM_ADQ_Dash
  ..\\vEnv_Meli_Code1\\Scripts\\activate
  python scripts/refresh_comms_oc_cache.py

Tablas BQ consultadas (3):
  · meli-bi-data.SBOX_MARKETING.BT_OC_CUST_EVENT
  · SBOX_EG_MKT.DASHBOARD_CAMPAIGNS_INDIVIDUOS_METRICAS  (sin prefijo de proyecto)
  · SBOX_EG_MKT.BT_OC_DASHBOARD_ALL_CAMPAIGNS            (sin prefijo de proyecto)

Ver History.md §45 para la arquitectura Two-Tier completa.
"""

import os
import sys
import json
import datetime
from google.cloud import bigquery


# ── Rutas ──────────────────────────────────────────────────────────────────
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
CACHE_PATH   = os.path.join(PROJECT_ROOT, 'data', 'comms_oc_cache.json')
# Metadata del cache: guarda oldest_date para que el purge no borre datos históricos
# agregados con --append. Si no existe, el purge usa CACHE_HISTORY_MONTHS por defecto.
CACHE_META_PATH = os.path.join(PROJECT_ROOT, 'data', 'comms_oc_cache_meta.json')
BQ_PROJECT   = 'meli-bi-data'

# Ventana histórica que cubre el cache (en meses).
# Registros más antiguos se eliminan automáticamente en el modo incremental.
# OJO: si se usó --append con fechas más antiguas, el metadata protege esos registros.
CACHE_HISTORY_MONTHS = 5


# ── Helpers de metadata ────────────────────────────────────────────────────

def load_cache_meta():
    """Carga metadata del cache. Retorna dict con 'oldest_date' si existe."""
    if os.path.exists(CACHE_META_PATH):
        with open(CACHE_META_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_cache_meta(oldest_date_str):
    """Guarda la fecha mínima protegida del cache en el archivo de metadata."""
    meta = {
        'oldest_date': oldest_date_str,
        'updated_at': datetime.datetime.now().isoformat()[:19],
    }
    with open(CACHE_META_PATH, 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

def get_oldest_allowed_date():
    """Retorna la fecha más antigua permitida en el cache.
    Si hay metadata (de un --append histórico), respeta esa fecha.
    Si no, usa los últimos CACHE_HISTORY_MONTHS meses (comportamiento original).
    """
    meta = load_cache_meta()
    if 'oldest_date' in meta:
        return datetime.date.fromisoformat(meta['oldest_date'])
    return get_five_months_ago_start()


# ══════════════════════════════════════════════════════════════════
# HELPERS DE FECHA
# ══════════════════════════════════════════════════════════════════

def get_cache_cutoff_date():
    """Retorna la fecha de corte del cache: primer día del mes actual.

    ARQUITECTURA MES CERRADO (reemplaza la anterior estrategia D-7):
      Cache (Tier 1): todos los meses ANTERIORES al mes actual (cerrados, estables).
      Fresh (Tier 2): solo el mes actual en curso (puede cambiar a diario).

    Ejemplo:
      Hoy = 17-Abr-2026 → corte = 01-Abr-2026
      Cache: Jan-2025 ... Mar-2026 (meses cerrados, nunca cambian)
      Fresh: Abr-2026 (mes en curso, query pequeña ~17 días de datos)

    Ventajas vs D-7:
      · Meses completos = análisis de patrones semanales/quincenales íntegros
      · Los meses cerrados son 100% estables (no hay revisiones retroactivas)
      · La fresh query cubre ~15 días en promedio (más pequeña y rápida)
      · Alínea con el ciclo de negocio natural (cierre mensual, IS mensual)
    """
    today = datetime.date.today()
    return datetime.date(today.year, today.month, 1)


def get_five_months_ago_start():
    """Retorna el primer día del mes de hace CACHE_HISTORY_MONTHS meses.
    Se usa como:
      · Límite inferior de la consulta FULL REBUILD
      · Fecha de purge del cache (eliminar registros más viejos)
    """
    today = datetime.date.today()
    month = today.month - CACHE_HISTORY_MONTHS
    year  = today.year
    if month <= 0:
        month += 12
        year  -= 1
    return datetime.date(year, month, 1)


def get_max_date_in_cache(cache_records_list):
    """Retorna la fecha más reciente de SENT_DATE en el cache existente.

    §75: migrado de FIRST_SENT_DATE → SENT_DATE (schema nuevo diario).
    Usa comparación de strings 'YYYY-MM-DD' que ordena correctamente lexicográficamente.
    Retorna None si el cache está vacío o no tiene fechas válidas.
    """
    dates = [
        r.get('SENT_DATE', '')
        for r in cache_records_list
        if r.get('SENT_DATE')
    ]
    return max(dates) if dates else None


# ══════════════════════════════════════════════════════════════════
# GENERADORES DE SQL
# ══════════════════════════════════════════════════════════════════

def build_comms_oc_sql_for_date_range(from_date_inclusive, to_date_exclusive):
    """Genera el SQL de comunicaciones OC para un rango de fechas específico (cache).

    §75 History.md — misma lógica que get_comms_oc_fresh_sql() pero con filtro de
    fecha paramétrico por rango (SENT_DATE >= from / < to) en lugar de mes actual.

    PARÁMETROS:
      from_date_inclusive : datetime.date — SENT_DATE >= esta fecha
      to_date_exclusive   : datetime.date — SENT_DATE <  esta fecha

    RAMAS (igual que fresh):
      · RAMA A: SBOX_EG_MKT.BT_OC_DASHBOARD_ALL_CAMPAIGNS_NR
      · RAMA B: SBOX_EG_MKT.BT_OC_DASHBOARD_ALL_CAMPAIGNS_NR_ACQUISITION

    COLUMNAS STRING-SAFE: SENT_DATE y MONTH_ID se castean en SQL para garantizar
    serialización JSON sin conversiones Python adicionales.
    """
    from_date_sql = from_date_inclusive.isoformat()   # 'YYYY-MM-DD'
    to_date_sql   = to_date_exclusive.isoformat()     # 'YYYY-MM-DD'

    return f"""
    -- ════════════════════════════════════════════════════════════════════
    -- build_comms_oc_sql_for_date_range() — Cache Comms OC | §75
    -- Rango: SENT_DATE >= '{from_date_sql}' AND < '{to_date_sql}'
    -- Ramas: ALL_CAMPAIGNS_NR + NR_ACQUISITION
    -- ════════════════════════════════════════════════════════════════════

    -- ── RAMAS A y B como CTEs — el colapso final unifica duplicados cross-tabla ──
    WITH rama_a AS (
    -- ── RAMA A: BT_OC_DASHBOARD_ALL_CAMPAIGNS_NR ────────────────────────
    SELECT
      CAST(SENT_DATE AS STRING)                                         AS SENT_DATE,
      FORMAT_DATE('%Y%m', MONTH_ID)                                     AS MONTH_ID,
      CAST(COMMUNICATION_ID AS STRING)                                  AS COMMUNICATION_ID,
      COMUNICATION_NAME                                                  AS CAMPAIGN_NAME,
      NULLIF(
        CASE WHEN ENDS_WITH(TRIM(COMUNICATION_NAME), '_DEFAULT')
             THEN SUBSTR(TRIM(COMUNICATION_NAME), 1, LENGTH(TRIM(COMUNICATION_NAME)) - 8)
             ELSE TRIM(COMUNICATION_NAME) END, '')                      AS CAMPAIGN_NAME_CLEAN,
      CANAL,
      CHANNEL,
      TEAM,
      STRATEGY,
      SUBSTRATEGY,
      EXPERIMENT,
      NOTIFICATION_TYPE,
      BUSINESS_LINE_SEGMENT_CHANNELS                                     AS BUSINESS_LINE_SEGMENT,
      BUSINESS_LINE,
      STATUS,
      COALESCE(VOLUMEN_SENT,           0.0) AS SENTS,
      COALESCE(VOLUMEN_ENTRY_TEST,     0)   AS TOTAL_TEST,
      COALESCE(VOLUMEN_CONTROL,        0)   AS TOTAL_CONTROL,
      COALESCE(VOLUMEN_SHOWN,          0)   AS TOTAL_ARRIVED,
      COALESCE(VOLUMEN_OPEN,           0)   AS TOTAL_OPEN,
      COALESCE(VOLUMEN_CLICK,          0)   AS TOTAL_CLICK,
      COALESCE(VOLUMEN_ENTRY_TEST,     0)   AS ENTRY_TEST_JNY,
      COALESCE(VOLUMEN_ENTRY_CONTROL,  0)   AS ENTRY_CONTROL_JNY,
      SAFE_DIVIDE(COALESCE(VOLUMEN_OPEN, 0),
        NULLIF(COALESCE(NULLIF(COALESCE(VOLUMEN_SHOWN,0),0), COALESCE(VOLUMEN_SENT,0)), 0)
      )                                                                  AS OPEN_RATE,
      -- USER_INC: lift puro (NR_INC_USERS) — alineado con Torre de Control.
      COALESCE(NR_INC_USERS, 0)                                          AS USER_INC,
      -- USER_INC_CON_ADJUST: fórmula oficial del equipo.
      -- CLASIF='UCRANIA' → Adjust 7D (calibrado por Blacklist). Resto → lift.
      CASE
        WHEN CLASIF_CAMPAIGNS = 'UCRANIA'
        THEN COALESCE(NEW_7D_ADJUST, 0) + COALESCE(REC_7D_ADJUST, 0)
        ELSE COALESCE(NR_INC_USERS, 0)
      END                                                                AS USER_INC_CON_ADJUST,
      COALESCE(NR_INC_VALUE, 0.0)                                       AS VALUE_INC,
      COALESCE(NEW_COUNT_USERS_TEST_CONV, 0)
        + COALESCE(REC_COUNT_USERS_TEST_CONV, 0)                        AS TOTAL_ABSOLUTO_NR,
      COALESCE(NEW_COUNT_USERS_CONTROL_CONV, 0)
        + COALESCE(REC_COUNT_USERS_CONTROL_CONV, 0)                     AS NR_TOTAL_CONTROL,
      CASE
        WHEN (COALESCE(NEW_COUNT_USERS_TEST_CONV, 0)
              + COALESCE(REC_COUNT_USERS_TEST_CONV, 0)) = 0
          THEN CAST(NULL AS FLOAT64)
        ELSE ROUND(SAFE_DIVIDE(
          (COALESCE(NEW_COUNT_USERS_TEST_CONV, 0) + COALESCE(REC_COUNT_USERS_TEST_CONV, 0))
          - CASE
              WHEN CLASIF_CAMPAIGNS = 'UCRANIA'
              THEN COALESCE(NEW_7D_ADJUST, 0) + COALESCE(REC_7D_ADJUST, 0)
              ELSE COALESCE(NR_INC_USERS, 0)
            END,
          (COALESCE(NEW_COUNT_USERS_TEST_CONV, 0) + COALESCE(REC_COUNT_USERS_TEST_CONV, 0))
        ), 4)
      END                                                                AS RATIO_CANIBALIZACION,
      CLASIF_CAMPAIGNS,
      FLAG_PAID,
      CAST(FLAG_INCENTIVO AS INT64)                                     AS FLAG_INCENTIVO,
      COALESCE(CONSUMIDO_USD,     0.0)                                  AS CONSUMIDO_USD,
      COALESCE(COSTO_ENVIO_USD,   0.0)                                  AS COSTO_ENVIO_USD,
      COALESCE(COSTO_MANTIKA_USD, 0.0)                                  AS COSTO_MANTIKA_USD,
      'ALL_CAMPAIGNS_NR'                                                 AS FUENTE_TABLA
    FROM `SBOX_EG_MKT.BT_OC_DASHBOARD_ALL_CAMPAIGNS_NR`
    WHERE SITE = 'MLM'
      AND SENT_DATE >= DATE '{from_date_sql}'
      AND SENT_DATE <  DATE '{to_date_sql}'
      AND (
        -- Canales regulares: filtro por strategy
        STRATEGY IN ('UCRANIA', 'ACTIVATION', 'ACQUISITION', 'RE-ACTIVATION', 'ENGAGEMENT')
        -- Journey: capturar todas sin restricción de strategy (incluye OTHERS/RETENTION/etc.)
        OR UPPER(CANAL) = 'JOURNEY'
      )
      AND (
        -- Journey bypass: sin filtro de team
        UPPER(CANAL) = 'JOURNEY'
        OR TEAM NOT IN ('SELLERS', 'ADHOC - SELLERS')
        OR ABS(COALESCE(NULLIF(COALESCE(NEW_7D_ADJUST,0)+COALESCE(REC_7D_ADJUST,0), 0), COALESCE(NR_INC_USERS,0))) > 250
      )
      AND (
        -- Journey bypass: sin filtros de nombre
        UPPER(CANAL) = 'JOURNEY'
        OR (
          COMUNICATION_NAME NOT LIKE '%SELLER%'
          AND COMUNICATION_NAME NOT LIKE '%-XT1-%'
          AND COMUNICATION_NAME NOT LIKE '%SEV-T3-%'
          AND COMUNICATION_NAME NOT LIKE '%-ENG%'
          AND COMUNICATION_NAME NOT LIKE '%-ENG'
          AND COMUNICATION_NAME NOT LIKE '%T1%'
          AND COMUNICATION_NAME NOT LIKE '%XSELL%'
          AND COMUNICATION_NAME NOT LIKE '%SVS_CUPON%'
          AND COMUNICATION_NAME NOT LIKE '%SVS%'
        )
      )
    QUALIFY ROW_NUMBER() OVER (
      PARTITION BY COMMUNICATION_ID, SENT_DATE, CANAL
      ORDER BY SENT_DATE DESC
    ) = 1
    ),  -- fin rama_a

    rama_b AS (
    -- ── RAMA B: BT_OC_DASHBOARD_ALL_CAMPAIGNS_NR_ACQUISITION ────────────
    SELECT
      CAST(SENT_DATE AS STRING)                                         AS SENT_DATE,
      FORMAT_DATE('%Y%m', MONTH_ID)                                     AS MONTH_ID,
      CAST(COMMUNICATION_ID AS STRING)                                  AS COMMUNICATION_ID,
      COMUNICATION_NAME                                                  AS CAMPAIGN_NAME,
      NULLIF(
        CASE WHEN ENDS_WITH(TRIM(COMUNICATION_NAME), '_DEFAULT')
             THEN SUBSTR(TRIM(COMUNICATION_NAME), 1, LENGTH(TRIM(COMUNICATION_NAME)) - 8)
             ELSE TRIM(COMUNICATION_NAME) END, '')                      AS CAMPAIGN_NAME_CLEAN,
      CANAL,
      CAST(NULL AS STRING)                                              AS CHANNEL,
      TEAM,
      STRATEGY,
      SUBSTRATEGY,
      CAST(NULL AS STRING)                                              AS EXPERIMENT,
      CAST(NULL AS STRING)                                              AS NOTIFICATION_TYPE,
      CAST(NULL AS STRING)                                              AS BUSINESS_LINE_SEGMENT,
      BUSINESS_LINE,
      CAST(NULL AS STRING)                                              AS STATUS,
      COALESCE(VOLUMEN_SENT,          0.0) AS SENTS,
      COALESCE(VOLUMEN_ENTRY_TEST,    0)   AS TOTAL_TEST,
      COALESCE(VOLUMEN_CONTROL,       0)   AS TOTAL_CONTROL,
      COALESCE(VOLUMEN_SHOWN,         0)   AS TOTAL_ARRIVED,
      COALESCE(VOLUMEN_OPEN,          0)   AS TOTAL_OPEN,
      CAST(0 AS INT64)                     AS TOTAL_CLICK,
      COALESCE(VOLUMEN_ENTRY_TEST,    0)   AS ENTRY_TEST_JNY,
      COALESCE(VOLUMEN_ENTRY_CONTROL, 0)   AS ENTRY_CONTROL_JNY,
      SAFE_DIVIDE(COALESCE(VOLUMEN_OPEN, 0),
        NULLIF(COALESCE(NULLIF(COALESCE(VOLUMEN_SHOWN,0),0), COALESCE(VOLUMEN_SENT,0)), 0)
      )                                                                  AS OPEN_RATE,
      COALESCE(Q_NR_7D, 0.0)                                           AS USER_INC,
      COALESCE(Q_NR_7D, 0.0)                                           AS USER_INC_CON_ADJUST,
      COALESCE(VALUE_PREDICTED, 0.0)                                    AS VALUE_INC,
      CAST(NULL AS FLOAT64)                                             AS TOTAL_ABSOLUTO_NR,
      CAST(NULL AS FLOAT64)                                             AS NR_TOTAL_CONTROL,
      CAST(NULL AS FLOAT64)                                             AS RATIO_CANIBALIZACION,
      CLASIFICATION                                                      AS CLASIF_CAMPAIGNS,
      FLAG_PAID,
      CAST(FLAG_INCENTIVO AS INT64)                                     AS FLAG_INCENTIVO,
      COALESCE(CONSUMIDO_USD,   0.0)                                    AS CONSUMIDO_USD,
      COALESCE(COSTO_ENVIO_USD, 0.0)                                    AS COSTO_ENVIO_USD,
      CAST(NULL AS FLOAT64)                                             AS COSTO_MANTIKA_USD,
      'NR_ACQUISITION'                                                   AS FUENTE_TABLA
    FROM `SBOX_EG_MKT.BT_OC_DASHBOARD_ALL_CAMPAIGNS_NR_ACQUISITION`
    WHERE SITE = 'MLM'
      AND SENT_DATE >= DATE '{from_date_sql}'
      AND SENT_DATE <  DATE '{to_date_sql}'
      AND (
        TEAM NOT IN ('SELLERS', 'ADHOC - SELLERS')
        OR ABS(COALESCE(Q_NR_7D, 0)) > 250
      )
      AND COMUNICATION_NAME NOT LIKE '%SELLER%'
      AND COMUNICATION_NAME NOT LIKE '%-XT1-%'
      AND COMUNICATION_NAME NOT LIKE '%SEV-T3-%'
      AND COMUNICATION_NAME NOT LIKE '%-ENG%'
      AND COMUNICATION_NAME NOT LIKE '%-ENG'
      AND COMUNICATION_NAME NOT LIKE '%T1%'
      AND COMUNICATION_NAME NOT LIKE '%XSELL%'
      AND COMUNICATION_NAME NOT LIKE '%SVS_CUPON%'
      AND COMUNICATION_NAME NOT LIKE '%SVS%'
      AND COMUNICATION_NAME NOT LIKE '%CHURN%'
    QUALIFY ROW_NUMBER() OVER (
      PARTITION BY COMMUNICATION_ID, SENT_DATE, CANAL
      ORDER BY SENT_DATE DESC
    ) = 1
    ),  -- fin rama_b

    combined AS (
      SELECT * FROM rama_a
      UNION ALL
      SELECT * FROM rama_b
    )

    -- ── COLAPSO CROSS-TABLA ──────────────────────────────────────────────────
    -- Objetivo: (COMMUNICATION_ID, SENT_DATE, CANAL) es la clave de unicidad.
    -- Si la misma comunicación aparece en AMBAS tablas en el mismo día y canal,
    -- se colapsa en UNA sola fila con FUENTE_TABLA = 'AMBAS'.
    -- Prioridad de métricas: Rama A (ALL_CAMPAIGNS_NR) sobre Rama B (NR_ACQUISITION).
    -- Los campos NULL en Rama B (CHANNEL, NOTIFICATION_TYPE, TOTAL_ABSOLUTO_NR,
    -- RATIO_CANIBALIZACION, COSTO_MANTIKA_USD, TOTAL_CLICK, STATUS,
    -- BUSINESS_LINE_SEGMENT) se toman directamente de Rama A via MAX().
    SELECT
      SENT_DATE,
      MONTH_ID,
      COMMUNICATION_ID,
      ANY_VALUE(CAMPAIGN_NAME)                                                     AS CAMPAIGN_NAME,
      ANY_VALUE(CAMPAIGN_NAME_CLEAN)                                               AS CAMPAIGN_NAME_CLEAN,
      CANAL,
      -- Campos NULL en Rama B → MAX toma automáticamente el valor de Rama A
      MAX(CHANNEL)                                                                 AS CHANNEL,
      -- Campos presentes en ambas: prioridad Rama A
      COALESCE(MAX(IF(FUENTE_TABLA='ALL_CAMPAIGNS_NR', TEAM,      NULL)), MAX(TEAM))      AS TEAM,
      COALESCE(MAX(IF(FUENTE_TABLA='ALL_CAMPAIGNS_NR', STRATEGY,  NULL)), MAX(STRATEGY))  AS STRATEGY,
      COALESCE(MAX(IF(FUENTE_TABLA='ALL_CAMPAIGNS_NR', SUBSTRATEGY,NULL)), MAX(SUBSTRATEGY)) AS SUBSTRATEGY,
      COALESCE(MAX(IF(FUENTE_TABLA='ALL_CAMPAIGNS_NR', EXPERIMENT, NULL)), MAX(EXPERIMENT)) AS EXPERIMENT,
      MAX(NOTIFICATION_TYPE)                                                       AS NOTIFICATION_TYPE,
      MAX(BUSINESS_LINE_SEGMENT)                                                   AS BUSINESS_LINE_SEGMENT,
      COALESCE(MAX(IF(FUENTE_TABLA='ALL_CAMPAIGNS_NR', BUSINESS_LINE,NULL)), MAX(BUSINESS_LINE)) AS BUSINESS_LINE,
      MAX(STATUS)                                                                  AS STATUS,
      -- Funnel: priorizar Rama A (metodología más completa)
      COALESCE(MAX(IF(FUENTE_TABLA='ALL_CAMPAIGNS_NR', SENTS,        NULL)), MAX(SENTS))        AS SENTS,
      COALESCE(MAX(IF(FUENTE_TABLA='ALL_CAMPAIGNS_NR', TOTAL_TEST,   NULL)), MAX(TOTAL_TEST))   AS TOTAL_TEST,
      COALESCE(MAX(IF(FUENTE_TABLA='ALL_CAMPAIGNS_NR', TOTAL_CONTROL,NULL)), MAX(TOTAL_CONTROL)) AS TOTAL_CONTROL,
      COALESCE(MAX(IF(FUENTE_TABLA='ALL_CAMPAIGNS_NR', TOTAL_ARRIVED,NULL)), MAX(TOTAL_ARRIVED)) AS TOTAL_ARRIVED,
      COALESCE(MAX(IF(FUENTE_TABLA='ALL_CAMPAIGNS_NR', TOTAL_OPEN,   NULL)), MAX(TOTAL_OPEN))   AS TOTAL_OPEN,
      MAX(TOTAL_CLICK)                                                             AS TOTAL_CLICK,
      COALESCE(MAX(IF(FUENTE_TABLA='ALL_CAMPAIGNS_NR', OPEN_RATE,    NULL)), MAX(OPEN_RATE))    AS OPEN_RATE,
      -- Impacto incremental: priorizar Rama A (NR_INC_USERS/7D_ADJUST vs Q_NR_7D)
      COALESCE(MAX(IF(FUENTE_TABLA='ALL_CAMPAIGNS_NR', USER_INC,             NULL)), MAX(USER_INC))             AS USER_INC,
      COALESCE(MAX(IF(FUENTE_TABLA='ALL_CAMPAIGNS_NR', USER_INC_CON_ADJUST,  NULL)), MAX(USER_INC_CON_ADJUST))  AS USER_INC_CON_ADJUST,
      COALESCE(MAX(IF(FUENTE_TABLA='ALL_CAMPAIGNS_NR', VALUE_INC,            NULL)), MAX(VALUE_INC))            AS VALUE_INC,
      -- Métricas solo en Rama A (NULL en Rama B → MAX funciona directamente)
      MAX(TOTAL_ABSOLUTO_NR)                                                       AS TOTAL_ABSOLUTO_NR,
      MAX(NR_TOTAL_CONTROL)                                                        AS NR_TOTAL_CONTROL,
      MAX(ENTRY_TEST_JNY)                                                          AS ENTRY_TEST_JNY,
      MAX(ENTRY_CONTROL_JNY)                                                       AS ENTRY_CONTROL_JNY,
      MAX(RATIO_CANIBALIZACION)                                                    AS RATIO_CANIBALIZACION,
      -- Clasificación y flags
      COALESCE(MAX(IF(FUENTE_TABLA='ALL_CAMPAIGNS_NR', CLASIF_CAMPAIGNS,NULL)), MAX(CLASIF_CAMPAIGNS)) AS CLASIF_CAMPAIGNS,
      COALESCE(MAX(IF(FUENTE_TABLA='ALL_CAMPAIGNS_NR', FLAG_PAID,     NULL)), MAX(FLAG_PAID))     AS FLAG_PAID,
      COALESCE(MAX(IF(FUENTE_TABLA='ALL_CAMPAIGNS_NR', FLAG_INCENTIVO,NULL)), MAX(FLAG_INCENTIVO)) AS FLAG_INCENTIVO,
      -- Costos
      MAX(CONSUMIDO_USD)                                                           AS CONSUMIDO_USD,
      MAX(COSTO_ENVIO_USD)                                                         AS COSTO_ENVIO_USD,
      MAX(COSTO_MANTIKA_USD)                                                       AS COSTO_MANTIKA_USD,
      -- FUENTE_TABLA: 'AMBAS' si la comm está en las 2 tablas el mismo día y canal
      CASE
        WHEN COUNT(DISTINCT FUENTE_TABLA) > 1 THEN 'AMBAS'
        ELSE ANY_VALUE(FUENTE_TABLA)
      END                                                                          AS FUENTE_TABLA
    FROM combined
    GROUP BY COMMUNICATION_ID, SENT_DATE, MONTH_ID, CANAL
    ORDER BY SENT_DATE DESC, COMMUNICATION_ID, CANAL
    """



# ══════════════════════════════════════════════════════════════════
# SERIALIZACIÓN JSON
# ══════════════════════════════════════════════════════════════════

def make_json_serializable(value):
    """Convierte tipos no-JSON-nativos a tipos Python básicos.
    Necesario porque pandas/BQ pueden retornar numpy scalars, datetime objects, NaN, etc.
    """
    if value is None:
        return None
    if hasattr(value, 'isoformat'):   # datetime.date, datetime.datetime, pandas Timestamp
        return value.isoformat()
    if hasattr(value, 'item'):        # numpy int64, numpy float64
        return value.item()
    if isinstance(value, float) and value != value:   # NaN check (NaN != NaN siempre)
        return None
    return value


def dataframe_to_serializable_records(dataframe):
    """Convierte un DataFrame BQ a lista de dicts JSON-seguros."""
    return [
        {col: make_json_serializable(val) for col, val in row.items()}
        for row in dataframe.to_dict(orient='records')
    ]


# ══════════════════════════════════════════════════════════════════
# MODOS DE EJECUCIÓN
# ══════════════════════════════════════════════════════════════════

def run_full_rebuild(bq_client):
    """MODO FULL REBUILD: consulta los 5 meses completos y guarda el cache desde cero.

    Cuándo se usa:
      · Primera ejecución (cache no existe) — automático
      · python scripts/refresh_comms_oc_cache.py --full — forzado por usuario
      · Cuando el cache está corrupto o se quiere un reset total

    Tiempo estimado: 30–50 min (depende del volumen de datos en BT_OC_CUST_EVENT).
    """
    from_date = get_five_months_ago_start()   # primer día del mes de hace 5 meses
    to_date   = get_cache_cutoff_date()       # hoy - 7 días (corte rodante, no lunes)

    print(f"  Rango: {from_date.isoformat()} → {to_date.isoformat()} (5 meses completos)")
    print(f"  ⏳ Esto puede tardar 30–50 minutos en BQ...")

    sql = build_comms_oc_sql_for_date_range(from_date, to_date)

    try:
        dataframe_from_bq = bq_client.query(sql).result(timeout=7200).to_dataframe()
    except Exception as bq_error:
        print(f"\n  ERROR BQ: {bq_error}")
        print("\n  Causas frecuentes:")
        print("    · ADC sin permisos en SBOX_MARKETING o SBOX_EG_MKT")
        print("    · Nombre de tabla incorrecto en uno de los 2 datasets")
        sys.exit(1)

    all_records_serializable = dataframe_to_serializable_records(dataframe_from_bq)

    with open(CACHE_PATH, 'w', encoding='utf-8') as cache_file:
        json.dump(all_records_serializable, cache_file, ensure_ascii=False, indent=2)

    cache_size_kb = os.path.getsize(CACHE_PATH) / 1024
    print(f"  OK: Cache guardado ({len(all_records_serializable)} registros, {cache_size_kb:.0f} KB)")
    return all_records_serializable


def run_incremental_update(bq_client):
    """MODO INCREMENTAL: agrega solo el nuevo período estable al cache existente (~2 min).

    Flujo:
      1. Carga el cache existente desde JSON
      2. Detecta la fecha más reciente en el cache (get_max_date_in_cache)
      3. Consulta BQ desde esa fecha hasta hoy - 7 días (el nuevo período estable)
      4. Deduplica por COMMUNICATION_ID (maneja re-ejecuciones accidentales)
      5. Elimina registros más viejos que CACHE_HISTORY_MONTHS meses (purge)
      6. Ordena por fecha y sobreescribe el JSON

    Corte temporal (NO es lunes-a-lunes):
      · Cache cubre: SENT_DATE < hoy - 7 días  (rodante)
      · Fresh cubre: SENT_DATE >= hoy - 7 días  (gen_dashboard_v2.py)
      · Ejemplo: si hoy es miércoles 15, el cache va hasta el miércoles 8.

    Cuándo se usa:
      · Modo default cuando el cache ya existe
      · Correr una vez por semana, cualquier día de la semana
      · Tiempo estimado: 1–3 minutos (solo consulta el nuevo período)

    Robustez:
      · Si se corre dos veces en el mismo día: la segunda consulta retorna los
        mismos registros → la deduplicación los sobreescribe sin duplicar.
      · Si no se corrió en 2 semanas: consulta esas 2 semanas automáticamente.
    """
    # ── PASO 1: Cargar cache existente ───────────────────────────────────────
    with open(CACHE_PATH, 'r', encoding='utf-8') as cache_file:
        existing_cache_records = json.load(cache_file)
    print(f"  Cache existente cargado: {len(existing_cache_records)} registros")

    # ── PASO 2: Determinar el rango de la consulta incremental ───────────────
    # from_date: el día siguiente al más reciente en el cache (o 5 meses atrás si vacío)
    # to_date: hoy - 7 días (corte rodante — los datos de los últimos 7 días aún pueden cambiar)
    cutoff_date   = get_cache_cutoff_date()   # hoy - 7 días
    max_date_str  = get_max_date_in_cache(existing_cache_records)

    if max_date_str:
        # Desde el día después del último registro del cache hasta el corte
        max_date_in_cache = datetime.date.fromisoformat(max_date_str)
        from_date_incremental = max_date_in_cache + datetime.timedelta(days=1)
    else:
        # Cache vacío — equivale a full rebuild pero con el rango normal
        from_date_incremental = get_five_months_ago_start()

    to_date_incremental = cutoff_date  # hoy - 7 días (exclusive)

    if from_date_incremental >= to_date_incremental:
        print(f"  Cache ya está al día (última fecha: {max_date_str}, corte: {cutoff_date})")
        print(f"  No hay datos nuevos para agregar.")
        return existing_cache_records

    print(f"  Rango incremental: {from_date_incremental.isoformat()} → {to_date_incremental.isoformat()}")
    print(f"  (Desde el día siguiente al último registro del cache hasta hoy - 7 días)")
    print(f"  ⏳ Esto tarda 1–3 minutos...")

    sql_for_new_week = build_comms_oc_sql_for_date_range(
        from_date_incremental,
        to_date_incremental
    )

    try:
        dataframe_new_week = bq_client.query(sql_for_new_week).result(timeout=7200).to_dataframe()
    except Exception as bq_error:
        print(f"\n  ERROR BQ consultando semana incremental: {bq_error}")
        print("  El cache existente NO fue modificado.")
        sys.exit(1)

    new_week_records_serializable = dataframe_to_serializable_records(dataframe_new_week)
    print(f"  BQ retornó {len(new_week_records_serializable)} registros nuevos de la semana pasada")

    # ── PASO 3: Merge — deduplicar por (COMMUNICATION_ID, SENT_DATE, CANAL, FUENTE_TABLA) ──
    # §75: clave compuesta diaria — un COMM_ID puede tener múltiples filas
    # (una por SENT_DATE × CANAL × FUENTE_TABLA). Los nuevos sobreescriben existentes
    # para el mismo día (útil si se corre dos veces o BQ corrige datos retroactivos).
    def _cache_key(r):
        return (
            str(r.get('COMMUNICATION_ID', '')),
            str(r.get('SENT_DATE', '')),
            str(r.get('CANAL', '')),
            str(r.get('FUENTE_TABLA', '')),
        )

    merged_records_dict_by_comm_id = {
        _cache_key(record): record
        for record in existing_cache_records
        if record.get('COMMUNICATION_ID')
    }
    overwritten_count = 0
    for new_record in new_week_records_serializable:
        if not new_record.get('COMMUNICATION_ID'):
            continue
        k = _cache_key(new_record)
        if k in merged_records_dict_by_comm_id:
            overwritten_count += 1
        merged_records_dict_by_comm_id[k] = new_record

    if overwritten_count > 0:
        print(f"  Nota: {overwritten_count} registros sobreescritos (re-ejecución o corrección BQ)")

    # ── PASO 4: Purge — eliminar registros fuera del horizonte permitido ──────
    # Usa get_oldest_allowed_date() que respeta el metadata si se usó --append.
    # Sin metadata: purge a 5 meses. Con metadata: respeta oldest_date.
    oldest_date_allowed = get_oldest_allowed_date()
    oldest_date_str     = oldest_date_allowed.isoformat()

    all_merged_records = list(merged_records_dict_by_comm_id.values())
    records_after_purge = [
        r for r in all_merged_records
        if str(r.get('SENT_DATE', '')) >= oldest_date_str   # §75: SENT_DATE (antes FIRST_SENT_DATE)
    ]
    purged_count = len(all_merged_records) - len(records_after_purge)
    if purged_count > 0:
        print(f"  Purge: {purged_count} registros eliminados (anteriores a {oldest_date_str})")

    # ── PASO 5: Ordenar y guardar ────────────────────────────────────────────
    records_after_purge.sort(
        key=lambda r: str(r.get('SENT_DATE', '')),    # §75: SENT_DATE (antes FIRST_SENT_DATE)
        reverse=True   # más reciente primero
    )

    with open(CACHE_PATH, 'w', encoding='utf-8') as cache_file:
        json.dump(records_after_purge, cache_file, ensure_ascii=False, indent=2)

    cache_size_kb = os.path.getsize(CACHE_PATH) / 1024
    print(f"  OK: Cache actualizado ({len(records_after_purge)} registros, {cache_size_kb:.0f} KB)")
    return records_after_purge


# ══════════════════════════════════════════════════════════════════
# MODO CLEAN — filtrado local sin BQ
# ══════════════════════════════════════════════════════════════════

def run_fix_email_dates():
    """MODO FIX-EMAIL-DATES: elimina del cache los registros de EMAIL con fecha fallback.

    El problema: emails que no matchearon en email_events (JOIN falla) quedan con
    FIRST_SENT_DATE = primer día del mes ('????-??-01') en lugar de la fecha real.
    Este modo elimina esos registros para que el próximo --append los regenere
    con la fecha correcta usando el HAVING corregido (test/arrived/open).

    Sin BQ, instantáneo. Recomendado antes de correr --append.
    """
    if not os.path.exists(CACHE_PATH):
        print("  ERROR: No existe el cache. Nada que limpiar.")
        return

    with open(CACHE_PATH, 'r', encoding='utf-8') as f:
        records = json.load(f)

    total_before = len(records)

    def _has_fallback_date(r):
        date = str(r.get('FIRST_SENT_DATE', ''))
        canal = str(r.get('CANAL', '')).upper()
        # Solo aplica a EMAIL. Fecha que termina en '-01' indica fallback.
        return canal == 'EMAIL' and date.endswith('-01')

    clean_records = [r for r in records if not _has_fallback_date(r)]
    removed = total_before - len(clean_records)

    if removed == 0:
        print(f"  OK: No se encontraron emails con fecha fallback ({total_before:,} registros).")
        return

    clean_records.sort(key=lambda r: str(r.get('FIRST_SENT_DATE', '')), reverse=True)
    with open(CACHE_PATH, 'w', encoding='utf-8') as f:
        json.dump(clean_records, f, ensure_ascii=False, indent=2)

    cache_size_kb = os.path.getsize(CACHE_PATH) / 1024
    print(f"  OK: {removed:,} emails con fecha '??-01' eliminados.")
    print(f"  Cache: {total_before:,} -> {len(clean_records):,} registros ({cache_size_kb:.0f} KB)")
    print(f"  Siguiente paso: correr --append para cada rango histórico.")
    print(f"  El merge inteligente asignará la fecha real a cada email.")


def _record_should_exclude(record):
    """Retorna True si el registro debe ser excluido por los filtros de calidad."""
    seg_canal    = str(record.get('BUSINESS_LINE_SEGMENT_CHANNELS') or '')
    team         = str(record.get('TEAM') or '')
    campaign     = str(record.get('CAMPAIGN_NAME_CLEAN') or record.get('CAMPAIGN_NAME') or '')
    campaign_up  = campaign.upper()
    canal        = str(record.get('CANAL') or '').upper()

    # Exclusiones generales (todos los canales)
    if (
        'SELLER'    in seg_canal.upper()
        or 'SELLER'    in team.upper()
        or '-XT1-'     in campaign_up
        or '-ENG'      in campaign_up
        or 'SEV-T3-'   in campaign_up
        or 'T1'        in campaign_up
        or 'XSELL'     in campaign_up
        or 'SVS_CUPON' in campaign_up
        or 'SVS'       in campaign_up
    ):
        return True

    # Exclusiones específicas REAL ESTATE (no aplicar a PUSH/EMAIL/FLOWS)
    if canal == 'REAL ESTATE' and (
        'POINT'          in campaign_up  # cross-sell mini POINT-SHCT-*
        or 'MINI'        in campaign_up  # MINI99, MINI109, MINI-MULTI
        or 'LOYALTY'     in campaign_up  # loyalty campaigns
        or 'CRYPTO'      in campaign_up  # crypto/cripto
        or 'CRIPTO'      in campaign_up
        or 'ENGAGED'     in campaign_up  # engagement (no adquisición)
        or '_ENG'        in campaign_up  # *_ENG_* (ej. LIFECYCLE_ENG_V1)
        or 'XSLL'        in campaign_up  # variante XSELL
        or 'XSMP'        in campaign_up  # cross-sell MP
        or 'CROSS_SELLING' in campaign_up
        or 'CROSS-SELLING' in campaign_up
    ):
        return True

    return False


def run_clean():
    """MODO CLEAN: filtra el cache existente en Python puro, sin consultar BQ.

    Aplica los mismos criterios de exclusión que el WHERE final de la query:
      · Elimina registros con SELLER en BUSINESS_LINE_SEGMENT_CHANNELS (Seg. Canal)
      · Elimina registros con SELLER en TEAM
    No modifica la lógica de purge ni el metadata.
    """
    if not os.path.exists(CACHE_PATH):
        print("  ERROR: No existe el cache. Nada que limpiar.")
        sys.exit(1)

    with open(CACHE_PATH, 'r', encoding='utf-8') as f:
        records = json.load(f)

    total_before = len(records)
    clean_records = [r for r in records if not _record_should_exclude(r)]
    removed = total_before - len(clean_records)

    if removed == 0:
        print(f"  OK: No se encontraron registros SELLER en el cache ({total_before:,} registros, nada que limpiar).")
        return

    # Ordenar y guardar
    clean_records.sort(key=lambda r: str(r.get('FIRST_SENT_DATE', '')), reverse=True)
    with open(CACHE_PATH, 'w', encoding='utf-8') as f:
        json.dump(clean_records, f, ensure_ascii=False, indent=2)

    cache_size_kb = os.path.getsize(CACHE_PATH) / 1024
    print(f"  OK: {removed:,} registros SELLER eliminados.")
    print(f"  Cache: {total_before:,} -> {len(clean_records):,} registros ({cache_size_kb:.0f} KB)")
    if clean_records:
        print(f"  Cobertura: {clean_records[-1].get('FIRST_SENT_DATE','?')} -> {clean_records[0].get('FIRST_SENT_DATE','?')}")


# ══════════════════════════════════════════════════════════════════
# MODO APPEND HISTÓRICO
# ══════════════════════════════════════════════════════════════════

def run_historical_append(bq_client, from_date_inclusive, to_date_exclusive):
    """MODO APPEND HISTÓRICO: agrega un rango pasado al cache existente.

    Uso típico:
      python scripts/refresh_comms_oc_cache.py --append --from 2025-06-01 --to 2025-11-01

    Flujo:
      1. Consulta BQ para el rango [from_date_inclusive, to_date_exclusive)
      2. Carga el cache existente (si hay)
      3. Merge deduplicando por COMMUNICATION_ID (los nuevos tienen prioridad)
      4. Ordena por FIRST_SENT_DATE desc
      5. Guarda metadata oldest_date para proteger estos registros del purge futuro
      6. Escribe el cache actualizado

    El modo incremental posterior respetará la oldest_date guardada en metadata
    y NO purgará los registros históricos añadidos aquí.

    Tiempo estimado: ~30-50 min por cada 5 meses de datos en BT_OC_CUST_EVENT.
    """
    print(f"  Rango histórico a agregar: {from_date_inclusive.isoformat()} → {to_date_exclusive.isoformat()}")
    print(f"  ⏳ Esto puede tardar 30-50 minutos en BQ (depende de contención de ranuras)...")

    sql = build_comms_oc_sql_for_date_range(from_date_inclusive, to_date_exclusive)

    try:
        df_historical = bq_client.query(sql).result(timeout=7200).to_dataframe()
    except Exception as bq_error:
        print(f"\n  ERROR BQ consultando rango histórico: {bq_error}")
        print("  El cache existente NO fue modificado.")
        sys.exit(1)

    new_historical_records = dataframe_to_serializable_records(df_historical)
    print(f"  BQ retornó {len(new_historical_records)} registros del rango histórico")

    # ── Cargar cache existente ───────────────────────────────────────────────
    existing_records = []
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, 'r', encoding='utf-8') as f:
            existing_records = json.load(f)
        print(f"  Cache existente: {len(existing_records)} registros")

    # ── Merge: dedup por (COMMUNICATION_ID, SENT_DATE, CANAL, FUENTE_TABLA) ──
    # §75: clave compuesta diaria — misma lógica que run_incremental_update y processors.py.
    # Regla: los registros NUEVOS de BQ siempre ganan sobre los existentes en el cache
    # para el mismo (COMM_ID, SENT_DATE, CANAL, FUENTE_TABLA).
    def _append_key(r):
        return (
            str(r.get('COMMUNICATION_ID', '')),
            str(r.get('SENT_DATE', '')),
            str(r.get('CANAL', '')),
            str(r.get('FUENTE_TABLA', '')),
        )

    existing_by_id = {_append_key(r): r
                      for r in existing_records if r.get('COMMUNICATION_ID')}
    overridden = 0
    added_new  = 0

    for new_rec in new_historical_records:
        if not new_rec.get('COMMUNICATION_ID'):
            continue
        k = _append_key(new_rec)
        if k in existing_by_id:
            overridden += 1
        else:
            added_new += 1
        existing_by_id[k] = new_rec   # nuevo siempre gana (viene directo de BQ)

    print(f"  Registros nuevos agregados: {added_new}")
    if overridden > 0:
        print(f"  Registros actualizados (mismo día+canal ya existía): {overridden}")

    # ── Combinar y ordenar ───────────────────────────────────────────────────
    merged = sorted(existing_by_id.values(),
                    key=lambda r: str(r.get('SENT_DATE', '')), reverse=True)  # §75: SENT_DATE

    # ── Guardar cache ────────────────────────────────────────────────────────
    with open(CACHE_PATH, 'w', encoding='utf-8') as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    cache_size_kb = os.path.getsize(CACHE_PATH) / 1024

    # ── Actualizar metadata: proteger oldest_date del purge futuro ───────────
    # Comparar con metadata existente y guardar la fecha más antigua
    current_meta   = load_cache_meta()
    current_oldest = current_meta.get('oldest_date', '9999-99-99')
    new_oldest     = from_date_inclusive.isoformat()
    oldest_to_save = min(current_oldest, new_oldest)  # la más antigua de las dos
    save_cache_meta(oldest_to_save)

    print(f"\n  OK: Cache actualizado — {len(merged)} registros totales ({cache_size_kb:.0f} KB)")
    if merged:
        oldest_in_cache = merged[-1].get('SENT_DATE', '?')   # §75: SENT_DATE
        newest_in_cache = merged[0].get('SENT_DATE', '?')
        print(f"  Cobertura: {oldest_in_cache} → {newest_in_cache}")
    print(f"  Metadata guardada: oldest_date protegida = {oldest_to_save}")
    print(f"  Los incrementales futuros NO purgarán registros anteriores a {oldest_to_save}")


# ══════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════

def main():
    force_full_rebuild    = '--full'             in sys.argv
    force_append_history  = '--append'           in sys.argv
    force_clean           = '--clean'            in sys.argv
    force_fix_email_dates = '--fix-email-dates'  in sys.argv
    cache_exists          = os.path.exists(CACHE_PATH)

    today        = datetime.date.today()
    cutoff_d7    = get_cache_cutoff_date()
    five_mo_ago  = get_five_months_ago_start()
    meta         = load_cache_meta()

    print("=" * 62)
    print("refresh_comms_oc_cache.py — Cache Comms_OC")
    print("=" * 62)
    print(f"Hoy          : {today.isoformat()}")
    print(f"Corte D-7    : {cutoff_d7.isoformat()} (cache cubre < esta fecha)")
    print(f"Cache destino: {CACHE_PATH}")
    print(f"Cache existe : {'SI' if cache_exists else 'NO'}")
    if meta.get('oldest_date'):
        print(f"Oldest date  : {meta['oldest_date']} (protegido por metadata — no se purgará)")
    print()

    # ── MODO FIX-EMAIL-DATES (sin BQ) ───────────────────────────────────────
    if force_fix_email_dates:
        print("MODO: FIX-EMAIL-DATES (sin BQ)")
        print("  Elimina emails con fecha fallback '??-01' para regenerar con fecha real")
        print()
        run_fix_email_dates()
        return

    # ── MODO CLEAN (sin BQ) ──────────────────────────────────────────────────
    if force_clean:
        print("MODO: CLEAN (filtrado local — sin BQ)")
        print("  Elimina registros con SELLER en Seg.Canal (BUSINESS_LINE_SEGMENT_CHANNELS) o Team")
        print()
        run_clean()
        return

    # ── MODO APPEND HISTÓRICO ────────────────────────────────────────────────
    if force_append_history:
        # Parsear --from y --to del argv
        try:
            from_idx   = sys.argv.index('--from') + 1
            to_idx     = sys.argv.index('--to')   + 1
            from_date  = datetime.date.fromisoformat(sys.argv[from_idx])
            to_date    = datetime.date.fromisoformat(sys.argv[to_idx])
        except (ValueError, IndexError):
            print("ERROR: --append requiere --from YYYY-MM-DD y --to YYYY-MM-DD")
            print("Ejemplo: python scripts/refresh_comms_oc_cache.py --append --from 2025-06-01 --to 2025-11-01")
            sys.exit(1)

        print("MODO: APPEND HISTÓRICO")
        print(f"  Rango     : {from_date.isoformat()} → {to_date.isoformat()}")
        print(f"  Atención  : esta consulta puede tardar 30-50 min en BQ.")
        print()
        client = bigquery.Client(project=BQ_PROJECT)
        run_historical_append(client, from_date, to_date)

    # ── MODO FULL REBUILD ────────────────────────────────────────────────────
    elif not cache_exists or force_full_rebuild:
        if force_full_rebuild and cache_exists:
            print("MODO: FULL REBUILD (forzado con --full)")
        else:
            print("MODO: FULL REBUILD (cache no existe — primera ejecucion)")
        print(f"  Rango BQ : {five_mo_ago.isoformat()} -> {cutoff_d7.isoformat()}")
        print(f"  Atencion : esta consulta puede tardar 30-50 minutos.")
        print()
        client = bigquery.Client(project=BQ_PROJECT)
        run_full_rebuild(client)

    # ── MODO INCREMENTAL ─────────────────────────────────────────────────────
    else:
        print("MODO: INCREMENTAL (cache existe)")
        print(f"  Corte     : hoy ({today}) - 7 dias = {cutoff_d7}")
        print(f"  Duracion  : 1-3 minutos (solo el periodo nuevo)")
        print()
        client = bigquery.Client(project=BQ_PROJECT)
        run_incremental_update(client)

    print()
    print("Siguiente paso: python src/gen_dashboard_v2.py")
    print()
    print("Correr una vez por semana (cualquier dia):")
    print("  Incremental (default, ~2 min) : python scripts/refresh_comms_oc_cache.py")
    print("  Full rebuild si hay problemas  : python scripts/refresh_comms_oc_cache.py --full")


if __name__ == '__main__':
    main()
