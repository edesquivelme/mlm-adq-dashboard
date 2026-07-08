# Reporting Tab — Metodología de Clasificación de Canales
**Creado**: 2026-05-06 | **Fuente código**: `src/builders.py → build_reporting_tab_html()`

---

## Mapeo Corp Node IDs → Segmentos del Reporting

### SECCIÓN 1 & 2: N+R in App por segmento Corp

| Segmento Chart | Corp Sub-canal(es) | Node IDs |
|---|---|---|
| **OC + UCR** | UCRANIA E&G + OWN CHANNELS RECURRING + OWN CHANNELS ADHOC | `corp_ucr_eg_*` + `corp_oc_rec_*` + `corp_oc_adhoc` |
| **POM** | ACQUISITION POM + ACTIVATION POM + WEB POM + CTW POM | `corp_acq_pom`, `corp_act_pom`, `corp_web_pom`, `corp_ctw_pom` |
| **Others** | MGM + L&P + UCR PRD + SEO + POM SELLERS + POM OTHERS | `corp_mgm`, `corp_lp_*`, `corp_ucr_prd`, `corp_seo`, `corp_pom_sellers`, `corp_pom_others` |
| **No Atribuído** | NO ATRIBUIDO | `corp_noatrib` |

### SECCIÓN 2: N+R por Canal (gráfica derecha)

| Segmento Chart | Fuente | Node IDs |
|---|---|---|
| **Own Channels (OC+UCR)** | Mismo que OC + UCR arriba | `corp_ucr_eg_*` + `corp_oc_rec_*` + `corp_oc_adhoc` |
| **POM** | Mismo que POM arriba | `corp_acq_pom`, `corp_act_pom`, `corp_web_pom`, `corp_ctw_pom` |
| **MGM** | Solo MGM (sub-canal de OTHERS Corp) | `corp_mgm` |
| **L&P** | Solo L&P (sub-canal de OTHERS Corp) | `corp_lp_brandformance`, `corp_lp_landings`, `corp_lp_partnerships`, `corp_lp_others`, `corp_lp_gtm`, `corp_lp_affiliates` |
| **No Atribuído / Org** | NO ATRIBUIDO | `corp_noatrib` |

### SECCIÓN 3: Evolución N+R por Estrategia OC+UCR

| Segmento Chart | Definición | Node IDs |
|---|---|---|
| **Ucrania** | UCRANIA E&G (todos sus medios: EMAIL, PANDORA, PUSH, REAL ESTATES, WPP) | `corp_ucr_eg_email`, `corp_ucr_eg_pandora`, `corp_ucr_eg_push`, `corp_ucr_eg_real_estates`, `corp_ucr_eg_wpp` |
| **Activation Rec** | OWN CHANNELS RECURRING **sin Journey** (EMAIL + PANDORA + PUSH + WPP) | `corp_oc_rec_email`, `corp_oc_rec_pandora`, `corp_oc_rec_push`, `corp_oc_rec_wpp` |
| **Ad Hoc** | OWN CHANNELS ADHOC (total) | `corp_oc_adhoc` |
| **Resto Rec (JNY)** | Medio JOURNEY dentro de OWN CHANNELS RECURRING | `corp_oc_rec_journey` |

**Nota**: Activation Rec + Resto Rec (JNY) = OWN CHANNELS RECURRING completo.

---

## New vs Recovered (Sección 2 izquierda)

**Fuente**: `BT_MP_USER_ENGAGEMENT_INAPP` (misma tabla que el total N+R del dashboard)
**Query**: `get_new_rec_monthly_sql()` en `src/queries.py`
**Columnas**: `NEW_USERS_INAPP` (New) + `RECOVERED_USERS_INAPP` (Recovered) por mes
**Cutoff**: D-1 (consistente con resto del dashboard)

---

## Valor Predictivo (Sección 1 derecha)

**Metodología**: Valor por segmento = NR_segmento × VPU_promedio_ponderado

```
VPU_promedio_ponderado(mes) = Σ(VPU_fm_label × NR_fm_label) / Σ(NR_fm_label)
```

Donde `perf_vpu_prod` contiene VPU por FM label (UCR Gest, OC ACT, POM ADQ, etc.).

**Limitación**: El VPU real por segmento Corp no está disponible separado en las tablas actuales. Se usa el VPU promedio ponderado de todos los canales FM. Para VPU exacto por Corp segment se requeriría un desglose adicional en BQ.

---

## Línea de Plan en Charts

| Chart | Plan usado | Fuente |
|---|---|---|
| N+R in App | Plan OC+UCR = Plan UCR Gest + Plan OC ACT | `plan_nr['UCR Gest'][month] + plan_nr['OC ACT'][month]` |
| Valor Predictivo | Plan Valor OC+UCR | `plan_valor['UCR Gest'][month] + plan_valor['OC ACT'][month]` |
| OC Estrategia | Plan OC+UCR | Mismo que arriba |

---

## Colores

| Segmento | Color HEX |
|---|---|
| OC + UCR / Ucrania | `#F5D000` (amarillo) |
| POM | `#1FB8D4` (teal) |
| Others | `#7A7D82` (gris) |
| No Atribuído | `#C8CDD8` (gris claro) |
| Plan (línea) | `#C00000` (rojo) |
| CPA (línea) | `#FF6B35` (naranja) |
| Activation Rec | `#5899D1` (azul) |
| Ad Hoc | `#1a2744` (azul navy) |
| Resto Rec Journey | `#2F9E8F` (verde teal) |
| New | `#1a2744` (navy) |
| Recovered | `#5899D1` (azul) |
| MGM | `#9C6B3C` (café) |
| L&P | `#8A4D99` (púrpura) |
