# Query Fuente: Pestaña `Comms_OC`

> ⚠️ **DOCUMENTO EN TRANSICIÓN** — §75 (pendiente): migración de fuentes a
> `BT_OC_DASHBOARD_ALL_CAMPAIGNS_NR` + `BT_OC_DASHBOARD_ALL_CAMPAIGNS_NR_ACQUISITION`.
> El estado **anterior a la migración** está documentado en `comms_oc_legacy.md` (snapshot inmutable).
> Este archivo se actualizará con la nueva arquitectura una vez completada la migración.

**Última actualización**: 2026-04-15 (pre-migración §75)
**Implementación actual (legacy)**: `src/queries.py` → `get_comms_oc_fresh_sql()` y
`scripts/refresh_comms_oc_cache.py` → `build_comms_oc_sql_for_date_range()`
**Estrategia de datos**: Two-Tier Caching (ver sección correspondiente)

---

## Propósito

Responde la pregunta: **¿Qué comunicaciones de OC se enviaron, a cuántos usuarios únicos
llegaron en cada paso del funnel, y cuál fue su eficiencia e impacto incremental?**

Vista a nivel de COMMUNICATION_ID individual. Permite analizar rendimiento de campañas
de Own Channels (UCR, OC ACT) cruzando tres fuentes de datos distintas.

---

## Tablas BQ involucradas (3 tablas, 2 datasets)

| Tabla | Dataset | Proyecto | Contenido | Clave de JOIN |
|---|---|---|---|---|
| `BT_OC_CUST_EVENT` | `SBOX_MARKETING` | `meli-bi-data` | Eventos del funnel por usuario × comunicación | `COMMUNICATION_ID` |
| `DASHBOARD_CAMPAIGNS_INDIVIDUOS_METRICAS` | `SBOX_EG_MKT` | *(default)* | Métricas de eficiencia e impacto a nivel CAMPAÑA × MES | `CAMPAIGN_NAME_CLEAN + SIT_SITE_ID + MONTH_ID` |
| `BT_OC_DASHBOARD_ALL_CAMPAIGNS` | `SBOX_EG_MKT` | *(default)* | Meta-data de cada comunicación: canal, app, título, texto | `COMMUNICATION_ID` |

> ⚠️ Las dos tablas de `SBOX_EG_MKT` **no llevan prefijo de proyecto** en el SQL —
> usan el proyecto por defecto del cliente BQ. Verificar que el ADC tenga permisos en ese dataset.

---

## SQL Canónico

Listo para ejecutar en BQ UI. Sustituye las fechas de ejemplo por las que necesites.

```sql
WITH raw_events_agg AS (
  -- FUNNEL DE USUARIOS ÚNICOS por COMMUNICATION_ID.
  -- COUNT(DISTINCT IF(..., CUS_CUST_ID, NULL)):
  --   cuenta cada usuario EXACTAMENTE UNA VEZ por tipo de evento,
  --   aunque genere múltiples filas en la tabla (reintentos, duplicados técnicos).
  -- CUS_CUST_ID = identificador único del cliente en BT_OC_CUST_EVENT.
  SELECT
    COMMUNICATION_ID,
    ANY_VALUE(CAMPAIGN_NAME)       AS CAMPAIGN_NAME,
    ANY_VALUE(SIT_SITE_ID)         AS SIT_SITE_ID,
    MIN(DATE(SENT_DATE))           AS FIRST_SENT_DATE,
    COUNT(DISTINCT IF(LOWER(TRIM(EVENT_TYPE)) = 'create',  CUS_CUST_ID, NULL)) AS TOTAL_CREATE_CUST_EVENT,
    COUNT(DISTINCT IF(LOWER(TRIM(EVENT_TYPE)) = 'test',    CUS_CUST_ID, NULL)) AS TOTAL_TEST_CUST_EVENT,
    COUNT(DISTINCT IF(LOWER(TRIM(EVENT_TYPE)) = 'control', CUS_CUST_ID, NULL)) AS TOTAL_CONTROL_CUST_EVENT,
    COUNT(DISTINCT IF(LOWER(TRIM(EVENT_TYPE)) = 'arrived', CUS_CUST_ID, NULL)) AS TOTAL_ARRIVED_CUST_EVENT,
    COUNT(DISTINCT IF(LOWER(TRIM(EVENT_TYPE)) = 'shown',   CUS_CUST_ID, NULL)) AS TOTAL_SHOWN_CUST_EVENT,
    COUNT(DISTINCT IF(LOWER(TRIM(EVENT_TYPE)) = 'open',    CUS_CUST_ID, NULL)) AS TOTAL_OPEN_CUST_EVENT
  FROM `meli-bi-data.SBOX_MARKETING.BT_OC_CUST_EVENT`
  WHERE SIT_SITE_ID = 'MLM'
    AND BUSINESS_UNIT IN ('MERCADOPAGO', 'MARKETPLACE')
    AND SENT_DATE >= DATE '2025-11-01'   -- ← ajustar según rango
    AND SENT_DATE <  DATE '2026-04-08'   -- ← ajustar según rango (exclusivo)
    AND LOWER(TRIM(EVENT_TYPE)) IN ('create', 'test', 'control', 'arrived', 'shown', 'open')
    AND COMMUNICATION_ID IS NOT NULL
  GROUP BY 1
),

ce_clean AS (
  -- Normalización de claves.
  -- COMMUNICATION_ID: puede venir como '12345.0' (float serializado)
  --   SPLIT('.')[OFFSET(0)] extrae solo la parte entera '12345'.
  -- CAMPAIGN_NAME: elimina sufijo '_DEFAULT' (variante A/B de control)
  --   para unificar todas las variantes bajo el mismo nombre de campaña.
  -- NULLIF(..., ''): evita cruces cartesianos si el nombre queda vacío tras normalizar.
  SELECT
    SPLIT(CAST(COMMUNICATION_ID AS STRING), '.')[OFFSET(0)] AS COMMUNICATION_ID_STR,
    CAMPAIGN_NAME,
    NULLIF(
      CASE
        WHEN ENDS_WITH(TRIM(CAMPAIGN_NAME), '_DEFAULT')
          THEN SUBSTR(TRIM(CAMPAIGN_NAME), 1, LENGTH(TRIM(CAMPAIGN_NAME)) - 8)
        ELSE TRIM(CAMPAIGN_NAME)
      END,
    '') AS CAMPAIGN_NAME_CLEAN,
    SIT_SITE_ID,
    FIRST_SENT_DATE,
    DATE_TRUNC(FIRST_SENT_DATE, MONTH) AS MONTH_ID,
    TOTAL_CREATE_CUST_EVENT, TOTAL_TEST_CUST_EVENT, TOTAL_CONTROL_CUST_EVENT,
    TOTAL_ARRIVED_CUST_EVENT, TOTAL_SHOWN_CUST_EVENT, TOTAL_OPEN_CUST_EVENT
  FROM raw_events_agg
),

indiv_metrics AS (
  -- Métricas de eficiencia e impacto agregadas a nivel CAMPAÑA × MES.
  -- ⚠️ GRANULARIDAD CAMPAÑA, no por comunicación individual:
  --    Si una campaña tiene N comunicaciones (N COMM_IDs), todas recibirán
  --    las mismas métricas al hacer LEFT JOIN más abajo.
  -- CHANNELS_METRICS: STRING_AGG de BUSINESS_LINE_SEGMENT_CHANNELS de esta tabla.
  --   Es distinto a cm.BUSINESS_LINE_SEGMENT_CHANNELS que viene de camp_meta
  --   (fuentes diferentes con posible diferencia en valores).
  -- MONTH_ID aquí es tipo DATE (primer día del mes: 2025-11-01).
  --   ⚠️ NO comparar con strings tipo '202511' — lanza error "Could not cast to DATE".
  SELECT
    MONTH_ID, SIT_SITE_ID,
    NULLIF(
      CASE
        WHEN ENDS_WITH(TRIM(CAMPAIGN_NAME), '_DEFAULT')
          THEN SUBSTR(TRIM(CAMPAIGN_NAME), 1, LENGTH(TRIM(CAMPAIGN_NAME)) - 8)
        ELSE TRIM(CAMPAIGN_NAME)
      END,
    '') AS CAMPAIGN_NAME_CLEAN,
    STRING_AGG(DISTINCT STRATEGY,                       ' | ') AS STRATEGIES,
    STRING_AGG(DISTINCT SUBSTRATEGY,                    ' | ') AS SUBSTRATEGIES,
    STRING_AGG(DISTINCT BUSINESS_LINE_SEGMENT_CHANNELS, ' | ') AS CHANNELS_METRICS,
    SUM(COUNT_USERS_TEST) AS SENTS,
    AVG(OPEN_RATE)        AS OPEN_RATE,
    AVG(M_CVR_TEST)       AS M_CVR_TEST,
    AVG(M_LIFT)           AS M_LIFT,
    SUM(M_INC_USERS)      AS USER_INC,
    SUM(M_INC_TPN_1)      AS TPN_INC,
    SUM(M_INC_TPV_1)      AS TPV_INC,
    SUM(M_INC_VALUE)      AS VALUE_INC
  FROM `SBOX_EG_MKT.DASHBOARD_CAMPAIGNS_INDIVIDUOS_METRICAS`
  WHERE SIT_SITE_ID = 'MLM'
    AND MONTH_ID >= DATE '2025-11-01'   -- ← primer día del mes de inicio
    AND STRATEGY NOT IN ('ENGAGEMENT', 'RETENTION')
    AND BUSINESS_LINE_SEGMENT_CHANNELS NOT LIKE '%SELLER%'
  GROUP BY 1, 2, 3
  HAVING CAMPAIGN_NAME_CLEAN IS NOT NULL
),

camp_meta AS (
  -- Meta-data de la comunicación individual.
  -- BUSINESS_LINE_SEGMENT_CHANNELS aquí viene de BT_OC_DASHBOARD_ALL_CAMPAIGNS.
  -- Es distinto a im.CHANNELS_METRICS (ver indiv_metrics arriba).
  -- ANY_VALUE: una comunicación puede tener múltiples filas en esta tabla (un mes = una fila).
  -- MONTH_ID aquí también es tipo DATE — mismo gotcha que en indiv_metrics.
  SELECT
    SPLIT(CAST(COMMUNICATION_ID AS STRING), '.')[OFFSET(0)] AS COMMUNICATION_ID_STR,
    ANY_VALUE(CANAL)                          AS CANAL,
    ANY_VALUE(APP)                            AS APP,
    ANY_VALUE(NOTIFICATION_TITLE)             AS NOTIFICATION_TITLE,
    ANY_VALUE(NOTIFICATION_TEXT)              AS NOTIFICATION_TEXT,
    ANY_VALUE(BUSINESS_LINE_SEGMENT_CHANNELS) AS BUSINESS_LINE_SEGMENT_CHANNELS
  FROM `SBOX_EG_MKT.BT_OC_DASHBOARD_ALL_CAMPAIGNS`
  WHERE SITE = 'MLM'
    AND MONTH_ID >= DATE '2025-11-01'   -- ← primer día del mes de inicio
    AND STRATEGY NOT IN ('ENGAGEMENT', 'RETENTION')
    AND COMMUNICATION_ID IS NOT NULL
  GROUP BY 1
  HAVING COMMUNICATION_ID_STR IS NOT NULL AND COMMUNICATION_ID_STR != ''
)

-- JOIN FINAL
-- LEFT JOINs: no se pierden comunicaciones aunque no tengan meta o no tengan métricas.
-- CAST + FORMAT_DATE en el SELECT: columnas ya STRING-safe para serialización JSON.
SELECT
  CAST(ce.FIRST_SENT_DATE AS STRING) AS FIRST_SENT_DATE,
  FORMAT_DATE('%Y%m', ce.MONTH_ID)  AS MONTH_ID,
  ce.COMMUNICATION_ID_STR           AS COMMUNICATION_ID,
  ce.CAMPAIGN_NAME,
  ce.CAMPAIGN_NAME_CLEAN,
  cm.CANAL,
  cm.APP,
  cm.NOTIFICATION_TITLE,
  cm.NOTIFICATION_TEXT,
  cm.BUSINESS_LINE_SEGMENT_CHANNELS,
  ce.TOTAL_CREATE_CUST_EVENT,
  ce.TOTAL_TEST_CUST_EVENT,
  ce.TOTAL_CONTROL_CUST_EVENT,
  ce.TOTAL_ARRIVED_CUST_EVENT,
  ce.TOTAL_SHOWN_CUST_EVENT,
  ce.TOTAL_OPEN_CUST_EVENT,
  im.STRATEGIES,
  im.SUBSTRATEGIES,
  im.CHANNELS_METRICS,
  im.SENTS,
  im.OPEN_RATE,
  im.M_CVR_TEST,
  im.M_LIFT,
  im.USER_INC,
  im.TPN_INC,
  im.TPV_INC,
  im.VALUE_INC
FROM ce_clean ce
LEFT JOIN camp_meta cm
  ON  ce.COMMUNICATION_ID_STR = cm.COMMUNICATION_ID_STR
LEFT JOIN indiv_metrics im
  ON  ce.CAMPAIGN_NAME_CLEAN  = im.CAMPAIGN_NAME_CLEAN
  AND ce.SIT_SITE_ID          = im.SIT_SITE_ID
  AND ce.MONTH_ID             = im.MONTH_ID
ORDER BY ce.FIRST_SENT_DATE DESC
```

---

## Parámetros de fecha (cómo varía entre cache y fresh)

| Parámetro | Cache (rebuild histórico) | Fresh (refresh diario) |
|---|---|---|
| `SENT_DATE >=` | Primer día de mes, hace 5 meses | `CURRENT_DATE - 7 días` |
| `SENT_DATE <` | `CURRENT_DATE - 7 días` | *(sin límite superior)* |
| `MONTH_ID >=` | Mismo mes del límite inferior | Mes del `CURRENT_DATE - 7` |
| Script | `scripts/refresh_comms_oc_cache.py --full` | `src/queries.py` `get_comms_oc_fresh_sql()` |
| Duración | ~40 min (5 meses de datos) | < 2 min (7 días) |

**Regla del corte D-7**: los datos con `SENT_DATE < hoy - 7 días` se consideran estables
(no cambian). La semana actual puede tener correcciones retroactivas de atribución.

---

## Columnas de salida (27 columnas)

### De `BT_OC_CUST_EVENT` vía `raw_events_agg` + `ce_clean`

| Columna | Tipo | Descripción |
|---|---|---|
| `FIRST_SENT_DATE` | STRING `'YYYY-MM-DD'` | Primera fecha de envío de la comunicación |
| `MONTH_ID` | STRING `'YYYYMM'` | Mes de la primera fecha (formateado para JSON) |
| `COMMUNICATION_ID` | STRING | ID único de la comunicación (limpiado de decimales) |
| `CAMPAIGN_NAME` | STRING | Nombre original de la campaña (raw, sin normalizar) |
| `CAMPAIGN_NAME_CLEAN` | STRING | Nombre normalizado (sufijo `_DEFAULT` removido) |
| `TOTAL_CREATE_CUST_EVENT` | INT | Usuarios únicos (CUS_CUST_ID) en evento CREATE |
| `TOTAL_TEST_CUST_EVENT` | INT | Usuarios únicos en grupo TEST |
| `TOTAL_CONTROL_CUST_EVENT` | INT | Usuarios únicos en grupo CONTROL |
| `TOTAL_ARRIVED_CUST_EVENT` | INT | Usuarios únicos que recibieron la comunicación |
| `TOTAL_SHOWN_CUST_EVENT` | INT | Usuarios únicos que la vieron |
| `TOTAL_OPEN_CUST_EVENT` | INT | Usuarios únicos que la abrieron |

### De `BT_OC_DASHBOARD_ALL_CAMPAIGNS` vía `camp_meta`

| Columna | Tipo | Descripción |
|---|---|---|
| `CANAL` | STRING | Tipo de canal: PUSH / EMAIL / PANDORA / JOURNEY / WPP |
| `APP` | STRING | Aplicación de origen de la comunicación |
| `NOTIFICATION_TITLE` | STRING | Asunto/título del mensaje (puede ser template `${payload.title}`) |
| `NOTIFICATION_TEXT` | STRING | Cuerpo del mensaje (puede ser muy largo) |
| `BUSINESS_LINE_SEGMENT_CHANNELS` | STRING | Segmento de canal de esta comunicación específica |

### De `DASHBOARD_CAMPAIGNS_INDIVIDUOS_METRICAS` vía `indiv_metrics`

| Columna | Tipo | Descripción |
|---|---|---|
| `STRATEGIES` | STRING | Estrategias de la campaña (STRING_AGG con ` \| `) |
| `SUBSTRATEGIES` | STRING | Sub-estrategias (STRING_AGG con ` \| `) |
| `CHANNELS_METRICS` | STRING | BUSINESS_LINE_SEGMENT_CHANNELS de esta tabla (puede diferir de `camp_meta`) |
| `SENTS` | FLOAT | Total de usuarios test (`COUNT_USERS_TEST`) |
| `OPEN_RATE` | FLOAT `[0-1]` | Tasa de apertura promedio |
| `M_CVR_TEST` | FLOAT `[0-1]` | Conversion rate del grupo test |
| `M_LIFT` | FLOAT `[0-1]` | Lift incremental (puede ser negativo) |
| `USER_INC` | FLOAT | Usuarios incrementales totales |
| `TPN_INC` | FLOAT | Transacciones incrementales |
| `TPV_INC` | FLOAT | Volumen de pago incremental |
| `VALUE_INC` | FLOAT `USD` | Valor incremental en dólares |

---

## Estrategia de actualización (Two-Tier Cache)

```
data/comms_oc_cache.json          ← Tier 1: histórico estable (< CURRENT_DATE - 7)
         +
get_comms_oc_fresh_sql()          ← Tier 2: semana actual (>= CURRENT_DATE - 7)
         ↓
processors.process_comms_oc()     ← merge automático en cada refresh del dashboard
```

**Protocolo semanal (una vez por semana, cualquier día):**
```bash
cd C:\Users\sergibarra\Documents\SI_Meli_code1\MLM_ADQ_Dash
..\vEnv_Meli_Code1\Scripts\activate
python scripts/refresh_comms_oc_cache.py          # incremental ~2 min
python src/gen_dashboard_v2.py                     # regenerar dashboard
```

**Full rebuild (solo si hay cambios de columnas o corrupción del cache):**
```bash
python scripts/refresh_comms_oc_cache.py --full   # ~40 min
```

---

## Gotchas críticos (errores ya cometidos — no repetir)

### 1. `EVENT_ID` no existe en `BT_OC_CUST_EVENT`
**Error**: `Unrecognized name: EVENT_ID`  
**Fix**: El campo correcto es `CUS_CUST_ID` (identificador único del cliente).  
**Impacto**: Si usas `COUNTIF` sin DISTINCT, puedes inflar conteos del funnel.

### 2. `MONTH_ID` es tipo `DATE`, no string
**Error**: `Could not cast literal "202511" to type DATE`  
**Fix**: Usar `DATE '2025-11-01'` (primer día del mes) en el WHERE, no `'202511'`.  
**Tablas afectadas**: `DASHBOARD_CAMPAIGNS_INDIVIDUOS_METRICAS` y `BT_OC_DASHBOARD_ALL_CAMPAIGNS`.

### 3. `NOTIFICATION_TEXT` omitido de `camp_meta`
**Síntoma**: Columna "Texto" siempre muestra `—` en el dashboard.  
**Causa**: Se olvidó incluir `ANY_VALUE(NOTIFICATION_TEXT)` en el SELECT de `camp_meta`.  
**Fix**: Siempre incluir los 5 campos de `camp_meta`: CANAL, APP, NOTIFICATION_TITLE, NOTIFICATION_TEXT, BUSINESS_LINE_SEGMENT_CHANNELS.

### 4. JOIN de `indiv_metrics` duplica métricas por campaña con N comunicaciones
**Comportamiento esperado (no es bug)**: Si una campaña tiene 3 COMMUNICATION_IDs,
los 3 registros en el output tendrán las mismas métricas (SENTS, USER_INC, etc.)
porque `indiv_metrics` agrega a nivel CAMPAÑA, no por comunicación individual.  
**Consecuencia**: Si sumas USER_INC sobre todos los COMM_IDs, triplicas el valor.  
**Fix en `builders.py`**: deduplicar por `CAMPAIGN_NAME_CLEAN` antes de agregar totales.

### 5. `SENT_DATE <  DATE '{to_date}'` es EXCLUSIVO
El filtro usa `<` (menor estricto), no `<=`. El día `to_date` no está incluido.  
Esto es intencional: el cache cubre `[from, D-7)` y el fresh cubre `[D-7, hoy]`.

### 6. `COMMUNICATION_ID` puede venir como float (`12345.0`)
El campo es numérico en BQ pero al castearlo a STRING puede incluir `.0`.  
**Fix**: `SPLIT(CAST(COMMUNICATION_ID AS STRING), '.')[OFFSET(0)]` extrae solo `'12345'`.

### 7. `CAMPAIGN_NAME` con sufijo `_DEFAULT`
Las variantes de control A/B agregan `_DEFAULT` al nombre.  
Sin normalización, la misma campaña aparece como dos campañas distintas y el JOIN
con `indiv_metrics` falla (no hay match para el nombre con sufijo).  
**Fix**: El CTE `ce_clean` elimina el sufijo antes de hacer el JOIN.

---

## Historial de cambios

| Fecha | Cambio |
|---|---|
| 2026-04-15 | Versión inicial. Query base con `COUNTIF` (sin DISTINCT). |
| 2026-04-15 | Agregado `NOTIFICATION_TEXT` y `BUSINESS_LINE_SEGMENT_CHANNELS` a `camp_meta`. |
| 2026-04-15 | Agregado `CHANNELS_METRICS` y `SUBSTRATEGIES` a `indiv_metrics`. |
| 2026-04-15 | Corregido conteo funnel: `COUNTIF` → `COUNT(DISTINCT IF(..., CUS_CUST_ID, NULL))`. |
| 2026-04-15 | Fix bug `MONTH_ID`: de string `'202511'` a `DATE '2025-11-01'`. |
| 2026-04-15 | Fix bug ORDER BY: eliminado `;` antes del `ORDER BY`. |
| 2026-04-15 | Implementada estrategia Two-Tier Cache con corte rodante D-7. |
