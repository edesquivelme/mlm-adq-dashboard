# /project:analizar-oc-pom — Entry Point del Skill Analizador de Performance MLM
#
# PROPÓSITO DE ESTE ARCHIVO:
#   Entry point en la raíz del repo (requerido por Claude Code para /project:).
#   Todo el cerebro analítico vive en MLM_ADQ_Dash/skills/.
#
# INVOCACIÓN — CANALES INDIVIDUALES:
#   /project:analizar-oc-pom oc           → deep dive OC+Ucrania
#   /project:analizar-oc-pom pom          → deep dive POM
#   /project:analizar-oc-pom mgm          → deep dive MGM
#   /project:analizar-oc-pom others       → deep dive L&P / Others / Partners
#   /project:analizar-oc-pom org          → análisis Orgánico
#
# INVOCACIÓN — VISTAS AGREGADAS:
#   /project:analizar-oc-pom              → análisis estratégico OC+UCR + POM (default)
#   /project:analizar-oc-pom total        → cross-canal: los 4 canales + mix + eficiencia
#   /project:analizar-oc-pom ejecutivo    → síntesis para C-Suite (90 seg, todos los canales)
#   /project:analizar-oc-pom camino-critico → critical path OC+UCR al target 286K
#
# INVOCACIÓN — ANÁLISIS ESPECÍFICOS:
#   /project:analizar-oc-pom mejores      → ranking subcanales top + qué replicar
#   /project:analizar-oc-pom peores       → ranking subcanales bottom + qué matar
#   /project:analizar-oc-pom replicar     → síntesis de qué escalar con evidencia
#   /project:analizar-oc-pom parar        → síntesis de qué matar/pivotar
#   /project:analizar-oc-pom subcanales   → ranking todos los subcanales 4 canales
#   /project:analizar-oc-pom [pregunta]   → responde pregunta específica

Lee el archivo `MLM_ADQ_Dash/skills/analizar-Optimizar_Performance_KPIs_skill.md` completo
y aplica exactamente sus instrucciones para generar el análisis solicitado.

El argumento del usuario es: $ARGUMENTS
