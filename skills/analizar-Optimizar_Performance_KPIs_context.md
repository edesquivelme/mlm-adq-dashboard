# analizar-Optimizar_Performance_KPIs_context.md
# ==============================================================================
# BASE DE CONOCIMIENTO: Analizador de Performance — MLM Mercado Pago México
#
# PROPÓSITO:
#   Fuente de datos pre-compilada para el skill analizar-Optimizar_Performance_KPIs_skill.md.
#   Contiene DATOS CRUDOS (series históricas, tablas de performance, benchmarks,
#   riesgos, oportunidades). Las CONCLUSIONES las deriva el skill, no este archivo.
#
# VISTA CORPORATIVA (CORP) — Nomenclatura usada en este archivo:
#   Los 4 canales Corp (fuente: config/channels_config.json → hierarchy_nr_corp_detail):
#     1. OC + UCR    → UCRANIA E&G + OWN CHANNELS RECURRING + OWN CHANNELS ADHOC
#     2. POM         → ACQ POM + ACT POM + WEB POM + CTW POM
#     3. OTHERS      → MGM + L&P + UCR PRD + SEO + POM SELLERS + POM OTHERS
#                      ⚠️ MGM es sub-canal de OTHERS, NO es canal independiente en Corp
#     4. NO ATRIBUIDO → equivale a "Orgánico" en la vista estándar del dashboard
#
#   Al escribir datos, SIEMPRE aclarar si son de la vista estándar o vista Corp.
#
# ARQUITECTURA DE ACTUALIZACIÓN (leer antes de editar este archivo):
#
#   SECCIÓN A — DATOS 2025: CERRADOS. Año completo y definitivo.
#     → NO MODIFICAR bajo ninguna circunstancia.
#     → Fuente: docs/Weekly Adquisición MLM_2025_versionClaud.md (421 páginas)
#
#   SECCIÓN B — DATOS 2026: ABIERTOS. Actualizar mensualmente.
#     → CÓMO ACTUALIZAR cuando llega un nuevo mes:
#       1. Agregar una fila al final de la tabla §B1 (Performance Mensual 2026)
#       2. Agregar una fila al final de la tabla §B2 (Weekly Cuts 2026)
#       3. Actualizar §B3 (Estado Actual) con el nuevo corte más reciente
#       4. Agregar la sesión nueva a §B4 (Sesiones Semanales 2026)
#       5. NO reescribir nada anterior — solo APPEND
#     → Último dato disponible: MARZO 2026 (actualizado el 13-Abr-2026)
#     → Próxima actualización esperada: al recibir PDF Abril 2026
#
# COLUMNAS SIEMPRE PRESENTES EN TABLAS DE PERFORMANCE:
#   Total N+R | OC+UCR | UCR Gest | UCR PRD | OC ACT | POM TOTAL | POM ADQ |
#   POM ACT | MGM | LP&Partners | ORG | Período/Corte
#
# REGLA ANTI-ALUCINACIÓN:
#   Este archivo no inventa datos. Cada celda vacía (—) significa "dato no disponible",
#   no "dato cero". El skill debe respetar esta distinción.
#
# ==============================================================================

---

## SECCIÓN A — DATOS 2025 (CERRADOS — NO MODIFICAR)
# Fuente canónica: docs/Weekly Adquisición MLM_2025_versionClaud.md
# Última sesión cubierta: 28 Nov 2025

### A1 — Serie Histórica OC+UCR Mensual (Feb-25 → Dic-25)
# Esta serie es el BENCHMARK HISTÓRICO. Usarla para comparativos YoY.
# Fuente: Weekly 2025 §3.1, Monthly Mar-26 §7.2
# ⚠️ NOTA: Esta tabla contiene métricas de EFICIENCIA (Share%, CPA, ROAS, VPU, Inv.)
#    pero NO tiene N+R absolutos mensuales. Para calcular gap YoY (ej: "OC Mar-25 vs Mar-26"):
#    → Leer docs/Weekly Adquisición MLM_2025_versionClaud.md §3.1 (serie mensual completa)
#    Referencia rápida de orden de magnitud 2025: OC+UCR ~65K–174K N+R/mes
#    (H1 bajo: ~65–100K · H2 alto: ~140–174K · pico Nov D23: 159K según §A2)

| Mes | Share N+R Total | CPA Blended (USD) | CPA Paid (USD) | ROAS Paid | VPU (USD) | Inversión (M USD) |
|---|---|---|---|---|---|---|
| Feb-25 | 13.8% | 1.3 | 17.7 | 3.3 | 56.5 | 0.7 |
| Mar-25 | 16.8% | 1.0 | 21.9 | 2.7 | 53.2 | 0.9 |
| Abr-25 | 17.2% | 1.2 | 17.6 | 3.3 | 53.3 | 1.1 |
| May-25 | 14.3% | 1.6 | 15.2 | 3.8 | 59.7 | 0.6 |
| Jun-25 | 16.7% | 1.0 | 11.1 | 5.6 | 59.0 | 0.7 |
| Jul-25 | 19.0% | 0.7 | 7.6 | 7.6 | 56.1 | 0.8 |
| Ago-25 | 17.8% | **0.6** | **4.3** | **13.0** | 53.1 | 0.9 |
| Sep-25 | 17.9% | 0.73 | 5.17 | 10.5 | 49.6 | 1.0 |
| Oct-25 | 17.0% | 0.88 | 5.99 | 8.7 | 55.1 | 1.2 |
| Nov-25 | 16.2% | 1.69 | 9.25 | 5.3 | 58.2 | 1.2 |
| Dic-25 | 14.3% | — | 11.0 | 5.5 | 60.9 | 1.2 |

### A2 — Performance MTD por Sesión Semanal 2025 (cortes seleccionados D7)
# Fuente: Weekly 2025 §2 (tablas completas)

| Sesión / Corte | Total N+R | OC+UCR | UCR Gest | UCR PRD | OC ACT | POM TOTAL | POM ADQ | POM ACT | MGM | LP&P | ORG | % Total vs LMTD |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Nov W47 (23/Nov D7) | 792.114 | 159.450 | 50.536 | 5.974 | 89.114 | 96.838 | 54.290 | 42.548 | 11.168 | 17.739 | 509.584 | **+8.0%** |
| Nov W46 (22/Oct→Nov D7F) | 629.376 | 128.112 | 41.287 | 4.714 | 70.340 | 72.482 | — | — | 8.983 | 14.856 | 404.943 | **+7.2%** |
| Oct W43 (22/Oct D7F) | 707.458 | 152.609 | 45.129 | 5.256 | 91.011 | 85.487 | — | — | 11.110 | 12.536 | 445.716 | **+3.8%** |
| May W2 (16/May D0) | 269.265 | 31.206 | — | — | — | 15.737 | — | — | 3.023 | 1.820 | 217.479 | **-5.7%** |
| May fin (30/May D0) | 751.596 | 92.353 | — | — | — | 49.753 | — | — | 8.237 | 5.622 | 595.630 | **+1.3%** |
| Jul W2 (13/Jul D7) | 347.170 | 61.021 | — | — | — | 30.956 | — | — | 3.405 | 2.807 | 248.981 | **-1.2%** |

### A3 — POM Performance Mensual 2025
# Fuente: Weekly 2025 §5.3, Monthly Mar-26 §8.2

| Mes | N+R POM | CPA (USD) | ROAS | Inversión | VPU | Nota |
|---|---|---|---|---|---|---|
| Ene-25 | ~85K | 14.5 | 3.89 | $1.11M | — | CPM -20% estacional aprovechado |
| Feb-25 | ~84K | ~14 | ~3.8 | ~$1.1M | — | CPM vuelve a niveles normales |
| Mar-25 | ~90K | ~13 | ~4.0 | ~$1.1M | — | — |
| Jun-25 | 48.2K (D0) | ~14 | — | — | — | — |
| Jul-25 | 76.5K | 14.5 | 3.89 | $1.11M | — | — |
| Oct-25 | 85.5K | ~14.5 | ~3.9 | — | 49-54 | — |
| Nov-25 | 96.8K | — | — | — | — | — |

### A4 — ACT Total Q1 2025 (evolución trimestral)
# Fuente: Weekly 2025 §S08, Monthly Mar-26 §7.1

| Métrica | Ene-25 | Feb-25 | Mar-25 | Mar vs Ene |
|---|---|---|---|---|
| Sents | 53.5M | 51.5M | 56.2M | +5% |
| N+R | 69K | 65K | 83K | **+20%** |
| N+R/Sents | 0.13% | 0.13% | 0.15% | +14% |
| Valor | $3.8M | $3.4M | $4.3M | +13% |
| VPU | $54.5 | $52.2 | $51.6 | -5% |
| CPA Paid | $8.2 | $8.3 | $9.0 | +10% |
| ROAS | 9.54 | 6.52 | 9.45 | -1% |

### A5 — Benchmarks de Incentivos (tests ejecutados 2025)
# Fuente: Weekly 2025 §9.2, §12.2

| VP | Configuración | Lift | CPA (USD) | ROAS | Canal |
|---|---|---|---|---|---|
| Money In | Ingresa $125 MXN, CBK $100 MXN | 0.06% | 4.8 | **10.5** | Push UCR |
| Money In | Ingresa $200, CBK $150 | 0.32% | 9.5 | 5.8 | Push UCR |
| Money In | Ingresa $300, CBK $200 | **0.35%** | 10.6 | 5.2 | Push UCR |
| Descuento ML | Cupón Simple $100 OFF | 0.04% | 2.4 | **15** | Push UCR |
| Descuento ML | Cupón Automático $100 OFF | 0.06% | 16.0 | 3 | Push UCR |
| Servicios/Pagos | Paga $150, CBK $100 | 0.03% | 0.6 | **111** | Push UCR |
| Recargas | Max $40 OFF | 0.06% | 0.8 | 56 | Push UCR |
| Recargas | Max $100 OFF | **0.10%** | 5.2 | 10.4 | Push UCR |
| Pandora DRW | $6 flat (Jul-25) | — | $4.2 | — | Pandora |
| Pandora Quincena | 15% OFF (Oct-25) | — | **$1.4** | — | Pandora |
| Incentivo 50% | TDD 50% descuento (Ene-26) | — | $7.9 | — | POM |
| Cashback 10% | CBK 10% TDD (Ene-26) | — | **$7.2** | — | POM |

### A6 — Benchmarks Pandora 2025
# Fuente: Weekly 2025 §4

| Audiencia | CVR ML | CVR MP | Mejor para |
|---|---|---|---|
| NEVER BUYER | 1.30% | 0.47% | Mayor incremental ecosistémico |
| RECOVERED | 44.89% | 1.05% | Balance volumen/eficiencia |
| NEW | 25.10% | **1.71%** | Mejor CVR MP |
| CHURNED | 0.44% | 0.22% | Alta propensión estacional |
| LATENT | 0.44% | 0.27% | Bajo performance |
| Carrito abandonado | — | — | **3x conversión** vs batch |

**Pandora — reglas operativas validadas 2025:**
- Descuento % > monto $ en +26% N+R. Mínimo $2 USD, máximo $6 USD.
- CPA histórico constante: **~$2.0 USD** (el mejor del portafolio).
- CPA en seasonal (BF, HS): ~$10 USD → **NO ejecutar Pandora en seasonals**.
- Calibrador 2025: osciló 0.2–1.0. Shocks de -7K NR/semana cuando baja.

### A7 — RE UCR Sub-canales (eficiencia histórica 2025)
# Fuente: Weekly 2025 §3.2

| Sub-canal | Share NR | Eficiencia pico (NR/print) | Tasa Activación pico |
|---|---|---|---|
| DRW (Drawer) | 20–38% | 0.070% (May-25) | 28.7% |
| QA (Quick Access) | 10–20% | 0.003% (estable) | 26.4% |
| DB (Discovery Banner) | 0–4% | 0.051% (lanzamiento) | 21.9% |
| CONG (Congrats) | ~1% | 0.009% | 32.9% |

**Atribución DRW (Cross App Links → installs UCR OC) — tendencia:**
| Fuente | Sep-25 | Oct-25 | Nov-25 | Dic-25 | Ene-26 | Variación total |
|---|---|---|---|---|---|---|
| Cross App Links UCR OC | 68.60% | 65.74% | 67.89% | 63.04% | **60.42%** | **-8.18pp** |
| Facebook Installs | 7.03% | 10.67% | 10.17% | 11.48% | 13.22% | +6.19pp |

### A8 — Análisis Quincenas 2025 (Ene–Jun 25)
# Fuente: Weekly 2025 §8.2, §8.3

| KPI | Quincena | Valle | Delta % |
|---|---|---|---|
| Installs Share | 51.24% | 48.76% | +2.52% |
| N+R CVR | 45.83% | 43.52% | **+2.30%** |
| New Users CVR | 26.32% | 24.59% | +1.73% |
| TPV | $746M | $574M | **+29.88%** |
| Ticket Promedio | $592 | $447 | +32.46% |

### A9 — Mantika — Estado del modelo 2025
# Fuente: Weekly 2025 §3.3

| Métrica | Valor |
|---|---|
| % Reach audiencia única mensual | 82% |
| Pushes/mes/usuario | 2.49 |
| Navegaciones/mes/usuario en ML | 7 |
| Lift usuarios navegantes vs no-navegantes | **2x** |
| Reach navegantes antes del 13-Feb-26 | 55% |
| Reach navegantes después del 13-Feb-26 | **75%** (cambio de regla) |
| Usuarios UCR sin opt-in Push | 3.7M |
| Señal de saturación | 5 pushes → 5% OR (punto de quiebre) |
| NR concentrado en Money In Paid | ~80% (señal de techo) |

### A10 — Hub de Newbies (experimento Oct-Nov 2025)
# Fuente: Weekly 2025 §7.4, Weekly Mar-26 §7

| KPI | Control | Test | Lift % | Users Inc. |
|---|---|---|---|---|
| Activación | 49.4% | 50.8% | +2% | — |
| Emisión TD | 37.9% | 41.3% | +7.1% | 5K |
| **Vinculación TD** | 30.6% | 33.4% | **+9.1%** | **11K** |
| Activación TD | 28.2% | 30.2% | +7.1% | 7.8K |
| Retención M3 | 61.8% | 62.3% | +1% | 1.7K |
| Money In | 43.3% | 45.0% | +3.7% | 6.2K |

**Resultado**: Rollout 100% de base. Dato de contexto: hábito = +20pp retención M3 vs no habituado.

### A11 — X-Channel Analysis 2025 (Curvas AUC W29)
# Fuente: Weekly 2025 §11

| Métrica | OC (E&G) | POM | Implicación |
|---|---|---|---|
| Inversión real W29 | $154K (39%) | $240K (61%) | E&G subdotado |
| CPA Breakeven | **$18.3 USD** | ~$20 USD | OC más eficiente |
| CPA Marginal Máx | **$27.5 USD** | — | — |
| ROAS Paid | 5.3–13.0 (rango 2025) | 3.6–4.0 | OC mejor ROAS |

Escenario reasignación 58% OC / 42% POM → **+12–16K NR/mes** adicionales.

### A12 — POM Plan 2025 vs 2024
# Fuente: Weekly 2025 §5.1

| Métrica | 2024 Real | 2025 Plan | YoY |
|---|---|---|---|
| Valor (USD) | $39.0M | $56.7M | **+45%** |
| Inversión (USD) | $10.2M | $15.6M | +53% |
| ROAS | 3.8 | 3.6 | -5% |
| N+R (K) | 684 | 927 | **+36%** |
| CPA (USD) | $14.9 | $16.8 | +13% |
| Web share POM (MLM) | 3% (Dic-24) | — | → **24%** (Dic-25) |

### A13 — Seasonals Impacto en OC/POM 2025
# Fuente: Weekly 2025 §8

| Seasonal | Período | Impacto en OC | Impacto en POM |
|---|---|---|---|
| Quincena (cualquier mes) | 14-16 y 29-31/1 | Pandora CPA $1.4 USD | — |
| Hot Sale / Double Días | May-Jun | Pandora CPA $10 USD → NO usar | Incentivos +24% share NR |
| LCDLF | Ago–Oct 25 | Awareness masivo, UCR VPs TDD/TDC/CC | Mass media + digital |
| Buen Fin | Nov (última semana) | DRW +24% NR; QA -16% NR | CPM -30% → escalar inv. |
| Enero post-estacional | Ene | Pool reducido + saturación Q4 | CPM -20% → escalar +30% |

### AE1 — Calendario Comercial México + Impacto Mercado Pago (permanente)
# Fuente: §A1,A3,A6,A8,A13 + conocimiento estructural del mercado
# PERMANENTE: Solo actualizar si hay nuevo evento validado con datos reales.
# CLAVE: Relacionar SIEMPRE eventos con su efecto cuantificado en NR, CPA y CPM.

| Mes | Evento(s) clave México | Relevancia MP | Impacto en OC+UCR | Impacto en POM | Alerta operativa |
|---|---|---|---|---|---|
| **Enero** | Post-estacional · Quincenas normales | CPM -20% estacional | IS ≈ 0.82 · pool reducido (saturación Q4) · arranque lento | **IS ≈ 1.05** · escalar inv +30% sobre CPM barato | Pandora: evitar (pool saturado); POM: ESCALAR |
| **Febrero** | Día del Amor y Amistad (14 Feb) | TDD/pagos en pareja | IS ≈ 0.86 · campaigns TDD oportunidad | IS ≈ 0.88 · sin impacto mayor | CPA estable; buen momento para test de VP |
| **Marzo** | Sin evento mayor | Recuperación gradual | IS ≈ 0.95 · más días de prints vs Feb (+3 días) | IS ≈ 0.92 · normalización | Efecto calendario: Mar > Feb siempre +3 días |
| **Abril** | Semana Santa / Pascua (varía 1-2 sem) | Caída consumo digital | IS ≈ 0.88 · semana de viaje = sin activación | IS ≈ 0.85 · CPM sube por competencia | Semana Santa: pausa o reduce inversión ambos canales |
| **Mayo** | Día de las Madres (10 May) + Hot Sale (última sem May) | Pico e-commerce H1 | IS ≈ 0.87 · **Pandora CPA $10 → NO USAR** (vs $2 normal) | **IS ≈ 1.15** · inversión +24% share NR · escalar POM | HOT SALE: OC debe pausar Pandora; POM debe escalar |
| **Junio** | Hot Sale overflow (1ra sem) + Double Days | Post-pico e-commerce | IS ≈ 0.88 · estabilización | IS ≈ 1.05 · overflow Hot Sale | Primer semana junio: mantener POM escalado |
| **Julio** | Vacaciones de verano | CPM caro + usuarios dispersos | IS ≈ 1.02 · CRM directo resiste mejor | IS ≈ 0.90 · CPM alto quita eficiencia | POM: reducir inversión en julio; OC: mantener |
| **Agosto** | Inicio LCDLF (11 sem Ago–Oct) + Back to School | Awareness masivo | **IS ≈ 1.15** · OC pico H2 · ROAS 13x (Ago-25) | IS ≈ 1.05 · awareness +NR | ESCALAR OC en agosto — mejor mes del año históricamente |
| **Septiembre** | LCDLF peak + Independencia (15-16 Sept) | Festividad + LCDLF en cumbre | **IS ≈ 1.09** · quincena 1ra más fuerte | IS ≈ 1.05 · awareness | 15-16 sept = festivo = día D0 cae; compensar D6 y D8 |
| **Octubre** | LCDLF cierre + preparación Buen Fin | Pre-Buen Fin | IS ≈ 1.03 · estable | IS ≈ 1.02 · preparación | CPM empieza a bajar → oportunidad POM |
| **Noviembre** | **BUEN FIN** (3ra sem Nov) + Black Friday | Pico absoluto del año | IS ≈ 1.00 · DRW +24% NR · **Pandora CPA $10 → NO USAR** | **IS ≈ 1.20+** · CPM -30% · pico absoluto POM | BUEN FIN = POM escala masivo; OC: solo DRW; NO Pandora |
| **Diciembre** | **Aguinaldo** (sem 1-2 Dec) + Navidad | Pico TPV · pool se satura | IS ≈ 0.87 · share 14.3% · post-BF saturación | IS ≈ 0.95 · CPM sube (publicidad navideña) | Aguinaldo = pico TPV pero NR cae (ya activados en BF) |

**IS = Índice de Estacionalidad** = NR_canal_mes / NR_canal_promedio_anual
(IS > 1.0 = mes sobre el promedio; IS < 1.0 = mes bajo el promedio)
Fuente IS OC+UCR: derivado de share% §A1 con promedio anual ≈ 16.5%. Fuente IS POM: §A3.

---

### AE2 — Índices de Estacionalidad Mensuales por Canal (2025 histórico)
# Fuente: §A1 (OC+UCR share%), §A3 (POM NR), §B1 (2026 absolutos)
# NOTA METODOLÓGICA:
#   IS OC+UCR = calculado desde share% (§A1) usando promedio anual ≈ 16.5%
#   IS POM    = calculado desde NR absoluto (§A3) usando promedio anual estimado ≈ 85K NR/mes (2025)
#   IS 2026   = calculado desde §B1 usando promedio Q1-26 ≈ 135K OC / 197K POM
#   [Estimado] = derivado de interpolación, no dato directo del contexto

| Mes | IS OC+UCR (2025) | IS POM (2025) | IS OC+UCR (2026 Q1) | IS POM (2026 Q1) | Patrón dominante |
|---|---|---|---|---|---|
| Enero | **0.84** | 1.00 | **0.82** | **1.05** (CPM -20%) | OC bajo / POM oportunidad |
| Febrero | 0.84 | 0.99 [est.] | 0.86 | 0.94 | Ambos bajo promedio |
| Marzo | 1.02 | 1.06 [est.] | 1.00 | 1.04 | Recuperación |
| Abril | [est. 0.88] | [est. 0.90] | — | — | Semana Santa dip |
| Mayo | **0.87** | **1.15** | — | — | Hot Sale = POM sube, OC no |
| Junio | 1.01 | [est. 1.05] | — | — | Overflow Hot Sale |
| Julio | 1.02 [D7] | **0.90** | — | — | OC estable, POM cae |
| Agosto | **1.15** | 1.05 [est.] | — | — | LCDLF = OC pico |
| Septiembre | **1.09** | 1.05 [est.] | — | — | LCDLF + Indie |
| Octubre | 1.03 | 1.01 | — | — | Pre-BF normal |
| Noviembre | 0.98 | **1.14** | — | — | Buen Fin = POM > OC |
| Diciembre | **0.87** | 0.95 [est.] | — | — | Post-BF saturación |

**Tendencia estructural confirmada**:
- OC+UCR tiene **pico estacional Jul–Sep** (LCDLF + CRM directo resiste mejor al verano)
- POM tiene **pico estacional Nov** (Buen Fin) y **oportunidad de Enero** (CPM barato)
- Ambos tienen **valle en Ene–Feb** (post-estacional Q4)
- Hot Sale (Mayo): **divergencia** — POM sube, OC cae (por prohibición de Pandora en seasonal)

---

### AE3 — Patrón Intra-Mensual: Quincenas y Semanas
# Fuente: §A8 (Quincenas Ene–Jun 25), §A6 (Pandora quincena CPA $1.4)
# QUINCENA = días 14-16 y 29-31 de cada mes (pago de salario quincenal en México)
# Impacto directo en TPV, activación de tarjeta y N+R

**Efecto Quincena vs Valle (datos §A8, Ene–Jun 2025)**:
| KPI | Quincena (días 14-16 y 29-31) | Valle (resto) | Delta |
|---|---|---|---|
| Installs Share | 51.24% | 48.76% | +2.52pp |
| N+R CVR | 45.83% | 43.52% | **+2.30pp** |
| New Users CVR | 26.32% | 24.59% | +1.73pp |
| TPV | $746M | $574M | **+29.88%** |
| Ticket Promedio | $592 | $447 | +32.46% |

**Regla de quincena para campañas**:
- Pandora en quincena: CPA **$1.4 USD** (vs $2.0 promedio = -30% más eficiente) → SIEMPRE activar
- Push en quincena: mayor propensión a activar TDD (usuarios reciben pago → mayor intención)
- POM en quincena: menor impacto diferencial (medios pagados no están tan sincroniozados con quincena)

**Patrón Semanal dentro del mes** (estimado de D7 cuts en §B2):
| Semana del mes | Días | NR típico % del mensual | Comportamiento |
|---|---|---|---|
| Semana 1 (D1–D7) | 1–7 | ~18–22% | Arranque lento; usuarios "resetting" post-quincena |
| Semana 2 (D8–D14/16) | 8–16 | ~28–32% | Pico quincena 1 (D14-16) |
| Semana 3 (D17–D22) | 17–22 | ~20–24% | Valle inter-quincenal |
| Semana 4+ (D23–fin) | 23–31 | ~26–30% | Pico quincena 2 (D29-31) |

*Fuente: interpolado de cortes D7 en §B2 (4-Feb: 23.5K = ~17% de Feb-26 total de 185.9K;
 16-Feb: 107K = ~77% del mes para D16 → implica fuerte aceleración en semana 2 y 3)*

---

### AE7 — Patrón Semanal dentro del Mes — IS por Semana
# Fuente: §A8 (efecto quincena CVR +2.3pp), §B2 (cortes acumulados Feb-26), razonamiento estructural
# IS_semanal = NR_semana / NR_promedio_semanal_mensual
# DATO CONFIRMADO: quincena boost (§A8). ESTIMADO [est]: distribución exacta por semana.

| Semana | Días | IS_semanal [est] | Driver principal | Implicación operativa |
|---|---|---|---|---|
| **S1** (D1–D7) | 1–7 | **0.75–0.82** | Post-quincena 2 del mes anterior. Usuarios "reseteando". | Inversión mínima. Testear, no escalar. |
| **S2** (D8–D16) | 8–16 | **1.20–1.30** | **Quincena 1 (D14-16)**: CVR +2.3pp · Pandora CPA $1.4 · TPV +30% (§A8) | PICO del mes. Escalar TODOS los canales OC. Pandora siempre activa. |
| **S3** (D17–D22) | 17–22 | **0.88–0.95** | Valle inter-quincenal. Usuarios gastaron, esperando siguiente pago. | Reducir inversión vs S2. Mantener Always On base. |
| **S4+** (D23–fin) | 23–fin | **1.05–1.15** | **Quincena 2 (D29-31)**: segundo pico, algo menor que S2 | Escalar en D28-31. Pandora activa. |

**Validación con datos Feb-26 (§B2)**:
- D1–D4: 15,794 OC+UCR = 11.7% del mes → IS_diario ≈ 0.58 (arranque muy lento)
- D1–D16: 73,733 = 54.5% del mes → D5–D16 = 42.8% en 12 días → IS_diario ≈ 0.88 (con quincena 1 incluida)
- D1–D23: 120,514 = 89.1% del mes → D17–D23 = 34.6% en 7 días → IS_diario ≈ 1.23 [¹]
- D24–D28: 14,822 = 10.9% → IS_diario ≈ 0.54 (febrero sin quincena 2 real — mes de 28 días)

[¹] El alto IS de D17-23 en feb-26 puede reflejar la aceleración post-quincena 1 que se concentra en la 3ra semana. Febrero 2026 fue IS mensual 0.86 (bajo) — interpretar con cautela como mes atípico de Q1.

**Patrón confirmado**: S2 (quincena 1) domina. S1 es el hoyo del mes. En meses de 31 días, S4 tiene segunda cima real.

---

### AE8 — Patrón Día de la Semana (DoW) por Tipo de Canal
# Fuente: benchmarks industria LATAM [inf] + estructura de cada canal. Sin datos D-nivel propios de MLM.
# IMPORTANTE: Los patrones DoW son INFERENCIAS ESTRUCTURALES marcadas [inf].
#   Para validar con datos reales: ejecutar query BQ por DAYOFWEEK(FECHA_DIARIA) × CANAL × NR_USERS
# Escala de confianza: ★★★ alta (industria estándar) · ★★ media · ★ baja (canal nuevo/variable)

| Día | EMAIL (OC) | PUSH UCR/ACT | PANDORA | RE (DRW/QA) | WPP UCR | TikTok POM | Google POM | Meta POM |
|---|---|---|---|---|---|---|---|---|
| **Lunes** | Malo (limpieza inbox) | Bueno (vuelta trabajo) | Bueno (ML activo) | Bueno (nav ML↑) | Regular | Regular | Bueno (intent↑) | Regular |
| **Martes** | **Muy bueno ★★★** | Muy bueno | Muy bueno | Muy bueno | Bueno | Regular | Muy bueno | Bueno |
| **Miércoles** | **Muy bueno ★★★** | Muy bueno | Muy bueno | Muy bueno | Bueno | Regular | **Mejor DoW ★★★** | Bueno |
| **Jueves** | Bueno | Bueno | Bueno | Bueno | Bueno | Bueno | Bueno | Bueno |
| **Viernes** | Regular | Regular (↓tarde) | Regular | Regular | Regular | Bueno (ocio↑) | Regular | Bueno |
| **Sábado** | Malo ★★★ | Malo (OR↓ 40%) | Malo (ML nav↓) | Malo | **Bueno ★★** | **Muy bueno ★★★** | Malo | **Muy bueno ★★★** |
| **Domingo** | Malo ★★★ | Malo (OR↓ 50%) | Malo | Malo | **Muy bueno ★★** | **Muy bueno ★★★** | Malo | **Muy bueno ★★★** |

**La paradoja del fin de semana** [inf]:
- Canales CRM (EMAIL, PUSH, PANDORA, RE): Peor Sáb-Dom porque el usuario de ML está menos activo en navegación transaccional.
  El OC+UCR depende de que el usuario esté en "modo comprar/pagar en ML" → menor en fines de semana.
- Canales POM social (TikTok, Meta): Mejor Sáb-Dom en REACH (entretenimiento), pero OJO:
  mayor reach no garantiza mayor conversión para productos financieros.
  Un usuario browsing TikTok el sábado no necesariamente está en "modo activar tarjeta".

**Implicación scheduling [inf]**:
- EMAIL OC: enviar Martes o Miércoles 7–9am o 11am–1pm. Evitar Viernes, Sábado, Domingo.
- PUSH UCR: enviar Lunes–Jueves. Mejor horario: 8am o 6-7pm (rutinas). Evitar fines de semana.
- PANDORA: activar Lunes–Viernes cuando ML tiene tráfico. Bajar budget Sábado-Domingo.
- RE (DRW/QA): correlaciona con navegación ML → mismos días que ML shopping (Lunes-Viernes).
- WPP UCR: inverso a los demás — Sábado-Domingo funciona mejor (mensajería personal, tiempo libre).
- TikTok/Meta POM: Viernes-Domingo más reach, pero validar conversión incremental. Martes-Jueves mejor CPM/clic.

---

### AE9 — Estacionalidad por Sub-canal y Medio OC+UCR
# Fuente: §AE1–§AE8 aplicados a cada sub-canal. [inf] = inferencia estructural. [dato] = confirmado en §A.
# Cobertura: UCRANIA E&G y OWN CHANNELS RECURRING (principales sub-canales corp de OC+UCR)

| Sub-canal/Medio | Patrón Mensual (IS) | Mejor Semana del Mes | Mejor DoW | Campaña/Evento crítico | Regla operativa clave |
|---|---|---|---|---|---|
| **EMAIL** (UCR E&G + RECURRING) | IS similar al canal (Jul↑, Ene↓) | S2 (D14-16 quincena) | **Mar-Mié** ★★★ | Hot Sale: emails de oferta funcionan bien [inf]. Buen Fin: informativo | Enviar Mart-Miér 8am o 11am. EVITAR Vie-Dom. Base: 2 envíos/semana max [dato §A9 saturación] |
| **PUSH** (UCR E&G + RECURRING) | Fuerte correlación con IS del canal | **S2 D14-16** (quincena máx) | **Lun-Jue** ★★★ | Quincena: CPA $1.4 [dato §A6]. LCDLF: audiences ampliadas. Buen Fin: pausa [dato §AE5] | 2.49 pushes/mes/usuario (§A9). >5 pushes = 5% OR (punto quiebre). Quincenas: 1 push extra siempre. |
| **PANDORA** (UCR E&G + RECURRING) | **Muy estacional**: IS 1.15+ en S2 quincena; IS 0.10 en Hot Sale/BF | **S2 quincena D14-16 y D29-31** | **Lun-Vie** ★★ | CPA $1.4 quincena [dato §A6]. CPA $10 Hot Sale/BF [dato §A6]. LCDLF: IS moderado positivo | **Regla absoluta**: Pandora SIEMPRE en quincenas; NUNCA en Hot Sale/Buen Fin. Mayor variación CPA por evento del portafolio. |
| **REAL ESTATES — DRW** | Sigue IS canal con amplificación en Buen Fin | S2 + Buen Fin (DRW +24% NR) | **Mar-Jue** ★★ | **Buen Fin: +24% NR** [dato §A13]. Impacto en DRW > que en Pandora para seasonals. | DRW correlaciona con ML tráfico → escalar cuando ML traffic es alto. Mejor placement de Seasonals. |
| **REAL ESTATES — QA** | IS moderado, menos volátil que DRW | S2 | Mar-Jue ★★ | Buen Fin: **-16% NR** [dato §A13] — QA cae en Buen Fin mientras DRW sube | No escalar QA en Buen Fin. Redirigir budget QA → DRW en esa semana. |
| **REAL ESTATES — DB** | Volátil (lanzamiento 2025, pocos datos) | S2 estimado | Lun-Vie [inf] | Lanzamiento May-25: NR/print 0.051% (§A7). Potencial no desarrollado. | Monitor performance antes de escalar. Datos históricos limitados. |
| **WPP** (UCR E&G) | En construcción (Q2-26 launch) | S4 estimado (mensajería Sáb-Dom) | **Sáb-Dom ★★** | Nuevo canal (§C4 O9: +25-30K NR/mes). Sin histórico completo. | Canal inverso a Push: mejor Sáb-Dom. Test antes de escalar. Validar con datos Q2. |
| **JOURNEY** (RECURRING) | Evento-driven (no seasonal puro) [inf] | Depende del trigger | Variable | Triggered por comportamiento → menos sensible a estacionalidad | Mantener activo todo el año. Revisar reglas de activación en LCDLF para aprovechar awareness. |

**Sub-canales POM por tipo de campaña** [inf + §B5a]:
| Sub-canal POM | Mejor Período Mensual | Mejor DoW | Campaña crítica | Nota |
|---|---|---|---|---|
| **TikTok ACQ** | Ene (CPM -20%), Buen Fin (+reach) | Vie-Dom (reach) | Hot Sale: oportunidad; calibrador en revisión (§B5a) | Calibrador 1.35 actual — validar incrementalidad antes de escalar |
| **TikTok ACT** | Ene, Hot Sale, Buen Fin | Vie-Dom | Scale-up Q1-26: +16% NR con +46% inv (§B3) | Canal en crecimiento activo. Escalar con prioridad. |
| **Google iOS** | Ene (CPM -20%), todo el año estable | Lun-Jue | Señal muy positiva W01-26 (§B5a) | VPU +70% vs Android. Sub-invertido. |
| **Meta ACQ/ACT** | Ene, Buen Fin, Hot Sale | Vie-Dom | Double Days con VP % (§C2: % > monto fijo) | Creativos visuales → VP porcentual siempre mejor |
| **Web POM** | Estable (3%→24% share Dic-25 — §A12) | Lun-Vie [inf] | Landing sin formulario +47% CTR (§C2) | CTR regla validada. Sin estacionalidad fuerte propia. |

---

### AE4 — Patrón de Días Especiales en el Año
# Reglas operativas validadas para scheduling de campañas

| Fecha / Período | Tipo | Acción recomendada OC+UCR | Acción recomendada POM |
|---|---|---|---|
| Enero 1–15 | Post-estacional | Volumen bajo, VP ligeros, testear audiencias nuevas | +30% inversión (CPM -20%) |
| 14 Febrero | Día Amor/Amistad | Campaign TDD/pagos en pareja | — |
| 10 Mayo (aprox) | Día Madres | Push + WPP con VP regalo digital | Escalar early (pre-día) |
| Última sem Mayo | Hot Sale | **PAUSAR Pandora** (CPA $10) · escalar DRW/RE | Máxima inversión del H1 |
| 15–16 Sept | Independencia | Pausa D0 (festivo); recuperar D+1 | Pausa esa semana si CPM sube |
| 1ra–2da sem Nov | Pre-Buen Fin | Acumular audiencia, no escalar aún | Preparar creativos y presupuesto |
| 3ra sem Nov | Buen Fin | DRW escala; **PAUSAR Pandora** (CPA $10) | **MÁXIMA INVERSIÓN del año** · CPM -30% |
| 1–15 Diciembre | Aguinaldo 1 | Push fuerte (usuarios con efectivo) | Mantener, CPM sube post-BF |
| 15–31 Diciembre | Aguinaldo 2 + Nav | Pool saturable; VP navideños ligeros | Reducir (CPM navideño +40%) |
| Días 14–16 (cualquier mes) | Quincena 1 | **Pandora CPA $1.4** (vs $2.0) → SIEMPRE | Minor boost |
| Días 29–31 (cualquier mes) | Quincena 2 | **Pandora CPA $1.4** → SIEMPRE | Minor boost |

---

### AE5 — Campañas Internas Mercado Pago/MeLi + Impacto en N+R (datos reales)
# Fuente: §A13, §B4, Weekly 2025 §8, Monthly Mar-26 §10, docs/BI docs
# ESTAS SON LAS CAMPAÑAS CON MAYOR IMPACTO DOCUMENTADO EN EL CANAL
# Actualizar con cada nuevo ciclo si hay datos de impacto validados.

#### LCDLF — La Cultura Del Lleno Financiero (Ago–Oct, 11 semanas)
| Dato | Valor | Fuente |
|---|---|---|
| Período | Agosto–Octubre (11 semanas) | §A13 |
| Tipo | Awareness masivo + digital | §A13 |
| Impacto OC+UCR | **IS ≈ 1.15** en Ago · IS ≈ 1.09 en Sep · IS ≈ 1.03 en Oct | §AE2 |
| Impacto POM | Moderado — LCDLF es mainly OC/brand | §A13 |
| Canales beneficiados | UCR E&G (awareness → push → activación), OC ACT | §A13 |
| VPs asociados | TDD, TDC, CC (tarjeta de crédito) — awareness de producto | §A13 |
| Efecto MoM | Ago > Jul en ~25% para OC+UCR | §AE2 derivado |
| **Regla operativa** | ESCALAR OC+UCR en LCDLF. Es el mejor período del año para E&G. | validado |

#### HOT SALE (última semana Mayo + 1ra sem Junio)
| Dato | Valor | Fuente |
|---|---|---|
| Período | Última sem Mayo + 1ra sem Junio (varía) | §A13 |
| Tipo | Evento e-commerce masivo (descuentos, campañas) | §A13 |
| Impacto OC+UCR | **NEGATIVO para Pandora**: CPA $2→$10 (+400%). **Positivo en RE/DRW** | §A6, §A13 |
| Impacto POM | **POSITIVO**: inversión +24% share NR en Hot Sale (POM beneficia del inventario) | §A13 |
| IS OC+UCR Mayo | 0.87 (abajo del promedio) — Pandora apagada pesa en el total | §AE2 |
| IS POM Mayo | 1.15 (pico H1 para POM) | §AE2 |
| **Regla operativa** | HOT SALE = PAUSA Pandora OC. ESCALA POM. Compensar con RE DRW en OC. | validado |

#### BUEN FIN (3ra semana Noviembre)
| Dato | Valor | Fuente |
|---|---|---|
| Período | 3ra semana de Noviembre (Thu–Sun) | §A13 |
| Tipo | El evento más grande del año en e-commerce México | §A13 |
| Impacto OC+UCR | DRW **+24% NR** · QA **-16% NR** · Pandora CPA $10 → NO USAR | §A13 |
| Impacto POM | CPM **-30%** → mayor eficiencia · pico absoluto del año · IS ≈ 1.20+ | §A13, §AE2 |
| Comparativa CPA POM | Buen Fin: CPA ~$12 (vs $14-15 promedio) = eficiencia por CPM barato | §A3 derivado |
| IS POM Noviembre | **1.14** (confirmado, §A3 Nov-25: 96.8K vs ~85K avg) | §A3 |
| IS OC+UCR Noviembre | 0.98 (moderado — Pandora apagada compensa el boost de DRW) | §AE2 |
| **Regla operativa** | BUEN FIN = POM MÁXIMA INVERSIÓN. OC: solo DRW escalado, NO Pandora. | validado |

#### JDV — Juego de Voces (campaign branding/seasonal MP)
| Dato | Valor | Fuente |
|---|---|---|
| Tipo | Campaign de branding/voz de MP (awareness) | Weekly Mar-26 (mencionado) |
| Impacto en N+R | Indirecto — genera pool de audiencia para activación posterior | [Inferencia de contexto] |
| Relación con OC | Awareness → mayor receptividad a push en días posteriores | [Inferencia] |
| **Dato disponible** | Mencionado en Weekly 2026 pero sin datos cuantificados en contexto actual | docs BI |
| **⚠️ Si se requiere profundidad** | Leer `docs/2026_MLM_ACQWeekly_AOMar2026_versionClau.md` §campañas | skill PASO_1 |

#### Double Days / Seasonal Days (varios — Hot Sale, World Cup TDC, etc.)
| Dato | Valor | Fuente |
|---|---|---|
| Tipo | Días de descuentos amplificados (ej: TDD 50% OFF, TDC 2x puntos) | §A5, Weekly 2026 |
| Impacto OC+UCR | Push con VP específico (TDD, CC) → lift variable 0.04%–0.35% | §A5 |
| Impacto POM | CPM puede subir si muchos competidores activos simultáneamente | [estructural] |
| **Regla operativa** | Double Days con VP de % > VP de monto fijo (+26% NR validado, §A6, §C2) | §C2 |

#### QUINCENAS (cada mes, días 14-16 y 29-31)
# No son campañas MP sino el ciclo de pago salarial de México
| Dato | Valor | Fuente |
|---|---|---|
| Frecuencia | 2x por mes, todos los meses del año | §A8 |
| Impacto N+R CVR | **+2.30pp** vs valle (45.83% vs 43.52%) | §A8 |
| Impacto TPV | **+29.88%** vs valle ($746M vs $574M) | §A8 |
| Pandora CPA en quincena | **$1.4 USD** (vs $2.0 promedio = -30% más eficiente) | §A6 |
| **Regla operativa** | SIEMPRE activar Pandora en quincenas. Es el mejor CPA del año fuera de seasonals. | §A6 validado |

---

### AE6 — Matriz de Decisión Estacional por Canal
# Lookup rápido: ¿qué hacer con cada canal en cada evento?
# Fuente: síntesis de §AE1–§AE5

| Evento / Período | OC+UCR (E&G) | OC ACT | POM | OTHERS/MGM |
|---|---|---|---|---|
| **Enero (CPM -20%)** | Bajo volumen · focus en test | Bajo volumen | **ESCALAR +30%** inversión | Estable |
| **Hot Sale (Mayo)** | **PAUSAR Pandora** · escalar DRW | Mantener | **ESCALAR** · pico H1 | Estable |
| **Buen Fin (Nov 3ra sem)** | DRW +24% · **PAUSAR Pandora** | Mantener | **MÁXIMA INVERSIÓN** · CPM -30% | Estable |
| **LCDLF (Ago–Oct)** | **ESCALAR** · mejor período del año | Escalar ACT | Mantener | Escalar MGM si hay budget |
| **Semana Santa (Abr)** | Reducir | Reducir | Reducir · CPM sube | Reducir |
| **Quincenas (14-16, 29-31)** | **Pandora $1.4 CPA** · ALWAYS ON | Escalar push | Minor boost | Minor boost |
| **Aguinaldo (1-15 Dic)** | Push fuerte TDD/pagos | Push fuerte | Mantener · CPM sube | Estable |
| **Post-Buen Fin (Dic 2da)** | Reducir · pool saturado | Reducir | Reducir · CPM navideño +40% | Reducir |

---

### A14 — Riesgos Estructurales Identificados 2025
# Fuente: Weekly 2025 §18

| ID | Riesgo | Impacto NR | Estado en Dic-25 |
|---|---|---|---|
| R1 | Canibalización QA-BNPL (-29% prints, -5K NR/mes) | -5K/mes | Sin resolver |
| R2 | Atribución DRW cayendo -8pp acumulado (sep-25→ene-26) | Medición | En revisión |
| R3 | Pandora calibrador volátil (shocks -7K NR/semana) | -7K max. sem. | Recurrente |
| R4 | Mantika en techo (80% en MYI Paid) | Saturación | En rediseño |
| R5 | iOS sin inversión POM durante H1-25 | Gap de valor | Resuelto H2 |

---

## SECCIÓN B — DATOS 2026 (ACTUALIZAR MENSUALMENTE — APPEND ONLY)
# ==============================================================================
# INSTRUCCIÓN PARA ACTUALIZAR:
#
#   Cuando llegue el PDF del mes siguiente (ej. Abril 2026):
#   1. EXTRAER texto con: python -c "import fitz; ..." → _raw.txt temporal
#   2. AGREGAR fila en §B1 (Performance Mensual 2026) — NO editar filas existentes
#   3. AGREGAR filas en §B2 (Weekly Cuts 2026) — solo los cortes nuevos
#   4. REEMPLAZAR §B3 (Estado Actual) con el nuevo mes
#   5. AGREGAR bloque en §B4 (Sesiones Semanales 2026) — preservar histórico
#   6. Actualizar la línea "Último dato disponible" al inicio del archivo
#
#   LO QUE NUNCA DEBES CAMBIAR:
#   - Filas existentes en §B1 y §B2
#   - Bloques históricos en §B4
#   - Toda la Sección A (datos 2025)
#
# ÚLTIMO DATO DISPONIBLE: MARZO 2026 (extraído el 13-Abr-2026)
# PRÓXIMA ACTUALIZACIÓN: cuando llegue PDF Abril 2026
# ==============================================================================

### B1 — Performance vs Plan Mensual 2026 (APPEND — agregar fila al final)
# Fuente: Monthly Mar-26 §3.1 para Ene-26, Feb-26, Mar-26

| Mes | Total N+R | OC Real | OC Plan | OC vs Plan | POM Real | POM Plan | POM vs Plan | ORG Real | YTD vs Plan |
|---|---|---|---|---|---|---|---|---|---|
| **Ene-26** | 1.043.624 | 121.833 | 173.289 | **-29.7%** | 201.330 | 97.812 | **+105.8%** | 660.336 | +12.1% |
| **Feb-26** | 964.474 | 135.336 | 173.289 | **-21.9%** | 185.924 | 97.812 | **+90.1%** | 596.619 | +12.4% |
| **Mar-26** | ~1.124.789 | 148.901 | 173.289 | **-14.1%** | 204.549 | 97.812 | **+109.1%** | ~725.672 | **+15.4%** |
| _[Abr-26]_ | _AGREGAR AQUÍ_ | | | | | | | | |

**YTD Q1 2026**: Plan 2.714.160 / Real 3.133.292 / **+15.44%** / Delta **+419.132 N+R**

### B2 — Weekly MTD Cuts 2026 (APPEND — agregar filas nuevas al final)
# Fuente: Weekly Mar-26 §2, Monthly Mar-26 §3.1

| Corte | Total N+R | OC+UCR | UCR Gest | UCR PRD | OC ACT | POM TOTAL | POM ADQ | POM ACT | ORG | % vs LMTD |
|---|---|---|---|---|---|---|---|---|---|---|
| 27-Ene D7 | 900.140 | 115.498 | 47.297 | 9.830 | 58.371 | 185.324 | 109.802 | 75.522 | 570.462 | **-5.9%** |
| 4-Feb D0 | 139.671 | 15.794 | 7.222 | 566 | 8.006 | 23.498 | 12.157 | 11.341 | 96.865 | **+13.2%** |
| 16-Feb D0 | 526.071 | 73.733 | 30.173 | 2.763 | 40.797 | 107.070 | 64.468 | 42.602 | 331.534 | **+4.6%** |
| 23-Feb D7 | 792.139 | 120.514 | 47.646 | 4.219 | 68.649 | 163.395 | 98.773 | 64.622 | 486.486 | **+2.6%** |
| 4-Mar D7F | 148.237 | 13.383 | 6.531 | 446 | 6.406 | 23.322 | 10.049 | 13.273 | 108.217 | **+3.6%** |
| 18-Mar D0 | 677.546 | 79.096 | 37.524 | 3.069 | 38.503 | 114.005 | 56.788 | 61.674 | 461.938 | **+6.7%** |
| 26-Mar D7 | 899.124 | 109.060 | 50.247 | 4.516 | 54.297 | 165.955 | 84.458 | 81.497 | 602.260 | **+5.2%** |
| _[próximo corte Abr-26]_ | _AGREGAR AQUÍ_ | | | | | | | | | |

### B3 — ESTADO ACTUAL (REEMPLAZAR con el mes más reciente)
# INSTRUCCIÓN: Cuando llegue Abril, reemplaza TODO este bloque §B3.
# Mantén el bloque de "Último estado registrado" en §B4 para el historial.
# ÚLTIMO MES: MARZO 2026 (corte D7 al 26 de Marzo)

**Titular de la semana**: "Orgánico (+16%) compensa impacto de Calibradores en performance de OC+UCR"

**OC+UCR Mar-26 (vs LMTD)**: -15.5% / -20K NR
- Pandora calibrado 0.6→0.2 en ambas estrategias: UCR -3K NR (-47%), ACT -4.2K NR (-56%)
- UCR Push: **+8% NR** (+11% inversión, mejoras optimizador Mantika)
- UCR RE: **+13% NR** (más días de prints en Mar vs Feb)
- OC ACT Push: recupera tracción W3 por mejora selector de campañas

**POM Mar-26 (vs LMTD)**: -6.7% / -12K NR (pero ACT +16%)
- TikTok ACQ calibrador: 2.25 → **1.35** (23/Feb): -24.2K NR (-13%) — nueva evidencia de menor incrementalidad
- Scale-up ACT (+46% inversión MoM: TikTok, DV360, Liftoff): **+16K NR (+8%)**
- Efecto calendario +3 días vs Feb: **+20.7K NR (+11%)**
- Moloco ACT calibrador: 0.47 → **0.21** (16/Mar): -2.6K NR (-1%)
- YouTube ACQ calibrador: 0.45 → **0.70** (16/Mar): +2.5K NR (+1%)

**X-Channel AUC Mar-26 (Eficiencia últimos 90 días)**:
- Total Mkt: **+~3%** vs Feb
- Own Channels: **+~13%** vs Feb ← OC mejora en eficiencia aunque pierde volumen
- POM: **-~10%** vs Feb ← calibradores TikTok degradan eficiencia

**Forecast Abril 2026** (presentado en cierre Mar-26):
| Canal | Mar Real | Abr Forecast | Abr Plan | Vs LM | Vs Plan |
|---|---|---|---|---|---|
| **Total** | ~1.124.789 | **1.143.463** | 905.579 | +1.7% | **+26.3%** |
| OC | 148.901 | **161.900** | 155.257 | +8.7% | +4.3% |
| POM gest. | 204.549 | **178.000** | 126.493 | **-13.0%** | +40.7% |
| ORG | ~725.672 | **754.699** | 554.892 | +4.0% | +36.0% |

**Share MKT en NR**: Ene 37% → Feb 38% → Mar **35%** (-3pp MoM).

### B4 — Sesiones Semanales 2026 Detalladas (APPEND — agregar al final)
# Fuente: Weekly Mar-26, sesiones S1–S7

#### S7 — 30 Ene 2026 (POM + E&G)
- **Titular**: POM como motor de crecimiento; OC -21% por exclusión profit negativo + migración herramientas
- **OC**: -21% MoM. Push ACT: Churn Paid -20K NR (-55%) por exclusión profit <0. RE UCR: DRW/QA pausados 5 días operativo + caída navegaciones (-10.5K NR).
- **POM**: +36% MoM. CPM -20% estacional aprovechado; +30% inversión. Google iOS test: muy positivo. TikTok Smart+2.0: +8K NR.
- **Proyección Enero**: 1.027K total (+10% vs plan, -5% MoM, +22% YoY). MKT Share 37%.

#### S6 — 06 Feb 2026 (Growth + Producto)
- **Titular**: Orgánico compensa caída XChannel en primeros 4 días. OC -18% (ventanas abiertas).
- **Plan 1.5M OC** presentado en sesión 24/02 visita MLA. Challenge: ~3X crecimiento OC.
- **Hub de Newbies**: experimento completado, rollout 100%.
- **Funnel SSOT**: Canal Null 9% installs. MGM mejor CVR activación. POM y OC 1-2pp bajo promedio.

#### S5 — 20 Feb 2026 (Field + Corp)
- **Titular**: +4.6% MTD impulsado por Orgánico y canales gestionables.
- **OC+UCR**: +11.7% vs LMTD (recuperación real). Pandora +3K UCR +5K ACT. Discovery DB recuperado.
- **POM**: +2.6K NR (+2.5% MoM). ACQ acelerando post-impacto CPM.
- **Análisis Quincenas** presentado (Q1 14-16, Q2 29-31/1). CPA Pandora quincena: $1.4 USD.

#### S4 — 27 Feb 2026 (POM + E&G)
- **Titular**: +2.6% MTD (+2.7% proyección final). Proyección 900K (+40K sobre plan).
- **OC ACT**: +34.1% vs LMTD. UCR +15.7%. UCR PRD -54.6%.
- **POM**: Celebrity Wilson Alcaraz: +7K NR (-8% MoM solo por menos días + CPM normal + calibrador TikTok).
- **TikTok ACQ**: calibrador bajado por menor incrementalidad detectada.

#### S3 — 06 Mar 2026 (Growth + Prod + E&G)
- **Titular**: +3.6% MTD. Hub de Newbies rollout. Plan Ucrania 3 pilares.
- **Bandit POC**: Marzo/Abril — 10% audiencia Bandit vs 90% Mantika. Reward: Open Rate.
- **Audiencias 29.28M contactables**: 75% via App, 7.32M solo mail, 20% ENGAGED, 29% RECOV/LATENT.
- **KYC arbitrage**: usuarios con KYC convierten 6x más en tests UCR.

#### S2 — 20 Mar 2026 (Field + Corp)
- **Titular**: +6.7% MTD. Ventanas abiertas. OC -12.9% por Pandora a la baja + Push flows.
- **LP&Partners**: Pausa Rocket y OJO7 (CPA >$20). Renegociación Z2A. Telcel CPA $0.
- **Diagnóstico Adquisición Feb-26**: 965K usuarios, Silver 43%, Bronze 34%, ~78% total.
- **Google ACQ Android**: calibrador +55% (W12). Moloco ACT: reducción 85% (W12).

#### S1 — 27 Mar 2026 (POM + E&G) — MÁS RECIENTE
- **Titular**: +5.2% MTD. Calibradores dominan el relato (TikTok -40% vs 23/Feb).
- **OC -15.5%**: Pandora double shock (UCR -47%, ACT -56%). Push y RE compensan parcialmente.
- **POM -6.7%**: ACT +16% (inversión +46%) vs ADQ -21.5% (calibradores). YouTube ACQ sube.
- **OC X-Channel**: eficiencia +13% (acciones funcionan) pese a volumen -15%.

### B5 — Calibradores Activos 2026 (APPEND — agregar cambios de calibrador)
# Tabla crítica para entender por qué POM u OC sube o baja semana a semana.
# Actualizar AMBAS secciones cuando llegue nuevo dato mensual.
# Fuente: Weekly Mar-26 §4, B3/B4 narrativa

#### B5a — POM Calibradores (media paga)
| Fecha | Sub-canal | Cal. Anterior | Cal. Nuevo | Impacto NR |
|---|---|---|---|---|
| W01-26 | Google iOS ACQ | baseline | **Subido significativamente** | +7K NR est. |
| W02-26 | Moloco ACT | — | Ajuste señal optimización | Mejora performance |
| W09-26 | TikTok ACQ | — | **-40% calibrador** | -5K NR/semana |
| 23-Feb-26 | TikTok ACQ | 2.25 | **1.35** | **-24.2K NR mes** |
| 16-Mar-26 | Moloco ACT | 0.47 | **0.21** (-55%) | -2.6K NR mes |
| 16-Mar-26 | YouTube ACQ | 0.45 | **0.70** (+56%) | +2.5K NR mes |
| _[AGREGAR Abr-26: sub-canal POM, cal. anterior→nuevo, impacto NR]_ | | | | |

#### B5b — OC Calibradores (Pandora UCR + ACT)
# Pandora es el mayor driver de volatilidad en OC: shocks de -7K NR/semana cuando cae.
# Cada cambio de calibrador impacta directamente el share NR del canal.
| Fecha | Sub-canal | Cal. Anterior | Cal. Nuevo | Impacto NR |
|---|---|---|---|---|
| Mar-26 | Pandora UCR | 0.6 | **0.2** | **-3K NR/mes** (-47%) |
| Mar-26 | Pandora ACT | 0.6 | **0.2** | **-4.2K NR/mes** (-56%) |
| _[AGREGAR Abr-26: Pandora UCR/ACT o cualquier otro canal OC, cal. anterior→nuevo, impacto NR]_ | | | | |

### B6 — OTHERS Corp + NO ATRIBUIDO Corp: Performance 2026 (APPEND — derivado de §B1)
# NOMENCLATURA CORP:
#   "OTHERS" = MGM + L&P + UCR PRD + SEO + POM SELLERS + POM OTHERS
#   "NO ATRIBUIDO" = Orgánico (col ORG en §B1)
# Derivado de: Total N+R - OC - POM = OTHERS + NO ATRIBUIDO (§B1)
# OTHERS individual no disponible en B1/B2 — aproximar desde §A2 ratio histórico
#   (MGM ~38% / L&P ~62% del total OTHERS en 2025; UCR PRD/SEO/POM No Gest. < 5% combinado)
# INSTRUCCIÓN: Actualizar cuando llegue nuevo dato mensual. Append-only.

| Mes | Total N+R | ORG Real | MGM+Others (derivado) | Share ORG | Share MGM+Others | Share MKT total |
|---|---|---|---|---|---|---|
| **Ene-26** | 1.043.624 | 660.336 | ~60.125 | **63.3%** | ~5.8% | ~30.9% |
| **Feb-26** | 964.474 | 596.619 | ~46.595 | **61.9%** | ~4.8% | ~33.3% |
| **Mar-26** | ~1.124.789 | ~725.672 | ~45.667 | **~64.5%** | ~4.1% | **~31.4%** |
| _[Abr-26: AGREGAR AQUÍ]_ | | | | | | |

**Nota de cálculo**: MGM+Others = Total − OC − POM − ORG. Para split MGM/Others individual: ratio 2025 ≈ 38%/62% (§A2). Ej: Ene-26 MGM ≈ 22.8K / Others ≈ 37.3K. ⚠️ Estimación — validar con BI docs.

**Tendencia clave**: Share MKT total cayó 37%→38%→35% en Q1-26 (§B3). ORG compensa: creció +22% YoY (§B4 S7).

---

## SECCIÓN A (continuación) — CANALES MGM, OTHERS Y ORGÁNICO (2025 CERRADO)

### A15 — MGM Performance 2025 (sub-canal de OTHERS Corp)
# Fuente: Weekly 2025 §A2 (cortes MTD), CLAUDE.md channel hierarchy
# POSICIÓN EN CORP: MGM es sub-canal dentro del grupo OTHERS (junto con L&P, UCR PRD, SEO, POM Sellers/Others)
# ⚠️ DATOS LIMITADOS: solo cortes MTD disponibles, no cierres mensuales completos.
#    Para análisis profundo: leer docs/Weekly Adquisición MLM_2025_versionClaud.md

| Corte | MGM NR (MTD D7) | Share del Total | Nota |
|---|---|---|---|
| May W2 (D0) | 3.023 | 1.1% | Primer corte disponible |
| May fin (D0) | 8.237 | 1.1% | ~full month proxy |
| Jul W2 (D7) | 3.405 | 1.0% | Estable en torno a 1% |
| Oct W43 (D7) | 11.110 | 1.6% | Crecimiento en H2 |
| Nov W46 (D7) | 8.983 | 1.4% | — |
| Nov W47 (D7 al 23-Nov) | 11.168 | 1.4% | Pico observable 2025 |

**Estructura canal MGM (desde CLAUDE.md)**:
- MGM ADQ: `ACQUISITION + MGM channel` → NR con inversión directa (cupones pagos)
- MGM ACT: `ACTIVATION/OTHER + MGM channel` → NR sin inversión directa (costo $0)
- ⚠️ `ADQUISITION` (sin C) = typo histórico en `PANEL_MONTHLY_COSTOS_CANALES` para MGM. No confundir con `ACQUISITION` en DAILY_HISTORICO.

**Insight clave de §B4 S6**: "MGM mejor CVR activación" → MGM ACT tiene el mejor ratio de conversión de todo el portafolio en la etapa de activación, aunque con volumen bajo.

**Benchmarks MGM 2025** (de §A3/A5 contexto general):
- Share total: ~1-2% del total N+R del site
- Comportamiento: estable, sin grandes shocks de calibrador (a diferencia de POM o Pandora)
- Inversión: mix canal (comisiones) + incentivos (cupones) — muy diferente a POM

---

### A16 — L&P / Others Performance 2025 (sub-canal de OTHERS Corp)
# Fuente: Weekly 2025 §A2 (cortes MTD), §B4 S2 (calibradores/decisiones Mar-26)
# POSICIÓN EN CORP: L&P es sub-canal de OTHERS Corp. Sus sub-canales propios:
#   BRANDFORMANCE · LANDINGS · PARTNERSHIPS · AFFILIATES · GTM · OTHERS (catch-all L&P)
# Nota: UCR PRD, SEO, POM SELLERS, POM OTHERS también son sub-canales de OTHERS Corp
#   pero no tienen datos históricos propios en este contexto (leer BI directo si se requieren).
# ⚠️ DATOS LIMITADOS: cortes MTD + decisiones de gestión. Leer BI para análisis completo.

| Corte | LP&P NR (MTD D7) | Share del Total | Nota |
|---|---|---|---|
| May W2 (D0) | 1.820 | 0.7% | — |
| May fin (D0) | 5.622 | 0.7% | ~full month proxy |
| Jul W2 (D7) | 2.807 | 0.8% | — |
| Oct W43 (D7) | 12.536 | 1.8% | Crecimiento notable H2 |
| Nov W46 (D7) | 14.856 | 2.4% | Escalamiento H2 |
| Nov W47 (D7 al 23-Nov) | 17.739 | 2.2% | Pico observable 2025 |

**Sub-canales L&P (desde CLAUDE.md queries.py)**:
`BRANDFORMANCE · LANDINGS · AFFILIATES · PARTNERSHIPS · GTM · OTHERS`

**Decisiones de gestión activas (§B4 S2, Mar-26)**:
- ❌ **Rocket pausado** (CPA >$20 — no rentable)
- ❌ **OJO7 pausado** (CPA >$20 — no rentable)
- 🔄 **Z2A en renegociación** (condiciones de CPA)
- ✅ **Telcel CPA $0** (partnership sin costo — only performance)

**Insight clave**: L&P tiene el mayor potencial de crecimiento eficiente si se activan partners con modelo CPA puro (sin inversión upfront). Telcel es el modelo a replicar.

---

### A17 — NO ATRIBUIDO / Orgánico — Tendencia 2025
# Fuente: §B1 (absolutos 2026 exactos), §B4 (narrativa 2025), §A2 (cortes MTD)
# NOMENCLATURA:
#   Vista estándar (NR Mensual): "ORG" / "Orgánico"
#   Vista Corp (tablas Corp): "NO ATRIBUIDO"
#   Son el mismo canal. En este contexto se usa ambos como equivalentes.
# DEFINICIÓN: catch-all — todo lo que no es OC+UCR, POM ni OTHERS en la vista Corp.
# Incluye: búsqueda orgánica, brand awareness, boca-a-boca, SEO app stores.

**Participación ORG en el total (tendencia conocida)**:

| Período | Share ORG estimado | Fuente |
|---|---|---|
| 2025 prom. (H1) | ~65-70% | Derivado de share OC+UCR (~15%) + POM (~12%) + Others (~2%) |
| 2025 prom. (H2) | ~60-65% | Mayor crecimiento MKT en H2 reduce share ORG relativo |
| Ene-26 | **63.3%** (660.3K) | §B1 exacto |
| Feb-26 | **61.9%** (596.6K) | §B1 exacto |
| Mar-26 | **~64.5%** (~725.7K) | §B1 exacto |

**Señales clave de ORG (§B4, §B3)**:
- Mar-26: ORG +16% MoM — compensó el impacto de calibradores en OC y POM (§B3)
- YoY Ene-26: +22% (§B4 S7 — "Proyección +22% YoY")
- ORG crece en términos absolutos con el crecimiento de la base de usuarios activos de MeLi

**Relación ORG ↔ MKT (insight estructural)**:
- ORG no cae cuando MKT sube — son complementarios, no canibalísticos
- El plan OC+UCR 1.5M no implica reducir ORG: OC crece más rápido, ORG sigue su tendencia
- Señal de alerta: si Share MKT cae y Share ORG sube = MKT no está agregando suficiente incremental

---

## SECCIÓN C — BENCHMARKS Y REFERENCIAS PERMANENTES
# Esta sección NO cambia (verdades permanentes del canal).
# Se actualiza solo si hay un cambio estructural de métricas de referencia.

### C1 — Benchmarks de Eficiencia (verdades permanentes del portafolio MLM)

| Métrica | OC+UCR | POM | Interpretación |
|---|---|---|---|
| CPA típico (USD) | $0.6–$1.7 Blended / $4–$11 Paid | $13–$17 | OC tiene mejor CPA en todos los rangos |
| ROAS típico | 3.3–13.0 (rango H1-25 a H2-25) | 3.6–4.0 | OC supera POM cuando opera bien |
| VPU (USD) | $49–$62 (promedio ~$55) | $49–$54 | Similar; iOS POM +70% vs Android |
| CPA Breakeven | $18.3 USD | ~$20 USD | OC más eficiente marginal |
| CPA Marginal Máx | $27.5 USD | — | OC puede escalar sin destruir ROAS |

### C2 — Reglas de Oro (validadas por datos, no teóricas)

1. **Usuarios navegantes ML = 2x Lift** vs no-navegantes. Targeting comportamental > demográfico.
2. **Descuento % > monto $ en Pandora** (+26% NR). Psicología del porcentaje funciona.
3. **Carrito abandonado = 3x conversión** en Pandora. La intención de compra predice activación.
4. **5 pushes = punto de quiebre** (5% OR). Con 1/5 del volumen de Nov: Ene generó 43% más NR inc.
5. **NO Pandora en seasonals**: CPA $2 → $10 USD (+400%).
6. **Landing sin formulario gana siempre** en POM Web: +47% CTR.
7. **iOS VPU +70% mejor que Android** en TikTok. Canal premium subatacado.
8. **CPM de Enero -20%**: comportamiento estacional todos los años. Aprovechar para escalar +30%.
9. **50% descuento POM = desconfianza**: Cashback 10% gana con 92% significancia estadística.
10. **OC tiene mejor ROAS que POM** (5-13x vs 3-4x) pero recibe ~40% del budget vs ~60%.

### C3 — Riesgos Estructurales Activos (actualizar si se resuelven)

| ID | Riesgo | Impacto NR | Estado al Mar-26 | Responsable |
|---|---|---|---|---|
| R1 | Canibalización QA-BNPL (-29% prints, -5K NR/mes) | **-5K/mes** | ❌ Sin resolver | — |
| R2 | Atribución DRW -8pp acumulado (sep-25→ene-26) | Medición | ⚠️ En revisión | MKT Corp |
| R3 | Pandora calibrador volátil (shocks -7K NR/semana) | -7K max. | ⚠️ Recurrente | E&G |
| R4 | Mantika en techo (80% NR en MYI Paid) | Saturación | 🔧 Bandit en desarrollo | E&G |
| R5 | TikTok ACQ calibrador bajo (2.25→1.35) | -24K NR mar | ⚠️ Pendiente validar incrementalidad | POM |
| R6 | Share MKT cayendo (38%→35% en Mar-26) | Pérdida control | 🔴 Estructural | Todo el equipo |
| R7 | Atribución CC incrementales sin fix | "Found money" sin medir | 🔴 **URGENTE** | MKT Corp |
| _[Abr-26: ACTUALIZAR ESTADO de los riesgos anteriores y AGREGAR nuevos si aplica]_ | | | | |

### C4 — Oportunidades Cuantificadas (ordenadas por impacto/esfuerzo)
# Actualizar columna "Estado" mensualmente. Leyenda: ✅ Ejecutado · 🟡 En curso · ⚠️ Pendiente · 🔴 Bloqueado · ❌ Descartado

| # | Oportunidad | NR potencial/mes | Fuente evidencia | ETA | Estado Apr-26 |
|---|---|---|---|---|---|
| O1 | Reasignación budget OC 58% / POM 42% | **+12–16K NR** | Curvas X-channel W29-25 | Inmediato | ⚠️ Pendiente ejecutar |
| O2 | Awareness en MeLi (Main Home + categorías) | **+50K NR** | Weekly Mar-26 p.112 | Q3 | 🟡 En roadmap Q3 |
| O3 | Espacio Favoritos/Carrito | **+20K NR** | Weekly Mar-26 p.112 | Q3 | 🟡 En roadmap Q3 |
| O4 | MP en Search ML | **+11K NR** | Weekly Mar-26 p.112 | Q2 | 🟡 En negociación con MeLi |
| O5 | Bandit RL UCR Push | **+3.5K NR** (piloto) | Monthly Mar-26 §10 | Q2 | 🟡 POC en curso (S3 Mar-26) |
| O6 | Pandora Always On UCR 85% | **+4.5K NR** | Weekly Mar-26 §6 | Inmediato | 🔴 Bloqueado — calibrador en 0.2 |
| O7 | Pandora Always On ACT 85% | **+6K NR** | Weekly Mar-26 §6 | Inmediato | 🔴 Bloqueado — calibrador en 0.2 |
| O8 | KYC 10M usuarios (6x conversión vs sin KYC) | Alto TBD | Weekly Mar-26 §11 | Q2 | 🟡 En definición Q2 |
| O9 | WPP Ucrania (6M sin opt-in, lift 0.5%) | **+25–30K NR** | Monthly Mar-26 §10.1 | Q2 | 🟡 En planificación Q2 |
| O10 | Gamification checkpoint + multi-target | **+15–20K NR** | Monthly Mar-26 §10.1 | Q2–Q3 | 🟡 En roadmap Q2–Q3 |
| _[ACTUALIZAR ESTADO al llegar Abr-26 y agregar nuevas oportunidades si aplica]_ | | | | | |
