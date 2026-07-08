# CHANGELOG — Skills de Análisis MLM ADQ
# ==============================================================================
# PROPÓSITO:
#   Registro cronológico de qué se actualizó, cuándo y por qué.
#   Permite auditar rápidamente el historial sin leer los archivos completos.
#
# CONVENCIÓN DE ACTUALIZACIÓN:
#   Cuando actualices context.md mensualmente, agrega una entrada aquí PRIMERO.
#   Formato: [YYYYMM] — [qué cambió] — [quién / fuente]
#
# LEYENDA DE SECCIONES:
#   [SKILL]   → cambio en analizar-Optimizar_Performance_KPIs_skill.md
#   [CONTEXT] → cambio en analizar-Optimizar_Performance_KPIs_context.md
#   [ARCH]    → cambio de arquitectura (archivos nuevos, renombrados, etc.)
# ==============================================================================

---

## v4.1 — 2026-04-27 (Modo 18 + TEMPLATE_STOP_OR_CONTINUE + trigger canibalizador)

**Archivos modificados**: `analizar-OC_Comms_skill.md` v3.4 + `OPTIMIZADOR-OC_skill.md` v4.1

**Motivación**: Auditoría de capacidades contra 6 ejemplos reales reveló 5 gaps en la capacidad de responder preguntas tipo:
"¿Vale la pena parar MLM-ML-I-EG-UCR-MTK-CAMP-NIA-MARA?" · "GENERIC_MP lleva meses bien, ¿se está fatigando?" · "CELLPHONE RECHARGE está negativo, ¿qué impacto tendría detenerlo?"

**Nuevo Modo 18: `campaña_historico [nombre_o_prefix]`** (Comms Skill)
- Construye la "carrera histórica" de una campaña o grupo específico a través de todos los meses en comms_monthly_summary.md
- Calcula Índice de Decaimiento (ID) mes a mes: ID = USER_INC_mes / USER_INC_pico
- Clasifica en 5 fases: PEAK (ID>0.80) / MESETA (0.50-0.80) / FATIGA (0.20-0.50) / AGOTADA (<0.20) / CANIBALIZANDO (<0)
- Aplica REGLA 6 automáticamente (MARA = código interno si aparece en múltiples meses)
- Incluye PASO 5 — ANÁLISIS STOP OR CONTINUE con impacto positivo + negativo + recomendación de sustituto
- Golden rule: una campaña con USER_INC<0 no se sustituye por una variante similar sin entender por qué canibaliza

**Nuevo TEMPLATE_STOP_OR_CONTINUE** (OPTIMIZADOR)
- Template estructurado para decisión parar/continuar con secciones explícitas: IMPACTO POSITIVO / IMPACTO NEGATIVO para ambas opciones + sustituto recomendado + golden rule

**Trigger canibalizador actualizado** (OPTIMIZADOR triage punto 2)
- Ahora incluye threshold explícito: USER_INC < 0 en > 50% de registros → CANIBALIZADOR SISTÉMICO → invocar Modo 18

**Tabla de orquestación OPTIMIZADOR expandida**
- Añadidas 3 filas: campaña_historico para stop/continue · fatiga · BL negativo

---

## v4.0 — 2026-04-27 (Fase 2 Rediseño: OPTIMIZADOR reescrito — Arquitectura Cross-Signal)

**Archivos modificados**: `OPTIMIZADOR-OC_skill.md` v3.2 → v4.0

**Reducción**: 2,062 líneas → 722 líneas (-65%). Eliminados ~700 líneas de análisis duplicado.

**Qué se eliminó del OPTIMIZADOR** (ahora delegado a los skills de Capa 1):
- Marco Analítico del Juez 6 pasos (Dimensiones 1-7 incluyendo funnel, fatiga VP, sweet spots)
- Toda lógica de cálculo de métricas (Efficiency Score, LIFT, etc.) — ahora referencia a Comms Skill
- Duplicación de protocolo de ciclo de VP (está en Comms Modo 10)
- 262 líneas de atribución causal detallada → reemplazadas por FILTRO 2 (check RATIO_CANIBALIZACION)

**Qué se añadió** (el corazón del rediseño):
- Contratos de Input explícitos: formato exacto de SERIE_KPI_ESTÁNDAR y FINGERPRINT_CAMPAÑA
- Tabla de Orquestación completa: qué skill + modo llamar para cada pregunta
- **Framework de Análisis Cross-Signal: 7 Patrones de agujas en el pajar**:
  1. Divergencia KPI-Comms (crecimiento es IS, no comms)
  2. Efecto Familia / Pareto interno (ruido canibaliza al ganador)
  3. Suelo invisible de saturación (reach crece, LIFT cae)
  4. Timing como driver real (no el canal, no el VP)
  5. RATIO_CANIBALIZACION creciente (experimento se degrada)
  6. Lag de calibrador (4-8 semanas entre ajuste y efecto)
  7. Concentración de audiencia cross-tabla (solapamiento ALL_CAMPAIGNS_NR + NR_ACQUISITION)
- Modo `familia [prefix]` — orquesta Comms Modo 17 con síntesis estratégica
- Templates simplificados pero completos (VEREDICTO, CAUSA_RAIZ, ALERTA)
- Triage inicial preservado y mejorado (los 5 puntos)
- Protocolo de Alerta Automática preservado (es muy valioso — caso MST2MP)
- 5 Filtros antes del veredicto preservados y actualizados con nuevos campos §75

**Visión**: El OPTIMIZADOR es la orquesta estratégica que recibe la música ya compuesta
por los 2 skills de Capa 1 y la ejecuta a nivel de VP — encontrando los patrones no
obvios que nadie ve en el dashboard, conectando las señales cruzadas KPI × Comms,
y generando la partitura de decisiones que mueven resultados reales.

---

## v3.3 — 2026-04-27 (Fase 1 Rediseño: Modo 17 familia_campanas + dispatch actualizado)

**Archivos modificados**: `analizar-OC_Comms_skill.md` v3.3

**Motivación**: Rediseño arquitectural de los 3 skills. El OPTIMIZADOR es la orquesta estratégica
que recibe información ya pulida de KPI Skill y Comms Skill, y analiza a nivel estratégico
cruzando señales para encontrar los insights no obvios — las agujas en el pajar que mueven
resultados reales.

**Nuevo Modo 17: `familia_campanas [prefix]`**
Análisis jerárquico de familias de campañas por prefijo de nombre. Resuelve el caso real:
flows_communication_MLM_I_EG_MTK_STOCK → STOCK_M → STOCK_MONEYINHI2 (7.2K UI = ganador).
- Construye árbol jerárquico por tokenización de sufijos
- 4 veredictos: GANADOR / CONTRIBUYENTE / RUIDO / CANIBALIZADOR
- Calcula impacto de simplificar la familia (NR directo + NR indirecto por audiencia liberada)
- Genera fingerprint del ganador para replicar en otras familias
- Ejemplo real Mar 2026 documentado con números reales

**Dispatch table actualizado**: añadidas filas `familia_campanas` y `ranking_multidim` explícitas.

---

## v3.2 — 2026-04-27 (§75: Migración schema Comms_OC a tablas Torre de Control unificadas)

**Archivos modificados**: `analizar-OC_Comms_skill.md` v3.2 + `OPTIMIZADOR-OC_skill.md` v3.2

**Motivación**: §75 History.md migró la fuente de Comms_OC de 4 ramas legacy (BT_OC_CUST_EVENT + DASHBOARD_CAMPAIGNS_INDIVIDUOS_METRICAS + BT_OC_EMAIL_MP_MONTHLY + BT_OC_MP_FLOWS_DAILY + DIM_REE_METRICS_PRINTS) a 2 tablas Torre de Control: `BT_OC_DASHBOARD_ALL_CAMPAIGNS_NR` + `BT_OC_DASHBOARD_ALL_CAMPAIGNS_NR_ACQUISITION`.

**Campos renombrados/actualizados:**
- `FIRST_SENT_DATE` → `SENT_DATE` (granularidad diaria por COMM_ID × SENT_DATE × CANAL)
- `CHANNELS_METRICS` → `BUSINESS_LINE`
- `STRATEGIES` / `SUBSTRATEGIES` → `STRATEGY` / `SUBSTRATEGY` (ya no STRING_AGG)
- `TYPE_NAME` → `CLASIF_CAMPAIGNS`

**Campos eliminados del schema:**
- `M_LIFT` — proxy: `USER_INC / TOTAL_TEST`
- `M_CVR_TEST` — proxy: mismo
- `TPN_INC`, `TPV_INC` — sin equivalente en nuevas tablas
- `NOTIFICATION_TITLE`, `NOTIFICATION_TEXT` — inferir desde CAMPAIGN_NAME_CLEAN
- `TOTAL_CREATE_CUST_EVENT`, `TOTAL_SHOWN_CUST_EVENT` — eliminados
- `TOTAL_BLACKLIST/BLOCKED/BOUNCE/SPAMREPORT` — eliminados

**Campos nuevos disponibles:**
- `TOTAL_ABSOLUTO_NR` — NR bruto sin calibrar (conversiones grupo test)
- `RATIO_CANIBALIZACION` — % conversión orgánica vs incremental (>50% = revisar experimento)
- `FUENTE_TABLA` — 'ALL_CAMPAIGNS_NR' | 'NR_ACQUISITION' | 'AMBAS' (dedup cross-tabla)
- `FLAG_PAID`, `FLAG_INCENTIVO` — clasificación de costo
- `CONSUMIDO_USD`, `COSTO_ENVIO_USD`, `COSTO_MANTIKA_USD` — costos directo en Comms_OC
- `CLASIF_CAMPAIGNS` — clasificación de campaña (UCRANIA/ACTIVACION/ADHOC/…)

**Notas para analistas:**
- JOURNEY ahora en Rama A (CANAL='JOURNEY'). No consultar BT_OC_MP_FLOWS_DAILY directamente.
- REAL ESTATE ahora en ambas ramas según sub-canal. Filtrar por FUENTE_TABLA para separar OC ACT vs UCR Gest RE.
- CPA de campaña individual ahora calculable: `CONSUMIDO_USD / USER_INC` directo en Comms_OC.

---

## v2.5 — 2026-04-14 (Análisis de Estacionalidad + Calendario Comercial México)

### [SKILL] analizar-Optimizar_Performance_KPIs_skill.md
- **Nuevo modo `"estacionalidad"` / `"temporal"`** → MODO_ESTACIONALIDAD
- **Nuevo PASO_3C_RAZONAMIENTO_ESTACIONALIDAD**: cadena de razonamiento de 9 pasos en 4 niveles:
  Nivel 1 (IS mensual) · Nivel 2 (quincenas + D7 cuts) · Nivel 3 (días especiales) · Nivel 4 (síntesis estratégica)
- **Nuevo TEMPLATE_ESTACIONALIDAD**: output estructurado con tabla IS por mes, campañas cuantificadas,
  distribución intra-mensual, desviaciones del patrón, calendario de decisiones próximos 3 meses
- **PASO_5 Checklist**: separado en 3 bloques (todos los modos / solo estacional / solo drill/estratégico)
- **Dispatch MODO→SECCIONES**: nueva fila MODO_ESTACIONALIDAD con §AE1–§AE6 como obligatorio
- **Dispatch MODO→TEMPLATE**: nueva fila MODO_ESTACIONALIDAD → TEMPLATE_ESTACIONALIDAD

### [CONTEXT] analizar-Optimizar_Performance_KPIs_context.md
- **Nueva §AE1 — Calendario Comercial México + Impacto MP**: 12 meses con IS estimado por canal,
  evento principal, acción operativa validada (basada en datos de §A1/A3/A6/A8/A13)
- **Nueva §AE2 — Índices de Estacionalidad Mensuales**: tabla IS OC+UCR + IS POM para 2025 completo
  + 2026 Q1. Metodología explicada (share-based para OC, absoluto para POM). [Estimado] marcado.
- **Nueva §AE3 — Patrón Intra-Mensual Quincenas**: datos de §A8 + Pandora CPA $1.4 en quincena.
  Distribución semanal estimada del NR con validación de D7 cuts de §B2.
- **Nueva §AE4 — Días Especiales del Año**: lookup de acción por canal × evento
- **Nueva §AE5 — Campañas Internas MP con Datos**: LCDLF, Hot Sale, Buen Fin, JDV, Double Days, Quincenas.
  Cada campaña con período, IS, datos cuantificados y fuente
- **Nueva §AE6 — Matriz de Decisión Estacional**: lookup rápido canal × evento (8 eventos × 4 canales)

---

## v2.4 — 2026-04-14 (Corrección nomenclatura vista Corp)

### [SKILL] analizar-Optimizar_Performance_KPIs_skill.md
- **Nuevo bloque "MAPA DE CANALES — VISTA CORPORATIVA"** al inicio del skill (antes del ROL):
  Árbol completo de la jerarquía Corp con fuente de verdad explícita (channels_config.json)
  + tabla de mapeo vista estándar ↔ vista Corp. Primera cosa que lee el modelo.
- **Corrección crítica en header**: CANALES CUBIERTOS reflejaba "MGM/Others · Orgánico" (incorrecto).
  Ahora usa los 4 grupos Corp exactos: OC+UCR · POM · OTHERS · NO ATRIBUIDO
- **OTHERS Corp correctamente definido**: incluye MGM + L&P + UCR PRD + SEO + POM SELLERS + POM OTHERS.
  MGM ya no aparece como canal independiente — es sub-canal de OTHERS.
- **MODO_ORGANICO renombrado a MODO_NO_ATRIBUIDO** (nombre Corp correcto).
  Alias "org" mantenido para retrocompatibilidad.
- **MODO_OTHERS_LP renombrado a MODO_OTHERS** (cubre todos los sub-canales de OTHERS Corp).
- **MODO_OC_UCRANIA renombrado a MODO_OC_UCR** (nombre Corp correcto).
- **Dispatch MODO→SECCIONES**: actualizado con nuevos nombres de modo.
- **PASO_3B subcanales**: OTHERS Corp detallado con todos sus 6 sub-canales.
  NO ATRIBUIDO reemplaza a ORG/Orgánico en la descripción.

### [CONTEXT] analizar-Optimizar_Performance_KPIs_context.md
- **Header**: agregada sección "VISTA CORPORATIVA" con los 4 canales Corp y la nota de equivalencia.
- **§A15 (MGM)**: nota de posición Corp (sub-canal de OTHERS, no canal independiente).
- **§A16 (L&P)**: nota de posición Corp + lista de sub-canales propios + mención de UCR PRD/SEO/POM No Gest.
- **§A17**: renombrado de "ORG/Orgánico" a "NO ATRIBUIDO / Orgánico" con tabla de equivalencia.
- **§B6**: renombrado header a "OTHERS Corp + NO ATRIBUIDO Corp" + aclaración de composición.

---

## v2.3 — 2026-04-13 (Extensión a 4 canales + rename)

### [ARCH] Rename de archivos
- `analizar-Optimizar_KPIs_oc_pom_skill.md` → `analizar-Optimizar_Performance_KPIs_skill.md`
- `analizar-Optimizar_KPIs_oc_pom_context.md` → `analizar-Optimizar_Performance_KPIs_context.md`
- 10 archivos con referencias actualizadas en cascada (entry points, builders_analysis.py, README, CHANGELOG, NR_impact_methodology.md)

### [SKILL] analizar-Optimizar_Performance_KPIs_skill.md
- **Header**: CANALES CUBIERTOS actualizado a los 4 canales · VERSIÓN 2.3 · DISPONIBILIDAD DE DATOS por canal
- **4 nuevos modos**: `mgm` → MODO_MGM · `others` → MODO_OTHERS_LP · `org` → MODO_ORGANICO · `total` → MODO_TOTAL_SITE
- **PASO_1 dispatch MODO→SECCIONES**: 4 nuevas filas con secciones específicas por canal (§A15/A16/A17/B6)
- **PASO_2 dispatch MODO→TEMPLATE**: 4 nuevas filas
- **PASO_3B subcanales**: añadidos MGM (ADQ/ACT), L&P/Others (Brandformance/Affiliates/etc.) y ORG (análisis de tendencia)

### [CONTEXT] analizar-Optimizar_Performance_KPIs_context.md
- **§A15**: MGM Performance 2025 — cortes MTD disponibles, estructura canal, insight CVR
- **§A16**: L&P/Others Performance 2025 — cortes MTD, sub-canales, decisiones activas (Rocket/OJO7 pausados, Telcel $0 CPA)
- **§A17**: ORG Tendencia 2025 — share histórico, relación ORG↔MKT, señal de alerta
- **§B6**: MGM+Others+ORG 2026 — derivado de §B1, tendencia Q1-26, share por canal

### [ARCH] Entry points actualizados
- Ambos entry points (`SI_Meli_code1/.claude/commands/` y `MLM_ADQ_Dash/.claude/commands/`) actualizados con los 15 modos completos y referencias al nuevo nombre de archivo

---

## v2.2 — 2026-04-13 (Optimización de arquitectura)

### [SKILL] analizar-Optimizar_Performance_KPIs_skill.md
- **Fix bug crítico**: header declaraba 6 modos, PASO_2 tenía 11. Alineados a 11 modos.
- **Nuevo**: tabla dispatch `MODO → SECCIONES DEL CONTEXTO` en PASO_1
  (minimiza tokens por modo — EJECUTIVO lee solo B3+B5+C3 en lugar de todo el contexto)
- **Nuevo**: tabla dispatch `MODO → TEMPLATE` en PASO_2
  (elimina ambigüedad en selección de template — antes el modelo infería)
- **Fix**: `TEMPLATE_CAMINO_CRITICO` tenía referencia rota `[Ver §SECCION...]`
  Completado con tabla de timeline mes a mes + hipótesis + riesgo principal

### [CONTEXT] analizar-Optimizar_Performance_KPIs_context.md
- **Nuevo §A1**: nota guía sobre N+R absolutos 2025 (no estaban en la tabla; apunta a Weekly 2025 §3.1)
- **Nuevo §B5b**: calibradores OC/Pandora separados de POM (antes estaban mezclados en B5)
  B5 ahora = B5a (POM) + B5b (OC Pandora) — ambas con instrucción APPEND
- **Nuevo §C4**: columna `Estado Apr-26` con semáforo de vigencia por oportunidad
  Previene que el skill recomiende oportunidades bloqueadas (O6/O7 por calibrador Pandora 0.2)

### [ARCH] Nuevo archivo
- Creado `skills/CHANGELOG.md` (este archivo) para auditoría de cambios

---

## v2.1 — 2026-04-13 (Versión inicial con arquitectura skills/)

### [ARCH] Arquitectura inicial
- Migración de `docs/OC_POM_master_context.md` → `skills/` folder
- Entry point: `.claude/commands/analizar-oc-pom.md` (thin wrapper)
- Skill principal: `skills/analizar-Optimizar_Performance_KPIs_skill.md` (560 líneas)
- Base de conocimiento: `skills/analizar-Optimizar_Performance_KPIs_context.md` (436 líneas)
- README: `skills/README.md` con protocolo de actualización mensual

### [CONTEXT] Datos cargados
- **§A (2025 CERRADO)**: A1–A14 — serie histórica OC+UCR (Feb–Dic 25), POM mensual,
  benchmarks incentivos, Pandora CVR, RE sub-canales, quincenas, Mantika, Hub Newbies,
  X-Channel AUC W29, POM Plan 2025, seasonals, riesgos estructurales
- **§B (2026 ABIERTO)**: B1 (performance mensual Ene–Mar), B2 (weekly cuts MTD),
  B3 (estado actual Mar-26), B4 (sesiones S1–S7), B5 (calibradores POM Ene–Mar)
- **§C (PERMANENTE)**: C1 benchmarks eficiencia, C2 reglas de oro (10),
  C3 riesgos activos (R1–R7), C4 oportunidades cuantificadas (O1–O10)

---

## PROTOCOLO DE ACTUALIZACIÓN MENSUAL (referencia rápida)

Cuando llegue PDF Abril 2026 (o cualquier mes siguiente):

```
1. Agregar entrada en este CHANGELOG (primero)
2. context.md §B1 → agregar fila Abr-26 (APPEND)
3. context.md §B2 → agregar cortes semanales de Abr (APPEND)
4. context.md §B3 → REEMPLAZAR con estado actual Abr-26
5. context.md §B4 → agregar sesiones de Abr (APPEND)
6. context.md §B5a/B5b → agregar cambios de calibrador POM/OC (APPEND)
7. context.md §C3 → actualizar estados de riesgos si cambiaron
8. context.md §C4 → actualizar columna Estado de oportunidades
9. Actualizar "ÚLTIMA ACTUALIZACIÓN" en header de skill.md si hubo cambio en el skill
```

**Tiempo estimado**: 15 minutos si se sigue el protocolo sin desviaciones.
