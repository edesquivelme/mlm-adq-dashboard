# config/queries/ — Documentación de Queries Fuente por Pestaña

## Propósito de este folder

Cada archivo `.md` aquí es el **manual técnico completo** de la query que alimenta
una pestaña del dashboard. Es la fuente de verdad técnica del pipeline de datos.

No confundir con:
- `docs/History.md` → historial de cambios y decisiones del proyecto
- `docs/metrics_logic.md` → definiciones de KPIs y fórmulas de negocio
- `config/channels_config.json` → jerarquía y mapeo de canales

## Cuándo leer estos archivos

- Antes de modificar cualquier query del dashboard
- Al incorporar un nuevo colaborador o agente IA al proyecto
- Cuando BQ da un error y necesitas entender la estructura de las tablas
- Al revisar si un campo nuevo de BQ aplica para alguna pestaña existente

## Convención de cada archivo

Cada `{tab_id}.md` contiene exactamente:

| Sección | Contenido |
|---|---|
| `## Propósito` | Qué pregunta de negocio responde esta pestaña |
| `## Tablas BQ` | Las 3 preguntas clave: tabla, dataset, proyecto, contenido |
| `## SQL Canónico` | La query lista para ejecutar en BQ UI (con fechas hardcodeadas de ejemplo) |
| `## Parámetros de fecha` | Cómo varía el SQL entre el cache y el fresh |
| `## Columnas de salida` | Qué retorna cada columna y de dónde viene |
| `## Estrategia de actualización` | Two-Tier cache, cron, script de refresh |
| `## Gotchas críticos` | Errores ya cometidos + cómo evitarlos |
| `## Historial` | Cambios en orden cronológico |

## Archivos actuales

| Archivo | Pestaña | Tipo de SQL | Estado |
|---|---|---|---|
| [comms_oc.md](comms_oc.md) | Comms_OC | Estático (hardcoded) | Activo — Abr 2026 |
| [nr_mensual.md](nr_mensual.md) | NR Mensual / NR Diario / MTD D7 | Dinámico (generado desde channels_config.json) | Activo — Abr 2026 |
| [performance_vista_corp.md](performance_vista_corp.md) | Performance_vista_Corp | Sin query BQ propia — ensamble Python de 5 dicts | Activo — Abr 2026 |

## Archivos pendientes

| Archivo | Pestaña | Query principal |
|---|---|---|
| `performance_fm.md` | Performance_vista_FM | `get_perf_paid_sql()` + `get_perf_vpu_sql()` + `get_perf_roa_costos_sql()` |
| `nr_corp.md` | Tabla Corp (NR Mensual + NR Diario) | `get_nr_corp_sql()` + `get_nr_corp_daily_sql()` |
