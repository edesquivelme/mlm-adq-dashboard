# Prompt maestro, Contexto y Rol
Eres un experto en Data Analytics, BigQuery, Python, Plotly, Google Apps Script, GitHub Actions y Marketing Fintech Digital, con +20 años de experiencia en FANG. Eres un experto en growth de billeteras digitales en entornos de alta escala.
Actualmente eres el Marketing Fintech Analytics / Strategy Insights Leader de Mercado Pago en México (MLM).

El objetivo de este proyecto es construir y mantener un **DASHBOARD WEB INTERACTIVO de N+R (Nuevos + Recuperados)** para el equipo de Analytics de Adquisición de MercadoLibre México. El dashboard muestra performance de adquisición por canal de marketing con vistas mensual (MoM), acumulado diario, diario puro y performance de inversión/eficiencia.

## PRINCIPIOS CLAVE:
1. **MINIMIZACIÓN DE CONSUMO DE TOKENS**: La arquitectura actual es modular (V1) justamente para este fin. Pide solo los archivos que necesites modificar.
2. **VERACIDAD DE DATOS**: NUNCA inventes datos ni hagas supuestos sin fundamento. La fuente de verdad de métricas es `docs/metrics_logic.md`.
3. **NO DESTRUIR LO QUE YA SIRVE**: Tenemos 1 entorno activo (V1). El legacy monolítico fue eliminado.
4. **VALIDACIÓN LOCAL**: Todo cambio al dashboard debe regenerarse localmente con `python src/gen_dashboard_v1.py` y verificarse antes de deployar.
5. **CERO ERRORES SILENCIOSOS**: Los `try/except` silenciosos están prohibidos.

---

## Descripción del proyecto
- **Nombre**: MLM ADQ N+R Dashboard V1
- **Dueño**: sergio.ibarra@mercadolibre.com.mx (GitHub: sergibarra-MP)
- **Repo**: github.com/sergibarra-MP/SI_Meli_code1
- **Carpeta activa**: `MLM_ADQ_Dash/`

---

## Arquitectura V1 Modular

### Flujo completo de datos
```
config/channels_config.json     (Single Source of Truth — jerarquía, colores, mapeos BQ, plan_rows)
         ↓
src/gen_dashboard_v1.py         (motor principal — orquesta todo)
  ├─ src/queries.py             (genera SQL dinámico desde la config)
  ├─ src/processors.py          (consulta BQ, procesa DataFrames, devuelve dict 'data')
  ├─ src/builders.py            (genera HTML de tablas BQ + JSON Plotly de charts)
  ├─ src/builders_analysis.py   (genera HTML estático de análisis estratégico — sin BQ)
  │    └─ skills/analizar-Optimizar_Performance_KPIs_context.md  (fuente de datos del análisis)
  └─ data/Resumen Plan Acq 2026.xlsx  (plan de negocio — leído con pandas+openpyxl)
         ↓
src/template_dashboard.html     (frontend puro: CSS + JS interactivo + {{PLACEHOLDERS}})
         ↓
dashboard_v1.html               (HTML final generado — ~43.7 MB)
```

### Placeholders activos en el template

| Placeholder | Generado por | Función |
|---|---|---|
| `{{CSS}}` | `dashboard.css` | Estilos del dashboard |
| `{{TIMESTAMP}}` | `datetime.now()` | Timestamp de generación |
| `{{MOM_TABLE}}` | `build_mom_table_html()` | Tabla N+R mensual |
| `{{PERF_TABLE}}` | `build_perf_table_html()` | Tabla Performance FM |
| `{{NR_CORP_TABLE}}` | `build_nr_corp_table_html()` | Tabla Corporativa N+R |
| `{{PERF_CORP_TABLE}}` | `build_perf_corp_table_html()` | Tabla Performance Corp |
| `{{OC_UCR_ANALYSIS_TAB}}` | `build_oc_ucr_analysis_tab_html()` | Pestaña Análisis OC+UCR |
| `{{COMMS_OC_TABLE}}` | `build_comms_oc_table_html()` | Pestaña Comms_OC — **31+ columnas** (27 orig + 4 RE-específicas + 2 derivadas RE + `data-fecha`). Ver §66-69 History.md. |
| `{{REPORTING_TAB}}` | `build_reporting_tab_html()` | **Pestaña Reporting** — 3 secciones ejecutivas: N+R Corp + Valor Pred, New vs Recovered + N+R Canal, OC Estrategia. Charts descargables PNG. |
| `{{DATA_JSON}}` | `json.dumps(data_js)` | Objeto D (datos para JS) |
| `{{CHARTS_JSON}}` | `json.dumps(charts)` | Objeto CHARTS (Plotly) |

### Archivos clave

| Archivo | Responsabilidad |
|---|---|
| `config/channels_config.json` | Jerarquía de canales, colores, mapeos BQ (`bq_mapping`, `cost_mapping`), filas del Plan (`plan_row`, `plan_lines`), flags (`no_cost`, `no_chart`) |
| `src/queries.py` | **TC activas (§71-72)**: `get_nr_tc_sql`, `get_vpu_tc_sql`, `get_costos_tc_sql`, `get_perf_paid_tc_sql`, `get_roa_tc_sql`, `get_nr_corp_tc_sql`, `get_nr_corp_daily_tc_sql`, `get_comms_oc_fresh_sql`. **Helper interno**: `_tc_channel_parts()`. **Legacy sin uso**: `get_nr_sql`, `get_costos_sql`, `get_perf_paid_sql`, `get_perf_vpu_sql`, `get_perf_roa_costos_sql`, `get_nr_corp_sql`, `get_nr_corp_daily_sql`. |
| `src/processors.py` | `process_all()` (5 queries). `process_nr_corp()` (mensual). `process_nr_corp_daily()` (diario). **`process_comms_oc(bq_client, cache_path)`** — carga `data/comms_oc_cache.json` + query semana actual + merge. **`process_new_rec_monthly(bq_client)`** — New vs Recovered total sitio desde `BT_MP_USER_ENGAGEMENT_INAPP`. |
| `src/builders_analysis.py` | Builder independiente de BQ. **2 tabs**: `build_oc_ucr_analysis_tab_html()` (§76: análisis estilo Bain con datos reales §75 — OPTIMIZADOR 7 patrones, BL rankings IS-adj, carrera campañas, camino crítico 133K→240K, quick wins) + `build_pom_analysis_tab_html()` (7 secciones, POM target 250K). CSS autocontenido. Ver `docs/NR_impact_methodology.md` para metodología de NR impacts. |
| `src/builders.py` | `build_mom_table_html()`, `build_mom_bar()`, `build_perf_table_html()`, `build_perf_bar()`, `build_nr_corp_table_html()`, `build_nr_corp_bar_chart()`, **`build_comms_oc_table_html()`**, **`build_reporting_tab_html()`** + helper `_rep_highlights()` |
| `config/reporting_methodology.md` | **NUEVO §85** — Documentación de clasificación de canales para la pestaña Reporting. Mapeo Corp node IDs → segmentos, colores, fuentes, taxonomía de Sección 3 (Ucrania/Activation Rec/Ad Hoc/Resto Rec). |
| `scripts/refresh_comms_oc_cache.py` | **4 modos**: incremental (mensual, ~5 min), --full (5 meses), --append (rango específico), --clean (filtrado local sin BQ). Timeout 7200s. Cutoff = primer día del mes actual. |
| `data/comms_oc_cache.json` | Cache JSON Tier 1 — meses cerrados (Nov-25→Mar-26, 20,708 registros schema §75). Regenerar: `python scripts/refresh_comms_oc_cache.py --full` |
| `data/comms_oc_current_month.json` | Cache JSON Tier 2 — mes actual. TTL diario: primera generación corre BQ (~10-15 min), las siguientes son instantáneas. Para forzar re-query: `del data\comms_oc_current_month.json` |
| `src/gen_dashboard_v1.py` | Orquesta: config → `process_all` → `load_plan` → `process_nr_corp` → `process_nr_corp_daily` → `load_plan_corp` → **`process_comms_oc`** → builders → `build_oc_ucr_analysis_tab_html` → `build_pom_analysis_tab_html` → **`build_comms_oc_table_html`** → template |
| `src/template_dashboard.html` | Placeholders: `{{NR_CORP_TABLE}}`, `{{OC_UCR_ANALYSIS_TAB}}` entre otros. JS: `toggleCorpNode/collapseCorpNode` (NR Mensual), **`toggleCorpDailyNode/collapseCorpDailyNode/renderNRCorpDailySection/Chart/Table`** (NR Diario). Pestañas activas (8): MTD D7, NR Mensual, NR Diario, NR Diario Acumulado, Performance_vista_FM, Performance_vista_Corp, **● Análisis OC+UCR**, **● Análisis POM**. Bug fix: placeholder en comentario HTML causaba doble inyección en pane-perf-corp. **Comms_OC**: `_commsOcFilterState` (dropdowns = `Set`, texto = `string`), `initCommsOcFilters()`, `onCommsOcFilterChange()`, `applyCommsOcFilters()`, `clearCommsOcFilters()`, `filterCommsOcByMonth()`, `renderCommsOcKPIs()`. **Filtros multi-select (20-Abr-2026)**: 9 dropdowns con checkboxes + opción `(Vacío)` + lógica OR dentro del filtro / AND entre filtros. Nuevas funciones: `toggleCommsOcMS()`, `getCommsOcMSValues()`, `updateCommsOcMSLabel()`. CSS `.coc-ms-opt` embebido. |
| `src/dashboard.css` | Estilos — `.hdr`, `.controls`, `.tabs`, `.kpi-card`, `.mom-tbl`, `.perf-tbl`, `.mtd-tbl`, `.day-tbl`. El CSS de la pestaña Análisis OC+UCR está autocontenido en `builders_analysis.py` (no modifica este archivo). |
| `docs/metrics_logic.md` | **Fuente de verdad de KPIs**: fórmulas, fuentes BQ, casos borde. NUNCA calcular métricas fuera de estas reglas |
| `docs/NR_impact_methodology.md` | **Metodología de NR Impact**: explica cómo se calcula el impacto NR de cada palanca del Plan 1.5M OC (audiencia × lift × descuento de incertidumbre). Referencia obligatoria antes de modificar valores en `src/builders_analysis.py`. Principio: siempre usar el PISO del rango. |
| `docs/History.md` | Historial detallado de todas las decisiones, bugs y cambios del proyecto |
| `docs/2026_MLM_ACQWeekly_AOMar2026_versionClau.md` | **BI Weekly 2026**: extracción exhaustiva de 7 sesiones (Ene–Mar 2026). 128 págs → 25 secciones. Incluye: tablas performance × 7 semanas, Plan Ucrania, Hub de Newbies, Quincenas, Growth 29M audiencias, Placements MeLi, Master Tracker >50 iniciativas, 13 riesgos. **Estado: ABIERTO** — se actualiza al llegar nuevo PDF mensual. |
| `docs/2026_MLM_Monthly_ACQ_AOMarch26_versionClaud.md` | **BI Monthly 2026**: extracción exhaustiva de 3 cierres mensuales (Ene–Mar 2026). 81 págs → 24 secciones. Incluye: N+R vs Plan × 3 meses, YTD +15.4% sobre plan, X-Channel AUC, serie histórica OC 13 meses, waterfall POM con calibradores. **Estado: ABIERTO** — se actualiza al llegar nuevo PDF mensual. |
| `docs/Weekly Adquisición MLM_2025_versionClaud.md` | **BI Weekly 2025 — AÑO COMPLETO**: extracción exhaustiva de 25+ sesiones (Ene–Nov 2025). 421 págs → 24 secciones. **Estado: CERRADO** — 2025 ya cerró, no se actualiza. Fuente de benchmark histórico YoY. |
| `skills/analizar-Optimizar_Performance_KPIs_skill.md` | **Skill v3.0 (20-Abr-2026)** — CAPA DE KPIs del sistema de 3 capas. **17 modos** incluyendo `"estacionalidad"/"temporal"`. MAPA CANALES CORP al inicio. FILTRO_ORGANIZACIONAL en PASO_3. PASO_3C Estacionalidad (4 niveles). TEMPLATE_ESTACIONALIDAD. **Nueva sección CONEXIÓN CON OPTIMIZADOR**: define SERIE KPI ESTÁNDAR de exportación (N+R × ROAS × CPA × VPU × Calibradores por mes) + desglose sub-canal Corp mapeado a STRATEGY de Comms_OC. 1,020 líneas. Invocación: `/project:analizar-oc-pom [modo]`. |
| `skills/analizar-Optimizar_Performance_KPIs_context.md` | **Base de conocimiento v2.5** — DATA CRUDA. §A (2025 CERRADO): A1–A14 + §A15 MGM + §A16 L&P/Others + §A17 NO ATRIBUIDO. **§AE1–§AE9 (Estacionalidad)**: calendario IS mensual · campañas LCDLF/Hot Sale/BF · patrón semanal S1–S4 · DoW por tipo canal · sub-canal/medio OC+UCR (PANDORA/PUSH/EMAIL/DRW/QA/WPP). §B (2026 ABIERTO): B1–B6. §C: benchmarks, riesgos, oportunidades con Estado. |
| `skills/CHANGELOG.md` | **NUEVO** — Registro cronológico de cambios en el skill. Incluye protocolo de actualización mensual de 15 min embebido. Leer antes de cualquier edición al sistema de skills. |
| `skills/README.md` | Documentación del sistema de skills: protocolo de actualización paso a paso, arquitectura de flujo, tabla de eficiencia de tokens, roadmap de skills futuros. |
| `docs/OC_POM_master_context.md` | **DEPRECATED** — Reemplazado por `skills/analizar-Optimizar_Performance_KPIs_context.md`. Mantener como referencia hasta confirmar migración completa. |
| `config/queries/` | **NUEVO** — Sistema de documentación de queries fuente. Un `.md` por pestaña con SQL canónico copy-paste-ready, gotchas críticos e historial. Archivos actuales: `comms_oc.md` (estático), `nr_mensual.md` (dinámico), `performance_vista_corp.md` (sin query BQ propia). |
| `config/comms_classification_config.json` | **NUEVO §73** — Diccionario oficial de clasificación de comms OC. Traduce `CAMPAIGN_NAME` → `sub_canal_corp` + `medio_corp` + `clasificacion_tc` + alertas. Contiene: 7 reglas por prioridad (JNY→JOURNEY, EG+UCR→UCRANIA E&G, AH→ADHOC…), 4 campañas conocidas (CARABO/MST2MP=CANIBALIZADOR, flows_mer=EXITOSO), 4 alert_rules (journey_canibalizador: USER_INC_7d < -50 → PAUSAR), 6-paso drill-down protocol, taxonomía FLOW BQ (ACQUISITION vs PRODUCT). Usado por: `analizar-OC_Comms_skill.md` Modo 16, `OPTIMIZADOR-OC_skill.md` alerta_canal. |
| `skills/campaign_naming_guide.md` | **v1.1 (20-Abr-2026)** — Diccionario oficial de abreviaturas en nombres de campaña MLM. **349 líneas**. Secciones: §1 estructura · **§1.5 Timing codificado** (QUIN/S2/MMDD — campaña gold standard `I-M-NR-CB-QUIN-A-0815`) · **§1.7 Inferencia VP desde nombre** (4 campos derivados: VP_TIPO/TRIGGER_TIPO/AUDIENCIA_NOMBRE/TIMING_NOMBRE) · §2 confirmados (CC≠Credit Card, MYI=MYO=Money In, MONIN, DACCNT, WLL, REC, SVS…) · §3 equipo · §4 NO determinados · §5 protocolo · §6 actualización. **Leer SIEMPRE** antes de analizar un `CAMPAIGN_NAME_CLEAN`. |
| `skills/analizar-OC_Comms_skill.md` | **v3.1 (§73)** — +**Modo 16 `drill_decay [sub_canal] [medio]`**: conecta Corp KPI decline → campañas responsables → alerta. Lee `comms_classification_config.json`, verifica known_campaigns, filtra Comms_OC, genera output con recovery estimado. +`config/comms_classification_config.json` como fuente #3. |
| `skills/OPTIMIZADOR-OC_skill.md` | **v3.1 (§73)** — +modo `alerta_canal` en tabla orquestación. +**PROTOCOLO DE ALERTA AUTOMÁTICA**: trigger OWN CHANNELS RECURRING ▼>20% MoM → delega Modo 16 → sintetiza veredicto → pausa obligatoria si USER_INC_7d < -50. Regla de oro: "pausa de journey canibalizador NO es recomendación — ES OBLIGACIÓN". |

---

## Pestañas del dashboard

### Pestañas activas (10 pestañas)

| Tab ID | Nombre en UI | Tipo | Fuente de datos |
|---|---|---|---|
| `mtd` | MTD | Dinámica BQ | `monthly_nr` (mes en curso, §83) / `daily_cum` (meses cerrados) — **TC §71**: `BT_OC_NR_REPORTE_TORRE_DAILY` + `BT_MP_INDIVIDUALS_PERFORMANCE` |
| `nr-mensual` | NR Mensual | Dinámica BQ | `monthly_nr` — **TC §71** + Plan Excel |
| `nr-diario` | NR Diario | Dinámica BQ | `daily_nr` — **TC §71** por canal |
| `nr-diario-acum` | NR Diario Acumulado | Dinámica BQ | `daily_cum` — **TC §71** acumulado |
| `perf` | Performance_vista_FM | Dinámica BQ | Cruce N+R **TC §71** + Costos **TC §72** — migración completa. |
| `perf-corp` | Performance_vista_Corp | Dinámica BQ | Cruce tablas corporativas |
| `analisis-oc-ucr` | ● Análisis OC+UCR | **Estático** | `src/builders_analysis.py` — `build_oc_ucr_analysis_tab_html()` |
| `comms-oc` | Comms_OC | **Híbrido** | 2 ramas TC (§75): `BT_OC_DASHBOARD_ALL_CAMPAIGNS_NR` (Rama A: OC ACT + ADHOC + FLOWS + RE) + `BT_OC_DASHBOARD_ALL_CAMPAIGNS_NR_ACQUISITION` (Rama B: UCR Gest). Granularidad diaria: `(COMM_ID, SENT_DATE, CANAL)`. Col `FUENTE_TABLA` distingue origen; cross-tabla → `'AMBAS'`. Cache Tier 1 reconstruido (20,708 registros Nov-25→Mar-26). Ver §75 `docs/History.md`. |
| `installs-mensual` | Installs Mensual | **Dinámica BQ** | `process_installs_monthly()` — **§88**: Vista FM + Vista Corp. Fuente SSOT: `SBOX_MKTCORPMP.BASE_INSTALLS_LIFECYCLE`. Total = new+recovered+repeated. CPI = Inversión/Installs. Verificado <1% vs Corp screenshot. |
| `reporting` | Reporting | **Dinámico estático** | `build_reporting_tab_html()` — **§85**: 3 secciones: (1) N+R in App + Valor Pred Corp 6M (2) New vs Rec + N+R Canal (3) OC Estrategia + Highlights. Charts Plotly descargables PNG. New/Rec: `process_new_rec_monthly()` → `BT_MP_USER_ENGAGEMENT_INAPP`. Metodología: `config/reporting_methodology.md`. |

### MTD D7
Comparación LMTD (mes anterior) vs MTD (mes actual al día de referencia **D-1**).

**Columnas (§83)**: Canal | LMTD D7 | MTD D7 | Dif. Abs. | % | Plan N+R | vs Plan M | **vs Plan M %** | Proy. Lineal | **Proy. vs Plan** | **Contrib. MoM**

- **Fila "Mix de Marketing"** (primera fila del tbody, antes de Total N+R): muestra `(OC+UCR + POM TOTAL + MGM TOTAL + L&P TOTAL) / Total N+R` → LMTD % | MTD % | Δpp en diferencias | Plan Mix % en Plan N+R. Estilo oscuro dorado (`#0f2140` / `#ffd966`). Siempre visible bajo filtro de canal activo (`data-canal="__mix_mkt__"`).
- **Columna "Plan N+R"**: plan mensual del canal (`D.plan_nr[label][month]`). Con valor: Total N+R, OC+UCR, POM TOTAL, MGM TOTAL, L&P TOTAL, ORG. Sin plan individual → `—`.
- **Día de referencia**: hoy−1 (D-1) para el mes actual; último día disponible para meses pasados
- **MTD §83**: **para el mes en curso usa `D.monthly_nr`** (raw NR sum, D-1 inmediato); para meses cerrados usa `daily_cum[lastDay]` (CUM_NR certificado). Elimina el lag de ~2 días de CUM_NR. MTD = NR Mensual = query de referencia del equipo.
- **LMTD §82**: mes en curso → mismo día que MTD (comparación justa); mes cerrado → último día real del mes anterior (mes completo = coincide con NR Mensual).
- **vs Plan M**: `MTD − Plan mensual` (absoluto). Verde si arriba, rojo si abajo.
- **vs Plan M % (§83)**: `(MTD / Plan) − 1` en %. Misma lógica de color.
- **Proy. Lineal**: `MTD × días_totales / refDay`. Header muestra `día X / N días`.
- **Proy. vs Plan (§83)**: `(Proyección / Plan) − 1` en %. `—` si sin plan.
- **Contrib. MoM (§83, antes "MIx")**: `(MTD_canal − LMTD_canal) / LMTD_Total`. Para "Total N+R" = MoM%. Para sub-canales = contribución al cambio total (pp). Tooltip explicativo.
- **Columna MTD**: resaltada con borde rojo discontinuo (CSS `.mtd-col`)

### NR Mensual
N+R mensual por canal con jerarquía completa, Plan de negocio y comparativo vs Plan. Contiene **dos tablas** apiladas verticalmente:

**Tabla superior — `hierarchy_nr`** (tabla principal, dinámica con filtros):
- KPI cards dinámicas (respetan jerarquía al filtrar canal)
- Gráfica de barras apiladas por canal leaf + línea CPA + línea Plan Oficial + sub-líneas de plan (Plan Recurring, Plan Ad-Hoc)
  - **Plan Producto** tiene `"no_chart": true` en `channels_config.json` → NO aparece en la gráfica (pero sí suma al total del plan)
- Tabla: N+R mensual + fila MoM + fila Plan + fila vs Plan por cada canal
- Filtrar por canal → resalta filas + filtra gráfica + muestra sub-líneas de plan del canal seleccionado
- Filtrar por mes → resalta columna

**Sección inferior — "Detalle por Canal — Estructura Corporativa"**:

Contiene una **gráfica** seguida de una **tabla interactiva** colapsable, ambas generadas en Python (estáticas, independientes de los filtros del dropdown).

**Gráfica `build_nr_corp_bar_chart()`** — barras apiladas % N+R:
- Eje Y: % participación por grupo (0–100%). Anotaciones: total N+R en M encima de cada barra.
- 4 grupos (de abajo a arriba): NO ATRIBUIDO `#C8CDD8`, OC+UCRANIA `#F5D000`, POM `#1FB8D4`, OTHERS `#7A7D82`
- Datos: `monthly_nr_corp_by_node` (sin nueva query BQ adicional)
- Init JS: `Plotly.newPlot('chart-nr-corp-bar', ...)` en `showTab('nr-mensual')` — solo una vez via flag `._hasPlot`

**Tabla `build_nr_corp_table_html()`** — 4 niveles con colapso interactivo, **6 filas por nodo**:

| # | Fila | Condición | Estilo |
|---|---|---|---|
| 1 | HEADER (nombre + toggle ▶) | Siempre | Fondo de nivel, negrita — única con `data-corp-node` |
| 2 | N+R | Siempre | Sub-fila gris `#f5f6f8` |
| 3 | Plan | Solo nodos en `hierarchy_PLAN_Corp` | Fondo crema `#fdf9ec` |
| 4 | vs Plan | Solo si hay Plan | Fondo crema, ▲/▼ color |
| 5 | MoM | Siempre | Sub-fila gris |
| 6 | Share N+R | Siempre | Sub-fila gris |

- **Estado inicial**: grupos (sub1) visibles; sub-canales y medios ocultos (`display:none`)
- **Orden**: OC+UCR → POM → OTHERS → NO ATRIBUIDO → [separador] → Total N+R (al fondo)
- **Toggle**: botón ▶/▼ en grupos/sub-canales con hijos; bullet `●` en hojas
- **JS**: `toggleCorpNode(nodeId)` expande solo hijos directos; `collapseCorpNode(nodeId)` colapsa toda la sub-rama recursivamente
- **Paleta limpia**: fondos blancos (`#ffffff`/`#f0f4fa`), texto oscuro, sub-filas gris `#f5f6f8`
- **Atributos HTML**: `data-corp-node` (solo fila HEADER, para colapso recursivo), `data-corp-parent` (todas las filas del hijo), `data-corp-toggle` (botón)
- **`node_by_id`** filtra por `'id' in c` (no por `_doc`) — bug corregido en §27
- **Plan corp** usa `plan_nr_corp_by_node_from_data[node_id]` (de `load_plan_corp()`) — **independiente de `plan_nr`** de NR Mensual

### NR Diario — Sección corporativa diaria

Aparece DEBAJO de la tabla principal de NR Diario, en `pane-nr-diario`:
- **Gráfica** `chart-nr-corp-daily-bar`: barras apiladas N+R absoluto diario por grupo. `Plotly.react()` en updates.
- **Tabla** `tbl-nr-corp-daily`: 2 filas por nodo (N+R + Share), columnas = días del mes. Mismo toggle colapsable.
- Fuente: `D.daily_nr_corp_by_node` (de `process_nr_corp_daily()` en `data_js`)
- Funciones JS: `renderNRCorpDailySection`, `renderNRCorpDailyChart`, `renderNRCorpDailyTable`, `toggleCorpDailyNode`, `collapseCorpDailyNode`, `buildDailyCorpNodeRows`
- Atributos `data-corp-daily-*` separados de los mensuales para evitar conflictos

### NR Diario Acumulado
Seguimiento del acumulado diario de N+R vs promedio de N meses previos.

- KPI cards del acumulado al último día disponible vs promedio N meses previos
- Gráfica de barras apiladas diarias (acumulado) + línea promedio + CPA en eje secundario
- Tabla de acumulado diario por canal + fila vs promedio
- Gráfica de líneas acumuladas (al fondo, reducida)
- Slider de N meses previos (1–6) aplica a promedio y % vs promedio

### NR Diario
N+R diario puro (no acumulado) por canal + comparativo % vs promedio N meses previos.

- KPI cards del NR diario del día de referencia (hoy−1 para mes actual, último día para meses pasados)
- Gráfica de barras apiladas N+R diario + promedio previo + CPA
- Tabla N+R diario por día + % vs promedio N meses

### Performance
Métricas de inversión, eficiencia y valor predicho por canal, cruzando las dos fuentes BQ.

**Columnas por canal** (tabla estática HTML generada en Python por `build_perf_table_html()`):
- N+R Total, ↳ N+R Paid, ↳ N+R Free, ↳ N+R Gest. Others (condicional)
- **Inv. Total (USD)** *(resaltada)*, ↳ Plan Inv., ↳ vs Plan Inv.
- **CPA Blend.** *(resaltada)*, ↳ Plan CPA, ↳ vs Plan CPA
- ↳ CPA Paid
- **VPU Pred 90D** *(resaltada)*, ↳ Plan VPU, ↳ vs Plan VPU
- ↳ Valor Pred 90D, ↳ Plan Valor, ↳ vs Plan Valor
- ROAs

Las filas `↳ Plan *` y `↳ vs Plan *` solo se muestran para los canales que tienen fila correspondiente en el Excel (`plan_row_valor` o `plan_row_inv` en `channels_config.json`). Plan VPU se **deriva** (plan_valor / plan_nr), no se lee directamente del Excel.

**Gráfica**: barras apiladas de Inversión por canal + líneas CPA Blend, ROAs y **Plan Inv.** (línea roja punteada, eje y1). Plan Inv. se recalcula dinámicamente al cambiar canal (`D.plan_inv[canal]`).

**Lógica de métricas**: ver `docs/metrics_logic.md` para fórmulas exactas y fuentes BQ.

---

## Fuentes de datos BigQuery

`SIT_SITE_ID = 'MLM'` | Histórico desde `2025-01-01`

### Torre de Control TC — Fuentes certificadas SSOT (§71 History.md)

Desde la sesión §71 (2026-04-24), el dashboard usa las tablas certificadas del SSOT en lugar de las tablas deprecated.

| Tabla TC | Dataset | Qué aporta | Usada por |
|---|---|---|---|
| **`BT_OC_NR_REPORTE_TORRE_DAILY`** | `meli-bi-data.SBOX_EG_MKT` | N+R OC (lift-based), costo OC, valor OC | `get_nr_tc_sql()` |
| **`BT_MP_INDIVIDUALS_PERFORMANCE`** | `meli-bi-data.SBOX_MARKETING` | N+R Paid (7D/std), costo Paid, valor Paid | `get_nr_tc_sql()` |
| **`BT_MP_USER_ENGAGEMENT_INAPP`** | `meli-bi-data.SBOX_MARKETING` | **TOTAL N+R diario** — fuente del residual ORG/NO ATRIBUIDO. ~20 GB para MLM desde 2025-01-01. | `get_nr_tc_sql()` (ORG residual FM §78) · `get_nr_corp_tc_sql/daily()` (NO ATRIBUIDO Corp §78) |
| `LK_API_CURRENCY_CONVERSION` | `meli-bi-data.WHOWNER` | Tipo de cambio LC→USD para costo incentivos | `get_nr_tc_sql()` |

**Tabla adicional para Installs Mensual (§88):**

| Tabla | Dataset | Qué aporta | Usada por |
|---|---|---|---|
| **`BASE_INSTALLS_LIFECYCLE`** | `meli-bi-data.SBOX_MKTCORPMP` | Installs mensuales por canal con desglose new/recovered/repeated. SSOT certificado — <1% vs Corp screenshot. | `get_installs_monthly_sql()`, `get_installs_corp_monthly_sql()` |

**Columnas clave de `BASE_INSTALLS_LIFECYCLE`:**
- `channel`: POM · Own Channels MKT · Own Channels PRD · Own Channels OTHERS · MGM · Partnerships · BRANDFORMANCE · OTHERS · ORGANICO
- `fecha_mes`: YYYYMM
- `flag_reinstall`: TRUE=reinstall / FALSE=instalación nueva
- `qty_custs_potential_new` + `qty_custs_potential_recovered` + `qty_custs_repeated` = **Total Installs**
- `sit_site_id`: filtro MLM

**Tablas deprecated (en proceso de migración):**

| Tabla | Estado | Reemplazada por | Fase |
|---|---|---|---|
| `SBOX_MKTCORPMP.PANEL_MONTHLY_DAILY_HISTORICO` | ✅ **MIGRADA §77** | `BT_OC_NR_REPORTE_TORRE_DAILY` (OC) + `BT_MP_INDIVIDUALS_PERFORMANCE` (Paid + ORG via NOT NETWORK APPE) | ✅ Migración completa |
| `SBOX_MKTCORPMP.PANEL_MONTHLY_COSTOS_CANALES` | ⚠️ **DEPRECATED** | STG tables TC (tablas base por confirmar) | 🔲 Fase 4 pendiente |

**Columnas clave de `BT_OC_NR_REPORTE_TORRE_DAILY`:**

| Columna | Descripción |
|---|---|
| `DAY_ID` | Fecha del registro |
| `SITE` | País (filtro `MLM`) |
| `CANAL` | Medio de comunicación: PUSH · EMAIL · REAL ESTATE - Drawer · REAL ESTATE - Quick Access · REAL ESTATE - Discovery · REAL ESTATE - Congrats · WHATSAPP · PANDORA · JOURNEY |
| `CLASIFICACION` | Estrategia OC: `UCRANIA` (UCR Gest) · `ACTIVATION` (OC ACT) · `ADHOC` (OC ACT) · `OTHER RECURRING` (UCR PRD) |
| `NR_INC_USERS` | Usuarios incrementales por lift (Test − Control). Negativos = correcciones retroactivas. |
| `NR_INC_VALUE` | Valor predicho 90D × NR incremental |
| `CONSUMIDO_USD` + `COSTO_ENVIO_USD` + `COSTO_MANTIKA_USD` | Inversión OC (3 componentes) |
| `FLAG_PAID` | `'PAID'` o `'FREE'` — usado para CPA/ROAS paid vs blended |

**Columnas clave de `BT_MP_INDIVIDUALS_PERFORMANCE`:**

| Columna | Descripción |
|---|---|
| `TIM_DAY` | Fecha del registro |
| `SIT_SITE_ID` | País (filtro `MLM`) |
| `STRATEGY_GROUP` | Estrategia: `ACQUISITION POM` · `ACTIVATION POM` · `WEB POM` · `CTW POM` · `ACTIVATION MGM` · `PANDORA` |
| `SOURCE_CD` | `INSTALLS` (ventana 7D) o `TOOL_COST` (ventana std) |
| `CHANNEL_GROUP` | Grupo canal. Filas `CHANNEL_GROUP='OC'` → EXCLUIR (ya en Torre Daily) |
| `NETWORK_GROUP_NAME` | Red: `MGM` · `MGM ECOSISTEMICO` · `LANDINGS` · `AFFILIATES` · `PARTNERSHIPS` · `BRANDFORMANCE` · **`NOT NETWORK APPE`** (§76: fuente ORG) |
| `NEW_USERS_7D_INAPP` + `RECOVERED_USERS_7D_INAPP` | N+R ventana 7D (para SOURCE_CD='INSTALLS') |
| `NEW_USERS_INAPP` + `RECOVERED_USERS_INAPP` | N+R ventana estándar (para SOURCE_CD='TOOL_COST') |
| `COST_USD` | Costo media USD |
| `COST_LC_INCENTIVOS` | Costo incentivos LC (convertir con `LK_API_CURRENCY_CONVERSION`) |

> **§77/§78**: ORG/NO ATRIBUIDO usa **residual INAPP exacto** desde `§78`. Metodología: `INAPP_TOTAL (BT_MP_USER_ENGAGEMENT_INAPP) − OC − PAID − POM_FLAG` por día. Resultado ~712K NR/mes ≈ referencia del equipo. El CTE `org_legacy_tc` en `get_nr_tc_sql()` (branch `baseline_skipped`) ahora implementa este residual. `pom_flag_tc` (POM_FLAG='POM Others') se resta del total pero **NO** aparece en `union_tc` — esas filas van al residual ORG, no a FM `pom_others`.

### Tablas de Comms_OC — Arquitectura 2 Ramas (§75)

La query `get_comms_oc_fresh_sql()` usa **2 ramas** unificadas (migración §75 desde 4 ramas legacy):

| Rama | Tabla TC | Dataset | Qué cubre |
|---|---|---|---|
| **A** | `BT_OC_DASHBOARD_ALL_CAMPAIGNS_NR` | `meli-bi-data.SBOX_EG_MKT` | OC ACT + ADHOC + FLOWS + RE |
| **B** | `BT_OC_DASHBOARD_ALL_CAMPAIGNS_NR_ACQUISITION` | `meli-bi-data.SBOX_EG_MKT` | UCR Gest (Ucrania Adquisición) |

- Dedup cross-tabla: si el mismo `(COMM_ID, SENT_DATE, CANAL)` está en ambas → `FUENTE_TABLA='AMBAS'`, métricas de Rama A
- `USER_INC` **§80**: fórmula strategy-agnostic data-driven. `COALESCE(NULLIF(7D_ADJUST, 0), NR_INC_USERS)`. Validado: ACQUISITION y ACTIVATION **nunca** tienen 7D_ADJUST ≠ 0; UCRANIA puede tener ambas (difieren ~134%). Rama B usa `Q_NR_7D`.
- **STRATEGY filter Rama A §81/§84**: `IN ('UCRANIA', 'ACTIVATION', 'ACQUISITION', 'RE-ACTIVATION', 'ENGAGEMENT') OR (STRATEGY='OTHERS' AND CANAL='JOURNEY')`. `RE-ACTIVATION` (§81) = flows churn recuperan inactivos 90+ días. `ENGAGEMENT` (§84) = journeys de engagement con impacto en N+R.
- **SELLERS rule §84**: por defecto `TEAM NOT IN ('SELLERS', 'ADHOC - SELLERS')` aplica. Excepción: si `ABS(USER_INC) > 250` la campaña sí entra para rastrear movimientos de aguja. Clasif → `CORP_SUBCANAL = FM_SUBCANAL = 'OTHERS_SELLERS'` (P0 en las 4 funciones `_classify_*`). Rama A usa fórmula USER_INC completa; Rama B usa `Q_NR_7D`.
- **Filtro CHURN §81**: `NOT LIKE '%CHURN%'` **eliminado de Rama A**. Conservado en Rama B (UCR Gest no tiene RE-ACTIVATION). El template `_EXCL` en queries.py es código muerto (definido, nunca referenciado).
- Nuevas cols §75: `FUENTE_TABLA`, `TOTAL_ABSOLUTO_NR` (→ `NR_TOTAL_Test` §79), `RATIO_CANIBALIZACION`, `CLASIF_CAMPAIGNS`, `FLAG_PAID`, costos
- **§79**: columna `TEST` renombrada → **`Sents`** · `Absoluto NR` renombrada → **`NR_TOTAL_Test`** · nueva columna **`NR_TOTAL_Control`** (`NEW_COUNT_USERS_CONTROL_CONV + REC_COUNT_USERS_CONTROL_CONV`)
- **§80**: +columna `EXPERIMENT` (Rama A de tabla, Rama B NULL). Gotcha: no debe aparecer en Rama A después de CLASIF_CAMPAIGNS (duplicado); en Rama B debe ser `CAST(NULL AS STRING)` en posición 11 (después de SUBSTRATEGY), no como lectura directa.
- Eliminadas cols legacy: M_LIFT, M_CVR_TEST, TPN_INC, TPV_INC, PRINTS_RE/TAPS_RE, TITLE, TEXT

> ⚠️ Las tablas `SBOX_EG_MKT.*` no llevan prefijo de proyecto. Verificar permisos ADC.

**Cache Two-Tier:**
- **Tier 1** `comms_oc_cache.json`: meses cerrados, **24,248 registros** (Nov-25→Mar-26), schema §75/§80/§81. Rebuild: `python scripts/refresh_comms_oc_cache.py --full` (~30-50 min). Nota: el mensaje final del script dice `gen_dashboard_v2.py` — texto stale, ignorar.
- **Tier 2** `comms_oc_current_month.json`: mes actual, **4,126 registros** (Abr-26). TTL diario. Primera generación corre BQ (~10-15 min). Siguientes: instantáneas. Forzar re-query: `del data\comms_oc_current_month.json`

> ~~`PANEL_MONTHLY_DAILY_HISTORICO`~~ — ✅ **Migrada completamente en §77**. Ninguna query activa la usa. `get_nr_sql()` y demás funciones legacy conservadas en `queries.py` como referencia (marcadas DEPRECATED).

> ~~`PANEL_MONTHLY_COSTOS_CANALES`~~ — ⚠️ **Pendiente migración** (Fase 4). `get_costos_tc_sql()` ya usa `BT_MP_INDIVIDUALS_PERFORMANCE` para Paid y `BT_OC_NR_REPORTE_TORRE_DAILY` para OC. Tablas base STG de costos por confirmar acceso.

### Plan de negocio
`data/Resumen Plan Acq 2026.xlsx` — leído con `pandas` + `openpyxl`. Tiene bloques de KPIs separados (ver `docs/metrics_logic.md §6`):

| Bloque | Filas Excel | `channels_config.json` |
|---|---|---|
| N+R | 1–30 | `plan_row` |
| Valor Pred 90D | 51–65 | `plan_row_valor` |
| Inversión Total | 83–97 | `plan_row_inv` |

- `plan_row` → N+R plan. Nodos sin fila propia (OC+UCR) lo calculan sumando sus `plan_lines`.
- `plan_row_valor` → Plan Valor Predicho. Nodos sin fila propia (Ucrania, POM TOTAL) se propagan bottom-up en `load_plan()`.
- `plan_row_inv` → Plan Inversión. El Excel ya tiene filas de agregados para nodos padre — sin propagación.
- `plan_lines` → sub-líneas del plan N+R (Plan Recurring, Plan Ad-Hoc, Plan Producto).
- Flag `"no_chart": true` en una plan_line → excluida del chart Plotly pero sigue sumando al total del plan padre.

`load_plan()` en `gen_dashboard_v1.py` retorna 4 dicts: `plan_nr`, `plan_lines_data`, `plan_valor`, `plan_inv`. Todos se inyectan en `data{}` y `data_js{}`.

---

## channels_config.json — Secciones principales

El JSON tiene **8 secciones** de primer nivel:

| Sección | Consumida por | Propósito |
|---|---|---|
| `hierarchy_nr` | `process_all()`, builders | Jerarquía N+R negocio. Fuente: **`get_nr_tc_sql()`** (TC §71). Cada nodo hoja tiene `tc_mapping` + `bq_mapping` (legacy) |
| `hierarchy_cost` | `process_all()`, builders | Jerarquía Costos. Fuente: `get_costos_tc_sql()` (TC §72). Incluye `pom_others_c` (§74). |
| `hierarchy_nr_corp` | Referencia documental | Versión corregida de `hierarchy_nr` con campos `ap1`/`ap2` documentales y `_doc` |
| `hierarchy_nr_corp_detail` | `process_nr_corp/daily`, `build_nr_corp_*` | Jerarquía corp de 4 niveles (AP1→AP2→TOUCHPOINT). Fuente: `get_nr_corp_sql()` |
| `hierarchy_PLAN` | Solo documentación | Mapa completo Excel→dashboard con reglas de negocio (no ejecutado) |
| `hierarchy_PLAN_Corp` | `load_plan_corp()` | Mappings ejecutables Excel→corp_node_id para Plan en tabla corp. **Independiente de `hierarchy_nr`** |
| `hierarchy_resumenPlan` | Solo documentación | Mapa Excel Plan ↔ labels dashboard anterior (referencia) |
| `visuals` | builders | Colores y estilos globales |

> **Separación crítica de plan**: `hierarchy_nr` usa `plan_row`/`plan_lines` → alimenta pestaña NR Mensual. `hierarchy_PLAN_Corp` → alimenta **solo** la tabla corp. Nunca se mezclan.

---

## channels_config.json — Campos clave

```json
{
  "id": "ucr_gest",
  "label": "UCR Gest",
  "level": "leaf",          // grand | sub1 | sub2 | leaf
  "indent": 3,              // profundidad de indentación en tablas
  "is_leaf": true,
  "color": "#5899D1",       // color oficial del canal (gráficas, bordes en tabla Performance)
  "parent": "ucrania",
  "bq_mapping": {           // LEGACY — tabla PANEL_MONTHLY_DAILY_HISTORICO (DEPRECATED §71)
    "strategy": "UCRANIA",
    "channel": "OWN CHANNELS MKT"
  },
  "tc_mapping": {           // ACTIVO §71 — Torre de Control. Leído por get_nr_tc_sql()
    "source_tc": "torre_daily",        // "torre_daily" | "individuals_performance" | "baseline_skipped"
    "clasificacion_tc": ["UCRANIA"]    // Para torre_daily: CLASIFICACION IN (...)
    // Para individuals_performance:
    //   "strategy_group_tc": [...]            — STRATEGY_GROUP IN (...)
    //   "network_group_name_tc": [...]        — UPPER(NETWORK_GROUP_NAME) IN (...)
    //   "source_cd_filter_tc": ["INSTALLS"]   — AND SOURCE_CD IN (...) para separar ADQ vs ACT
    // Para baseline_skipped (ORG §76):
    //   CTE dedicado en get_nr_tc_sql() — NOT NETWORK APPE + SOURCE_CD='TOOL_COST'
    //   Evita colisión de CASE WHEN con POM Others. Sin cache ni residual.
  },
  "cost_mapping": {         // LEGACY — tabla PANEL_MONTHLY_COSTOS_CANALES (DEPRECATED §72)
    "strategy": ["UCRANIA"],
    "channel": "OWN CHANNELS MKT",
    "gest_others_strategies": []
  },
  "plan_row": 6,            // fila iloc en Excel — bloque N+R (int = una fila)
  "plan_rows": [5, 9],      // ALTERNATIVA a plan_row — suma de múltiples filas (§74, solo pom_total)
  "plan_row_valor": 54,     // fila iloc en Excel — bloque Valor Pred 90D. Solo nodos con plan individual.
                            // UCR Gest/UCR PRD/OC ACT/POM ADQ/POM ACT NO tienen plan_row_valor (§74).
  "plan_row_inv": 82        // fila iloc en Excel — bloque Inversión Total
}
```

> **§71**: `tc_mapping` es el campo activo. `bq_mapping` y `cost_mapping` son legacy (tablas deprecated) — se conservan como documentación y fallback hasta completar la migración.

**Flags especiales**:
- `"no_cost": true` — canal sin inversión (ej. L&P ADQ, L&P ACT, UCR PRD). Excluido de `getLeafCostToHL()`.
- `"no_chart": true` en `plan_lines` — plan_line excluida del chart Plotly (sigue sumando al total del plan padre).
- `"is_org": true` en `bq_mapping` — canal orgánico legacy. Equivalente TC: `tc_mapping.source_tc = "baseline_skipped"`.

---

## Mapeo de queries a fuentes

| Función SQL (`queries.py`) | Tabla BQ | Usada para | Estado |
|---|---|---|---|
| **`get_nr_tc_sql(HIERARCHY_NR)`** | Torre Daily + Individuals Perf + **BT_MP_USER_ENGAGEMENT_INAPP** (ORG residual) | N+R mensual/diario. ORG: `org_legacy_tc` = INAPP − OC − PAID (§79: `pom_flag_tc` ya NO se resta del residual FM → FM Total = INAPP Total). `pom_flag_tc` definido en WITH pero no en union_tc ni en residual. D-1 cutoff (§82). | ✅ **ACTIVA §71/§79** |
| **`get_vpu_tc_sql(HIERARCHY_NR)`** | Torre Daily + Individuals Perf + legacy ORG | VPU / Valor Pred 90D por canal/mes. `NR_INC_VALUE` (OC) + `VALUE_MKT_USD_*` (Paid). ⚠️ **VPU model break en Abr-26** — ver §86. | ✅ **ACTIVA §72** |
| **`get_costos_tc_sql(HIERARCHY_NR)`** | Torre Daily + Individuals Perf | Inversión: `INV_CANAL`, `INV_INCENTIVO`, `INV_TOTAL`, `INV_MANTIKA`. POM usa solo `COST_USD` (sin `COST_LC_INCENTIVOS`). | ✅ **ACTIVA §72** |
| **`get_perf_paid_tc_sql(HIERARCHY_NR)`** | Torre Daily + Individuals Perf | N+R Paid (`FLAG_PAID='PAID'` para OC, `COST_USD>0` para Paid). `NR_GEST_OTHERS=0`. | ✅ **ACTIVA §72** |
| **`get_roa_tc_sql()`** | Torre Daily | ROA numerador: `NR_INC_VALUE` donde `FLAG_PAID='PAID'` y costo > 0. Solo OC (UCRANIA+ACTIVATION+ADHOC). | ✅ **ACTIVA §72** |
| **`get_nr_corp_tc_sql()`** | Torre Daily + Individuals Perf + **BT_MP_USER_ENGAGEMENT_INAPP** | Tabla Corp mensual. §78 fixes: UCR PRD (`OTHER RECURRING→OTH\|UCR_PRD`), POM Others (POM_FLAG), L&P (UPPER), NO ATRIBUIDO = INAPP residual. D-1 cutoff (§82). | ✅ **ACTIVA §72/§78** |
| **`get_nr_corp_daily_tc_sql()`** | Torre Daily + Individuals Perf + **BT_MP_USER_ENGAGEMENT_INAPP** | Tabla Corp diaria. Mismos §78 fixes + `dia_del_mes`. | ✅ **ACTIVA §72/§78** |
| `get_comms_oc_fresh_sql()` | `BT_OC_DASHBOARD_ALL_CAMPAIGNS_NR` + `BT_OC_DASHBOARD_ALL_CAMPAIGNS_NR_ACQUISITION` | Comms_OC Tier 2 (mes actual). 2 ramas UNION ALL con dedup FUENTE_TABLA. | ✅ **ACTIVA §75** |
| **`get_new_rec_monthly_sql()`** | `BT_MP_USER_ENGAGEMENT_INAPP` | New vs Recovered total sitio por mes. Columnas: `new_nr`, `rec_nr`. D-1 cutoff. Usado por pestaña Reporting §85. | ✅ **NUEVA §85** |
| **`get_installs_monthly_sql(HIERARCHY_NR)`** | `BASE_INSTALLS_LIFECYCLE` | Installs mensuales por canal FM. Total = new+rec+repeat. <1% vs Corp screenshot. Mapping: POM→'POM ADQ', Own Ch. MKT→'UCR Gest', Own Ch. OTHERS→'OC ACT', etc. | ✅ **NUEVA §88** |
| **`get_installs_corp_monthly_sql()`** | `BASE_INSTALLS_LIFECYCLE` | Installs por corp_key para Vista Corp. Usa node_id directo para corp_ucr_eg y corp_pom (sin bq_key). | ✅ **NUEVA §88** |
| `_tc_channel_parts(HIERARCHY_NR)` | — | Helper privado. Reutilizado por `get_vpu_tc_sql`, `get_costos_tc_sql`, `get_perf_paid_tc_sql`. | ✅ ACTIVA §72 |
| ~~`get_nr_sql`~~ / ~~`get_costos_sql`~~ / ~~`get_perf_paid_sql`~~ / ~~`get_perf_vpu_sql`~~ / ~~`get_perf_roa_costos_sql`~~ / ~~`get_nr_corp_sql`~~ / ~~`get_nr_corp_daily_sql`~~ | ~~Tablas deprecated~~ | ~~Todas reemplazadas por TC~~ | 🗄️ conservadas sin uso |

---

## Modelo de Valor Pred 90D / VPU — Cambio de modelo en Abr 2026 (§86)

> ⚠️ **LEER ANTES DE TRABAJAR CON VPU O VALOR PRED 90D**

### Qué pasó

En Abril 2026 el equipo de Marketing Science Corp implementó un **nuevo modelo de valor "Fact Based"** que reemplazó el modelo de predicción anterior. Esto produjo un corte abrupto en todas las columnas de valor en BQ simultáneamente:

| Período | Modelo | VPU típico/usuario | Valor total site/mes |
|---|---|---|---|
| Ene 2025 — Mar 2026 | Viejo (prediction-based) | ~$50–70 USD | ~$50–70 M USD |
| **Abr 2026 en adelante** | **Nuevo (fact-based)** | **~$22–26 USD** | **~$22–28 M USD** |

### Tablas afectadas (corte exacto en Abr 2026)

| Tabla BQ | Columna afectada |
|---|---|
| `SBOX_EG_MKT.BT_OC_NR_REPORTE_TORRE_DAILY` | `NR_INC_VALUE` |
| `SBOX_EG_MKT.BT_OC_DASHBOARD_ALL_CAMPAIGNS_NR` | `NEW_VALUE_7D_ADJUST`, `REC_VALUE_7D_ADJUST`, `NEW_INC_VALUE`, `REC_INC_VALUE` |
| `SBOX_MARKETING.BT_MP_INDIVIDUALS_PERFORMANCE` | `VALUE_MKT_USD_NEW_USERS_7D`, `VALUE_MKT_USD_RECOVERED_USERS_7D`, `VALUE_MKT_USD_NEW_USERS`, `VALUE_MKT_USD_RECOVERED_USERS` |
| `SBOX_MARKETING.BT_MP_ACTIVATION_REVENUE_MKT_SCORING` | `REVENUE_PREDICTION` |

### Implicaciones en el dashboard

1. **Datos actuales (Abr-26 en adelante)**: VPU/Valor **alineados** con el Corp tool ✅
2. **Datos históricos (pre-Abr-26)**: VPU/Valor en el dashboard muestran el **modelo viejo** (~$56-62/usuario). El Corp tool muestra ~$22-24 histórico porque usa un **pipeline interno de MktSci que retroactivamente actualiza `BT_MP_ACTIVATION_REVENUE_MKT_SCORING`** al desplegar un nuevo modelo. Ese pipeline opera sobre versión interna no accesible desde `SBOX_MARKETING` pública. **Confirmado §86**: el Corp query corrido HOY sobre BQ público produce los mismos VPU históricos que nosotros (~$60 Mar-26). El dato BQ público está congelado en modelo viejo para pre-Abr 26.
3. **N+R y CPA**: **Sin impacto** — el cambio de modelo solo afecta columnas de valor predicho, no conteos de usuarios ni inversión.

### Validación empírica clave (§86)

Se verificó que `BT_OC_NR_REPORTE_TORRE_DAILY.NR_INC_VALUE` y `BT_OC_DASHBOARD_ALL_CAMPAIGNS_NR.NEW_VALUE_7D_ADJUST` producen **exactamente los mismos valores de VPU** para UCR (diff = 0.00 en todos los meses). Cambiar la fuente de OC no resuelve el gap histórico.

### Factor de normalización histórica — confirmado por MktSci Corp (§87)

El equipo de Marketing Science Corp confirmó que para comparaciones históricas justas se adoptó un **factor único de nivelación**:

```
Valor histórico (pre-202604) × 0.38 = Valor fact-based equivalente
```

Validación: `$60.87 × 0.38 = $23.13` (Mar-26) ✓ · `$53.55 × 0.38 = $20.35` (Ene-26) ✓

**✅ Implementado en `src/processors.py` (§87, corregido §89)**: constantes `_VALOR_BREAK_MONTH = '202604'` y `_VALOR_HIST_FACTOR = 0.38`.
- `perf_vpu_prod`: ×0.38 a todos los canales post-propagación bottom-up ✅
- `perf_roa_num`: ×0.38 **sólo a canales OC** (`_oc_roa_labels` = UCR Gest + OC ACT, que vienen raw de BQ). POM se asigna desde `perf_vpu_prod` ya normalizado — **sin segundo factor** (§89 fix doble-aplicación). Propagación bottom-up corre después con todos los valores correctos.

Impacta: Performance_vista_FM (VPU/Valor/ROAs), Reporting Sección 1 (Valor Predictivo chart + tabla), Reporting Sección 3 (ROAs OC).

**No implementar** `BT_MP_ACTIVATION_REVENUE_MKT_SCORING` como fuente alternativa — tiene el mismo corte de modelo y el factor 0.38 ya normaliza correctamente desde nuestras fuentes actuales.

### Fix deploy SSL — `deploy_appscript_v1.py` (§87)

`ssl.SSLWantWriteError` al subir ~110 MB via `googleapiclient+httplib2`. Fix: `update_files()` usa `google.auth.transport.requests.AuthorizedSession` con `timeout=300`. Ver §87 History.md para detalle.

---

## Lógica de ROA por canal — Torre de Control (§72)

> ✅ **Migrado a TC en §72**. Ver también metodología de costos OC en §72.7 de History.md.

| Canal | Fuente ROA numerador (TC) | Fuente ROA denominador |
|---|---|---|
| UCR Gest | `NR_INC_VALUE` de `BT_OC_NR_REPORTE_TORRE_DAILY` (CLASIFICACION='UCRANIA', FLAG_PAID='PAID') | `CONSUMIDO + ENVIO + MANTIKA` mismo día |
| OC ACT | `NR_INC_VALUE` de Torre Daily (CLASIFICACION='ACTIVATION'+'ADHOC', FLAG_PAID='PAID') | Mismo |
| POM ADQ / POM ACT | `perf_vpu_prod` calculado por `get_vpu_tc_sql()` — `VALUE_MKT_USD_7D` de Individuals Performance | `COST_USD` (media, sin incentivos) |
| MGM ADQ | `perf_vpu_prod` de `get_vpu_tc_sql()` | `COST_USD` de Individuals Performance |
| MGM ACT / UCR PRD / L&P / ORG | Sin ROA (valor `—`) | N/A |

## Metodología de costos OC — Tres metodologías distintas (§72)

> ⚠️ Los números OC del dashboard NO deben coincidir con el Corp centralizado. Son metodologías distintas.

| Metodología | Fuente | NR OC Mar26 | INV_TOTAL OC Mar26 | CPA resultante |
|---|---|---|---|---|
| **TC (LIFT) — nuestro dashboard** | `BT_OC_NR_REPORTE_TORRE_DAILY` | ~139K (incremental Test−Control) | ~$986K (presupuesto consumido) | ~$7.1 |
| **Tabla vieja (atribución clásica)** | `PANEL_MONTHLY_COSTOS_CANALES` | ~113K | ~$883K | ~$7.8 |
| **Corp centralizado (atribución total)** | Fuente propia (commitado) | ~426K (todos los tocados) | ~$2.6M (presupuesto comprometido) | ~$6.1 |

Todos los CPA son **internamente consistentes** con su metodología. El CPA del Corp ($6.1) usa 426K NR y $2.6M inversión. El nuestro ($7.1) usa 139K NR y $986K. Misma calidad de campaña medida diferente.

**Desglose de componentes de inversión OC (verificado vs Corp centralizado §72.8):**

| Componente | Campo Torre Daily | Valor típico | Corp label |
|---|---|---|---|
| Inv. Canal | `COSTO_ENVIO_USD` | ≈ $0 para UCRANIA, pequeño para ACTIVATION | Inversión Canal |
| Inv. Incentivos | `CONSUMIDO_USD` | Mayor componente — cashback al usuario | Inversión Incentivos |
| Inv. Mantika | `COSTO_MANTIKA_USD` | Fee plataforma Mantika | Inversión Mantika |
| **Inv. Total** | Suma de 3 | | Inversión Total |

**⚠️ COST_LC_INCENTIVOS de POM NO se suma**: El Corp muestra POM INV_INCENTIVO = $0. Los incentivos de POM son costos de producto, no marketing. Excluidos de `get_costos_tc_sql()` desde §72.

---

## Estructura JS del template (funciones principales)

### Pestaña MTD D7
- `renderMTDTable(month)` — construye toda la tabla MTD dinámicamente en JS

### Pestaña NR Mensual
- `renderKPIsNRMensual(month, canal)` — KPI cards
- `highlightRowNRMensual(canal)` — resalta fila en tabla
- `filterTableNRMensual(canal)` — filtra tabla por jerarquía
- `highlightColNRMensual(month)` — resalta columna de mes
- `highlightChartNRMensual(canal)` — filtra y resalta series en chart
- `updateCPANRMensual(canal)`, `updatePlanNRMensual(canal)`, `updateAnnotNRMensual(canal)` — actualizaciones del chart
- `highlightMonthNRMensual(month)` — línea vertical de mes en chart
- `toggleCorpNode(nodeId)` — expande/colapsa hijos directos de un nodo de la tabla corporativa
- `collapseCorpNode(nodeId)` — colapso recursivo completo: oculta hijos + todos los descendientes, restablece botones ▶

### Pestañas NR Diario Acumulado / NR Diario (compartidas)
- `renderDynamic(tab)` — dispatcher: llama `renderNRDiarioAcum` o `renderNRDiario` según el tab activo
- `getPriorMonths(month, n)`, `computeAvg(canal, month, n)`, `getChannelsForCanal(canal)` — helpers
- `getDailyNR(ch, month, d)` — obtiene NR diario de un canal/mes/día (delta de acumulados)

### Pestaña NR Diario Acumulado
- `renderNRDiarioAcum(month)` — renderiza chart de líneas + tabla + KPIs
- `renderKPIsNRDiarioAcum(month, canal, nPrior)` — KPI cards acumuladas
- `renderChartNRDiarioAcum(month)` — chart de barras apiladas acumuladas
- `renderTableNRDiarioAcum(month, canal, nPrior)` — tabla de acumulado diario

### Pestaña NR Diario
- `renderNRDiario(month)` — renderiza chart + KPIs + tabla + sección corp diaria
- `renderKPIsNRDiario(month, canal, nPrior)` — KPI cards de NR diario
- `renderTableNRDiario(month)` — tabla de NR diario + % vs promedio
- `renderNRCorpDailySection(month_key)` — dispatcher gráfica + tabla corp diaria
- `renderNRCorpDailyChart(month_key)` — Plotly barras N+R diario por grupo (con `Plotly.react` en updates)
- `renderNRCorpDailyTable(month_key)` — tabla colapsable dinámica con `buildDailyCorpNodeRows()`
- `toggleCorpDailyNode(node_id)` / `collapseCorpDailyNode(node_id)` — toggle/colapso recursivo (atributos `data-corp-daily-*`)

### Pestaña Performance
- `updateChartPerf(canal)` — actualiza chart: visibilidad de barras, recalcula CPA Blend, ROAs y **Plan Inv.** (usa `D.plan_inv[canal]`), actualiza anotaciones
- `filterTablePerf(canal)` — filtra tabla por jerarquía
- `highlightColPerf(month)` — resalta columna de mes
- `getLeafCostToHL(canal)` — helper: obtiene hojas de Costo para resaltar en chart

### Helpers de NR
- `getLeafNRToHL(canal)` — obtiene canales leaf de NR para resaltar en charts

### Pestaña Comms_OC
- `_commsOcFilterState` — objeto global de estado de los filtros activos (month, fuente, canal, strategy, substrat, bizseg, clasif, campaign). Dropdowns = `Set` (multi-select); texto = `string`. §75: eliminados `app`/`typename`/`title`/`text`; añadidos `fuente`/`clasif`.
- `initCommsOcFilters()` — construye la barra de filtros (dropdowns + text inputs), corre una sola vez al entrar al tab
- `onCommsOcFilterChange()` — lee todos los inputs, actualiza `_commsOcFilterState`, llama `applyCommsOcFilters()`
- `applyCommsOcFilters()` — aplica TODOS los filtros activos (AND logic), muestra/oculta filas, llama `renderCommsOcKPIs()`
- `clearCommsOcFilters()` — resetea filtros de la barra (conserva el mes del selector global)
- `filterCommsOcByMonth(month)` — actualiza `_state.month` y delega a `applyCommsOcFilters()`
- `renderCommsOcKPIs()` — calcula 11 KPI cards sobre las filas VISIBLES (post-filtro): funnel (Create/Test/Control/Arrived/Shown/Open) + eficiencia (Avg Open%/CVR%/Lift%) + impacto (Σ User Inc/Value Inc)
- `toggleCommsGroup(groupId)` — toggle de filas de detalle por grupo (legacy de v1 de la tabla, puede quedar residual)

---

## Flujos de CI/CD (GitHub Actions)

- **Producción (V1)**: `refresh_MLM_ADQ_Dashboard.yml` + `src/deploy_appscript_v1.py` → pipeline único activo
- **Disparo**: cron-job.org → `workflow_dispatch` a las 7:30am y 5pm CDMX (días hábiles)
- **Guardia de seguridad**: el flujo verifica que el HTML pese > 50KB antes de subir (evita borrar producción si BQ falla)
- **Credenciales**: Google ADC en secret `GOOGLE_ADC_CREDENTIALS` + GitHub PAT en cron-job.org

---

## Historial de sesiones resumido

> Para sesiones anteriores a §70, ver `docs/History.md` (§1–§69 cubren Mar–Abr 2026: arquitectura modular, UI jerarquía, pestaña Performance, tablas Corp, NR Diario, extracciones BI, skills v1-v3.1, Comms_OC full pipeline con 4 ramas legacy).

| Sesión | Cambios principales |
|---|---|
| **§70 — 24-Abr-2026** | MTD D7: +columna Plan N+R + fila Mix de Marketing. Eliminación `legacy_v1/` · rename `v2→v1` · rename `CLAUDE2.md→CLAUDE.md`. |
| **§71 — 24-Abr-2026** | Migración Torre de Control Fase 1: `PANEL_MONTHLY_DAILY_HISTORICO` deprecated. `get_nr_tc_sql()` nuevo (SQL dinámico desde `tc_mapping`). `channels_config.json` +`tc_mapping` en todos los nodos hoja. D-2 cutoff (cambiado a D-1 en §82). ORG temporal via CTE `org_legacy_tc` (PANEL ORGANICO). |
| **§72 — 24-Abr-2026** | TC Fases 2-4: `get_vpu_tc_sql()`, `get_costos_tc_sql()`, `get_perf_paid_tc_sql()`, `get_roa_tc_sql()`. `get_nr_corp_tc_sql()` + daily Corp. Helper `_tc_channel_parts()`. Costos OC: 3 componentes (envío/incentivo/mantika). Diagnóstico: OC $986K (LIFT) ≠ Corp $2.6M (atribución) = correcto, metodologías distintas. |
| **§73 — 25-27-Abr-2026** | `config/comms_classification_config.json` NUEVO. Skills: +Modo 16 `drill_decay` (Comms) + `alerta_canal` (OPTIMIZADOR). `build_oc_ucr_analysis_tab_html()` reescrita con datos reales (waterfall, JOURNEY canibalizadores, DEB-CARD +31.7K, camino crítico 133K→240K). Gotchas BQ: `CAMPAIGN_NAME` ≠ `CAMPAIGN_NAME_CLEAN`; `COMUNICATION_NAME` (typo Meli). |
| **§74 — 27-Abr-2026** | `pom_others` nuevo en `hierarchy_nr` (WEB POM + CTW POM). `plan_rows:[5,9]` en pom_total. `multiplier:0.5` en Plan Producto. Eliminado `plan_row_valor` de 5 canales (ucr_gest, ucr_prd, oc_act, pom_adq, pom_act). `pom_others_c` en `hierarchy_cost`. |
| **§75 — 27-Abr-2026** | Comms_OC: 4 ramas legacy → **2 ramas TC** (`BT_OC_DASHBOARD_ALL_CAMPAIGNS_NR` + `_NR_ACQUISITION`). Granularidad diaria (COMM_ID×SENT_DATE×CANAL). Col `FUENTE_TABLA` + dedup cross-tabla `'AMBAS'`. −12 cols legacy, +8 cols nuevas. Cache Tier 1 rebuild completo (20,708 registros schema §75). |
| **§76 — 27-Abr-2026** | Skills: OPTIMIZADOR v4.1 (2,062→792 líneas, 7 Patrones Cross-Signal, `TEMPLATE_STOP_OR_CONTINUE`). Comms Skill +Modo 17 `familia_campanas` +Modo 18 `campaña_historico` (Índice Decaimiento, STOP_OR_CONTINUE). Tab Análisis OC+UCR reescrito con datos reales §75. |
| **§77 — 27-Abr-2026** | **ORG definitivo**: `NOT NETWORK APPE + SOURCE_CD='TOOL_COST'` desde `BT_MP_INDIVIDUALS_PERFORMANCE` via CTE dedicado (branch `baseline_skipped`). Corp NO ATRIBUIDO: mismo fix en `org_corp_tc` / `org_corp_daily_tc`. Eliminado bloque cache ORG en `processors.py`. `refresh_org_cache.py` DEPRECATED. Resultado: ORG ~640K Abr-26 MTD (era 5K o negativo). Dashboard: **43.7 MB**. |
| **§88 — 11-May-2026** | **Nueva pestaña "Installs Mensual"**. Fuente SSOT: `BASE_INSTALLS_LIFECYCLE` (SBOX_MKTCORPMP) — verificado <1% vs Corp screenshot en todos los canales. Vista FM: barras apiladas por canal + CPI line. Vista Corp: barras por grupo + tabla colapsable. Total = new+recovered+repeated. Diagnóstico exhaustivo: primero se intentó `QTY_DEVICES` de INDIVIDUALS_PERFORMANCE (518K POM vs 811K Corp — gap inexplicable en BQ público), luego Corp CTE_ADQ_ACT (mismo gap), finalmente BASE_INSTALLS_LIFECYCLE (818K POM ≈ 811K Corp ✓). Fix clave: Corp usa nodos padre (`corp_ucr_eg`, `corp_pom`) sin breakdown de medio — `directly_populated: set()` evita que bottom-up sobreescriba con sum(children=0). Builder GROUPS fix: usar `['corp_pom']` y `['corp_ucr_eg','corp_oc_adhoc']` en vez de hijos individuales. +`get_installs_monthly_sql()`, `get_installs_corp_monthly_sql()`, `process_installs_monthly()`, 4 builders, 9 funciones JS, Paso 3d. Dashboard: **~113,905 KB**. |
| **§89 — 11-May-2026** | **Fix crítico doble aplicación factor 0.38 en ROAS POM**. Síntoma: Total ROAS pre-Abr-26 mostraba 0.9x–1.1x vs Corp 1.5x–2.0x. Root cause: `perf_roa_num` POM recibía ×0.38 dos veces: (1) heredado de `perf_vpu_prod` que ya fue normalizado, (2) loop final que aplicaba el factor a todos los canales sin excepción. Fix: reordenar pasos — aplicar ×0.38 primero a canales OC solamente (`_oc_roa_labels` derivado de `df_perf_roa`), luego asignar POM desde `perf_vpu_prod` (ya normalizado), luego propagación bottom-up, sin segundo loop. Archivos: `src/processors.py`. |
| **§87 — 7-May-2026** | **Factor 0.38 normalización histórica + marcador modelo + fix deploy SSL**. MktSci Corp confirmó factor único de nivelación: `valor_hist × 0.38 = valor_fact_based`. Implementado en `processors.py` para `perf_vpu_prod` y `perf_roa_num` (meses < `'202604'`), post-propagación bottom-up. Validado: $60.87×0.38=$23.13 (Mar-26) ✓ · $53.55×0.38=$20.35 (Ene-26) ✓. Marcador visual `_apply_model_break()` en c2 Reporting: línea marrón discontinua + callout `⚠ Nuevo modelo` entre Mar-26 y Abr-26, auto-extinción cuando todos los meses sean post-Abr-26. Fix deploy `ssl.SSLWantWriteError`: `update_files()` migrada de `googleapiclient+httplib2` a `AuthorizedSession(requests)` con `timeout=300` — resuelve envío de ~110 MB sobre SSL. Dashboard regenerado y deployado: **110,444 KB** (2026-05-07 13:59). |
| **§86 — 7-May-2026** | **Diagnóstico cambio modelo Valor/VPU + Reporting fixes**. Diagnóstico exhaustivo BQ (5 queries) comparando Torre Daily vs Dashboard Campaigns vs Scoring table. **Root cause gap VPU**: cambio modelo "Fact Based" Abr-2026 en TODAS las tablas simultáneamente (VPU $55-70 → $22-26). Para datos actuales (Abr/May 26) ya alineados con Corp. Para histórico (pre-Abr 26): gap estructural sin solución por tabla retroactiva no accesible. Confirmado: Torre Daily = Dashboard Campaigns (diff=0.00 para UCR VPU). `CLASIF_CAMPAIGNS` usa español ('ACTIVACION' no 'ACTIVATION'). Reporting fixes §85 follow-up: `total_inv()` usando 'Total Inversión' (fix double-count), `vsplan_row` → Total N+R/Plan Total N+R, `growth_annotations(use_arrows=True)` callouts PPT-style, formatos sin sufijo M, `margin.t=75`. Dashboard regenerado: **110,443 KB** (2026-05-07 09:36). Documentado en: `CLAUDE.md §Modelo Valor` + `docs/History.md §86`. **Pendiente §87**: marcador visual Abr-26 en gráficas VPU/Valor. |
| **§85 — 5-May-2026** | **Sesión extensa — múltiples fixes + Reporting tab**. USER_INC fórmula equipo (CLASIF=UCRANIA→Adjust). +col `USER_INC_CON_ADJUST`. Corp/FM Sub-canal Aux (OTHERS_SELLERS mapea a OC ACT / OWN CHANNELS RECURRING). Journey CANAL bypass (todo `CANAL='JOURNEY'` bypasea filtros team/nombre → ~95% journeys capturadas). MEDIO_CLASIF_FINAL +EYG condition. Fix bug `selectAllVisibleCommsOcMS` (scope global). MTD D7→MTD, label D-X dinámico, descripción eliminada. Tab Análisis POM borrado. Skills: Comms Modo 21 `top_medio` (top5/bottom5 por canal×subcanal×medio + USER_INC_ADJ). OPTIMIZADOR +USER_INC_ADJ en equivalencia. **Nueva pestaña Reporting** (3 secciones: N+R Corp + Valor Pred / New vs Rec + N+R Canal / OC Estrategia — charts Plotly descargables PNG). +`get_new_rec_monthly_sql()` + `process_new_rec_monthly()`. `config/reporting_methodology.md` creado. |
| **§84 — 5-May-2026** | **ENGAGEMENT + SELLERS alto impacto en Comms_OC**. Diagnóstico `MLM_S_M_ENG_SWE_PBD`: STRATEGY='OTHERS' + TEAM='ADHOC - SELLERS' (no ENGAGEMENT). Nueva regla: incluir SELLERS si `ABS(USER_INC) > 250` → `CORP/FM_SUBCANAL='OTHERS_SELLERS'`. SQL Rama A (`USER_INC` fórmula completa) y Rama B (`Q_NR_7D`). +`'ENGAGEMENT'` sincronizado en `refresh_comms_oc_cache.py`. P0 SELLERS en 4 funciones `_classify_*`. Pendiente: `--append` rebuild cache con SQL nuevo. |
| **§83 — 5-May-2026** | **MTD D7 mejoras**: badge D-2→D-1 (faltaba en §82). `hoy2`→`hoy1` (refDay usa D-1 real). **MTD usa `monthly_nr` para mes en curso** → MTD = NR Mensual = 105.4K (antes 73K por CUM_NR lag de 2 días). +2 columnas: "vs Plan M %" + "Proy. vs Plan %". Renombrado "MIx"→"Contrib. MoM" con tooltip. Dashboard: **pendiente regeneración**. |
| **§82 — 4-May-2026** | **Corp Total = FM Total** (~1,188 NR/mes perdido por `others_catchall_corp_tc` desapareciendo del UNION ALL): `org_corp_tc` ahora resta `ucr_total_corp` en lugar de `catch_total_corp`. **LMTD inteligente**: mes en curso → mismo día (comparación justa); mes cerrado → mes completo (coincide con NR Mensual). **D-2 → D-1** cutoff: 31 ocurrencias en `queries.py`, label UI actualizado. Dashboard: **84,170 KB**. |
| **§81 — 30-Abr-2026** | **Inclusión RE-ACTIVATION**: +`'RE-ACTIVATION'` a STRATEGY filter Rama A. Eliminado `NOT LIKE '%CHURN%'` de Rama A (conservado en Rama B). Eliminado `'CHURN' in campaign_up` del Python post-proc. Auditoría reveló ~39K NR/mes invisible de flows churn = Recuperados legítimos. Tier 1: 20,643→**24,248** registros. Tier 2: 3,342→**4,126**. Dashboard: **50,929 KB**. |
| **§80 — 30-Abr-2026** | **Fix definitivo USER_INC**: fórmula strategy-agnostic `COALESCE(NULLIF(7D_ADJUST,0), NR_INC_USERS)`. Root cause: ACQUISITION nunca tiene 7D_ADJUST (validado empíricamente 21K+ filas). Impacto corregido: ~144K NR invisible (ACQ: 129K + UCR: 15K). **3 bugs SQL EXPERIMENT** corregidos (duplicate en Rama A pos tardía, duplicate en Rama B pos 11 cruda, type mismatch UNION ALL). Tier 2 cache eliminado y regenerado (USER_INC=912 para MYIJDV-260401-1 ✓). Tier 1 rebuild completado. Dashboard: **43,084 KB**. |
| **§79 — 29-Abr-2026** | **Comms_OC columnas §79**: `TEST→Sents` · `Absoluto NR→NR_TOTAL_Test` · +`NR_TOTAL_Control` (conversiones brutas grupo control, `NEW_COUNT_USERS_CONTROL_CONV + REC_COUNT_USERS_CONTROL_CONV`). KPI card `Σ NR_TOTAL_Control` en `renderCommsOcKPIs()`. **FM Total fix**: eliminado `pf_day_tc` del residual ORG en `get_nr_tc_sql()` → FM Total = Corp Total = INAPP Total (~1,045K). **L&P diagnóstico**: `BT_MP_INDIVIDUALS_PERFORMANCE` para MLM Abr-26 solo tiene 6,953 NR en NETWORK IN (PARTNERSHIPS/LANDINGS/BRANDFORMANCE) — nuestro L&P es correcto para las fuentes disponibles; brecha vs referencia (~6K) proviene de versión diferente de query de referencia. Dashboard: **46.0 MB**. Cache Tier 1 requiere `--full` para `NR_TOTAL_CONTROL`. |
| **§78 — 29-Abr-2026** | **3 fixes Corp OTHERS** (~14K brecha vs referencia): (1) UCR PRD: `OTHER RECURRING→OTH\|UCR_PRD\|TOTAL` en `oc_corp_tc`; (2) POM Others: `UPPER(POM_FLAG) IN ('POM ACTIVATION','POM ACQUISITION','POM OTHERS')` en `paid_corp_tc`; (3) L&P: UPPER() consistente en `NETWORK_GROUP_NAME = 'PARTNERSHIPS'` (era case-sensitive). **INAPP residual** para NO ATRIBUIDO Corp (~46K brecha): `get_nr_corp_tc_sql/daily()` usan `BT_MP_USER_ENGAGEMENT_INAPP` (~20 GB MLM) → residual `INAPP − OC − PAID`. **FM ORG residual** (Fix A): mismo approach en `get_nr_tc_sql()`, `org_legacy_tc` = INAPP residual → ORG ~712K. **POM Others FM** (Fix B): `pom_flag_tc` CTE en `get_nr_tc_sql()` para substracción ORG PERO no en `union_tc` → FM `pom_others` = WEB+CTW solo (~5.3K, consistente con Corp corp_web/ctw_pom). POM_FLAG rows (~2.4K) van al residual ORG. `_tc_channel_parts()`: +`pom_others_label`. Deploy: `check_version_count()` + `VERSION_HARD_LIMIT=199` para Apps Script 200-version limit. Dashboard: **44.0 MB**. |
