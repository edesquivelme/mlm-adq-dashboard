# Query Fuente: Pestaña `NR Mensual` (y derivadas: NR Diario, NR Diario Acumulado, MTD D7)

**Última actualización**: 2026-04-15  
**Implementación**: `src/queries.py` → `get_nr_sql(HIERARCHY_NR)`  
**Tipo de SQL**: ⚠️ **DINÁMICO** — generado por Python desde `config/channels_config.json`

---

## Diferencia fundamental vs. Comms_OC

> **En Comms_OC**, el SQL es estático (hardcoded). La fuente de verdad ES el SQL.
>
> **En NR_Mensual**, el SQL es generado. La fuente de verdad es `channels_config.json`.
> El `CASE WHEN` que clasifica canales se construye automáticamente leyendo
> `hierarchy_nr[].bq_mapping` de cada canal hoja (`is_leaf: true`).
>
> **Consecuencia**: para agregar o modificar un canal, **nunca** se edita el SQL —
> se edita `channels_config.json` y el SQL se regenera solo en el próximo run.

---

## Propósito

Responde la pregunta: **¿Cuántos N+R (Nuevos+Recuperados) generó cada canal de marketing
por día, mes y acumulado desde 2025-01-01?**

Esta query alimenta CUATRO pestañas del dashboard:

| Pestaña | Cómo usa los datos |
|---|---|
| **NR Mensual** | Suma `NR` por `FECHA_MES` → N+R mensual por canal |
| **NR Diario** | Delta diario: `CUM_NR[día D] - CUM_NR[día D-1]` |
| **NR Diario Acumulado** | `CUM_NR` directamente |
| **MTD D7** | `CUM_NR` al día de referencia (hoy-2 o último día disponible) |

---

## Tabla BQ fuente (1 tabla)

| Tabla | Dataset | Proyecto | Filtro principal |
|---|---|---|---|
| `PANEL_MONTHLY_DAILY_HISTORICO` | `SBOX_MKTCORPMP` | `meli-bi-data` | `SIT_SITE_ID = 'MLM'` · `FECHA_DIARIA >= 2025-01-01` |

> ⚠️ **Schema actualizado abr-2026**: columna renombrada de `CHANNEL` → `CHANNEL_APERTURA_3`
> y de `COST_USD` → `INVERSION_TOTAL_USD`. La query ya usa los nuevos nombres.

---

## SQL Canónico — Versión PLANTILLA

Esta es la estructura lógica. El bloque `{CASE_WHEN_CANALES}` lo genera Python.

```sql
WITH base AS (
  SELECT
    CASE
      {CASE_WHEN_CANALES}   -- ← generado desde channels_config.json
      ELSE 'ORG'
    END AS CANAL,
    FORMAT_DATE('%Y%m', FECHA_DIARIA)            AS FECHA_MES,
    CAST(EXTRACT(DAY FROM FECHA_DIARIA) AS INT64) AS DIA,
    NR_USERS                                      AS NR,
    COALESCE(INVERSION_TOTAL_USD, 0)              AS COST
  FROM `meli-bi-data.SBOX_MKTCORPMP.PANEL_MONTHLY_DAILY_HISTORICO`
  WHERE SIT_SITE_ID = 'MLM'
    AND FECHA_DIARIA >= DATE '2025-01-01'
),
agg AS (
  SELECT CANAL, FECHA_MES, DIA,
         SUM(NR)   AS NR,
         SUM(COST) AS COST
  FROM base
  GROUP BY 1, 2, 3
)
SELECT *,
       SUM(NR) OVER (PARTITION BY CANAL, FECHA_MES ORDER BY DIA) AS CUM_NR
FROM agg
```

---

## SQL Canónico — Versión GENERADA (estado actual: 2026-04-15)

Esta es la query exacta que corre hoy. Cambiará si se modifica `channels_config.json`.
**Copiar en BQ UI para debugging.**

```sql
WITH base AS (
  SELECT
    CASE
      WHEN STRATEGY IN ('ACQUISITION') AND UPPER(CHANNEL_APERTURA_3) IN ('OWN CHANNELS MKT')
        THEN 'UCR Gest'
      WHEN STRATEGY IN ('ACQUISITION') AND UPPER(CHANNEL_APERTURA_3) IN ('OWN CHANNELS PRD')
        THEN 'UCR PRD'
      WHEN STRATEGY IN ('ACTIVATION', 'OTHER') AND UPPER(CHANNEL_APERTURA_3) IN ('OWN CHANNELS MKT', 'ADHOC')
        THEN 'OC ACT'
      WHEN STRATEGY IN ('ACQUISITION') AND UPPER(CHANNEL_APERTURA_3) IN ('ACQUISITION POM', 'WEB POM', 'CTW POM', 'ACTIVATION POM', 'POM OTHERS', 'POM SELLERS')
        THEN 'POM ADQ'
      WHEN STRATEGY IN ('ACTIVATION', 'OTHER') AND UPPER(CHANNEL_APERTURA_3) IN ('ACTIVATION POM', 'WEB POM', 'CTW POM', 'POM OTHERS', 'POM SELLERS')
        THEN 'POM ACT'
      WHEN STRATEGY IN ('ACQUISITION') AND UPPER(CHANNEL_APERTURA_3) IN ('MGM')
        THEN 'MGM ADQ'
      WHEN STRATEGY IN ('ACTIVATION', 'OTHER') AND UPPER(CHANNEL_APERTURA_3) IN ('MGM')
        THEN 'MGM ACT'
      WHEN STRATEGY IN ('ACQUISITION') AND UPPER(CHANNEL_APERTURA_3) IN ('BRANDFORMANCE', 'OTHERS', 'PARTNERSHIPS', 'LANDINGS', 'AFFILIATES')
        THEN 'L&P ADQ'
      WHEN STRATEGY IN ('ACTIVATION') AND UPPER(CHANNEL_APERTURA_3) IN ('BRANDFORMANCE', 'OTHERS', 'PARTNERSHIPS', 'LANDINGS')
        THEN 'L&P ACT'
      ELSE 'ORG'
    END AS CANAL,
    FORMAT_DATE('%Y%m', FECHA_DIARIA)             AS FECHA_MES,
    CAST(EXTRACT(DAY FROM FECHA_DIARIA) AS INT64)  AS DIA,
    NR_USERS                                       AS NR,
    COALESCE(INVERSION_TOTAL_USD, 0)               AS COST
  FROM `meli-bi-data.SBOX_MKTCORPMP.PANEL_MONTHLY_DAILY_HISTORICO`
  WHERE SIT_SITE_ID = 'MLM'
    AND FECHA_DIARIA >= DATE '2025-01-01'
),
agg AS (
  SELECT CANAL, FECHA_MES, DIA,
         SUM(NR)   AS NR,
         SUM(COST) AS COST
  FROM base
  GROUP BY 1, 2, 3
)
SELECT *,
       SUM(NR) OVER (PARTITION BY CANAL, FECHA_MES ORDER BY DIA) AS CUM_NR
FROM agg
```

> ⚠️ Esta versión generada puede quedar desactualizada si se modifica `channels_config.json`.
> Para regenerarla: `python -c "import json,sys; sys.path.insert(0,'src'); from queries import get_nr_sql; print(get_nr_sql(json.load(open('config/channels_config.json'))['hierarchy_nr']))"` 
> ejecutado desde `MLM_ADQ_Dash/`.

---

## Cómo se genera el CASE WHEN (relación con channels_config.json)

Cada canal hoja (`is_leaf: true`) en `hierarchy_nr` tiene un campo `bq_mapping`:

```json
{
  "id": "oc_act",
  "label": "OC ACT",
  "is_leaf": true,
  "bq_mapping": {
    "strategy": ["ACTIVATION", "OTHER"],
    "channel":  ["OWN CHANNELS MKT", "ADHOC"]
  }
}
```

Python convierte esto en:
```sql
WHEN STRATEGY IN ('ACTIVATION', 'OTHER')
 AND UPPER(CHANNEL_APERTURA_3) IN ('OWN CHANNELS MKT', 'ADHOC')
 THEN 'OC ACT'
```

**Regla**: `channel` mapea a `CHANNEL_APERTURA_3` (nivel fino del schema abr-2026).  
El canal `ORG` es el catch-all — captura todo lo que no matchea ningún WHEN.  
Los canales con `"is_org": true` en `bq_mapping` son excluidos del CASE WHEN y van al ELSE.

---

## Columnas de salida

| Columna | Tipo | Descripción |
|---|---|---|
| `CANAL` | STRING | Label del canal según jerarquía del dashboard (ej. 'UCR Gest', 'POM ADQ', 'ORG') |
| `FECHA_MES` | STRING `'YYYYMM'` | Mes de la fecha diaria formateado |
| `DIA` | INT | Número de día dentro del mes (1–31) |
| `NR` | FLOAT | N+R del canal en ese día (puede ser negativo — correcciones de atribución) |
| `COST` | FLOAT | Inversión total del día en USD (`INVERSION_TOTAL_USD`, antes `COST_USD`) |
| `CUM_NR` | FLOAT | N+R acumulado del canal en el mes hasta el día D (window function) |

---

## Procesamiento posterior en Python (`processors.py`)

La query retorna granularidad diaria. `process_all()` hace forward-fill en Python:

```
Si CUM_NR del día D == 0 y CUM_NR del día D-1 > 0
  → conservar el último valor conocido (el canal no reportó ese día, no cayó a 0)
```

Después calcula los nodos agregados (bottom-up):
```
OC + UCR = UCR Gest + UCR PRD + OC ACT
POM TOTAL = POM ADQ + POM ACT
Total N+R = suma de todos los canales hoja
```

---

## Gotchas críticos

### 1. `CHANNEL` → `CHANNEL_APERTURA_3` (cambio de schema abr-2026)
La tabla renombró la columna. Cualquier referencia a `CHANNEL` en el WHERE lanza:
`Unrecognized name: CHANNEL at [4:57]`.  
**Fix ya aplicado**: la query usa `CHANNEL_APERTURA_3`.  
**Afecta a**: `get_nr_sql()` y `get_perf_vpu_sql()` (ambas leen DAILY_HISTORICO).

### 2. `COST_USD` → `INVERSION_TOTAL_USD` (mismo cambio de schema)
El campo de inversión también fue renombrado.  
**Fix ya aplicado**: la query usa `COALESCE(INVERSION_TOTAL_USD, 0)`.

### 3. Valores negativos en NR — son normales
`NR_USERS` puede ser negativo en días recientes. Son correcciones retroactivas de atribución.
Se cancelan en el acumulado mensual. **No es un bug**.

### 4. Días sin datos → forward-fill en Python
Si un canal no tiene fila para un día específico en BQ, no hay registro vacío — directamente
no existe la fila. El forward-fill en `processors.py` propaga el último `CUM_NR` conocido.

### 5. Valores POM renombrados en abr-2026
Los valores de `CHANNEL_APERTURA_3` para POM cambiaron:

| Antes | Ahora |
|---|---|
| `POM ACQ` | `ACQUISITION POM` |
| `POM ACT` | absorbido por `ACTIVATION POM` / `WEB POM` / `CTW POM` |
| `POM` | distribuido en sub-canales |
| `POM OTHERS SELLERS` | `POM SELLERS` |

**Fix ya aplicado** en `channels_config.json → pom_adq.bq_mapping.channel`.

### 6. El SQL generado es la query más pesada a las 7am
`PANEL_MONTHLY_DAILY_HISTORICO` es un proyecto compartido con toda Meli.
A las 7am en punto hay pico de jobs → `quotaExceeded`.  
**Fix**: retry automático (3 intentos / 120s) en `processors.bq_query()`.  
**Horario**: el cron corre a las 7:30am CDMX, no a las 7:00am en punto.

---

## Cómo actualizar los canales

**Para agregar un nuevo canal o modificar el mapeo de uno existente:**

1. Editar `config/channels_config.json` → sección `hierarchy_nr` → campo `bq_mapping`
2. Verificar en BQ que los valores de `STRATEGY` y `CHANNEL_APERTURA_3` son correctos
3. Regenerar localmente: `python src/gen_dashboard_v2.py`
4. **Nunca** editar `get_nr_sql()` en `queries.py` directamente — el SQL es el output, no el input

---

## Historial de cambios

| Fecha | Cambio |
|---|---|
| Mar 2026 — V2 | Migración de monolito a arquitectura modular. `get_nr_sql()` se genera desde config. |
| Abr 2026 | Schema BQ: `CHANNEL` → `CHANNEL_APERTURA_3`, `COST_USD` → `INVERSION_TOTAL_USD`. |
| Abr 2026 | Valores POM actualizados (`ACQUISITION POM`, `ACTIVATION POM`, etc.). |
| Abr 2026 | OC ACT añade `ADHOC` como nuevo valor de `CHANNEL_APERTURA_3`. |
| Abr 2026 | L&P añade `LANDINGS` y `AFFILIATES` a los canales mapeados. |
| 2026-04-15 | Documentación creada en `config/queries/nr_mensual.md`. |
