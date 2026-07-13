# builders_analysis.py
# ==============================================================================
# PROPÓSITO:
#   Genera el HTML estático para las pestañas de análisis estratégico del dashboard.
#   Estas pestañas son INDEPENDIENTES de BigQuery — su contenido proviene del
#   skill de análisis (skills/analizar-Optimizar_Performance_KPIs_skill.md) aplicado sobre los datos
#   pre-compilados en (skills/analizar-Optimizar_Performance_KPIs_context.md).
#
# CUÁNDO ACTUALIZAR ESTE ARCHIVO:
#   - Cuando llegue nuevo dato mensual de 2026 (agregar columnas/datos nuevos)
#   - Cuando el equipo tome nuevas decisiones estratégicas validadas con datos
#   - NO actualizar para cambios de performance semanal (eso es el dashboard principal)
#
# CONVENCIÓN DE NOMBRES EN ESTE ARCHIVO:
#   - FASE_*         : constantes de fases históricas del canal
#   - DRIVER_*       : drivers de crecimiento identificados
#   - CAUSA_*        : causas de caída identificadas
#   - PALANCA_*      : palancas del plan de crecimiento
#   - RIESGO_*       : riesgos activos del canal
#   - _html_tag_*    : funciones privadas de construcción de elementos HTML
#   - build_*_tab_html : funciones públicas que devuelven el HTML de cada pestaña
#
# FUENTES DE DATOS (fuente de verdad):
#   skills/analizar-Optimizar_Performance_KPIs_context.md — Sección A (2025 cerrado)
#   skills/analizar-Optimizar_Performance_KPIs_context.md — Sección B (2026 hasta Marzo)
#   skills/analizar-Optimizar_Performance_KPIs_context.md — Sección C (benchmarks permanentes)
#
# ÚLTIMA ACTUALIZACIÓN: 27 Abr 2026 — Datos: KPIs hasta Mar-26 · Comms_OC hasta Abr-26 D25
# Skills aplicados: KPI Skill §A1/B1-B5 + Comms Skill Modos 14/17 + OPTIMIZADOR v4.0 (7 Patrones Cross-Signal)
# Cross-signal insights nuevos: EMAIL motor oculto (OR 23-27% vs PUSH 3-5%), Familia STOCK (MONEYINHI2 ganador),
# Abr colapso (+63 USER_INC) = lag Pandora 0.2 + saturación PUSH + JOURNEY canibalizadores
# ==============================================================================

def _cs(v):
    """Coerce to str NaN-safe. float NaN es truthy en Python, 'v or default' no funciona."""
    if v is None or (isinstance(v, float) and v != v):
        return ''
    return str(v).strip()


# ──────────────────────────────────────────────────────────────────────────────
# DATOS ESTRATÉGICOS OC+UCR
# Fuente: skills/analizar-Optimizar_Performance_KPIs_context.md §Parte 0, §B1, §B3, §C
# Última validación: 13-Abr-2026
# ──────────────────────────────────────────────────────────────────────────────

# Fases históricas del canal (promedio mensual N+R)
FASE_H1_2025_NOMBRE        = "H1 2025 — BASE"
FASE_H1_2025_NR            = "~130K"
FASE_H1_2025_SUBTITULO     = "prom. mensual Ene–Jun 25"
FASE_H1_2025_DESCRIPCION   = "Canal en modo «steady state»"
FASE_H1_2025_COLOR_BG      = "#3c78d8"

FASE_H2_2025_NOMBRE        = "H2 2025 — ACELERACIÓN"
FASE_H2_2025_NR            = "~174K"
FASE_H2_2025_SUBTITULO     = "prom. mensual Jul–Dic 25"
FASE_H2_2025_DESCRIPCION   = "+33% vs H1 · pico Nov: 177K"
FASE_H2_2025_COLOR_BG      = "#188038"

FASE_Q1_2026_NOMBRE        = "Q1 2026 — RECUPERACIÓN"
FASE_Q1_2026_NR            = "~135K"
FASE_Q1_2026_SUBTITULO     = "121.8K → 135.3K → 148.9K (Ene–Mar 26) · YTD +15.4%"
FASE_Q1_2026_DESCRIPCION   = "Gap vs plan: −29.7%→−14.1% (+15pp MoM). Apr: tormenta perfecta (Pandora lag 0.2 + PUSH saturación + JOURNEY canibalizadores)"
FASE_Q1_2026_COLOR_BG      = "#e37400"

FASE_TARGET_NOMBRE         = "TARGET AGO 26"
FASE_TARGET_NR             = "~240K"
FASE_TARGET_SUBTITULO      = "+61% vs Q1-26 promedio"
FASE_TARGET_DESCRIPCION    = "5 meses · ~+10% MoM compuesto"
FASE_TARGET_COLOR_BG       = "#7627bb"

# Drivers de crecimiento H2 2025
# Fuente: KPI context §A1–A9 + analizar-OC_Comms_context.md §A,§C + Comms_OC data
# PRINCIPIO: cada driver tiene su evidencia de KPI Y su evidencia de comms
DRIVERS_H2_2025 = [
    (
        "EMAIL channel: el motor oculto validado en Abr-26 — OR 26.7%, +17,980 UI en 1 campaña",
        "KPI: Apr-26 confirmó que el canal EMAIL es el de mayor OR del portafolio. "
        "COMMS: La campaña MLM-ML-I-EG-UCR-MTK-CAMP-NIA-DEB-CARD-2 (EMAIL, Abr-26) generó "
        "+17,980 USER_INC con OR 26.7% — la mejor performance de canal individual desde "
        "Sep-25 (CC_MARA +50,277). EMAIL históricamente muestra OR 15-26% (vs Push 5-13%) "
        "pero recibe solo 30-35 comms/mes vs 120+ de Push. "
        "H2-25 pudo haber sido aún mayor si EMAIL hubiera recibido la misma densidad de campañas. "
        "Insight del Relojero Suizo: 10× más comms de Push que de EMAIL, pero EMAIL tiene "
        "5× mejor OR. La asignación de recursos está sistemáticamente invertida. "
        "[Comms_OC Abr-26 · analizar-OC_Comms Modo 14 ranking_multidim Canal]"
    ),
    (
        "Activación Always On escalada — comms + KPI alineados",
        "KPI: Base RR creció de ~110K (Ene-25) a ~175K (Jul–Nov-25). ROAS pico 13x en Ago-25. "
        "Pandora acumuló 42.3K N+R al CPA más bajo del portafolio ($2.0 USD). "
        "COMMS: Nov-25 (mejor mes de volumen) registra OR 13.1% — consistente con el patrón "
        "de que OR > 12% correlaciona con ROAS > 5x. "
        "Pandora en quincena S2: CPA $1.4 USD (3× más eficiente que el baseline de $2.0). "
        "WPP ACT: +60% Lift Q4-25. La ecuación: más comms bien calibradas → más TEST → OR alto → USER_INC alto → ROAS alto."
        " [KPI context §A1 · Comms context §A1,§C2 · Comms_OC Nov-25]"
    ),
    (
        "Estacionalidad favorable (Jul–Nov) — IS alto amplifica cada comm enviada",
        "KPI: IS Ago 1.15, Sep 1.09, Oct 1.05 → tres meses consecutivos sobre la media anual. "
        "DRW: +24% NR MoM en Buen Fin solo por prints adicionales. "
        "COMMS: Con IS alto, el mismo número de comunicaciones genera más TEST → más SHOWN → más OPEN. "
        "Pandora en quincena de Ago-25 generó CPA $1.4 — el dato de Comms más bajo del año. "
        "IS 1.15 × OR 13%+ = stack multiplicador: cada $1 invertido en comms vale 1.15× más en ese mes."
        " [KPI context §AE1,§AE2 · Comms context §E1,§A2]"
    ),
    (
        "Ucrania escalado: reach 75% navegantes, OR > 12%, USER_INC máximo",
        "KPI: Push paid ROAS pico histórico 13.0x en Ago-25 ($4.3 CPA). "
        "COMMS: El motor fue el targeting de navegantes — 2× lift vs no-navegantes (Comms context §C1). "
        "Configuración Push MYI CBK $125: ROAS 10.5x, lift 0.06%. Recargas: ROAS 56x. "
        "Cuando el equipo subió reach de navegantes de 55% → 75% (cambio de capeo 4→2 días, Feb-26), "
        "los TEST aumentaron 20% sin incrementar comms enviadas — más reach por el mismo número de campañas. "
        "La palanca no era enviar más comms, era enviar mejor."
        " [KPI context §A1 · Comms context §C1,§D1,§F1]"
    ),
    (
        "Triggerización comportamental: 3× conversión en comms by-trigger vs batch",
        "KPI: N+R incrementales consistentes en H2-25. Carrito abandonado: 3× conversión vs batch. "
        "COMMS: Las campañas basadas en comportamiento (drop, instalación, inactividad) tienen "
        "estructuralmente HIGHER M_LIFT que batch. Dato clave: lift batch promedio −0.03% (H1-25) → "
        "+0.01% (H2-25) después de migrar a triggers. Pandora trigger carrito: CPA $4.2 vs batch $5.3. "
        "Implicación directa: en la tabla Comms_OC, las campañas con mayor M_LIFT son "
        "invariablemente las basadas en comportamiento o timing (quincena) — no las de blast masivo."
        " [KPI context §A4 · Comms context §D3,§C2]"
    ),
    (
        "Mejora de VPs e iteración rápida: lift 0.06% → 0.10% = +67% USER_INC con mismo presupuesto",
        "KPI: Lift de comms pasó de avg −0.03% (H1) a +0.01% (H2) tras iteración. "
        "COMMS: La variable que predice la mejora del KPI es el M_LIFT de las comunicaciones. "
        "Regla operativa confirmada en datos: Descuento % > monto $ → +26% N+R. "
        "Cupón Simple > Cupón Automático → ROAS 15× vs 3× (mismo costo, diferente formato). "
        "Recargas: lift 0.06% → 0.10% con misma audiencia. El impacto: esos 0.04pp adicionales "
        "× volumen de H2-25 (~5M sents/mes) = +2K NR/mes incrementales sin inversión adicional."
        " [KPI context §A7 · Comms context §D1,§D2,§D3]"
    ),
]

# Causas de caída Q1 2026
# Fuente: KPI context §B3, Monthly Mar-26 §7.3 + Comms_OC data (Nov-25 → Mar-26)
# PRINCIPIO: cada causa explica el KPI Y su firma en los datos de comms
CAUSAS_CAIDA_Q1_2026 = [
    (
        "Fatiga de VP MONIN/CBK — Oct-25 colapsó a OR 5.1% y +29K USER_INC tras pico Jul-Ago-Sep",
        "KPI: Oct-25 USER_INC total = +29,902 (vs +93,385 Sep-25 y +60,866 Ago-25). "
        "Caída del 68% en USER_INC con IS 1.03 (mes favorable). No fue estacional — fue VP fatiga. "
        "COMMS: Jul-25 estaba dominado por 3 campañas MONIN/CBK en el top 3 con lifts bajos "
        "(0.11–0.19%). En Ago-25, I-M-NR-CB-QUIN-A-0815 (quincena, fresh VP) rompió el patrón. "
        "En Oct-25 OR cayó a 5.1% — señal inequívoca de audiencia saturada con el mismo VP. "
        "El modelo del VP: MES 1-3 ID>0.8 (peak), MES 4-5 ID 0.2-0.5 (fatiga). "
        "El equipo nunca rotó el VP MONIN en tiempo — dejó correr la misma mecánica hasta "
        "que el Índice de Decaimiento cayó <0.3. La recuperación del canal en Nov-25 "
        "vino de cambiar el mix de VP, no de más volumen. "
        "[Comms_OC Jul-Oct 25 · OPTIMIZADOR Modo 10 vp_ciclo · analizar-OC_Comms Modo 14]"
    ),
    (
        "Pandora doble shock Mar-26 — firma en comms: OR cayó de 13% → 9%",
        "KPI: Calibrador UCR 0.6→0.2: −3K NR. Calibrador ACT 0.6→0.2: −4.2K NR. Total: −7.2K NR. "
        "COMMS: La firma de este shock es inequívoca en los datos de Comms_OC. "
        "Ene-26 (peor mes, Pandora 0.2): OR = 9.0%, USER_INC total = +14.2K. "
        "Feb-26 (Pandora ramp 0.6): OR = 13.2%, USER_INC = +22.1K. "
        "Diferencia: 4.2pp de OR = +7.9K USER_INC = diferencia en el ROAS (4.6× vs 5.2×). "
        "El calibrador de Pandora NO es solo un KPI de inversión — es un driver directo "
        "del Open Rate y el USER_INC de todo el canal. Sin protocolo de circuit-breaker, "
        "cada caída de calibrador replica este patrón. [§B5b, §C3 R3 · Comms_OC Jan/Feb-26]"
    ),
    (
        "Exclusión Churn Paid Ene-26: −20K NR → firma en comms: −277 campañas, −4.9M TEST",
        "KPI: Push ACT exclusión profit <0 = −20K NR (−55%) en Ene-26. "
        "COMMS: El impacto en la tabla de comunicaciones: Ene-26 bajó a ~847 comms "
        "(vs ~1,124 de Feb-26, cuando se recuperó el canal), con TEST de 23.4M "
        "(vs 28.7M en Feb). La audiencia excluida representaba el 38% de los sents. "
        "Cuando esa audiencia se reintegró parcialmente, el Open Rate subió de 9.0% → 13.2% "
        "y el USER_INC de +14.2K → +22.1K — confirmando que la audiencia excluida "
        "era de ALTA CALIDAD (respondía mejor). Correcto estratégicamente, "
        "pero el plan debió ajustarse anticipando el gap. [§B4 S6 · Comms_OC Jan/Feb-26]"
    ),
    (
        "Comparativo severo vs Q4-25 + IS estacional bajo (0.83 en Ene-26)",
        "KPI: Q4-25 fue el pico histórico. Q1-26 compara contra ese pico. Señal positiva: "
        "tendencia mejora 10pp cada mes (−29.7% → −14.1% vs plan). "
        "COMMS: El IS 0.83 de Enero explica parte del bajo OR (9.0%): con IS bajo, "
        "los usuarios están menos en 'modo transaccional' ML. La misma campaña enviada "
        "en Agosto (IS 1.15) generaría ~40% más NR que en Enero. "
        "La relación IS × OR es un multiplicador estructural: IS 0.83 × OR eficiencia "
        "= el 'piso' del canal en ese mes. No es el canal que falla — es el contexto. "
        "El canal mejora cuando el contexto estacional y las comms se alinean. [§AE2 · Comms context §E1]"
    ),
    (
        "Mantika en techo: OR de push baja a 5% cuando se superan 5 envíos por segmento",
        "KPI: ~80% N+R en MYI Paid single-target. 3.7M usuarios UCR sin opt-in Push. "
        "COMMS: El techo de Mantika es visible en los datos de comms. Nov-25 con 112 campañas "
        "Field = 1K NR incremental total (el mes de menor eficiencia). Ene-26 con 23 campañas = "
        "1.5K NR — el 20% del volumen generó el 150% del resultado. "
        "Regla demostrada: >5 pushes al mismo segmento = OR colapsa a 5% (Comms context §C1). "
        "El OR bajo no es falla del canal — es la señal de saturación. Cuando el OR cae "
        "de 13% a 5%, el USER_INC del mes siguiente cae proporcionalmente. "
        "La solución: mezcla de canales (WPP + RE + Push), no más push. [§A9 · Comms context §C1,§F2]"
    ),
    (
        "Sub-atribución CC: el canal es 5–8% mejor de lo que los KPIs muestran",
        "KPI: X-Channel AUC Mar-26: OC +13% eficiencia pese a −15.5% volumen. "
        "COMMS: El USER_INC en la tabla Comms_OC refleja el M_INC_USERS de cada campaña — "
        "que SÍ usa atribución de incrementalidad. Comparar el USER_INC de Comms "
        "con el N+R del dashboard revela el gap de atribución: si USER_INC total del mes "
        "suma, por ejemplo, +22.1K (Feb-26) pero el N+R incremental del canal muestra menos, "
        "la diferencia es atribución no capturada. Este gap del 5–8% es el 'found money' "
        "que el fix de medición recuperaría. [§B3, §C3 R7 · Comms_OC Feb-26]"
    ),
]

# Iniciativas a escalar
# Fuente: KPI context §C2,§C4 + Comms context §C,§D,§G + Comms_OC data
# PRINCIPIO: cada iniciativa especifica qué métrica de comms esperar al implementarla
INICIATIVAS_ESCALAR = [
    (
        "ESCALAR",
        "#188038",
        "WPP Ucrania — 6M usuarios sin opt-in: la palanca de TEST más grande",
        "KPI objetivo: +20K NR/mes con lift conservador 0.5%. "
        "COMMS: WPP es la única palanca que expande el universo de TEST sin saturar "
        "los segmentos existentes de Push. En Feb-26, el equipo alcanzó 28.7M TEST "
        "con las herramientas actuales. Con WPP Ucrania activo, ese número puede "
        "crecer 20%+ sin tocar las campañas de Push existentes. "
        "OR esperado WPP: similar al ACT Q4-25 (+60% Lift). "
        "USER_INC proyectado: +20K/mes una vez en escala. "
        "Señal de éxito en Comms_OC: nueva línea CANAL='WPP' con M_LIFT > 0.3% y USER_INC > 5K/mes. "
        "BC WPP Ucrania pendiente. [Comms context §C4 · KPI context §C4 O9]"
    ),
    (
        "ESCALAR",
        "#188038",
        "Triggerización comportamental — 3× M_LIFT vs batch demostrado en datos",
        "KPI: campañas by-trigger convierten 3–5× más que batch. "
        "COMMS: En la tabla Comms_OC, las campañas con mayor M_LIFT son invariablemente "
        "las de trigger (carrito abandonado, post-drop, inactividad). "
        "Pandora trigger carrito: CPA $4.2 vs batch $5.3 (−21%). "
        "La señal: si amplías triggers a favoritos e insurance, el M_LIFT promedio "
        "del canal sube del nivel actual (~0.1%) hacia el 0.2–0.3% — "
        "multiplicando el USER_INC total sin aumentar el número de comms enviadas. "
        "Kpi de control: Open Rate debe mantenerse > 12% en las nuevas campañas de trigger. "
        "[Comms context §D3 · KPI context §A4,§C4 O7]"
    ),
    (
        "ESCALAR",
        "#188038",
        "Gamification (multi-target) — rompe el techo de USER_INC del MYI único",
        "KPI: MYI single-target concentra ~80% del N+R. Techo estructural documentado. "
        "COMMS: En Comms_OC, las campañas de MYI comparten el mismo M_LIFT (~0.06–0.35%). "
        "Multi-target activaría segmentos sin M_LIFT actual (= 0): Gamification checkpoint "
        "y mecánicas no-MYI. El efecto esperado: nuevas líneas en Comms_OC con STRATEGIES "
        "diferentes a ACQUISITION/ACTIVATION, con USER_INC positivo donde hoy es 0. "
        "Señal de éxito: CHANNELS_METRICS diversificado en la tabla de campañas del mes. "
        "[Comms context §G · KPI context §C4]"
    ),
    (
        "ESCALAR",
        "#188038",
        "Nuevos RE ML (carrito/favoritos) — +TEST sin costo extra de comms",
        "KPI: ~10M navegadores en alta intención. RE DRW peak 0.070% eficiencia. "
        "COMMS: RE es el canal con mejor ARRIVED/TEST ratio del portafolio "
        "(los usuarios que ven el RE casi siempre lo reciben). Nuevos espacios "
        "en carrito y favoritos añaden TEST sin enviar más comunicaciones — "
        "aumentan el denominador del OR y por tanto el USER_INC total. "
        "Señal de éxito en Comms_OC: nuevas líneas con CANAL='RE - FAVORITOS' "
        "o 'RE - CARRITO' con TOTAL_SHOWN/TOTAL_TEST > 85% (alta visibilidad). "
        "[Comms context §C3 · KPI context §C4 O2,O3]"
    ),
    (
        "ACELERAR",
        "#1a73e8",
        "Velocidad de A/B testing — el OR y el M_LIFT son los KPIs de iteración",
        "KPI: lift pasó de −0.03% (H1-25) a +0.01% (H2-25) con iteración. "
        "COMMS: La columna M_LIFT en Comms_OC es la fuente de verdad de cuáles "
        "campañas funcionan. Con 2–4 tests/semana (benchmark industria), el equipo "
        "puede identificar las configuraciones ganadoras en 2 meses vs los 6 actuales. "
        "Métrica de control: número de campañas con M_LIFT > 0.1% en el mes "
        "debe crecer de ~5 actuales a 15+ para llegar al benchmark Nubank/Grab. "
        "[Comms context §G,§F1 · KPI context §A7]"
    ),
]

# Iniciativas a parar o pivotar
# Fuente: KPI context §C3 + Comms context §F2,§G + Comms_OC data
# PRINCIPIO: cada parada/pivote tiene un umbral de Comms que lo activa
INICIATIVAS_PARAR_PIVOTAR = [
    (
        "PARAR",
        "#d93025",
        "Campañas con M_LIFT negativo > 2 semanas — están quemando audiencia",
        "KPI: avg lift −0.03% antes de la iteración de H2-25. "
        "COMMS: La tabla Comms_OC muestra el M_LIFT de cada comunicación. "
        "Regla operativa concreta: cualquier campaña con M_LIFT < 0% por 2 semanas "
        "consecutivas → parar inmediatamente. No solo no genera USER_INC — "
        "quema el pool de audiencia y baja el OR del canal completo. "
        "El Open Rate promedio del mes refleja el 'crédito' de reputación del canal: "
        "cada campaña con M_LIFT negativo lo erosiona para las campañas siguientes. "
        "Acción: filtrar en Comms_OC por M_LIFT < 0 → esas son las campañas a parar. "
        "[Comms context §G · KPI context §A7]"
    ),
    (
        "PARAR",
        "#d93025",
        "Más de 5 Push al mismo segmento/mes — OR cae a 5%, USER_INC colapsa",
        "KPI: punto de quiebre demostrado: >5 pushes = OR 5% en ese segmento. "
        "COMMS: La frecuencia de envíos es visible en Comms_OC — el número de comms "
        "enviadas al mismo CANAL/STRATEGY en un mes. Cuando hay >5 campañas de Push "
        "al mismo segmento, el Open Rate del siguiente grupo cae 60%. "
        "Nov-25 con 112 campañas Field = 1K NR incremental total. "
        "Ene-26 con 23 campañas = 1.5K NR — el 20% del volumen, 150% del resultado. "
        "Regla: máx 5 Push/mes por segmento. Para navegantes: 2 días entre envíos. "
        "Señal de alerta en Comms_OC: OR < 8% en campañas de Push → segmento saturado. "
        "[Comms context §C1,§F2 · KPI context §A9]"
    ),
    (
        "PIVOTAR",
        "#e37400",
        "Blast masivo a toda la base → targeting por Open Rate histórico del usuario",
        "KPI: usuarios que navegan ML convierten 2× más que los que no. "
        "COMMS: El Open Rate por campaña (TOTAL_OPEN / TOTAL_TEST en Comms_OC) "
        "es la señal más confiable de qué usuarios responden. "
        "Los usuarios que consistentemente abren = audiencia de alta propensión. "
        "Los que nunca abren = degradan el OR del canal y no generan USER_INC. "
        "El pivote: construir un segmento 'abre siempre' y priorizarlo en cada comm. "
        "Evidencia: Feb-26 (OR 13.2%) vs Ene-26 (OR 9.0%) = la diferencia no fue "
        "cuántas comms se enviaron, sino a quiénes. "
        "[Comms context §C1,§G · KPI context §A4]"
    ),
    (
        "PIVOTAR",
        "#e37400",
        "Pandora en seasonals (Hot Sale, BF) → Push navegantes + quincena S2",
        "KPI: Pandora en Hot Sale = CPA $10 vs $2.0 baseline (5× peor). "
        "COMMS: El M_LIFT de las campañas Pandora en seasonals colapsa porque los "
        "usuarios ya están en 'modo compra' — el incentivo no añade incrementalidad. "
        "Protocolo correcto: cuando IS < 0.90 o hay seasonal activo → "
        "apagar Pandora y redirigir budget a Push navegantes + quincena S2. "
        "El Open Rate y el USER_INC de Push en esas semanas es más alto "
        "que Pandora en seasonal. Regla absoluta sin excepción."
        "[Comms context §E1,§G,§F1 · KPI context §AE5]"
    ),
    (
        "URGENTE",
        "#7627bb",
        "Fix medición antes de escalar: USER_INC de Comms vs N+R del dash = el gap real",
        "KPI: X-Channel AUC Mar-26 OC +13% eficiencia. El canal es mejor de lo que parece. "
        "COMMS: La forma de cuantificar el gap de atribución es comparar "
        "el USER_INC total del mes en Comms_OC vs el N+R incremental del canal en el dashboard. "
        "Si USER_INC (Feb-26) = +22.1K pero el dashboard muestra un incremento menor, "
        "la diferencia ES el gap de atribución no capturado. "
        "Sin este fix, escalar los canales correctos es imposible — se optimiza "
        "sobre el denominador equivocado. Es el prerequisito de todo lo demás. "
        "[KPI context §B3,§C3 R7 · Comms_OC Feb-26 USER_INC vs NR dashboard]"
    ),
]

# Camino crítico (fuente: Context §Parte 0, Monthly Mar-26 §10)
CAMINO_CRITICO_DESDE   = "~149K (Mar-26 real) → ~133K Abr-26 D25 (impacto Pandora lag)"
CAMINO_CRITICO_HASTA   = "240K"
CAMINO_CRITICO_MESES   = 5
CAMINO_CRITICO_PERIODO = "Abr–Ago 2026"
CAMINO_CRITICO_CRECIMIENTO_PCT = "+61%"
CAMINO_CRITICO_MOM_COMPUESTO   = "~+10% MoM compuesto"
CAMINO_CRITICO_PALANCAS        = 5

# Camino crítico: (mes, NR target, palanca + TARGET de Comms para ese mes)
# Fuente: KPI context §Parte 0 + Comms context §A,§E + Comms_OC data
# PRINCIPIO: el N+R target de cada mes tiene un objetivo de comms que lo respalda
CAMINO_CRITICO_MESES_DATOS = [
    ("ABR 26",  "~133K",
     "⚠️ Tormenta perfecta: Pandora lag 0.2 + PUSH saturación + JOURNEY canibalizadores\n"
     "Palanca inmediata: EMAIL DEB-CARD sistematizar (OR 27%+) · apagar STOCK_MONEYINAM\n"
     "TARGET COMMS: EMAIL >1,200 comms · OR EMAIL > 23% · JOURNEY canibalizadores pausados"),
    ("MAY 26",  "~155K",
     "Pandora ramp-up 0.2→0.6 (si se activa en may-1) · WPP Ucrania arranque\n"
     "⚠️ Hot Sale (IS 0.87): EMAIL resiste mejor que PUSH en meses IS bajo\n"
     "TARGET COMMS: Pandora cal ≥ 0.4 · EMAIL OR > 20% · USER_INC > 18K"),
    ("JUN 26",  "~182K",
     "Pandora 0.6 estabilizado + WPP Ucrania escala + KYC audiencias Q2\n"
     "TARGET COMMS: Pandora cal ≥ 0.6 · EMAIL+PUSH mix balanceado · USER_INC > 25K"),
    ("JUL 26",  "~210K",
     "MeLi Placements (Favoritos + Home) + IS 1.08 LCDLF pre-arranque\n"
     "TARGET COMMS: OR > 13% (IS alto) · USER_INC > 28K · SHOWN > 25M"),
    ("AGO 26 🎯", "~240K",
     "Todas las palancas en velocidad de crucero · IS 1.15\n"
     "TARGET COMMS: OR > 13% · USER_INC > 30K · Stack = LCDLF + Pandora 0.8+ + EMAIL+PUSH+WPP"),
]

CAMINO_CRITICO_HIPOTESIS = (
    "[URGENTE] EMAIL DEB-CARD sistemático en quincena S2 de cada mes (+12-18K NR — "
    "OR 23-27% demostrado en Mar-Abr 26 vs 3-5% PUSH · sin inversión adicional) · "
    "[URGENTE] Pandora recuperación cal 0.2→0.6 (+7K/mes — Comms_OC firma: OR 9%→13%) · "
    "[URGENTE] Apagar JOURNEY canibalizadores + STOCK_MONEYINAM (+5K NR/mes liberado) · "
    "WPP Ucrania (+20K/mes cuando live — USER_INC nueva línea CANAL=WPP) · "
    "Rotación VP MONIN→CBK_QUIN (romper fatiga — premium timing 2-3× en quincena) · "
    "MeLi Placements Favoritos+Home (+6K/mes Q3 — SHOWN/TEST > 85% en RE nuevos) · "
    "KYC audiencias 6× conversión (+8K/mes al madurar) · "
    "Fix atribución CC: +6K 'found money' (X-Channel AUC OC +13% Mar-26 — §C3 R7)."
)

CAMINO_CRITICO_RIESGO_PRINCIPAL = (
    "[RIESGO ACTIVO HOY] Pandora en 0.2 + PUSH saturación = tormenta perfecta en Mayo (IS 0.87). "
    "Sin EMAIL como sustituto, el NR de Mayo caerá a ~120-130K — 30K bajo el camino crítico. "
    "El Single Point of Failure no es WPP (largo plazo) — es el lag de Pandora que se siente ahora. "
    "Señal de alerta accionable: si en May D1-7 el USER_INC de EMAIL no supera 3K "
    "→ el canal no está compensando Pandora → escalar WPP ACT como emergencia."
)

# Principios CRM (fuente: Context §Parte 0 - Principios, benchmarks industria)
PRINCIPIOS_CRM = [
    (
        "① Velocidad de experimentación > perfección",
        "Nubank, Rappi y Grab corren 15–20 tests por mes, no 3–4. El aprendizaje "
        "compuesto de tests rápidos supera a la campaña perfecta que tarda semanas "
        "en lanzar. <strong>MLM está en ese camino, pero lleva retraso.</strong> "
        "El backlog de A/Bs debe mantenerse lleno para evitar el gap del Q1."
    ),
    (
        "② El reach sostenible es comportamental, no demográfico",
        "Los canales que mantienen crecimiento YoY usan modelos de propensión "
        "para encontrar al «usuario siguiente listo para activar», no blast a toda "
        "la base. <strong>Mantika + Bandit es el análogo en MLM — la pregunta es "
        "velocidad de adopción.</strong>"
    ),
    (
        "③ La medición incorrecta destruye más valor que la mala ejecución",
        "Si atribuyes mal, optimizas el canal equivocado. El fix de CC incrementales "
        "puede «encontrar» 5–10% de N+R que ya estás generando pero no "
        "contabilizando. <strong>MLM debe llegar ahí urgente — el fix de CC "
        "incrementales es el primer paso crítico para operar con la misma lógica que MLB.</strong>"
    ),
    (
        "④ Medición incremental como estándar de decisión",
        "MLB toma decisiones de inversión basadas en incrementalidad medida, no en "
        "atribución last-click. Esto les permite saber exactamente qué cada lever "
        "genera en N+R adicional. "
        "<strong>MLM debe llegar ahí urgente.</strong>"
    ),
    (
        "⑤ Mix OC vs Orgánico — la tesis del «shift activo»",
        "MLB tiene 48% Orgánico vs MLM 68%. No es que MLB perdió orgánico — es que "
        "hizo crecer los canales controlables más rápido que el orgánico. El mismo "
        "patrón aplica al Plan 1.5M: <strong>Orgánico no baja en absoluto, pero OC "
        "y POM crecen más rápido.</strong> El 19.1% objetivo de OC es alcanzable "
        "siguiendo el mismo playbook que Brasil ejecutó entre 2022 y 2024."
    ),
]

PRINCIPIOS_BRECHA_OPORTUNIDAD = (
    "MLB lleva ~2 años de ventaja en madurez de CRM. MLM no necesita reinventar — "
    "necesita ejecutar el mismo playbook con velocidad y disciplina operativa. "
    "Las iniciativas del plan (WPP Ucrania, Bandit, Gamification, Atribución) son "
    "exactamente los movimientos que MLB hizo en su momento. La diferencia será la "
    "velocidad y el músculo de ejecución."
)

# Palancas del Plan 1.5M OC (fuente: Context §C4, Monthly Mar-26 §10)
PALANCAS_PLAN_1_5M = [
    {
        "numero":     "1",
        "nombre":     "WPP Ucrania Always On",
        "descripcion": "6M usuarios UCR sin opt-in Push. Always On escalado + WPP + "
                       "segmentación comportamental (Mantika). "
                       "Lift conservador 0.4% = piso defensible. "
                       "Ver: docs/NR_impact_methodology.md §Palanca 1",
        "eta":        "Abr-26",
        "nr_impacto": "+20K/mes",
        "blocker":    "BC WPP aprobado; atribución GA/REs",
        "color":      "#f9ab00",
    },
    {
        "numero":     "2",
        "nombre":     "Gamification (checkpoint + multi-target)",
        "descripcion": "MYI single-target tiene techo documentado (~80% NR en MYI). "
                       "Checkpoint y multi-target activan el segmento que no responde a MYI. "
                       "Ver: docs/NR_impact_methodology.md §Palanca 2",
        "eta":        "May-26",
        "nr_impacto": "+12K/mes",
        "blocker":    "Features Gami E&G ≠ Gami Negocio",
        "color":      "#f9ab00",
    },
    {
        "numero":     "3",
        "nombre":     "Nuevos Espacios ML (Favoritos / Carrito / Home)",
        "descripcion": "~10M navegadores en alta intención de compra. "
                       "RE en estos espacios captura usuarios que ya interactúan con ML. "
                       "Piso = primeros 60 días post-lanzamiento. "
                       "Ver: docs/NR_impact_methodology.md §Palanca 3",
        "eta":        "Jun-26",
        "nr_impacto": "+6K/mes al escalar",
        "blocker":    "Acuerdos ML · Roadmap Producto Q2",
        "color":      "#f9ab00",
    },
    {
        "numero":     "4",
        "nombre":     "Pandora: Ramp Up + CC Attribution + Incentivos",
        "descripcion": "Always On UCR 85% (+4.5K) + ACT 85% (+6K) = +10.5K combinado. "
                       "Actualmente BLOQUEADO por calibrador en 0.2 (−7.2K NR/mes perdidos). "
                       "Ver: docs/NR_impact_methodology.md §Palanca 4",
        "eta":        "Q2–Q3",
        "nr_impacto": "+3K/mes por track",
        "blocker":    "Calibrador 0.2 → necesita subir a ≥0.6",
        "color":      "#f9ab00",
    },
    {
        "numero":     "5",
        "nombre":     "Segmentación por Valor: KYC, FS not-in-app, Meli+",
        "descripcion": "~10M KYC (6x conversión validada en tests). "
                       "Piso conservador solo con KYC, descuento 20% por incertidumbre de escala. "
                       "FS not-in-app (~4.1M) y Meli+ (~720K) son upside adicional. "
                       "Ver: docs/NR_impact_methodology.md §Palanca 5",
        "eta":        "May–Jun",
        "nr_impacto": "+8K/mes al madurar",
        "blocker":    "Análisis reach audiencias · Medición Corp",
        "color":      "#f9ab00",
    },
]

PALANCA_TRACK_0 = {
    "numero":     "0",
    "nombre":     "Atribución CC Incrementales",
    "descripcion": "N+R que YA SE GENERA pero no se atribuye. "
                   "Sin este fix las palancas 1-5 se optimizan sobre denominador incorrecto. "
                   "Cálculo: 5% × 149K (Mar-26) = 7.5K → piso 7K. "
                   "Ver: docs/NR_impact_methodology.md §Track 0",
    "eta":        "Urgente Q1-Q2",
    "nr_impacto": "+6K «found» N+R",
    "blocker":    "En revisión MKT Corp",
}

# Quick wins (próximas 4 semanas)
# Actualizado con Cross-Signal Insights de OPTIMIZADOR v4.0 — 27 Abr 2026
# Patrón 3 (saturación PUSH) + Patrón 4 (EMAIL como timing driver) + Patrón 2 (familia STOCK)
QUICK_WINS = [
    (
        "🔴 URGENTE: EMAIL sistematizar — OR 23-27% vs PUSH 3-5%: el motor oculto más grande del portafolio",
        "[Cross-Signal Pattern 4 — Timing/Canal como driver real] "
        "Abr-26 confirma: EMAIL DEB-CARD OR 23.6-27.2% (5-8× mayor que PUSH). "
        "Solo 786 comms EMAIL/mes vs 1,631 PUSH — la asignación está invertida. "
        "MONEYINHI2 y DEB-CARD (EMAIL) son los top performers del portafolio. "
        "Acción: duplicar comms EMAIL en Mayo D8-16 (quincena S2). Costo: $0. "
        "Estimado: +12-18K NR/mes adicionales si se lleva a 1,500+ comms EMAIL. "
        "[Comms_OC Mar-Abr 26 · Comms Skill Modo 14 ranking_multidim Canal]"
    ),
    (
        "🔴 URGENTE: Apagar JOURNEY canibalizadores + simplificar familia STOCK",
        "[Cross-Signal Pattern 2 — Efecto Familia] "
        "Familia flows_..._STOCK: MONEYINHI2 genera 56% del USER_INC total de la familia. "
        "STOCK_MONEYINAM (Abr: +25 UI) compite por la misma audiencia que el ganador. "
        "JOURNEY CARABO + MST2MP confirmados canibalizadores (§63). "
        "Acción: pausar STOCK_MONEYINAM + JOURNEY canibalizadores esta semana. "
        "Recovery: +5-8K NR/mes (audiencia liberada para MONEYINHI2 + eliminación NR negativo). "
        "[Comms Skill Modo 17 familia_campanas · comms_classification_config.json]"
    ),
    (
        "🟡 Restaurar Pandora a ≥0.4 — lag de 4-6 semanas ya está activo",
        "[Cross-Signal Pattern 6 — Lag de calibrador] "
        "Pandora bajó a 0.2 el 18-Mar. El colapso de Abr (+63 USER_INC) es exactamente "
        "el lag esperado. El peor mes todavía viene: Mayo IS 0.87 + Pandora 0.2 = riesgo crítico. "
        "Acción: restaurar calibrador UCR a 0.4+ en la quincena S1 de Mayo. "
        "Estimado: +3-5K NR/mes por cada 0.2 de calibrador recuperado. "
        "[KPI context §B5b · X-Channel AUC OC +13% Mar-26 pese a caída volumen]"
    ),
    (
        "🟡 Rotar VP: MONIN fatigado → Cashback en quincena S2 Mayo",
        "+3-5K NR recuperados. Comms_OC confirma fatiga MONIN (ID < 0.3 consistente). "
        "La campaña I-M-NR-CB-QUIN-A-0815 (Ago-25): +5,657 UI con VP Cashback fresco. "
        "Premium de timing quincena: 2-3× vs misma campaña en S1. "
        "Acción: lanzar Cashback en D8-D16 Mayo — combina VP fresco + timing IS_semanal 1.25+. "
        "[Comms Skill Modo 15 timing_codificado · Comms context §D1]"
    ),
    (
        "🟡 Solicitar inversión incremental OC — X-Channel AUC +13% justifica el caso",
        "+4K NR/mes por cada 10% adicional de budget. "
        "OC generó X-Channel AUC +13% en Mar-26 mientras el volumen caía -15.5%. "
        "Las comms que siguen activas son cada vez más eficientes — no hace falta más comms, "
        "hace falta más budget para escalar las que funcionan (EMAIL + PUSH curado). "
        "Con YTD +15.4% sobre plan, existe el caso de negocio para pedir presupuesto incremental "
        "sin tocar POM — que también cumple y no debe recortarse. "
        "[KPI context §B3 · X-Channel AUC §C3]"
    ),
]

QUICK_WINS_TOTAL_RANGO = (
    "+20-30K N+R/mes adicionales en Mayo — "
    "EMAIL sistematizar (+12-18K) + apagar ruido/canibalizadores (+5-8K) + Pandora lag (+3-5K). "
    "Sin inversión adicional. Solo ejecución esta semana."
)

ESTRUCTURALES_H2_2026 = [
    ("WhatsApp Ucrania live",                  "+25K N+R/mes — la palanca más grande del plan (Q2)"),
    ("Nuevas mecánicas de activación (Gamification)", "Rompe el techo del incentivo único actual (Q2–Q3)"),
    ("Presencia en MercadoLibre (Home, Favoritos, Búsqueda)", "~10M usuarios en momento de alta intención de compra (Q2–Q3)"),
    ("Pandora + usuarios con historial financiero (KYC)", "Segmentos de 6x mayor conversión aún sin atacar (Q2–Q3)"),
    ("Fix de medición de atribución",          "Prerequisito para escalar todo lo demás correctamente (Q1-Q2)"),
]

OBJETIVO_REALISTA = (
    "~240K N+R/mes en Ago-26 · "
    "Escenario URGENTE (Mayo): email sistematizar + canibalizadores apagados → ~155K. "
    "Escenario BASE Ago-26: 220K (EMAIL QUIN + WPP + Pandora recuperado + Bandit). "
    "Escenario OPTIMISTA Ago-26: 240K (todas las palancas en tiempo + IS 1.15 amplificando). "
    "MOTOR CONFIRMADO: EMAIL DEB-CARD en quincena [OR 23-27%, datos reales Abr-26]. "
    "RIESGO ACTIVO: si Pandora no sube a ≥0.4 en Mayo → camino crítico se retrasa a Oct-26. "
    "[OPTIMIZADOR v4.0 · 7 Patrones Cross-Signal aplicados · 27-Abr-2026]"
)


# ──────────────────────────────────────────────────────────────────────────────
# ESTACIONALIDAD OC+UCR
# Fuente: skills/context.md §AE1–§AE6 · §A1 (share%) · §B1 (2026 absolutos)
# Skill aplicado: MODO_ESTACIONALIDAD / PASO_3C ejecutado al 14-Abr-2026
# IS = NR_canal_mes / NR_canal_promedio_anual. Promedio OC+UCR 2025 ≈ 16.5% share.
# Actualizar anualmente cuando cierre el año y los IS reales estén disponibles.
# ──────────────────────────────────────────────────────────────────────────────

# Tabla de IS mensual: (mes, is_valor, nivel, evento_principal, accion_operativa, is_num)
# nivel: "alto" IS≥1.10 | "medio" IS 0.95–1.09 | "bajo" IS 0.85–0.94 | "critico" IS<0.85
# is_num: valor numérico para cálculo del gráfico / ordenamiento
OC_IS_MENSUAL = [
    ("Enero",      "0.83", "critico", "Post-estacional Q4 · Pool saturado",
     "Testear nuevas audiencias · VP ligeros · no escalar"),
    ("Febrero",    "0.85", "bajo",    "Recuperación inicio · Día Amor/Amistad (14 Feb)",
     "Always On conservador · campaign TDD si hay VP"),
    ("Marzo",      "0.99", "medio",   "Recuperación gradual · +3 días calendario vs Feb",
     "Escalar RE (más días de prints) · Pandora normal"),
    ("Abril",      "0.88", "bajo",    "Semana Santa (varía) · Caída consumo digital",
     "Reducir en semana Santa · conservar budget para Mayo"),
    ("Mayo",       "0.87", "bajo",    "Hot Sale (última sem) · Pandora CPA $2→$10 (+400%)",
     "PAUSAR Pandora · escalar solo DRW/RE · redirigir budget a POM"),
    ("Junio",      "1.01", "medio",   "Overflow Hot Sale · Normalización del canal",
     "Reactivar Pandora · Pandora quincena $1.4 CPA"),
    ("Julio",      "1.08", "alto",    "Inicio H2 · Verano · ROAS histórico pre-pico",
     "ESCALAR OC · Push + Pandora full · preparar LCDLF"),
    ("Agosto",     "1.15", "alto",    "LCDLF inicio · ROAS pico 13x (Ago-25 histórico)",
     "MÁXIMA INVERSIÓN OC del año · presupuesto adicional justificado"),
    ("Septiembre", "1.09", "alto",    "LCDLF peak · Independencia 15-16 sept (festivo D0)",
     "Escalar · compensar caída D15-16 en D14 y D17"),
    ("Octubre",    "1.03", "medio",   "LCDLF cierre · Preparación Buen Fin",
     "Mantener escala · activar audiencias pre-Buen Fin"),
    ("Noviembre",  "0.98", "medio",   "Buen Fin 3ra sem · DRW +24% NR · Pandora CPA $10",
     "ESCALAR DRW · PAUSAR Pandora en semana BF · reactivar post-BF"),
    ("Diciembre",  "0.87", "bajo",    "Aguinaldo 1-15 Dic (pico TPV) · Post-Nav saturación",
     "Push fuerte 1–15 Dic · reducir inversión 16–31"),
]

# 3 insights clave de estacionalidad (Bain-level, máximo impacto)
OC_ESTACIONALIDAD_INSIGHTS = [
    (
        "El mismo presupuesto en Agosto genera 40% más NR que en Enero",
        "IS Ago = 1.15 vs IS Ene = 0.83 → diferencia de 39% en eficiencia por peso invertido. "
        "Un presupuesto flat durante el año implica subsidiar los meses malos con el potencial de los buenos. "
        "La decisión de mayor impacto no es cuánto invertir, sino cuándo. "
        "(§AE2, §A1 — ROAS Ago-25: 13x vs promedio anual ~6x)",
    ),
    (
        "Pandora en quincena = CPA $1.4 USD. Pandora en Hot Sale/Buen Fin = CPA $10 USD",
        "La misma plataforma, el mismo canal — pero con diferencia de 7x en costo por usuario "
        "según el momento del mes o el evento. Operar Pandora sin calendario estacional "
        "es un gasto innecesario del 30–400% según el período. "
        "(§AE3: CPA quincena $1.4 · §AE5: Hot Sale/BF CPA $10 · §A6 validado)",
    ),
    (
        "LCDLF–Buen Fin–Aguinaldo (Ago–Dic): 5 meses de IS sobre promedio que no se repiten",
        "IS Ago 1.15 · IS Sep 1.09 · IS Oct 1.03 · IS Nov 0.98 · IS Dic 0.87 (1ra quincena alta). "
        "Este es el único período del año con 3 meses consecutivos sobre IS 1.0. "
        "Perder agosto por calibradores bajos de Pandora es perder el 15% de eficiencia extra "
        "que nunca se recupera en otro mes del año. (§AE2, §AE5)",
    ),
]

# Campañas y su impacto cuantificado en OC+UCR
OC_CAMPANAS_IMPACTO = [
    ("LCDLF",     "Ago–Oct · 11 semanas", "IS 1.08–1.15 · ROAS pico 13x (Ago-25)",
     "Escalar OC. El mejor período del año.", "#188038"),
    ("Hot Sale",  "Última sem Mayo + 1ra Jun", "Pandora CPA $10 (+400% vs $2 normal) · IS OC 0.87",
     "PAUSAR Pandora. Redirigir budget DRW/RE.", "#d93025"),
    ("Buen Fin",  "3ra sem Noviembre",  "DRW +24% NR · Pandora CPA $10 · CPM -30% (POM beneficia)",
     "DRW escala; PAUSAR Pandora en semana BF.", "#e37400"),
    ("Quincenas", "Días 14–16 y 29–31 (cada mes)", "CPA Pandora $1.4 (vs $2.0 promedio) · CVR +2.3pp",
     "SIEMPRE activar Pandora en quincenas.", "#1a73e8"),
]

# Patrones semanales dentro del mes (IS_semanal — derivado §A8 + §B2 + razonamiento estructural)
# Formato: (semana_label, dias, is_rango, driver, implicacion, nivel)
OC_PATRONES_SEMANA = [
    ("Semana 1", "D1–D7",  "IS ≈ 0.75–0.82", "Post-quincena 2 del mes anterior. Usuarios en pausa.",
     "Inversión mínima. Testear VPs. No escalar.", "critico"),
    ("Semana 2", "D8–D16", "IS ≈ 1.20–1.30", "QUINCENA 1 (D14-16): CVR +2.3pp · Pandora CPA $1.4 · TPV +30%",
     "PICO del mes. Escalar todos los canales OC. Pandora obligatoria.", "alto"),
    ("Semana 3", "D17–D22", "IS ≈ 0.88–0.95", "Valle inter-quincenal. Usuarios post-pago esperando.",
     "Reducir vs S2. Mantener Always On base.", "bajo"),
    ("Semana 4+", "D23–fin", "IS ≈ 1.05–1.15", "QUINCENA 2 (D29-31): segundo pico (solo en meses de 30-31 días)",
     "Escalar en D28–31. Pandora siempre activa en quincenas.", "medio"),
]

# Patrones día de la semana por tipo de canal OC+UCR
# Formato: (dia, descripcion_oc_crm, descripcion_pom_paid, nivel_oc, nivel_pom)
# nivel: "optimo" | "bueno" | "regular" | "evitar"
OC_DOW_PATTERNS = [
    ("Lunes",     "Bueno: vuelta al trabajo → ML activo",         "Regular: foco laboralvuelta al trabajo",    "bueno",   "regular"),
    ("Martes",    "MUY BUENO: mejor OR email + engagement ML [inf]", "Bueno: intent-based ↑, CPM moderado",   "optimo",  "bueno"),
    ("Miércoles", "MUY BUENO: pico OR email LATAM · ML nav ↑ [inf]", "ÓPTIMO: mejor conversión Google/intent","optimo",  "optimo"),
    ("Jueves",    "Bueno: ML nav activa",                         "Bueno: balance reach/conversión",           "bueno",   "bueno"),
    ("Viernes",   "Regular: menor ML nav tarde",                  "Bueno: reach ocio ↑ (TikTok/Meta)",        "regular", "bueno"),
    ("Sábado",    "EVITAR: OR email −40% · Push OR −40% [inf]",  "Muy bueno REACH · OJO: conversión MP baja","evitar",  "bueno"),
    ("Domingo",   "EVITAR: OR email −50% · Push OR −50% [inf]",  "Muy bueno REACH (TikTok/Meta peak)",       "evitar",  "optimo"),
]

# Sub-canal/Medio: estacionalidad específica (lo más granular disponible)
# Formato: (medio, patron_mensual_clave, mejor_semana, mejor_dow, evento_critico, regla_oro, dato_o_inf)
OC_SUBCANAL_MEDIO_SEASONAL = [
    # ── PANDORA ──────────────────────────────────────────────────────────────
    ("PANDORA",
     "IS muy volátil: 1.30+ en quincenas · IS ~0.10 en Hot Sale y Buen Fin",
     "S2 (D14-16) + S4 (D29-31) — quincenas",
     "Lun–Vie",
     "Quincena: CPA $1.4 (vs $2.0 avg). Hot Sale/BF: CPA $10 (+400%)",
     "Pandora SIEMPRE en quincenas. NUNCA en Hot Sale ni Buen Fin. Mayor variación CPA por evento del portafolio.",
     "dato §A6"),
    # ── PUSH (UCR E&G + RECURRING) ─────────────────────────────────────────
    ("PUSH UCR/ACT",
     "Sigue IS del canal (Jul-Sep alto · Ene-Feb bajo) + quincena boost en S2/S4",
     "S2 quincena (pico) · S4 segundo pico",
     "Lun–Jue (OR más alto en días laborales)",
     "Quincena: usuarios con efectivo → mayor propensión a activar TDD/pagos. LCDLF: audiences ampliadas.",
     "Max 2.49 pushes/mes/usuario (§A9). >5 pushes = 5% OR punto de quiebre. Quincenas: push extra siempre.",
     "dato §A9"),
    # ── EMAIL (UCR E&G + RECURRING) ─────────────────────────────────────────
    ("EMAIL OC",
     "Sigue IS del canal. Menos estacional que Pandora/Push.",
     "S2 (quincena) · S1 baja (inbox saturado inicio de mes)",
     "Mar–Mié (benchmark LATAM email: OR pico Martes-Miércoles 7-9am)",
     "Buen Fin: emails informativos de oferta funcionan bien (menos CPA-sensitive). Hot Sale: comunicar deals.",
     "Enviar Martes-Miércoles. Evitar Viernes-Domingo. Max 1 email/semana en períodos normales.",
     "inf §AE8"),
    # ── REAL ESTATES DRW ────────────────────────────────────────────────────
    ("RE — DRW (Drawer)",
     "IS correlaciona con navegación ML. Amplificación en Buen Fin (+24% NR)",
     "S2 + Buen Fin (3ra sem Nov = pico absoluto de DRW)",
     "Lun–Jue (ML navigation días laborales)",
     "Buen Fin: +24% NR confirmado [dato §A13]. LCDLF: awareness → más navegación ML → más impresiones DRW.",
     "DRW es el mejor canal OC en Buen Fin mientras Pandora está prohibida. Siempre activar.",
     "dato §A13"),
    # ── REAL ESTATES QA ─────────────────────────────────────────────────────
    ("RE — QA (Quick Access)",
     "IS estable (menos volátil que DRW). Canibalización BNPL activa (-29% prints §C3 R1)",
     "S2 (quincena, leve boost)",
     "Lun–Jue",
     "Buen Fin: -16% NR (CONTRA la tendencia de DRW) [dato §A13]. Canibalización QA-BNPL: riesgo activo.",
     "NO escalar QA en Buen Fin — redirigir ese budget a DRW. Monitorear prints vs BNPL.",
     "dato §A13, §C3 R1"),
    # ── WPP UCR ─────────────────────────────────────────────────────────────
    ("WPP UCR",
     "Canal nuevo (Q2-26 launch). Sin histórico mensual. [Patrón proyectado]",
     "S4 (D29-31) estimado — mensajería más activa fines de semana",
     "Sáb–Dom (WhatsApp: uso personal, tiempo libre)",
     "Canal inverso a Push en DoW. WPP tiene mayor engagement en tiempo libre vs Push en tiempo laboral.",
     "Validar patrón con primeros 2 meses de datos antes de optimizar scheduling. VPU potential alto.",
     "inf §AE8, §C4 O9"),
    # ── WPP ACT (OWN CHANNELS RECURRING) ───────────────────────────────────
    ("WPP ACT",
     "ACT: base de usuarios ya activos → menor estacionalidad que UCR adquisición",
     "S2 + S4 (quincenas — usuarios con efectivo están más receptivos a mensajes de activación)",
     "Sáb–Dom",
     "LCDLF: awareness → re-activación por WPP es oportuna. Buen Fin: comunicar ofertas.",
     "WPP ACT puede escalar 2x/mes sin saturar (base de usuarios diferente a UCR).",
     "inf §AE8, §B4 S6"),
]

# Calendario de decisiones: próximos 3 meses (actualizar cuando cambie el mes actual)
# Desde: Abril 2026
OC_PROXIMOS_3_MESES = [
    ("Mayo 2026",      "0.87 🔴",
     "Hot Sale (última semana)",
     "PAUSAR Pandora toda la semana BF · Escalar DRW/RE · Redirigir $$ Pandora → POM ADQ",
     "Sin acción: Pandora quema $MM a CPA $10 (5x ineficiente vs normal)"),
    ("Junio 2026",     "1.01 🟢",
     "Post-Hot Sale · Quincena 1 (D14-16) y Quincena 2 (D29-30)",
     "Reactivar Pandora completa · Activar Pandora en quincenas D14-16 y D29-30 (CPA $1.4)",
     "Oportunidad: recuperar NR perdido en Mayo con quincenas optimizadas"),
    ("Julio 2026",     "1.08 🟢",
     "Inicio H2 · Pre-LCDLF · Preparar audiencias LCDLF",
     "ESCALAR inversión OC · Push E&G + Pandora al máximo · Activar audiencias LCDLF",
     "Julio es la rampa de aceleración: quien llega débil a Agosto pierde el pico 13x ROAS"),
]

# ──────────────────────────────────────────────────────────────────────────────
# DATOS ESTRATÉGICOS POM
# Fuente: skills/analizar-Optimizar_Performance_KPIs_context.md §A3,A5,A12,A13,B1,B3,B5a,C1,C3
# Última validación: 13-Abr-2026 — Skill MODO_POM aplicado
# ──────────────────────────────────────────────────────────────────────────────

# Fases históricas del canal POM
FASE_POM_H1_2025_NOMBRE      = "H1 2025 — BASE"
FASE_POM_H1_2025_NR          = "~86K"
FASE_POM_H1_2025_SUBTITULO   = "prom. mensual Ene–Jun 25"
FASE_POM_H1_2025_DESCRIPCION = "CPA estable $13–15 · ROAS 3.8–4.0 · CPM estacional Ene aprovechado"
FASE_POM_H1_2025_COLOR_BG    = "#2F9E8F"

FASE_POM_H2_2025_NOMBRE      = "H2 2025 — ESCALAMIENTO"
FASE_POM_H2_2025_NR          = "~91K"
FASE_POM_H2_2025_SUBTITULO   = "prom. mensual Jul–Dic 25"
FASE_POM_H2_2025_DESCRIPCION = "+6% vs H1 · Google iOS launched · Web POM 3%→24%"
FASE_POM_H2_2025_COLOR_BG    = "#188038"

FASE_POM_Q1_2026_NOMBRE      = "Q1 2026 — EXPLOSIÓN"
FASE_POM_Q1_2026_NR          = "~197K"
FASE_POM_Q1_2026_SUBTITULO   = "201.3K → 185.9K → 204.5K (Ene–Mar 26)"
FASE_POM_Q1_2026_DESCRIPCION = "+100% vs plan · ACT +16% MoM Mar · TikTok ACQ calibrador en revisión"
FASE_POM_Q1_2026_COLOR_BG    = "#e37400"

FASE_POM_TARGET_NOMBRE       = "TARGET AGO 26"
FASE_POM_TARGET_NR           = "~250K"
FASE_POM_TARGET_SUBTITULO    = "mínimo 240K · con mix validado e incrementalidad confirmada"
FASE_POM_TARGET_DESCRIPCION  = "+27% vs Q1-26 · ACT >40% del mix · plataformas diversificadas"
FASE_POM_TARGET_COLOR_BG     = "#7627bb"

# Drivers de crecimiento H2-2025 → Q1-2026
# Fuente: §B4 S7 (Ene-26), §B5a, §A12, §A13
DRIVERS_POM_CRECIMIENTO = [
    (
        "CPM de Enero −20%: palanca estacional ejecutada a máxima potencia",
        "Ene-26: inversión +30% sobre base → extrae el máximo del mercado barato. "
        "CPA efectivo de Enero ~10% más eficiente que el promedio del año. "
        "Comportamiento validado 2024 y 2025 — replicable todos los eneros (§A13)."
    ),
    (
        "Google iOS: lanzado con señal muy positiva",
        "W01-26: calibrador subido significativamente → +7K NR estimados solo en la primera semana. "
        "iOS entrega VPU +70% vs Android — los usuarios de iPhone tienen mayor valor de vida predicho. "
        "Segmento históricamente sub-invertido en POM MLM (§B5a, §C2)."
    ),
    (
        "TikTok Smart+2.0: tecnología de optimización mejorada",
        "+8K NR adicionales en Ene-26 vs la versión anterior. "
        "Smart+2.0 mejora la selección de audiencia automáticamente en tiempo real, "
        "reduciendo el CPA sin cambiar el presupuesto (§B4 S7)."
    ),
    (
        "POM ACT: scale-up sostenido con +46% de inversión",
        "Mar-26: TikTok ACT + DV360 + Liftoff escalados → +16K NR (+8% MoM). "
        "ACT tiene una dinámica diferente a ACQ: menor dependencia de calibradores de plataforma "
        "y mejor perfil de retención a largo plazo (§B3)."
    ),
    (
        "Web POM: canal completamente establecido",
        "De 3% share (Dic-24) a 24% share (Dic-25): multiplica 8x en un año. "
        "Web POM diversifica el riesgo de concentración en apps y captura un segmento "
        "de usuarios con mayor intención declarada (§A12)."
    ),
]

# Causas de tensión / riesgos Q1-2026
# Fuente: §B3, §B5a, §C3 R5
CAUSAS_TENSION_POM_Q1_2026 = [
    (
        "TikTok ACQ: menor incrementalidad confirmada con calibrador a la baja",
        "23-Feb-26: calibrador TikTok ACQ 2.25→1.35 = −24.2K NR/mes (−13%). "
        "No es solo un ajuste técnico: es evidencia de que los usuarios adquiridos vía TikTok ACQ "
        "se estarían activando igualmente por otros canales. Sin test hold-out, la cifra es estimada "
        "pero la señal es real (§B5a, §C3 R5)."
    ),
    (
        "Concentración de riesgo: un solo calibrador mueve −24K NR",
        "TikTok domina el mix de POM ADQ. Cuando su algoritmo de optimización ajusta, "
        "el impacto en el total del canal es inmediato y masivo. "
        "Cualquier operación de escala global (Nubank, Grab) distribuye riesgo en ≥4 plataformas — "
        "MLM POM opera con concentración >60% en una (§B5a)."
    ),
    (
        "Moloco ACT también en revisión de calibrador",
        "16-Mar-26: Moloco ACT 0.47→0.21 (−55%) = −2.6K NR. "
        "Señal de que no solo TikTok está siendo ajustado — hay un patrón de revisión de "
        "incrementalidad en múltiples plataformas simultáneamente (§B5a)."
    ),
    (
        "Incrementalidad no medida con rigor en todo el canal",
        "Sin test hold-out activo, no se sabe con certeza cuántos de los ~200K NR/mes de POM "
        "son verdaderamente incrementales vs usuarios que se habrían activado por otros canales. "
        "Esta es la diferencia entre un canal de $1M/mes eficiente y uno que quema presupuesto."
    ),
    (
        "Mix ADQ-heavy sin confirmación de calidad incremental ← el riesgo más estructural",
        "POM ADQ domina el volumen pero es el canal con mayor exposición a decrementos de "
        "incrementalidad. Mientras ACT crece (+16%) y se diversifica, ADQ concentra el riesgo. "
        "El mix ideal al que apuntan operaciones globales equivalentes es 40-60% ACT."
    ),
]

# Acciones: escalar, acelerar, pivotar, parar
# Fuente: §A5 (VP tests), §B3, §B5a, §C1, §C2, §C3
INICIATIVAS_ESCALAR_POM = [
    (
        "ESCALAR",
        "#188038",
        "TikTok ACT — el canal que ya demostró retorno sostenible",
        "Mar-26: +16K NR con solo +46% de inversión. ACT tiene menor dependencia "
        "de calibradores y mejor retención que ADQ. Cada peso adicional aquí genera "
        "NR de mayor calidad incremental (§B3)."
    ),
    (
        "ESCALAR",
        "#188038",
        "Google iOS — el segmento premium sub-invertido",
        "VPU +70% vs Android (§C2). Señal muy positiva desde W01-26. "
        "Los usuarios de iOS tienen mayor ticket promedio y mejor retención a M3. "
        "Incrementar presupuesto iOS es la palanca de mayor VPU disponible en POM."
    ),
    (
        "ESCALAR",
        "#188038",
        "Cashback 10% TDD como VP dominante en todos los canales",
        "Ganó vs descuento 50% con 92% de significancia estadística: CPA $7.2 vs $7.9. "
        "Psicología del porcentaje supera al monto fijo. Estandarizar como VP base "
        "de toda la operación POM (§A5)."
    ),
    (
        "ESCALAR",
        "#188038",
        "Diversificación de plataformas ACQ: Meta + más Google",
        "Reducir concentración en TikTok ACQ del >60% actual hacia ≤40%. "
        "Meta ACQ y Google Android son plataformas maduras con menor riesgo de "
        "calibración masiva y audiencias complementarias a TikTok."
    ),
    (
        "ACELERAR",
        "#1a73e8",
        "DV360 ACT — canal con menor riesgo de plataforma que TikTok",
        "DV360 opera sobre inventory de Google, más estable y diversificado. "
        "Acelerar antes de que TikTok ACT también reciba presión de calibración. "
        "La diversificación dentro de ACT es tan importante como en ACQ."
    ),
]

INICIATIVAS_PARAR_PIVOTAR_POM = [
    (
        "PARAR",
        "#d93025",
        "Escalar TikTok ACQ sin evidencia de incrementalidad confirmada",
        "Con el calibrador en 1.35 y la señal de menor incrementalidad, cada peso adicional "
        "en TikTok ACQ tiene probabilidad alta de ser gasto sin retorno neto. "
        "No escalar hasta completar el test de incrementalidad."
    ),
    (
        "PARAR",
        "#d93025",
        "VP de descuento 50% en TDD",
        "Perdió vs Cashback 10% con 92% de significancia estadística. "
        "CPA $7.9 vs $7.2 del ganador. No hay caso de negocio para seguir usando el "
        "incentivo más costoso cuando el más barato convierte mejor (§A5)."
    ),
    (
        "PIVOTAR",
        "#e37400",
        "Estrategia ADQ-heavy → estrategia ACT-first",
        "La evidencia de Q1-26 es clara: ACT crece (+16%), ADQ se calibra a la baja. "
        "Pivotar el mix hacia ≥40% ACT no significa reducir ADQ — significa que el "
        "crecimiento incremental viene de ACT mientras ADQ se estabiliza."
    ),
    (
        "PIVOTAR",
        "#e37400",
        "Maximizar volumen bruto → maximizar NR incremental confirmado",
        "POM ya está 100%+ sobre plan. El siguiente nivel no es más volumen — "
        "es saber cuánto de ese volumen es realmente incremental. "
        "Las mejores operaciones globales optimizan por NR incremental, no por NR total."
    ),
    (
        "URGENTE",
        "#7627bb",
        "Test de incrementalidad (hold-out) antes de definir presupuesto Q3",
        "Sin un grupo de control, no se puede saber si los 200K NR/mes de POM son "
        "100% incrementales o si parte se hubieran activado por OC u Orgánico. "
        "Un test mal ejecutado es mejor que no tener test. Q3 no puede presupuestarse "
        "en ciego (análogo al fix atribución CC en OC)."
    ),
]

# Camino hacia sostenibilidad: defender y calificar 200K+
POM_CRITICO_DESDE         = "~197K (Q1-26 promedio)"
POM_CRITICO_HASTA         = "~250K"
POM_CRITICO_MESES         = 5
POM_CRITICO_PERIODO       = "Abr–Ago 2026"
POM_CRITICO_DESCRIPCION   = "Mínimo 240K · óptimo 250K con mix ACT>40% e incrementalidad confirmada"
POM_CRITICO_CRECIMIENTO   = "+27% vs Q1-26 · ~+5% MoM compuesto"

POM_CRITICO_MESES_DATOS = [
    ("ABR 26",  "~205K", "TikTok ACT estabiliza\nCashback 10% como VP estándar"),
    ("MAY 26",  "~218K", "Google iOS full scale\n+ Test incrementalidad"),
    ("JUN 26",  "~230K", "ACT >40% del mix\nDiversificación plataformas ACQ"),
    ("JUL 26",  "~240K", "Decisiones Q3 informadas\npor incrementalidad real"),
    ("AGO 26 🎯", "~250K", "250K sostenible\nmix validado · mínimo 240K"),
]

POM_CRITICO_HIPOTESIS = (
    "TikTok ACT full scale (+15K/mes) · "
    "Google iOS full scale (+8K/mes, VPU +70% — §C2) · "
    "Diversificación plataformas ACQ (+5K/mes) · "
    "VP optimizado CBK 10% (+3K NR por mejor conversión — §A5) · "
    "TikTok ACQ: ±24K según resultado de test de incrementalidad (§B5a)."
)

POM_CRITICO_RIESGO_PRINCIPAL = (
    "Test de incrementalidad sin ejecutar: si Q3 se presupuesta sin este dato, "
    "se puede escalar TikTok ACQ (+$MM) en un canal que no genera NR incremental neto. "
    "Riesgo #2: concentración — si TikTok (ACQ + ACT) tiene un problema de plataforma, "
    "POM pierde >60% de su volumen sin respaldo disponible inmediato."
)

# Principios de operaciones POM de clase mundial
PRINCIPIOS_POM = [
    (
        "① Incrementalidad como estándar de decisión — no last-click",
        "Uber, Spotify y Netflix miden el valor real de cada canal con tests hold-out: "
        "¿cuántos de estos usuarios se hubieran adquirido sin esta inversión? "
        "El modelo last-click sobreestima sistemáticamente los canales de retargeting. "
        "<strong>MLM POM opera en un escenario donde +100% sobre plan puede significar "
        "mucho volumen incremental o mucho gasto mal atribuido — sin el test, no se sabe.</strong>"
    ),
    (
        "② iOS es el canal premium — VPU +70% vs Android",
        "Apple App Store users tienen LTV sistémicamente mayor en fintechs LATAM. "
        "Nubank y Rappi descubrieron esto en 2021 y movieron mix iOS a ≥30% del budget POM. "
        "MLM iOS mostró señal muy positiva en W01-26. "
        "<strong>Cada mes que iOS está sub-invertido es VPU premium que se deja sobre la mesa.</strong>"
    ),
    (
        "③ ACT > ADQ en ROAS ponderado por retención a M3",
        "Las operaciones de UA más eficientes de LATAM (Nubank, iFood) priorizan "
        "usuarios que ya tienen intención de activar sobre usuarios completamente nuevos. "
        "ACT tiene menor dependencia de calibradores de plataforma, mejor retención M3 y "
        "mayor probabilidad de hábito (uso frecuente en primeros 30 días). "
        "<strong>MLM ACT está creciendo a +16% MoM: este es el canal a construir.</strong>"
    ),
    (
        "④ Diversificación de plataformas como gestión de riesgo operacional",
        "Meta, Google, TikTok y DSPs tienen dinámicas de calibración independientes. "
        "Grab distribuye >5 plataformas con ninguna >25% del budget — un calibrador "
        "de TikTok no puede mover -24K NR/mes en un portafolio diversificado. "
        "<strong>MLM POM tiene >60% en TikTok: un riesgo de concentración que ninguna "
        "operación de escala global aceptaría.</strong>"
    ),
    (
        "⑤ La frecuencia de los primeros 30 días predice el LTV a 12 meses",
        "Análisis de cohortes de Rappi y Nubank muestran que usuarios con >3 transacciones "
        "en los primeros 30 días tienen 3-4x mayor retención a M12. "
        "El incentivo del VP debe diseñarse para generar ese segundo y tercer uso, "
        "no solo el primero. <strong>Cashback 10% TDD ya mostró 92% de significancia "
        "sobre descuento 50% — el VP correcto genera el hábito, no solo la conversión.</strong>"
    ),
]

PRINCIPIOS_POM_BRECHA = (
    "Las operaciones POM de clase mundial llevan 3-4 años de ventaja en rigor de "
    "medición de incrementalidad. MLM no necesita reinventar — necesita ejecutar el mismo "
    "playbook: test hold-out → decisión de mix → diversificación de plataformas. "
    "El volumen (+197K/mes) ya existe. El siguiente paso es saber cuánto de ese volumen "
    "es realmente incremental — y eso decide si 2026 es un año de eficiencia o de gasto."
)

# Palancas del plan POM
PALANCAS_PLAN_POM = [
    {
        "numero":     "1",
        "nombre":     "TikTok ACT — scale continuo",
        "descripcion": "Ya demostrado: +16K NR/mes con +46% inversión en Mar-26. "
                       "Menor dependencia de calibradores de plataforma, mejor retención. "
                       "Ver: docs/NR_impact_methodology.md §POM Palanca 1",
        "eta":        "Abr-26",
        "nr_impacto": "+15K/mes",
        "blocker":    "Presupuesto ACT Q2 aprobado",
        "color":      "#2F9E8F",
    },
    {
        "numero":     "2",
        "nombre":     "Google iOS — escalar el canal premium",
        "descripcion": "VPU +70% vs Android. Señal muy positiva W01-26. "
                       "Sub-invertido históricamente. Incrementar antes de Q3. "
                       "Ver: docs/NR_impact_methodology.md §POM Palanca 2",
        "eta":        "Abr-May-26",
        "nr_impacto": "+8K/mes",
        "blocker":    "Budget iOS separado de Android en plan",
        "color":      "#2F9E8F",
    },
    {
        "numero":     "3",
        "nombre":     "Diversificación plataformas ACQ",
        "descripcion": "Meta ACQ + Google Android + DV360 ACT para reducir concentración "
                       "en TikTok de >60% a ≤40%. Gestión de riesgo operacional. "
                       "Ver: docs/NR_impact_methodology.md §POM Palanca 3",
        "eta":        "May-Jun-26",
        "nr_impacto": "+5K/mes",
        "blocker":    "Setup creatives Meta · activación DV360",
        "color":      "#2F9E8F",
    },
    {
        "numero":     "4",
        "nombre":     "VP estándar: Cashback 10% TDD en toda la operación",
        "descripcion": "Ganó vs descuento 50% con 92% de significancia: CPA $7.2 vs $7.9. "
                       "Estandarizar como VP base genera el hábito de uso, no solo la conversión. "
                       "Ver: docs/NR_impact_methodology.md §POM Palanca 4",
        "eta":        "Abr-26",
        "nr_impacto": "+3K/mes",
        "blocker":    "Aprobación VP Q2 con CBK 10% como default",
        "color":      "#2F9E8F",
    },
    {
        "numero":     "5",
        "nombre":     "Liftoff ACT + Moloco ACT — plataformas de respaldo",
        "descripcion": "Liftoff y Moloco funcionan como balance a TikTok ACT. "
                       "Moloco ACT ajustó calibrador en Mar-26: recuperar nivel previo "
                       "una vez que el ajuste de incrementalidad sea validado.",
        "eta":        "May-26",
        "nr_impacto": "+4K/mes",
        "blocker":    "Resultado calibrador Moloco Q2 · Liftoff escala",
        "color":      "#2F9E8F",
    },
]

PALANCA_TRACK_0_POM = {
    "numero":     "0",
    "nombre":     "Test de Incrementalidad (hold-out group)",
    "descripcion": "Sin este test, las decisiones de presupuesto Q3 son en ciego. "
                   "Define si TikTok ACQ genera ±24K NR realmente incrementales. "
                   "Una semana de test correctamente diseñado responde la pregunta más "
                   "importante de toda la operación POM 2026.",
    "eta":        "Urgente Q2",
    "nr_impacto": "Decisión ±24K NR",
    "blocker":    "Diseño metodológico · MKT Corp aprobación",
}

POM_QUICK_WINS = [
    (
        "Estandarizar Cashback 10% TDD como VP base en todas las plataformas",
        "+3K NR/mes — ya probado con 92% de significancia estadística. Sin nuevo canal, sin nuevo presupuesto."
    ),
    (
        "Aumentar inversión en Google iOS (actualmente sub-invertido)",
        "+3-5K NR/mes — señal muy positiva desde Enero. VPU +70% vs Android: el mejor ROI del portafolio POM."
    ),
    (
        "Congelar escala de TikTok ACQ hasta resultado del test de incrementalidad",
        "Evita gastar presupuesto en canal con incrementalidad cuestionada. Ahorra para reasignar a canales confirmados."
    ),
    (
        "Activar TikTok ACT a nivel de Mar-26 como estándar de Abril",
        "+5K NR/mes — el nivel de ACT en Mar-26 ya demostró funcionar. Mantenerlo como piso."
    ),
    (
        "Lanzar test hold-out de incrementalidad (1 semana, 10% del presupuesto)",
        "Responde la pregunta más importante de 2026 para POM. Q3 no puede presupuestarse sin este dato."
    ),
]

POM_QUICK_WINS_TOTAL = "+11K NR/mes adicionales en Abril — sin nuevo canal, con decisiones informadas"

POM_ESTRUCTURALES_H2_2026 = [
    ("TikTok ACT full scale", "+15K NR/mes sostenible con menor riesgo de plataforma (Q2)"),
    ("Google iOS full scale", "+8K NR/mes con VPU +70% vs Android — canal premium (Q2)"),
    ("Diversificación plataformas", "Reducir concentración TikTok a ≤40%, gestión de riesgo (Q2–Q3)"),
    ("Decisión TikTok ACQ basada en incrementalidad", "±24K NR según resultado del test hold-out (Q2)"),
    ("Mix ACT ≥40% del total POM", "Modelo más sostenible, menos dependiente de calibradores externos (Q3)"),
]

POM_OBJETIVO_REALISTA = "Objetivo Ago-26: ~250K NR/mes · mínimo 240K · escenario base 240K (TikTok ACT + iOS + diversificación) · escenario optimista 250K+ (todas las palancas + TikTok ACQ incremental confirmado)"

# ──────────────────────────────────────────────────────────────────────────────
# ESTACIONALIDAD POM
# Skill aplicado: MODO_ESTACIONALIDAD PASO_3C · Fuente: §AE1-§AE6, §A3, §A12, §A13, §B1
# POM es el canal MÁS sensible al CPM estacional (TikTok/Meta/Google siguen el mercado).
# OC/CRM puede mantener eficiencia con CPM variable → POM no.
# IS = NR_canal_mes / NR_canal_promedio_anual. Promedio POM 2025 ≈ 85K NR/mes (§A3).
# Actualizar anualmente. IS 2026 distorsionado por cambio de mix y Google iOS.
# ──────────────────────────────────────────────────────────────────────────────

# IS mensual POM: (mes, is_valor, nivel, evento, accion, is_num)
POM_IS_MENSUAL = [
    ("Enero",      "1.05", "medio",   "CPM −20% estacional · escalar +30% inversión",
     "ESCALAR TikTok/Meta/Google. El mejor mes de H1 para POM."),
    ("Febrero",    "0.99", "medio",   "Sin evento mayor · CPM regresa a niveles normales",
     "Mantener Always On. VP Cashback 10% como estándar."),
    ("Marzo",      "1.06", "medio",   "Recuperación gradual · más días calendario vs Feb",
     "Escalar ACT que viene con momentum desde Ene-Feb."),
    ("Abril",      "0.87", "bajo",    "Semana Santa · CPM sube por competencia offline",
     "Reducir inversión semana Santa. Conservar Google iOS (menos CPM-sensible)."),
    ("Mayo",       "1.15", "alto",    "HOT SALE (última sem) · intención de compra máxima H1",
     "MÁXIMA INVERSIÓN POM H1. CPM no cae pero conversión es la más alta del semestre."),
    ("Junio",      "1.05", "medio",   "Overflow Hot Sale · CPM normaliza",
     "Mantener escala de mayo. Rebalancear ACQ/ACT."),
    ("Julio",      "0.90", "bajo",    "Verano · CPM caro (TikTok/Meta +15-20% vs promedio)",
     "REDUCIR inversión TikTok/Meta. Mantener Google iOS (intent-based, menos CPM-volátil)."),
    ("Agosto",     "1.03", "medio",   "LCDLF inicio · awareness masivo beneficia POM moderadamente",
     "Mantener. El awareness de LCDLF amplía pool para POM ACT."),
    ("Septiembre", "1.05", "medio",   "LCDLF peak · Independencia 15-16 sept (festivo)",
     "Mantener escala. Pausa inversión D15-16 (festivo)."),
    ("Octubre",    "1.02", "medio",   "LCDLF cierre · CPM empieza a bajar · Pre-Buen Fin",
     "Preparar creativos y presupuesto para Buen Fin. CPM ya bajando: moment ideal."),
    ("Noviembre",  "1.20", "alto",    "BUEN FIN (3ra sem) · CPM −30% · PICO ABSOLUTO POM",
     "MÁXIMA INVERSIÓN DEL AÑO. CPM −30% + intención máxima = mejor CPA del portafolio."),
    ("Diciembre",  "0.95", "medio",   "Aguinaldo 1-15 Dic (buena conversión) · CPM navideño sube 16-31",
     "Escalar 1-15 Dic (aguinaldo = usuarios con efectivo). Reducir 16-31 (CPM +40%)."),
]

# 3 insights clave POM estacionalidad
POM_ESTACIONALIDAD_INSIGHTS = [
    (
        "Buen Fin = el evento del año para POM: CPM −30% × intención máxima = CPA histórico",
        "Noviembre IS 1.20 (confirmado: Nov-25 = 96.8K vs promedio 85K = IS 1.14, §A3). "
        "CPM −30% en medios pagados (TikTok, Meta, Google) × intención de compra en su pico anual. "
        "CPA estimado en BF: ~$12 USD vs promedio $14-15 (−15%). "
        "Es el único mes donde POM y OC coinciden ambos sobre IS 1.0 pero con dinámicas opuestas: "
        "OC limita Pandora (CPA $10) mientras POM escala al máximo. (§AE5, §A3, §AE1)"
    ),
    (
        "Enero: la única ventana H1 donde POM supera su promedio por CPM, no por demanda",
        "IS Enero ≈ 1.05 porque CPM cae −20% (estacional en TikTok/Meta/Google). "
        "No hay más demanda de activación — hay menos costo de adquisición. "
        "Táctica validada 2025: inversión +30% en enero = +13K NR extra vs promedio (§B4 S7). "
        "El mismo NR en enero cuesta 20% menos que en los meses siguientes. (§AE1, §B4 S7, §A13)"
    ),
    (
        "La paradoja del CPM: POM pierde eficiencia exactamente cuando OC la gana",
        "Julio-Verano: CPM TikTok/Meta +15-20% → IS POM 0.90. OC mantiene IS 1.08 (LCDLF). "
        "Semana Santa-Abril: CPM sube → IS POM 0.87. OC mantiene IS similar. "
        "Hot Sale-Mayo: CPM no baja pero intención sube → IS POM 1.15. OC cae a IS 0.87 (Pandora apagada). "
        "→ La asignación de presupuesto ideal rota entre canales según el mes: "
        "Mayo=POM máximo/OC mínimo · Agosto=OC máximo/POM moderado. (§AE1, §AE2)"
    ),
]

# Campañas con impacto cuantificado en POM
POM_CAMPANAS_IMPACTO = [
    ("BUEN FIN",   "3ra sem Noviembre",     "CPM −30% · IS 1.20+ · CPA ~$12 (vs $14-15 avg)",
     "MÁXIMA INVERSIÓN del año. Creativos de descuento/oferta.", "#0d5c2f"),
    ("HOT SALE",   "Última sem Mayo + 1ra Jun", "IS 1.15 · Intención de compra pico H1",
     "MÁXIMA INVERSIÓN H1. Escalar todos los subcanales.", "#188038"),
    ("Enero CPM",  "Enero completo",        "CPM −20% · IS 1.05 · Inversión +30% validada (§B4 S7)",
     "Escalar +30% sobre el CPM barato. Aprovechar el descuento.", "#1a73e8"),
    ("LCDLF",      "Ago–Oct · 11 semanas",  "IS 1.03–1.05 moderado · Awareness amplía pool ACT",
     "Escalar ACT. LCDLF beneficia más a OC que a POM.", "#e37400"),
    ("Semana Santa", "Abr (variable)",      "IS 0.87 · CPM sube · Conversión baja",
     "REDUCIR inversión. Conservar solo Google iOS.", "#d93025"),
]

# Próximos 3 meses POM (Mayo-Julio 2026)
POM_PROXIMOS_3_MESES = [
    ("Mayo 2026",  "1.15 🟢",
     "HOT SALE (última semana)",
     "MÁXIMA INVERSIÓN POM H1 · Todos los subcanales escalados · VP Cashback 10% en toda la operación",
     "Sin acción: se pierde el mejor mes de H1 con CPM competitivo y mayor intención de compra"),
    ("Junio 2026", "1.05 🟢",
     "Post-Hot Sale · Quincenas D14-16 y D29-30",
     "Mantener escala de Mayo · Rebalancear ACQ→ACT · Quincenas: leve boost en conversión",
     "Oportunidad: el overflow de Hot Sale extiende la ventana alta hasta mediados de Junio"),
    ("Julio 2026", "0.90 🟡",
     "Verano · CPM caro en TikTok/Meta",
     "REDUCIR TikTok/Meta (CPM +15-20%) · Mantener Google iOS (intent-based, menos CPM-volátil) · Priorizar ACT",
     "Si se mantiene inversión flat en julio vs mayo, el CPA sube ~20% por CPM. Mejor esperar Agosto."),
]

# Patrón semanal POM (menos quincena-driven que OC, más CPM-driven)
POM_PATRONES_SEMANA = [
    ("Semana 1", "D1–D7",  "IS ≈ 0.85–0.90",
     "Inicio mes. Menor intención post-quincena anterior. CPM estable.",
     "Inversión conservadora. Testear creativos.", "bajo"),
    ("Semana 2", "D8–D16", "IS ≈ 1.05–1.10",
     "Quincena 1 (D14-16): efecto menor en POM que en OC. "
     "POM no depende del payday directo como OC/CRM.",
     "Leve escala. Quincena: +5-10% en conversión vs valle.", "medio"),
    ("Semana 3", "D17–D22", "IS ≈ 0.90–1.00",
     "Valle inter-quincenal. POM mantiene mejor que OC (plataformas always-on).",
     "Mantener Always On. Menor reducción que OC.", "medio"),
    ("Semana 4+", "D23–fin", "IS ≈ 1.05–1.10",
     "Quincena 2 (D29-31): segundo pico moderado.",
     "Escalar D28-31 ligeramente. Efecto quincena < que en OC.", "medio"),
]

# DoW POM: distinción clave reach vs conversión para productos financieros
POM_DOW_PATTERNS = [
    ("Lunes",     "Bueno: intent post-weekend · Google inicio semana↑",    "Regular: TikTok/Meta tráfico bajo",   "bueno",   "regular"),
    ("Martes",    "MUY BUENO: conversión Google intent-based ★★★",         "Bueno: CPM más bajo · mejor ROAS",    "optimo",  "bueno"),
    ("Miércoles", "MUY BUENO: Google + DV360 peak conversión ★★★",         "Bueno: balance reach/coste",          "optimo",  "bueno"),
    ("Jueves",    "Bueno: intent activo todo el día",                       "Bueno: reach crece hacia fin semana", "bueno",   "bueno"),
    ("Viernes",   "Regular: conversión baja al caer la tarde",              "BUENO REACH: TikTok/Meta sube ★★",   "regular", "bueno"),
    ("Sábado",    "Regular: iOS activo · Android menor [inf]",              "ALTO REACH: TikTok/Meta peak ★★★",   "regular", "optimo"),
    ("Domingo",   "Regular: intent financiero bajo",                        "ALTO REACH: TikTok/Meta peak ★★★",   "regular", "optimo"),
]

# Sub-canal POM: estacionalidad granular
# Formato: (subcanal, patron_mensual, mejor_semana, mejor_dow, evento_critico, regla_oro, fuente)
POM_SUBCANAL_MEDIO_SEASONAL = [
    ("TikTok ACQ",
     "IS sigue CPM: 1.05 Ene · 1.15 May · 0.90 Jul · 1.20 Nov (BF). Calibrador 1.35 en revisión.",
     "S2 (D14-16 leve boost)", "Mar–Mié (conversión) · Vie-Dom (reach)",
     "Calibrador 2.25→1.35 = −24.2K NR/mes. Hot Sale/BF: pico de CPM bajo y conversión alta.",
     "No escalar sin test incrementalidad. Mejor oportunidad: Buen Fin + Enero CPM bajo.",
     "dato §B5a, §B3"),
    ("TikTok ACT",
     "IS similar ACQ pero más estable: menor dependencia de calibrador ACQ. Mar-26: +16% NR con +46% inv.",
     "S2 + S4 (quincenas moderadas)", "Vie-Dom (reach máximo para re-activación)",
     "Scale-up sostenido: +46% inversión → +16K NR (Mar-26). Hot Sale y BF = pico.",
     "ESCALAR con prioridad. Es el sub-canal de mayor crecimiento activo en Q1-26.",
     "dato §B3"),
    ("Google iOS",
     "IS estable + pico en Ene/Nov por CPM favorable. VPU +70% vs Android siempre.",
     "Toda la semana (intent-based = menos sensible a semana)", "Mar–Jue (intent-based ★★★)",
     "W01-26: señal muy positiva (§B5a). iOS = VPU +70% vs Android. Sub-invertido históricamente.",
     "Mantener inversión iOS incluso en julio (menos CPM-volátil que social). VPU premium siempre.",
     "dato §B5a, §C2"),
    ("Meta ACQ/ACT",
     "IS sigue CPM de Meta: 1.05 Ene · 1.15 May-Nov · 0.90 Jul. Muy correlacionado con TikTok.",
     "S2 + S4 (quincenas leve boost)", "Vie-Dom (reach) · Mar–Jue (conversión/CPC)",
     "Double Days: VP % siempre mejor que monto fijo en Meta (§C2). Hot Sale + BF = pico.",
     "VP porcentual (Cashback %) siempre sobre descuento fijo en creativos Meta.",
     "inf §AE8, §C2"),
    ("DV360 ACT",
     "IS moderado (display Google = menos volátil que social). Estabilidad > TikTok/Meta.",
     "S2-S3 (más constante que TikTok)", "Mar–Jue ★★",
     "Canal de balance de riesgo: cuando TikTok/Meta tienen CPM alto, DV360 mantiene eficiencia.",
     "Escalar en julio/Semana Santa cuando TikTok/Meta son caros. Canal de cobertura.",
     "inf §AE8"),
    ("Web POM",
     "IS estable todo el año (intent CPC, no CPM display). 3%→24% share Dic-25 (§A12).",
     "Toda la semana (búsqueda = intent on-demand)", "Lun–Vie ★★ (búsqueda laboral)",
     "Landing sin formulario +47% CTR (§C2). Hot Sale: tráfico de búsqueda de ofertas MP.",
     "Regla validada: landing sin formulario siempre. Estacionalidad menor — canal de intent puro.",
     "dato §A12, §C2"),
    ("Liftoff/Moloco ACT",
     "Calibrador Moloco en revisión (0.47→0.21 Mar-26). Liftoff escala en Q2.",
     "S2 (boost moderado)", "Mar–Jue [inf]",
     "Moloco ACT calibrador 0.47→0.21 (Mar-26) = −2.6K NR/mes. Liftoff como balance.",
     "Recuperar Moloco post-calibración Q2. Liftoff: escalar como diversificación vs TikTok.",
     "dato §B5a"),
]

# ──────────────────────────────────────────────────────────────────────────────
# FUNCIONES AUXILIARES DE HTML (privadas — uso interno del builder)
# ──────────────────────────────────────────────────────────────────────────────

def _html_badge(tipo_badge: str, color_bg: str) -> str:
    """
    Genera el HTML de un badge de acción (ESCALAR, PARAR, PIVOTAR, URGENTE, ACELERAR).

    Args:
        tipo_badge: Texto del badge ("ESCALAR", "PARAR", etc.)
        color_bg:   Color de fondo en hex

    Returns:
        str: HTML del badge con estilos inline
    """
    return (
        f'<span style="display:inline-block;padding:2px 8px;border-radius:4px;'
        f'background:{color_bg};color:#fff;font-size:10px;font-weight:700;'
        f'letter-spacing:0.5px;margin-right:8px;vertical-align:middle;">'
        f'{tipo_badge}</span>'
    )


def _html_section_title(title: str, subtitle: str = "", icon: str = "") -> str:
    """
    Genera el HTML del título de una sección con icono opcional y subtítulo.

    Args:
        title:    Título principal de la sección
        subtitle: Subtítulo opcional (se muestra debajo)
        icon:     Emoji o carácter de icono

    Returns:
        str: HTML del encabezado de sección
    """
    icon_html = f'<span style="margin-right:8px;font-size:18px;">{icon}</span>' if icon else ''
    subtitle_html = (
        f'<div style="font-size:11px;color:#666;font-weight:400;margin-top:2px;">'
        f'{subtitle}</div>'
    ) if subtitle else ''
    return (
        f'<div style="font-size:15px;font-weight:700;color:#1a2744;margin-bottom:12px;'
        f'padding-bottom:8px;border-bottom:2px solid #e8eaf0;">'
        f'{icon_html}{title}{subtitle_html}</div>'
    )


def _html_card(content_html: str, bg: str = "#fff",
               border_left: str = "", padding: str = "16px") -> str:
    """
    Genera el HTML de una tarjeta de contenido con borde izquierdo opcional.

    Args:
        content_html: HTML interno de la tarjeta
        bg:           Color de fondo
        border_left:  Color del borde izquierdo (si aplica)
        padding:      Padding CSS

    Returns:
        str: HTML de la tarjeta
    """
    border_style = f"border-left:4px solid {border_left};" if border_left else ""
    return (
        f'<div style="background:{bg};{border_style}border-radius:8px;'
        f'padding:{padding};box-shadow:0 1px 3px rgba(0,0,0,.08);">'
        f'{content_html}</div>'
    )


# ──────────────────────────────────────────────────────────────────────────────
# FUNCIÓN PRINCIPAL — BUILDER DE LA PESTAÑA OC+UCR
# ──────────────────────────────────────────────────────────────────────────────


# ── Helpers para el análisis dinámico de Comms × Corp Sub-canal (§83) ────────

def _classify_fm_subcanal_analysis(strategy: str, team: str, campaign_name: str = '') -> str:
    """Sub-canal FM — tabla §83 + regla UCR por nombre de campaña."""
    s   = (_cs(strategy) or '').upper()
    t   = (_cs(team)     or '').upper()
    ucr = 'UCR' in (_cs(campaign_name) or '').upper()
    # P0: SELLERS team con |USER_INC| > 250 — incluida pero marcada aparte
    if 'SELLERS' in t:
        return 'OTHERS_SELLERS'
    if ucr and any(x in t for x in ('ADHOC', 'INDIVIDUALS')):
        return 'UCR GEST'
    if ucr and any(x in t for x in ('OTHERS', 'CREDITS')):
        return 'UCR PRD'
    if s in ('UCRANIA', 'ACQUISITION') and any(x in t for x in ('CREDITS', 'OTHERS')):
        return 'UCR PRD'
    if s in ('UCRANIA', 'ACQUISITION') and any(x in t for x in ('ADHOC', 'INDIVIDUALS')):
        return 'UCR GEST'
    if s in ('ACTIVATION', 'OTHERS', 'RE-ACTIVATION'):
        return 'OC ACT'
    return 'OTROS'


def _classify_corp_subcanal_analysis(strategy: str, notif_type: str, team: str,
                                      substrategy: str = '', clasif_campaigns: str = '',
                                      campaign_name: str = '') -> str:
    """Sub-canal Corp — tabla §83 + regla UCR por nombre de campaña."""
    s   = (_cs(strategy)         or '').upper()
    nt  = (_cs(notif_type)       or '').upper()
    t   = (_cs(team)             or '').upper()
    ss  = (_cs(substrategy)      or '').upper()
    cl  = (_cs(clasif_campaigns) or '').upper()
    ucr = 'UCR' in (_cs(campaign_name) or '').upper()
    # P0: SELLERS team con |USER_INC| > 250 — incluida pero marcada aparte
    if 'SELLERS' in t:
        return 'OTHERS_SELLERS'
    if s in ('UCRANIA', 'ACQUISITION') and any(x in t for x in ('CREDITS', 'OTHERS')):
        return 'UCR PRD'
    if ucr and 'ADHOC' in t:
        return 'OWN CHANNELS ADHOC'
    if ucr and any(x in t for x in ('OTHERS', 'INDIVIDUALS', 'CREDITS')):
        return 'UCRANIA E&G'
    # ACQUISITION + SUBSTRATEGY UCRANIA/NEW/STOCK + ADHOC → OWN CHANNELS ADHOC
    if s == 'ACQUISITION' and 'ADHOC' in t and any(x in ss for x in ('UCRANIA', 'NEW', 'STOCK')):
        return 'OWN CHANNELS ADHOC'
    if 'ADHOC' in t:
        return 'OWN CHANNELS ADHOC' if cl == 'UCRANIA' else 'OWN CHANNELS RECURRING'
    if s == 'UCRANIA':
        return 'UCRANIA E&G'
    if s == 'OTHERS' and ss == 'OTHERS':
        return 'OWN CHANNELS RECURRING'
    if s in ('ACTIVATION', 'RE-ACTIVATION'):
        return 'OWN CHANNELS RECURRING'
    return 'OTROS'


def _compute_comms_analysis(comms_records: list, months_sorted: list):
    """Agrega records de Comms_OC por sub-canal Corp para análisis MTD y mes cerrado.

    Regla crítica: USER_INC Comms ≡ N+R para OC+UCR
    (comms_classification_config.json → metric_equivalences)

    Retorna dict con:
      · mtd: análisis MTD (mes en curso D1-Dref vs mes anterior D1-Dref)
      · closed: análisis mes cerrado (mes anterior completo vs mes anterior-anterior)
    """
    from collections import defaultdict
    import datetime as _dt

    if not comms_records or not months_sorted:
        return {'mtd': {}, 'closed': {}}

    # Determinar meses relevantes
    current_month  = months_sorted[-1]   # mes en curso (parcial)
    closed_month   = months_sorted[-2] if len(months_sorted) >= 2 else None
    prev_month     = months_sorted[-3] if len(months_sorted) >= 3 else None

    SUBCANALES    = ['UCRANIA E&G', 'OWN CHANNELS RECURRING', 'OWN CHANNELS ADHOC', 'UCR PRD']
    SUBCANALES_FM = ['UCR GEST', 'OC ACT', 'UCR PRD']

    def _day_of(record):
        sd = str(record.get('SENT_DATE', ''))[:10]
        try: return int(sd.split('-')[2])
        except: return 0

    def _month_of(record):
        return str(record.get('MONTH_ID', ''))

    # Día de referencia MTD: D-2 (atribución OC certificada).
    # Se usa D-2 en lugar del último día disponible para asegurar que los datos
    # de Torre Daily están estabilizados y la atribución por canal es confiable.
    import datetime as _dt2
    _d2_date   = _dt2.date.today() - _dt2.timedelta(days=2)
    _d2_day    = _d2_date.day
    _d2_month  = _d2_date.strftime('%Y%m')
    curr_days  = [_day_of(r) for r in comms_records if _month_of(r) == current_month]
    # Usar el último día disponible que no supere D-2
    _avail_d2  = [d for d in curr_days if d <= _d2_day] if _d2_month == current_month else curr_days
    mtd_ref_day = max(_avail_d2) if _avail_d2 else (max(curr_days) if curr_days else 0)
    # Fecha exacta para mostrar en el análisis
    mtd_ref_date_str = _d2_date.strftime('%d/%m/%Y') if _d2_month == current_month else (
        _dt2.date(_d2_date.year, int(current_month[4:6]), mtd_ref_day).strftime('%d/%m/%Y')
        if mtd_ref_day else ''
    )

    def _aggregate_period(month_id, max_day=None, use_fm=False):
        """Suma métricas por (subcanal, campaign_name) para un período.
        use_fm=False → clasifica por Corp sub-canal
        use_fm=True  → clasifica por FM sub-canal
        """
        result = defaultdict(lambda: defaultdict(lambda: {
            'user_inc': 0.0, 'sents': 0.0, 'opens': 0.0, 'n_rows': 0
        }))
        for r in comms_records:
            if _month_of(r) != month_id:
                continue
            if max_day and _day_of(r) > max_day:
                continue
            cn = _cs(r.get('CAMPAIGN_NAME_CLEAN')) or _cs(r.get('CAMPAIGN_NAME')) or ''
            if use_fm:
                sc = _classify_fm_subcanal_analysis(r.get('STRATEGY', ''), r.get('TEAM', ''), cn)
            else:
                sc = _classify_corp_subcanal_analysis(
                    r.get('STRATEGY', ''), r.get('NOTIFICATION_TYPE', ''), r.get('TEAM', ''),
                    r.get('SUBSTRATEGY', ''), r.get('CLASIF_CAMPAIGNS', ''), cn)
            cn  = _cs(r.get('CAMPAIGN_NAME_CLEAN')) or _cs(r.get('CAMPAIGN_NAME')) or 'UNKNOWN'
            entry = result[sc][cn]
            entry['user_inc'] += float(r.get('USER_INC') or 0)
            entry['sents']    += float(r.get('SENTS') or 0)
            entry['opens']    += float(r.get('TOTAL_OPEN') or 0)
            entry['n_rows']   += 1
        return result

    def _subcanal_totals(agg, sc_list=None):
        totals = {}
        for sc in (sc_list or SUBCANALES):
            camps = agg.get(sc, {})
            ui = sum(v['user_inc'] for v in camps.values())
            sents = sum(v['sents']    for v in camps.values())
            opens = sum(v['opens']    for v in camps.values())
            totals[sc] = {
                'user_inc': ui, 'sents': sents, 'opens': opens,
                'or': (opens / sents * 100) if sents > 0 else 0,
                'n_camps': len(camps),
                'camps': camps
            }
        return totals

    def _cruce(curr_totals, prev_totals, curr_agg, prev_agg, sc_list=None):
        """Calcula deltas y detecta señales diagnósticas."""
        cruce = {}
        for sc in (sc_list or SUBCANALES):
            c = curr_totals.get(sc, {'user_inc': 0, 'sents': 0, 'opens': 0, 'or': 0, 'n_camps': 0, 'camps': {}})
            p = prev_totals.get(sc, {'user_inc': 0, 'sents': 0, 'opens': 0, 'or': 0, 'n_camps': 0, 'camps': {}})
            curr_camps = curr_agg.get(sc, {})
            prev_camps = prev_agg.get(sc, {})

            ui_delta     = c['user_inc']  - p['user_inc']
            ui_pct       = (ui_delta / abs(p['user_inc']) * 100) if p['user_inc'] != 0 else None
            sents_pct    = ((c['sents'] - p['sents']) / p['sents'] * 100) if p['sents'] > 0 else None
            or_delta     = c['or'] - p['or']

            turned_off   = {n: d for n, d in prev_camps.items() if n not in curr_camps and d['user_inc'] != 0}
            new_camps    = {n: d for n, d in curr_camps.items()  if n not in prev_camps and d['user_inc'] != 0}
            active_both  = {
                n: {'curr': curr_camps[n], 'prev': prev_camps[n],
                    'ui_delta': curr_camps[n]['user_inc'] - prev_camps[n]['user_inc'],
                    'sents_delta_pct': ((curr_camps[n]['sents']-prev_camps[n]['sents'])/prev_camps[n]['sents']*100)
                                        if prev_camps[n]['sents'] > 0 else None}
                for n in curr_camps if n in prev_camps
            }

            lost_ui    = sum(d['user_inc'] for d in turned_off.values())
            gained_ui  = sum(d['user_inc'] for d in new_camps.values())

            # Señal dominante
            signals = []
            if turned_off:
                pct_gap = (abs(lost_ui) / abs(p['user_inc']) * 100) if p['user_inc'] != 0 else 0
                signals.append({'tipo': 'APAGADAS', 'n': len(turned_off), 'ui_lost': lost_ui, 'pct_gap': pct_gap})
            if new_camps:
                signals.append({'tipo': 'NUEVAS', 'n': len(new_camps), 'ui_gained': gained_ui})
            if sents_pct is not None and sents_pct < -10:
                signals.append({'tipo': 'SENTS_CAIDOS', 'delta_pct': sents_pct})
            if or_delta < -1.5:
                signals.append({'tipo': 'OR_CAIDO', 'delta_pp': or_delta})

            top_curr = sorted(curr_camps.items(), key=lambda x: x[1]['user_inc'], reverse=True)[:5]
            top_prev = sorted(prev_camps.items(), key=lambda x: x[1]['user_inc'], reverse=True)[:5]
            worst_ab = sorted(active_both.items(), key=lambda x: x[1]['ui_delta'])[:3]
            best_ab  = sorted(active_both.items(), key=lambda x: x[1]['ui_delta'], reverse=True)[:3]

            cruce[sc] = {
                'curr': c, 'prev': p,
                'ui_delta': ui_delta, 'ui_pct': ui_pct,
                'sents_pct': sents_pct, 'or_delta': or_delta,
                'turned_off': turned_off, 'new_camps': new_camps,
                'active_both': active_both,
                'lost_ui': lost_ui, 'gained_ui': gained_ui,
                'signals': signals,
                'top_curr': top_curr, 'top_prev': top_prev,
                'worst_ab': worst_ab, 'best_ab': best_ab,
            }
        return cruce

    # MTD: mes en curso D1-Dref vs mes anterior D1-Dref
    mtd_data = {}
    if current_month and months_sorted:
        prev_m = months_sorted[-2] if len(months_sorted) >= 2 else None
        if prev_m and mtd_ref_day > 0:
            # Corp aggregation
            curr_agg   = _aggregate_period(current_month, max_day=mtd_ref_day)
            prev_agg   = _aggregate_period(prev_m,        max_day=mtd_ref_day)
            curr_tot   = _subcanal_totals(curr_agg)
            prev_tot   = _subcanal_totals(prev_agg)
            # FM aggregation
            curr_agg_fm = _aggregate_period(current_month, max_day=mtd_ref_day, use_fm=True)
            prev_agg_fm = _aggregate_period(prev_m,        max_day=mtd_ref_day, use_fm=True)
            curr_tot_fm = _subcanal_totals(curr_agg_fm, sc_list=SUBCANALES_FM)
            prev_tot_fm = _subcanal_totals(prev_agg_fm, sc_list=SUBCANALES_FM)
            mtd_data   = {
                'current_month': current_month, 'prev_month': prev_m,
                'ref_day': mtd_ref_day,
                'ref_date_str': mtd_ref_date_str,   # fecha exacta D-2 para mostrar
                'cruce':    _cruce(curr_tot,    prev_tot,    curr_agg,    prev_agg),
                'cruce_fm': _cruce(curr_tot_fm, prev_tot_fm, curr_agg_fm, prev_agg_fm,
                                   sc_list=SUBCANALES_FM),
                'curr_totals': curr_tot, 'prev_totals': prev_tot,
                'curr_totals_fm': curr_tot_fm, 'prev_totals_fm': prev_tot_fm,
            }

    # Mes cerrado: mes anterior completo vs mes anterior-anterior
    closed_data = {}
    if closed_month and prev_month:
        cl_agg    = _aggregate_period(closed_month)
        pr_agg    = _aggregate_period(prev_month)
        cl_tot    = _subcanal_totals(cl_agg)
        pr_tot    = _subcanal_totals(pr_agg)
        cl_agg_fm = _aggregate_period(closed_month, use_fm=True)
        pr_agg_fm = _aggregate_period(prev_month,   use_fm=True)
        cl_tot_fm = _subcanal_totals(cl_agg_fm, sc_list=SUBCANALES_FM)
        pr_tot_fm = _subcanal_totals(pr_agg_fm, sc_list=SUBCANALES_FM)
        closed_data = {
            'closed_month': closed_month, 'prev_month': prev_month,
            'cruce':    _cruce(cl_tot,    pr_tot,    cl_agg,    pr_agg),
            'cruce_fm': _cruce(cl_tot_fm, pr_tot_fm, cl_agg_fm, pr_agg_fm,
                               sc_list=SUBCANALES_FM),
            'curr_totals': cl_tot, 'prev_totals': pr_tot,
            'curr_totals_fm': cl_tot_fm, 'prev_totals_fm': pr_tot_fm,
        }

    return {'mtd': mtd_data, 'closed': closed_data}


def _fmt_month_label(yyyymm: str) -> str:
    MONTHS = {'01':'Ene','02':'Feb','03':'Mar','04':'Abr','05':'May','06':'Jun',
              '07':'Jul','08':'Ago','09':'Sep','10':'Oct','11':'Nov','12':'Dic'}
    if len(yyyymm) == 6:
        return f"{MONTHS.get(yyyymm[4:6], yyyymm[4:6])}-{yyyymm[2:4]}"
    return yyyymm


def _build_dynamic_analysis_html(comms_records: list, months_sorted: list) -> str:
    """Genera las 2 secciones dinámicas de análisis (MTD + Mes Cerrado) para la pestaña OC+UCR.

    REGLA: USER_INC Comms ≡ N+R para OC+UCR.
    Las dos secciones aparecen ARRIBA del análisis estático existente.
    """
    if not comms_records or not months_sorted:
        return ''

    analysis = _compute_comms_analysis(comms_records, months_sorted)
    mtd      = analysis.get('mtd', {})
    closed   = analysis.get('closed', {})

    SUBCANALES    = ['UCRANIA E&G', 'OWN CHANNELS RECURRING', 'OWN CHANNELS ADHOC', 'UCR PRD']
    SUBCANALES_FM = ['UCR GEST', 'OC ACT', 'UCR PRD']
    SC_COLOR   = {
        'UCRANIA E&G':            '#5899D1',
        'OWN CHANNELS RECURRING': '#2F9E8F',
        'OWN CHANNELS ADHOC':     '#7627bb',
        'UCR PRD':                '#e65100',
        'UCR GEST':               '#5899D1',
        'OC ACT':                 '#2F9E8F',
    }
    SC_EMOJI = {
        'UCRANIA E&G': '🔵', 'OWN CHANNELS RECURRING': '🟢',
        'OWN CHANNELS ADHOC': '🟣', 'UCR PRD': '🟠',
        'UCR GEST': '🔵', 'OC ACT': '🟢',
    }

    def _pct_badge(pct, inverse=False):
        if pct is None: return '<span style="color:#aaa">—</span>'
        good = pct >= 0 if not inverse else pct <= 0
        col  = '#2e7d32' if good else '#c62828'
        sym  = '▲' if pct >= 0 else '▼'
        return f'<span style="color:{col};font-weight:700">{sym} {abs(pct):.1f}%</span>'

    def _num(v, suffix=''):
        if v is None: return '—'
        if abs(v) >= 1000: return f'{v/1000:.1f}K{suffix}'
        return f'{v:.0f}{suffix}'

    def _delta_color(v):
        if v is None: return '#666'
        return '#2e7d32' if v >= 0 else '#c62828'

    def _signal_badge(sig):
        tipo = sig.get('tipo', '')
        if tipo == 'APAGADAS':
            n   = sig.get('n', 0)
            pct = sig.get('pct_gap', 0)
            return (f'<span style="background:#ffebee;color:#c62828;border-radius:4px;padding:2px 6px;'
                    f'font-size:10px;font-weight:700">🚫 {n} comms apagadas ({pct:.0f}% del gap)</span>')
        if tipo == 'NUEVAS':
            return (f'<span style="background:#e8f5e9;color:#2e7d32;border-radius:4px;padding:2px 6px;'
                    f'font-size:10px;font-weight:700">✨ {sig.get("n",0)} comms nuevas</span>')
        if tipo == 'SENTS_CAIDOS':
            return (f'<span style="background:#fff3e0;color:#e65100;border-radius:4px;padding:2px 6px;'
                    f'font-size:10px;font-weight:700">📉 Sents {sig.get("delta_pct",0):.1f}%</span>')
        if tipo == 'OR_CAIDO':
            return (f'<span style="background:#f3e5f5;color:#7627bb;border-radius:4px;padding:2px 6px;'
                    f'font-size:10px;font-weight:700">📭 OR {sig.get("delta_pp",0):.1f}pp</span>')
        return ''

    # ─────────────────────────────────────────────────────────────────────────
    # SECCIÓN 1 — MTD (D1-Dref vs mismo período mes anterior)
    # ─────────────────────────────────────────────────────────────────────────
    html_mtd = ''
    if mtd and mtd.get('cruce'):
        curr_lbl      = _fmt_month_label(mtd['current_month'])
        prev_lbl      = _fmt_month_label(mtd['prev_month'])
        ref_day       = mtd['ref_day']
        ref_date_str  = mtd.get('ref_date_str', '')   # fecha exacta D-2
        cruce         = mtd['cruce']

        # Total USER_INC MTD
        total_curr = sum(cruce[sc]['curr']['user_inc'] for sc in SUBCANALES if sc in cruce)
        total_prev = sum(cruce[sc]['prev']['user_inc'] for sc in SUBCANALES if sc in cruce)
        total_delta = total_curr - total_prev
        total_pct   = (total_delta / abs(total_prev) * 100) if total_prev != 0 else None

        # Identificar sub-canal con mayor caída y mayor subida
        sc_sorted_delta = sorted(
            [(sc, cruce[sc]['ui_delta']) for sc in SUBCANALES if sc in cruce],
            key=lambda x: x[1]
        )
        worst_sc = sc_sorted_delta[0][0] if sc_sorted_delta else None
        best_sc  = sc_sorted_delta[-1][0] if sc_sorted_delta else None

        # Causa raíz dominante del peor sub-canal
        root_cause = ''
        if worst_sc and cruce.get(worst_sc, {}).get('signals'):
            sigs = cruce[worst_sc]['signals']
            primary = sigs[0]
            if primary['tipo'] == 'APAGADAS':
                n_off = primary['n']
                ui_lost = primary['ui_lost']
                pct_g   = primary['pct_gap']
                root_cause = (f'<strong>Causa raíz dominante — {worst_sc}</strong>: '
                             f'{n_off} campaña{"s" if n_off>1 else ""} apagada{"s" if n_off>1 else ""} '
                             f'explica{"n" if n_off>1 else ""} {_num(abs(ui_lost))} USER_INC perdido '
                             f'({pct_g:.0f}% del gap del sub-canal).')
            elif primary['tipo'] == 'SENTS_CAIDOS':
                root_cause = (f'<strong>Causa raíz dominante — {worst_sc}</strong>: '
                             f'Sents cayeron {primary["delta_pct"]:.1f}% — '
                             f'mismas campañas activas pero se están enviando menos comunicaciones.')
            elif primary['tipo'] == 'OR_CAIDO':
                root_cause = (f'<strong>Causa raíz dominante — {worst_sc}</strong>: '
                             f'Open Rate cayó {primary["delta_pp"]:.1f}pp — '
                             f'señal de fatiga de mensaje o propuesta de valor incorrecta.')

        col_total = '#2e7d32' if total_delta >= 0 else '#c62828'
        sym_total = '▲' if total_delta >= 0 else '▼'

        rows_html = ''
        for sc in SUBCANALES:
            if sc not in cruce: continue
            c = cruce[sc]
            col = SC_COLOR.get(sc, '#666')
            em  = SC_EMOJI.get(sc, '●')
            ui_curr = c['curr']['user_inc']
            ui_prev = c['prev']['user_inc']
            delta   = c['ui_delta']
            pct     = c['ui_pct']
            n_off   = len(c['turned_off'])
            n_new   = len(c['new_camps'])
            sig_html = ' '.join(_signal_badge(s) for s in c['signals'][:2])
            dcol     = _delta_color(delta)
            sym      = '▲' if delta >= 0 else '▼'
            pct_str  = f'{sym} {abs(pct):.1f}%' if pct is not None else '—'

            # Top 2 campañas con mayor impacto en el Δ (apagadas + activas, por impacto absoluto)
            _all_impacts = []
            for cn, d in c['turned_off'].items():
                if d['sents'] > 0 or d['user_inc'] != 0:
                    _all_impacts.append((cn, d['user_inc'], 'APAGADA'))
            for cn, ab in c['worst_ab']:
                if ab['ui_delta'] < 0:
                    _all_impacts.append((cn, ab['ui_delta'], 'CAYENDO'))
            for cn, ab in c['best_ab']:
                if ab['ui_delta'] > 0:
                    _all_impacts.append((cn, ab['ui_delta'], 'SUBIENDO'))
            _all_impacts.sort(key=lambda x: abs(x[1]), reverse=True)
            _top2 = _all_impacts[:2]

            if _top2:
                _lines = []
                for _cn, _ui, _tipo in _top2:
                    _c2 = '#c62828' if _ui < 0 else '#2e7d32'
                    _sym = '' if _ui >= 0 else ''
                    _lines.append(
                        f'<strong style="color:#1a1a2e">{_cn}</strong>'
                        f'<br><span style="font-size:10px;color:{_c2};font-weight:700">'
                        f'{_tipo} · {_sym}{_num(_ui)} UI</span>'
                    )
                _resp_html = '<br>'.join(_lines)
                _resp_col  = '#c62828' if _top2[0][1] < 0 else '#2e7d32'
            else:
                _resp_html, _resp_col = '—', '#666'

            rows_html += f'''
            <tr>
              <td style="border-left:3px solid {col};padding-left:8px;font-weight:600;color:#1a1a2e">
                {em} {sc}
              </td>
              <td style="text-align:right;font-weight:700;color:{dcol}">{_num(ui_curr)}</td>
              <td style="text-align:right;color:#666">{_num(ui_prev)}</td>
              <td style="text-align:right;font-weight:700;color:{dcol}">{_num(delta, " UI")}</td>
              <td style="text-align:right;font-weight:700;color:{dcol}">{pct_str}</td>
              <td style="font-size:11px">{sig_html if sig_html else '<span style="color:#2e7d32">✓ Estable</span>'}</td>
              <td style="font-size:10.5px;word-break:break-word;min-width:200px">
                {_resp_html}
              </td>
            </tr>'''

        html_mtd = f'''
<div class="oca-section" style="border-left:4px solid #f5d000;background:linear-gradient(180deg,#fff 0%,#fffdf0 100%)">
  <h2 style="color:#0f2140">
    📊 MTD D1-D{ref_day} — {curr_lbl} vs {prev_lbl}
    <span class="badge badge-blue">D-2 certificado · datos hasta {ref_date_str} · USER_INC ≡ N+R OC+UCR</span>
    <span style="margin-left:auto;font-size:20px;font-weight:800;color:{col_total}">{sym_total} {f"{abs(total_pct):.1f}%" if total_pct is not None else "—"} MoM</span>
  </h2>

  <div style="background:#f8faff;border-radius:8px;padding:14px 16px;margin-bottom:14px;border:1px solid #e3eaf8">
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:16px">
      <div>
        <div style="font-size:10px;color:#888;text-transform:uppercase;letter-spacing:.5px">USER INC Total OC+UCR</div>
        <div style="font-size:24px;font-weight:800;color:{col_total}">{_num(total_curr)}</div>
        <div style="font-size:11px;color:#666">vs {_num(total_prev)} en {prev_lbl} D{ref_day}
          &nbsp;<span style="font-weight:700;color:{col_total}">{sym_total} {_num(abs(total_delta))}</span>
        </div>
      </div>
      <div>
        <div style="font-size:10px;color:#888;text-transform:uppercase;letter-spacing:.5px">Sub-canal con mayor caída</div>
        <div style="font-size:16px;font-weight:700;color:#c62828">{worst_sc or '—'}</div>
        <div style="font-size:11px;color:#666">{_num(cruce.get(worst_sc,{}).get('ui_delta',0))} USER_INC MoM</div>
      </div>
      <div>
        <div style="font-size:10px;color:#888;text-transform:uppercase;letter-spacing:.5px">Sub-canal más fuerte</div>
        <div style="font-size:16px;font-weight:700;color:#2e7d32">{best_sc or '—'}</div>
        <div style="font-size:11px;color:#666">+{_num(cruce.get(best_sc,{}).get("ui_delta",0))} USER_INC MoM</div>
      </div>
      <div>
        <div style="font-size:10px;color:#888;text-transform:uppercase;letter-spacing:.5px">Regla clave</div>
        <div style="font-size:12px;font-weight:600;color:#1565c0;line-height:1.4">USER_INC Comms<br>≡ N+R OC+UCR</div>
      </div>
    </div>
  </div>

  {"<div class='alert-box alert-amber'><strong>🔍 " + root_cause + "</strong></div>" if root_cause else ''}

  <div style="overflow-x:auto">
    <table class="oca-table" style="min-width:800px">
      <thead>
        <tr style="background:#0f2140;color:#fff">
          <th style="background:#0f2140;color:#e8f0ff;padding:9px 10px">Sub-canal Corp</th>
          <th style="background:#0f2140;color:#f5d000;text-align:right">{curr_lbl} D{ref_day}</th>
          <th style="background:#0f2140;color:#a8c4e8;text-align:right">{prev_lbl} D{ref_day}</th>
          <th style="background:#0f2140;color:#e8f0ff;text-align:right">Δ USER INC</th>
          <th style="background:#0f2140;color:#e8f0ff;text-align:right">Δ %</th>
          <th style="background:#0f2140;color:#e8f0ff">Señales diagnósticas</th>
          <th style="background:#0f2140;color:#f5d000">Campaña más responsable del Δ</th>
        </tr>
      </thead>
      <tbody>{rows_html}</tbody>
    </table>
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:14px">
'''

        # ── Deep dive por sub-canal — Vista Corp (nombres completos, sin cortar) ──
        html_mtd += '\n  </div>\n'  # close 2col grid summary
        html_mtd += f'''
  <h3 style="font-size:14px;font-weight:700;color:#0f2140;margin:16px 0 10px;border-top:1px solid #e4e8f0;padding-top:14px">
    🏢 Vista Corp — Detalle por sub-canal (campañas responsables del Δ)
  </h3>'''

        for sc in SUBCANALES:
            if sc not in cruce: continue
            wc = cruce[sc]
            if not wc['turned_off'] and not wc['worst_ab'] and not wc['best_ab']:
                continue
            sc_delta    = wc['ui_delta']
            sc_delta_col = _delta_color(sc_delta)
            sc_sym       = '▲' if sc_delta >= 0 else '▼'
            sc_pct_str   = f'{abs(wc["ui_pct"]):.1f}%' if wc['ui_pct'] is not None else '—'
            icon = '🔴' if sc_delta < -200 else ('🟡' if sc_delta < 0 else '🟢')

            # Campañas apagadas — nombres completos
            off_rows = ''
            for cn, d in sorted(wc['turned_off'].items(), key=lambda x: abs(x[1]['user_inc']), reverse=True):
                if d['sents'] == 0 and d['user_inc'] == 0:
                    continue  # filtra registros fantasma
                off_rows += f'''<tr>
                  <td style="font-size:11px;color:#333;word-break:break-word;max-width:400px">{cn}</td>
                  <td style="text-align:right;color:#c62828;font-weight:700;white-space:nowrap">{_num(d["user_inc"])} UI</td>
                  <td style="text-align:right;white-space:nowrap">{_num(d["sents"])}</td>
                  <td><span class="tag t-stop">REACTIVAR?</span></td>
                </tr>'''

            # Campañas activas con mayor caída MoM — nombres completos
            worst_rows = ''
            for cn, ab in wc['worst_ab']:
                if ab['ui_delta'] >= 0: continue
                c_ui = ab['curr']['user_inc']
                p_ui = ab['prev']['user_inc']
                ui_d = ab['ui_delta']
                s_d  = ab.get('sents_delta_pct')
                s_str = f'{s_d:.0f}%' if s_d is not None else '—'
                action = 'ESCALAR SENTS' if (s_d or 0) < -20 else ('ROTAR VP' if (wc.get('or_delta') or 0) < -1.5 else 'INVESTIGAR')
                worst_rows += f'''<tr>
                  <td style="font-size:11px;color:#333;word-break:break-word;max-width:400px">{cn}</td>
                  <td style="text-align:right;font-size:11px;white-space:nowrap">{_num(c_ui)}</td>
                  <td style="text-align:right;font-size:11px;white-space:nowrap">{_num(p_ui)}</td>
                  <td style="text-align:right;font-weight:700;color:#c62828;white-space:nowrap">{_num(ui_d)}</td>
                  <td style="text-align:right;font-size:11px;white-space:nowrap">{s_str}</td>
                  <td><span class="tag t-test">{action}</span></td>
                </tr>'''

            # Campañas ganando fuerza — nombres completos
            best_rows = ''
            for cn, ab in wc['best_ab']:
                if ab['ui_delta'] <= 0: continue
                best_rows += f'''<tr>
                  <td style="font-size:11px;color:#333;word-break:break-word;max-width:400px">{cn}</td>
                  <td style="text-align:right;color:#2e7d32;font-weight:700;white-space:nowrap">+{_num(ab["ui_delta"])} UI</td>
                  <td style="text-align:right;font-size:11px;white-space:nowrap">{_num(ab["curr"]["user_inc"])}</td>
                  <td><span class="tag t-scale">ESCALAR</span></td>
                </tr>'''

            border_col = '#c62828' if sc_delta < 0 else '#2e7d32'
            html_mtd += f'''
  <div class="oca-card" style="border-top:3px solid {border_col};margin-bottom:12px">
    <h3>{icon} {sc} &nbsp;
      <span style="color:{sc_delta_col};font-weight:800">{sc_sym} {sc_pct_str} MoM</span>
      <span style="font-size:11px;color:#666;font-weight:400;margin-left:8px">
        {curr_lbl} D{ref_day}: {_num(wc["curr"]["user_inc"])} UI &nbsp;|&nbsp; {prev_lbl} D{ref_day}: {_num(wc["prev"]["user_inc"])} UI
      </span>
    </h3>
    {"<p style='font-size:12px;color:#c62828;font-weight:600;margin:0 0 6px'>🚫 Campañas apagadas:</p><div style='overflow-x:auto'><table class=\"oca-table\"><thead><tr><th>Campaña (nombre completo)</th><th style=\"text-align:right\">USER_INC perdido</th><th style=\"text-align:right\">Sents anteriores</th><th>Acción</th></tr></thead><tbody>" + off_rows + "</tbody></table></div>" if off_rows else ""}
    {"<p style='font-size:12px;color:#e65100;font-weight:600;margin:10px 0 6px'>📉 Campañas activas con mayor caída:</p><div style='overflow-x:auto'><table class=\"oca-table\"><thead><tr><th>Campaña (nombre completo)</th><th style=\"text-align:right\">May D{ref_day}</th><th style=\"text-align:right\">Abr D{ref_day}</th><th style=\"text-align:right\">Δ UI</th><th style=\"text-align:right\">Δ Sents</th><th>Acción</th></tr></thead><tbody>" + worst_rows + "</tbody></table></div>" if worst_rows else ""}
    {"<p style='font-size:12px;color:#2e7d32;font-weight:600;margin:10px 0 6px'>🚀 Campañas ganando fuerza:</p><div style='overflow-x:auto'><table class=\"oca-table\"><thead><tr><th>Campaña (nombre completo)</th><th style=\"text-align:right\">Δ UI</th><th style=\"text-align:right\">Total actual</th><th>Acción</th></tr></thead><tbody>" + best_rows + "</tbody></table></div>" if best_rows else ""}
  </div>'''

        # ── Vista FM — Detalle por sub-canal (UCR GEST / OC ACT / UCR PRD) ──
        cruce_fm = mtd.get('cruce_fm', {})
        if cruce_fm:
            html_mtd += f'''
  <h3 style="font-size:14px;font-weight:700;color:#0f2140;margin:20px 0 10px;border-top:2px solid #1565c0;padding-top:14px">
    📊 Vista FM — Detalle por sub-canal (campañas responsables del Δ)
    <span style="font-size:11px;font-weight:400;color:#666;margin-left:8px">
      Clasificación: UCR GEST · OC ACT · UCR PRD
    </span>
  </h3>'''
            for sc_fm in SUBCANALES_FM:
                if sc_fm not in cruce_fm: continue
                wc = cruce_fm[sc_fm]
                if not wc['turned_off'] and not wc['worst_ab'] and not wc['best_ab']: continue
                sc_delta     = wc['ui_delta']
                sc_delta_col = _delta_color(sc_delta)
                sc_sym       = '▲' if sc_delta >= 0 else '▼'
                sc_pct_str   = f'{abs(wc["ui_pct"]):.1f}%' if wc['ui_pct'] is not None else '—'
                icon_fm      = '🔴' if sc_delta < -200 else ('🟡' if sc_delta < 0 else '🟢')
                col_fm       = SC_COLOR.get(sc_fm, '#555')

                off_rows_fm = ''
                for cn, d in sorted(wc['turned_off'].items(), key=lambda x: abs(x[1]['user_inc']), reverse=True):
                    if d['sents'] == 0 and d['user_inc'] == 0: continue
                    off_rows_fm += f'''<tr>
                      <td style="font-size:11px;word-break:break-word;max-width:420px">{cn}</td>
                      <td style="text-align:right;color:#c62828;font-weight:700;white-space:nowrap">{_num(d["user_inc"])} UI</td>
                      <td style="text-align:right;white-space:nowrap">{_num(d["sents"])}</td>
                      <td><span class="tag t-stop">REACTIVAR?</span></td></tr>'''

                worst_rows_fm = ''
                for cn, ab in wc['worst_ab']:
                    if ab['ui_delta'] >= 0: continue
                    c_ui = ab['curr']['user_inc']
                    p_ui = ab['prev']['user_inc']
                    ui_d = ab['ui_delta']
                    s_d  = ab.get('sents_delta_pct')
                    s_str = f'{s_d:.0f}%' if s_d is not None else '—'
                    action = 'ESCALAR SENTS' if (s_d or 0) < -20 else 'INVESTIGAR'
                    worst_rows_fm += f'''<tr>
                      <td style="font-size:11px;word-break:break-word;max-width:420px">{cn}</td>
                      <td style="text-align:right;white-space:nowrap">{_num(c_ui)}</td>
                      <td style="text-align:right;white-space:nowrap">{_num(p_ui)}</td>
                      <td style="text-align:right;font-weight:700;color:#c62828;white-space:nowrap">{_num(ui_d)}</td>
                      <td style="text-align:right;white-space:nowrap">{s_str}</td>
                      <td><span class="tag t-test">{action}</span></td></tr>'''

                best_rows_fm = ''
                for cn, ab in wc['best_ab']:
                    if ab['ui_delta'] <= 0: continue
                    best_rows_fm += f'''<tr>
                      <td style="font-size:11px;word-break:break-word;max-width:420px">{cn}</td>
                      <td style="text-align:right;color:#2e7d32;font-weight:700;white-space:nowrap">+{_num(ab["ui_delta"])} UI</td>
                      <td style="text-align:right;white-space:nowrap">{_num(ab["curr"]["user_inc"])}</td>
                      <td><span class="tag t-scale">ESCALAR</span></td></tr>'''

                border_col_fm = '#c62828' if sc_delta < 0 else '#2e7d32'
                html_mtd += f'''
  <div class="oca-card" style="border-top:3px solid {border_col_fm};margin-bottom:12px">
    <h3>{icon_fm} {sc_fm} &nbsp;
      <span style="color:{sc_delta_col};font-weight:800">{sc_sym} {sc_pct_str} MoM</span>
      <span style="font-size:11px;color:#666;font-weight:400;margin-left:8px">
        {curr_lbl} D{ref_day}: {_num(wc["curr"]["user_inc"])} UI &nbsp;|&nbsp; {prev_lbl} D{ref_day}: {_num(wc["prev"]["user_inc"])} UI
      </span>
    </h3>
    {"<p style='font-size:12px;color:#c62828;font-weight:600;margin:0 0 6px'>🚫 Campañas apagadas:</p><div style='overflow-x:auto'><table class=\"oca-table\"><thead><tr><th>Campaña</th><th style=\"text-align:right\">UI perdido</th><th style=\"text-align:right\">Sents</th><th>Acción</th></tr></thead><tbody>" + off_rows_fm + "</tbody></table></div>" if off_rows_fm else ""}
    {"<p style='font-size:12px;color:#e65100;font-weight:600;margin:8px 0 4px'>📉 Campañas con mayor caída:</p><div style='overflow-x:auto'><table class=\"oca-table\"><thead><tr><th>Campaña</th><th style=\"text-align:right\">May</th><th style=\"text-align:right\">Abr</th><th style=\"text-align:right\">Δ UI</th><th style=\"text-align:right\">Δ Sents</th><th>Acción</th></tr></thead><tbody>" + worst_rows_fm + "</tbody></table></div>" if worst_rows_fm else ""}
    {"<p style='font-size:12px;color:#2e7d32;font-weight:600;margin:8px 0 4px'>🚀 Campañas ganando fuerza:</p><div style='overflow-x:auto'><table class=\"oca-table\"><thead><tr><th>Campaña</th><th style=\"text-align:right\">Δ UI</th><th style=\"text-align:right\">Total</th><th>Acción</th></tr></thead><tbody>" + best_rows_fm + "</tbody></table></div>" if best_rows_fm else ""}
  </div>'''

        # Recomendaciones MTD con nombres de campaña explícitos
        recs = []
        for sc in SUBCANALES:
            if sc not in cruce: continue
            c = cruce[sc]
            for sig in c['signals']:
                if sig['tipo'] == 'APAGADAS' and sig.get('pct_gap', 0) > 20:
                    # Nombres explícitos de campañas a reactivar
                    camp_names = [n for n, d in sorted(c['turned_off'].items(),
                                   key=lambda x: abs(x[1]['user_inc']), reverse=True)[:3]
                                  if d['sents'] > 0 or d['user_inc'] != 0]
                    camps_str = ' · '.join(camp_names) if camp_names else 'verificar en Comms_OC'
                    recs.append({'prio': 'URGENTE', 'col': '#c62828',
                                 'accion': f'[{sc}] REACTIVAR: {camps_str}',
                                 'impacto': f'+{_num(abs(sig["ui_lost"]))} USER_INC/período si se reactivan',
                                 'eta': 'Hoy'})
                if sig['tipo'] == 'SENTS_CAIDOS' and sig.get('delta_pct', 0) < -20:
                    camp_names = [n for n, ab in c['worst_ab'][:2] if (ab.get('sents_delta_pct') or 0) < -20]
                    camps_str = ' · '.join(camp_names) if camp_names else f'{sc}'
                    recs.append({'prio': 'ESCALAR', 'col': '#e65100',
                                 'accion': f'[{sc}] ESCALAR SENTS: {camps_str} (sents cayeron {sig["delta_pct"]:.0f}%)',
                                 'impacto': 'Recuperar volumen de envíos = recuperar USER_INC directo',
                                 'eta': 'Esta semana'})
                if sig['tipo'] == 'OR_CAIDO':
                    camp_names = [n for n, ab in c['worst_ab'][:2]]
                    camps_str = ' · '.join(camp_names) if camp_names else f'{sc}'
                    recs.append({'prio': 'REPENSAR', 'col': '#7627bb',
                                 'accion': f'[{sc}] ROTAR VP: {camps_str} (OR cayó {sig["delta_pp"]:.1f}pp)',
                                 'impacto': 'Fatiga de mensaje — nuevo creativo o VP mejora conversión',
                                 'eta': '1-2 semanas'})

        if recs:
            recs_html = ''
            for r in recs[:4]:
                recs_html += f'''
              <div class="action-row">
                <div class="action-num" style="background:{r['col']}">{r['prio'][:1]}</div>
                <div class="action-body">
                  <strong>[{r['prio']}] {r['accion']}</strong>
                  <p>Impacto estimado: {r['impacto']} · ETA: {r['eta']}</p>
                </div>
              </div>'''
            html_mtd += f'''
  <div style="margin-top:14px">
    <h3 style="font-size:13px;font-weight:700;color:#0f2140;margin:0 0 10px">⚡ Recomendaciones inmediatas</h3>
    {recs_html}
  </div>'''

        html_mtd += f'''
  <div class="skill-note">Fuente: Comms_OC D1-D{ref_day} · USER_INC Comms ≡ N+R OC+UCR (§83) · Modo 20 Comms Skill · comms_classification_config.json</div>
</div>'''

    # ─────────────────────────────────────────────────────────────────────────
    # SECCIÓN 2 — MES CERRADO (análisis full month, ciclo de vida, patrones)
    # ─────────────────────────────────────────────────────────────────────────
    html_closed = ''
    if closed and closed.get('cruce'):
        cl_lbl  = _fmt_month_label(closed['closed_month'])
        pr_lbl  = _fmt_month_label(closed['prev_month'])
        cruce   = closed['cruce']

        total_cl = sum(cruce[sc]['curr']['user_inc'] for sc in SUBCANALES if sc in cruce)
        total_pr = sum(cruce[sc]['prev']['user_inc'] for sc in SUBCANALES if sc in cruce)
        total_d  = total_cl - total_pr
        total_p  = (total_d / abs(total_pr) * 100) if total_pr != 0 else None
        tcol     = '#2e7d32' if total_d >= 0 else '#c62828'
        tsym     = '▲' if total_d >= 0 else '▼'

        sc_rows = ''
        for sc in SUBCANALES:
            if sc not in cruce: continue
            c   = cruce[sc]
            col = SC_COLOR.get(sc, '#666')
            em  = SC_EMOJI.get(sc, '●')
            dcol = _delta_color(c['ui_delta'])
            sym  = '▲' if c['ui_delta'] >= 0 else '▼'
            pct  = c['ui_pct']
            pct_str = f'{sym} {abs(pct):.1f}%' if pct is not None else '—'
            or_d = c['or_delta']
            or_col = '#c62828' if or_d < -1 else ('#2e7d32' if or_d > 0.5 else '#555')
            s_pct = c['sents_pct']
            s_str = f'{s_pct:.1f}%' if s_pct is not None else '—'
            s_col = '#c62828' if (s_pct or 0) < -10 else '#555'
            n_off = len(c['turned_off'])
            n_new = len(c['new_camps'])
            n_act = len(c['active_both'])
            sig_html = ' '.join(_signal_badge(s) for s in c['signals'][:2])

            # Top gainer y top loser del mes cerrado
            best  = c['best_ab'][0][0][:30]  + '…' if c['best_ab']  else '—'
            worst = c['worst_ab'][0][0][:30] + '…' if c['worst_ab'] else '—'
            best_d  = f"+{_num(c['best_ab'][0][1]['ui_delta'])}"  if c['best_ab']  else '—'
            worst_d = f"{_num(c['worst_ab'][0][1]['ui_delta'])}" if c['worst_ab'] else '—'

            sc_rows += f'''
            <tr>
              <td style="border-left:3px solid {col};padding-left:8px;font-weight:600">{em} {sc}</td>
              <td style="text-align:right;font-weight:700">{_num(c['curr']['user_inc'])}</td>
              <td style="text-align:right;color:#666">{_num(c['prev']['user_inc'])}</td>
              <td style="text-align:right;font-weight:700;color:{dcol}">{pct_str}</td>
              <td style="text-align:right;color:{s_col}">{s_str}</td>
              <td style="text-align:right;color:{or_col}">{or_d:+.1f}pp</td>
              <td style="font-size:10px;text-align:center">{n_off}🚫 {n_new}✨ {n_act}↔</td>
              <td style="font-size:10px;color:#2e7d32">{best}<br><span style="font-weight:700">{best_d} UI</span></td>
              <td style="font-size:10px;color:#c62828">{worst}<br><span style="font-weight:700">{worst_d} UI</span></td>
              <td style="font-size:10px">{sig_html}</td>
            </tr>'''

        # Campañas en aceleración vs en desgaste (ciclo de vida)
        accel_rows = ''
        wear_rows  = ''
        for sc in SUBCANALES:
            if sc not in cruce: continue
            for cn, ab in cruce[sc].get('best_ab', [])[:2]:
                if ab['ui_delta'] > 100:
                    accel_rows += f'<li style="font-size:12px;margin-bottom:4px"><strong>{cn[:40]}</strong> · {sc} · <span style="color:#2e7d32">+{_num(ab["ui_delta"])} UI MoM</span></li>'
            for cn, ab in cruce[sc].get('worst_ab', [])[:2]:
                if ab['ui_delta'] < -100:
                    wear_rows += f'<li style="font-size:12px;margin-bottom:4px"><strong>{cn[:40]}</strong> · {sc} · <span style="color:#c62828">{_num(ab["ui_delta"])} UI MoM</span></li>'

        html_closed = f'''
<div class="oca-section" style="border-left:4px solid #1565c0">
  <h2 style="color:#0f2140">
    📅 Mes Cerrado: {cl_lbl} completo vs {pr_lbl}
    <span class="badge badge-blue">Análisis full-month · Ciclo de vida · Patrones</span>
    <span style="margin-left:auto;font-size:20px;font-weight:800;color:{tcol}">{tsym} {f"{abs(total_p):.1f}%" if total_p is not None else "—"} MoM</span>
  </h2>

  <div style="overflow-x:auto;margin-bottom:16px">
    <table class="oca-table" style="min-width:1000px">
      <thead>
        <tr style="background:#1565c0;color:#fff">
          <th style="background:#1565c0;color:#e8f0ff">Sub-canal Corp</th>
          <th style="background:#1565c0;color:#f5d000;text-align:right">{cl_lbl} (real)</th>
          <th style="background:#1565c0;color:#a8c4e8;text-align:right">{pr_lbl}</th>
          <th style="background:#1565c0;color:#e8f0ff;text-align:right">USER INC MoM</th>
          <th style="background:#1565c0;color:#e8f0ff;text-align:right">Δ Sents</th>
          <th style="background:#1565c0;color:#e8f0ff;text-align:right">Δ OR</th>
          <th style="background:#1565c0;color:#e8f0ff;text-align:center">Comms 🚫✨↔</th>
          <th style="background:#1565c0;color:#a8c4e8">Top gainer</th>
          <th style="background:#1565c0;color:#f28b82">Top loser</th>
          <th style="background:#1565c0;color:#e8f0ff">Señales</th>
        </tr>
      </thead>
      <tbody>{sc_rows}</tbody>
    </table>
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:14px">
    <div class="oca-card" style="border-top:3px solid #2e7d32">
      <h3>📈 Campañas ganando fuerza en {cl_lbl}</h3>
      {"<ul style='margin:0;padding-left:16px'>" + accel_rows + "</ul>" if accel_rows else "<p style='color:#888;font-size:12px'>Sin campañas con crecimiento significativo</p>"}
    </div>
    <div class="oca-card" style="border-top:3px solid #c62828">
      <h3>📉 Campañas en desgaste en {cl_lbl}</h3>
      {"<ul style='margin:0;padding-left:16px'>" + wear_rows + "</ul>" if wear_rows else "<p style='color:#888;font-size:12px'>Sin campañas con caída significativa</p>"}
    </div>
  </div>

  <div class="skill-note">Fuente: Comms_OC mes completo {cl_lbl} vs {pr_lbl} · USER_INC Comms ≡ N+R OC+UCR · Modo 20 Comms Skill · §83</div>
</div>'''

    return html_mtd + html_closed


def build_oc_ucr_analysis_tab_html(comms_monthly_summary: dict = None,
                                    comms_oc_records: list = None,
                                    monthly_nr_corp_by_node: dict = None,
                                    monthly_nr: dict = None,
                                    data_months: list = None) -> str:
    """Análisis estratégico OC+UCR generado con los 3 skills de IA.
    Skills: analizar-Optimizar_Performance_KPIs_skill.md (MODO_OC_UCR) +
            analizar-OC_Comms_skill.md (drill_decay + ranking_multidim) +
            OPTIMIZADOR-OC_skill.md (alerta_canal + protocolo automático).
    Fuentes: KPI context §B1 (Q1-2026) + comms_monthly_summary Abr-2026 +
             BT_OC_MP_FLOWS_DAILY + comms_classification_config.json.
    Datos al: Abril 22, 2026. Próxima actualización: Mayo 2026.
    """

    _css = """<style>
.oca{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;max-width:1180px;margin:0 auto;padding:20px;color:#1a1a2e;line-height:1.5}
.oca-hero{background:linear-gradient(135deg,#0f2140 0%,#1a3a6b 60%,#0d3060 100%);border-radius:14px;padding:28px 32px;margin-bottom:20px;color:#fff}
.oca-hero h1{margin:0 0 6px;font-size:22px;font-weight:700;color:#f5d000}
.oca-hero .oca-sub{font-size:13px;color:#a8c4e8;margin-bottom:16px}
.oca-hero .oca-bl{font-size:15px;color:#e8f0ff;line-height:1.6;border-left:3px solid #f5d000;padding-left:14px;margin-top:8px}
.oca-kpi-row{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px}
.oca-kpi{background:#fff;border-radius:10px;padding:14px 16px;box-shadow:0 2px 8px rgba(0,0,0,.07);border-top:3px solid #5899d1}
.oca-kpi.red{border-top-color:#e53935}.oca-kpi.green{border-top-color:#2e7d32}.oca-kpi.amber{border-top-color:#f57c00}.oca-kpi.gold{border-top-color:#f5d000}
.oca-kpi .kv{font-size:26px;font-weight:700;color:#1a1a2e;margin-bottom:2px}.oca-kpi .kl{font-size:11px;color:#666;text-transform:uppercase;letter-spacing:.5px}
.oca-kpi .kd{font-size:12px;margin-top:4px}.kd.neg{color:#c62828;font-weight:600}.kd.pos{color:#2e7d32;font-weight:600}.kd.warn{color:#e65100;font-weight:600}
.oca-section{background:#fff;border-radius:12px;padding:22px 24px;margin-bottom:16px;box-shadow:0 2px 8px rgba(0,0,0,.06)}
.oca-section h2{margin:0 0 14px;font-size:15px;font-weight:700;color:#0f2140;display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.oca-section h2 .badge{font-size:11px;padding:2px 8px;border-radius:20px;font-weight:600}
.badge-red{background:#ffebee;color:#c62828}.badge-green{background:#e8f5e9;color:#2e7d32}.badge-amber{background:#fff3e0;color:#e65100}.badge-blue{background:#e3f2fd;color:#0d47a1}
.oca-2col{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:16px}
.oca-3col{display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px;margin-bottom:16px}
.oca-card{background:#fff;border-radius:10px;padding:16px 18px;box-shadow:0 2px 8px rgba(0,0,0,.07)}
.oca-card h3{margin:0 0 10px;font-size:13px;font-weight:700;color:#333;display:flex;align-items:center;gap:6px}
.oca-table{width:100%;border-collapse:collapse;font-size:12.5px}
.oca-table th{background:#f0f4fa;color:#333;font-weight:600;padding:7px 10px;text-align:left;border-bottom:2px solid #dde3ee}
.oca-table td{padding:7px 10px;border-bottom:1px solid #f0f4fa;color:#444}
.oca-table tr:hover td{background:#f8faff}
.oca-table td.pos{color:#2e7d32;font-weight:600}.oca-table td.neg{color:#c62828;font-weight:600}.oca-table td.warn{color:#e65100;font-weight:600}
.wf-row{display:flex;align-items:center;margin:5px 0;gap:8px;font-size:13px}
.wf-bar{height:16px;border-radius:3px;min-width:4px}
.wf-bar.neg-bar{background:#ef9a9a}.wf-bar.pos-bar{background:#a5d6a7}
.wf-label{flex:1;color:#444}.wf-val{font-weight:700;min-width:70px;text-align:right}
.alert-box{border-radius:8px;padding:14px 16px;margin:12px 0;border-left:4px solid}
.alert-red{background:#ffebee;border-color:#e53935}.alert-green{background:#e8f5e9;border-color:#2e7d32}
.alert-amber{background:#fff3e0;border-color:#f57c00}.alert-blue{background:#e3f2fd;border-color:#1565c0}
.alert-box strong{display:block;margin-bottom:4px;font-size:13px}
.alert-box p{margin:0;font-size:12.5px;color:#555}
.action-row{display:flex;align-items:flex-start;gap:12px;padding:12px 0;border-bottom:1px solid #f0f4fa}
.action-row:last-child{border-bottom:none}
.action-num{width:28px;height:28px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:13px;flex-shrink:0;color:#fff}
.a-red{background:#e53935}.a-green{background:#2e7d32}.a-blue{background:#1565c0}.a-amber{background:#f57c00}
.action-body strong{font-size:13px;color:#1a1a2e;display:block;margin-bottom:3px}
.action-body p{margin:0;font-size:12px;color:#666}
.action-body .impact{display:inline-block;margin-top:5px;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:700}
.imp-red{background:#ffebee;color:#c62828}.imp-green{background:#e8f5e9;color:#2e7d32}.imp-amber{background:#fff3e0;color:#e65100}
.cp-row{display:flex;align-items:center;gap:0;margin:14px 0;flex-wrap:wrap}
.cp-step{flex:1;text-align:center;min-width:100px}
.cp-month{font-size:12px;font-weight:700;color:#1565c0;margin-bottom:4px}
.cp-nr{font-size:22px;font-weight:800;color:#0f2140}
.cp-bar{height:6px;border-radius:3px;background:#e3f2fd;margin:6px 8px 0}
.cp-bar-fill{height:6px;border-radius:3px;background:linear-gradient(90deg,#5899d1,#f5d000)}
.cp-lever{font-size:10px;color:#666;margin-top:4px}
.cp-arr{font-size:20px;color:#bbb;align-self:center;padding-bottom:10px}
.tag{display:inline-block;padding:2px 7px;border-radius:10px;font-size:10.5px;font-weight:600;margin:2px 2px 0 0}
.t-stop{background:#ffebee;color:#c62828}.t-scale{background:#e8f5e9;color:#2e7d32}.t-test{background:#e3f2fd;color:#1565c0}
.skill-note{font-size:10.5px;color:#999;margin-top:6px;font-style:italic}
.highlight-box{background:linear-gradient(135deg,#f5d000 0%,#ffe57f 100%);border-radius:10px;padding:16px 20px;margin:12px 0}
.highlight-box strong{color:#0f2140;font-size:14px;display:block;margin-bottom:6px}
.highlight-box p{margin:0;color:#1a1a2e;font-size:13px}
</style>"""

    # ── Secciones 0A y 0B: análisis dinámico MTD + Mes Cerrado (§83) ─────────
    # Generadas desde comms_oc_records actuales — aparecen PRIMERO antes del análisis estático.
    dynamic_sections_html = ''
    if comms_oc_records and data_months:
        dynamic_sections_html = _build_dynamic_analysis_html(comms_oc_records, data_months)

    html = _css + '<div class="oca">\n' + dynamic_sections_html + """

<!-- 3 Skills × Datos reales Q1-2026 | KPI v2.4 · Comms v3.4 (Modos 14/17/18) · OPTIMIZADOR v4.1 (9 Patrones Cross-Signal) · §80/§81 formula fix aplicado -->

<div class="oca-hero">
  <div class="oca-sub">● KPI Skill v2.4 · Comms Skill v3.4 (Modos 14/17/18) · OPTIMIZADOR v4.1 (9 Patrones Cross-Signal) · KPI: Mar-26 real · Comms: Abr-26 D30 · 30-Abr-2026 · §80 USER_INC fix · §81 RE-ACTIVATION incluida</div>
  <h1>OC+UCR — 7 señales que el dashboard no muestra</h1>
  <div class="oca-bl">
    <strong>Bottom Line (OPTIMIZADOR v4.1)</strong>: Q1 2026 mejoró mes a mes (-29.7%→-14.1% vs plan). Pero el análisis cross-signal 30-Abr revela 7 agujas en el pajar:
    <strong>(1) 🔴 URGENTE P9: Colapso `MONIN_AO-UCR_ALL_INST`</strong> — Feb-26: +24K NR → Abr-26: +319 (-99%). Causa desconocida. Si es error: +24K NR recuperables HOY.
    <strong>(2) 🔴 P8: Brecha transición familia MONIN-AO</strong> — La familia `PUSHMP_DACCNT_MONIN_AO` traía 50K NR/mes (Jul-Nov-25) y fue reemplazada por `flows_CHURN` (21K/mes Abr). GAP estructural: -25-30K NR/mes que no se cierra solo.
    <strong>(3) 🟡 WPP multi-decline Abr-26</strong>: CHURN -4K + STOCK -1K + NEW -1K = -6K acumulado en 3 campañas simultáneas. Señal de saturación de audiencia, no de campaña individual.
    <strong>(4) RATIO_CANIBALIZACION ≈ 0.97</strong> — solo el 3% de las conversiones positivas son verdaderamente incrementales. El canal NO es el problema — el CG sí.
    <strong>(5) INDIVIDUAL LIFE CYCLE creció +137% en Q1</strong> mientras DIGITAL ACCOUNTS cayó -55%: el mix de BL se invierte solo — oportunidad de re-asignación.
    <strong>(6) GENERIC_MP (RE-Drawer) llegó a PEAK en Mar (+883 UI, 4.39 UI/comm)</strong> y desapareció en Abril sin razón documentada. El canal sigue generando (+16.7K).
    <strong>(7) WPP tiene OR 65-68% en TODOS los meses</strong> con solo 170-290 comms vs 1,600+ PUSH. El canal más sub-escalado del portafolio.
    YTD empresa: +15.4% sobre plan (orgánico compensa, pero es un colchón frágil).
  </div>
</div>

<div class="oca-kpi-row">
  <div class="oca-kpi green">
    <div class="kl">Mar-26 OC+UCR (real confirmado)</div>
    <div class="kv">148.9K</div>
    <div class="kd pos">+10% vs Feb · Mejor mes Q1 · IS=0.95</div>
  </div>
  <div class="oca-kpi amber">
    <div class="kl">Abr-26 pace D25</div>
    <div class="kv">~133K</div>
    <div class="kd warn">Pandora lag 0.2 · -10.7% vs Mar</div>
  </div>
  <div class="oca-kpi red">
    <div class="kl">Ratio Canib. comms (Patrón 5)</div>
    <div class="kv">~0.97</div>
    <div class="kd neg">97% orgánico · 3% incremental real</div>
  </div>
  <div class="oca-kpi gold">
    <div class="kl">WPP OR consistente (Patrón 4)</div>
    <div class="kv">65-68%</div>
    <div class="kd pos">5× EMAIL · 170-290 comms/mes · sub-escalado</div>
  </div>
</div>

<!-- SECCIÓN 1: PATRONES CROSS-SIGNAL -->
<div class="oca-section" style="border-left:4px solid #f5d000;margin-bottom:16px">
  <h2>⚡ OPTIMIZADOR v4.1 — 7 Patrones detectados en datos reales (9 tipos disponibles)</h2>
  <div class="oca-3col">
    <div class="oca-card" style="border-top:3px solid #c62828">
      <h3>🔴 Patrón 5: RATIO_CANIBALIZACION ~0.97</h3>
      <p style="font-size:12px;color:#555">USER_INC NETO: +2,214 (Ene) · +2,652 (Feb) · +3,742 (Mar) · +63 (Abr). Positivo bruto por canal: PUSH +42-56K, RE-DRAWER +17-21K, WPP +7-9K. Ratio ≈ 0.97: el 97% son conversiones orgánicas. <strong>No es que las comms no sirven — el experimento mide principalmente conversiones que ya ocurrirían.</strong></p>
      <p style="font-size:11px;color:#c62828;font-weight:700;margin-top:6px">Acción: revisar diseño del CG antes de invertir en volumen. El canal NO está fallando.</p>
    </div>
    <div class="oca-card" style="border-top:3px solid #2e7d32">
      <h3>🟢 Patrón 4: WPP = motor invisible</h3>
      <p style="font-size:12px;color:#555">OR 65-68% constante en Ene, Feb, Mar (vs PUSH 3-5%, EMAIL 23-27%). Solo 170-290 comms/mes vs 1,600+ PUSH. La asignación está 5-8× invertida vs la eficiencia real. Con 1,000 comms WPP = estimado +5-10K UI adicionales. <strong>Es estructura, no timing.</strong></p>
      <p style="font-size:11px;color:#2e7d32;font-weight:700;margin-top:6px">Acción: escalar WPP de 200 → 800-1,000 comms/mes. Costo: $0. ETA: 1 semana.</p>
    </div>
    <div class="oca-card" style="border-top:3px solid #e65100">
      <h3>🟠 Patrón 3: DIGITAL ACCOUNTS en suelo invisible</h3>
      <p style="font-size:12px;color:#555">BL más grande en Ene (+38.5K IS-adj) → cayó 55% en Abr (+17.3K). Audiencia PUSH saturada. El canal sigue enviando pero la eficiencia colapsa. Cross-signal: si se migra DIGITAL ACCOUNTS de PUSH → WPP, el OR recuperaría eficiencia inmediatamente.</p>
      <p style="font-size:11px;color:#e65100;font-weight:700;margin-top:6px">Acción: migrar DIGITAL ACCOUNTS de PUSH → WPP o EMAIL. Mismo BL, diferente canal.</p>
    </div>
  </div>
  <div class="oca-2col" style="margin-top:14px">
    <div class="oca-card" style="border-top:3px solid #1565c0">
      <h3>🔵 Patrón 6: Lag Pandora — el peor mes viene</h3>
      <p style="font-size:12px;color:#555">Pandora cortó a 0.2 el 18-Mar. Lag documentado: 4-6 semanas. El colapso de Abr (+63 neto vs +3,742 Mar) es exactamente ese lag. <strong>Mayo IS 0.87 + Pandora 0.2 = riesgo NR &lt;120K si no se actúa esta semana.</strong> Cada semana de delay = -3,600 NR adicionales perdidos (calibrador 0.2 × 7 días × eficiencia histórica).</p>
      <p style="font-size:11px;color:#1565c0;font-weight:700;margin-top:6px">Acción URGENTE: restaurar Pandora ≥ 0.4 en May D1-7. Costo: $0.</p>
    </div>
    <div class="oca-card" style="border-top:3px solid #7627bb">
      <h3>🟣 Patrón 2: GENERIC_MP en PEAK — ausente en Abr</h3>
      <p style="font-size:12px;color:#555">MLM_DRW_UCR_I_EG_MP_GENERIC_MP llegó a ID=1.00 en Mar-26 (4.39 UI/comm — mejor RE del portafolio). En Abril: AUSENTE. El canal RE-DRAWER sigue fuerte (+16.7K) pero sin esta campaña. Familia STOCK: MONEYINHI2 (+18 Abr) vs MONEYINAM (+25 Abr) — dos campañas compitiendo por la misma audiencia.</p>
      <p style="font-size:11px;color:#7627bb;font-weight:700;margin-top:6px">Acción: reactivar GENERIC_MP + apagar MONEYINAM. Estimado: +800-900 + liberar audiencia.</p>
    </div>
  </div>
  <div class="skill-note">Fuente: OPTIMIZADOR v4.1 · KPI context §B3 · Comms_OC Abr-26 D30 · comms_monthly_summary.md · Comms Skill Modos 14/17/18</div>
</div>

<!-- SECCIÓN 1B: PATRONES 8 Y 9 — ALERTAS NUEVAS 30-ABR -->
<div class="oca-section" style="border-left:4px solid #c62828;margin-bottom:16px">
  <h2>🚨 OPTIMIZADOR v4.1 — Patrones 8 y 9 activados (30-Abr-2026)</h2>
  <div class="oca-2col">

    <div class="oca-card" style="border-top:3px solid #c62828">
      <h3>🔴 Patrón 9: Colapso Súbito — MONIN_AO-UCR_ALL_INST (-99%)</h3>
      <table class="oca-table">
        <thead><tr><th>Mes</th><th>USER_INC</th><th>Delta</th><th>Estado</th></tr></thead>
        <tbody>
          <tr><td>Feb-26</td><td class="pos">+24,000</td><td>—</td><td class="pos">🏆 MOTOR</td></tr>
          <tr><td>Mar-26</td><td class="warn">?</td><td>—</td><td class="warn">A verificar</td></tr>
          <tr style="background:#ffebee;font-weight:700"><td>Abr-26</td><td class="neg">+319</td><td class="neg">-99%</td><td class="neg">🔴 COLAPSO</td></tr>
        </tbody>
      </table>
      <div class="alert-box alert-red" style="margin-top:10px">
        <strong>⚡ URGENTE 72h — diagnosticar causa del colapso</strong>
        <p>Campaña: <code>MLM_MP_ML-PUSHML_DACCNT_MONIN_AO-UCR_ALL_INST_X_X_DEFAULT_</code><br>
        Feb-26: +24,000 NR → Abr-26: +319 NR (<strong>-99%</strong>). Caída abrupta, no gradual (≠ Patrón 3).<br>
        <strong>Hipótesis A</strong>: Pausa intencional no documentada → Si sí: documentar reemplazo.<br>
        <strong>Hipótesis B</strong>: Error operativo (CG roto, segmentación dañada) → Si sí: reactivar. Impacto: <strong>+24K NR inmediatos</strong>.<br>
        Cada semana sin diagnóstico = 6,000 NR perdidos irrecuperables.</p>
      </div>
    </div>

    <div class="oca-card" style="border-top:3px solid #e65100">
      <h3>🟠 Patrón 8: Brecha de Transición — Familia MONIN-AO</h3>
      <table class="oca-table">
        <thead><tr><th>Familia</th><th>Peak</th><th>Dic-25</th><th>Ene-26</th><th>Abr-26</th></tr></thead>
        <tbody>
          <tr><td style="font-size:10px"><strong>PUSHMP_DACCNT_MONIN_AO</strong> (antigua)</td><td class="pos">50K/mes</td><td class="warn">35K</td><td class="neg">11K → reemplazo</td><td class="neg">—</td></tr>
          <tr><td style="font-size:10px"><strong>flows_CHURN MLM_I_EG_MTK</strong> (nueva)</td><td>—</td><td>—</td><td class="warn">11K</td><td class="warn">21K</td></tr>
          <tr style="background:#fff3e0;font-weight:700"><td>GAP de transición</td><td colspan="4" class="neg" style="text-align:center">-25-30K NR/mes que no se ha recuperado</td></tr>
        </tbody>
      </table>
      <p style="font-size:12px;color:#555;margin-top:8px">La familia <code>flows_CHURN</code> escaló rápido hasta Feb-26 (+25K) pero está en <strong>meseta con tendencia bajista</strong> (Feb=25K → Mar=23K → Abr=21K). Sin intervención, el GAP no se cierra. El gap representa ~15-18% del target mensual OC+UCR.</p>
      <div class="alert-box alert-amber" style="margin-top:8px">
        <strong>Opciones para cerrar el gap:</strong>
        <p>(A) Escalar <code>flows_CHURN</code> de 21K → 35K — ¿hay audiencia disponible?<br>
        (B) Reactivar familia MONIN-AO en versión actualizada.<br>
        (C) Compensar con escala WPP (+20-30K cuando live) + EMAIL sistematizado.<br>
        <strong>Costo de no actuar: -25K NR/mes acumulados cada mes.</strong></p>
      </div>
    </div>
  </div>

  <div class="oca-section" style="margin-top:14px;background:#fff8e1;border-radius:8px;padding:14px">
    <h3 style="margin:0 0 10px;font-size:13px">🟡 WPP Multi-decline Abril — Saturación de audiencia, no de campaña</h3>
    <table class="oca-table">
      <thead><tr><th>Campaña WPP</th><th>Mar-26</th><th>Abr-26</th><th>Delta</th><th>Diagnóstico</th></tr></thead>
      <tbody>
        <tr><td style="font-size:10px">MLM_MP_WSPP-WAP_..._I-EG-CHURN</td><td>~10K</td><td class="neg">6K</td><td class="neg">-4K</td><td>Principal · 60% del decline WPP</td></tr>
        <tr><td style="font-size:10px">MLM_MP_WSPP-WAP_..._I-EG-STOCK</td><td>base</td><td class="neg">base-1K</td><td class="neg">-1K</td><td>Secundario</td></tr>
        <tr><td style="font-size:10px">MLM_MP_WSPP-WAP_..._I-EG-NEW</td><td>base</td><td class="neg">base-1K</td><td class="neg">-1K</td><td>Secundario</td></tr>
        <tr style="font-weight:700;background:#fff3e0"><td>Total WPP decline</td><td>~10K</td><td class="neg">~4-5K</td><td class="neg">-6K (-55%)</td><td>⚠️ Multi-campaña → audiencia, no VP</td></tr>
      </tbody>
    </table>
    <p style="font-size:12px;color:#555;margin-top:8px"><strong>Patrón 3 activo en WPP</strong>: Cuando 3 campañas diferentes declinan simultáneamente en el mismo canal, el problema es la <strong>audiencia agotada</strong>, no el mensaje individual. Fix: refresh de segmentación de audiencia WPP + rotar hacia segmentos no-saturados. Si TOTAL_TEST también bajó → confirmar agotamiento de reach.</p>
  </div>

  <div class="skill-note">Fuente: OPTIMIZADOR v4.1 Patrones 8+9 · Comms_OC Abr-26 · datos provistos por equipo 30-Abr-2026</div>
</div>

<!-- SECCIÓN 2: Q1 vs PLAN + CANAL PERFORMANCE -->
<div class="oca-2col">
  <div class="oca-section">
    <h2>📊 Performance vs Plan — Q1 2026 real <span class="badge badge-amber">Brecha cerrándose</span></h2>
    <table class="oca-table">
      <thead><tr><th>Mes</th><th>OC Real</th><th>Plan</th><th>vs Plan</th><th>IS</th><th>N+R_adj</th><th>Driver clave</th></tr></thead>
      <tbody>
        <tr><td>Ene-26</td><td>121.8K</td><td>173.3K</td><td class="neg">-29.7%</td><td>0.83</td><td class="warn">146.7K</td><td>IS bajo · Churn Paid excl. -20K</td></tr>
        <tr><td>Feb-26</td><td>135.3K</td><td>173.3K</td><td class="neg">-21.9%</td><td>0.89</td><td class="warn">152.0K</td><td>Pandora 0.6 activo · recuperación</td></tr>
        <tr><td>Mar-26</td><td>148.9K</td><td>173.3K</td><td class="neg">-14.1%</td><td>0.95</td><td class="warn">156.7K</td><td>Mejor Q1 · Pandora cortó a 0.2</td></tr>
        <tr style="font-weight:700;background:#fff8e1"><td>Abr-26 (D25)</td><td>~133K</td><td>173.3K</td><td class="neg">~-23%</td><td>0.97</td><td class="neg">~137K</td><td>Lag Pandora + PUSH saturación</td></tr>
        <tr style="color:#777;font-size:11px"><td colspan="7">N+R_adj = N+R/IS · YTD empresa: +15.4% · X-Channel AUC OC: +13% Mar-26</td></tr>
      </tbody>
    </table>
    <div class="alert-box alert-blue" style="margin-top:12px">
      <strong>💡 Patrón 1 — Divergencia KPI-Comms</strong>
      <p>N+R IS-ajustado Q1 mejora mes a mes (~152K prom). Pero USER_INC NETO de comms: +2.2K → +3.7K → +63. El crecimiento de N+R es mayoritariamente orgánico/IS — no de comms incrementales. Las comms tienen RATIO_CANIBALIZACION ~0.97. Sin embargo: recortar comms sería un error — el "pisado" de audiencia también protege la conversión orgánica.</p>
    </div>
  </div>
  <div class="oca-section">
    <h2>📡 USER_INC positivo por Canal — Q1 2026 <span class="badge badge-blue">Comms Skill Modo 14</span></h2>
    <table class="oca-table">
      <thead><tr><th>Canal</th><th>Ene-26</th><th>Feb-26</th><th>Mar-26</th><th>Abr-26</th><th>OR</th><th>Señal</th></tr></thead>
      <tbody>
        <tr><td><strong>PUSH</strong></td><td>+42.2K</td><td>+44.1K</td><td class="pos">+55.9K</td><td class="warn">+37.6K ↓</td><td>~3-5%</td><td>⚠️ Saturación BL DIGITAL ACCOUNTS</td></tr>
        <tr><td><strong>RE-DRAWER</strong></td><td>+16.8K</td><td>+17.4K</td><td class="pos">+21.3K</td><td>+16.7K</td><td>—</td><td>✅ Motor estable · GENERIC_MP ausente</td></tr>
        <tr><td><strong>WPP</strong></td><td>+9.5K</td><td>+7.8K</td><td>+7.9K</td><td>+5.4K</td><td class="pos">65-68%</td><td>🚀 OR 5× EMAIL · 170-290 comms</td></tr>
        <tr><td><strong>PANDORA</strong></td><td>+4.2K</td><td class="pos">+11.4K</td><td class="warn">+5.7K ↓</td><td>—</td><td>—</td><td>🔴 Cal 0.2 · ausente Abr</td></tr>
        <tr><td><strong>EMAIL</strong></td><td>—</td><td>—</td><td>+4.3K</td><td class="pos">+6.3K ↑</td><td class="pos">23-27%</td><td>🚀 Emergente · OR 5-8× PUSH</td></tr>
        <tr><td><strong>RE-QA</strong></td><td>+2.8K</td><td>+3.1K</td><td>—</td><td class="pos">+5.7K ↑</td><td>—</td><td>↑ Creciendo en Abr</td></tr>
      </tbody>
    </table>
    <div class="highlight-box" style="margin-top:10px">
      <strong>🔑 WPP como driver estructural (no de timing)</strong>
      <p>OR 65-68% en TODOS los meses vs IS, mes y VP. La audiencia WPP responde 5-8× mejor SIEMPRE. Escalar de 200 → 1,000 comms/mes = estimado +5-10K UI sin nueva inversión. El blocker no es eficiencia — es volumen de audiencia disponible.</p>
    </div>
  </div>
</div>

<!-- SECCIÓN 3: BL RANKINGS IS-AJUSTADOS + MARA STOP -->
<div class="oca-section">
  <h2>📈 Business Line Rankings IS-ajustados — Q1 2026 <span class="badge badge-blue">Comms Skill Modo 14</span></h2>
  <div class="oca-3col">
    <div class="oca-card" style="border-top:3px solid #2e7d32">
      <h3>🏆 TOP 3 GANADORES — IS-adj ascendente</h3>
      <table class="oca-table">
        <thead><tr><th>Business Line</th><th>Ene</th><th>Mar</th><th>Abr</th><th>Δ Q1</th></tr></thead>
        <tbody>
          <tr><td><strong>INDIVIDUAL LIFE CYCLE</strong></td><td>+15.1K</td><td class="pos">+31.2K</td><td>+23.4K</td><td class="pos">↑↑ +107%</td></tr>
          <tr><td><strong>CARDS (DEB-CARD efecto)</strong></td><td>+2.5K</td><td class="pos">+6.3K</td><td class="pos">+6.4K</td><td class="pos">↑↑ +156%</td></tr>
          <tr><td><strong>MP GENERIC (RE)</strong></td><td>+3.4K</td><td>—</td><td class="pos">+5.9K</td><td class="pos">↑ Creciendo</td></tr>
        </tbody>
      </table>
      <p class="skill-note">INDIVIDUAL LIFE CYCLE incluye GENERIC_MP, DEB-CARD, flows trigger. Esta audiencia responde mejor a triggers comportamentales. El crecimiento +107% en Q1 es la señal más clara de dónde está la oportunidad.</p>
    </div>
    <div class="oca-card" style="border-top:3px solid #c62828">
      <h3>⚠️ BOTTOM 3 — IS-adj descendente</h3>
      <table class="oca-table">
        <thead><tr><th>Business Line</th><th>Ene</th><th>Mar</th><th>Abr</th><th>Δ Q1</th></tr></thead>
        <tbody>
          <tr><td><strong>DIGITAL ACCOUNTS</strong></td><td class="pos">+38.5K</td><td class="neg">+23.3K</td><td class="neg">+17.3K</td><td class="neg">↓↓ -55%</td></tr>
          <tr><td><strong>SIN_BL (no atribuido)</strong></td><td>+30.7K</td><td>+32.6K</td><td class="warn">+24.7K</td><td class="warn">↓ Abr cae</td></tr>
          <tr><td><strong>WALLET</strong></td><td>—</td><td class="warn">+7.0K</td><td>—</td><td class="warn">? Solo Mar</td></tr>
        </tbody>
      </table>
      <p class="skill-note">DIGITAL ACCOUNTS: de BL dominante (+38.5K) a caída del 55% en Q1. Diagnóstico Patrón 3: saturación PUSH. Fix: migrar este BL a WPP o EMAIL = recovery inmediato sin inversión adicional.</p>
    </div>
    <div class="oca-card" style="border-top:3px solid #c62828">
      <h3>🛑 MARA — Modo 18: STOP definitivo</h3>
      <p style="font-size:12px;font-weight:700;color:#555;margin-bottom:6px">MLM-ML-I-EG-UCR-MTK-CAMP-NIA-MARA</p>
      <table class="oca-table">
        <thead><tr><th>Mes</th><th>USER_INC</th><th>OR</th><th>ID</th><th>Fase</th></tr></thead>
        <tbody>
          <tr><td>Ene-26</td><td class="neg">0</td><td>—</td><td class="neg">0.00</td><td class="neg">CANIB.</td></tr>
          <tr><td>Feb-26</td><td class="neg">0</td><td>13.0%</td><td class="neg">0.00</td><td class="neg">CANIB.</td></tr>
          <tr><td>Mar-26</td><td class="neg">0</td><td>12.5%</td><td class="neg">0.00</td><td class="neg">CANIB.</td></tr>
        </tbody>
      </table>
      <p style="font-size:11px;color:#c62828;font-weight:700;margin-top:8px">⚠️ REGLA 6 Anti-Alucinación: "MARA" en múltiples meses = código interno, NO es el Maratón CDMX (fue Ago-25). OR 12-13% (abre curiosidad, nunca convierte). USER_INC=0 siempre. Impacto POSITIVO de parar: libera audiencia. Impacto NEGATIVO: ninguno documentado. VEREDICTO: PARAR.</p>
    </div>
  </div>
</div>

<!-- SECCIÓN 4: CARRERA DE CAMPAÑAS CLAVE — Modo 18 -->
<div class="oca-section">
  <h2>🔬 Modo 18: Carrera histórica de campañas clave <span class="badge badge-blue">Comms Skill Modo 18</span></h2>
  <div class="oca-2col">
    <div class="oca-card" style="border-top:3px solid #2e7d32">
      <h3>✅ GENERIC_MP (RE-Drawer) — PEAK en Mar, ausente en Abr</h3>
      <table class="oca-table">
        <thead><tr><th>Mes</th><th>UI</th><th>n_comms</th><th>UI/comm</th><th>ID</th><th>Fase</th></tr></thead>
        <tbody>
          <tr><td>Ene-26</td><td>+642</td><td>345</td><td>1.86</td><td>0.73</td><td class="warn">MESETA</td></tr>
          <tr><td>Feb-26</td><td>+530</td><td>174</td><td>3.05</td><td>0.60</td><td class="warn">MESETA</td></tr>
          <tr style="background:#e8f5e9"><td><strong>Mar-26</strong></td><td class="pos"><strong>+883</strong></td><td>201</td><td class="pos"><strong>4.39</strong></td><td class="pos"><strong>1.00</strong></td><td class="pos">🏆 PEAK</td></tr>
          <tr><td>Abr-26</td><td class="neg">AUSENTE</td><td>—</td><td>—</td><td class="neg">?</td><td class="neg">PAUSA?</td></tr>
        </tbody>
      </table>
      <p style="font-size:11.5px;margin-top:8px">Impacto SI se reactivara: POSITIVO +600-900 UI/mes (efficiency score en PEAK). Impacto SI sigue ausente: NEGATIVO -900 UI/mes que el canal RE-DRAWER no puede recuperar sin ella. El canal sigue fuerte (+16.7K Abr) — solo falta la campaña.</p>
      <p style="font-size:11px;color:#c62828;font-weight:700">⚡ REACTIVAR ESTA SEMANA. Golden Rule: no sustituir con variante similar sin entender por qué fue pausada.</p>
    </div>
    <div class="oca-card" style="border-top:3px solid #f57c00">
      <h3>📧 DEB-CARD EMAIL — OR excepcional consistente</h3>
      <table class="oca-table">
        <thead><tr><th>Mes</th><th>UI</th><th>OR</th><th>ID</th><th>Fase</th></tr></thead>
        <tbody>
          <tr><td>Ene-26</td><td>+19</td><td class="pos">18.0%</td><td>0.12</td><td>INICIO</td></tr>
          <tr style="background:#fff3e0"><td>Feb-26</td><td class="pos"><strong>+127</strong></td><td class="pos">26.7%</td><td class="pos">0.82</td><td class="pos">MESETA</td></tr>
          <tr><td>Mar-26</td><td class="pos">+155</td><td class="pos">23.6%</td><td class="pos"><strong>1.00</strong></td><td class="pos">🏆 PEAK</td></tr>
          <tr><td>Abr-26</td><td>+44</td><td class="pos">27.2%</td><td>0.28</td><td class="warn">FATIGA ALCANCE</td></tr>
        </tbody>
      </table>
      <p style="font-size:11.5px;margin-top:8px">ID de Abr = 0.28 pero OR 27.2% (más alto del historial). La fatiga es de VOLUMEN, no de calidad del VP. El OR del canal sigue siendo excepcional. El fix: más reach con el mismo VP. Potencial: +1-3K UI/mes con ×3 comms enviadas.</p>
    </div>
  </div>
  <div class="oca-2col" style="margin-top:14px">
    <div class="oca-card" style="border-top:3px solid #1565c0">
      <h3>🚀 WPP DACCNT/MONIN — OR 65-68% cada mes</h3>
      <table class="oca-table">
        <thead><tr><th>Mes</th><th>UI</th><th>OR</th><th>n_comms</th><th>UI/comm</th></tr></thead>
        <tbody>
          <tr><td>Ene-26</td><td>+70</td><td class="pos">67.9%</td><td>~20</td><td>3.5</td></tr>
          <tr><td>Feb-26</td><td>+35</td><td class="pos">65.8%</td><td>~15</td><td>2.3</td></tr>
          <tr><td>Mar-26</td><td>+61</td><td class="pos">66.2%</td><td>~20</td><td>3.1</td></tr>
        </tbody>
      </table>
      <p style="font-size:11.5px;margin-top:8px">OR 65-68% independiente del mes, IS o VP. Es el canal per se. La "fatiga" de Feb (ID bajo) se recuperó en Mar — no es degradación estructural. Escalar de 20 → 500 comms manteniendo el mismo OR: estimado +800-1,500 UI/mes. El VP DACCNT/MONIN + canal WPP = combinación ganadora documentada.</p>
    </div>
    <div class="oca-card" style="border-top:3px solid #7627bb">
      <h3>🏆 MONEYINHI2 (familia STOCK) — Ganador rodeado de ruido</h3>
      <table class="oca-table">
        <thead><tr><th>Mes</th><th>UI</th><th>OR</th><th>% familia</th><th>Fase</th></tr></thead>
        <tbody>
          <tr><td>Ene-26</td><td>+157</td><td>2.4%</td><td>~40%</td><td class="warn">FATIGA</td></tr>
          <tr><td>Feb-26</td><td>(no top)</td><td>—</td><td>—</td><td>—</td></tr>
          <tr style="background:#f3e5f5"><td>Mar-26</td><td class="pos"><strong>+502</strong></td><td>1.8%</td><td class="pos"><strong>56%</strong></td><td class="pos">🏆 PEAK</td></tr>
          <tr><td>Abr-26</td><td class="warn">+18</td><td>1.8%</td><td class="warn">~35%</td><td class="neg">COLAPSO</td></tr>
        </tbody>
      </table>
      <p style="font-size:11.5px;margin-top:8px">Modo 17 familia STOCK: MONEYINHI2 genera 56% del USER_INC familiar en Mar. STOCK_MONEYINAM (+25 Abr, mismo canal+fecha) compite por la misma audiencia sin aportar proporcionalmente. Apagar MONEYINAM → libera audiencia para MONEYINHI2. Estimado: +5-8K UI/mes.</p>
    </div>
  </div>
</div>

<!-- SECCIÓN 5: JOURNEY CANIBALIZADORES + EFICIENCIA COMMS -->
<div class="oca-2col">
  <div class="oca-section">
    <h2>⚠️ Causa Raíz: JOURNEY Canibalizadores <span class="badge badge-red">CRÍTICO · Pausar HOY</span></h2>
    <div class="oca-2col" style="margin-bottom:12px">
      <div>
        <h3 style="font-size:13px;margin:0 0 8px">🦷 El mecanismo del daño</h3>
        <p style="font-size:12.5px;color:#444">Los journeys <strong>CARABO</strong> y <strong>MST2MP</strong> corren TODOS los días. Llegan al usuario antes de que convierta orgánicamente pero no logran que convierta mejor que el grupo de control. Resultado: USER_INC negativo sistemático = canibalismo de conversión orgánica.</p>
        <div class="alert-box alert-red" style="margin-top:8px">
          <strong>BT_OC_DASHBOARD_ALL_CAMPAIGNS_NR confirma:</strong>
          <p>USER_INC negativo en &gt;50% de envíos · RATIO_CANIBALIZACION &gt; 0.70 · MST2MP: -174 NR/7días documentado (§63 History.md).</p>
        </div>
      </div>
      <div>
        <h3 style="font-size:13px;margin:0 0 8px">🎯 Los culpables identificados</h3>
        <table class="oca-table">
          <thead><tr><th>Journey</th><th>Flow BQ</th><th>Acción</th></tr></thead>
          <tbody>
            <tr><td style="font-size:11px">JNY_CARABO</td><td>APP-MP-INSTALL</td><td><span class="t-stop">PAUSAR HOY</span></td></tr>
            <tr><td style="font-size:11px">JNY_MST2MP</td><td>APP-MP-INSTALL</td><td><span class="t-stop">PAUSAR HOY</span></td></tr>
            <tr style="background:#e8f5e9"><td style="font-size:11px">flows_*_mer_*</td><td>Trigger Miércoles</td><td><span class="t-scale">MANTENER ✓</span></td></tr>
          </tbody>
        </table>
        <p class="skill-note" style="margin-top:6px">MST2MP = Meses Sin Tarjeta (§63). Journeys trigger-based miércoles = USER_INC positivo histórico (§61). El patrón: trigger-based + día específico ≠ automation diaria.</p>
      </div>
    </div>
    <div class="alert-box alert-green">
      <strong>Recovery estimado: +14K NR/mes · Costo: $0</strong>
      <p>Pausar CARABO + MST2MP = eliminar -650 NR/día de canibalización. Cada día de delay = -650 NR adicionales perdidos. <strong>Golden Rule OPTIMIZADOR: esta pausa NO es una recomendación — ES UNA OBLIGACIÓN. Ver §63 History.md — protocolo validado.</strong></p>
    </div>
  </div>

  <div class="oca-section">
    <h2>📊 Eficiencia de Comms — schema §75 real <span class="badge badge-blue">Comms Skill Modo 14</span></h2>
    <div class="alert-box alert-amber" style="margin-bottom:12px">
      <strong>⚠️ Cambio de metodología §75</strong>
      <p>Schema viejo usaba M_INC_USERS (KPI Match, todos los grupos tocados, número mayor). Schema nuevo §75 usa NR_INC_USERS calibrado por Blacklist (TEST - CONTROL, verdaderamente incremental, número más pequeño pero más preciso). Los números actuales son correctos — el método anterior sobreestimaba la contribución.</p>
    </div>
    <table class="oca-table">
      <thead><tr><th>Mes</th><th>NR/comm (score)</th><th>USER_INC neto</th><th>OR dominante</th><th>Canal con OR máx</th></tr></thead>
      <tbody>
        <tr><td>Ene-26</td><td>5.7</td><td>+2,214</td><td>3.3% (PUSH)</td><td>PUSH (2,573 comms)</td></tr>
        <tr><td>Feb-26</td><td>~7.5 est.</td><td>+2,652</td><td>26.7% (EMAIL)</td><td>EMAIL DEB-CARD</td></tr>
        <tr style="background:#e8f5e9;font-weight:700"><td>Mar-26</td><td class="pos">10.3 ↑</td><td class="pos">+3,742</td><td>23.6% (EMAIL)</td><td>EMAIL DEB-CARD</td></tr>
        <tr style="background:#ffebee;font-weight:700"><td>Abr-26 (D25)</td><td class="neg">0.2 ↓↓</td><td class="neg">+63</td><td>27.2% (EMAIL)</td><td>EMAIL crece +46%</td></tr>
      </tbody>
    </table>
    <div class="highlight-box" style="margin-top:12px">
      <strong>💡 EMAIL como contratendencia en Abril</strong>
      <p>En Abril, EMAIL es el ÚNICO canal que CRECIÓ: +592 comms (+46% vs Mar) y +6.3K UI positivo (vs +4.3K Mar). Mientras PUSH colapsa por saturación, EMAIL mantiene OR 27.2%. UCRANIA E&G también crece: +7.9% MoM (+3,820 NR adicionales). El freno es SOLO el calibrador Pandora 0.2 — sin él, el canal habría estado ~+6K por encima del pace actual.</p>
    </div>
  </div>
</div>

</div>

<!-- SECCIÓN 6: QUICK WINS + CAMINO CRÍTICO -->
<div class="oca-2col">
  <div class="oca-section">
    <h2>⚡ Quick Wins — Esta semana, sin inversión adicional</h2>
    <div class="action-row">
      <div class="action-num a-red">0</div>
      <div class="action-body"><strong>🔴 CRÍTICO 72h: Diagnosticar colapso MONIN_AO-UCR_ALL_INST (P9)</strong><p>[OPTIMIZADOR Patrón 9 — Colapso Súbito] Feb-26: +24,000 NR → Abr-26: +319 NR (-99% en 2 meses). Verificar: ¿pausa intencional o error operativo? TOTAL_TEST: ¿cayó o se mantiene? Si TOTAL_TEST cayó = envío detenido (pausa/error). Si TOTAL_TEST estable pero USER_INC colapsa = experimento contaminado. Si es error: reactivar = +24K NR inmediatos. Responsable: equipo CRM OC. ETA: antes del 3-May.</p></div>
    </div>
    <div class="action-row">
      <div class="action-num a-red">1</div>
      <div class="action-body"><strong>🔴 URGENTE: EMAIL sistematizar — OR 23-27% vs PUSH 3-5%: el motor oculto más grande del portafolio</strong><p>[Cross-Signal Pattern 4 — Timing/Canal como driver real] Abr-26 confirma: EMAIL DEB-CARD OR 23.6-27.2% (5-8× mayor que PUSH). Solo 786 comms EMAIL/mes vs 1,631 PUSH — la asignación está invertida. MONEYINHI2 y DEB-CARD (EMAIL) son los top performers del portafolio. Acción: duplic...</p></div>
    </div>
    <div class="action-row">
      <div class="action-num a-red">2</div>
      <div class="action-body"><strong>🔴 URGENTE: Apagar JOURNEY canibalizadores + simplificar familia STOCK</strong><p>[Cross-Signal Pattern 2 — Efecto Familia] Familia flows_..._STOCK: MONEYINHI2 genera 56% del USER_INC total de la familia. STOCK_MONEYINAM (Abr: +25 UI) compite por la misma audiencia que el ganador. JOURNEY CARABO + MST2MP confirmados canibalizadores (§63). Acción: pausar STOCK_...</p></div>
    </div>
    <div class="action-row">
      <div class="action-num a-green">3</div>
      <div class="action-body"><strong>🟡 Restaurar Pandora a ≥0.4 — lag de 4-6 semanas ya está activo</strong><p>[Cross-Signal Pattern 6 — Lag de calibrador] Pandora bajó a 0.2 el 18-Mar. El colapso de Abr (+63 USER_INC) es exactamente el lag esperado. El peor mes todavía viene: Mayo IS 0.87 + Pandora 0.2 = riesgo crítico. Acción: restaurar calibrador UCR a 0.4+ en la quincena S1 de Mayo. E...</p></div>
    </div>
    <div class="action-row">
      <div class="action-num a-green">4</div>
      <div class="action-body"><strong>🟡 Rotar VP: MONIN fatigado → Cashback en quincena S2 Mayo</strong><p>+3-5K NR recuperados. Comms_OC confirma fatiga MONIN (ID &lt; 0.3 consistente). La campaña I-M-NR-CB-QUIN-A-0815 (Ago-25): +5,657 UI con VP Cashback fresco. Premium de timing quincena: 2-3× vs misma campaña en S1. Acción: lanzar Cashback en D8-D16 Mayo — combina VP fresco + timing I...</p></div>
    </div>
    <div class="action-row">
      <div class="action-num a-green">5</div>
      <div class="action-body"><strong>🟡 Solicitar inversión incremental OC — X-Channel AUC +13% justifica el caso</strong><p>+4K NR/mes por cada 10% adicional de budget. OC generó X-Channel AUC +13% en Mar-26 mientras el volumen caía -15.5%. Las comms que siguen activas son cada vez más eficientes — no hace falta más comms, hace falta más budget para escalar las que funcionan (EMAIL + PUSH curado). Con...</p></div>
    </div>
    <div class="alert-box alert-green" style="margin-top:10px">
      <strong>💰 Total estimado: +20-30K N+R/mes adicionales en Mayo — EMAIL sistematizar (+12-18K) + apagar ruido/canibalizadores (+5-8K) + Pandora lag (+3-5K). Sin inversión adicional. Solo ejecución esta semana.</strong>
    </div>
    <div class="skill-note">Fuente: OPTIMIZADOR v4.1 · Comms Skill Modos 14/17/18 · KPI context §B3 · Comms_OC Abr-26 D25</div>
  </div>

  <div class="oca-section">
    <h2>🚀 Camino Crítico — ~133K → 240K (Abr→Ago 2026)</h2>
    <div class="alert-box alert-red" style="margin-bottom:12px">
      <strong>⚠️ Single Point of Failure</strong>
      <p>[RIESGO ACTIVO HOY] Pandora en 0.2 + PUSH saturación = tormenta perfecta en Mayo (IS 0.87). Sin EMAIL como sustituto, el NR de Mayo caerá a ~120-130K — 30K bajo el camino crítico. El Single Point of Failure no es WPP (largo plazo) — es el lag de Pandora que se siente ahora. Señal de alerta accionable: si en May D1-7 el USER_INC de EMAIL no supera 3...</p>
    </div>
    <div class="cp-row">
      <div class="cp-step">
        <div class="cp-month">ABR 26</div>
        <div class="cp-nr">~133K</div>
        <div class="cp-bar"><div class="cp-bar-fill" style="width:55%"></div></div>
        <div class="cp-lever">⚠️ Tormenta perfecta: Pandora lag 0.2 + PUSH saturación</div>
      </div><div class="cp-arr">→</div>
      <div class="cp-step">
        <div class="cp-month">MAY 26</div>
        <div class="cp-nr">~155K</div>
        <div class="cp-bar"><div class="cp-bar-fill" style="width:65%"></div></div>
        <div class="cp-lever">Pandora ramp-up 0.2→0.6 (si se activa en may-1) · WPP U</div>
      </div><div class="cp-arr">→</div>
      <div class="cp-step">
        <div class="cp-month">JUN 26</div>
        <div class="cp-nr">~182K</div>
        <div class="cp-bar"><div class="cp-bar-fill" style="width:76%"></div></div>
        <div class="cp-lever">Pandora 0.6 estabilizado + WPP Ucrania escala + KYC aud</div>
      </div><div class="cp-arr">→</div>
      <div class="cp-step">
        <div class="cp-month">JUL 26</div>
        <div class="cp-nr">~210K</div>
        <div class="cp-bar"><div class="cp-bar-fill" style="width:87%"></div></div>
        <div class="cp-lever">MeLi Placements (Favoritos + Home) + IS 1.08 LCDLF pre-</div>
      </div><div class="cp-arr">→</div>
      <div class="cp-step">
        <div class="cp-month">AGO 26 🎯</div>
        <div class="cp-nr">~240K</div>
        <div class="cp-bar"><div class="cp-bar-fill" style="width:100%"></div></div>
        <div class="cp-lever">Todas las palancas en velocidad de crucero · IS 1.15</div>
      </div>    </div>
    <div class="alert-box alert-blue" style="margin-top:12px">
      <strong>💡 Hipótesis IS-ajustada</strong>
      <p>[URGENTE] EMAIL DEB-CARD sistemático en quincena S2 de cada mes (+12-18K NR — OR 23-27% demostrado en Mar-Abr 26 vs 3-5% PUSH · sin inversión adicional) · [URGENTE] Pandora recuperación cal 0.2→0.6 (+7K/mes — Comms_OC firma: OR 9%→13%) · [URGENTE] Apagar JOURNEY canibalizadores + STOCK_MONEYINAM (+5K NR/mes liberado) · WPP Ucrania (+20K/mes cuando live — USER_INC nueva línea CANAL=WPP) · Rotación ...</p>
    </div>
    <div class="skill-note">Fuente: OPTIMIZADOR v4.1 × KPI Skill §AE2 × Comms Modos 14/17/18 · 27-Abr-2026</div>
  </div>
</div>

<!-- SECCIÓN 7: VEREDICTO DEL VP -->
<div style="background:linear-gradient(135deg,#0f2140 0%,#1a3a6b 100%);border-radius:12px;padding:22px 26px;margin-bottom:16px">
  <h2 style="color:#f5d000;margin:0 0 14px;font-size:16px">⚖️ Veredicto del VP — 6 Decisiones No Negociables (30-Abr-2026)</h2>
  <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px">
    <div style="background:rgba(198,40,40,.25);border:1px solid rgba(198,40,40,.5);border-radius:8px;padding:14px">
      <div style="color:#ef9a9a;font-size:10px;font-weight:700;text-transform:uppercase;margin-bottom:6px">🔴 DIAGNOSTICAR — 72h (P9)</div>
      <div style="color:#fff;font-size:12px">MONIN_AO-UCR_ALL_INST: 24K→319 NR (-99%). ¿Pausa intencional o error? Si es error: +24K NR inmediatos. Cada semana sin resolver = 6K NR perdidos irrecuperables.</div>
    </div>
    <div style="background:rgba(198,40,40,.25);border:1px solid rgba(198,40,40,.5);border-radius:8px;padding:14px">
      <div style="color:#ef9a9a;font-size:10px;font-weight:700;text-transform:uppercase;margin-bottom:6px">🔴 CERRAR GAP — 2 semanas (P8)</div>
      <div style="color:#fff;font-size:12px">Familia MONIN-AO en meseta 21K vs peak 50K. GAP -25-30K/mes estructural. Escalar flows_CHURN O reactivar familia antigua actualizada O compensar con WPP+EMAIL. No se cierra solo.</div>
    </div>
    <div style="background:rgba(198,40,40,.15);border:1px solid rgba(198,40,40,.3);border-radius:8px;padding:14px">
      <div style="color:#ef9a9a;font-size:10px;font-weight:700;text-transform:uppercase;margin-bottom:6px">🔴 PARAR — HOY</div>
      <div style="color:#fff;font-size:12px">CARABO + MST2MP + MARA. -650 NR/día cada día activos. §63 protocolo validado. No hay argumento que justifique delay.</div>
    </div>
    <div style="background:rgba(255,255,255,.08);border-radius:8px;padding:14px">
      <div style="color:#a5d6a7;font-size:10px;font-weight:700;text-transform:uppercase;margin-bottom:6px">INVESTIGAR WPP — Esta semana (P3)</div>
      <div style="color:#fff;font-size:12px">3 campañas WPP bajan -6K simultáneo → saturación de audiencia. Revisar TOTAL_TEST. Si cae: refresh segmentación. Si se mantiene: rotar VP. Recuperar 3-4K del decline.</div>
    </div>
    <div style="background:rgba(255,255,255,.08);border-radius:8px;padding:14px">
      <div style="color:#80cbc4;font-size:10px;font-weight:700;text-transform:uppercase;margin-bottom:6px">REACTIVAR + ESCALAR — Esta semana</div>
      <div style="color:#fff;font-size:12px">GENERIC_MP (RE-Drawer, PEAK Mar ausente Abr). WPP 200→800+ comms (OR 67%). EMAIL DEB-CARD +reach. Pandora ≥0.4. Apagar MONEYINAM. Todo sin inversión adicional.</div>
    </div>
    <div style="background:rgba(255,255,255,.08);border-radius:8px;padding:14px">
      <div style="color:#f5d000;font-size:10px;font-weight:700;text-transform:uppercase;margin-bottom:6px">ENTENDER — Esta semana</div>
      <div style="color:#fff;font-size:12px">RATIO_CANIBALIZACION ~0.97. Revisar diseño del CG antes de aumentar volumen. El problema no es el canal — es la calidad del experimento. Sin esto, escalar es quemar presupuesto.</div>
    </div>
  </div>
  <div style="margin-top:14px;padding:10px 14px;background:rgba(245,208,0,.1);border-radius:6px;color:#f5d000;font-size:12px">
    <strong>💰 NR potencial si se ejecutan las 6 decisiones en Mayo:</strong> P9 diagnóstico (+24K si error) · P8 gap closure (+8-12K incrementales) · WPP refresh (+3-4K) · GENERIC_MP reactivación (+800) · Journeys pausa (+14K liberado) · Pandora ramp-up (+7K) = <strong>+30-60K NR/mes adicionales en Mayo. La mayoría sin inversión nueva.</strong>
  </div>
  <div style="margin-top:10px;padding-top:10px;border-top:1px solid rgba(255,255,255,.15);color:#a8c4e8;font-size:11px">
    KPI Skill v2.4 (MODO_OC_UCR) · Comms Skill v3.4 (Modos 14/17/18) · OPTIMIZADOR v4.1 (9 Patrones Cross-Signal) · §80 fix USER_INC · §81 RE-ACTIVATION · Datos: §B1 + comms_monthly_summary Abr-2026 D30 · 30-Abr-2026
  </div>
</div>
"""

    return html



def build_pom_analysis_tab_html() -> str:
    """Genera el HTML completo de la pestaña KPIs POM.
    Usa las mismas clases CSS que build_oc_ucr_analysis_tab_html().
    Target: 250K NR/mes Ago-26 (minimo 240K).
    Fuente datos: context.md A3,A5,A12,A13,B1,B3,B5a.
    """
    css_embed = """
    <style id="css-analysis-pom">
      #pane-analisis-pom .analysis-header-banner {
        background: linear-gradient(135deg, #0d4b43 0%, #2F9E8F 100%);
      }
      #pane-analisis-pom .palancas-table th { background: #0d4b43; }
    </style>
    """

    # 1. HEADER
    html_header = (
        '<div class="analysis-header-banner">'
        '<div>'
        '<div class="analysis-header-title">KPIs Estrategicos POM — Diagnostico, Riesgos y Camino al Target</div>'
        '<div style="font-size:12px;opacity:0.7;margin-top:4px;">Medios Pagados · Mercado Pago Mexico · Target: ~250K NR/mes Ago-26</div>'
        '</div>'
        '<div style="text-align:right;flex-shrink:0;margin-left:20px;">'
        '<div class="analysis-header-badge">Basado en datos reales Ene 25 - Mar 26</div>'
        '<div style="font-size:10px;opacity:0.6;margin-top:6px;">Ultimo dato: Marzo 2026 · 2025 cerrado · 2026 actualiza mensualmente</div>'
        '</div></div>'
    )

    # 2. FASES
    phases_html = ""
    for bg, nombre, nr, sub, desc in [
        (FASE_POM_H1_2025_COLOR_BG, FASE_POM_H1_2025_NOMBRE, FASE_POM_H1_2025_NR,
         FASE_POM_H1_2025_SUBTITULO, FASE_POM_H1_2025_DESCRIPCION),
        (FASE_POM_H2_2025_COLOR_BG, FASE_POM_H2_2025_NOMBRE, FASE_POM_H2_2025_NR,
         FASE_POM_H2_2025_SUBTITULO, FASE_POM_H2_2025_DESCRIPCION),
        (FASE_POM_Q1_2026_COLOR_BG, FASE_POM_Q1_2026_NOMBRE, FASE_POM_Q1_2026_NR,
         FASE_POM_Q1_2026_SUBTITULO, FASE_POM_Q1_2026_DESCRIPCION),
        (FASE_POM_TARGET_COLOR_BG,  FASE_POM_TARGET_NOMBRE,  FASE_POM_TARGET_NR,
         FASE_POM_TARGET_SUBTITULO,  FASE_POM_TARGET_DESCRIPCION),
    ]:
        phases_html += (
            f'<div class="phase-card" style="background:{bg};">'
            f'<div class="phase-card-label">{nombre}</div>'
            f'<div class="phase-card-nr">{nr}</div>'
            f'<div class="phase-card-subtitle">{sub}</div>'
            f'<div class="phase-card-desc">{desc}</div></div>'
        )
    html_phases = f'<div class="phases-grid">{phases_html}</div>'

    # 3. NARRATIVA
    def make_narrative(title_color, border_color, icon, title, items):
        html = f'<div class="narrative-card">'
        html += (f'<div class="narrative-card-title" style="color:{title_color};'
                 f'border-bottom-color:{border_color};">{icon} {title}</div>')
        for t, d in items:
            html += (f'<div class="narrative-item">'
                     f'<div class="narrative-item-title">• {t}</div>'
                     f'<div>{d}</div></div>')
        html += '</div>'
        return html

    html_drivers = make_narrative('#188038', '#2F9E8F', '', 'Que impulso el crecimiento H2-25 a Q1-26', DRIVERS_POM_CRECIMIENTO)
    html_tensiones = make_narrative('#e37400', '#f9ab00', '', 'Tensiones y riesgos activos en Q1-26', CAUSAS_TENSION_POM_Q1_2026)
    html_narrative = f'<div class="two-col-grid">{html_drivers}{html_tensiones}</div>'

    # 4. ACCIONES
    def make_actions(title_color, border_color, icon, title, items):
        html = f'<div class="action-card">'
        html += (f'<div class="action-card-title" style="color:{title_color};'
                 f'border-bottom-color:{border_color};">{icon} {title}</div>')
        for badge_tipo, badge_color, nombre, desc in items:
            html += (f'<div class="action-item">'
                     f'<span class="action-item-badge" style="background:{badge_color};">{badge_tipo}</span>'
                     f'<div class="action-item-content"><strong>{nombre}:</strong> {desc}</div></div>')
        html += '</div>'
        return html

    html_escalar = make_actions('#188038', '#2F9E8F', '', 'Que escalar sin miedo', INICIATIVAS_ESCALAR_POM)
    html_parar   = make_actions('#d93025', '#ea4335', '', 'Que parar o pivotar', INICIATIVAS_PARAR_PIVOTAR_POM)
    html_actions = f'<div class="two-col-grid">{html_escalar}{html_parar}</div>'

    # 5. CAMINO CRITICO
    months_html = ""
    for mes, nr, lever in POM_CRITICO_MESES_DATOS:
        months_html += (
            f'<div class="cp-month-card">'
            f'<div class="cp-month-label">{mes}</div>'
            f'<div class="cp-month-nr">{nr}</div>'
            f'<div class="cp-month-lever">{lever}</div></div>'
        )
    html_critical_path = (
        '<div class="critical-path-container">'
        f'<div class="critical-path-header">'
        f'<div class="critical-path-title">Camino al Target: {POM_CRITICO_DESDE} — {POM_CRITICO_HASTA}</div>'
        f'<div class="critical-path-meta">{POM_CRITICO_PERIODO} · {POM_CRITICO_CRECIMIENTO}</div>'
        f'</div>'
        f'<div style="font-size:11px;color:rgba(255,255,255,0.6);margin-bottom:12px;">{POM_CRITICO_DESCRIPCION}</div>'
        f'<div class="critical-path-months">{months_html}</div>'
        f'<div class="critical-path-hypothesis"><strong style="color:#7dd3c0;">Hipotesis:</strong> {POM_CRITICO_HIPOTESIS}</div>'
        f'<div class="critical-path-risk"><strong>Riesgo principal:</strong> {POM_CRITICO_RIESGO_PRINCIPAL}</div>'
        '</div>'
    )

    # 6. PRINCIPIOS
    p_html = ""
    for titulo, cuerpo in PRINCIPIOS_POM:
        p_html += (f'<div class="principle-card">'
                   f'<div class="principle-title">{titulo}</div>'
                   f'<div class="principle-body">{cuerpo}</div></div>')
    html_principles_section = (
        '<div style="margin-bottom:20px;">'
        '<div style="font-size:15px;font-weight:700;color:#1a2744;margin-bottom:12px;'
        'padding-bottom:8px;border-bottom:2px solid #e8eaf0;">'
        'Principios de las mejores operaciones POM de escala global'
        '<div style="font-size:11px;color:#666;font-weight:400;margin-top:2px;">Aplicados a POM MLM</div>'
        '</div>'
        f'<div class="principles-grid">{p_html}</div>'
        f'<div class="brecha-box"><strong>Brecha y oportunidad:</strong> {PRINCIPIOS_POM_BRECHA}</div>'
        '</div>'
    )

    # 7. PLAN
    rows_html = ""
    for p in PALANCAS_PLAN_POM:
        rows_html += (
            f'<tr>'
            f'<td style="text-align:center;"><span class="palanca-num" style="background:{p["color"]};">{p["numero"]}</span></td>'
            f'<td><strong>{p["nombre"]}</strong></td>'
            f'<td class="palanca-desc">{p["descripcion"]}</td>'
            f'<td style="white-space:nowrap;">{p["eta"]}</td>'
            f'<td><span class="nr-impacto-badge">{p["nr_impacto"]}</span></td>'
            f'<td><span class="blocker-text">&#9679; {p["blocker"]}</span></td>'
            f'</tr>'
        )
    t0 = PALANCA_TRACK_0_POM
    rows_html += (
        '<tr class="track-0-row">'
        f'<td style="text-align:center;"><span class="palanca-num track-0">0</span></td>'
        f'<td><strong style="color:#c77700;">{t0["nombre"]}</strong>'
        ' <span style="background:#f9ab00;color:#333;padding:1px 6px;border-radius:4px;font-size:9.5px;font-weight:700;">TRACK 0</span></td>'
        f'<td class="palanca-desc">{t0["descripcion"]}</td>'
        f'<td style="white-space:nowrap;color:#c77700;font-weight:700;">{t0["eta"]}</td>'
        f'<td><span class="nr-impacto-badge track-0">{t0["nr_impacto"]}</span></td>'
        f'<td><span class="blocker-text">&#9679; {t0["blocker"]}</span></td>'
        '</tr>'
    )
    qw_items = "".join(
        f'<div class="quick-win-item"><span class="qw-bullet">&#8594;</span>'
        f'<div><strong>{qw[0]}</strong><span class="qw-impact"> {qw[1]}</span></div></div>'
        for qw in POM_QUICK_WINS
    )
    est_items = "".join(
        f'<div style="font-size:11.5px;margin-bottom:6px;color:#333;">'
        f'&#8594; <strong>{e[0]}</strong>: <span style="color:#555;">{e[1]}</span></div>'
        for e in POM_ESTRUCTURALES_H2_2026
    )
    html_plan_section = (
        '<div class="palancas-section">'
        '<div style="font-size:14px;font-weight:700;color:#1a2744;margin-bottom:4px;">Plan POM — Palancas hacia ~250K NR/mes</div>'
        '<div style="font-size:11px;color:#888;margin-bottom:16px;">Target Ago-26: ~250K · minimo 240K · Fuente: Context B1,B3,B5a,A5</div>'
        '<div style="overflow-x:auto;"><table class="palancas-table">'
        '<thead><tr><th>#</th><th>Palanca</th><th>Descripcion</th><th>ETA</th><th>NR Impact</th><th>Blocker</th></tr></thead>'
        f'<tbody>{rows_html}</tbody></table></div>'
        '<div class="quick-wins-grid">'
        f'<div class="quick-wins-box"><div class="quick-wins-box-title">Quick Wins — proximas 4 semanas</div>{qw_items}'
        f'<div class="objetivo-realista" style="margin-top:10px;">{POM_QUICK_WINS_TOTAL}</div></div>'
        f'<div class="estructurales-box"><div class="estructurales-box-title">Para H2 2026 (palancas estructurales)</div>{est_items}'
        f'<div class="objetivo-realista" style="margin-top:10px;">{POM_OBJETIVO_REALISTA}</div></div>'
        '</div></div>'
    )

    # ── 8. ESTACIONALIDAD POM ─────────────────────────────────────────────────
    IS_C = {"alto":("#0d5c2f","#fff"), "medio":("#1e7e3e","#fff"),
            "bajo":("#f9ab00","#1a2744"), "critico":("#d93025","#fff")}
    IS_L = {"alto":"ALTO", "medio":"ESTABLE", "bajo":"BAJO", "critico":"CRÍTICO"}

    # IS Heatmap 12 meses
    pom_meses_html = ""
    for mes, is_val, nivel, evento, accion in POM_IS_MENSUAL:
        bg, fg = IS_C[nivel]
        pom_meses_html += (
            f'<div style="background:#fff;border-radius:8px;border:1px solid #e8eaf0;padding:10px 12px;">'
            f'<div style="font-size:10px;font-weight:700;color:#888;text-transform:uppercase;'
            f'letter-spacing:.5px;margin-bottom:4px;">{mes[:3].upper()}</div>'
            f'<div style="font-size:20px;font-weight:800;color:#1a2744;line-height:1;">{is_val}</div>'
            f'<div style="margin:4px 0;"><span style="background:{bg};color:{fg};font-size:9px;'
            f'font-weight:700;padding:2px 6px;border-radius:10px;">{IS_L[nivel]}</span></div>'
            f'<div style="font-size:10px;color:#555;line-height:1.3;">{evento}</div>'
            f'</div>'
        )

    # Key insights
    pom_insights_html = ""
    for i, (titulo, desc) in enumerate(POM_ESTACIONALIDAD_INSIGHTS, 1):
        pom_insights_html += (
            f'<div style="background:#fff;border-radius:8px;border:1px solid #e8eaf0;'
            f'padding:14px 16px;border-left:4px solid #2F9E8F;">'
            f'<div style="font-size:12.5px;font-weight:700;color:#1a2744;margin-bottom:6px;">'
            f'{i}. {titulo}</div>'
            f'<div style="font-size:11.5px;color:#444;line-height:1.6;">{desc}</div>'
            f'</div>'
        )

    # Campañas
    pom_campanas_html = ""
    for nombre, periodo, impacto, accion, color in POM_CAMPANAS_IMPACTO:
        pom_campanas_html += (
            f'<tr style="border-bottom:1px solid #f0f0f0;">'
            f'<td style="padding:8px 12px;"><span style="background:{color};color:#fff;'
            f'padding:2px 10px;border-radius:4px;font-size:11px;font-weight:700;">{nombre}</span></td>'
            f'<td style="padding:8px 12px;font-size:11.5px;color:#555;">{periodo}</td>'
            f'<td style="padding:8px 12px;font-size:11.5px;color:#333;font-weight:500;">{impacto}</td>'
            f'<td style="padding:8px 12px;font-size:11px;color:#0d5c2f;font-weight:600;">{accion}</td>'
            f'</tr>'
        )

    # Próximos 3 meses
    pom_proximos_html = ""
    for mes, is_badge, evento, accion, riesgo in POM_PROXIMOS_3_MESES:
        pom_proximos_html += (
            f'<div style="background:#fff;border-radius:8px;border:1px solid #e8eaf0;padding:14px 16px;">'
            f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">'
            f'<div style="font-size:13px;font-weight:700;color:#1a2744;">{mes}</div>'
            f'<div style="font-size:12px;font-weight:700;color:#888;">IS {is_badge}</div>'
            f'<div style="font-size:11px;color:#888;font-style:italic;">{evento}</div></div>'
            f'<div style="font-size:11.5px;color:#0d5c2f;font-weight:600;margin-bottom:4px;">'
            f'&#8594; {accion}</div>'
            f'<div style="font-size:10.5px;color:#c77700;margin-top:4px;">'
            f'&#9888; {riesgo}</div>'
            f'</div>'
        )

    # Patrón semanal POM
    IS_SC = {"alto":("#0d5c2f","#fff"), "medio":("#1e7e3e","#fff"),
             "bajo":("#f9ab00","#1a2744"), "critico":("#d93025","#fff")}
    pom_semanas_html = ""
    for sem, dias, is_r, driver, impl, nivel in POM_PATRONES_SEMANA:
        bg, fg = IS_SC[nivel]
        pom_semanas_html += (
            f'<div style="background:#fff;border-radius:8px;border:1px solid #e8eaf0;padding:12px 14px;">'
            f'<div style="font-size:11px;font-weight:700;color:#1a2744;margin-bottom:2px;">{sem}</div>'
            f'<div style="font-size:10px;color:#888;margin-bottom:6px;">{dias}</div>'
            f'<div style="margin-bottom:6px;"><span style="background:{bg};color:{fg};font-size:10px;'
            f'font-weight:700;padding:2px 8px;border-radius:10px;">{is_r}</span></div>'
            f'<div style="font-size:10.5px;color:#444;margin-bottom:5px;line-height:1.4;">{driver}</div>'
            f'<div style="font-size:10px;color:#0d5c2f;font-weight:600;line-height:1.3;">{impl}</div>'
            f'</div>'
        )

    # DoW POM
    DOW_BG  = {"optimo":"#e6f4ea","bueno":"#f0f8f2","regular":"#fff9e6","evitar":"#fce8e6"}
    DOW_COL = {"optimo":"#0d5c2f","bueno":"#188038","regular":"#c77700","evitar":"#d93025"}
    pom_dow_html = ""
    for dia, desc_paid, desc_reach, n_paid, n_reach in POM_DOW_PATTERNS:
        pom_dow_html += (
            f'<tr style="border-bottom:1px solid #f0f0f0;">'
            f'<td style="padding:7px 12px;font-weight:700;color:#1a2744;font-size:11px;">{dia}</td>'
            f'<td style="padding:7px 12px;background:{DOW_BG[n_paid]};">'
            f'<span style="color:{DOW_COL[n_paid]};font-size:11px;">{desc_paid}</span></td>'
            f'<td style="padding:7px 12px;background:{DOW_BG[n_reach]};">'
            f'<span style="color:{DOW_COL[n_reach]};font-size:11px;">{desc_reach}</span></td>'
            f'</tr>'
        )

    # Sub-canal / Medio POM
    pom_subcanal_html = ""
    for i, (medio, patron, mejor_sem, mejor_dow, evento, regla, fuente) in enumerate(POM_SUBCANAL_MEDIO_SEASONAL):
        bg_row = "#f8f9ff" if i % 2 == 0 else "#fff"
        pom_subcanal_html += (
            f'<tr style="background:{bg_row};border-bottom:1px solid #f0f0f0;">'
            f'<td style="padding:8px 12px;font-weight:700;color:#1a2744;font-size:11px;'
            f'border-left:3px solid #2F9E8F;">{medio}'
            f'<br><span style="font-size:9px;color:#888;font-weight:400;">{fuente}</span></td>'
            f'<td style="padding:8px 12px;font-size:10.5px;color:#333;line-height:1.4;">{patron}</td>'
            f'<td style="padding:8px 12px;font-size:10.5px;font-weight:600;color:#1e7e3e;">{mejor_sem}</td>'
            f'<td style="padding:8px 12px;font-size:10.5px;font-weight:600;color:#1a73e8;">{mejor_dow}</td>'
            f'<td style="padding:8px 12px;font-size:10.5px;color:#555;line-height:1.4;">{evento}</td>'
            f'<td style="padding:8px 12px;font-size:10.5px;color:#1a2744;font-weight:500;line-height:1.4;">{regla}</td>'
            f'</tr>'
        )

    html_estacionalidad_pom = (
        '<div style="margin-bottom:20px;">'
        '<div style="font-size:15px;font-weight:700;color:#1a2744;margin-bottom:4px;'
        'padding-bottom:8px;border-bottom:2px solid #e8eaf0;">'
        '&#128197; Estacionalidad POM &#8212; CPM, Campañas y Calendario de Decisiones'
        '<div style="font-size:11px;color:#666;font-weight:400;margin-top:2px;">'
        'IS mensual 2025 (§A3 histórico) · Foco: POM es el canal MÁS sensible al CPM estacional'
        '</div></div>'

        # IS heatmap
        '<div style="font-size:11px;font-weight:700;color:#888;text-transform:uppercase;'
        'letter-spacing:.5px;margin-bottom:8px;">ÍNDICE DE ESTACIONALIDAD MENSUAL POM'
        '<span style="font-weight:400;font-style:italic;text-transform:none;letter-spacing:0;">'
        ' · IS = NR_mes / NR_prom_anual · Promedio POM 2025 ≈ 85K NR/mes (§A3)</span></div>'
        f'<div style="display:grid;grid-template-columns:repeat(6,1fr);gap:8px;margin-bottom:8px;">{pom_meses_html}</div>'
        '<div style="display:flex;gap:16px;margin-bottom:16px;font-size:10.5px;color:#888;">'
        '<span><span style="background:#0d5c2f;color:#fff;padding:1px 6px;border-radius:3px;">ALTO</span> IS &#8805; 1.10</span>'
        '<span><span style="background:#1e7e3e;color:#fff;padding:1px 6px;border-radius:3px;">ESTABLE</span> IS 0.95&#8211;1.09</span>'
        '<span><span style="background:#f9ab00;color:#1a2744;padding:1px 6px;border-radius:3px;">BAJO</span> IS 0.85&#8211;0.94</span>'
        '<span><span style="background:#d93025;color:#fff;padding:1px 6px;border-radius:3px;">CRÍTICO</span> IS &lt; 0.85</span>'
        '</div>'

        # Insights
        '<div style="font-size:11px;font-weight:700;color:#888;text-transform:uppercase;'
        'letter-spacing:.5px;margin-bottom:8px;">3 INSIGHTS CLAVE DE ESTACIONALIDAD POM</div>'
        f'<div style="display:grid;grid-template-columns:1fr;gap:8px;margin-bottom:16px;">{pom_insights_html}</div>'

        # Campañas
        '<div style="font-size:11px;font-weight:700;color:#888;text-transform:uppercase;'
        'letter-spacing:.5px;margin-bottom:8px;">CAMPAÑAS + IMPACTO CUANTIFICADO EN POM</div>'
        '<div style="overflow-x:auto;margin-bottom:16px;">'
        '<table style="width:100%;border-collapse:collapse;font-size:12px;background:#fff;border-radius:8px;overflow:hidden;">'
        '<thead><tr style="background:#f0f3f8;">'
        '<th style="padding:8px 12px;text-align:left;font-size:10.5px;color:#7a8499;font-weight:600;">CAMPAÑA</th>'
        '<th style="padding:8px 12px;text-align:left;font-size:10.5px;color:#7a8499;font-weight:600;">PERÍODO</th>'
        '<th style="padding:8px 12px;text-align:left;font-size:10.5px;color:#7a8499;font-weight:600;">IMPACTO EN POM</th>'
        '<th style="padding:8px 12px;text-align:left;font-size:10.5px;color:#7a8499;font-weight:600;">ACCIÓN VALIDADA</th>'
        '</tr></thead>'
        f'<tbody>{pom_campanas_html}</tbody></table></div>'

        # Próximos 3 meses
        '<div style="font-size:11px;font-weight:700;color:#888;text-transform:uppercase;'
        'letter-spacing:.5px;margin-bottom:8px;">CALENDARIO DE DECISIONES — PRÓXIMOS 3 MESES</div>'
        f'<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-bottom:20px;">{pom_proximos_html}</div>'

        # Patrón semanal
        '<div style="font-size:11px;font-weight:700;color:#888;text-transform:uppercase;'
        'letter-spacing:.5px;margin:16px 0 8px;">PATRÓN SEMANAL DENTRO DEL MES</div>'
        '<div style="font-size:10.5px;color:#888;margin-bottom:10px;font-style:italic;">'
        'POM es menos sensible a quincenas que OC/CRM — el CPM no varía por payday. '
        'El efecto quincena en POM es moderado (IS_semanal ≈ 1.05-1.10 vs 1.20-1.30 en OC).</div>'
        f'<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:16px;">{pom_semanas_html}</div>'

        # DoW
        '<div style="font-size:11px;font-weight:700;color:#888;text-transform:uppercase;'
        'letter-spacing:.5px;margin-bottom:8px;">PATRÓN DÍA DE LA SEMANA — CONVERSIÓN vs REACH</div>'
        '<div style="font-size:10.5px;color:#888;margin-bottom:8px;font-style:italic;">'
        '[inf] = inferencia. Clave POM: mayor REACH en Sáb-Dom (TikTok/Meta) ≠ mayor CONVERSIÓN de tarjeta MP.</div>'
        '<div style="overflow-x:auto;margin-bottom:16px;">'
        '<table style="width:100%;border-collapse:collapse;font-size:11.5px;background:#fff;border-radius:8px;">'
        '<thead><tr style="background:#f0f3f8;">'
        '<th style="padding:8px 12px;text-align:left;font-size:10px;color:#7a8499;font-weight:600;">DÍA</th>'
        '<th style="padding:8px 12px;text-align:left;font-size:10px;color:#2F9E8F;font-weight:600;">CONVERSIÓN (Google·DV360·intent)</th>'
        '<th style="padding:8px 12px;text-align:left;font-size:10px;color:#5899D1;font-weight:600;">REACH (TikTok·Meta·social)</th>'
        '</tr></thead>'
        f'<tbody>{pom_dow_html}</tbody></table></div>'

        # Sub-canal
        '<div style="font-size:11px;font-weight:700;color:#888;text-transform:uppercase;'
        'letter-spacing:.5px;margin-bottom:8px;">ESTACIONALIDAD POR SUB-CANAL POM</div>'
        '<div style="overflow-x:auto;">'
        '<table style="width:100%;border-collapse:collapse;font-size:11px;background:#fff;border-radius:8px;">'
        '<thead><tr style="background:#0d4b43;color:#fff;">'
        '<th style="padding:8px 12px;font-size:10px;font-weight:600;min-width:110px;">SUB-CANAL</th>'
        '<th style="padding:8px 12px;font-size:10px;font-weight:600;">PATRÓN MENSUAL</th>'
        '<th style="padding:8px 12px;font-size:10px;font-weight:600;min-width:90px;">MEJOR SEMANA</th>'
        '<th style="padding:8px 12px;font-size:10px;font-weight:600;min-width:80px;">MEJOR DoW</th>'
        '<th style="padding:8px 12px;font-size:10px;font-weight:600;">EVENTO CRÍTICO</th>'
        '<th style="padding:8px 12px;font-size:10px;font-weight:600;min-width:160px;">REGLA DE ORO</th>'
        '</tr></thead>'
        f'<tbody>{pom_subcanal_html}</tbody></table></div>'
        '</div>'
    )

    html_update_note = (
        '<div class="update-note">Datos al 14-Abr-2026 · 2025 cerrado y definitivo · '
        '2026 se actualiza mensualmente en <code>src/builders_analysis.py</code> '
        '+ <code>skills/analizar-Optimizar_Performance_KPIs_context.md</code></div>'
    )

    return (
        css_embed
        + '<div class="analysis-tab-container">'
        + html_header + html_phases + html_narrative + html_actions
        + html_critical_path + html_principles_section + html_plan_section
        + html_estacionalidad_pom + html_update_note + '</div>'
    )
