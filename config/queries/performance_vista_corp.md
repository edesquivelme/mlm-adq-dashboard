# Query Fuente: Pestaña `Performance_vista_Corp`

**Última actualización**: 2026-04-15  
**Implementación**: `src/gen_dashboard_v2.py` → `build_perf_corp_data(config, data)`  
**Tipo**: ⚠️ **SIN QUERY BQ PROPIA** — ensamble Python puro que reutiliza dicts de otras queries

---

## El insight fundamental

> `Performance_vista_Corp` **no ejecuta ninguna query nueva en BigQuery**.
> Es una función Python (`build_perf_corp_data`) que **cruza 5 dicts ya calculados**
> por otras queries del pipeline, usando `hierarchy_cost_corp.mappings` en
> `channels_config.json` como puente de traducción entre:
>
> - **Jerarquía Corporativa** (`corp_oc_ucr`, `corp_pom`, `corp_mgm`...) — vista externa/presentaciones
> - **Jerarquía Estándar** (`OC + UCR`, `POM TOTAL`, `MGM TOTAL`...) — vista interna del dashboard
>
> La complejidad no está en el SQL — está en el **mapeo entre dos jerarquías distintas**.

---

## Propósito

Muestra las mismas métricas de Performance (N+R, Inversión, CPA, VPU, ROA) que
`Performance_vista_FM`, pero organizadas según la **estructura corporativa de canales**
(AP1 → AP2 → Touchpoint) en lugar de la jerarquía de negocio estándar del dashboard.

Permite comparar directamente con los reportes de liderazgo de Meli que usan la
nomenclatura corporativa (OC+UCR, POM, OTHERS, NO ATRIBUIDO).

---

## Las 5 fuentes de datos (queries que ya corrieron antes)

La función `build_perf_corp_data()` accede al dict `data{}` que `process_all()` ya llenó.
No hay retries, no hay nueva conexión a BQ. Todo está en memoria.

| Dict en `data{}` | Query que lo genera | Tabla BQ | Qué aporta |
|---|---|---|---|
| `monthly_nr_corp_by_node` | `get_nr_corp_sql()` | `PANEL_MONTHLY_DAILY_HISTORICO` | N+R real por nodo corp (AP1+AP2+TOUCHPOINT) |
| `monthly_inv_total` | `get_costos_sql()` | `PANEL_MONTHLY_COSTOS_CANALES` | Inversión USD real por canal estándar |
| `perf_nr_paid` + `perf_nr_go` | `get_perf_paid_sql()` | `PANEL_MONTHLY_COSTOS_CANALES` | N+R Paid y N+R Gest Others por canal estándar |
| `perf_vpu_prod` | `get_perf_vpu_sql()` | `PANEL_MONTHLY_DAILY_HISTORICO` | SUM(NR × VPU) pre-multiplicado por canal estándar |
| `perf_roa_num` | `get_perf_roa_costos_sql()` + `perf_vpu_prod` | COSTOS (UCR/OC) + DAILY (POM/MGM) | Numerador ROA por canal (fuente mixta) |
| `plan_inv` + `plan_valor` + `plan_nr_corp_by_node` | `load_plan()` + `load_plan_corp()` | Excel `Resumen Plan Acq 2026.xlsx` | Plan de negocio por canal |

---

## El puente de mapeo: `hierarchy_cost_corp.mappings`

Definido en `config/channels_config.json → hierarchy_cost_corp.mappings`.
Cada entrada conecta un nodo corporativo con sus equivalentes en la jerarquía estándar.

```json
{
  "corp_node_id":     "corp_oc_ucr",      ← ID del nodo en la jerarquía corp
  "nr_perf_label":    "OC + UCR",         ← clave en perf_nr_paid, perf_vpu_prod, perf_roa_num
  "cost_inv_label":   "OC + UCR",         ← clave en monthly_inv_total
  "plan_inv_label":   "OC + UCR",         ← clave en plan_inv
  "plan_valor_label": "OC + UCR",         ← clave en plan_valor
  "has_cost": true, "has_vpu": true, "has_roa": true
}
```

**Cómo funciona `build_perf_corp_data()` para cada nodo:**

```python
for mapping in hierarchy_cost_corp.mappings:
    corp_id     = mapping['corp_node_id']       # ej. 'corp_oc_ucr'
    nr_label    = mapping['nr_perf_label']       # ej. 'OC + UCR'
    cost_label  = mapping['cost_inv_label']      # ej. 'OC + UCR'

    for month in all_months:
        actual_nr_total  = monthly_nr_corp_by_node[corp_id][month]   # ← estructura corp
        actual_nr_paid   = perf_nr_paid[nr_label][month]             # ← estructura estándar
        actual_inv_total = monthly_inv_total[cost_label][month]      # ← estructura estándar
        actual_vpu_prod  = perf_vpu_prod[nr_label][month]            # ← estructura estándar
        actual_roa_num   = perf_roa_num[nr_label][month]             # ← estructura estándar (mixta)
        plan_inv         = plan_inv[plan_inv_label][month]            # ← Excel
        plan_valor       = plan_valor[plan_valor_label][month]        # ← Excel
        plan_nr          = plan_nr_corp_by_node[corp_id][month]      # ← Excel corp
```

---

## Tabla completa de mappings (estado actual)

| corp_node_id | nr_perf_label | cost_inv_label | has_cost | has_vpu | has_roa | Nota |
|---|---|---|---|---|---|---|
| `corp_total` | `Total N+R` | `Total Inversión` | ✅ | ✅ | ✅ | Agregado completo |
| `corp_oc_ucr` | `OC + UCR` | `OC + UCR` | ✅ | ✅ | ✅ | Suma de todos los hijos OC |
| `corp_ucr_eg` | `UCR Gest` | `UCR Gest` | ✅ | ✅ | ✅ | UCRANIA E&G = UCR Gest en estándar |
| `corp_oc_recurring` | `OC ACT` | `OC ACT` | ✅ | ✅ | ✅ | ⚠️ COSTOS no separa Recurring de ADHOC |
| `corp_oc_adhoc` | `null` | `null` | ❌ | ❌ | ❌ | ACTIVATION_OTHER_TEAM → INV=0 en COSTOS |
| `corp_pom` | `POM TOTAL` | `POM TOTAL` | ✅ | ✅ | ✅ | |
| `corp_acq_pom` | `POM ADQ` | `POM ADQ` | ✅ | ✅ | ✅ | ACQUISITION POM |
| `corp_act_pom` | `POM ACT` | `POM ACT` | ✅ | ✅ | ✅ | ACTIVATION POM (incluye ACQUISITION+ACTIVATION) |
| `corp_web_pom` | `null` | `null` | ❌ | ❌ | ❌ | Sin tracking en hierarchy_nr |
| `corp_ctw_pom` | `null` | `null` | ❌ | ❌ | ❌ | Sin tracking en hierarchy_nr |
| `corp_others` | `null` | `null` | ❌ | ❌ | ❌ | Grupo heterogéneo sin mapeo limpio |
| `corp_mgm` | `MGM TOTAL` | `MGM TOTAL` | ✅ | ✅ | ✅ | CHANNEL=MGM, STRATEGY='ADQUISITION' en COSTOS |
| `corp_lp` | `L&P TOTAL` | `null` | ❌ | ✅ | ❌ | no_cost=true; VPU de DAILY disponible |
| `corp_ucr_prd` | `UCR PRD` | `null` | ❌ | ✅ | ❌ | no_cost=true; VPU de DAILY disponible |
| `corp_seo` | `null` | `null` | ❌ | ❌ | ❌ | Sin tracking en hierarchy_nr |
| `corp_pom_sellers` | `null` | `null` | ❌ | ❌ | ❌ | Sin tracking en hierarchy_nr |
| `corp_pom_others` | `null` | `null` | ❌ | ❌ | ❌ | Sin tracking en hierarchy_nr |
| `corp_noatrib` | `ORG` | `null` | ❌ | ✅ | ❌ | AP1=ORGANICO; VPU de DAILY disponible |

---

## Métricas por nodo y cómo se calculan

### N+R Total (`actual_nr_total`)
- **Fuente**: `monthly_nr_corp_by_node[corp_node_id][month]`
- **Origen**: `get_nr_corp_sql()` → usa AP1+AP2+TOUCHPOINT de `PANEL_MONTHLY_DAILY_HISTORICO`
- **Diferencia vs. vista FM**: el N+R total puede diferir porque la vista Corp usa la taxonomía
  AP1/AP2 (corporativa) mientras que la vista FM usa STRATEGY+CHANNEL_APERTURA_3 (estándar)

### N+R Paid (`actual_nr_paid`)
- **Fuente**: `perf_nr_paid[nr_perf_label][month]`
- **Origen**: `get_perf_paid_sql()` → `PANEL_MONTHLY_COSTOS_CANALES`
- **Criterio PAID**: `INVERSION_TOTAL_USD > 0`
- **Solo disponible**: UCR Gest, OC ACT, MGM ADQ, POM ADQ/ACT (100% paid por definición)

### N+R Gest Others (`actual_nr_go`)
- **Fuente**: `perf_nr_go[nr_perf_label][month]`
- **Origen**: `get_perf_paid_sql()` → `STRATEGY = 'ACTIVATION_OTHER_TEAM'`
- **Solo aplica**: OC ACT y sus padres

### Inversión Total (`actual_inv_total`)
- **Fuente**: `monthly_inv_total[cost_inv_label][month]`
- **Origen**: `get_costos_sql()` → `PANEL_MONTHLY_COSTOS_CANALES`
- **`null`** para nodos con `cost_inv_label = null` (L&P, UCR PRD, ORG, SEO, etc.)

### VPU / Valor Predicho (`actual_vpu_prod`)
- **Fuente**: `perf_vpu_prod[nr_perf_label][month]`
- **Origen**: `get_perf_vpu_sql()` → `PANEL_MONTHLY_DAILY_HISTORICO`
- **Campo BQ**: `VALUE_MKT_PREDICTION_90D_NR_USERS` (ya pre-multiplicado por NR)
- **Cálculo**: `VPU_avg = SUM(col) / SUM(NR_USERS)` — sin multiplicación adicional
- **Disponible** para todos los nodos con `has_vpu: true` (incluyendo L&P, UCR PRD, ORG)

### ROA Numerador (`actual_roa_num`) — lógica mixta
- **Fuente**: `perf_roa_num[nr_perf_label][month]`
- **Origen**: mixto según canal:

| Canal | Fuente del numerador ROA |
|---|---|
| UCR Gest / OC ACT | `VALUE_PRED` de `PANEL_MONTHLY_COSTOS_CANALES` (filtro `INV > 0`) |
| POM ADQ / POM ACT / MGM ADQ | `VALUE_MKT_PREDICTION_90D_NR_USERS` de `PANEL_MONTHLY_DAILY_HISTORICO` |
| Resto | 0 — sin ROA (`has_roa: false`) |

---

## Las 5 queries BQ subyacentes (textos completos en sus propios .md)

Estas queries ya están documentadas o pendientes de documentar:

### Query 1: `get_nr_corp_sql()` → N+R real por nodo corp

```sql
-- Simplificada para legibilidad — ver nr_corp.md para el SQL completo
WITH base_corp AS (
  SELECT
    FORMAT_DATE('%Y%m', FECHA_DIARIA) AS FECHA_MES_CORP,
    CHANNEL_APERTURA_1 AS ap1_corp,
    CHANNEL_APERTURA_2 AS ap2_corp,
    CHANNEL_APERTURA_3 AS ap3_corp,
    TOUCHPOINT         AS touchpoint_corp,
    COALESCE(NR_USERS, 0) AS nr_corp
  FROM `meli-bi-data.SBOX_MKTCORPMP.PANEL_MONTHLY_DAILY_HISTORICO`
  WHERE SIT_SITE_ID = 'MLM' AND FECHA_DIARIA >= DATE '2025-01-01'
),
keyed_corp AS (
  SELECT FECHA_MES_CORP,
    CASE
      WHEN ap1_corp = 'OC' AND ap2_corp = 'UCRANIA E&G' AND touchpoint_corp IN ('EMAIL','SMS') THEN 'OC|UCR_EG|EMAIL'
      WHEN ap1_corp = 'OC' AND ap2_corp = 'UCRANIA E&G' AND touchpoint_corp = 'PANDORA'        THEN 'OC|UCR_EG|PANDORA'
      -- ... 22 ramas en total ...
      ELSE 'NOATRIB|ORGANICO|TOTAL'
    END AS corp_key,
    nr_corp
  FROM base_corp
)
SELECT FECHA_MES_CORP AS fecha_mes_corp, corp_key,
       SUM(nr_corp) AS nr_total_corp
FROM keyed_corp
GROUP BY fecha_mes_corp, corp_key
ORDER BY fecha_mes_corp, corp_key
```

### Query 2: `get_costos_sql()` → Inversión por canal estándar
Ver `config/queries/performance_fm.md` (pendiente de crear) para el SQL completo.
Fuente: `PANEL_MONTHLY_COSTOS_CANALES`. CASE WHEN dinámico desde `hierarchy_cost → cost_mapping`.

### Query 3: `get_perf_paid_sql()` → N+R Paid y Gest Others
Ver `config/queries/performance_fm.md`. Fuente: `PANEL_MONTHLY_COSTOS_CANALES`.
Criterio PAID: `INVERSION_TOTAL_USD > 0`. Criterio Gest Others: `STRATEGY = 'ACTIVATION_OTHER_TEAM'`.

### Query 4: `get_perf_vpu_sql()` → VPU / Valor Predictivo
Ver `config/queries/performance_fm.md`. Fuente: `PANEL_MONTHLY_DAILY_HISTORICO`.
Campo: `VALUE_MKT_PREDICTION_90D_NR_USERS` (pre-multiplicado — no multiplicar de nuevo).

### Query 5: `get_perf_roa_costos_sql()` → ROA numerador UCR/OC
```sql
WITH base AS (
  SELECT
    MONTH_ID,
    CASE
      WHEN CHANNEL = 'OWN CHANNELS MKT' AND STRATEGY = 'UCRANIA'    THEN 'UCR Gest'
      WHEN CHANNEL = 'OWN CHANNELS MKT' AND STRATEGY = 'ACTIVATION' THEN 'OC ACT'
    END AS PERF_CANAL,
    COALESCE(VALUE_PRED, 0) AS VALUE_PRED
  FROM `meli-bi-data.SBOX_MKTCORPMP.PANEL_MONTHLY_COSTOS_CANALES`
  WHERE SIT_SITE_ID = 'MLM'
    AND MONTH_ID >= '202501'
    AND COALESCE(INVERSION_TOTAL_USD, 0) > 0
)
SELECT MONTH_ID, PERF_CANAL, SUM(VALUE_PRED) AS ROA_VALUE_PRED
FROM base
WHERE PERF_CANAL IS NOT NULL
GROUP BY MONTH_ID, PERF_CANAL
```

---

## Plan de negocio (fuente Excel, no BQ)

Dos fuentes de plan independientes:

| Función | Archivo | Retorna | Consumido en |
|---|---|---|---|
| `load_plan()` | `data/Resumen Plan Acq 2026.xlsx` | `plan_inv`, `plan_valor` (por `hierarchy_nr` label) | `plan_inv_for_node`, `plan_valor_for_node` |
| `load_plan_corp()` | `data/Resumen Plan Acq 2026.xlsx` | `plan_nr_corp_by_node` (por `corp_node_id`) | `plan_nr_for_node` |

> **Separación crítica**: `load_plan()` usa `hierarchy_nr` labels como clave.
> `load_plan_corp()` usa `corp_node_id` como clave (de `hierarchy_PLAN_Corp.mappings`).
> **Nunca mezclar** — son independientes y se acceden por claves distintas.

---

## Comparación con Performance_vista_FM

| Aspecto | Performance_vista_FM | Performance_vista_Corp |
|---|---|---|
| Jerarquía | `hierarchy_nr` (negocio estándar) | `hierarchy_nr_corp_detail` (corporativa) |
| N+R Total | `monthly_nr[hier_nr_label]` | `monthly_nr_corp_by_node[corp_node_id]` |
| N+R Paid | mismo | mismo (via `nr_perf_label`) |
| Inversión | mismo | mismo (via `cost_inv_label`) |
| VPU/ROA | mismo | mismo (via `nr_perf_label`) |
| Plan N+R | `plan_nr[hier_nr_label]` | `plan_nr_corp_by_node[corp_node_id]` |
| Queries BQ | 4–5 queries | 0 queries adicionales (reutiliza todo) |

---

## Gotchas críticos

### 1. `corp_oc_recurring` ≠ exactamente OWN CHANNELS RECURRING
`corp_oc_recurring` mapea a `OC ACT` en la jerarquía estándar.
Pero `PANEL_MONTHLY_COSTOS_CANALES` no distingue entre Recurring y ADHOC —
ambos son `STRATEGY = 'ACTIVATION'`. La inversión de `corp_oc_recurring` incluye
también la de ADHOC. Es la mejor aproximación disponible.

### 2. `corp_oc_adhoc` no tiene datos de performance
`ACTIVATION_OTHER_TEAM` en COSTOS_CANALES siempre tiene `INVERSION_TOTAL_USD = 0`.
No hay inversión rastreable → `has_cost: false`, `has_vpu: false`, `has_roa: false`.
El N+R total sí está disponible desde `get_nr_corp_sql()`.

### 3. N+R Total puede diferir entre vista FM y vista Corp para el mismo canal
- Vista FM: usa `STRATEGY + CHANNEL_APERTURA_3` para clasificar → captura exactamente
  los canales en `bq_mapping`
- Vista Corp: usa `AP1 + AP2 + TOUCHPOINT` → puede capturar combinaciones distintas

La diferencia más notable: UCR PRD en vista FM usa `STRATEGY=ACQUISITION, CHANNEL=OWN CHANNELS PRD`
pero en vista Corp es `AP1=OTHERS, AP2=UCRANIA PRD` — canales diferentes en la taxonomía.

### 4. ROA numerador: la fuente varía por canal
- UCR Gest y OC ACT: `VALUE_PRED` de `COSTOS_CANALES` (solo filas con `INV > 0`)
- POM, MGM: `perf_vpu_prod` de `DAILY_HISTORICO` (todos los usuarios, no solo paid)
- Esto replica la lógica del Excel `MLM_Costos_Performance.xlsx` (ver History.md §13)

### 5. `MONTH_ID` en `PANEL_MONTHLY_COSTOS_CANALES` es STRING `'YYYYMM'`
A diferencia de otras tablas, `COSTOS_CANALES.MONTH_ID` es `'202501'`, `'202502'`, etc.
No es tipo DATE. Por eso el filtro usa `AND MONTH_ID >= '202501'` (comparación de strings).

### 6. `STRATEGY = 'ADQUISITION'` (typo histórico) para MGM en COSTOS_CANALES
El valor real en la tabla es `'ADQUISITION'` (sin la 'C' de ACQUISITION).
La query `get_perf_paid_sql()` lo maneja correctamente pero es un gotcha para
cualquier nueva query que toque MGM en COSTOS_CANALES.

---

## Cómo agregar o modificar un nodo en Performance_vista_Corp

1. Identificar el `corp_node_id` en `hierarchy_nr_corp_detail`
2. Determinar los labels equivalentes en `hierarchy_nr` (`nr_perf_label`) y `hierarchy_cost` (`cost_inv_label`)
3. Agregar el mapping en `config/channels_config.json → hierarchy_cost_corp.mappings`
4. Si el nodo no tiene equivalente en la jerarquía estándar → `null` en los labels correspondientes
5. Regenerar: `python src/gen_dashboard_v2.py`
6. **Nunca** crear una nueva query BQ para este tab — si los datos no existen en los dicts
   actuales, la solución correcta es agregar la query en `process_all()` y exponer el dict

---

## Historial de cambios

| Fecha | Cambio |
|---|---|
| Abr 2026 | Implementación inicial. `build_perf_corp_data()` como función sin queries BQ propias. |
| Abr 2026 | `hierarchy_cost_corp.mappings` con 18 nodos definidos en `channels_config.json`. |
| Abr 2026 | ROA numerador con lógica mixta: COSTOS para UCR/OC, DAILY para POM/MGM. |
| 2026-04-15 | Documentación creada en `config/queries/performance_vista_corp.md`. |
