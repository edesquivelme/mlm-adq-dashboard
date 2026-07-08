# MLM_ADQ_Dash — Skills Directory
# ==============================================================================
# PROPÓSITO DE ESTA CARPETA:
#   Contiene todas las Skills (bots especializados) del proyecto de Analytics de
#   Adquisición de Mercado Pago México (MLM). Cada skill es un agente de análisis
#   con acceso a las fuentes de datos del proyecto y expertise especializado.
#
# CONVENCIÓN DE NOMBRES:
#   {canal_o_dominio}_{tipo_de_skill}_{version}.{extensión}
#   Ejemplos:
#     analizar-Optimizar_Performance_KPIs_skill.md          → Skill de análisis estratégico OC + POM
#     analizar-Optimizar_Performance_KPIs_context.md        → Base de conocimiento del skill OC + POM
#     bq_daily_adq_skill.py             → Skill Python para consultas BigQuery diarias
#
# CONVENCIÓN DE COMENTARIOS:
#   Cada archivo de skill comienza con un bloque de metadatos que describe:
#   - Propósito exacto del skill
#   - Canales/dominios cubiertos
#   - Archivos fuente de datos que consume
#   - Modos de invocación disponibles
#   - Última actualización y autor
#
# POLÍTICA DE DATOS TEMPORALES:
#   - Datos 2025: CERRADOS. El año 2025 está completo. No se actualizarán.
#     Fuente: docs/Weekly Adquisición MLM_2025_versionClaud.md
#   - Datos 2026: ABIERTOS. Se actualizan mensualmente.
#     Último cierre disponible: MARZO 2026 (al 13-Abr-2026)
#     Fuentes: docs/2026_MLM_ACQWeekly_AOMar2026_versionClau.md
#              docs/2026_MLM_Monthly_ACQ_AOMarch26_versionClaud.md
#   Cuando llegue el PDF de Abril 2026 → repetir extracción PyMuPDF y
#   actualizar las fuentes BI + el contexto del skill correspondiente.
#
# CÓMO INVOCAR LOS SKILLS (Claude Code):
#   Todos los skills se invocan desde Claude Code con el prefijo /project:
#   Ver .claude/commands/ para los entry points de cada skill.
#
# ==============================================================================

## CÓMO ACTUALIZAR CUANDO LLEGA NUEVO DATO 2026
# ==============================================================================
# PROTOCOLO DE ACTUALIZACIÓN MENSUAL (aprox. 15 minutos de trabajo):
#
# PASO 1 — Extraer el nuevo PDF:
#   cd C:\Users\sergibarra\Documents\SI_Meli_code1
#   python -c "
#   import fitz
#   doc = fitz.open('MLM_ADQ_Dash/docs/NUEVO_ARCHIVO.pdf')
#   with open('MLM_ADQ_Dash/docs/_nuevo_raw.txt', 'w', encoding='utf-8') as f:
#       for i, page in enumerate(doc):
#           f.write(f'\n===== PAGINA {i+1} =====\n')
#           f.write(page.get_text('text'))
#   print('Done.')
#   "
#
# PASO 2 — Actualizar el contexto del skill (4 operaciones APPEND-ONLY):
#   Abrir: skills/analizar-Optimizar_Performance_KPIs_context.md
#   2a. Agregar fila en §B1 (Performance Mensual 2026)
#   2b. Agregar filas en §B2 (Weekly Cuts 2026)
#   2c. Reemplazar §B3 (Estado Actual) con el nuevo mes
#   2d. Agregar bloque en §B4 (Sesiones Semanales 2026)
#   2e. Actualizar §C3 (Riesgos) si hay cambios
#
# PASO 3 — Crear el nuevo BI markdown (extracción detallada):
#   Seguir el mismo proceso que se usó para los archivos en docs/:
#   - docs/2026_MLM_ACQWeekly_AOMar2026_versionClau.md (referencia de formato)
#   - El nuevo archivo: docs/2026_MLM_ACQWeekly_AOAbr2026_versionClau.md (ejemplo)
#
# PASO 4 — Actualizar documentación:
#   - docs/History.md: agregar entrada en la tabla de sesiones
#   - CLAUDE.md: actualizar referencia al último dato disponible
#
# LO QUE NUNCA DEBES CAMBIAR:
#   - Sección A del contexto (datos 2025 cerrados)
#   - La lógica del skill (analizar-Optimizar_Performance_KPIs_skill.md)
#   - El entry point (.claude/commands/analizar-oc-pom.md)
# ==============================================================================

## Skills disponibles

| Skill | Entry Point | Archivo principal | Contexto de datos | Canales |
|---|---|---|---|---|
| **Analizador OC+POM** | `/project:analizar-oc-pom` | `analizar-Optimizar_Performance_KPIs_skill.md` | `analizar-Optimizar_Performance_KPIs_context.md` | OC+Ucrania, POM |
| **BQ Daily ADQ** | `bq_daily_adq_skill.py` | `bq_daily_adq_skill.py` | BigQuery directo | All channels |

## Arquitectura de un skill

```
[Usuario invoca /project:analizar-oc-pom en Claude Code]
          ↓
[.claude/commands/analizar-oc-pom.md]     ← Entry point thin wrapper
  Lee →  [skills/analizar-Optimizar_Performance_KPIs_skill.md]  ← Instrucciones completas del skill
  Lee →  [skills/analizar-Optimizar_Performance_KPIs_context.md] ← Base de conocimiento pre-compilada
  Lee →  [docs/*.md]                          ← Fuentes BI según sea necesario
          ↓
[Claude aplica 20+ años de expertise analítico sobre los datos]
          ↓
[Output: Análisis nivel Bain — fases, drivers, ESCALAR/PARAR, camino crítico, palancas]
```

## Eficiencia de tokens por diseño

| Enfoque | Tokens por invocación | Cobertura |
|---|---|---|
| Leer los 4 PDFs fuente completos | ~80.000 tokens | 100% |
| **Skill con contexto pre-compilado** | **~12.000 tokens** | **95%** |
| Solo contexto pre-compilado | ~8.000 tokens | 80% |

## Roadmap de skills futuros

- [ ] `analizar_mgm_skill.md` — Análisis MGM (referidos)
- [ ] `analizar_lp_partners_skill.md` — Análisis LP & Partners
- [ ] `analizar_organico_skill.md` — Análisis ORG
- [ ] `generar_reporte_ejecutivo_skill.md` — Reporte ejecutivo multi-canal
- [ ] `forecaster_nr_skill.md` — Forecaster de N+R con escenarios
