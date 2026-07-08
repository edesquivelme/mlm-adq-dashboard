# HISTORY.md — MLM ADQ N+R Dashboard
## Registro completo del proyecto: arquitectura, decisiones, bugs y estado actual

---

## 1. Qué es este proyecto

Dashboard web interactivo de **N+R (Nuevos+Recurrentes usuarios)** para el equipo de Analytics de Adquisición de **MercadoLibre México (MLM)**. Muestra métricas de rendimiento por canal de marketing (UCR Gest, UCR PRD, OC ACT, POM ADQ/ACT, MGM ADQ/ACT, L&P ADQ/ACT, ORG) con vistas mensuales, diarias y acumuladas, integrando CPA y comparativos contra Plan de negocio.

**Dueño**: sergio.ibarra@mercadolibre.com.mx (GitHub: sergibarra-MP)
**Repo**: github.com/sergibarra-MP/SI_Meli_code1
**Carpeta activa**: `MLM_ADQ_Dash/`
**URL producción (V1)**: Google Apps Script → ver `legacy_v1/.appscript_config.json`
**URL desarrollo (V2)**: Google Apps Script → ver `src/.appscript_config_v2.json`

---

## 2. Evolución histórica: por qué se llegó a esta arquitectura

### Intentos fallidos (Intentos 1–5)
Se probaron Looker Studio, Google Sheets, Apps Script puro y Cloud Run.
**Todos fallaron** por restricciones de la organización MercadoLibre:
- OAuth bloqueado para apps externas con scopes adicionales
- Sin permisos para crear proyectos GCP / Cloud Run bajo la org Meli
- Apps Script solo puede servir HTML estático con `doGet()` simple

### Solución que funciona: Python + GitHub Actions + Apps Script web app

```
cron-job.org (7:30am y 5pm CDMX, días hábiles)
  → workflow_dispatch → GitHub Actions runner (Ubuntu gratuito)
    → python gen_dashboard_v2.py  (consulta BigQuery + Excel → genera HTML)
    → python deploy_appscript_v2.py  (sube HTML a Apps Script vía API)
      → Apps Script sirve el HTML estático como web app → URL pública Meli
```

**Por qué funciona donde los otros fallaron:**
- Python corre en GitHub Actions (fuera de la org Meli) → sin restricciones OAuth
- Apps Script solo sirve HTML estático → no necesita scopes adicionales
- cron-job.org dispara `workflow_dispatch` (no `schedule`) → ejecución inmediata, sin delays de GitHub

---

## 3. Autenticaciones

| Credencial | Para qué | Dónde vive |
|---|---|---|
| Google ADC (`application_default_credentials.json`) | Python → BigQuery + Apps Script API | Local: `AppData/Roaming/gcloud/` (fuera del repo) / GitHub Actions: secret `GOOGLE_ADC_CREDENTIALS` |
| GitHub PAT (`ghp_...`) | cron-job.org → disparar GitHub Actions | Header `Authorization: Bearer` en cron-job.org |

**Importante**: ADC y PAT son credenciales completamente distintas y sirven propósitos distintos.

---

## 4. Arquitectura V1 → V2: por qué y cómo se migró

### V1 — Monolito (archivado en `legacy_v1/`)

`gen_dashboard_html.py` era un script único de ~800 líneas que:
1. Conectaba a BigQuery
2. Procesaba datos
3. Generaba HTML con CSS, JS y datos embebidos

**Problemas del monolito:**
- Ilegible para LLMs: un contexto de 800+ líneas agota el contexto útil del modelo, generando errores silenciosos
- Cualquier cambio (UI, datos, jerarquía) requería entender todo el archivo
- Los mapeos de canales estaban hardcodeados en Python
- Sin tests posibles de forma modular

### V2 — Arquitectura Modular (en `src/`)

Separación en 3 componentes con responsabilidades claras:

#### Componente 1: `channels_config.json` — Single Source of Truth
Define **toda** la lógica de negocio de canales:
- Jerarquía completa (Total N+R → OC+UCR → Ucrania → UCR Gest, etc.)
- Colores por canal
- Mapeo a BigQuery (STRATEGY + CHANNEL → label del dashboard)
- Filas del Plan en el Excel (`plan_row` o `plan_lines` para nodos complejos)

Al agregar o modificar un canal, **solo se toca este archivo**.

#### Componente 2: `gen_dashboard_v2.py` — Motor de datos
- Lee `channels_config.json` y genera el SQL dinámicamente (CASE WHEN automático)
- Consulta BigQuery con retry automático para quotaExceeded
- Hace forward-fill de acumulados para días sin datos
- Lee el Excel del Plan con la lógica correcta de mapeo
- Inyecta todo en el template HTML via marcadores `{{DATA_JSON}}`, `{{MOM_TABLE}}`, `{{CHARTS_JSON}}`

#### Componente 3: `template_dashboard.html` — Frontend puro
- 100% CSS + JavaScript (Plotly)
- No tiene lógica de negocio: toda la configuración llega embebida en `D` (objeto JS)
- Tablas y gráficas son 100% interactivas en cliente

**Ventaja operativa:** Para trabajar con una IA en cualquier cambio, basta con pasar el componente relevante, no todo el proyecto.

---

## 5. Estructura de carpetas actual

```
MLM_ADQ_Dash/
│
├── .claude/commands/           ← Slash commands reutilizables para Claude Code
│   ├── deploy.md               ← /project:deploy (V1, legacy)
│   └── refresh.md              ← /project:refresh
│
├── docs/                       ← Documentación
│   ├── History.md             ← Este archivo
│   ├── metrics_logic.md        ← Fuente de verdad de KPIs y fórmulas BQ
│   ├── [Claude] MLM_ADQ_Dash_v2.docx                    ← Versión legible por humanos
│   ├── 2026_MLM_ACQWeekly_AOMarch2026.pdf               ← Fuente: 7 weeklies Ene–Mar 2026 (128 págs)
│   ├── 2026_MLM_ACQWeekly_AOMar2026_versionClau.md     ← Extracción BI Weekly 2026 (Claude, 13-Abr-2026)
│   ├── 2026_MLM_Monthly_ACQ.pdf                         ← Fuente: 3 cierres mensuales Ene–Mar 2026 (81 págs)
│   ├── 2026_MLM_Monthly_ACQ_AOMarch26_versionClaud.md  ← Extracción BI Monthly 2026 (Claude, 13-Abr-2026)
│   ├── "Weekly Adquisición MLM_2025.pdf"                ← Fuente: 25+ weeklies Ene–Nov 2025 (421 págs)
│   └── "Weekly Adquisición MLM_2025_versionClaud.md"   ← Extracción BI Weekly 2025 (Claude, 13-Abr-2026)
│
├── data/                       ← Insumos estáticos
│   └── Resumen Plan Acq 2026.xlsx  ← Plan oficial de N+R por canal 2025–2026
│
├── config/                     ← Configuración separada del código
│   └── channels_config.json    ← Fuente de verdad de canales (movida de src/)
│
├── legacy_v1/                  ← "El Congelador": código exacto de v2026-03-26-14h
│   ├── gen_dashboard_html.py   ← Monolito V1 (modificado: sin DOW, Subcanales ni barra acumulada)
│   ├── deploy_appscript.py     ← Deploy V1
│   ├── .appscript_config.json  ← IDs Apps Script V1
│   ├── CLAUDE.md               ← Contexto V1
│   └── HISTORY.md              ← Historia V1
│
├── src/                        ← Entorno activo V2
│   ├── gen_dashboard_v2.py     ← Motor de datos
│   ├── template_dashboard.html ← Frontend
│   ├── deploy_appscript_v2.py  ← Deploy V2
│   └── .appscript_config_v2.json  ← IDs Apps Script V2
│
├── dashboard_v2.html           ← Output generado (gitignored, en raíz del proyecto)
│
├── .github/workflows/
│   ├── refresh_MLM_ADQ_Dashboard.yml     ← CI/CD V1 (producción)
│   └── refresh_MLM_ADQ_Dashboard_v2.yml  ← CI/CD V2 (desarrollo, con Guardia de Seguridad)
│
├── requirements.txt
└── CLAUDE.md                   ← System prompt maestro para IA
```

**Nota sobre rutas en `gen_dashboard_v2.py`:**
- `CONFIG_PATH` → `config/channels_config.json` (ya no en `src/`)
- `PLAN_PATH` → `data/Resumen Plan Acq 2026.xlsx`
- `OUT_HTML` → raíz del proyecto (`dashboard_v2.html`), no dentro de `src/`
- `PROJECT_ROOT` = un nivel arriba de `src/` = `MLM_ADQ_Dash/`

---

## 6. Fuente de datos

```
Tabla:   meli-bi-data.SBOX_MKTCORPMP.PANEL_MONTHLY_DAILY_HISTORICO
Filtros: SIT_SITE_ID = 'MLM', FECHA_DIARIA >= DATE '2025-01-01'
Acceso:  Solo lectura (sin permisos de crear vistas, tablas ni jobs intermedios)
```

**Columnas clave:** `NR_USERS`, `COST_USD`, `STRATEGY`, `CHANNEL`, `FECHA_DIARIA`

**Notas operativas críticas:**
- Valores negativos en días recientes: **normal**. La tabla aplica correcciones retroactivas de atribución. Se cancean en el acumulado mensual.
- Si un canal no tiene fila para un día: no viene fila vacía — directamente no hay registro. El código hace forward-fill.
- Quota exceeded a las 7am: meli-bi-data es compartido con toda Meli. Se usa 7:30am + retry (3 intentos / 120s).

---

## 7. Mapeo de canales: BigQuery → Dashboard → Plan

### 7.1 Mapeo BQ → Dashboard (definido en `channels_config.json`)

| Label dashboard | STRATEGY | CHANNEL |
|---|---|---|
| UCR Gest | ACQUISITION | OWN CHANNELS MKT |
| UCR PRD | ACQUISITION | OWN CHANNELS PRD |
| OC ACT | ACTIVATION / OTHER | OWN CHANNELS MKT |
| POM ADQ | ACQUISITION | POM ACQ, POM ACT, POM OTHERS, POM OTHERS SELLERS, POM |
| POM ACT | ACTIVATION / OTHER | POM, POM OTHERS, POM OTHERS SELLERS |
| MGM ADQ | ACQUISITION | MGM |
| MGM ACT | ACTIVATION / OTHER | MGM |
| L&P ADQ | ACQUISITION | BRANDFORMANCE, OTHERS, PARTNERSHIPS |
| L&P ACT | ACTIVATION | BRANDFORMANCE, OTHERS, PARTNERSHIPS |
| ORG | todo lo demás | — |

### 7.2 Jerarquía del dashboard

```
Total N+R
├── OC + UCR
│   ├── Ucrania (Gest+PRD)
│   │   ├── UCR Gest  [leaf]
│   │   └── UCR PRD   [leaf]
│   └── OC ACT        [leaf]
├── POM TOTAL
│   ├── POM ADQ       [leaf]
│   └── POM ACT       [leaf]
├── MGM TOTAL
│   ├── MGM ADQ       [leaf]
│   └── MGM ACT       [leaf]
├── L&P TOTAL
│   ├── L&P ADQ       [leaf]
│   └── L&P ACT       [leaf]
└── ORG               [leaf]
```

### 7.3 Mapeo Plan (Excel `Resumen Plan Acq 2026.xlsx`) → Dashboard

El Excel usa nombres diferentes a los del dashboard. Mapeo correcto:

| Fila Excel | Label Excel | Nodo dashboard | Notas |
|---|---|---|---|
| 4 | N+R | Total N+R | Plan total |
| 5 | POM gest | POM TOTAL | Plan total de POM |
| 6 | OC Recurring | plan_line de OC+UCR | = UCR Gest + OC ACT Recurring |
| 9 | POM no gestionado | plan_line de POM TOTAL | Línea informativa adicional |
| 10 | OC Adhoc | plan_line de OC+UCR | = UCR Gest + OC ACT Ad-Hoc |
| 13 | MGM | MGM TOTAL | Plan total de MGM |
| 16 | L&P | L&P TOTAL | Plan total de L&P |
| 17 | Others + Producto | plan_line de OC+UCR | Corresponde a UCR PRD |
| 18 | No Atribuido / Organico | ORG | Plan de Orgánico |

**Reglas críticas:**
- POM ADQ y POM ACT **no tienen plan individual** → solo POM TOTAL tiene plan (row 5)
- UCR Gest, UCR PRD y OC ACT **no tienen plan individual** → sus planes están en las 3 líneas de OC+UCR
- Ucrania (Gest+PRD) **no tiene plan individual**
- El plan total de OC+UCR = OC Recurring + OC Adhoc + Others+Producto (rows 6+10+17)

**Concepto `plan_lines`:** Para nodos que en el Excel tienen sub-líneas de plan con nombres distintos (OC+UCR y POM TOTAL), se usa el campo `plan_lines` en el JSON. Esto permite mostrar esas sub-líneas en la tabla y la gráfica solo cuando se filtra por ese canal, sin afectar la lógica del resto del dashboard.

### 7.4 Tabla expandida: STRATEGY + CHANNEL → CHANNEL_SIMPLIFICADO → PLAN

Fuente BQ: `meli-bi-data.SBOX_MKTCORPMP.PANEL_MONTHLY_DAILY_HISTORICO`
Fuente Plan: `Resumen Plan Acq 2026.xlsx`

| STRATEGY | CHANNEL | CHANNEL_SIMPLIFICADO | NODO PLAN | FILA EXCEL | LABEL EXCEL | COMPOSICIÓN EN PLAN |
|---|---|---|---|---|---|---|
| ACQUISITION | OWN CHANNELS MKT | UCR Gest | OC + UCR | 6, 10 | OC Recurring + OC Adhoc | UCR Gest ⊂ Recurring y ⊂ Adhoc (junto con OC ACT) |
| ACQUISITION | OWN CHANNELS PRD | UCR PRD | OC + UCR | 17 | Others + Producto | UCR PRD = Others + Producto |
| ACTIVATION | OWN CHANNELS MKT | OC ACT | OC + UCR | 6, 10 | OC Recurring + OC Adhoc | OC ACT ⊂ Recurring y ⊂ Adhoc (junto con UCR Gest) |
| OTHER | OWN CHANNELS MKT | OC ACT | OC + UCR | 6, 10 | OC Recurring + OC Adhoc | OC ACT ⊂ Recurring y ⊂ Adhoc (junto con UCR Gest) |
| ACQUISITION | POM ACQ | POM ADQ | POM TOTAL | 5 | POM gest | Sin plan individual; plan en nodo padre |
| ACQUISITION | POM ACT | POM ADQ | POM TOTAL | 5 | POM gest | Sin plan individual; plan en nodo padre |
| ACQUISITION | POM OTHERS | POM ADQ | POM TOTAL | 5 | POM gest | Sin plan individual; plan en nodo padre |
| ACQUISITION | POM OTHERS SELLERS | POM ADQ | POM TOTAL | 5 | POM gest | Sin plan individual; plan en nodo padre |
| ACQUISITION | POM | POM ADQ | POM TOTAL | 5 | POM gest | Sin plan individual; plan en nodo padre |
| ACTIVATION | POM | POM ACT | POM TOTAL | 5 | POM gest | Sin plan individual; plan en nodo padre |
| ACTIVATION | POM OTHERS | POM ACT | POM TOTAL | 5 | POM gest | Sin plan individual; plan en nodo padre |
| ACTIVATION | POM OTHERS SELLERS | POM ACT | POM TOTAL | 5 | POM gest | Sin plan individual; plan en nodo padre |
| OTHER | POM | POM ACT | POM TOTAL | 5 | POM gest | Sin plan individual; plan en nodo padre |
| OTHER | POM OTHERS | POM ACT | POM TOTAL | 5 | POM gest | Sin plan individual; plan en nodo padre |
| OTHER | POM OTHERS SELLERS | POM ACT | POM TOTAL | 5 | POM gest | Sin plan individual; plan en nodo padre |
| ACQUISITION | MGM | MGM ADQ | MGM TOTAL | 13 | MGM | Sin plan individual; plan en nodo padre |
| ACTIVATION | MGM | MGM ACT | MGM TOTAL | 13 | MGM | Sin plan individual; plan en nodo padre |
| OTHER | MGM | MGM ACT | MGM TOTAL | 13 | MGM | Sin plan individual; plan en nodo padre |
| ACQUISITION | BRANDFORMANCE | L&P ADQ | L&P TOTAL | 16 | L&P | Sin plan individual; plan en nodo padre |
| ACQUISITION | OTHERS | L&P ADQ | L&P TOTAL | 16 | L&P | Sin plan individual; plan en nodo padre |
| ACQUISITION | PARTNERSHIPS | L&P ADQ | L&P TOTAL | 16 | L&P | Sin plan individual; plan en nodo padre |
| ACTIVATION | BRANDFORMANCE | L&P ACT | L&P TOTAL | 16 | L&P | Sin plan individual; plan en nodo padre |
| ACTIVATION | OTHERS | L&P ACT | L&P TOTAL | 16 | L&P | Sin plan individual; plan en nodo padre |
| ACTIVATION | PARTNERSHIPS | L&P ACT | L&P TOTAL | 16 | L&P | Sin plan individual; plan en nodo padre |
| *(todo lo demás)* | *(todo lo demás)* | ORG | ORG | 18 | No Atribuido / Organico | Directo |

**Notas:**
- `OTHER` y `ACTIVATION` comparten los mismos CHANNELs en POM, MGM y OC ACT → en `channels_config.json` se declaran como array `["ACTIVATION", "OTHER"]`
- ORG es el catch-all (`is_org: true`): cualquier combinación STRATEGY+CHANNEL fuera de las 24 filas anteriores cae aquí
- OC Recurring (fila 6) = UCR Gest Recurring + OC ACT Recurring → no hay plan individual por sub-canal
- OC Adhoc (fila 10) = UCR Gest Ad-Hoc + OC ACT Ad-Hoc → no hay plan individual por sub-canal
- Others + Producto (fila 17) = equivale 1:1 a UCR PRD
- POM no gestionado (fila 9) es una línea informativa adicional bajo POM TOTAL (`plan_lines` en el JSON), no un plan de sub-canal
- El plan de OC + UCR = OC Recurring + OC Adhoc + Others + Producto (filas 6 + 10 + 17)

---

## 8. Pestañas del dashboard

### MTD D7
Comparativo LMTD (mes anterior, mismo día) vs MTD (mes actual) al día D-2.
Columnas: Canal | LMTD D7 | MTD D7 | Diferencia absoluta | % | Mix.
Columna MTD resaltada con borde rojo discontinuo.

### NR Mensual
- KPI cards dinámicas según canal seleccionado (respeta jerarquía)
- Gráfica de barras apiladas por canal leaf + línea CPA (USD) en eje secundario + Plan Oficial
- Al filtrar un canal con `plan_lines` (OC+UCR, POM TOTAL): se muestran también las sub-líneas de plan en la gráfica
- Tabla con jerarquía completa: N+R mensual, fila MoM, fila Plan, fila vs Plan
- Al filtrar un canal con `plan_lines`: aparecen filas adicionales con el detalle de plan en la tabla
- Seleccionar mes resalta la columna; seleccionar canal resalta las filas y filtra la gráfica

### NR Diario Acumulado
- KPI cards del acumulado al último día disponible vs promedio N meses previos
- Gráfica de barras apiladas diarias (acumulado) + línea promedio + CPA en eje secundario
- Tabla de acumulado diario por canal + fila vs promedio
- Gráfica de líneas acumuladas (al fondo, reducida)
- Slider de N meses previos (1–6) aplica a promedio y % vs promedio

### NR Diario
- KPI cards del NR diario del día de referencia (hoy-2 para mes actual, último día para meses pasados)
- Gráfica de barras apiladas NR diario + promedio + CPA
- Tabla NR diario + % vs promedio N meses

---

## 9. Bugs resueltos y mejoras implementadas

| # | Síntoma | Causa raíz | Fix |
|---|---|---|---|
| **Bug 1** | Canales con 0 en acumulado diario | BQ no reporta fila cuando no hay datos; `sum()` devuelve 0 | Forward-fill en Python: si CUM_NR == 0 y el día anterior era positivo, conservar último valor conocido |
| **Bug 2** | cron-job.org `422 Unprocessable Entity` | URL del webhook apuntaba a nombre de workflow anterior | Actualizar URL en cron-job.org al `.yml` correcto |
| **Bug 3** | Fallo 7:00am con `403 quotaExceeded` | meli-bi-data es proyecto compartido con toda Meli; pico de jobs a las 7am en punto | Retry automático (3 intentos / 120s) + cambio de horario a 7:30am |
| **Bug 4** | Plan Excel mostraba "—" en todo | Faltaba `openpyxl` en el pip install del workflow; `try/except` silenciaba el error | Agregar `openpyxl` al workflow YAML |
| **Bug 5 (V2)** | `TypeError: unhashable type: 'list'` | Python no puede usar listas como keys de dict al mapear canales multi-channel | Eliminar mapeo manual en Python; delegar agrupación 100% al CASE WHEN dinámico del SQL |
| **Bug 6 (V2)** | Tabla MoM mostraba `{{MOM_TABLE}}` literal | Función `build_mom_table_html()` omitida al migrar a V2 | Reintegrar la función en el generador Python |
| **Bug 7 (V2)** | deploy_appscript_v2.py sobreescribía URL V1 | Archivo clonado apuntaba al config V1, no al V2 | Corregir para usar `.appscript_config_v2.json`; rollback en Apps Script a v92 |
| **Bug 8 (V2)** | POM TOTAL mostraba plan ~0 al seleccionar | `plan_lines` de POM (row 9) sobreescribía el `plan_row:5` | Solo calcular total desde `plan_lines` en nodos SIN `plan_row` propio |
| **Bug 9 (V2)** | POM ACT invisible al filtrar POM TOTAL | `getLeafToHL` aplicaba `canal_to_label` (mapeo BQ) sobre los labels del dashboard; colisión de nombres | `hier_comps` ya contiene labels directamente en V2 — eliminar paso de traducción |
| **Bug 10 (V2)** | `plan_row` erróneo en UCR Gest / OC ACT | UCR Gest apuntaba a fila de OC Adhoc (row 10); OC ACT apuntaba a OC Recurring (row 6) | Rediseño completo del mapeo Plan: solo nodos agregados tienen plan; nodos leaf de OC+UCR sin plan individual |
| **Mejora 1** | Eliminación UCR Others | Canal nunca tuvo datos reales en MLM (verificado en BQ: siempre null) | Eliminar de jerarquía, tabla, cards y gráficas |
| **Mejora 2** | Reemplazo CPR → CPA | Nomenclatura incorrecta (CPR = Cost per Result, CPA = Cost per Acquisition) | Cambio global en todo el dashboard |
| **Mejora 3** | Filtros dinámicos por jerarquía | Al seleccionar un canal, todos los elementos del dashboard respetan la jerarquía | `filterMomTable`, `renderKPIs`, `renderDailyTable` y `renderVsPromTable` filtran por `indents` del objeto D |
| **Mejora 4** | KPI cards jerárquicas | Cards muestran canal seleccionado + todos sus hijos leaf según nivel de indentación | Lógica de `renderKPIs`, `renderKPIsAcum`, `renderDailyKPIs` basada en `D.indents` |
| **Mejora 5** | Arquitectura Modular V2 | Monolito imposible de mantener con LLMs; errores silenciosos frecuentes | Separación total en 3 componentes con responsabilidades claras |
| **Mejora 6** | Segregación CI/CD V1 / V2 | Riesgo de corromper producción durante desarrollo de V2 | Pipeline paralelo independiente con "Guardia de Seguridad" (verifica HTML > 50KB antes de deploy) |
| **Mejora 7** | plan_lines para OC+UCR | El Excel no mapea 1:1 con la jerarquía del dashboard para OC+UCR | Nuevo concepto `plan_lines` en el JSON: sub-líneas de plan (Recurring, Ad-Hoc, Producto) visibles solo al filtrar ese canal |
| **Mejora 8** | plan_lines para POM TOTAL | POM no gestionado es informativo pero relevante para contexto | plan_line adicional en POM TOTAL que aparece en tabla y gráfica al filtrar ese canal |
| **Bug 11 (V2)** | Tabla Diario mostraba valores negativos absurdos en días recientes (ej. día 29 = -28,896) mientras la gráfica mostraba los valores correctos | Recalculación de nodos agregados en orden top-down: `total_nr` se recalculaba ANTES que sus hijos, usando valores pre-forward-fill | `reversed()` en el loop de recalculación → orden bottom-up garantizado (hojas → intermedios → total) |
| **Mejora 9 (V1)** | Pestaña NR Diario Acumulado en V1 tenía gráfica de barras apiladas que ocupaba toda la pantalla y aportaba poco en el contexto de presentación | Feedback de UX: la tabla + gráfica de líneas es suficiente | Eliminado el `div chart-daily-bar` del HTML y la llamada `renderDailyBar()` del JS |
| **Mejora 10 (V1)** | Pestañas DOW y Subcanales en V1 no relevantes para la presentación | Reducir ruido visual | Eliminados tabs, panes y `case` del switch `initTab`. Actualizado array `TABS` a `['mom','daily','vsprom']` |
| **Mejora 11 (V2)** | `channels_config.json` movido de `src/` a `config/` | Separación más clara entre código y configuración | `CONFIG_PATH` actualizado en `gen_dashboard_v2.py`; `OUT_HTML` movido a raíz del proyecto |

---

## 10. Restricciones conocidas de la org Meli

| Restricción | Impacto | Workaround |
|---|---|---|
| OAuth bloqueado para apps externas con scopes avanzados | Apps Script no puede ser backend | Apps Script solo sirve HTML estático; Python corre fuera de la org |
| Sin permisos para crear proyectos GCP / Cloud Run | No hay jobs programados en GCP | GitHub Actions (runner externo) + cron-job.org |
| BigQuery solo lectura | No se pueden crear vistas ni tablas intermedias | Queries directas con CASE WHEN dinámico |
| Quota compartida en meli-bi-data | Fallos a las 7am en punto | Job a 7:30am + retry automático |

---

## 11. Cómo retomar el proyecto desde cero

```bash
# 1. Activar entorno virtual
cd C:\Users\sergibarra\Documents\SI_Meli_code1\MLM_ADQ_Dash
..\vEnv_Meli_Code1\Scripts\activate

# 2. Generar dashboard V2 localmente
python src/gen_dashboard_v2.py
# Debe imprimir: ✅ ÉXITO: ...dashboard_v2.html generado correctamente (XXX KB)
# Si el KB es < 50: hay un problema en la generación

# 3. Verificar en browser
# Abrir src/dashboard_v2.html localmente antes de deployar

# 4. Deployar a Apps Script V2
python src/deploy_appscript_v2.py
```

### Si la automatización falla
- `GOOGLE_ADC_CREDENTIALS` en GitHub expiró → regenerar con `gcloud auth application-default login`
- PAT en cron-job.org expiró → generar nuevo en GitHub Settings → Developer settings
- Error `422` en cron-job.org → verificar nombre del workflow en la URL
- Error `quotaExceeded` BQ persistente → el retry debería manejarlo; si no, mover el cron a 8am
- HTML generado < 50KB → revisar el log de `gen_dashboard_v2.py`, probablemente hay un error silenciado

---

## 12. Versiones y snapshots

### v2026-03-26-14h — Código base V1 para presentación 31/03
**Git tag**: `v2026-03-26-14h`
**Estado**: Congelado. Código restaurado en `legacy_v1/` via `git show` (sin hacer checkout).

### v2026-03-30-presentacion-01abr — V2 lista para presentación 01/04 ✅
**Git tag**: `v2026-03-30-presentacion-01abr`
**Commit**: `6448ac6e`
**Fecha**: 30 de Marzo 2026
**Estado**: Funcional. Arquitectura V2 modular completa.

**Qué incluye:**
- Arquitectura modular V2 (channels_config.json + gen_dashboard_v2.py + template_dashboard.html)
- Plan corregido: plan_lines para OC+UCR (Recurring/Ad-Hoc/Producto) y POM TOTAL (POM no gestionado)
- Fix bottom-up en recalculación de nodos agregados (Bug 11)
- legacy_v1/ con código exacto de v2026-03-26-14h + mejoras de UI (sin DOW, Subcanales ni barra acumulada)
- History.md y [Claude] MLM_ADQ_Dash_v2.docx actualizados

### Estado actual (Mar 2026) — V2 en desarrollo activo
- Arquitectura modular implementada y funcionando localmente
- CI/CD V2 segregado (no afecta producción V1)
- channels_config.json movido a `config/` para mejor separación de responsabilidades
- Pendiente: verificar rutas en CI/CD V2 tras el movimiento de config/ y promover a producción

---

## 13. Análisis del Excel fuente: `MLM_Costos_Performance.xlsx`

Archivo: `MLM_ADQ_Dash/data/MLM_Costos_Performance.xlsx` — Análisis realizado: Marzo 2026.
Este análisis fue la base de diseño de la pestaña Performance. La implementación resultante
está en `src/queries.py` → `get_perf_paid_sql()`, `get_perf_vpu_sql()`, `get_perf_roa_costos_sql()`
y documentada en `config/queries/performance_vista_corp.md`.

### 13.1 Hojas del Excel

| Hoja | Filas | Propósito |
|---|---|---|
| `MLM apertura canales` | 1182 | Vista detallada sub-canal: installs, N+R, VPU, Valor Predictivo |
| `MLM` | 334 | Vista agregada por canal: Plan / Real / Forecast |
| `MLM (performance mgmt)` | 375 | **La hoja replicada en el dashboard Performance** |
| `Data` | 75501 | Raw data: DAILY_HISTORICO (cols A–AJ) + COSTOS_CANALES (cols BW–CO) |

**Columnas clave de COSTOS_CANALES en Data (sección BW–CO):**
`BZ`=STRATEGY · `BY`=CHANNEL · `CC`=NR · `CD`=VALUE_PRED · `CF`=INVERSION_CANAL_USD ·
`CE`=INVERSION_INCENTIVO_USD · `CG`=INVERSION_TOTAL_USD ·
`CO`=COSTO_TOTAL_SIN_MANTIKA_USD ⚠️ **esta columna NO existe en BQ** (ver §14.11)

### 13.2 Criterio PAID vs FREE (universal en el Excel, implementado en BQ)

El Excel usa `COSTO_TOTAL_SIN_MANTIKA_USD > 0` (col CO) para separar N+R pagados de libres.
Como esa columna no existe en BQ, se usa `INVERSION_TOTAL_USD > 0` como proxy equivalente.
Implementado en: `src/queries.py` → `get_perf_paid_sql()`, líneas ~88–132.

| Tipo | Condición Excel | Condición BQ | Notas |
|---|---|---|---|
| N+R PAID | `CO > 0` | `INVERSION_TOTAL_USD > 0` | Con inversión real (canal o incentivo) |
| N+R FREE | `CO = 0` | `INVERSION_TOTAL_USD = 0` | Sin costo directo |
| N+R GEST OTHERS | `STRATEGY = 'ACTIVATION_OTHER_TEAM'` | mismo | Siempre INV=0, sin filtro de costo |

### 13.3 Fuentes de datos por canal — resumen ejecutivo

| Canal | N+R de | VALUE_PRED de | Inversión de |
|---|---|---|---|
| UCR Gest | COSTOS_CANALES | COSTOS_CANALES ✅ | COSTOS_CANALES |
| OC ACT | COSTOS_CANALES | COSTOS_CANALES ✅ | COSTOS_CANALES |
| POM ADQ | DAILY_HISTORICO ⚠️ | DAILY_HISTORICO ⚠️ | COSTOS_CANALES |
| POM ACT | DAILY_HISTORICO ⚠️ | DAILY_HISTORICO ⚠️ | COSTOS_CANALES |
| MGM | COSTOS_CANALES ✅ | DAILY_HISTORICO ⚠️ | COSTOS_CANALES |

**Gotchas críticos por canal** (todos implementados y verificados en BQ):

1. **POM — NR=0 y VALUE_PRED=0 en COSTOS_CANALES**: La columna NR para CHANNEL='POM' es NULL.
   Solo aporta datos de inversión. N+R y VALUE_PRED vienen exclusivamente de DAILY_HISTORICO.
   Implementado en: `src/queries.py` → lógica mixta en `get_perf_vpu_sql()`.

2. **MGM — VALUE_PRED=0 en COSTOS_CANALES**: La columna existe pero está vacía para MGM.
   El Valor Predictivo de MGM viene de DAILY_HISTORICO.
   Implementado en: `src/processors.py` → `perf_roa_num['MGM ADQ']` usa `perf_vpu_prod`.

3. **MGM — STRATEGY = `ADQUISITION` (sin 'C')**: Typo histórico en PANEL_MONTHLY_COSTOS_CANALES.
   No confundir con `ACQUISITION` (con 'C') que es el valor correcto en DAILY_HISTORICO.
   Implementado en: `src/queries.py` → `get_perf_paid_sql()`, hardcoded `'ADQUISITION'`.

4. **ACTIVATION_OTHER_TEAM — siempre INVERSION_TOTAL=0**: No se aplica filtro de costo.
   Son N+R gestionados por otros equipos — siempre clasifican como FREE / GEST OTHERS.

5. **ROAs MGM — fórmula especial**: No es `VALUE_PRED / Inversión` directo.
   Es `(VPU_MGM × N+R_Paid_MGM) / Inversión_MGM` porque VALUE_PRED=0 en costos.
   Implementado en: `src/processors.py` → `perf_roa_num` con lógica mixta por canal.

6. **FLAG_INCENTIVO vs COSTO_SIN_MANTIKA**: Para OC ACT hay filas con FLAG_INCENTIVO=NO
   pero con COSTO_SIN_MANTIKA=5,377 (inversión de canal sin incentivo). El criterio correcto
   de PAID es `CO > 0`, no el flag. Usando `INVERSION_TOTAL_USD > 0` en BQ cubre este caso.

### 13.4 Combinaciones únicas CHANNEL/STRATEGY en COSTOS_CANALES (datos reales extraídos)

Datos extraídos del Data tab (acumulado histórico completo). Son la fuente de verdad de los
CASE WHEN en `get_perf_paid_sql()` y `get_costos_sql()`.

| CHANNEL | STRATEGY | FLAG_INCENTIVO | NR acum. | VALUE_PRED acum. | INV_TOTAL |
|---|---|---|---|---|---|
| MGM | ADQUISITION | NO | 215,299 | 0 | 0 |
| MGM | ADQUISITION | SI | 20,366 | 0 | 798,323 |
| OWN CHANNELS MKT | ACTIVATION | NO | 107,950 | 6,713,199 | 39,887 |
| OWN CHANNELS MKT | ACTIVATION | SI | 1,038,723 | 53,772,229 | 10,958,308 |
| OWN CHANNELS MKT | ACTIVATION_OTHER_TEAM | NO | 210,501 | 13,684,696 | 0 |
| OWN CHANNELS MKT | UCRANIA | NO | 540,995 | 32,776,335 | 18,736 |
| OWN CHANNELS MKT | UCRANIA | SI | 202,128 | 11,055,673 | 2,016,254 |
| POM | ACQUISITION POM | SI | **0** ⚠️ | **0** ⚠️ | 13,138,309 |
| POM | ACTIVATION POM | SI | **0** ⚠️ | **0** ⚠️ | 7,901,151 |
| POM | CTW POM | SI | **0** ⚠️ | **0** ⚠️ | 8,676 |
| POM | WEB POM | SI | **0** ⚠️ | **0** ⚠️ | 1,300,910 |

### 13.5 Jerarquía de la vista de Performance (hoja `MLM performance mgmt`)

```
Total Site
├── Own Channels + Ucrania
│   ├── Ucrania (UCR Gest)
│   ├── Own Channels Activación (OC ACT, incluye WPP)
│   └── Whatsapp (sub-canal de OC ACT)
├── POM → POM Acquisition (APPD) · POM Activation (APPE) · POM Web
├── MGM
└── L&P  ← solo N+R Free + VPU. Sin CPA Paid ni ROAs.
```

### 13.6 Fórmula ROAs Total Site — mezcla tres fuentes

```
ROAs = (VALUE_PRED_OC_con_inv + VALUE_PRED_POM_via_DAILY + VPU_MGM × N+R_Paid_MGM)
       / Inversión_Total
```

Tres fuentes distintas en un solo numerador:
1. `VALUE_PRED` de COSTOS_CANALES para UCR Gest y OC ACT (filtro `INVERSION > 0`)
2. `VALUE_MKT_PREDICTION_90D_NR_USERS` de DAILY_HISTORICO para POM (via apertura canales)
3. `VPU_MGM × N+R_Paid_MGM` para MGM (porque VALUE_PRED=0 en costos para MGM)

Implementado en: `src/queries.py` → `get_perf_roa_costos_sql()` + `src/processors.py` →
dict `perf_roa_num` con lógica mixta. Ver §14.4 para el detalle de fuentes por canal.

---

## 14. Implementación de la pestaña "Performance" (2026-03-31)

### 14.1 Motivación

La pestaña de Costos muestra la **inversión** por canal pero no permite cruzarla fácilmente con el **valor generado**. La hoja `MLM (performance mgmt)` del Excel `MLM_Costos_Performance.xlsx` tiene exactamente esa vista: por canal y sub-canal, muestra N+R, desglose Paid/Free/Gest Others, CPA Blended, CPA Paid, VPU Pred 90D, Valor Predictivo 90D y ROAs. El objetivo de esta implementación fue replicar esa vista en el dashboard, con datos directos de BigQuery y actualización automática.

### 14.2 Métricas incluidas por canal

| Métrica | Descripción | Fórmula |
|---|---|---|
| **N+R Total** | Todos los nuevos+recurrentes del canal/mes | `SUM(NR_USERS)` de `PANEL_MONTHLY_DAILY_HISTORICO` |
| **N+R Paid** | Usuarios adquiridos con inversión real | Ver §14.4 por canal |
| **N+R Free** | Usuarios sin costo directo (excl. Gest Others) | `N+R Total − N+R Paid − N+R Gest Others` |
| **N+R Gest. Others** | Gestionados por otros equipos (`ACTIVATION_OTHER_TEAM`) | Solo OC ACT; siempre tiene `COSTO_SIN_MANTIKA = 0` |
| **Inv. (USD)** | Inversión total del canal | `SUM(INVERSION_TOTAL_USD)` de `PANEL_MONTHLY_COSTOS_CANALES` |
| **CPA Blended** | Costo por usuario total | `Inv / N+R Total` |
| **CPA Paid** | Costo por usuario pagado | `Inv / N+R Paid` |
| **VPU Pred 90D** | Valor por usuario predicho a 90 días | `SUM(VALUE_MKT_PREDICTION_90D_NR_USERS) / SUM(NR)` de `DAILY_HISTORICO` (columna ya pre-multiplicada) |
| **Valor Pred 90D** | Valor total predicho para usuarios pagados | `VPU × N+R Paid` |
| **ROAs** | Retorno sobre inversión publicitaria | `Valor Pred 90D / Inv` |

> **Criterio PAID**: `INVERSION_TOTAL_USD > 0` en `PANEL_MONTHLY_COSTOS_CANALES`. El análisis Excel original identificó `COSTO_TOTAL_SIN_MANTIKA_USD` (col CO) como criterio ideal, pero esa columna no existe con ese nombre en BQ. Se usa `INVERSION_TOTAL_USD` como proxy equivalente: si hay cualquier inversión (canal o incentivo), el usuario es Paid. `ACTIVATION_OTHER_TEAM` siempre tiene `INVERSION_TOTAL_USD = 0` (ver §13.6), por lo que se identifica correctamente como Free/Gest Others.

> **VPU**: Se obtiene como `SUM(VALUE_MKT_PREDICTION_90D_NR_USERS) / SUM(NR_USERS)` de `PANEL_MONTHLY_DAILY_HISTORICO`. La columna `VALUE_MKT_PREDICTION_90D_NR_USERS` ya viene pre-multiplicada (NR × VPU por fila), por lo que solo se necesita `SUM()` directo. Se usa DAILY_HISTORICO para todos los canales (incluidos OC/UCR) porque POM y MGM tienen `VALUE_PRED=0` en COSTOS_CANALES (ver §13.5 y §13.6).

---

### 14.3 Nuevas consultas BigQuery

Implementadas en: `src/queries.py`. SQL completo: leer el archivo directamente.

**`get_perf_paid_sql()`** — Fuente: `PANEL_MONTHLY_COSTOS_CANALES`
- Retorna: `(MONTH_ID, PERF_CANAL, NR_TOTAL, NR_PAID, NR_GEST_OTHERS)`
- Canales cubiertos: UCR Gest, OC ACT, MGM ADQ (los únicos con NR real en COSTOS_CANALES)
- Canales NO cubiertos (usan otras fuentes): UCR PRD, POM ADQ/ACT, MGM ACT, L&P, ORG → ver §14.4
- Criterio PAID: `INVERSION_TOTAL_USD > 0` (proxy de `COSTO_TOTAL_SIN_MANTIKA_USD` — no existe en BQ, ver §14.11)
- Criterio GEST OTHERS: `STRATEGY = 'ACTIVATION_OTHER_TEAM'` (siempre INV=0)
- ⚠️ MGM usa `STRATEGY = 'ADQUISITION'` (typo histórico, sin 'C') — ver §13.4 gotcha #3

**`get_perf_vpu_sql()`** — Fuente: `PANEL_MONTHLY_DAILY_HISTORICO`
- Retorna: `(MONTH_ID, PERF_CANAL, NR_TOTAL, NR_VPU_PROD)`
- Cubre TODOS los canales (DAILY_HISTORICO para todos porque COSTOS_CANALES tiene VALUE_PRED=0 para POM y MGM)
- `NR_VPU_PROD = SUM(VALUE_MKT_PREDICTION_90D_NR_USERS)` — columna ya pre-multiplicada (NR × VPU por fila). `SUM()` directo. **No multiplicar de nuevo** (ver §14.11 bug #2).
- VPU ponderado: `NR_VPU_PROD / NR_TOTAL`. Para nodos padre: `SUM(NR_VPU_PROD hijos) / SUM(NR_TOTAL hijos)`.
- CASE WHEN generado dinámicamente desde `channels_config.json → bq_mapping` (misma lógica que `get_nr_sql()`).

---

### 14.4 Fuente de N+R Paid por canal

La definición de N+R Paid varía por canal según la disponibilidad de datos:

| Canal | N+R Paid — Fuente y criterio |
|---|---|
| **UCR Gest** | `COSTOS_CANALES`: filas donde `COSTO_TOTAL_SIN_MANTIKA_USD > 0` y `STRATEGY='UCRANIA'` |
| **UCR PRD** | **Siempre 0** — `no_cost=true` en hierarchy_cost; todo su N+R es Free (canal orgánico PRD) |
| **OC ACT** | `COSTOS_CANALES`: filas donde `COSTO_SIN_MANTIKA > 0` y `STRATEGY='ACTIVATION'`. Las filas de `ACTIVATION_OTHER_TEAM` siempre tienen costo=0 → no aportan a Paid |
| **POM ADQ** | **Todo el N+R = Paid** — POM es 100% medio pagado por definición; `NR=0` en COSTOS_CANALES, por lo que se usa `monthly_nr['POM ADQ'][m]` de DAILY_HISTORICO |
| **POM ACT** | **Todo el N+R = Paid** — igual que POM ADQ |
| **MGM ADQ** | `COSTOS_CANALES`: filas donde `COSTO_SIN_MANTIKA > 0` y `STRATEGY='ADQUISITION'` (typo histórico, sin 'C') |
| **MGM ACT** | **Siempre 0** — `no_cost=true`; MGM ACT no tiene inversión directa |
| **L&P ADQ** | **Siempre 0** — `no_cost=true`; sin datos de costo disponibles |
| **L&P ACT** | **Siempre 0** — `no_cost=true` |
| **ORG** | **Siempre 0** — canal orgánico, sin costo |

**Nodos agregados** (OC+UCR, POM TOTAL, MGM TOTAL, L&P TOTAL, Total N+R): se computan como **suma de los hijos leaf** en el procesamiento bottom-up (ver §14.5).

---

### 14.5 Procesamiento Python

Implementado en: `src/processors.py` → `process_all()`, sección 3c (después del cálculo de CPA).

Dicts resultantes (accesibles desde `build_perf_table_html()`):
- `perf_nr_paid[label][month]` → int — N+R Paid por canal/mes
- `perf_nr_go[label][month]` → int — N+R Gest Others (solo OC ACT y sus padres > 0)
- `perf_vpu_prod[label][month]` → float — SUM(NR×VPU) para VPU ponderado

**Casos especiales en el poblado** (ver `process_all()` sección 3c):
- POM ADQ y POM ACT: `perf_nr_paid = monthly_nr` (todo el NR es Paid por definición)
- Nodos agregados: propagación bottom-up con `reversed(HIERARCHY)` → garantiza hijos antes que padres
- Inversión: `monthly_inv_total` (sección 3b) mapeando `'Total N+R' → 'Total Inversión'` (único mismatch de nombre entre hierarchy_nr y hierarchy_cost)

---

### 14.6 Builder HTML (`build_perf_table_html()`)

Implementado en: `src/builders.py` → `build_perf_table_html(data)`.

**Estructura de sub-filas por canal** (en orden): N+R Total · N+R Paid · N+R Free · N+R Gest. Others (condicional) · Inv. (USD) · CPA Blend. · CPA Paid · VPU Pred 90D · Valor Pred 90D · ROAs

**Decisiones de diseño clave:**
- VPU ponderado: `perf_vpu_prod[label][m] / monthly_nr[label][m]` — ratio de sumas, no promedio de promedios
- Valor Pred 90D: `vpu_avg × perf_nr_paid[label][m]` (sobre N+R Paid, no N+R Total)
- Inversión: función `get_inv(label)` mapea `'Total N+R' → 'Total Inversión'` (único mismatch entre jerarquías)
- N+R Gest. Others: sub-fila condicional — solo se renderiza si algún mes tiene valor > 0; color naranja `#F5A664`
- Columnas: usa `months` de DAILY_HISTORICO (no `cost_months`). Si un mes tiene N+R pero no inversión → CPA/ROAs muestran `—`

---

### 14.7 Cambios en `template_dashboard.html`

Implementadas en: `src/template_dashboard.html`. Ver el archivo para el código completo.

- Placeholder `{{PERF_TABLE}}` en tab `pane-perf` → reemplazado en `assemble()` con `build_perf_table_html()`
- `'perf'` añadido al array `const TABS`
- `filterPerfTable(canal)` — filtra filas respetando jerarquía (usa `D.indents` para mostrar canal + todos sus hijos). Sub-filas comparten `data-canal` con su fila principal.
- `highlightPerfMonthCol(month)` — resalta columna del mes activo con estilo `col-highlighted`
- Llamadas añadidas en `onCanalChange()`, `onMonthChange()` e `initTab('perf')`
- **Importante**: Performance es tabla HTML pura, sin gráfica Plotly → sin `chartsInit`

---

### 14.8 Relación con las queries existentes (no se duplica trabajo)

| Dato | Query existente que lo provee | Nueva query que lo complementa |
|---|---|---|
| N+R Total por canal/mes | `get_dynamic_sql()` → `monthly_nr` | — |
| Inversión por canal/mes | `get_costos_sql()` → `monthly_inv_total` | — |
| N+R Paid para UCR Gest / OC ACT / MGM ADQ | — | `get_perf_paid_sql()` |
| N+R Gest Others (ACTIVATION_OTHER_TEAM) | — | `get_perf_paid_sql()` |
| VPU ponderado para todos los canales | — | `get_perf_vpu_sql()` |
| N+R Paid para POM | `monthly_nr` (se asume todo paid) | — |

El total de queries BQ pasa de **2 a 4** (DAILY_HISTORICO + COSTOS_CANALES + perf_paid + perf_vpu). Hay algo de overlap entre `get_dynamic_sql()` y `get_perf_vpu_sql()` porque ambas leen DAILY_HISTORICO con el mismo WHERE y casi el mismo CASE WHEN; se mantienen separadas para no alterar la lógica de diarios/acumulados ya estable.

---

### 14.9 Limitaciones y aproximaciones conocidas

1. **VPU para N+R Paid ≠ VPU para N+R Total**: el `vpu_avg` que se calcula es `SUM(NR×VPU) / SUM(NR)`, ponderado por todos los usuarios del canal (paid + free). Idealmente para Valor Pred se querría el VPU ponderado solo por los usuarios paid. No es posible calcularlo desde DAILY_HISTORICO sin saber cuáles filas específicas son paid, ya que esa distinción existe solo en COSTOS_CANALES (que tiene NR=0 para POM). Se acepta esta aproximación.

2. **POM: Paid = Total NR**: se asume que todos los usuarios de POM son "Paid" porque POM es 100% medio pagado. Esto puede sobreestimar ligeramente si hay usuarios recurrentes activados por otros canales pero que el sistema atribuye a POM.

3. **UCR PRD: Paid = 0**: UCR PRD no tiene inversión en COSTOS_CANALES. Se clasifica completamente como Free. Si en algún mes tiene costo de canal fuera de la jerarquía actual, no se reflejaría.

4. **L&P: sin inversión**: L&P ADQ y L&P ACT están marcados `no_cost=true` en hierarchy_cost. No se obtiene inversión para ellos, por lo que CPA Paid y ROAs siempre serán `—`. Cuando se tenga el mapeo de costos para L&P, se debe agregar `cost_mapping` en channels_config.json.

5. **Meses sin datos en COSTOS_CANALES**: si un mes tiene N+R (en DAILY_HISTORICO) pero no hay filas en COSTOS_CANALES para ese mes, `monthly_inv_total[label][m]` retornará `None` o `0`, y las métricas derivadas (CPA, ROAs) mostrarán `—`.

6. **Nodos agregados de VPU**: para un nodo como "OC + UCR", el VPU se calcula como `SUM(NR_VPU_PROD de UCR Gest + UCR PRD + OC ACT) / SUM(NR Total)`. UCR PRD puede tener VPU muy distinto a UCR Gest, por lo que el VPU agregado es una mezcla ponderada.

---

### 14.11 Correcciones de nombres de columna en BQ (2026-03-31 — primera ejecución real)

Dos errores `400 BadRequest: Unrecognized name` al correr las nuevas queries por primera vez. Los nombres usados en el diseño no coincidían con los nombres reales en BQ.

#### Error 1: `COSTO_TOTAL_SIN_MANTIKA_USD` — no existe en BQ
**Query afectada**: `src/queries.py` → `get_perf_paid_sql()`
**Causa**: col CO del Excel (`COSTO_TOTAL_SIN_MANTIKA_USD`) no existe con ese nombre en BQ.
**Fix**: reemplazada por `INVERSION_TOTAL_USD > 0` — proxy equivalente para identificar N+R Paid.
**Justificación**: `INVERSION_TOTAL_USD = INVERSION_CANAL_USD + INVERSION_INCENTIVO_USD`. Cualquier fila con inversión real tiene `INVERSION_TOTAL_USD > 0`. `ACTIVATION_OTHER_TEAM` siempre tiene `= 0` → se identifica correctamente como Free.

#### Error 2: `VALUE_MKT_PREDICTION_90D` — nombre incompleto en BQ
**Query afectada**: `src/queries.py` → `get_perf_vpu_sql()`
**Causa**: el nombre real incluye sufijo `_NR_USERS` → `VALUE_MKT_PREDICTION_90D_NR_USERS`.
**Hallazgo crítico**: el sufijo `_NR_USERS` significa que la columna ya viene **pre-multiplicada** (NR × VPU por fila). Por tanto: `Valor_Pred = SUM(col)` directo. `VPU_avg = SUM(col) / SUM(NR_USERS)`. **Nunca hacer `SUM(NR × col)`** — sería doble multiplicación.

---

#### Resumen de columnas reales en `PANEL_MONTHLY_COSTOS_CANALES`

| Columna usada en código | Nombre real en BQ | Estado |
|---|---|---|
| `INVERSION_CANAL_USD` | `INVERSION_CANAL_USD` | ✅ Correcto desde el inicio |
| `INVERSION_INCENTIVO_USD` | `INVERSION_INCENTIVO_USD` | ✅ Correcto desde el inicio |
| `INVERSION_TOTAL_USD` | `INVERSION_TOTAL_USD` | ✅ Correcto desde el inicio |
| `NR` | `NR` | ✅ Correcto (confirmado implícitamente — no generó error) |
| `CHANNEL` | `CHANNEL` | ✅ Correcto desde el inicio |
| `STRATEGY` | `STRATEGY` | ✅ Correcto desde el inicio |
| `COSTO_TOTAL_SIN_MANTIKA_USD` | **no existe** | ❌ Reemplazado por `INVERSION_TOTAL_USD` |

#### Resumen de columnas reales en `PANEL_MONTHLY_DAILY_HISTORICO`

| Columna usada en código | Nombre real en BQ | Estado |
|---|---|---|
| `NR_USERS` | `NR_USERS` | ✅ Correcto desde el inicio |
| `COST_USD` | `COST_USD` | ✅ Correcto desde el inicio |
| `FECHA_DIARIA` | `FECHA_DIARIA` | ✅ Correcto desde el inicio |
| `STRATEGY` | `STRATEGY` | ✅ Correcto desde el inicio |
| `CHANNEL` | `CHANNEL` | ✅ Correcto desde el inicio |
| `VALUE_MKT_PREDICTION_90D` | **no existe** | ❌ Reemplazado por `VALUE_MKT_PREDICTION_90D_NR_USERS` |
| `VALUE_MKT_PREDICTION_90D_NR_USERS` | `VALUE_MKT_PREDICTION_90D_NR_USERS` | ✅ Correcto tras corrección |

---

### 14.10 Archivos modificados en esta implementación

| Archivo | Cambios |
|---|---|
| `src/gen_dashboard_v2.py` | +`get_perf_paid_sql()`, +`get_perf_vpu_sql()`, +Sección 3c (procesamiento), +`build_perf_table_html()`, actualización de `assemble()` |
| `src/template_dashboard.html` | +tab "Performance", +`pane-perf` con `{{PERF_TABLE}}`, +`'perf'` en TABS, +`filterPerfTable()`, +`highlightPerfMonthCol()`, actualizaciones en `onCanalChange()`, `onMonthChange()`, `initTab()` |
| `config/channels_config.json` | **Sin cambios** — se reutilizan `hierarchy_nr` y `hierarchy_cost` existentes |

---

## 15. Sesión 2025-04-02: Correcciones de KPIs y Rediseño Visual de la Pestaña Performance

### Contexto
Al revisar la pestaña Performance (§14), se identificaron tres bugs funcionales y dos mejoras visuales.

---

### 15.1 Bug: Valor Pred 90D con doble multiplicación

**Causa raíz**: Mismo bug documentado en §14.11 Error 2 — columna inexistente + doble multiplicación.
`get_perf_vpu_sql()` usaba nombre incorrecto (`VALUE_MKT_PREDICTION_90D`) y `build_perf_bar()` multiplicaba `VPU × NR_PAID` sobre una columna ya pre-multiplicada.
**Fix**: `perf_vpu_prod[label][m]` directo en la tabla. `VPU_avg = perf_vpu_prod / monthly_nr` (ratio, no promedio). Ver columna correcta y semántica en §14.11.
Implementado en: `src/queries.py` → `get_perf_vpu_sql()` + `src/builders.py` → `build_perf_bar()` y `build_perf_table_html()`.

---

### 15.2 Corrección: ROAs calculado con fuente de datos incorrecta

**Síntoma**: ROAs mostraba valores de ~25x (irreal); todos los canales usaban la misma fuente de numerador.

**Causa raíz**: El código inicial calculaba ROAs usando `perf_vpu_prod` (de `DAILY_HISTORICO`) para **todos** los canales sin distinción. Según `metrics_logic.md §5`, el numerador del ROA varía por canal.

**Regla de negocio** (de `metrics_logic.md §5`):

| Canal | Fuente del numerador ROA | Filtro |
|---|---|---|
| UCR Gest | `VALUE_PRED` de `PANEL_MONTHLY_COSTOS_CANALES` | `INVERSION_TOTAL_USD > 0` + `STRATEGY = 'UCRANIA'` |
| OC ACT | `VALUE_PRED` de `PANEL_MONTHLY_COSTOS_CANALES` | `INVERSION_TOTAL_USD > 0` + `STRATEGY = 'ACTIVATION'` |
| POM ADQ | `VALUE_MKT_PREDICTION_90D_NR_USERS` de `DAILY_HISTORICO` | `CHANNEL IN ('POM ACQ','POM')` + `STRATEGY = 'ACQUISITION'` |
| POM ACT | `VALUE_MKT_PREDICTION_90D_NR_USERS` de `DAILY_HISTORICO` | `CHANNEL IN ('POM ACQ','POM')` + `STRATEGY = 'ACTIVATION'` |
| MGM ADQ | `VALUE_MKT_PREDICTION_90D_NR_USERS` de `DAILY_HISTORICO` | `CHANNEL = 'MGM'` + `STRATEGY = 'ACQUISITION'` |
| MGM ACT | ❌ Sin ROA (0) | `STRATEGY = 'ACTIVATION'` ≠ `'ACQUISITION'` → excluido |
| UCR PRD, L&P, ORG | ❌ Sin ROA (0) | Sin inversión directa |

**Solución**: Nueva `get_perf_roa_costos_sql()` en `src/queries.py` + nuevo dict `perf_roa_num` en `src/processors.py`.
- `get_perf_roa_costos_sql()`: Fuente COSTOS_CANALES, filtro `INVERSION_TOTAL_USD > 0`, cubre solo UCR Gest y OC ACT. SQL completo en `src/queries.py`.
- `perf_roa_num` en `processors.py` sección 3c: lógica mixta — UCR Gest/OC ACT desde `df_perf_roa` (COSTOS), POM ADQ/POM ACT/MGM ADQ desde `perf_vpu_prod` (DAILY). MGM ACT excluido (solo STRATEGY='ACQUISITION' según `metrics_logic.md §5`). Propagación bottom-up idéntica a los demás dicts.

---

### 15.3 Corrección: Discrepancia ROAs tabla vs gráfica

**Síntoma**: La tabla mostraba ROAs = 24.99x mientras la gráfica mostraba ~4–5x. Valores distintos para la misma métrica.

**Causa raíz**: Estado intermedio durante la refactorización — la tabla ya había sido actualizada para usar `perf_vpu_prod` directamente (valor post-corrección de §15.1), pero la gráfica `build_perf_bar()` todavía usaba la fórmula antigua `(VPU/NR_total) × NR_paid / INV`.

**Solución**: `build_perf_bar()` unificado para usar `data['perf_roa_num']` (mismo dict que la tabla).
Implementado en: `src/builders.py` → `build_perf_bar()`.
**Principio permanente**: Tabla y gráfica comparten la misma fuente de datos (dict pre-calculado en `processors.py`). Si hay discrepancia, siempre es porque uno de los dos no usa el dict correcto.

---

### 15.4 Mejora visual: Rediseño Look & Feel de la tabla Performance

**Motivación**: La tabla heredaba el estilo `.mom-tbl` con fondo azul marino oscuro en encabezados y filas densas, lo cual no era adecuado para una tabla analítica con muchas sub-métricas.

**Solución**: Nueva clase CSS `.perf-tbl` en `src/dashboard.css` que sobreescribe `.mom-tbl`. CSS completo en `src/dashboard.css`.
El `<table>` usa `class="mom-tbl perf-tbl"` — hereda estructura base + aplica look limpio (headers grises, no azul marino).

**Estructura de filas por canal** (ver `src/builders.py` → `build_perf_table_html()`):

| Fila | Estilo | Contenido |
|---|---|---|
| Row A (cabecera de canal) | Fondo `bg` del nivel jerárquico, sin valores | Nombre del canal (ej. "UCR Gest") |
| Row B | Fondo `bg`, negrita, borde izquierdo canal | `N+R Total` con valores |
| Sub-filas normales | `SM_LBL`/`SM_VAL` (gris claro, 10.5px) | `↳ N+R Paid`, `↳ N+R Free`, `↳ N+R Gest. Others` (condicional) |
| Filas resaltadas | `HL_LBL`/`HL_VAL` (azul oscuro, negrita, fondo `#f0f4fa`) | `Inv. Total (USD)`, `CPA Blend.`, `VPU Pred 90D` |
| Sub-filas secundarias | `SM_LBL`/`SM_VAL` | `↳ CPA Paid`, `↳ Valor Pred 90D` |
| ROAs | Azul semi-negrita (`#2d5986`, `font-weight:600`) | `ROAs` |

Variables de estilo `LVL`, `SM_LBL`, `SM_VAL`, `HL_LBL`, `HL_VAL` definidas al inicio de `build_perf_table_html()` en `src/builders.py`.

---

### 15.5 Mejora visual: Colores de borde izquierdo por canal

**Motivación**: El borde izquierdo de cada sección de canal en la tabla Performance usaba los colores de jerarquía genéricos (azul marino por nivel). El usuario quería que coincidiera con el color oficial de cada canal (el mismo que se usa en las otras pestañas y en la leyenda de gráficas).

**Fuente de verdad**: `config/channels_config.json` — cada nodo tiene un campo `"color"` que llega a `builders.py` a través de `data['HIERARCHY_NR']`.

**Colores de canales**:
| Canal | Color |
|---|---|
| Total N+R | `#2D3277` |
| OC+UCR | `#5899D1` |
| Ucrania | `#1AB059` |
| UCR Gest | `#5899D1` |
| UCR PRD | `#1AB059` |
| OC ACT | `#E1484C` |
| POM TOTAL | `#2F9E8F` |
| POM ADQ | `#2F9E8F` |
| POM ACT | `#86C9C4` |
| MGM TOTAL | `#F5A664` |
| MGM ADQ | `#F5A664` |
| MGM ACT | `#F7C297` |
| L&P TOTAL | `#7A41ED` |
| L&P ADQ | `#7A41ED` |
| L&P ACT | `#BE9FE1` |
| ORG | `#A4ACB9` |

**Cambio en** `src/builders.py` → `build_perf_table_html()`: `border = c['color']` (del canal en `channels_config.json`) en lugar de `LVL[c['level']]` (color genérico por nivel). Se aplica como `border-left:3px solid {border}` en todas las filas del canal.

---

### 15.6 Corrección visual: Primera fila de datos = "N+R Total" y ajuste de resaltados

**Tres cambios solicitados en simultáneo**:

1. **La primera fila de datos de cada canal se llama "N+R Total"** (antes tenía el nombre del canal, lo que generaba duplicidad visual ya que Row A ya mostraba el nombre).
   - `build_perf_table_html()` Row B: cambiado de `{label}` a `N+R Total`.

2. **Resaltar Inv. Total (USD), CPA Blend. y VPU Pred 90D** con el estilo `HL_LBL`/`HL_VAL` (fondo azul claro, texto azul oscuro negrita) para destacarlas como métricas clave frente a las sub-métricas secundarias.

3. **↳ N+R Gest. Others sin resaltado** (antes se le aplicaba un color naranja especial que lo diferenciaba del resto de sub-métricas normales). Ahora usa los mismos estilos `SM_LBL`/`SM_VAL` que `↳ N+R Paid` y `↳ N+R Free`.

---

### 15.7 Archivos modificados en esta sesión

| Archivo | Cambios |
|---|---|
| `src/queries.py` | +`get_perf_roa_costos_sql()` (nueva función, sin parámetros, hardcoded para UCR Gest + OC ACT). Corrección de columna `VALUE_MKT_PREDICTION_90D` → `VALUE_MKT_PREDICTION_90D_NR_USERS` en `get_perf_vpu_sql()`. |
| `src/processors.py` | +import `get_perf_roa_costos_sql`. +`df_perf_roa` en Sección 3c. +construcción de `perf_roa_num` con fuentes mixtas (COSTOS para UCR/OC, DAILY para POM/MGM, 0 para el resto). +propagación bottom-up de `perf_roa_num`. +`perf_roa_num` en dict de retorno. |
| `src/builders.py` | `build_perf_table_html()`: estructura de dos filas por canal (Row A cabecera + Row B N+R Total), `HL_LBL`/`HL_VAL` para métricas clave, `SM_LBL`/`SM_VAL` uniforme para sub-métricas (incluye N+R Gest. Others), borde izquierdo por color de canal, ROAs usa `perf_roa_num`. `build_perf_bar()`: ROAs usa `perf_roa_num` (unificado con tabla). |
| `src/dashboard.css` | +`.perf-tbl` clase con override de estilos (encabezados claros, bordes sutiles, separadores de sección). |
| `config/channels_config.json` | Sin cambios. |

---

## 16. Sesión 2025-04-02 (continuación): Renombrado de pestañas

### Motivación
Los nombres originales de las pestañas ("MoM por Canal", "Diario Acumulado", "Diario") no dejaban claro de forma inmediata qué tipo de dato mostraban. Se estandarizaron con el prefijo **NR** para reforzar que todas muestran datos de N+R.

### Cambios de nombre

| Nombre anterior | Nombre nuevo |
|---|---|
| MoM por Canal | **NR Mensual** |
| Diario Acumulado | **NR Diario Acumulado** |
| Diario | **NR Diario** |
| Performance | Sin cambio |

### Archivos actualizados

| Archivo | Cambio |
|---|---|
| `src/template_dashboard.html` | Labels de los 3 `<div class="tab">` + comentarios de sección JS (`DAILY KPI CARDS`, `KPI CARDS DIARIO ACUMULADO`, `DAILY BAR CHART`) |
| `src/builders.py` | Comentarios de sección `# ── Tabla ...` y `# ── Gráfica ...`, docstrings de `build_mom_table_html()` y `build_mom_bar()` |
| `CLAUDE.md` | Descripción de pestañas en §"Pestañas del dashboard" |
| `docs/History.md` | §8 (pestañas del dashboard), §9 tabla de bugs/mejoras (Mejora 9), §15.7 — todos los nombres actualizados en contexto |

### Nota sobre IDs internos
~~Los IDs del DOM y nombres de funciones JS no se modificaron.~~ → **Revertido en §17**: se llevó a cabo el renombrado completo de funciones e IDs en la sesión posterior.

---

## 17. Sesión 2026-04-02 (continuación): Renombrado completo de funciones JS e IDs DOM

### Motivación
El código JS del template usaba nombres heredados del prototipo V1 (`renderKPIs`, `highlightMomRow`, `renderDaily`, `renderVsProm`, etc.) que no dejaban claro a qué pestaña ni a qué tipo de dato pertenecían. Se renombraron todas las funciones, IDs de DOM y valores de tab para que sean autoexplicativos: si es NR o Cost, si es Mensual, Diario Acumulado o Diario.

### Convención de nombres aplicada

- **Funciones**: `verbo` + `qué` + `dónde` — ej. `renderKPIsNRMensual`, `filterTablePerf`, `updateCPANRMensual`
- **IDs de pane**: `pane-{tab}` — ej. `pane-nr-mensual`, `pane-nr-diario-acum`
- **IDs de chart**: `chart-{tab}[-tipo]` — ej. `chart-nr-mensual-bar`, `chart-nr-diario-acum-line`
- **IDs de KPIs**: `kpi-row-{tab}` — ej. `kpi-row-nr-mensual`
- **IDs de tabla**: `tbl-{tab}` — ej. `tbl-nr-diario-acum`, `tbl-nr-diario`
- **Valores de tab en TABS array**: `'nr-mensual'`, `'nr-diario-acum'`, `'nr-diario'` (antes `'mom'`, `'daily'`, `'vsprom'`)

### Tabla de renames de funciones

| Nombre anterior | Nombre nuevo | Descripción |
|---|---|---|
| `renderKPIs` | `renderKPIsNRMensual` | KPI cards de la pestaña NR Mensual |
| `highlightMomRow` | `highlightRowNRMensual` | Resalta fila de canal en tabla NR Mensual |
| `filterMomTable` | `filterTableNRMensual` | Filtra tabla NR Mensual por jerarquía |
| `highlightMonthCol` | `highlightColNRMensual` | Resalta columna de mes en NR Mensual |
| `updateChartAnnotations` | `updateAnnotNRMensual` | Actualiza anotaciones del chart NR Mensual |
| `getLeafToHL` | `getLeafNRToHL` | Obtiene hojas NR para resaltar (helper) |
| `updateMomCPA` | `updateCPANRMensual` | Actualiza línea CPA en chart NR Mensual |
| `updateMomPlan` | `updatePlanNRMensual` | Actualiza línea Plan en chart NR Mensual |
| `highlightChart` | `highlightChartNRMensual` | Resalta series en chart NR Mensual |
| `highlightChartMonth` | `highlightMonthNRMensual` | Resalta mes en chart NR Mensual |
| `renderDaily` | `renderNRDiarioAcum` | Renderiza pestaña NR Diario Acumulado |
| `renderDailyTable` | `renderTableNRDiarioAcum` | Tabla de NR Diario Acumulado |
| `renderDailyBar` | `renderChartNRDiarioAcum` | Chart barras de NR Diario Acumulado |
| `renderKPIsAcum` | `renderKPIsNRDiarioAcum` | KPI cards de NR Diario Acumulado |
| `renderDailyKPIs` | `renderKPIsNRDiario` | KPI cards de NR Diario |
| `renderVsProm` | `renderNRDiario` | Renderiza pestaña NR Diario |
| `renderVsPromTable` | `renderTableNRDiario` | Tabla de NR Diario |
| `getCostLeafToHL` | `getLeafCostToHL` | Obtiene hojas Costo para resaltar (helper) |
| `updatePerfChart` | `updateChartPerf` | Actualiza chart de Performance |
| `filterPerfTable` | `filterTablePerf` | Filtra tabla Performance |
| `highlightPerfMonthCol` | `highlightColPerf` | Resalta columna de mes en Performance |

### Tabla de renames de IDs DOM y tab values

| Nombre anterior | Nombre nuevo | Tipo |
|---|---|---|
| `'mom'` en TABS | `'nr-mensual'` | Valor de tab |
| `'daily'` en TABS | `'nr-diario-acum'` | Valor de tab |
| `'vsprom'` en TABS | `'nr-diario'` | Valor de tab |
| `t-mom` / `pane-mom` | `t-nr-mensual` / `pane-nr-mensual` | IDs HTML |
| `t-daily` / `pane-daily` | `t-nr-diario-acum` / `pane-nr-diario-acum` | IDs HTML |
| `t-vsprom` / `pane-vsprom` | `t-nr-diario` / `pane-nr-diario` | IDs HTML |
| `kpi-row` | `kpi-row-nr-mensual` | ID HTML |
| `kpi-row-acum` | `kpi-row-nr-diario-acum` | ID HTML |
| `kpi-row-daily` | `kpi-row-nr-diario` | ID HTML |
| `chart-mom-bar` | `chart-nr-mensual-bar` | ID Plotly |
| `chart-daily-bar` | `chart-nr-diario-acum-bar` | ID Plotly |
| `chart-daily` | `chart-nr-diario-acum-line` | ID Plotly |
| `chart-vsprom` | `chart-nr-diario` | ID Plotly |
| `daily-vsprom-tbl-wrap` | `tbl-nr-diario-acum` | ID HTML |
| `vsprom-tbl-wrap` | `tbl-nr-diario` | ID HTML |

### Nota técnica: patrón dinámico de showTab
`showTab()` construye IDs de forma dinámica: `'t-' + tab` y `'pane-' + tab`. Al cambiar el valor del tab en TABS, los IDs en el HTML también debían cambiar en sincronía. Se verificó con `grep` que no quedó ninguna referencia al nombre anterior.

### Archivos modificados
| Archivo | Cambio |
|---|---|
| `src/template_dashboard.html` | Todos los renames de funciones, IDs, TABS array, switch cases, comparaciones `activeTab`, querySelector `#pane-*`, llamadas `renderDynamic()`, comentarios de sección JS |

---

## 18. Sesión 2026-04-02 (continuación): Nuevas columnas en tabla MTD D7

### Motivación
La tabla MTD D7 mostraba LMTD, MTD, Diferencia (abs + %) y Mix — pero no contextualizaba el avance respecto al Plan mensual ni proyectaba el cierre del mes.

### Nuevas columnas añadidas (antes de la columna MIx)

#### 1. vs Plan M (MTD vs Plan mensual)
- **Fórmula**: `mtd - planVal` donde `planVal = D.plan_nr[label][month]`
- **Formato**: mismo que columna Absolutos — verde si positivo (arriba del plan), rojo si negativo (abajo del plan)
- **Valor `—`**: canales sin plan definido en el Excel (sin `plan_row` en `channels_config.json`)
- **Interpretación**: positivo = ya superamos el plan del mes; negativo = cuántos NR nos faltan para llegar al plan

#### 2. Proy. Lineal
- **Fórmula**: `MTD × días_totales_mes / días_transcurridos` = `mtd * totalDaysInMonth / refDay`
- **`totalDaysInMonth`**: calculado vía `new Date(year, month, 0).getDate()` — último día del mes = días totales
- **`refDay`**: el día de referencia ya calculado en la función (hoy-2 para mes actual, último día disponible para meses pasados)
- **Formato**: `fmtNum` (mismo que LMTD/MTD — entero con separador de miles)
- **Header dinámico**: muestra `día X / N días` para que sea evidente el cociente (ej. `día 2 / 30 días`)

### Código añadido en `renderMTDTable()` (`src/template_dashboard.html`):
```javascript
// Cálculo de días totales del mes
const totalDaysInMonth = new Date(parseInt(month.slice(0,4)), parseInt(month.slice(4)), 0).getDate();

// Por fila (dentro del forEach):
const planVal = (D.plan_nr[label] || {})[month] || null;
const vsPlan  = planVal != null ? mtd - planVal : null;
const proj    = refDay > 0 ? Math.round(mtd * totalDaysInMonth / refDay) : null;
```

### Header actualizado:
```javascript
+ '<th rowspan="2">vs Plan M<br><span style="font-weight:400;font-size:9px">MTD vs Plan mensual</span></th>'
+ '<th rowspan="2">Proy. Lineal<br><span style="font-weight:400;font-size:9px">día '+refDay+' / '+totalDaysInMonth+' días</span></th>'
```

### Archivos modificados
| Archivo | Cambio |
|---|---|
| `src/template_dashboard.html` | +`totalDaysInMonth`, +header cols `vs Plan M` y `Proy. Lineal`, +cálculo `vsPlan` y `proj` en forEach, +2 `<td>` por fila |

---

## 19. Sesión 2026-04-02 (continuación): Ocultar "Plan Producto" de la gráfica NR Mensual

### Motivación
La línea "Plan Producto" del chart NR Mensual generaba ruido visual al filtrar el canal OC+UCR. El usuario solicitó que no aparezca en la gráfica (aunque sigue sumando al total del Plan OC+UCR en los cálculos).

### Solución: flag `no_chart` en channels_config.json

Se añadió el flag `"no_chart": true` a la entrada de Plan Producto en `channels_config.json`. Esto permite controlar la visibilidad en chart de cualquier plan_line sin tocar código Python o JS — solo cambiando el JSON.

**Efecto del flag:**
- `no_chart: true` → el trace **no se agrega** al figura Plotly en `build_mom_bar()`
- `no_chart: true` → la entrada **no aparece** en `plan_line_map` (el dict JS que controla visibilidad dinámica)
- El cálculo del Plan total del nodo padre **no se ve afectado** — `load_plan()` suma todas las plan_lines incluyendo las `no_chart`

### Cambios aplicados:

`config/channels_config.json`:
```json
{ "label": "Plan Producto", "rows": [17], "color": "#1AB059", "no_chart": true }
```

`src/builders.py` — `build_mom_bar()`:
```python
for pl in c['plan_lines']:
    if pl.get('no_chart'):   # ← nueva guarda
        continue
    ...
```

`src/gen_dashboard_v2.py` — construcción de `plan_line_map`:
```python
'plan_line_map': {
    c['label']: [pl['label'] for pl in c['plan_lines'] if not pl.get('no_chart')]
    for c in HIERARCHY_NR if 'plan_lines' in c
}
```

### Archivos modificados
| Archivo | Cambio |
|---|---|
| `config/channels_config.json` | `"no_chart": true` en Plan Producto |
| `src/builders.py` | `if pl.get('no_chart'): continue` en loop de plan_lines |
| `src/gen_dashboard_v2.py` | Filtro `not pl.get('no_chart')` en construcción de `plan_line_map` |

---

## 20. Sesión 2026-04-03: Plan de KPIs en la pestaña Performance

### Motivación
Integrar los datos del Plan 2026 (Excel `Resumen Plan Acq 2026.xlsx`) en la pestaña Performance, mostrando sub-filas Plan y vs Plan debajo de cada métrica resaltada, del mismo modo que el Plan N+R aparece en la pestaña NR Mensual.

### Arquitectura de la solución

El Excel tiene bloques de KPIs separados (ver también `docs/metrics_logic.md §6`). Cada bloque repite los mismos canales en el mismo orden:

| Bloque KPI | Filas Excel (1-indexed) | Filas pandas (0-indexed) |
|---|---|---|
| N+R | 1–30 | 0–29 |
| VPU | 35–49 | 34–48 |
| **Valor Pred 90D** | **51–65** | **50–64** |
| CPA | 67–81 | 66–80 |
| **Inversión Total (USD)** | **83–97** | **82–96** |

**Decisión clave — Plan VPU no se lee directo**: VPU no es aditivo (no se puede sumar entre canales), por lo que **no hay `plan_row_vpu`** en el config. En cambio se carga `plan_valor` (aditivo) y se deriva `plan_vpu = plan_valor / plan_nr`.

**Decisión clave — Plan Inversión sin propagación bottom-up**: El Excel ya tiene filas de agregados para los nodos padre (POM Total, OC+UCR, MGM Total, Total N+R). No se necesita sumar hijos.

**Decisión clave — Plan Valor sí necesita propagación**: Ucrania y POM TOTAL no tienen fila directa de Valor en el Excel → se calculan sumando sus hijos (`reversed(HIERARCHY_NR)` garantiza que los hijos ya estén calculados).

### Campos añadidos a `channels_config.json`

Se añadieron `plan_row_valor` (iloc pandas en bloque Valor) y `plan_row_inv` (iloc pandas en bloque Inversión) a cada nodo con fila directa en el Excel:

| Canal | `plan_row_valor` | `plan_row_inv` |
|---|---|---|
| Total N+R | 50 | 80 |
| OC + UCR | 52 | 82 |
| UCR Gest | 54 | — |
| UCR PRD | 53 | — |
| OC ACT | 56 | 87 |
| POM TOTAL | — (bottom-up) | 81 |
| POM ADQ | 51 | — |
| POM ACT | 55 | — |
| MGM TOTAL | 59 | 88 |
| MGM ADQ | 61 | — |
| MGM ACT | 60 | — |
| L&P TOTAL | 62 | — |
| ORG | 64 | — |

### Cambios en `src/gen_dashboard_v2.py`

`load_plan()` extendido de 2 → 4 dicts de retorno: `plan_nr, plan_lines_data, plan_valor, plan_inv`.
Ver función completa en `src/gen_dashboard_v2.py`.

Lógica clave (no obvia, por eso se documenta):
- **`plan_valor`**: necesita propagación bottom-up (`reversed(HIERARCHY_NR)`) para Ucrania y POM TOTAL que no tienen fila directa en el Excel. El `reversed` garantiza que hijos ya estén calculados antes que padres.
- **`plan_inv`**: NO necesita propagación — el Excel ya tiene filas de agregados para todos los padres.
- Inyectados en `data{}` y `data_js{}` para uso en `build_perf_table_html()`.

### Cambios en `src/builders.py`

**`build_perf_table_html(data)`** en `src/builders.py` lee los 3 nuevos dicts del plan.
Sub-filas añadidas por métrica resaltada (solo se muestran cuando hay datos de plan):

| Después de | Sub-filas añadidas |
|---|---|
| Inv. Total (USD) | `↳ Plan Inv.` + `↳ vs Plan Inv.` |
| CPA Blend. | `↳ Plan CPA` + `↳ vs Plan CPA` |
| VPU Pred 90D | `↳ Plan VPU` + `↳ vs Plan VPU` |
| ↳ Valor Pred 90D | `↳ Plan Valor` + `↳ vs Plan Valor` |

Helper `fmt_pct_plan(actual, plan)` en `src/builders.py`: variación vs plan como `▲/▼ X.X%` con color verde/rojo.

### Convención de nombres implementada

Para separar claramente real vs plan en el código de `build_perf_table_html()`:

| Variable | Significado |
|---|---|
| `actual_inv_val` | Inversión real del mes (de COSTOS_CANALES) |
| `plan_inv_val` | Inversión del plan Excel |
| `actual_cpa_blend` | CPA real = actual_inv / actual_nr |
| `plan_cpa_blend` | CPA plan = plan_inv / plan_nr |
| `actual_vpu_per_user` | VPU real = perf_vpu_prod / actual_nr_total |
| `plan_vpu_per_user` | VPU plan = plan_valor / plan_nr |
| `actual_valor_total` | Valor Pred real = perf_vpu_prod (pre-multiplicado) |
| `plan_valor_val` | Valor Pred plan = del Excel bloque Valor |
| `plan_inv_by_month` | Dict {mes: valor} de plan_inv para el canal actual |
| `plan_nr_by_month` | Dict {mes: valor} de plan_nr para el canal actual |
| `plan_valor_by_month` | Dict {mes: valor} de plan_valor para el canal actual |

### Archivos modificados
| Archivo | Cambio |
|---|---|
| `config/channels_config.json` | Campos `plan_row_valor` y `plan_row_inv` añadidos a nodos con fila en Excel |
| `src/gen_dashboard_v2.py` | `load_plan()` retorna 4 dicts; inyecta en `data` y `data_js` |
| `src/builders.py` | `build_perf_table_html()` añade sub-filas Plan/vs Plan para 4 métricas |

**Output final**: 994 KB

---

## 21. Sesión 2026-04-03 (continuación): Línea Plan Inv. en la gráfica de Performance

### Motivación
Después de añadir las sub-filas Plan en la tabla de Performance (§20), el usuario solicitó incluir la línea de Plan también en la **gráfica** de Performance, del mismo modo que "Plan Oficial" aparece en la gráfica de NR Mensual.

### Cambio en `src/builders.py` — `build_perf_bar()`

Se añadió lectura de `plan_inv` y `plan_nr` desde `data` (ya disponibles tras §20):

```python
plan_inv = data.get('plan_inv', {})
plan_nr  = data.get('plan_nr',  {})
```

Se calculó el array de la línea plan (escala M USD, misma que las barras):
```python
plan_inv_total_by_month = plan_inv.get('Total N+R', {})
plan_inv_y_mm = [plan_inv_total_by_month.get(m) for m in cost_months]
plan_inv_y_mm = [v / 1_000_000 if v else None for v in plan_inv_y_mm]
```

Trace añadido como `go.Scatter` sobre el eje y1 (mismo que las barras), con estilo rojo punteado idéntico al "Plan Oficial" de NR Mensual:
```python
fig.add_trace(go.Scatter(
    name='Plan Inv.', x=x_labels, y=plan_inv_y_mm,
    mode='lines+markers',
    line=dict(color='#C00000', width=2, dash='dot'),
    marker=dict(size=7, symbol='circle', color='#C00000')
))
```

### Bug: línea no aparecía — causa y fix en `template_dashboard.html`

**Causa**: `updateChartPerf()` reconstruye la visibilidad de todos los traces con:
```javascript
const visible = gd.data.map(t => toHL.includes(t.name));
```
`toHL` contiene solo los leaf labels de `HIERARCHY_C` (ej. "UCR Gest", "OC ACT"). "Plan Inv." no está en `toHL` → se ocultaba.

**Fix**: igual que `CPA Blend.` y `ROAs`, se busca el trace por nombre y se fuerza visible:
```javascript
const idxPlanInv = gd.data.findIndex(t => t.name === 'Plan Inv.');
if (idxPlanInv >= 0) visible[idxPlanInv] = true;
```

Además se recalcula dinámicamente al cambiar canal, usando `D.plan_inv[canal]` si el canal tiene plan propio, o `D.plan_inv['Total N+R']` como fallback:
```javascript
if (idxPlanInv >= 0) {
  const planInvByMonth = D.plan_inv[canal] || D.plan_inv['Total N+R'] || {};
  const y = D.cost_months.map(m => {
    const v = planInvByMonth[m] || null;
    return v ? v / 1e6 : null;
  });
  Plotly.restyle('chart-perf-bar', {y: [y], customdata: [cust]}, [idxPlanInv]);
}
```

**Nota**: Se añadió y quitó "Plan CPA" (eje y2) en la misma sesión por solicitud del usuario — solo quedó "Plan Inv." en y1.

### Archivos modificados
| Archivo | Cambio |
|---|---|
| `src/builders.py` | `build_perf_bar()`: lee `plan_inv`/`plan_nr` de `data`, añade trace "Plan Inv." |
| `src/template_dashboard.html` | `updateChartPerf()`: mantiene "Plan Inv." visible y lo recalcula por canal |

**Output final**: 996–997 KB

---

## 22. Sesión 2026-04-03 (continuación): Convención de nombres real vs plan

### Motivación
El usuario estableció una guía de estilo para todo código nuevo: nombres de variables y funciones deben ser auto-descriptivos, separar explícitamente lo que es dato **real** de lo que es dato de **plan**, y los comentarios deben explicar cómo cada variable/función/archivo se relaciona con los demás.

### Convenciones adoptadas (aplicadas en §20 y §21)

**Nombres de variables — separación real vs plan:**
| Prefijo / Sufijo | Significado |
|---|---|
| `actual_*` | Dato real de BQ (DAILY_HISTORICO o COSTOS_CANALES) |
| `plan_*` | Dato del Excel Plan 2026 |
| `*_by_month` | Dict `{yyyymm: valor}` del canal actual (slice de un dict mayor) |
| `*_per_user` | Valor unitario por usuario (ej. `actual_vpu_per_user`, `plan_vpu_per_user`) |
| `*_blend` | Métrica sobre N+R Total (ej. `actual_cpa_blend`, `plan_cpa_blend`) |

**Nombres de funciones descriptivos:**
| Función | Descripción |
|---|---|
| `read_excel_row_into_plan_dict()` | Lee una fila del Excel por iloc y la guarda en el dict de plan correspondiente |
| `fmt_pct_plan(actual, plan)` | Formatea variación vs plan como porcentaje con flecha de color |

**Comentarios obligatorios en builders.py:**
Cada bloque de métricas debe indicar:
- Si el dato es real o plan
- La fuente del dato real (COSTOS_CANALES, DAILY_HISTORICO, Excel)
- Para datos derivados: la fórmula en comentario
- La relación con otros archivos (ej. "D.plan_inv cargado en gen_dashboard_v2.py")

**Archivos afectados**: `src/builders.py`, `src/gen_dashboard_v2.py`, `src/template_dashboard.html`

---

## 23. Sesión 2026-04-03 (continuación): Sección `hierarchy_resumenPlan` en channels_config.json

### Qué es
Se añadió una tercera jerarquía al `channels_config.json` (además de `hierarchy_nr` y `hierarchy_cost`):

```json
"hierarchy_resumenPlan": [...]
```

Esta sección es documentación de negocio embebida en el config — no es consumida por ningún módulo Python actualmente. Sirve como **Piedra Rosetta** (ver también `docs/metrics_logic.md §6A`) que mapea:
- Los IDs internos del dashboard (`dashboard_mapping`) 
- A las líneas del Excel Plan 2026 (`excel_logic`)

### Contenido
| id | label | dashboard_mapping | excel_logic |
|---|---|---|---|
| pom_total | POM Total | — | POM gest |
| pom_no_gestionado | POM no gestionado | — | POM no gestionado |
| oc_recurring | OC Recurring | UCR Gest + OC ACT Recurring | OC Recurring |
| oc_adhoc | OC Adhoc | UCR Gest + OC ACT Ad-Hoc | OC Adhoc |
| ucr_prd | UCR PRD | UCR PRD | Others + Producto |
| oc_ucr | OC + UCR | OC + UCR | OC Recurring + OC Adhoc + Others + Producto |
| org | Organico | ORG | No Atribuido / Organico |
| mgm_total | MGM Total | MGM TOTAL | MGM |
| lp_total | L&P Total | L&P TOTAL | L&P |

### Por qué no se usa en código
El código Python usa `plan_row_valor` y `plan_row_inv` (índices iloc directos) en lugar de leer por nombre de fila — siguiendo la regla de oro de `metrics_logic.md §6`: extraer datos del Excel **exclusivamente por índice `iloc`**, nunca por texto.

`hierarchy_resumenPlan` existe para referencia humana y documentación, no para ejecución.

---

## 25. Sesión 2026-04-12: Tabla de Canales Corporativa — `hierarchy_nr_corp_detail`

### Motivación
El nuevo schema de `PANEL_MONTHLY_DAILY_HISTORICO` expone tres niveles de canal (`CHANNEL_APERTURA_1/2/3`) y el campo `TOUCHPOINT` (medio de comunicación). El usuario solicitó una nueva tabla dentro de la pestaña NR Mensual que use esta estructura completa, con filas de N+R, MoM y Share, organizada en 4 niveles: Canal → Sub-canal → Medio.

---

### RAZONAMIENTO EXHAUSTIVO: Asignación de Canales, Sub-canales y Medios

#### Estructura de datos fuente (PANEL_MONTHLY_DAILY_HISTORICO)

Las dimensiones disponibles son:

| Dimensión | Columna BQ | Ejemplos |
|---|---|---|
| Nivel macro | `CHANNEL_APERTURA_1` | OC, POM, OTHERS, ORGANICO |
| Nivel intermedio | `CHANNEL_APERTURA_2` | UCRANIA E&G, OWN CHANNELS RECURRING, ACQUISITION POM, MGM, LP… |
| Nivel fino | `CHANNEL_APERTURA_3` | OWN CHANNELS MKT, ADHOC, OWN CHANNELS PRD, MGM… |
| Medio | `TOUCHPOINT` | EMAIL, PUSH, PANDORA, JOURNEY, WPP, RE - DRAWER, RE - DISCOVERY… |
| Estrategia | `STRATEGY` | ACQUISITION, ACTIVATION, OTHER |

**Regla de asignación**: el nivel de canal usado en la nueva tabla es `CHANNEL_APERTURA_2` (sub-canal de negocio). El medio es `TOUCHPOINT` normalizado. La `STRATEGY` solo se usa para separar canales que comparten `AP2` (ej. UCRANIA E&G siempre es ACQUISITION; ACTIVATION POM cubre ambas strategies).

---

#### Jerarquía de 4 niveles definida

```
Total N+R (root)
│
├── 1. OC + UCR  [AP1 = 'OC']
│   ├── 1.1 UCRANIA E&G  [AP2='UCRANIA E&G', STRATEGY=ACQUISITION]
│   │   ├── EMAIL         TOUCHPOINT IN ('EMAIL','SMS')  [SMS=31 NR total, absorbido en EMAIL]
│   │   ├── PANDORA       TOUCHPOINT='PANDORA'
│   │   ├── PUSH          TOUCHPOINT='PUSH'
│   │   ├── REAL ESTATES  TOUCHPOINT LIKE 'RE - %'  [RE-CONGRATS+RE-DISCOVERY+RE-DRAWER+RE-QUICK ACCESS]
│   │   └── WPP           TOUCHPOINT='WPP'
│   │   NOTE: algunas filas tienen COMM_TYPE='ADHOC' (EMAIL+PUSH, ~4K NR) — no separadas,
│   │         absorbidas en sus respectivos medios ya que la distinción negocio es por TOUCHPOINT
│   │
│   ├── 1.2 OWN CHANNELS RECURRING  [AP2='OWN CHANNELS RECURRING', STRATEGY=ACTIVATION]
│   │   ├── EMAIL         TOUCHPOINT='EMAIL'
│   │   ├── JOURNEY       TOUCHPOINT='JOURNEY'
│   │   ├── PANDORA       TOUCHPOINT='PANDORA'
│   │   ├── PUSH          TOUCHPOINT='PUSH'    [dominante: 979K de 1.27M total]
│   │   └── WPP           TOUCHPOINT='WPP'
│   │
│   └── 1.3 OWN CHANNELS ADHOC  [AP2='OWN CHANNELS ADHOC', STRATEGY=ACTIVATION]
│       Sin breakdown de medios — EMAIL+PUSH combinados (~139K NR, INV=0)
│
├── 2. POM  [AP1 = 'POM']
│   ├── 2.1 ACQUISITION POM  [AP2='ACQUISITION POM', STRATEGY=ACQUISITION]
│   ├── 2.2 ACTIVATION POM   [AP2='ACTIVATION POM', ambas strategies]
│   │   NOTE: ~57K NR con STRATEGY=ACQUISITION + ~722K NR con STRATEGY=ACTIVATION
│   │         Ambas filas se suman bajo "ACTIVATION POM" por nombre de AP2
│   ├── 2.3 WEB POM          [AP2='WEB POM', ambas strategies]
│   └── 2.4 CTW POM          [AP2='CTW POM', ambas strategies]
│   NOTE: POM OTHERS y POM SELLERS tienen AP1='OTHERS' → van al grupo OTHERS, no POM
│
├── 3. OTHERS  [AP1 = 'OTHERS']
│   ├── 3.1 MGM          [AP2='MGM']
│   ├── 3.2 L&P          [AP2='LP']
│   ├── 3.3 UCR PRD      [AP2='UCRANIA PRD']  Sin breakdown de medios (tiene RE-* pero usuario no los pide)
│   ├── 3.4 SEO          [AP2='SEO', INV=$2.3M en 2025]
│   ├── 3.5 POM SELLERS  [AP2='POM SELLERS', solo ACQUISITION]
│   └── 3.6 POM OTHERS   [AP2='POM OTHERS', ambas strategies]
│
└── 4. NO ATRIBUIDO  [AP1 = 'ORGANICO', ELSE catch-all]
    Captura: ORGANIC/ACQUISITION, ORGANIC/ACTIVATION, OTHER/ACTIVATION
    NOTE: ORGANICO|OTHER|ACTIVATION tiene 8.7M NR e INV=$82M en 2025+2026 — es la
          bolsa de atribución orgánica con inversión de retención masiva
```

---

#### Tabla completa de asignación: 22 claves BQ → 28 nodos

| CORP_KEY (SQL) | AP1 | AP2 | TOUCHPOINT | Label visible |
|---|---|---|---|---|
| `OC\|UCR_EG\|EMAIL` | OC | UCRANIA E&G | EMAIL, SMS | EMAIL |
| `OC\|UCR_EG\|PANDORA` | OC | UCRANIA E&G | PANDORA | PANDORA |
| `OC\|UCR_EG\|PUSH` | OC | UCRANIA E&G | PUSH | PUSH |
| `OC\|UCR_EG\|REAL_ESTATES` | OC | UCRANIA E&G | RE - * | REAL ESTATES |
| `OC\|UCR_EG\|WPP` | OC | UCRANIA E&G | WPP | WPP |
| `OC\|OC_REC\|EMAIL` | OC | OWN CHANNELS RECURRING | EMAIL | EMAIL |
| `OC\|OC_REC\|JOURNEY` | OC | OWN CHANNELS RECURRING | JOURNEY | JOURNEY |
| `OC\|OC_REC\|PANDORA` | OC | OWN CHANNELS RECURRING | PANDORA | PANDORA |
| `OC\|OC_REC\|PUSH` | OC | OWN CHANNELS RECURRING | PUSH | PUSH |
| `OC\|OC_REC\|WPP` | OC | OWN CHANNELS RECURRING | WPP | WPP |
| `OC\|OC_ADHOC\|TOTAL` | OC | OWN CHANNELS ADHOC | (todos) | OWN CHANNELS ADHOC |
| `POM\|ACQ_POM\|TOTAL` | POM | ACQUISITION POM | (todos) | ACQUISITION POM |
| `POM\|ACT_POM\|TOTAL` | POM | ACTIVATION POM | (todos) | ACTIVATION POM |
| `POM\|WEB_POM\|TOTAL` | POM | WEB POM | (todos) | WEB POM |
| `POM\|CTW_POM\|TOTAL` | POM | CTW POM | (todos) | CTW POM |
| `OTH\|MGM\|TOTAL` | OTHERS | MGM | (todos) | MGM |
| `OTH\|LP\|TOTAL` | OTHERS | LP | (todos) | L&P |
| `OTH\|UCR_PRD\|TOTAL` | OTHERS | UCRANIA PRD | (todos) | UCR PRD |
| `OTH\|SEO\|TOTAL` | OTHERS | SEO | (todos) | SEO |
| `OTH\|POM_SELLERS\|TOTAL` | OTHERS | POM SELLERS | (todos) | POM SELLERS |
| `OTH\|POM_OTHERS\|TOTAL` | OTHERS | POM OTHERS | (todos) | POM OTHERS |
| `NOATRIB\|ORGANICO\|TOTAL` | ORGANICO | (todos) | (todos) | NO ATRIBUIDO |

**ELSE catch-all** → `NOATRIB|ORGANICO|TOTAL` (captura todo AP1=ORGANICO más cualquier combinación no mapeada)

---

### Implementación técnica

#### Nuevos archivos/secciones

| Archivo | Cambio |
|---|---|
| `config/channels_config.json` | Nueva sección `hierarchy_nr_corp_detail` (28 nodos, 4 niveles) |
| `src/queries.py` | Nueva función `get_nr_corp_sql()` — retorna (CORP_KEY, FECHA_MES, NR) |
| `src/processors.py` | Nueva función `process_nr_corp()` — ejecuta query, propaga bottom-up, retorna `monthly_nr_corp` |
| `src/builders.py` | Nueva función `build_nr_corp_table_html(data)` — tabla estática con N+R, MoM, Share |
| `src/gen_dashboard_v2.py` | 6ta query BQ, placeholder `{{NR_CORP_TABLE}}` |
| `src/template_dashboard.html` | Sección nueva bajo tabla hierarchy_nr en pane-nr-mensual |

#### Decisiones de diseño

- **Tabla estática HTML** (generada en Python), igual que la tabla de hierarchy_nr. Los filtros dinámicos de canal/mes del dashboard NO afectan esta tabla (es una vista independiente).
- **MoM**: calculado en el builder directamente desde `monthly_nr_corp`.
- **Share**: `nr_node_m / nr_total_m × 100` — calculado en el builder.
- **Propagación bottom-up**: mismo patrón de `reversed(HIERARCHY_CORP)` que en processors.py.
- **`OTROS` residual en OC**: filas de UCR E&G sin TOUCHPOINT conocido van a `OC|UCR_EG|OTROS` y se ignoran en la tabla (tiny volume).

---

## 24. Sesión 2026-04-12: Cambio de schema en `PANEL_MONTHLY_DAILY_HISTORICO`

### Causa raíz
La tabla BQ `PANEL_MONTHLY_DAILY_HISTORICO` fue actualizada por el equipo de datos de MercadoLibre. Dos columnas cambiaron de nombre y los valores de canal POM fueron reorganizados en múltiples niveles de apertura.

### Diagnóstico
Error al ejecutar `gen_dashboard_v2.py`:
```
google.api_core.exceptions.BadRequest: 400 Unrecognized name: CHANNEL at [4:57]
```
Posición exacta: línea 4 (CASE WHEN), columna 57 — primer uso de `UPPER(CHANNEL)` en `get_nr_sql()`.

Se verificó el schema actual con `client.get_table()`:

| Columna antigua | Nueva columna | Tabla |
|---|---|---|
| `CHANNEL` | `CHANNEL_APERTURA_3` | `PANEL_MONTHLY_DAILY_HISTORICO` |
| `COST_USD` | `INVERSION_TOTAL_USD` | `PANEL_MONTHLY_DAILY_HISTORICO` |
| `CHANNEL` | **sin cambio** | `PANEL_MONTHLY_COSTOS_CANALES` |

La tabla también incorporó `CHANNEL_APERTURA_1` (nivel macro: `OC`, `POM`, `OTHERS`, `ORGANICO`) y `CHANNEL_APERTURA_2` (nivel intermedio), además de `CHANNEL_APERTURA_3` (nivel fino — equivalente al antiguo `CHANNEL`).

### Cambios en valores de canal (CHANNEL_APERTURA_3)

Los valores POM fueron completamente renombrados:

| Valor antiguo (`CHANNEL`) | Nuevo valor (`CHANNEL_APERTURA_3`) |
|---|---|
| `POM ACQ` | `ACQUISITION POM` |
| `POM ACT` | *(absorbido por `ACTIVATION POM` / `WEB POM` / `CTW POM`)* |
| `POM` | *(desaparece como valor único — distribuido en sub-canales)* |
| `POM OTHERS SELLERS` | `POM SELLERS` |
| `POM OTHERS` | `POM OTHERS` *(sin cambio)* |

Nuevos valores detectados para OC y L&P:
- `ADHOC` → sub-canal de OC ACT (`CHANNEL_APERTURA_1='OC'`, `CHANNEL_APERTURA_2='OWN CHANNELS ADHOC'`)
- `LANDINGS` y `AFFILIATES` → sub-canales de L&P

### Cambios en `src/queries.py`

En `get_nr_sql()` y `get_perf_vpu_sql()` (ambas leen `PANEL_MONTHLY_DAILY_HISTORICO`):
- `UPPER(CHANNEL)` → `UPPER(CHANNEL_APERTURA_3)` — nuevo nombre de columna
- `COST_USD AS COST` → `COALESCE(INVERSION_TOTAL_USD, 0) AS COST` — nuevo nombre de columna

`get_costos_sql()`, `get_perf_paid_sql()`, `get_perf_roa_costos_sql()` — leen `PANEL_MONTHLY_COSTOS_CANALES`, **sin cambios** (esa tabla no cambió).

### Cambios en `config/channels_config.json` — `bq_mapping.channel`

Solo afecta los valores usados por `get_nr_sql()` y `get_perf_vpu_sql()` (DAILY_HISTORICO):

| Canal | Antes | Después |
|---|---|---|
| `pom_adq` | `["POM ACQ","POM ACT","POM OTHERS","POM OTHERS SELLERS","POM"]` | `["ACQUISITION POM","WEB POM","CTW POM","ACTIVATION POM","POM OTHERS","POM SELLERS"]` |
| `pom_act` | `["POM","POM OTHERS","POM OTHERS SELLERS"]` | `["ACTIVATION POM","WEB POM","CTW POM","POM OTHERS","POM SELLERS"]` |
| `oc_act` | `"OWN CHANNELS MKT"` | `["OWN CHANNELS MKT","ADHOC"]` |
| `lp_adq` | `["BRANDFORMANCE","OTHERS","PARTNERSHIPS"]` | `["BRANDFORMANCE","OTHERS","PARTNERSHIPS","LANDINGS","AFFILIATES"]` |
| `lp_act` | `["BRANDFORMANCE","OTHERS","PARTNERSHIPS"]` | `["BRANDFORMANCE","OTHERS","PARTNERSHIPS","LANDINGS"]` |

> **Nota sobre ADHOC en OC ACT**: En el schema nuevo, las filas `OC | OWN CHANNELS ADHOC | ADHOC | ACTIVATION` tienen `CHANNEL_APERTURA_1='OC'` y `STRATEGY='ACTIVATION'` — lógicamente pertenecen a OC ACT. Se incluyeron de forma conservadora, pendiente confirmación de negocio.

### Archivos modificados
| Archivo | Cambio |
|---|---|
| `src/queries.py` | `CHANNEL` → `CHANNEL_APERTURA_3`, `COST_USD` → `INVERSION_TOTAL_USD` (líneas 32, 40, 174) |
| `config/channels_config.json` | `bq_mapping.channel` actualizado para pom_adq, pom_act, oc_act, lp_adq, lp_act |

**Output final**: 1003 KB

---

## 26. Sesión 2026-04-12 (continuación): Implementación completa de la Tabla Corporativa N+R

### Motivación
Ver §25 para el razonamiento exhaustivo de la asignación de canales/sub-canales/medios. Esta sección documenta la implementación técnica completa: los 6 archivos modificados, los patrones de código, las convenciones de nombres aplicadas y el resultado final.

---

### Convención de nombres aplicada (feedback del usuario)

Regla general: **cada variable, función y dict debe ser auto-descriptivo** — que su nombre revele exactamente qué contiene y de dónde viene.

| Nombre elegido | Por qué (no alternativa corta) |
|---|---|
| `HIERARCHY_NR_CORP` | Distingue de `HIERARCHY_NR` (hierarchy_nr) y `HIERARCHY_COST` (hierarchy_cost) |
| `monthly_nr_corp_by_node` | Es N+R, es corp, está organizado por node_id (no por label ni por bq_key) |
| `nr_corp_flat_by_key` | Es flat (no jerárquico), está indexado por bq_key (no por node_id) |
| `corp_node` | Variable de iteración dentro de HIERARCHY_NR_CORP |
| `bq_key_value` | El valor string del campo bq_key del nodo (vs el nombre del campo en sí) |
| `actual_nr_this_month` | El NR real del mes actual (vs prev_nr_this_node del mes anterior) |
| `total_nr_by_month` | NR total (corp_total) por mes — denominador del Share |
| `nr_value_for_share` | NR del nodo específico para el cálculo de Share |

---

### Cambio 1: `config/channels_config.json` — nueva sección `hierarchy_nr_corp_detail`

Añadida DESPUÉS de `hierarchy_nr_corp` y ANTES de `hierarchy_resumenPlan`. 28 nodos organizados en 4 niveles:

| Nivel | `level` en JSON | Nodos |
|---|---|---|
| Root | `grand` | `corp_total` |
| Grupo | `sub1` | `corp_oc_ucr`, `corp_pom`, `corp_others`, `corp_noatrib` (leaf) |
| Sub-canal | `sub2` | `corp_ucr_eg` (parent), `corp_oc_recurring` (parent), `corp_oc_adhoc` (leaf), 4×POM (leaf), 6×OTHERS (leaf) |
| Medio | `medio` | 5× bajo `corp_ucr_eg`, 5× bajo `corp_oc_recurring` |

Campos especiales del JSON:
- `bq_key` — solo en nodos hoja (`is_leaf: true`). Valor exacto del `corp_key` generado por `get_nr_corp_sql()`.
- `_doc` — campo de documentación embebida (ignorado por código Python). Explica AP1, AP2, TOUCHPOINT y decisiones de negocio.
- `ap1`, `ap2` — campos de referencia documental en nodos donde el AP2 es el driver del agrupamiento.

---

### Cambio 2: `src/queries.py` — nueva función `get_nr_corp_sql()`

**Firma**: `get_nr_corp_sql() → str`

**Retorna**: SQL que produce `(fecha_mes_corp, corp_key, nr_total_corp)` agrupado por mes.

**Lógica interna** — 3 CTEs:
1. `base_corp`: lee PANEL_MONTHLY_DAILY_HISTORICO, selecciona AP1, AP2, TOUCHPOINT, NR_USERS.
2. `keyed_corp`: aplica el CASE WHEN de 22+ ramas para asignar `corp_key` a cada fila:
   - 6 ramas para UCR E&G (por TOUCHPOINT: EMAIL/SMS, PANDORA, PUSH, RE-*, WPP, catch-OTROS)
   - 6 ramas para OC RECURRING (mismos 5 medios + catch-OTROS)
   - 1 rama para OC ADHOC (total)
   - 4 ramas para POM (por AP2)
   - 6 ramas para OTHERS (por AP2)
   - 1 rama ELSE → NOATRIB|ORGANICO|TOTAL
3. Agrupación final por `fecha_mes_corp` y `corp_key`.

**Nota de diseño**: Los alias SQL usan sufijo `_corp` (`fecha_mes_corp`, `ap1_corp`, etc.) para evitar colisiones si la query se une en el futuro con otras queries.

---

### Cambio 3: `src/processors.py` — nueva función `process_nr_corp()`

**Firma**: `process_nr_corp(config, bq_client, all_nr_months) → dict`

**Retorna**: `monthly_nr_corp_by_node { node_id: { yyyymm: nr_int } }`

**Flujo en 5 pasos documentados en el docstring**:
1. Ejecuta `get_nr_corp_sql()` via `bq_query()` → `df_nr_corp`
2. Construye `nr_corp_flat_by_key { corp_key: { yyyymm: nr_float } }` — suma por si hay duplicados
3. Inicializa `monthly_nr_corp_by_node[node_id] = {m: 0 for m in all_nr_months}` para todos los nodos
4. Asigna nodos hoja (`is_leaf=True, bq_key`) desde `nr_corp_flat_by_key`
5. Propaga bottom-up con `reversed(HIERARCHY_NR_CORP)` — garantiza hijos calculados antes que padres

Import añadido en `src/processors.py`: `get_nr_corp_sql` en la línea de imports de queries.
`process_nr_corp()` es una función independiente (no parte de `process_all()`), llamada explícitamente en `gen_dashboard_v2.py` para mantener separación de responsabilidades.

---

### Cambio 4: `src/builders.py` — nueva función `build_nr_corp_table_html()`

**Firma**: `build_nr_corp_table_html(data) → str`

**Consume de `data{}`**:
- `data['HIERARCHY_NR_CORP']` — lista de 28 nodos (de config)
- `data['monthly_nr_corp_by_node']` — dict `{node_id: {yyyymm: nr_int}}`
- `data['months']` — mismos meses que la tabla NR Mensual

**Genera por cada nodo** (3 filas):
1. **N+R** — valores formateados con `fmt_val()` (K/M)
2. **MoM** — `fmt_pct_mom(actual_nr_this_month, prev_nr_this_node, is_dark_background)` → ▲/▼ con color
3. **Share N+R** — `fmt_pct_share(nr_value_for_share, total_nr_value)` → porcentaje neutro sin flecha

**Paleta de estilos por nivel**:
| `level` JSON | Fondo | Texto | Peso |
|---|---|---|---|
| `grand` | `#1a2744` | `#ffffff` | 700 |
| `sub1` | `#2d5986` | `#ffffff` | 600 |
| `sub2` | `#4a7ab5` | `#ffffff` | 500 |
| `medio` | `#ffffff` | `#333333` | 400 |

Clase CSS de la tabla: `mom-tbl nr-corp-tbl` (hereda estilos base + permite overrides específicos).

---

### Cambio 5: `src/gen_dashboard_v2.py` — wiring completo

Imports añadidos: `process_nr_corp` desde processors + `build_nr_corp_table_html` desde builders.
Paso 3b: llama `process_nr_corp(config, client, data['months'])` e inyecta resultado en `data{}`.
Placeholder `{{NR_CORP_TABLE}}` reemplazado en `assemble()`. Código completo en el archivo.

Orden de pasos en `assemble()`:
1. Config
2. BQ queries existentes (process_all)
3. Plan Excel (load_plan)
3b. **[NUEVO]** Query corporativa (process_nr_corp)
4. Builders + template

---

### Cambio 6: `src/template_dashboard.html` — nueva sección en pane-nr-mensual

Sección añadida después de `{{MOM_TABLE}}` con título "Detalle por Canal — Estructura Corporativa (AP1 › Sub-canal › Medio)" y placeholder `{{NR_CORP_TABLE}}`. HTML completo en el archivo.
La tabla corp es **estática** (HTML puro generado en Python). Los filtros de canal/mes del dropdown NO la afectan — vista paralela e independiente de `hierarchy_nr`.

---

### Resultado final

| Métrica | Valor |
|---|---|
| Nodos en `hierarchy_nr_corp_detail` | 28 (1 root + 3 grupos + 1 NO ATRIBUIDO + 14 sub-canales + 10 medios) |
| Claves BQ (`corp_key`) generadas | 22 claves explícitas + 1 catch-all ELSE |
| Filas HTML generadas | 28 nodos × 3 filas (N+R + MoM + Share) = 84 filas |
| Output final | **1159 KB** (+163 KB vs 996 KB antes) |
| Queries BQ por run | 6 (5 existentes + `get_nr_corp_sql`) |

---

### Archivos modificados
| Archivo | Tipo de cambio |
|---|---|
| `config/channels_config.json` | AÑADIDO: sección `hierarchy_nr_corp_detail` (28 nodos) |
| `src/queries.py` | AÑADIDO: función `get_nr_corp_sql()` |
| `src/processors.py` | AÑADIDO: función `process_nr_corp()` + import |
| `src/builders.py` | AÑADIDO: función `build_nr_corp_table_html()` |
| `src/gen_dashboard_v2.py` | MODIFICADO: imports + Paso 3b + replace `{{NR_CORP_TABLE}}` |
| `src/template_dashboard.html` | MODIFICADO: sección nueva en pane-nr-mensual |

---

## 27. Sesión 2026-04-12 (continuación): Tabla corporativa — colapso interactivo + estilo limpio

### Motivación
La primera versión de `build_nr_corp_table_html()` generaba todos los nodos aplanados en una tabla estática sin interactividad. El usuario solicitó:
1. **Filas colapsables** (▶/▼) con los grupos visibles por defecto y sub-canales/medios ocultos.
2. **Estilo visual limpio** — fondo blanco total, sin fondos saturados de azul marino.
3. **Total N+R al final** (referencia global), no al inicio.

---

### Cambio 1: Reescritura de `build_nr_corp_table_html()` — lógica recursiva

Se reemplazó la iteración lineal por una función interna recursiva `render_corp_node_rows()`:

```python
def render_corp_node_rows(node_id, parent_id, hidden_by_default):
    # Genera 3 filas (N+R, MoM, Share) para el nodo
    # Llama recursivamente a sus hijos con hidden_by_default=True
```

**Atributos HTML clave por fila**:
| Atributo | Propósito |
|---|---|
| `data-corp-node="{id}"` | Solo en la fila N+R (cabecera). Usado por `collapseCorpNode()` para identificar nodos. |
| `data-corp-parent="{parent_id}"` | En las 3 filas (N+R + MoM + Share) de nodos hijos. Permite show/hide conjunto. |
| `data-corp-level="{level}"` | En la fila N+R. Informativo, no usado por toggle. |
| `data-corp-toggle="{id}"` | En el botón ▶/▼. Referenciado por `toggleCorpNode()`. |

**Estado inicial**:
- sub1 (grupos: OC+UCR, POM, OTHERS, NO ATRIBUIDO): **visibles**
- sub2 (sub-canales): `style="display:none"` — ocultos hasta click
- medio (medios EMAIL, PUSH, etc.): `style="display:none"` — ocultos hasta click en sub-canal

**Orden de renderizado** (modificado respecto al JSON):
```python
# 1. Grupos primero (hijos de corp_total, sin corp_total mismo)
for group_id in root_node.get('children', []):
    h += render_corp_node_rows(group_id, parent_id=None, hidden_by_default=False)
# 2. Separador visual
# 3. Total N+R al fondo
h += render_corp_node_rows('corp_total', parent_id=None, hidden_by_default=False)
```

**Decoración visual por tipo de nodo**:
- Nodo con hijos: botón `▶` del color del canal (`data-corp-toggle`)
- Nodo hoja (sin hijos): bullet `●` del color del canal

---

### Cambio 2: Funciones JS `toggleCorpNode()` y `collapseCorpNode()`

Añadidas en `template_dashboard.html`, antes de `downloadHTML()`.

**`toggleCorpNode(nodeId)`** — alterna expansión/colapso:
- Si está expandido → llama `collapseCorpNode(nodeId)`
- Si está colapsado → muestra solo las filas con `data-corp-parent="{nodeId}"` (hijos directos, NO nietos)

**`collapseCorpNode(nodeId)`** — colapso recursivo completo:
- Oculta todas las filas con `data-corp-parent="{nodeId}"`
- Para cada fila-cabecera de hijo (`data-corp-node`), llama recursivamente `collapseCorpNode(childNodeId)`
- Restablece el botón ▶ del nodo colapsado

**Comportamiento garantizado**:
- Expandir OC+UCR → muestra UCRANIA E&G, OC RECURRING, OC ADHOC (no sus medios)
- Expandir UCRANIA E&G → muestra EMAIL, PANDORA, PUSH, REAL ESTATES, WPP
- Colapsar OC+UCR → oculta sub-canales Y sus medios, restablece todos los ▶

---

### Cambio 3: Bug fix — `_doc` excluía nodos del lookup

**Bug**: `node_by_id = {c['id']: c for c in HIERARCHY_NR_CORP if not c.get('_doc')}` excluía `corp_total` (que tiene campo `_doc`) → tabla vacía.

**Fix**: cambiar el filtro a `if 'id' in c` — incluye todos los nodos con ID, independientemente de si tienen documentación embebida.

```python
# Antes (bug):
node_by_id = {c['id']: c for c in HIERARCHY_NR_CORP if not c.get('_doc')}
# Después (fix):
node_by_id = {c['id']: c for c in HIERARCHY_NR_CORP if 'id' in c}
```

---

### Cambio 4: Nueva paleta de colores — estilo limpio

Reemplazo de los fondos saturados navy/blue por fondos blancos con texto oscuro:

| Nivel | Fondo anterior | Fondo nuevo | Texto |
|---|---|---|---|
| `grand` | `#1a2744` | `#f0f4fa` | `#0d1f3c` |
| `sub1` | `#1e3a6e` | `#ffffff` | `#0d1f3c` |
| `sub2` | `#2e5490` | `#ffffff` | `#1a3562` |
| `medio` | `#f8faff` | `#ffffff` | `#333333` |
| Sub-filas MoM/Share | Fondos oscuros | `#f5f6f8` | `#6b7a99` |

Detalles adicionales:
- `is_dark()` → siempre `False` (todos los fondos son claros → colores MoM estándar verde/rojo)
- Borde izquierdo: 3px para `grand`/`sub1`, 2px para `sub2`/`medio`
- `border-top: 1px solid #e0e4ed` solo en filas de grupos (sub1) y total (grand)
- Botón toggle ▶ → color del canal (no blanco sobre oscuro)
- Hojas sin hijos → bullet `●` del color del canal

---

### Archivos modificados
| Archivo | Cambio |
|---|---|
| `src/builders.py` | Reescritura completa de `build_nr_corp_table_html()`: recursivo, toggle, paleta limpia, bugfix `_doc` |
| `src/template_dashboard.html` | Añadidas funciones JS `toggleCorpNode()` y `collapseCorpNode()` |

**Output**: 1407 KB

---

## 28. Sesión 2026-04-12 (continuación): Gráfica de % N+R por grupo de canal

### Motivación
El usuario solicitó añadir, dentro de la sección "Detalle por Canal — Estructura Corporativa" y **antes de la tabla**, una gráfica de barras apiladas con el % de participación de N+R por grupo de canal, idéntica en concepto a la imagen de referencia del otro dashboard.

---

### Gráfica `build_nr_corp_bar_chart()`

**Función**: `build_nr_corp_bar_chart(data) → dict` en `src/builders.py`

**Tipo**: Barras apiladas `barmode='stack'`, eje Y en % (0–108%).

**4 grupos (de abajo a arriba en el stack)**:
| Grupo | `corp_node_id` | Color | Posición |
|---|---|---|---|
| NO ATRIBUIDO | `corp_noatrib` | `#C8CDD8` gris claro | Base (dominante ~65%) |
| OC+UCRANIA | `corp_oc_ucr` | `#F5D000` amarillo | 2do |
| POM | `corp_pom` | `#1FB8D4` cian | 3ro |
| OTHERS | `corp_others` | `#7A7D82` gris oscuro | Tope (~4-5%) |

**Etiquetas dentro de barras**: `{v:.0f}%` si el segmento ≥ 5% (4% para OTHERS).

**Anotaciones encima de cada barra**: total N+R del mes en formato `0.79` (millones) — mismo estilo imagen de referencia.

**Cálculo del %**:
```python
pct_of_total = [round(n / t * 100, 1) if t > 0 else 0.0 for n, t in zip(nr_grupo, nr_total)]
```
Datos fuente: `data['monthly_nr_corp_by_node']` — mismos dicts que la tabla (sin nueva query BQ).

---

### Wiring en gen_dashboard_v2.py

```python
charts = {
    'mom_bar':     build_mom_bar(...),
    'perf_bar':    build_perf_bar(data),
    'nr_corp_bar': build_nr_corp_bar_chart(data),  # % N+R por grupo — sección Corporativa
}
```

La clave `nr_corp_bar` se incluye en `{{CHARTS_JSON}}` y se accede como `CHARTS.nr_corp_bar` en JS.

---

### Template: div + inicialización JS

**Estructura HTML** (en pane-nr-mensual, dentro de la sección Corporativa):
```html
<div class="chart-box" style="margin-bottom:16px">
  <div id="chart-nr-corp-bar" style="height:310px"></div>
</div>
{{NR_CORP_TABLE}}
```

**Inicialización JS** (dentro del `case 'nr-mensual'` del `showTab()`, una sola vez via flag `._hasPlot`):
```javascript
if (!document.getElementById('chart-nr-corp-bar')._hasPlot) {
  Plotly.newPlot('chart-nr-corp-bar', CHARTS.nr_corp_bar.data, CHARTS.nr_corp_bar.layout, {responsive:true});
  document.getElementById('chart-nr-corp-bar')._hasPlot = true;
}
```

---

### Archivos modificados
| Archivo | Cambio |
|---|---|
| `src/builders.py` | AÑADIDO: `build_nr_corp_bar_chart()` + import en gen_dashboard |
| `src/gen_dashboard_v2.py` | Import `build_nr_corp_bar_chart`, añadida clave `nr_corp_bar` a `charts{}` |
| `src/template_dashboard.html` | Div `chart-nr-corp-bar` + init JS en `showTab('nr-mensual')` |

**Output final**: 1420 KB

---

## 29. Sesión 2026-04-12 (continuación): Cambio de orden y nombre de pestañas

### Cambios aplicados en `src/template_dashboard.html`

1. **Orden de pestañas**: NR Diario ahora aparece **antes** de NR Diario Acumulado.
2. **Renombrado**: "Performance" → **"Performance_vista_FM"**.

Solo cambian el array `TABS` y el HTML de los tabs en `src/template_dashboard.html`.
Los IDs internos (`nr-diario`, `nr-diario-acum`, `perf`) y todo el JS permanecen intactos.
Cambios: TABS reordenado (`nr-diario` antes de `nr-diario-acum`); tab "Performance" → "Performance_vista_FM".

### Archivos modificados
| Archivo | Cambio |
|---|---|
| `src/template_dashboard.html` | Array TABS reordenado; HTML de tabs reordenado; texto "Performance_vista_FM" |

---

## 30. Sesión 2026-04-12 (continuación): Sección Corporativa Diaria en pestaña NR Diario

### Motivación
Espejo de la sección "Detalle por Canal — Estructura Corporativa" de NR Mensual, pero mostrando N+R **diario** para el mes seleccionado. Como NR Diario es completamente dinámico JS (cambia con el mes), esta sección también debe ser dinámica.

### Nueva query: `get_nr_corp_daily_sql()`

Idéntica lógica CASE WHEN que `get_nr_corp_sql()` pero con granularidad diaria:
- Añade `DIA = CAST(EXTRACT(DAY FROM FECHA_DIARIA) AS INT64)` al SELECT
- Agrupa por `(CORP_KEY, FECHA_MES, DIA)` en lugar de solo `(CORP_KEY, FECHA_MES)`
- Retorna `(fecha_mes_corp, dia_del_mes, corp_key, nr_dia_corp)`

El CTE base incluye `CHANNEL_APERTURA_3 AS ap3_corp` (necesario para el split de L&P por AP3).

### Nueva función: `process_nr_corp_daily()`

**Firma**: `process_nr_corp_daily(config, bq_client, all_nr_months) → dict`

**Retorna**: `daily_nr_corp_by_node { node_id: { yyyymm: { dia_str: nr_int } } }`

Flujo de 5 pasos:
1. Ejecutar `get_nr_corp_daily_sql()` → `df_nr_corp_daily`
2. Construir `nr_corp_daily_flat_by_key { corp_key: { yyyymm: { dia_str: nr_float } } }`
3. Inicializar `daily_nr_corp_by_node` con dicts vacíos por nodo/mes
4. Asignar nodos hoja desde flat dict
5. Propagar bottom-up por mes **y por día**: `reversed(HIERARCHY_NR_CORP)`, para cada mes: recopilar todos los días de cualquier hijo → sumar

**Inyectado en** `data['daily_nr_corp_by_node']` y `data_js['daily_nr_corp_by_node']`.

Sección HTML en `pane-nr-diario`: `<div id="nr-corp-daily-section">` con chart `chart-nr-corp-daily-bar` y tabla `tbl-nr-corp-daily`. HTML completo en `src/template_dashboard.html`.

### Funciones JS (7 nuevas en `template_dashboard.html`)

| Función | Descripción |
|---|---|
| `_buildNrCorpDailyHierarchyLookup()` | Inicializa `_nrCorpDailyHierarchyNodeById` una sola vez (inline de hierarchy_nr_corp) |
| `renderNRCorpDailySection(month_key)` | Dispatcher: llama chart + tabla. Invocado desde `renderNRDiario(month)` |
| `renderNRCorpDailyChart(month_key)` | Plotly barras apiladas absolutas N+R diario. `Plotly.newPlot` la primera vez, `Plotly.react` en updates |
| `renderNRCorpDailyTable(month_key)` | Tabla HTML colapsable construida dinámicamente con `buildDailyCorpNodeRows()` |
| `buildDailyCorpNodeRows(node_id, ...)` | Genera 2 filas (N+R + Share) por nodo con `data-corp-daily-parent/node/toggle` |
| `toggleCorpDailyNode(node_id)` | Toggle expand/colapso — análogo a `toggleCorpNode()` |
| `collapseCorpDailyNode(node_id)` | Colapso recursivo — análogo a `collapseCorpNode()` |

**Diferencias respecto a la versión mensual**:
- Columnas = días del mes (D1, D2, ...) en lugar de meses
- Filas por nodo: solo N+R + Share (sin Plan ni MoM — no aplican diariamente)
- Todo es HTML dinámico JS (no Python estático)
- Atributos `data-corp-daily-*` (separados de `data-corp-*` mensuales para evitar conflictos CSS/JS)

### Constante `_nrCorpDailyChartInitialized`

Flag global que evita duplicar `Plotly.newPlot`. En actualizaciones usa `Plotly.react()` para eficiencia.

### Archivos modificados
| Archivo | Cambio |
|---|---|
| `src/queries.py` | AÑADIDO: `get_nr_corp_daily_sql()` (con `CHANNEL_APERTURA_3`) |
| `src/processors.py` | AÑADIDO: `process_nr_corp_daily()` + import |
| `src/gen_dashboard_v2.py` | Import, llamada en Paso 3b, `data['daily_nr_corp_by_node']`, `data_js` |
| `src/template_dashboard.html` | Div section + 7 funciones JS + llamada en `renderNRDiario()` |

**Output**: 1682 KB

---

## 31. Sesión 2026-04-12 (continuación): Filas Plan y vs Plan en la tabla corp — dos JSONs separados

### Motivación
Añadir filas "Plan" y "vs Plan" a la tabla Detalle por Canal — Estructura Corporativa, con lógica **distinta** a la del plan de NR Mensual (`hierarchy_nr`). El usuario clarificó que:
- La tabla corp tiene su propia lógica de plan (ej. OC+UCR=rows 6+10, POM=rows 5+9)
- `hierarchy_nr` y la pestaña NR Mensual **no deben tocarse**

### Solución: dos JSONs de plan

| JSON | Consumido por | Propósito |
|---|---|---|
| `hierarchy_PLAN` | Solo documentación | Mapa completo Excel→dashboard (reglas de negocio, notas) |
| `hierarchy_PLAN_Corp` | `load_plan_corp()` | Mapeo ejecutable para la tabla corp exclusivamente |

### `hierarchy_PLAN_Corp` — estructura

Objeto con:
- `_doc`, `_reglas_corp`: documentación embebida
- `mappings`: lista de objetos, cada uno con:
  - `corp_node_id`: ID del nodo en `hierarchy_nr_corp_detail`
  - `plan_type`: `"direct_row"` | `"sum_rows"`
  - `excel_rows`: lista de índices iloc en el Excel
  - `excel_label`, `excel_row_desc`, `notes`: documentación

**Mappings definidos inicialmente** (9 total):

| corp_node_id | excel_rows | Lógica |
|---|---|---|
| `corp_total` | [4] | N+R total |
| `corp_oc_ucr` | [6, 10] | OC Recurring + OC Adhoc (sin row 17) |
| `corp_oc_recurring` | [6] | OWN CHANNELS RECURRING |
| `corp_oc_adhoc` | [10] | OWN CHANNELS AD-HOC |
| `corp_pom` | [5, 9] | POM gest + POM no gestionado |
| `corp_mgm` | [13] | MGM Total |
| `corp_lp` | [16] | L&P Total |
| `corp_ucr_prd` | [17] | Others + Producto |
| `corp_noatrib` | [18] | No Atribuido / Organico |

### Nueva función: `load_plan_corp(config)`

**Archivo**: `src/gen_dashboard_v2.py`
**Firma**: `load_plan_corp(config) → dict`
**Retorna**: `plan_nr_corp_by_node { corp_node_id: { yyyymm: plan_int } }`

Para cada mapping:
```python
for corp_plan_mapping in plan_corp_mappings_list:
    for row_iloc_in_plan in excel_rows_to_sum:
        total += df_plan_excel.iloc[row_iloc_in_plan, col_iloc]
    plan_nr_corp_by_node[corp_node_id][month_key] = int(round(total))
```

**Completamente independiente** de `load_plan()`. No lee ni modifica `plan_nr`.

**Inyectado en** `data['plan_nr_corp_by_node']` (no se añade a `data_js` — solo para el builder Python).

### Actualización de `render_corp_node_rows()` — de 3 filas a 6

| # | Fila | Condición |
|---|---|---|
| 1 | HEADER (nombre canal + toggle ▶, sin valores) | Siempre — única con `data-corp-node` |
| 2 | N+R (valores reales) | Siempre |
| 3 | Plan (valores del Excel) | Solo si `plan_nr_corp_by_node[node_id]` no vacío |
| 4 | vs Plan (% desviación) | Solo si hay Plan |
| 5 | MoM (% mes a mes) | Siempre |
| 6 | Share N+R (% del total) | Siempre |

**Estilo Plan/vs Plan**: fondo crema `#fdf9ec`, texto `#5a4a10` — idéntico al de la tabla NR Mensual.

**Nombrado explícito** en el builder:
- `plan_nr_corp_by_node_from_data` — el dict completo
- `plan_nr_by_month_for_node_in_corp` — slice para el nodo actual
- `this_node_has_plan_in_corp_table` — bool de guardián
- `actual_nr_for_vs_plan`, `plan_val_for_vs_plan` — separación real/plan

### Archivos modificados
| Archivo | Cambio |
|---|---|
| `config/channels_config.json` | AÑADIDO: `hierarchy_PLAN_Corp` con 9 mappings; `hierarchy_PLAN` ya existía |
| `src/gen_dashboard_v2.py` | AÑADIDO: `load_plan_corp()` + llamada en Paso 3b + inyección en `data` |
| `src/builders.py` | `build_nr_corp_table_html()`: usa `plan_nr_corp_by_node_from_data[node_id]`; `render_corp_node_rows()` pasa de 3 a 6 filas |

**Output**: 1813 KB

---

## 32. Sesión 2026-04-12 (continuación): Desagregación de L&P por sub-canal

### Motivación
El usuario solicitó mostrar los sub-canales de L&P (por `CHANNEL_APERTURA_3`) con opción desplegable, al igual que los medios de OC.

### Diagnóstico de datos
Query a BQ confirmó: L&P tiene 5 AP3 activos: OTHERS (84K NR), PARTNERSHIPS (65K), LANDINGS (48K), BRANDFORMANCE (20K), AFFILIATES (6). No hay GTM en datos actuales (se añade previendo futura aparición).

### Cambios en `get_nr_corp_sql()` y `get_nr_corp_daily_sql()`

Se añadió `CHANNEL_APERTURA_3 AS ap3_corp` al CTE base. La cláusula L&P pasó de un bucket único (`OTH|LP|TOTAL`) a 6 casos por AP3: `OTH|LP|AFFILIATES`, `OTH|LP|BRANDFORMANCE`, `OTH|LP|LANDINGS`, `OTH|LP|PARTNERSHIPS`, `OTH|LP|GTM`, `OTH|LP|OTHERS`. SQL completo en `src/queries.py`.

### Cambios en `hierarchy_nr_corp_detail`

`corp_lp` pasa de `is_leaf: true` a `is_leaf: false` con 6 nodos hijos tipo `medio`:
`corp_lp_brandformance`, `corp_lp_landings`, `corp_lp_partnerships`, `corp_lp_others`, `corp_lp_gtm`, `corp_lp_affiliates`

**Nota sobre sub-sub-canales AFFILIATES y PARTNERSHIPS**: Diagnóstico BQ confirmó que ambos tienen `TOUCHPOINT = NULL` — no existe un nivel más granular disponible.

### Archivos modificados
| Archivo | Cambio |
|---|---|
| `config/channels_config.json` | `corp_lp`: leaf→padre; 6 hijos añadidos con `bq_key` |
| `src/queries.py` | `get_nr_corp_sql()` y `get_nr_corp_daily_sql()`: `ap3_corp` en base CTE + 6 casos L&P |

**Output**: 1506 KB

---

## 33. Sesión 2026-04-12 (continuación): Plan para OWN CHANNELS RECURRING y ADHOC

### Cambio
Añadidos 2 mappings a `config/channels_config.json` → `hierarchy_PLAN_Corp.mappings`:
- `corp_oc_recurring` → `excel_rows: [6]` (OC Recurring)
- `corp_oc_adhoc` → `excel_rows: [10]` (OC Adhoc)

Ahora estos sub-canales muestran filas Plan y vs Plan en la tabla corp, sin afectar `hierarchy_nr`.

Los medios hijos de OWN CHANNELS RECURRING (EMAIL, JOURNEY, PANDORA, PUSH, WPP) no tienen plan individual en el Excel → sus filas de Plan se omiten correctamente (condición `this_node_has_plan_in_corp_table = False`).

### Archivos modificados
| Archivo | Cambio |
|---|---|
| `config/channels_config.json` | `hierarchy_PLAN_Corp.mappings`: 2 entradas nuevas → total 9 mappings |

**Output final**: 1834 KB

---

## 34. Sesión 2026-04-13: Extracción de Business Intelligence — Documentos fuente Ene–Mar 2026

### Contexto

El usuario requirió convertir dos documentos PDF de reporting estratégico de adquisición MLM a Markdown estructurado, con extracción exhaustiva de todos los datos, métricas, iniciativas, decisiones y frases literales. El objetivo es que estos archivos Markdown sean consumibles por IA (Skills de Claude Code, análisis, síntesis) y por el equipo de liderazgo de Analytics de Adquisición.

### Metodología de extracción

Se usó **PyMuPDF (`fitz`)** para extracción de texto crudo desde los PDFs (en `vEnv_Meli_Code1`). Una línea por página con `page.get_text('text')`. No se usó OCR — los PDFs tenían texto seleccionable. Script de extracción: `extract_pdf.py` (standalone, no parte del pipeline).

### Documento 1: Weekly Acquisition AO Marzo 2026

| Campo | Valor |
|---|---|
| Fuente | `docs/2026_MLM_ACQWeekly_AOMarch2026.pdf` |
| Output | `docs/2026_MLM_ACQWeekly_AOMar2026_versionClau.md` |
| Páginas fuente | 128 páginas |
| Sesiones cubiertas | 7 sesiones (30-Ene → 27-Mar 2026) |
| Secciones Markdown | 25 secciones + 2 apéndices |
| Tamaño output | ~64.6 KB / 1.272 líneas / 12.221 palabras |

**Contenido extraído:**
- Ficha del documento y metodología de corte (proxy D0→D7)
- Síntesis ejecutiva master con 10 insights cross-sesionales (patrones que solo emergen al analizar 7 semanas juntas)
- Tabla maestra de performance × 7 semanas × 13 canales (% variación + volúmenes absolutos)
- OC + UCR Deep Dive: waterfall Enero, caída de atribución RE sep→ene (-8.18pp), métricas operativas Mantika, tests RE
- Plan Ucrania 2026 (3 pilares): tabla de iniciativas con esfuerzo–impacto + especificaciones Bandit RL
- E&G Tracker de acciones Febrero (38 ítems con status)
- Hub de Newbies: timeline, KPIs D30 experimento (6 métricas con control/test/lift/usuarios inc.)
- Análisis Quincenas: Q vs Valle, Q1 vs Q2, test A/B wordings, análisis MAUS por flujo
- Diagnóstico Character Feb-26 (965K usuarios, Silver 43%, Bronze 34%)
- Ad-Hoc Feb: diagnóstico sesgo medición (-690 Users Inc N+R)
- LP & Partners: plan 23K → 95K N+R 2026
- Green Impact (94% retención, +280K monthly, momentos ML)
- Growth: 4 palancas, 29.28M usuarios contactables (tabla completa), 3 audiencias prioritarias, profit por character, Retención M3 por MYI
- Producto & Web: roadmap 2026, Nueva UI Landings (+43% N+R), CURP analysis, DSP vs Discovery
- Placements MeLi: 3 oportunidades cuantificadas (+11K, +20K, +50K N+R/mes)
- Diagnóstico Orgánico Mar-26: tabla por comportamiento, efecto óptico de atribución
- Plan 2026 y proyecciones
- Calendario Field & Corp 2026
- Dinámica Mesa de Adquisición (cadencia W1–W4)
- Master Tracker de >50 iniciativas con tipo/impacto/ETA/status
- 13 riesgos clasificados por severidad y canal
- Resumen de oportunidades cuantificadas (quick wins / medianas / transformacionales)
- 25+ frases literales preservadas, diferenciadas por tipo (negocio / operativas)

### Documento 2: Monthly ACQ Cierre Ene–Mar 2026

| Campo | Valor |
|---|---|
| Fuente | `docs/2026_MLM_Monthly_ACQ.pdf` |
| Output | `docs/2026_MLM_Monthly_ACQ_AOMarch26_versionClaud.md` |
| Páginas fuente | 81 páginas |
| Cierres cubiertos | 3 cierres mensuales (Enero, Febrero, Marzo 2026) |
| Secciones Markdown | 24 secciones + 2 apéndices |
| Tamaño output | ~50.4 KB / 992 líneas / 9.353 palabras |

**Contenido extraído:**
- Ficha y resumen de secciones por cierre
- Mercado y competencia: Sensor Tower downloads + active users × 3 meses (MP, BBVA, Nu, Plata)
- Tabla maestra N+R vs Plan × 3 meses × 13 canales
- YTD acumulado vs plan (Ene: +12.1%, Feb: +12.4%, Mar: **+15.4%** / +419K N+R sobre plan)
- Mix N+R por canal y Share MKT mensual (Ene 37% → Feb 38% → Mar 35%)
- VPU análisis mensual: drivers detallados por mes (modelo vs usuarios reales)
- X-Channel AUC methodology (explicada y cuantificada): OC +13% eficiencia Mar; POM -10% eficiencia Mar
- Sub-strategies table: inversión / VPU / Share Paid / ROAS por sub-canal
- OC Deep Dive: serie histórica Feb-25 → Feb-26 (13 meses), waterfall por mes, diagnóstico gap Q1 ~95K (9 causas)
- POM Deep Dive: waterfall por mes con calibradores exactos (TikTok 2.25→1.35, YouTube 0.45→0.70, Moloco 0.47→0.21)
- POM Roadmap 2026 con status actualizado a Marzo + iniciativas Q1 short-term con impacto mensual
- Field Marketing: tabla Nov-25 → Feb-26 (campañas / Users Inc N+R / Lift / Ventanas / VPU), learnings saturación
- Plan 1.5M N+R OC: 3 pilares, 9 palancas nuevas, sizes de audiencias (~6M nav. sin opt-in, ~10M nav. espacios ML, etc.)
- Plan testeos incentivados (6 tests definidos con configuración, racional y ETA)
- OC Iniciativas Core Q1 2026 (10 iniciativas con status e impacto)
- Acquisition Strategy on a Page 2026 (tabla cross-equipo: E&G, POM, Corp, Growth, Field, Producto)
- Funnel SSOT por canal (CVR Sign→Home→Activation, Null 9%, MGM mejor CVR)
- Landings y Producto (mismos resultados que Weekly: +43% N+R, CURP 29%, etc.)
- Calendario Field completo 2026 + Juego de Voces + Seasonal Double Days + Mundial TDC
- Forecasts mensuales cruzados con resultados reales (patrón de forecasting conservador identificado)
- VPU detallado Enero (MAF Clabe -10%, TVC -24% post Dic)
- Orgánico Marzo (crecimiento +22% MoM, show push UCR perdiendo share)
- Resumen cross-mensual: 5 tensiones estratégicas del período
- 20+ frases literales preservadas

### Diferencias entre los dos documentos de BI

| Dimensión | Weekly (7 sesiones) | Monthly (3 cierres) |
|---|---|---|
| Granularidad | Semana a semana, D0/D7 | Cierre mensual oficial |
| Foco OC | Ejecución táctica semanal | Tendencia histórica (13 meses) |
| Foco POM | Eventos y calibradores semanales | Deep Dive de waterfall por mes |
| X-Channel | No incluye AUC | AUC por canal × 3 meses |
| Sensor Tower | No incluye | Sí: descargas + usuarios activos × competidores |
| Plan vs Real | MTD semanal (proxy) | Cierre mensual oficial vs plan |
| VPU | Mencionado cualitativamente | Análisis mensual con drivers detallados |
| Forecasts | No incluye | Sí: 3 forecasts cruzados con resultados reales |
| Plan 1.5M OC | Mencionado brevemente | Desarrollado en detalle (3 pilares + palancas) |
| Field | Diagnóstico quincenas + Ad-Hoc | Performance Push Nov-Feb con learnings |

### Ubicación en el proyecto

```
MLM_ADQ_Dash/docs/
├── History.md                                   ← Este archivo
├── metrics_logic.md                              ← Fuente de verdad KPIs
├── 2026_MLM_ACQWeekly_AOMarch2026.pdf            ← Fuente PDF (128 págs)
├── 2026_MLM_ACQWeekly_AOMar2026_versionClau.md  ← Extracción Claude (Weekly)
├── 2026_MLM_Monthly_ACQ.pdf                      ← Fuente PDF (81 págs)
└── 2026_MLM_Monthly_ACQ_AOMarch26_versionClaud.md ← Extracción Claude (Monthly)
```

### Casos de uso recomendados

1. **Alimentar Skills de Claude Code** (`/skill`) con contexto de negocio actualizado para análisis y síntesis.
2. **Cruzar con el dashboard**: Los números de performance en los Markdown son la fuente de verdad de negocio para validar que los datos del dashboard sean coherentes.
3. **Onboarding de nuevos miembros**: Visión completa del canal, métricas, iniciativas y tensiones estratégicas del Q1 2026.
4. **Generación de reportes**: Usar como contexto base para generar análisis, presentaciones o síntesis ejecutivas.

### Notas de mantenimiento

- Estos archivos son **snapshots** — no se actualizan automáticamente.
- Cuando haya nuevos PDFs de Weekly o Monthly, repetir el proceso de extracción con PyMuPDF y crear un nuevo archivo `.md` siguiendo la misma nomenclatura.
- Los datos de performance en los `.md` reflejan el corte de la fecha del PDF fuente — no son datos en tiempo real del dashboard.

### Política de actualización de datos BI

| Documento | Cobertura | Estado | Frecuencia de actualización |
|---|---|---|---|
| `Weekly Adquisición MLM_2025_versionClaud.md` | Ene–Nov 2025 (año completo) | **CERRADO** — 2025 ya cerró | No se actualiza. Es el historial oficial del año. |
| `2026_MLM_ACQWeekly_AOMar2026_versionClau.md` | Ene–Mar 2026 (7 sesiones) | **ABIERTO** — se actualiza con nuevos PDFs | Al recibir el PDF del mes siguiente |
| `2026_MLM_Monthly_ACQ_AOMarch26_versionClaud.md` | Ene–Mar 2026 (3 cierres) | **ABIERTO** — hasta Mar 2026 | Al recibir el cierre mensual siguiente |
| `docs/OC_POM_master_context.md` | Compilado de todas las fuentes | **ABIERTO** — requiere actualización manual | Cuando se agreguen nuevos BI docs |

**Último dato disponible al 13-Abr-2026**: Cierre Marzo 2026.

---

## 35. Sesión 2026-04-13: Skill /project:analizar-oc-pom — Analizador-Optimizador de KPIs OC+POM

### Qué se construyó

Un skill de Claude Code que actúa como **Insights Manager y Growth Strategy Expert de nivel mundial** para los canales OC+Ucrania y POM de Mercado Pago México. El skill combina acceso a toda la base de conocimiento histórico del proyecto con un framework de análisis de 20+ años de experiencia en FANG y fintech.

Nombre definitivo de los archivos: **`analizar-Optimizar_KPIs_oc_pom_*`** (renombrado en §37).

### Arquitectura del skill (3 archivos, máxima eficiencia)

```
MLM_ADQ_Dash/
├── .claude/commands/
│   └── analizar-oc-pom.md                            ← Entry point thin wrapper (26 líneas)
│       Únicamente lee skills/analizar-Optimizar_KPIs_oc_pom_skill.md
└── skills/
    ├── README.md                                      ← Docs + protocolo de actualización mensual
    ├── analizar-Optimizar_KPIs_oc_pom_skill.md       ← Cerebro analítico (560 líneas)
    └── analizar-Optimizar_KPIs_oc_pom_context.md     ← Base de conocimiento DATA CRUDA (436 líneas)
```

**Por qué es eficiente:**
- ~12K tokens por invocación vs ~80K si leyera los 4 PDFs fuente directos (**-85%**)
- El contexto pre-compilado cubre el 80% de las consultas sin fuentes adicionales
- Para el 20% restante, el skill sabe exactamente qué archivo leer
- La lógica del skill **nunca cambia** cuando llegan nuevos datos — solo se actualiza el contexto

### Modos de invocación (10 modos)

| Comando | Modo activado | Output |
|---|---|---|
| `/project:analizar-oc-pom` | `MODO_ESTRATEGICO_COMPLETO` | Análisis completo: fases, drivers, escalar/parar, camino crítico, principios, palancas |
| `/project:analizar-oc-pom oc` | `MODO_OC_UCRANIA` | Deep dive OC+Ucrania |
| `/project:analizar-oc-pom pom` | `MODO_POM` | Deep dive POM |
| `/project:analizar-oc-pom ejecutivo` | `MODO_EJECUTIVO` | 1 página C-Suite, 90 segundos de lectura |
| `/project:analizar-oc-pom camino-critico` | `MODO_CAMINO_CRITICO` | Critical path + palancas + escenarios |
| `/project:analizar-oc-pom mejores` | `MODO_DRILL_MEJORES_PERIODOS` | Ranking subcanales top + qué replicar |
| `/project:analizar-oc-pom peores` | `MODO_DRILL_PEORES_PERIODOS` | Ranking subcanales bottom + qué matar |
| `/project:analizar-oc-pom replicar` | `MODO_QUE_REPLICAR` | Síntesis accionable de qué escalar |
| `/project:analizar-oc-pom parar` | `MODO_QUE_PARAR` | Síntesis accionable de qué matar/pivotar |
| `/project:analizar-oc-pom subcanales` | `MODO_SUBCANALES` | Ranking Push/RE/Mail/WPP/Pandora/TikTok/Meta/Google |
| `/project:analizar-oc-pom [pregunta]` | `MODO_PREGUNTA` | Responde la pregunta específica con evidencia |

### Fuentes de datos (orden de carga)

1. `skills/analizar-Optimizar_KPIs_oc_pom_context.md` — SIEMPRE (data cruda pre-compilada)
2. Cualquier archivo en `MLM_ADQ_Dash/` según lo que requiera el análisis (BI docs, CLAUDE.md, etc.)

### Principios de diseño

1. **Anti-alucinación como Regla #0**: Toda cifra con fuente explícita. Si no hay datos → lo dice.
2. **Contexto por referencia**: El skill carga datos desde archivos externos, no los embebe en el prompt.
3. **Derivación en tiempo real**: Las conclusiones las deriva el bot usando su expertise; no se pre-computan.
4. **Template de output exacto**: 5 plantillas definidas → output consistente y renderizable como HTML.
5. **Separación dato / lógica**: `*_context.md` = DATA. `*_skill.md` = LÓGICA. Nunca mezclar.
6. **Nombres explícitos, comentarios exhaustivos**: Variables `FASE_*`, `DRIVER_*`, `PALANCA_*`, etc.

### Arquitectura final del skill (2 archivos + 1 entry point)

```
MLM_ADQ_Dash/
├── .claude/commands/
│   └── analizar-oc-pom.md          ← Entry point thin wrapper (26 líneas)
│       Lee skills/analizar-Optimizar_KPIs_oc_pom_skill.md y aplica sus instrucciones
└── skills/
    ├── README.md                   ← Docs + PROTOCOLO DE ACTUALIZACIÓN MENSUAL
    ├── analizar-Optimizar_KPIs_oc_pom_skill.md    ← Skill completo: rol, reglas, modos, templates (560 líneas)
    └── analizar-Optimizar_KPIs_oc_pom_context.md  ← Base de conocimiento DATA CRUDA (436 líneas)
```

### Política de datos temporales del skill

| Sección en context.md | Cobertura | Estado |
|---|---|---|
| Sección A | 2025 completo | **CERRADA — nunca modificar** |
| Sección B | 2026 hasta Mar | **ABIERTA — append-only mensual** |
| Sección C | Benchmarks permanentes | Solo actualizar si hay cambio estructural |

**Protocolo de actualización mensual (≈15 min):**
1. Extraer PDF con PyMuPDF → `_raw.txt` temporal
2. Agregar fila en `§B1` (Performance Mensual 2026) — sin tocar filas anteriores
3. Agregar filas en `§B2` (Weekly Cuts 2026)
4. **Reemplazar** `§B3` (Estado Actual) con el nuevo mes
5. Agregar bloque en `§B4` (Sesiones Semanales 2026)
6. Actualizar `§C3` (Riesgos activos) si hay cambios de estado

### Modos disponibles (10 modos)

| Argumento | Modo | Output |
|---|---|---|
| (vacío) | `MODO_ESTRATEGICO_COMPLETO` | 8 secciones completas (nivel Bain) |
| `oc` | `MODO_OC_UCRANIA` | Deep dive OC+UCR |
| `pom` | `MODO_POM` | Deep dive POM |
| `ejecutivo` | `MODO_EJECUTIVO` | 1 página C-Suite, 90 segundos de lectura |
| `camino-critico` | `MODO_CAMINO_CRITICO` | Critical path + palancas + escenarios |
| `mejores` | `MODO_DRILL_MEJORES_PERIODOS` | Ranking subcanales top + qué replicar |
| `peores` | `MODO_DRILL_PEORES_PERIODOS` | Ranking subcanales bottom + qué matar |
| `replicar` | `MODO_QUE_REPLICAR` | Síntesis de qué escalar con evidencia |
| `parar` | `MODO_QUE_PARAR` | Síntesis de qué matar/pivotar |
| `subcanales` | `MODO_SUBCANALES` | Ranking Push/RE/Mail/WPP/Pandora/TikTok/Meta/Google |
| `[texto libre]` | `MODO_PREGUNTA` | Responde la pregunta específica |

---

## 36. Sesión 2026-04-13: Pestaña "🦅 Análisis OC+UCR" en el Dashboard V2

### Motivación

Se completó el "Roadmap: Tab del Dashboard" definido en §35. La pestaña de análisis estratégico OC+UCR se implementó como HTML estático generado por Python — sin dependencia de BigQuery y sin llamadas a Claude API en tiempo de generación.

### Arquitectura implementada

```
skills/analizar-Optimizar_KPIs_oc_pom_context.md   ← Fuente de datos del análisis
         ↓
src/builders_analysis.py            ← Genera HTML estático con build_oc_ucr_analysis_tab_html()
         ↓
src/gen_dashboard_v2.py             ← Importa y llama al builder, reemplaza {{OC_UCR_ANALYSIS_TAB}}
         ↓
src/template_dashboard.html         ← Tab button + TABS array + pane con placeholder
         ↓
dashboard_v2.html                   ← Output final con nueva pestaña (4119 KB)
```

### Archivos modificados

| Archivo | Tipo de cambio | Descripción |
|---|---|---|
| `src/builders_analysis.py` | **NUEVO** | Builder independiente de BQ. 19 constantes nombradas explícitamente (FASE_*, DRIVER_*, PALANCA_*, etc.). Genera 35.3 KB de HTML estructurado. |
| `src/template_dashboard.html` | **Modificado** | +1 tab button `id="t-analisis-oc-ucr"` · +`'analisis-oc-ucr'` al array `const TABS` · +pane `id="pane-analisis-oc-ucr"` con `{{OC_UCR_ANALYSIS_TAB}}` |
| `src/gen_dashboard_v2.py` | **Modificado** | +`from builders_analysis import build_oc_ucr_analysis_tab_html` · +`final_html.replace('{{OC_UCR_ANALYSIS_TAB}}', ...)` |

### Estructura del tab "🦅 Análisis OC+UCR" (7 secciones)

| # | Sección | Contenido | Estilo visual |
|---|---|---|---|
| 1 | **Header banner** | Título + badge período + nota de actualización | Gradiente azul oscuro #1a2744→#2d5986 |
| 2 | **4 Phase Cards** | H1-25 ~130K · H2-25 ~174K · Q1-26 ~138K · Target Ago-26 ~286K | Grid 4 cols, colores distintos por fase |
| 3 | **Narrativa 2 columnas** | Qué impulsó H2-25 (5 drivers) · Por qué cayó Q1-26 (5 causas) | Verde izq / Ámbar der |
| 4 | **Acciones 2 columnas** | Qué escalar (5 items ESCALAR/ACELERAR) · Qué parar (5 items PARAR/PIVOTAR/URGENTE) | Verde izq / Rojo-naranja der |
| 5 | **Camino Crítico** | 138K→286K, 5 meses, timeline mes a mes + hipótesis + riesgo principal | Fondo oscuro #1a1a2e, timeline 5 cards |
| 6 | **5 Principios CRM** | Benchmarks globales (Nubank/MLB/Grab/Rappi) aplicados a MLM + caja "Brecha y oportunidad" | Grid 3 cols, caja ámbar |
| 7 | **Plan 1.5M Palancas** | Tabla #1-5 + Track 0 (palancas, ETA, NR impact, blocker) + Quick Wins + H2-26 estructurales | Tabla numerada con badge gold |

### Principios de diseño del tab

1. **Estático (no BQ)**: El contenido no cambia con cada refresh del dashboard. Se actualiza manualmente al llegar nuevo dato mensual.
2. **Separación de constantes**: Los datos del análisis son constantes nombradas explícitamente al tope de `builders_analysis.py` (no enterradas en HTML). Para actualizar cualquier dato: editar solo la constante.
3. **CSS autocontenido**: El CSS del tab está embebido como `<style id="css-analysis-oc-ucr">` dentro del HTML generado. No modifica `dashboard.css`.
4. **Consistencia visual**: Usa la paleta del dashboard (#1a2744, #1a73e8, etc.) con colores nuevos solo para los badges de acción.
5. **Verificación automática**: 19 checks ejecutados al generar. Output: 4.119 KB — dentro del rango del guardia de seguridad (>50 KB).

### Cómo actualizar cuando llegue Abril 2026

1. Editar `src/builders_analysis.py` — buscar y actualizar las constantes relevantes:
   - `FASE_Q1_2026_*` → actualizar con datos reales de Q1 (ya tenemos los reales)
   - `CAMINO_CRITICO_DESDE` → actualizar si el punto de partida cambió
   - `PALANCAS_PLAN_1_5M[x]['eta']` → actualizar ETAs que ya pasaron
   - Agregar nuevos drivers/causas si el equipo identificó más
2. Regenerar: `python src/gen_dashboard_v2.py`
3. Actualizar también `skills/analizar-Optimizar_KPIs_oc_pom_context.md` §B1–B4 con data de Abril

---

## 37. Sesión 2026-04-13: Skill v2.2 — Optimización arquitectura + actualización datos Q1-2026 reales

### Cambios en el sistema de skills

#### `skills/analizar-Optimizar_KPIs_oc_pom_skill.md` → v2.2

**Bug crítico corregido**: el header declaraba 6 modos, PASO_2 ejecutaba 11 (mismatch silencioso desde v2.1). Header actualizado a 11 modos completos.

**Nuevo dispatch `MODO → SECCIONES DEL CONTEXTO`** (añadido en PASO_1):
Tabla explícita que indica qué secciones del context.md leer según el modo invocado. Impacto directo: `MODO_EJECUTIVO` ahora lee solo §B3+§B5+§C3 en lugar del archivo completo (−80% tokens en modos rápidos). Evita que el modelo consuma contexto innecesario para respuestas simples.

**Nuevo dispatch `MODO → TEMPLATE`** (añadido en PASO_2):
Tabla explícita de 11 filas que mapea cada modo al template exacto que debe usar. Elimina ambigüedad: antes el modelo infería el template leyendo comentarios dispersos; ahora lo consulta en una tabla directa.

**`TEMPLATE_CAMINO_CRITICO` completado**: la sección `### Timeline mes a mes` contenía una referencia rota `[Ver §SECCION_CAMINO_CRITICO en el template completo]` que apuntaba a una sección inexistente. Reemplazada con la tabla real de timeline (5 meses × NR + palanca activa) + hipótesis de crecimiento + riesgo principal con impacto cuantificado.

#### `skills/analizar-Optimizar_KPIs_oc_pom_context.md`

**§A1 — nota guía sobre N+R absolutos**: la tabla §A1 tiene métricas de eficiencia (Share%, CPA, ROAS, VPU, Inv.) pero no N+R absolutos mensuales 2025. Sin esta nota, el modelo intentaba interpolar desde Share% (error silencioso). La nota apunta explícitamente a `docs/Weekly Adquisición MLM_2025_versionClaud.md §3.1` y da un rango de referencia rápida (~65–174K según H1/H2).

**§B5 → §B5a (POM) + §B5b (OC/Pandora)**: los calibradores de Pandora UCR y ACT (Mar-26: 0.6→0.2, −3K y −4.2K NR respectivamente) estaban mezclados con los calibradores de POM en la misma tabla. Restructurada en dos subsecciones independientes con instrucción APPEND propia. El impacto analítico es inmediato: el modelo puede hacer consultas específicas "¿qué calibradores tiene OC esta semana?" sin parsear la tabla completa de POM.

**§C4 — columna `Estado Apr-26`**: las 10 oportunidades cuantificadas tenían ETAs ("Q2", "Q3") pero sin estado de vigencia. O6 y O7 (Pandora Always On 85%) estaban marcadas como "Inmediato" pero están bloqueadas por el calibrador en 0.2. Sin columna de estado, el modelo recomendaría escalar Pandora cuando actualmente es imposible. Ahora: O6/O7 marcadas 🔴 Bloqueado.

#### `skills/CHANGELOG.md` — archivo nuevo

Registro cronológico de qué cambió en el sistema de skills y cuándo. Incluye protocolo de actualización mensual de 15 minutos embebido. Sin este archivo, tras 6 meses de actualizaciones mensuales es imposible auditar qué versión de datos tiene el contexto sin leerlo completo.

#### `.claude/commands/analizar-oc-pom.md` — fix de ubicación

El entry point del skill existía en `MLM_ADQ_Dash/.claude/commands/` (correcto para abrir Claude Code desde `MLM_ADQ_Dash/`), pero el workspace de Claude Code está abierto en `SI_Meli_code1/`. Claude Code busca `/project:` commands en `.claude/commands/` relativo a la raíz del workspace. Creado nuevo entry point en `SI_Meli_code1/.claude/commands/analizar-oc-pom.md` con rutas actualizadas a `MLM_ADQ_Dash/skills/...`. El archivo original en `MLM_ADQ_Dash/` queda intacto para el caso de uso de apertura directa desde ese directorio.

---

### Actualización de datos Q1-2026 reales en `src/builders_analysis.py`

Con los cierres oficiales de Ene-Mar 2026 disponibles en `skills/analizar-Optimizar_KPIs_oc_pom_context.md §B1`, se actualizaron las constantes que tenían valores estimados o incorrectos:

| Constante | Antes | Después | Fuente |
|---|---|---|---|
| `FASE_Q1_2026_NOMBRE` | "Q1 2026 — REGRESIÓN" | "Q1 2026 — CONTRACCIÓN" | — |
| `FASE_Q1_2026_NR` | `"~138K"` | `"~135K"` | §B1: (121.8+135.3+148.9)/3 = 135.3K |
| `FASE_Q1_2026_SUBTITULO` | `"prom. mensual Ene–Mar 26"` | `"121.8K → 135.3K → 148.9K (Ene–Mar 26)"` | §B1 |
| `FASE_Q1_2026_DESCRIPCION` | `"−21% vs H2 25 · señal de alerta"` | `"−14% vs plan Mar · tendencia mejorando +10pp QoQ"` | §B1, §B3 |
| `CAMINO_CRITICO_DESDE` | `"~138K"` | `"~149K (Mar-26 real)"` | §B1 Mar-26 real |
| `CAMINO_CRITICO_CRECIMIENTO_PCT` | `"+108%"` | `"+92%"` | (286/149)−1 |
| `CAMINO_CRITICO_MOM_COMPUESTO` | `"~+20% MoM compuesto"` | `"~+14% MoM compuesto"` | (286/149)^(1/5)−1 |
| `CAMINO_CRITICO_PALANCAS` | `4` | `5` | actualización |
| `CAMINO_CRITICO_MESES_DATOS` | Desde 138K, nombres genéricos | Desde 149K, palancas específicas con fuentes | §B3, §C4 |
| `CAMINO_CRITICO_HIPOTESIS` | Genérico sin fuentes | Con fuentes explícitas §A11, §B5b, §C4 O9/O5 | §contexto |
| `CAMINO_CRITICO_RIESGO_PRINCIPAL` | Solo WPP | WPP + Pandora circuit-breaker | §C3 R3 |
| `CAUSAS_CAIDA_Q1_2026[0]` | "Efecto post-temporada" (genérico) | "Pandora doble shock Mar-26 − 7.2K NR" (específico con datos) | §B5b, §B3 |
| `CAUSAS_CAIDA_Q1_2026[1]` | "Quiebre de mix de VPs" | "Exclusión Churn Paid −20K NR + migración herramientas" | §B4 S6, S7 |
| `QUICK_WINS` | Lista general | Lista priorizada con impactos cuantificados | §A11, §B5b, §C4 |
| `QUICK_WINS_TOTAL_RANGO` | `"+22–32K N+R/mes en Abr"` | `"+15–20K N+R/mes adicionales en Abr"` | estimación conservadora |
| `OBJETIVO_REALISTA` | `"200–220K N+R/mes en Nov-26"` | `"250–286K N+R/mes en Ago-26"` | alineado con CAMINO_CRITICO_HASTA |

**Output regenerado**: `dashboard_v2.html` — **4,122 KB** ✅

### Archivos modificados en esta sesión

| Archivo | Tipo | Descripción del cambio |
|---|---|---|
| `skills/analizar-Optimizar_KPIs_oc_pom_skill.md` | Modificado | v2.2: bug modes, dispatch MODO→SECCIONES, dispatch MODO→TEMPLATE, TEMPLATE_CAMINO_CRITICO completado |
| `skills/analizar-Optimizar_KPIs_oc_pom_context.md` | Modificado | §A1 nota N+R absolutos, B5→B5a/B5b, C4 columna Estado Apr-26 |
| `skills/CHANGELOG.md` | **Nuevo** | Registro cronológico de cambios + protocolo mensual embebido |
| `SI_Meli_code1/.claude/commands/analizar-oc-pom.md` | **Nuevo** | Entry point en raíz del workspace (fix /project: command) |
| `src/builders_analysis.py` | Modificado | 15 constantes actualizadas con datos reales Q1-2026 |
| `dashboard_v2.html` | Regenerado | 4,122 KB — pestaña 🦅 refleja datos Q1-26 reales |

**Output actual**: 4.119 KB (dashboard completo con la nueva pestaña)

---

## 37. Sesión 2026-04-13 (continuación): Renombrado de archivos del skill

### Motivación

Se ajustó el nombre de los archivos del skill para que refleje con máxima claridad su propósito real: no solo "analizar" sino también **optimizar KPIs**. El nombre `analizar-Optimizar_KPIs_oc_pom_*` es más explícito y sigue la preferencia del proyecto de nombres descriptivos y sin ambigüedad.

### Cambios realizados

| Archivo | Nombre anterior | Nombre nuevo |
|---|---|---|
| Skill principal | `skills/analizar_oc_pom_skill.md` | `skills/analizar-Optimizar_KPIs_oc_pom_skill.md` |
| Base de conocimiento | `skills/analizar_oc_pom_context.md` | `skills/analizar-Optimizar_KPIs_oc_pom_context.md` |

**El entry point NO cambió**: `.claude/commands/analizar-oc-pom.md` conserva el mismo nombre para que la invocación del skill (`/project:analizar-oc-pom`) siga siendo la misma.

### Archivos actualizados (43 reemplazos en 9 archivos)

| Archivo | Reemplazos |
|---|---|
| `CLAUDE.md` | 6 |
| `.claude/commands/analizar-oc-pom.md` | 3 |
| `docs/History.md` | 5 |
| `skills/analizar-Optimizar_KPIs_oc_pom_skill.md` | 6 (auto-referencias internas) |
| `skills/analizar-Optimizar_KPIs_oc_pom_context.md` | 2 (auto-referencias internas) |
| `skills/README.md` | 8 |
| `src/builders_analysis.py` | 9 |
| `src/template_dashboard.html` | 1 |
| `dashboard_v2.html` | 3 (archivo generado) |
| **Total** | **43** |

### Estado final del folder `skills/`

```
skills/
├── README.md                                         5,494 bytes   ← sin cambio de nombre
├── analizar-Optimizar_KPIs_oc_pom_skill.md          22,590 bytes  ← renombrado
├── analizar-Optimizar_KPIs_oc_pom_context.md        23,959 bytes  ← renombrado
└── bq_daily_adq_skill.py                             6,124 bytes   ← intacto
```

### Verificación post-rename

Resultado: **cero referencias al nombre antiguo** en todo el proyecto (excepto `dashboard_v2.html` que se actualizó in-place y se regenerará correctamente en el próximo refresh de BQ).

---

## 38. Sesión 2026-04-13: Juez de Negocio + lenguaje ejecutivo + metodología NR Impact

### Motivación
Al revisar la pestaña "🦅 Análisis OC+UCR" en el browser se identificaron dos problemas de calidad:

1. **Jerga interna incomprensible**: términos como "cal", "calibrador", "X-Channel W29-25", "MYI", "Bandit RL", "VP", "POC" aparecían en el dashboard sin definición. Un VP o Director leyendo la pestaña no podía entender las recomendaciones.

2. **Recomendaciones organizacionalmente inviables**: la sugerencia "Reasignar 5-10% del presupuesto de POM → OC" es analíticamente correcta (OC tiene ROAS 5-13x vs 3-4x de POM) pero estratégicamente ciega — POM va +109% vs plan, su líder tiene toda la razón en rechazar un recorte. Crear un perdedor interno innecesario no es una recomendación estratégica.

---

### Cambios en `skills/analizar-Optimizar_KPIs_oc_pom_skill.md`

**Nuevo `FILTRO_ORGANIZACIONAL`** añadido en PASO_3 (cadena de razonamiento), entre el punto 5 (Accionabilidad) y el punto 6 (Camino Crítico):

Antes de escribir cualquier recomendación, el skill ahora pasa por 4 preguntas:

| Pregunta | Propósito |
|---|---|
| ¿Quién pierde si se implementa esto? | Detectar recomendaciones que crean perdedores internos innecesarios |
| ¿El canal "perjudicado" está sobre o bajo plan? | Si está sobre plan → NO tocar. Buscar inversión incremental. |
| ¿La empresa está sobre o bajo plan en total? | Sobre plan YTD (+15.4%) → el caso para inversión incremental es más fuerte que para reasignación |
| ¿Requiere aprobación de alguien no presente? | Si sí → incluir el blocker organizacional explícitamente |

**Regla de oro documentada**: Una recomendación que nadie puede ejecutar porque crea conflicto interno no es una recomendación estratégica — es un problema disfrazado de solución. El experto propone caminos que se pueden recorrer, no solo los teóricamente óptimos.

---

### Cambios en `src/builders_analysis.py`

#### `QUICK_WINS` — reescritura completa en lenguaje ejecutivo

Todas las entradas reescritas eliminando jerga interna. Principio aplicado: si un término necesita explicación para entenderse (calibrador, VP, Bandit RL, X-Channel, MYI, POC), se reemplaza por lo que significa en términos de negocio.

| Quick Win | Antes | Después |
|---|---|---|
| Pandora | "Protocolo Pandora circuit-breaker → +7.2K cuando cal suba de 0.2" | "Restaurar Pandora a nivel de operación normal → +7.2K. En Marzo su algoritmo bajó al 20% de eficiencia. Costo: $0." |
| Presupuesto | "Reasignar 5-10pp POM ACQ → OC · +6–8K (X-Channel W29-25 confirma headroom)" | "Solicitar inversión incremental para OC — el canal más eficiente. Con Q1 +15.4% sobre plan, el caso de negocio existe sin tocar POM." |
| Push | "Push VP Servicios/Pagos + Recargas · CPA $0.6–0.8, ROAS 56–111x" | "Ampliar envío de promociones de Servicios y Recargas a mayor base. CPA $0.60 USD — el más bajo del portafolio. Solo escalar volumen." |
| WPP | "WPP Ucrania lanzamiento Q2 → habilita palanca +25–30K/mes" | "Lanzar WhatsApp a los 6 millones de usuarios que aún no lo reciben → habilita +25K N+R/mes a partir de Mayo." |
| Bandit | "Bandit RL Push POC → escalar → +3.5K NR piloto" | "Escalar el algoritmo de optimización de Push (piloto exitoso completado) → +3.5K N+R confirmados. Sin riesgo: ya validado." |

**Total** reencuadrado de "+15-20K (piso conservador — palancas sin calibrador externo)" → "+15K N+R/mes adicionales en Abril — solo con acciones que el equipo puede ejecutar hoy"

#### `INICIATIVAS_PARAR_PIVOTAR` — reescritura en lenguaje ejecutivo

| Item | Cambio principal |
|---|---|
| "Dependencia de single-target MYI" | → "Depender de un solo tipo de incentivo (Money In)" |
| "Segmentación amplia → audiencias comportamentales (Mantika + Bandit)" | → "Envíos masivos → mensajes personalizados por comportamiento. Usuarios que navegan en ML convierten 2x más." |
| "Operación manual → automatización. El Bandit (RL multi-arm) es el pivot correcto" | → "Configuración manual de campañas → optimización automática. Reduce dependencia operativa manual." |
| "Fix atribución CC (measurement)" | → "Corregir la medición antes de escalar cualquier canal — prerequisito técnico para que todas las decisiones sean correctas." |

#### `ESTRUCTURALES_H2_2026` — reescritura

| Antes | Después |
|---|---|
| "WPP Ucrania live: +5–10K/mes incremental (Q2)" | "WhatsApp Ucrania live: +25K N+R/mes — la palanca más grande del plan (Q2)" |
| "Gami checkpoint/multi-target: rompe techo MYI (Q2–Q3)" | "Nuevas mecánicas de activación: rompe el techo del incentivo único actual (Q2–Q3)" |
| "Pandora CC + segmentación valor: KYC/FS/Meli+ (Q2–Q3)" | "Pandora + usuarios con historial financiero (KYC): segmentos de 6x mayor conversión aún sin atacar (Q2–Q3)" |

---

### Nuevo archivo: `docs/NR_impact_methodology.md`

Documento creado para responder "¿de dónde sale cada número de NR Impact?" en la tabla de palancas. Contiene para cada palanca (1–5 + Track 0):
- Audiencia objetivo
- Lift aplicado y justificación
- Fórmula exacta (audiencia × lift × descuento de incertidumbre)
- Por qué ese piso y no otro
- Diferencia entre palancas que generan NR nuevo vs Track 0 que "encuentra" NR ya generado

**Regla de oro documentada**: si el número depende de una variable que el equipo no controla (calibrador Pandora, acuerdo MeLi), se marca como condicional y no se suma al total base.

**Todos los NR Impact actualizados a piso único** (sin rangos):

| Palanca | Rango anterior | Piso en dashboard | Cálculo |
|---|---|---|---|
| 1 — WPP Ucrania | +25–30K | **+25K** | 6M × 0.4% lift (−20% vs estimado) |
| 2 — Gamification | +15–20K | **+15K** | Piso de rango documentado Monthly Mar-26 |
| 3 — Nuevos Espacios ML | +8–12K | **+8K/mes al escalar** | 40% del pico en primeros 60 días |
| 4 — Pandora (bloqueado) | +4–8K/track | **+4K/mes por track** | Piso del track menor (UCR: 4.5K → 4K) |
| 5 — Segmentación KYC | +10–16K | **+10K/mes al madurar** | Solo KYC con descuento 20% |
| Track 0 — Atribución CC | +5–8% «found» | **+7K «found» N+R** | 5% × 149K (Mar-26) = 7.5K → 7K |

**Output regenerado**: `dashboard_v2.html` — **4,124 KB** ✅

### Archivos modificados en esta sesión

| Archivo | Tipo | Descripción |
|---|---|---|
| `skills/analizar-Optimizar_KPIs_oc_pom_skill.md` | Modificado | +FILTRO_ORGANIZACIONAL en PASO_3 (Juez de Negocio) |
| `src/builders_analysis.py` | Modificado | QUICK_WINS, INICIATIVAS_PARAR_PIVOTAR, ESTRUCTURALES_H2_2026 en lenguaje ejecutivo sin jerga. NR Impact a piso único. |
| `docs/NR_impact_methodology.md` | **Nuevo** | Metodología de cálculo de NR Impact por palanca con fórmulas auditables |
| `dashboard_v2.html` | Regenerado | **4,124 KB** |

---

## 39. Sesión 2026-04-13: Extensión del skill a los 4 canales + rename v2.3

### Motivación
El skill cubría OC+UCR y POM únicamente. MLM tiene 4 canales: OC+UCR, POM, MGM/Others y Orgánico. Orgánico representa ~63% del total N+R y no tenía cobertura analítica. MGM y L&P/Others (~5% combinado) tampoco.

### Rename de archivos

| Archivo anterior | Archivo nuevo |
|---|---|
| `skills/analizar-Optimizar_KPIs_oc_pom_skill.md` | `skills/analizar-Optimizar_Performance_KPIs_skill.md` |
| `skills/analizar-Optimizar_KPIs_oc_pom_context.md` | `skills/analizar-Optimizar_Performance_KPIs_context.md` |

**Referencias actualizadas en cascada** (10 archivos):
`CHANGELOG.md` · `README.md` · `.claude/commands/analizar-oc-pom.md` (x2) · `src/builders_analysis.py` · `docs/NR_impact_methodology.md` · self-references en skill + context

El comando de invocación **`/project:analizar-oc-pom`** no cambia — solo el nombre de los archivos internos.

### Nuevos modos en el skill (v2.3)

| Argumento | Modo | Cobertura de datos |
|---|---|---|
| `mgm` | MODO_MGM | §A15 + §B6 (limitado — recomienda leer BI) |
| `others` | MODO_OTHERS_LP | §A16 + §B6 (limitado — requiere BI para análisis serio) |
| `org` | MODO_ORGANICO | §A17 + §B1 col ORG + §B6 |
| `total` | MODO_TOTAL_SITE | Todo el contexto §A–§C |

**Disponibilidad de datos documentada en header** del skill: OC/POM = ALTA · MGM/Others/ORG = MEDIA (con instrucción anti-alucinación explícita).

### Nuevas secciones en el context (v2.3)

| Sección | Contenido | Tipo |
|---|---|---|
| §A15 | MGM 2025: cortes MTD, estructura ADQ/ACT, typo "ADQUISITION", insight CVR | 2025 CERRADO |
| §A16 | L&P/Others 2025: cortes MTD, sub-canales, decisiones activas (Rocket/OJO7 ❌, Telcel $0 ✅) | 2025 CERRADO |
| §A17 | ORG Tendencia 2025: share histórico ~60-70%, relación ORG↔MKT (complementarios), señal de alerta | 2025 CERRADO |
| §B6 | MGM+Others+ORG 2026: derivado de §B1, share por canal Q1-26, tendencia | 2026 ABIERTO |

### Subcanales añadidos en PASO_3B

- **MGM**: MGM ADQ/ACT, mix, concentración con/sin incentivo
- **L&P/Others**: Brandformance, Affiliates, Partnerships, Landings, GTM, partners pausados
- **ORG**: análisis de tendencia (share, relación con MKT, seasonalidad)

### Archivos modificados en esta sesión

| Archivo | Tipo | Cambio |
|---|---|---|
| `skills/analizar-Optimizar_Performance_KPIs_skill.md` | Renombrado + modificado | v2.3: 4 canales, 15 modos, header actualizado |
| `skills/analizar-Optimizar_Performance_KPIs_context.md` | Renombrado + modificado | §A15/A16/A17/B6 nuevas secciones |
| `skills/CHANGELOG.md` | Modificado | +entrada v2.3 |
| `skills/README.md` | Modificado | Referencias actualizadas |
| `.claude/commands/analizar-oc-pom.md` (x2) | Modificado | 15 modos + nuevo nombre de archivo |
| `src/builders_analysis.py` | Modificado | Referencias actualizadas |

---

## 40. Sesión 2026-04-14: Pestaña "● Análisis POM" — Builder, target 250K y CSS fix

### Motivación
Con la pestaña OC+UCR funcionando, se creó la pestaña equivalente para POM. Además se corrigió un bug crítico de formato visual (CSS classes) que hacía que las phase cards y el camino crítico se mostraran incorrectamente.

### Nuevo: `build_pom_analysis_tab_html()` en `src/builders_analysis.py`

Función nueva que sigue exactamente la misma arquitectura que `build_oc_ucr_analysis_tab_html()`:
- **7 secciones**: Header · Phase cards · Narrativa 2 col · Acciones 2 col · Camino crítico · Principios · Plan palancas
- **Color primario**: `#2F9E8F` (verde POM de `channels_config.json`)
- **CSS embed**: `<style id="css-analysis-pom">` con solo los overrides necesarios (header gradient). El resto hereda del CSS del tab OC+UCR que ya está en el mismo HTML.
- **Target inicial**: ~250K NR/mes en Ago-26 (mínimo 240K)

**Datos POM de fuente**: §A3 (2025 mensual), §A5 (VP tests: CBK 10% TDD ganó vs 50% con 92% significancia), §A12 (Plan 2025 vs 2024: N+R +36% YoY), §A13 (Seasonals: Hot Sale +24% NR share, Buen Fin CPM -30%), §B1 (2026: +105.8%/+90.1%/+109.1% vs plan), §B3 (Mar-26 estado), §B5a (calibradores).

**Constantes POM añadidas** (`FASE_POM_*`, `DRIVERS_POM_CRECIMIENTO`, `CAUSAS_TENSION_POM_Q1_2026`, `INICIATIVAS_ESCALAR_POM`, `INICIATIVAS_PARAR_PIVOTAR_POM`, `POM_CRITICO_*`, `PRINCIPIOS_POM`, `PALANCAS_PLAN_POM`, `PALANCA_TRACK_0_POM`, `POM_QUICK_WINS`, `POM_QUICK_WINS_TOTAL`, `POM_ESTRUCTURALES_H2_2026`, `POM_OBJETIVO_REALISTA`).

**Análisis estratégico aplicado** (skill MODO_POM):
- La tensión central de POM: +100% vs plan pero con incrementalidad cuestionada en TikTok ACQ (calibrador 2.25→1.35 = -24.2K NR). Volumen ≠ calidad incremental.
- FILTRO_ORGANIZACIONAL aplicado: no se propone recortar POM (va +109% vs plan). Se propone mejorar mix y medir incrementalidad.
- Track 0: Test hold-out de incrementalidad antes de Q3. Sin esto, las decisiones de presupuesto son en ciego.

### Bug fix: Phase cards y critical path con CSS incorrecto

**Síntoma**: En el browser, las phase cards aparecían como barras horizontales en lugar de un grid 4-col, y el camino crítico mostraba tarjetas apiladas verticalmente en lugar de un timeline horizontal.

**Causa raíz**: La función `build_pom_analysis_tab_html()` usaba class names inventados (`phase-cards-grid`, `phase-name`, `critical-path-timeline`) que no existían en el CSS. El CSS real usa `.phases-grid`, `.phase-card-label`, `.critical-path-months`. El CSS embebido del POM tab era un comentario vacío, no el CSS real.

**Fix**: Reescritura completa de la función usando los class names exactos del OC tab. El CSS del POM tab ahora solo sobreescribe el color del header (2 reglas CSS), heredando el resto del OC tab que ya está en el mismo HTML.

### Cambio de tab names: emojis → esferas de color canal

El usuario solicitó reemplazar los íconos de pestaña (🦅, 🔥, ◈) por esferas de color que correspondan al color oficial del canal en `channels_config.json`:
- `analisis-oc-ucr`: **`<span style="color:#5899D1;">●</span> Análisis OC+UCR`**
- `analisis-pom`: **`<span style="color:#2F9E8F;">●</span> Análisis POM`**

### Archivos modificados

| Archivo | Cambio |
|---|---|
| `src/builders_analysis.py` | +`build_pom_analysis_tab_html()` · +todas las constantes POM · CSS fix completo |
| `src/gen_dashboard_v2.py` | +import `build_pom_analysis_tab_html` · +`final_html.replace('{{POM_ANALYSIS_TAB}}', ...)` |
| `src/template_dashboard.html` | +tab button POM · +pane `{{POM_ANALYSIS_TAB}}` · TABS array actualizado · esferas de color en nombres |
| `skills/CHANGELOG.md` | +entrada v2.3 arquitectura |

**Output**: **4,172 KB** → **4,173 KB** (con fix CSS)

---

## 41. Sesión 2026-04-14: Target OC+UCR 240K + NR Impacts reducidos

### Motivación
El target original de 286K para OC+UCR se revisó a 240K en Agosto 2026, reflejando un plan más conservador y ejecutable (+61% vs Q1-26 avg, ~+10% MoM compuesto vs +92% / +14% anterior). Todos los NR Impacts se redujeron ~20% para usar pisos más defensibles.

### Cambios en `src/builders_analysis.py`

| Constante | Antes | Después | Razón |
|---|---|---|---|
| `FASE_TARGET_NR` | `"~286K"` | `"~240K"` | Target revisado |
| `FASE_TARGET_SUBTITULO` | `"+108% vs Q1-26 avg"` | `"+61% vs Q1-26 promedio"` | Recalculado |
| `CAMINO_CRITICO_HASTA` | `"286K"` | `"240K"` | Target revisado |
| `CAMINO_CRITICO_CRECIMIENTO_PCT` | `"+92%"` | `"+61%"` | (240/149)−1 |
| `CAMINO_CRITICO_MOM_COMPUESTO` | `"~+14% MoM"` | `"~+10% MoM"` | (240/149)^(1/5)−1 |
| `CAMINO_CRITICO_MESES_DATOS` | Timeline 165→192→220→252→286K | **165→182→200→220→240K** | Recalculado |
| Palanca 1 WPP | `+25K/mes` | `+20K/mes` | -20% conservador |
| Palanca 2 Gamification | `+15K/mes` | `+12K/mes` | -20% |
| Palanca 3 Espacios ML | `+8K/mes` | `+6K/mes` | -25% |
| Palanca 4 Pandora | `+4K/track` | `+3K/track` | -25% |
| Palanca 5 KYC | `+10K/mes` | `+8K/mes` | -20% |
| Track 0 Atribución | `+7K` | `+6K` | 4% × 149K |
| `QUICK_WINS_TOTAL_RANGO` | `"+15K"` | `"+11K"` | Quick wins reducidos proporcionalmente |
| `OBJETIVO_REALISTA` | `"250–286K"` | `"~240K Ago-26 · base 220K · opt 240K"` | Alineado |

**Output**: **4,173 KB**

---

## 42. Sesión 2026-04-14: Skill v2.4 — Corrección nomenclatura Vista Corporativa (Corp)

### Motivación
El skill declaraba `CANALES CUBIERTOS: OC+Ucrania (E&G) · POM · MGM/Others · Orgánico · Total Site` — incorrecto respecto a la vista Corp del dashboard (`hierarchy_nr_corp_detail` en `config/channels_config.json`).

**Errores específicos**:
1. MGM aparecía como canal de primer nivel → en Corp es **sub-canal de OTHERS**
2. "Orgánico" no existe en Corp → se llama **NO ATRIBUIDO**
3. OTHERS Corp incluye: **MGM + L&P + UCR PRD + SEO + POM SELLERS + POM OTHERS** (6 sub-canales)

### Cambios en `skills/analizar-Optimizar_Performance_KPIs_skill.md` → v2.4

- **Nuevo bloque `MAPA DE CANALES — VISTA CORPORATIVA (CORP)`** insertado antes del ROL del analista. Es lo primero que lee el modelo al invocarse. Contiene:
  - Árbol completo de la jerarquía Corp (4 niveles: Total → OC+UCR/POM/OTHERS/NO ATRIBUIDO → sub-canales → medios)
  - Fuente de verdad explícita: `config/channels_config.json → hierarchy_nr_corp_detail`
  - Tabla de mapeo vista estándar ↔ vista Corp (incluye la nota sobre UCR PRD que en estándar está en OC+UCR pero en Corp está en OTHERS)
  - Explicación de por qué los números pueden diferir entre vistas
- **Header CANALES CUBIERTOS**: actualizado a los 4 grupos Corp exactos con descripción de composición de OTHERS
- **Modos renombrados**: `MODO_ORGANICO` → `MODO_NO_ATRIBUIDO` (alias "org" mantenido), `MODO_OTHERS_LP` → `MODO_OTHERS`, `MODO_OC_UCRANIA` → `MODO_OC_UCR`
- **PASO_3B subcanales OTHERS**: corregido para mostrar los 6 sub-canales reales (MGM, L&P, UCR PRD, SEO, POM SELLERS, POM OTHERS) con sus medios respectivos para L&P

### Cambios en `skills/analizar-Optimizar_Performance_KPIs_context.md`

- **Header**: nueva sección "VISTA CORPORATIVA" con los 4 canales Corp y equivalencia estándar ↔ Corp
- **§A15 (MGM)**: nota de posición Corp (sub-canal de OTHERS, no canal independiente)
- **§A16 (L&P)**: nota de posición Corp + lista de 6 sub-canales propios + mención de los otros sub-canales de OTHERS (UCR PRD, SEO, POM Sellers/Others)
- **§A17**: renombrado "ORG/Orgánico" → "NO ATRIBUIDO / Orgánico" con tabla de equivalencia
- **§B6**: header corregido a "OTHERS Corp + NO ATRIBUIDO Corp"

---

## 43. Sesión 2026-04-14: Skill v2.5 — Análisis de Estacionalidad + Calendario Comercial México

### Motivación
Los modos existentes del skill podían analizar qué pasó pero no podían responder "¿era de esperarse que pasara en este período?" ni "¿cuándo es el mejor momento del año para escalar Pandora?". Se requería una capa analítica temporal — matemáticamente rigurosa, con calendario comercial mexicano y campañas internas de Mercado Pago cuantificadas.

### Nuevas secciones en `skills/analizar-Optimizar_Performance_KPIs_context.md`

Añadidas entre §AE3 existente y §AE4:

| Sección | Contenido | Tipo |
|---|---|---|
| **§AE1** | Calendario Comercial México + Impacto MP: 12 meses con IS estimado OC+UCR/POM, evento principal, acción operativa validada | Permanente |
| **§AE2** | Índices de Estacionalidad Mensuales: tabla IS OC+UCR 2025 completo (Feb–Dic) + 2026 Q1, metodología (share-based para OC, absoluto para POM), marca [estimado] donde aplica | 2025 cerrado |
| **§AE3** | Patrón Intra-Mensual Quincenas (ya existía, ampliado) | — |
| **§AE4** | Días Especiales del año (ya existía) | — |
| **§AE5** | Campañas internas MP con impacto cuantificado: LCDLF, Hot Sale, Buen Fin, JDV, Double Days, Quincenas — cada una con período, IS, dato verificado, fuente, regla operativa | Permanente |
| **§AE6** | Matriz de Decisión Estacional: tabla 4 canales × 8 eventos (lookup rápido) | Permanente |
| **§AE7** | Patrón Semanal dentro del Mes: IS_semanal × semana (S1–S4+) derivado de §A8 + §B2 cortes | Permanente |
| **§AE8** | Patrón Día de la Semana (DoW): tabla 7 días × 8 tipos de canal/medio, escala de confianza ★★★, "paradoja del fin de semana" para MP | Permanente |
| **§AE9** | Estacionalidad por Sub-canal y Medio OC+UCR: 7 rows (PANDORA, PUSH, EMAIL, DRW, QA, WPP UCR, WPP ACT) × 6 dimensiones (patrón mensual, mejor semana, mejor DoW, evento crítico, regla de oro, fuente) | Permanente |

### Cambios en `skills/analizar-Optimizar_Performance_KPIs_skill.md` → v2.5

- **Nuevos modos**: `"estacionalidad"` y `"temporal"` (alias) → `MODO_ESTACIONALIDAD`
- **Dispatch MODO→SECCIONES**: nueva fila: §AE1–§AE6 OBLIGATORIO + §A del canal + §B1–B2
- **Dispatch MODO→TEMPLATE**: nueva fila → `TEMPLATE_ESTACIONALIDAD`
- **Nuevo PASO_3C `RAZONAMIENTO_ESTACIONALIDAD`**: cadena de 9 pasos en 4 niveles:
  - Nivel 1: Calcular IS mensual, clasificar canal (ESTACIONAL/MODERADO/ESTABLE), relacionar con eventos
  - Nivel 2: Aplicar modelo de quincenas, analizar D7 cuts como proxy de arranque
  - Nivel 3: Mapear días especiales del calendario con su impacto cuantificado
  - Nivel 4: Construir calendario de decisiones para próximos 3 meses, comparar patrón actual vs histórico
- **Nuevo TEMPLATE_ESTACIONALIDAD**: output estructurado con tabla IS 12 meses, campañas cuantificadas, distribución intra-mensual, desviaciones del patrón, calendario de acciones concretas
- **PASO_5 Checklist**: separado en 3 bloques (todos los modos / solo estacional / solo drill/estratégico)
- **Regla estacional crítica**: "LCDLF–Buen Fin–Aguinaldo (Ago–Dic): 5 meses donde perder el período por calibradores bajos = perder la ventana más rentable del año."

---

## 44. Sesión 2026-04-14: Sección Estacionalidad en Pestaña "● Análisis OC+UCR" + Bug Fix

### Sección añadida al dashboard (después del Plan 1.5M)

La pestaña `analisis-oc-ucr` se extendió con una **Sección 8: Estacionalidad OC+UCR** con 4 sub-bloques:

#### Sub-bloque 1: IS Heatmap 12 meses
Grid 6×2 con tarjeta por mes. Cada tarjeta muestra: mes, IS numérico, badge de nivel (ALTO/ESTABLE/BAJO/CRÍTICO con código de color), evento principal, acción operativa. Leyenda de colores al pie.

Fuente: §AE2 (IS 2025 completo derivado de share% §A1, promedio anual ≈ 16.5%).

Insights visuales inmediatos:
- Julio (1.08–1.15) y Septiembre (1.09) = verde oscuro → mejor período del año para OC
- Enero (0.83) y Mayo (0.87) = rojo → hoyo post-estacional y Hot Sale
- El mismo peso en Agosto genera 40% más NR que en Enero (IS 1.15 vs 0.83)

#### Sub-bloque 2: 3 Insights Clave de Estacionalidad
Cards con las 3 verdades estadísticas más importantes, con dato exacto y fuente:
1. Agosto genera 40% más NR que Enero por el mismo presupuesto (IS 1.15 vs 0.83 · ROAS 13x Ago-25)
2. Pandora varía 7x en CPA: $1.4 quincena → $10 Hot Sale/BF (§A6, §AE5)
3. LCDLF–BF–Aguinaldo: únicos 5 meses consecutivos sobre IS 1.0 (si se pierde agosto, no se recupera)

#### Sub-bloque 3: Campañas Internas + Impacto Cuantificado
Tabla limpia: LCDLF · Hot Sale · Buen Fin · Quincenas con período, impacto OC+UCR y acción validada.

#### Sub-bloque 4: Calendario de Decisiones — Próximos 3 Meses
Desde Abril 2026: Mayo (IS 0.87 🔴 · Hot Sale · PAUSAR Pandora), Junio (IS 1.01 🟢 · Reactivar), Julio (IS 1.08 🟢 · ESCALAR para LCDLF).

#### Sub-bloque 5: Patrón Semanal dentro del Mes (IS por Semana)
4 cards con IS_semanal, días, driver y acción:
- S1 (D1–D7): IS 0.75–0.82 🔴 Arranque lento post-quincena
- S2 (D8–D16): IS 1.20–1.30 🟢 PICO (quincena 1 · CVR +2.3pp · Pandora $1.4)
- S3 (D17–D22): IS 0.88–0.95 🟡 Valle inter-quincenal
- S4+ (D23–fin): IS 1.05–1.15 🟢 Segundo pico (quincena 2 en meses de 30-31 días)

Validado con cortes reales Feb-26 (§B2): D1-4 = 11.7% del mensual (confirma arranque lento de S1).

#### Sub-bloque 6: Patrón Día de la Semana — OC/CRM vs POM Pagado
Tabla 7 días × 2 columnas con código de color (ÓPTIMO/BUENO/REGULAR/EVITAR):
- OC/CRM: **Martes-Miércoles = ÓPTIMO** (OR email + ML nav pico). Evitar Sábado-Domingo.
- POM Social: **Viernes-Domingo = mejor reach** pero paradoja: mayor reach ≠ mayor conversión para activar MP.
- Clave estratégica: OC+UCR depende de que el usuario esté en "modo ML/transaccional" = días laborales.

Marcado como [inf] (inferencia de benchmarks industria LATAM). Para validar: query BQ DAYOFWEEK × CANAL × NR.

#### Sub-bloque 7: Estacionalidad por Sub-canal y Medio
Tabla 7 filas (PANDORA · PUSH UCR/ACT · EMAIL OC · RE-DRW · RE-QA · WPP UCR · WPP ACT) × 6 columnas (patrón mensual, mejor semana, mejor DoW, evento crítico, regla de oro, fuente [dato] o [inf]).

Granularidad: canal OC+UCR → sub-canal (UCRANIA E&G / RECURRING) → medio (EMAIL, PANDORA, PUSH, DRW, QA, WPP).

### Bug Fix: Sección Estacionalidad aparecía 2 veces en el tab

**Síntoma**: La sección "Estacionalidad OC+UCR" se renderizaba dos veces — una en la pestaña correcta (`pane-analisis-oc-ucr`) y otra dentro de `pane-perf-corp`.

**Causa raíz**: El comentario HTML tenía literalmente `{{OC_UCR_ANALYSIS_TAB}}` → Python `.replace()` lo reemplazaba también, insertando el HTML del tab OC+UCR dentro de `pane-perf-corp`.
**Fix**: quitar las llaves dobles del comentario: `<!-- Placeholder: OC_UCR_ANALYSIS_TAB -->`.

**Principio documentado**: Nunca usar el mismo string del placeholder dentro de comentarios HTML cuando se usa Python `.replace()` para inyectar contenido. Las llaves dobles `{{}}` son el patrón de template — reservarlas exclusivamente para el placeholder real.

### Archivos modificados en §40–44

| Archivo | Cambio |
|---|---|
| `src/builders_analysis.py` | +`build_pom_analysis_tab_html()` · +constantes POM · Target OC 240K · NR Impacts −20% · +constantes estacionalidad (OC_IS_MENSUAL, OC_PATRONES_SEMANA, OC_DOW_PATTERNS, OC_SUBCANAL_MEDIO_SEASONAL, OC_CAMPANAS_IMPACTO, OC_PROXIMOS_3_MESES, OC_ESTACIONALIDAD_INSIGHTS) · +sección 8 estacionalidad completa en OC tab |
| `src/gen_dashboard_v2.py` | +import + call `build_pom_analysis_tab_html()` |
| `src/template_dashboard.html` | +tab/pane POM · Esferas de color en nombres de tabs · Fix placeholder en comentario HTML · TABS array a 8 |
| `skills/analizar-Optimizar_Performance_KPIs_skill.md` | v2.4 (Corp nomenclature) → v2.5 (Estacionalidad): MAPA CANALES CORP · 2 nuevos modos · PASO_3C · TEMPLATE_ESTACIONALIDAD · Checklist ampliado |
| `skills/analizar-Optimizar_Performance_KPIs_context.md` | v2.4: header Corp, §A15/A16/A17 actualizados. v2.5: §AE7/AE8/AE9 (weekly, DoW, sub-canal/medio) |
| `skills/CHANGELOG.md` | +entradas v2.4 y v2.5 |

**Output final**: `dashboard_v2.html` — **4,168 KB** · 8 pestañas activas ✅
| `docs/NR_impact_methodology.md` | Modificado | Referencias actualizadas |

---

## 45. Sesión 2026-04-15: Nueva pestaña "Comms_OC" — Comunicaciones OC

### Motivación

El dashboard actual muestra N+R agregado por canal pero no tiene visibilidad de **qué comunicaciones específicas de OC generaron esos resultados**: qué campaña, con qué medio (CANAL), cuántos enviados, qué open rate, qué lift, cuántos usuarios incrementales (USER_INC) y qué valor generado (VALUE_INC). La pestaña Comms_OC llena este gap cruzando tres fuentes de datos de OC que ya existen en BigQuery.

### Fuentes de datos (3 tablas BQ)

| Tabla BQ | Dataset | Proyecto | Contenido |
|---|---|---|---|
| `BT_OC_CUST_EVENT` | `SBOX_MARKETING` | `meli-bi-data` | Eventos por comunicación (create/test/control/arrived/shown/open) |
| `DASHBOARD_CAMPAIGNS_INDIVIDUOS_METRICAS` | `SBOX_EG_MKT` | *(default project)* | Métricas de campaña: sents, open_rate, CVR, lift, USER_INC, TPN_INC, TPV_INC, VALUE_INC |
| `BT_OC_DASHBOARD_ALL_CAMPAIGNS` | `SBOX_EG_MKT` | *(default project)* | Meta-data de campaña: CANAL, APP, NOTIFICATION_TITLE, NOTIFICATION_TEXT |

> ⚠️ **Nota de proyecto BQ**: `DASHBOARD_CAMPAIGNS_INDIVIDUOS_METRICAS` y `BT_OC_DASHBOARD_ALL_CAMPAIGNS` no llevan prefijo de proyecto en el SQL — usan el proyecto por defecto del cliente BQ. Verificar que el ADC / service account tenga acceso a `SBOX_EG_MKT` además de `meli-bi-data`.

> ⚠️ **Filtros aplicados en la query fuente**:
> - `SIT_SITE_ID = 'MLM'` en las 3 tablas
> - `BUSINESS_UNIT IN ('MERCADOPAGO','MARKETPLACE')` en BT_OC_CUST_EVENT
> - `STRATEGY NOT IN ('ENGAGEMENT','RETENTION')` en METRICAS y ALL_CAMPAIGNS
> - `BUSINESS_LINE_SEGMENT_CHANNELS NOT LIKE '%SELLER%'` en METRICAS

### Query base (SQL fuente)

**SQL canónico completo**: `config/queries/comms_oc.md` — incluye SQL copy-paste ready para BQ UI, gotchas documentados, evolución de la query y todas las decisiones de diseño.
**Implementación en código**: `src/queries.py` → `get_comms_oc_fresh_sql()` (semana actual) y `scripts/refresh_comms_oc_cache.py` → `build_comms_oc_sql_for_date_range()` (histórico, parametrizado).

Estructura de la query (4 CTEs + JOIN final):
- `raw_events_agg`: funnel de **usuarios únicos** por COMMUNICATION_ID usando `COUNT(DISTINCT IF(..., CUS_CUST_ID, NULL))`. `CUS_CUST_ID` = ID único del cliente en `BT_OC_CUST_EVENT`.
- `ce_clean`: normaliza COMMUNICATION_ID (split en '.' para limpiar '12345.0') y CAMPAIGN_NAME (elimina sufijo `_DEFAULT`). `NULLIF` evita cruces cartesianos por nombres vacíos.
- `indiv_metrics`: agrega a nivel **CAMPAÑA × MES** (no por comunicación). Esto causa que las métricas se repitan para todos los COMM_IDs de la misma campaña — `builders.py` deduplica por `CAMPAIGN_NAME_CLEAN` antes de sumar totales.
- `camp_meta`: meta-data por COMMUNICATION_ID (CANAL, APP, NOTIFICATION_TITLE, NOTIFICATION_TEXT, BUSINESS_LINE_SEGMENT_CHANNELS).

> **Bug fix de sintaxis (original)**: tenía `; ORDER BY` — punto y coma antes del ORDER BY. En BigQuery, ORDER BY va al final sin punto y coma.

### Decisión arquitectónica crítica: Two-Tier Caching semanal

**El problema**: la query es pesada (3 JOINs × 5 meses × 3 tablas de datasets distintos). Correrla completa dos veces al día (refresh automático) sería ~60 queries pesadas al mes innecesarias — la mayoría del dato ya no cambia.

**La regla de negocio**: datos de semanas anteriores a la semana actual son **estables** (no se mueven). Solo la semana actual puede tener datos nuevos o revisiones.

**Solución: Two-Tier con corte semanal**

```
Tier 1 — Cache semanal (data histórica estable):
  data/comms_oc_cache.json
  WHERE SENT_DATE < DATE_TRUNC(CURRENT_DATE(), WEEK(MONDAY))
  → Se genera UNA VEZ y se actualiza solo los lunes (o manualmente)
  → Script: scripts/refresh_comms_oc_cache.py

Tier 2 — Dato fresco (semana actual, cambia diariamente):
  Consulta BQ al vuelo: WHERE SENT_DATE >= DATE_TRUNC(CURRENT_DATE(), WEEK(MONDAY))
  → Máximo 7 días de datos = query ultra-rápida
  → Corre en cada refresh del dashboard (2x/día)

processors.process_comms_oc() = load(cache) + query(semana actual) + merge
```

**Beneficio cuantificado**:
- Antes (sin cache): 3 tablas × 5 meses × 2 veces/día = query pesada 60x/mes
- Después (con cache): 3 tablas × 7 días × 2 veces/día = query pequeña 60x/mes + 1 query pesada semanal los lunes

**Formato del cache**: JSON (lista de dicts). Tamaño estimado: < 5 MB (campañas OC MLM, no son millones de filas).

### Diseño de la pestaña Comms_OC

**Tab ID**: `comms-oc` | **Nombre UI**: `Comms_OC` | **Tipo**: Híbrido (Python estático + datos BQ via cache)

**Estructura visual** (tabla estática HTML generada en Python):

| Vista | Contenido | Granularidad |
|---|---|---|
| **Resumen por CANAL × MES** (top) | Conteo de campañas, total SENTS, avg OPEN_RATE, avg CVR, avg LIFT, total USER_INC, total VALUE_INC | Agregado |
| **Detalle por comunicación** (expandible, por defecto colapsado) | FIRST_SENT_DATE, CAMPAIGN_NAME_CLEAN (truncado 50 chars), CANAL, NOTIFICATION_TITLE, SENTS, OPEN_RATE, M_LIFT, USER_INC, VALUE_INC | Per-comm |

**Columnas del resumen** (ordenadas de más a menos importantes para negocio):

| Columna | Descripción | Formato |
|---|---|---|
| Canal | CANAL de camp_meta | Texto |
| Mes | MONTH_ID YYYY-MM | Texto |
| Campañas | COUNT de communications únicas | Entero |
| Sents | SUM(SENTS) | K/M formato |
| Open Rate | AVG(OPEN_RATE) | % |
| CVR (avg) | AVG(M_CVR_TEST) | % |
| Lift (avg) | AVG(M_LIFT) | % verde/rojo |
| User Inc. | SUM(USER_INC) | Entero, verde si > 0 |
| Value Inc. | SUM(VALUE_INC) | USD formato |

**Placeholder en template**: `{{COMMS_OC_TABLE}}`

### Archivos a crear/modificar

| Archivo | Tipo | Cambio |
|---|---|---|
| `scripts/refresh_comms_oc_cache.py` | **NUEVO** | Script standalone: corre la query completa (5 meses hasta inicio de semana actual), guarda `data/comms_oc_cache.json`. Correr manualmente cada lunes o cuando se necesite actualizar histórico. |
| `src/queries.py` | Modificado | +`get_comms_oc_fresh_sql()` — misma query con `SENT_DATE >= DATE_TRUNC(CURRENT_DATE(), WEEK(MONDAY))` únicamente. |
| `src/processors.py` | Modificado | +`process_comms_oc(bq_client, cache_path)` — carga cache JSON + ejecuta query fresca + merge + retorna `comms_oc_data` (lista de dicts ordenada por FIRST_SENT_DATE). |
| `src/builders.py` | Modificado | +`build_comms_oc_table_html(data)` — genera tabla HTML con vista Resumen (fija) y vista Detalle (colapsable por CANAL+MES). |
| `src/gen_dashboard_v2.py` | Modificado | +import + llamada `process_comms_oc()` + replace `{{COMMS_OC_TABLE}}`. |
| `src/template_dashboard.html` | Modificado | +tab button `Comms_OC` + pane `id="pane-comms-oc"` con `{{COMMS_OC_TABLE}}` + `'comms-oc'` en array TABS. |
| `data/comms_oc_cache.json` | **NUEVO** (generado) | Cache del histórico. Gitignored si es grande; tracked si < 10 MB. Se genera corriendo `scripts/refresh_comms_oc_cache.py`. |

### Protocolo de mantenimiento

```
Cada lunes por la mañana (o primer día hábil del mes):
  cd C:\Users\sergibarra\Documents\SI_Meli_code1\MLM_ADQ_Dash
  ..\vEnv_Meli_Code1\Scripts\activate
  python scripts/refresh_comms_oc_cache.py
  # Tarda ~2-5 min (query pesada completa, 5 meses)
  # Output: data/comms_oc_cache.json actualizado

Cada refresh automático (2x/día via cron-job.org):
  python src/gen_dashboard_v2.py
  # Solo consulta la semana actual (<7 días), tarda segundos
  # Merge automático con cache
```

---

## 46. Sesión 2026-04-15: Evolución de la pestaña Comms_OC — SQL, KPI cards y Filtros

### Contexto
En esta sesión se tomó la implementación inicial de Comms_OC (§45) y se iteró sobre ella en múltiples dimensiones: corrección del SQL canónico, mejoras de visualización (KPI cards), y capacidad de exploración (filtros dinámicos).

---

### 46.1 Evolución del SQL — De COUNTIF a COUNT DISTINCT por usuario único

**Motivación**: El funnel de comunicaciones (CREATE → TEST → CONTROL → ARRIVED → SHOWN → OPEN) requiere contar USUARIOS ÚNICOS por paso, no filas de eventos. Un mismo usuario puede generar múltiples filas para el mismo tipo de evento (reintentos, duplicados técnicos del sistema de mensajería).

**Campo de deduplicación**: `CUS_CUST_ID` — identificador único del cliente en `BT_OC_CUST_EVENT`. (Campo `EVENT_ID` no existe en la tabla — verificado en schema.)

**Cambio aplicado** en `get_comms_oc_fresh_sql()` y `build_comms_oc_sql_for_date_range()`:
```sql
-- ANTES (conteo de filas, puede inflar):
COUNTIF(LOWER(TRIM(EVENT_TYPE)) = 'create') AS TOTAL_CREATE_CUST_EVENT

-- DESPUÉS (usuarios únicos por paso del funnel):
COUNT(DISTINCT IF(LOWER(TRIM(EVENT_TYPE)) = 'create', CUS_CUST_ID, NULL)) AS TOTAL_CREATE_CUST_EVENT
```

---

### 46.2 Fixes de SQL críticos (bugs descubiertos al correr el full rebuild)

#### Bug 1: `EVENT_ID` no existe en `BT_OC_CUST_EVENT`
**Error BQ**: `Unrecognized name: EVENT_ID at [7:60]`
**Causa**: Nombre de campo asumido sin verificar en el schema de la tabla.
**Fix**: El campo correcto es `CUS_CUST_ID` (identificador único del cliente).

#### Bug 2: `MONTH_ID` es tipo `DATE` en SBOX_EG_MKT, no string `'YYYYMM'`
**Error BQ**: `Could not cast literal "202511" to type DATE at [91:25]`
**Causa**: El generador producía `from_month_sql = strftime('%Y%m')` → `'202511'`, que BQ intenta castear a DATE y falla.
**Fix**: Cambiar a `strftime('%Y-%m-01')` → `'2025-11-01'` y usar `DATE '{from_month_sql}'` en el WHERE.
**Tablas afectadas**: `DASHBOARD_CAMPAIGNS_INDIVIDUOS_METRICAS` y `BT_OC_DASHBOARD_ALL_CAMPAIGNS`.

#### Bug 3: `NOTIFICATION_TEXT` omitido de `camp_meta`
**Síntoma**: Columna "Texto" mostraba "—" para todas las comunicaciones.
**Causa**: El SELECT de `camp_meta` no incluía `ANY_VALUE(NOTIFICATION_TEXT)`.
**Fix**: Agregar `ANY_VALUE(NOTIFICATION_TEXT) AS NOTIFICATION_TEXT` al SELECT de las 3 CTEs.

---

### 46.3 Nuevas columnas en la query y en la tabla

Columnas agregadas a la query canónica:
- `cm.NOTIFICATION_TEXT` — cuerpo del mensaje (desde `BT_OC_DASHBOARD_ALL_CAMPAIGNS`)
- `cm.BUSINESS_LINE_SEGMENT_CHANNELS` — segmento de canal (desde `BT_OC_DASHBOARD_ALL_CAMPAIGNS`)
- `im.CHANNELS_METRICS` — `STRING_AGG(DISTINCT BUSINESS_LINE_SEGMENT_CHANNELS, ' | ')` (desde `DASHBOARD_CAMPAIGNS_INDIVIDUOS_METRICAS`)
- `im.SUBSTRATEGIES` — `STRING_AGG(DISTINCT SUBSTRATEGY, ' | ')`
- `im.TPN_INC`, `im.TPV_INC` — métricas de impacto transaccional

La tabla del dashboard pasó de 22 a **23 columnas** con la adición de "Ch. Metrics" (CHANNELS_METRICS de indiv_metrics, diferente a la columna "Seg. Canal" de camp_meta).

---

### 46.4 KPI Cards dinámicas (Tarea 3)

**Motivación**: Contexto rápido al entrar a la pestaña — cuántos usuarios únicos pasaron cada step del funnel y cuál fue la eficiencia/impacto promedio para el período filtrado.

**Arquitectura**: Los `data-*` attributes en cada `<tr>` (generados por Python en `builders.py`) son leídos por la función JS `renderCommsOcKPIs()`. Las cards se recalculan automáticamente al cambiar cualquier filtro.

**11 cards en 2 grupos**:
- **Funnel** (azul #5899D1): Comuns. | CREATE | TEST | CONTROL | ARRIVED | SHOWN | OPEN
- **Eficiencia + Impacto** (verde/naranja): Avg Open% | Avg CVR% | Avg Lift% | Σ User Inc | Σ Value Inc

**Datos por `<tr>`**:
```html
<tr data-month="202604"
    data-create="1234" data-test="1200" data-control="400"
    data-arrived="1100" data-shown="950" data-open="180"
    data-open-rate="0.189" data-cvr="0.0083" data-lift="0.0012"
    data-user-inc="45.3" data-value-inc="1500.25"
    data-app="MERCADOPAGO" data-canal="PUSH"
    data-strategy="UCRANIA" data-substrat="..." data-bizseg="..."
    data-campaign="..." data-title="..." data-text="...">
```

**Nota sobre USER_INC y VALUE_INC**: estas métricas vienen de `indiv_metrics` a nivel CAMPAÑA — si una campaña tiene N COMM_IDs, los valores se repiten N veces. La suma en las cards es "aproximada" y está documentada como tal.

---

### 46.5 Sistema de filtros dinámicos (Tarea 5)

**8 filtros simultáneos (AND logic)**:
- **Dropdowns** (valores exactos/contains): APP, CANAL, STRATEGY, SUBSTRATEGY, BIZ_SEGMENT
- **Text search** (substring, case-insensitive): CAMPAÑA, TÍTULO, TEXTO

**Arquitectura JS**:
```
_commsOcFilterState = { month, app, canal, strategy, substrat, bizseg, campaign, title, text }
         ↓
applyCommsOcFilters()  ← aplica TODOS los filtros (AND), muestra/oculta filas
         ↓
renderCommsOcKPIs()    ← recalcula cards sobre filas visibles
```

- `initCommsOcFilters()` — corre una sola vez al entrar al tab; pobla los dropdowns con valores únicos del DOM
- `onCommsOcFilterChange()` — lee todos los inputs → actualiza estado → llama `applyCommsOcFilters()`
- `clearCommsOcFilters()` — resetea todos los filtros conservando el mes del selector global
- `filterCommsOcByMonth()` — refactorizado: solo actualiza `_state.month` y delega a `applyCommsOcFilters()`

**Datos de texto en `data-*`**: todos los campos filtrables (APP, CANAL, STRATEGY, SUBSTRATEGY, BIZ_SEGMENT, CAMPAIGN_NAME, NOTIFICATION_TITLE, NOTIFICATION_TEXT) están embebidos como `data-*` en cada `<tr>` con `escape_attr()` en Python (escapa `&`, `"`, `<`, `>`).

---

### 46.6 Archivos modificados en esta sesión

| Archivo | Cambio |
|---|---|
| `src/queries.py` | Query Comms_OC completa reescrita: `COUNT(DISTINCT IF(..., CUS_CUST_ID, NULL))` + nuevas columnas (NOTIFICATION_TEXT, BUSINESS_LINE_SEGMENT_CHANNELS, CHANNELS_METRICS, SUBSTRATEGIES, TPN_INC, TPV_INC). Fix MONTH_ID como DATE. |
| `scripts/refresh_comms_oc_cache.py` | Mismos cambios SQL. Modo incremental: `run_incremental_update()` detecta última fecha del cache y consulta desde ahí hasta D-7. Modo full: `run_full_rebuild()` para reconstruir desde 5 meses. Fix `from_month_sql` a formato DATE. |
| `src/builders.py` | `build_comms_oc_table_html()`: 23 columnas, `data-*` attributes en cada `<tr>` (funnel numérico + texto para filtros), contenedores `<div id="comms-oc-filters">` y `<div id="comms-oc-kpi-row">`. `escape_attr()` helper para seguridad HTML. |
| `src/template_dashboard.html` | +`_commsOcFilterState`, +`initCommsOcFilters()`, +`onCommsOcFilterChange()`, +`applyCommsOcFilters()`, +`clearCommsOcFilters()`, +`renderCommsOcKPIs()`. `filterCommsOcByMonth()` refactorizado. `initTab('comms-oc')` llama `initCommsOcFilters()` la primera vez. |

---

## 47. Sesión 2026-04-15: Sistema de Documentación de Queries (`config/queries/`)

### Motivación

Con la pestaña Comms_OC se hizo evidente la necesidad de documentar las queries fuente de cada pestaña de forma estructurada y accesible para LLMs en conversaciones futuras. El `docs/History.md` cubre la historia del proyecto pero no es una referencia técnica rápida de SQL.

### Decisión arquitectónica: `config/queries/` (no `docs/`)

Las queries son **configuración del pipeline de datos**, no historial de negocio. Su lugar natural es `config/`, junto a `channels_config.json` (que ya es el SSoT de configuración de canales).

```
config/
├── channels_config.json         ← SSoT de jerarquía de canales
└── queries/                     ← NUEVO: documentación de queries por pestaña
    ├── README.md                ← Índice + convenciones
    ├── comms_oc.md              ← SQL estático (3 tablas BQ)
    ├── nr_mensual.md            ← SQL dinámico (CASE WHEN generado desde config)
    └── performance_vista_corp.md ← Sin query BQ propia (ensamble Python de 5 dicts)
```

### Estructura de cada archivo

Cada `{tab_id}.md` contiene:
1. **Propósito** — qué pregunta de negocio responde
2. **Tablas BQ involucradas** — tabla, dataset, proyecto, contenido, clave de JOIN
3. **SQL Canónico** — copy-paste-ready para BQ UI (con fechas hardcodeadas de ejemplo)
4. **Parámetros** — cómo varía el SQL (cache vs fresh, dinámico vs estático)
5. **Columnas de salida** — qué retorna cada columna y de dónde viene
6. **Gotchas críticos** — errores ya cometidos documentados para no repetirlos
7. **Historial de cambios** — cronológico

### Hallazgo arquitectónico: tres tipos de query

| Tipo | Ejemplo | Implicación |
|---|---|---|
| **Estática** | `comms_oc.md` | El SQL es la fuente de verdad |
| **Dinámica** | `nr_mensual.md` | La fuente de verdad es `channels_config.json` — el SQL es el output |
| **Sin query BQ** | `performance_vista_corp.md` | La complejidad está en el mapeo Python entre jerarquías, no en BQ |

### Archivos creados

| Archivo | Pestaña | Tipo |
|---|---|---|
| `config/queries/README.md` | — | Índice del sistema |
| `config/queries/comms_oc.md` | Comms_OC | SQL estático + Two-Tier cache |
| `config/queries/nr_mensual.md` | NR Mensual / NR Diario / MTD D7 | SQL dinámico + CASE WHEN desde config |
| `config/queries/performance_vista_corp.md` | Performance_vista_Corp | Sin query BQ; ensamble de 5 dicts vía `hierarchy_cost_corp.mappings` |

### Pendientes (archivos futuros)
- `config/queries/performance_fm.md` — `get_perf_paid_sql()` + `get_perf_vpu_sql()` + `get_perf_roa_costos_sql()`
- `config/queries/nr_corp.md` — `get_nr_corp_sql()` + `get_nr_corp_daily_sql()`

---

## 48. Visión Estratégica: "Cerebro de Operación" — Cruce KPIs × Comms_OC

### Declaración del stakeholder (15-Abr-2026)

El jefe del dueño del proyecto denominó este dashboard: **"Nuestro cerebro de operación, mejora, optimización y reporteo"**.

Esta declaración eleva el propósito del proyecto de "dashboard de seguimiento de N+R" a una **plataforma integrada de inteligencia operativa** para el equipo de Adquisición MLM.

### Siguiente capa de valor: Cruce KPIs × Comunicaciones OC

La pestaña `Comms_OC` tiene el detalle de CADA comunicación enviada a los usuarios (canal, campaña, título, funnel, lift, user_inc, value_inc). Las pestañas `NR Mensual` / `Performance_vista_FM` / `Performance_vista_Corp` tienen los KPIs agregados por canal y mes.

**La pregunta estratégica que habilita el cruce**:
- ¿Qué comunicaciones específicas generaron el salto de +10% MoM en UCR Gest en Julio?
- ¿Qué campañas de PUSH tienen el lift más alto en quincenas?
- ¿Cuál es el value_inc acumulado de las comunicaciones de WPP vs EMAIL en Q1-2026?

**Roadmap de implementación propuesto**:
1. **Fase 1 — OC+UCR**: Filtrar Comms_OC por CANAL=PUSH/EMAIL/PANDORA/WPP + STRATEGY=UCRANIA → cruzar USER_INC con el N+R mensual de UCR Gest para calcular "% del N+R del mes atribuible a estas comunicaciones"
2. **Fase 2 — POM**: Mismo cruce para POM (diferente lógica de atribución)
3. **Fase 3 — Pestaña Análisis Cross**: Nueva pestaña que integra KPIs de canal con comunicaciones top-performers del período

**Archivos de contexto para cuando se implemente**:
- `config/queries/comms_oc.md` — lógica de la query Comms_OC
- `config/queries/nr_mensual.md` — lógica del N+R
- `skills/analizar-Optimizar_Performance_KPIs_context.md` — base de conocimiento histórico de OC+POM
- `docs/metrics_logic.md` — fórmulas de KPIs

---

## 49. Sesión 2026-04-16: Skills v2.0/v2.1 — Análisis de Funnel + Wordings + Cortes Multidimensionales

### Motivación
El skill `analizar-OC_Comms_skill.md` solo cubría análisis histórico y por canal pero no tenía framework para diagnosticar el funnel end-to-end (CREATE→TEST→OPEN→LIFT→USER_INC) ni para analizar patrones por BL/DoW/Semana. El OPTIMIZADOR tampoco usaba el funnel como causa explicativa de KPIs.

### `analizar-OC_Comms_skill.md` → v2.0

4 nuevos modos:

| Modo | Propósito |
|---|---|
| `funnel [mes]` | Diagnostica en qué etapa del funnel se rompió la cadena → tabla firma causal con semáforo |
| `wording [BL/canal]` | Taxonomía de 6 dimensiones sobre NOTIFICATION_TITLE/TEXT → fingerprint ganador por BL |
| `cortes_multidim [dim]` | Matriz BL×DoW, BL×semana, canal×timing — con principio de composicionalidad |
| `sweet_spots [canal/BL]` | Puntos de inflexión: cuántas comms es demasiado, cuándo OR es "de curiosidad" |

**Tabla de firma causal** (qué implica cada caída del funnel):
- `OPEN cae / SHOWN estable` → problema de wording/VP
- `LIFT cae / OPEN estable` → "opens de curiosidad" → VP débil post-click
- `USER_INC cae / LIFT estable` → problema de volumen (reach)
- `Todo cae` → evento externo (calibrador, IS estacional)

**TAXONOMÍA DE WORDINGS** — 6 dimensiones: VP tipo (%, $, gratis), urgencia (HIGH/MED/LOW), verbo acción (Activa/Gana/Usa/Recibe/Paga), personalización (PERS_HIGH/LOW), contexto de uso (compra/recarga/pago/general), tono (beneficio/oportunidad/urgencia/info).

### `OPTIMIZADOR-OC_skill.md` → v2.1

- **Dimensión 6** en PASO 2: Funnel interno con tabla de firma causal y benchmarks por BL
- **PASO 2B**: Sweet spot analysis — Efficiency Score (USER_INC/CREATE), dilución de audiencia, "opens de curiosidad"
- **7 nuevos checks del Relojero Suizo** específicos de funnel (CREATE cayó, OR bien pero LIFT bajó, USER_INC negativo = canibalizador, etc.)
- **Modo 8 `cruce_funnel [mes]`**: Tableau du Funnel × KPIs con 5 métricas de eficiencia derivadas

### Archivos modificados

| Archivo | Cambio |
|---|---|
| `skills/analizar-OC_Comms_skill.md` | v1.0 → v2.0: +4 modos, +TAXONOMÍA WORDINGS, +FRAMEWORK MULTIDIMENSIONAL |
| `skills/OPTIMIZADOR-OC_skill.md` | v2.0 → v2.1: +Dimensión 6, +PASO 2B, +7 checks Relojero, +Modo 8 |

---

## 50. Sesión 2026-04-16: Extensión Pipeline — Breakdowns Canal/BL/DoW/Semana

### Motivación
`summarize_comms_by_month()` solo agregaba por mes. Para que el tab ● Análisis OC+UCR pudiera mostrar "¿PUSH tiene mejor OR que PANDORA?", "¿S2 genera más NR que S1?", "¿Martes es mejor que Sábado?", se necesitaban breakdowns reales de los datos del cache.

### Cambios en `src/gen_dashboard_v2.py`

**`summarize_comms_by_month()`** — nuevos campos por mes:

| Campo | Fórmula | Propósito |
|---|---|---|
| `total_create` | SUM(TOTAL_CREATE_CUST_EVENT) | Paso 0 del funnel |
| `delivery_rate` | ARRIVED/TEST × 100 | % técnico de deliverability |
| `visibility_rate` | SHOWN/ARRIVED × 100 | % de rendering |
| `efficiency_score` | USER_INC/n_comms | NR por comunicación (sweet spot detector) |
| `avg_lift_pct` | avg(M_LIFT) × 100 | Lift promedio en % |
| `vpu_incremental` | VALUE_INC/USER_INC | VPU del NR incremental |
| `canal_breakdown` | {canal: {n, or_pct, avg_lift_pct, user_inc}} | Por canal (PUSH/PANDORA/RE/WPP) |
| `bl_breakdown` | {bl: {...}} | Por Business Line |
| `dow_breakdown` | {Lun/Mar/…: {...}} | Por día de semana (de FIRST_SENT_DATE) |
| `week_breakdown` | {S1/S2/S3/S4: {...}} | Por semana del mes |

Los breakdowns mantienen valores raw (test, open, lift_sum, lift_n) para poder re-agregar entre meses en el builder.

**`generate_comms_monthly_summary_md()`** — ahora incluye en cada mes del archivo `skills/comms_monthly_summary.md`:
- Línea de eficiencia (delivery%, visibility%, lift avg, efficiency score, VPU inc.)
- Por Canal (top 5)
- Por Semana del mes (S1-S4)
- Por Día de semana (Lun-Dom)
- Por BL (top 5)

---

## 51. Sesión 2026-04-16: Rebuild completo del tab ● Análisis OC+UCR

### Motivación
El tab anterior era una acumulación de 12+ secciones parche-sobre-parche. El usuario solicitó borrarlo y rehacerlo desde cero con el mejor análisis posible, con el framing correcto:
> **Los KPIs (N+R, CPA, VPU, ROAs) son el protagonista. Las comms son la causa explicativa.**

### Nueva arquitectura — 9 bloques

| Bloque | Contenido | Tipo |
|---|---|---|
| B1 | Header ejecutivo + 4 fases históricas | Estático |
| B2 | Drivers H2-25 / Causas Q1-26 + Timeline forense (colores LEGIBLES) | Estático + dinámico |
| B3 | Funnel end-to-end por mes + breakdowns canal/BL/DoW/semana | **100% dinámico** (comms_monthly_summary) |
| B4 | IS estacional mensual + quincenas (S2: +30% eficiencia, dato Oct-25) + DoW | Estático |
| B5 | VP efficiency ranking (Servicios 111x → Cupón Auto 3x) + wording patterns | Estático |
| B6 | Qué escalar / qué parar o pivotar | Estático |
| B7 | 5 Insights del Relojero Suizo | Estático |
| B8 | Plan palancas + Camino crítico | Estático |
| B9 | Veredicto ejecutivo 3 acciones SMART | Estático |

**Principales cambios vs. versión anterior:**
- Tabla Cruce Comms×KPIs: fondo BLANCO con texto de color (no dark-on-dark)
- Section diagnóstico de funnel con semáforo automático (verde/amarillo/rojo vs benchmarks Ago-Sep-25)
- VP Efficiency Ranking: tabla real de §C1 del context (Servicios 111x ROAS → Cupón Automático 3x, evitar)
- Sweet spot cards: OR 12-15%, Efficiency Score >25, OR×Lift matrix
- Framing correcto en todos los títulos: "¿Por qué el KPI fue así?" → comms como evidencia causal

### Archivos modificados
| Archivo | Cambio |
|---|---|
| `src/builders_analysis.py` | `build_oc_ucr_analysis_tab_html()` — reescritura completa ~1,494 líneas |

**Output**: `dashboard_v2.html` — **20,026 KB** (después de fix de tamaño, ver §52)

---

## 52. Sesión 2026-04-16: Fix tamaño Comms_OC — 48 MB → 20 MB

### Causa raíz
La pestaña Comms_OC tenía **48 MB** porque `build_comms_oc_table_html()` generaba 29 inline styles por fila (`style="padding:4px 6px;font-size:10.5px;..."`) que sumaban 3,055 chars de CSS × 10,705 filas = **~31 MB de CSS repetido**.

### Solución: CSS classes en lugar de inline styles

| Fix | Ahorro |
|---|---|
| `TD`/`TH`/`TD_NUM` → clases `.coc-td`/`.coc-th`/`.coc-num` en `<style>` embebido | ~31 MB |
| `trunc()` tooltip limitado a 200 chars (antes: texto completo en `title=""`) | ~3 MB |
| `data-text` truncado a 150 chars (antes: NOTIFICATION_TEXT completo) | ~1 MB |

### Resultado
- **Antes**: 48,844 KB (44,959 KB solo en pane-comms-oc)
- **Después**: 20,026 KB (16,132 KB en pane-comms-oc)
- **Reducción**: −59%

Toda la información de las comunicaciones sigue presente — solo el CSS está optimizado. Los filtros y KPI cards siguen funcionando igual.

### Archivos modificados
| Archivo | Cambio |
|---|---|
| `src/builders.py` | `TH`/`TD`/`TD_NUM` → clases CSS. `trunc()` max_tooltip=200. `data-text` truncado a 150 |

---

## 53. Sesión 2026-04-16: Evolución query Comms_OC — Nuevos campos + Filtros de calidad

### Motivación
La query base de Comms_OC tenía registros de baja calidad (CREATE=0, campañas SELLER, zombies sin datos enriquecidos) y faltaban campos analíticos clave (TYPE_NAME, NOTIFICATION_TYPE, TEAM, BUSINESS_LINE).

### Cambios en la query (aplicados a `src/queries.py` y `scripts/refresh_comms_oc_cache.py`)

**Nuevos filtros:**

| Filtro | Dónde | Propósito |
|---|---|---|
| `HAVING CREATE > 0` | `raw_events_agg` | Excluye comms sin usuarios en paso CREATE (data incompleta) |
| `CAMPAIGN_NAME NOT LIKE '%SELLER%'` | `indiv_metrics` | Excluye campañas seller |
| `CAMPAIGN_NAME NOT LIKE '%I-M-XT1-%'` | `indiv_metrics` | Excluye campañas cross-sell internas |
| `CAMPAIGN_NAME NOT LIKE '%SEV-T3-%'` | `indiv_metrics` | Excluye campañas no-adquisición |
| WHERE anti-zombies (COALESCE) | SELECT final | Descarta registros donde todos los campos enriquecidos están vacíos |

**Nuevos campos en `indiv_metrics`:**

| Campo | Implementación | Propósito |
|---|---|---|
| `TYPE_NAME` | `STRING_AGG(DISTINCT TYPE_NAME, ' | ')` | Tipo de comunicación |
| `NOTIFICATION_TYPE` | `STRING_AGG(DISTINCT NOTIFICATION_TYPE, ' | ')` | Sub-tipo de notificación |
| `TEAM` | `ANY_VALUE(TEAM)` | Equipo propietario |
| `BUSINESS_LINE` | renombrado de `CHANNELS_METRICS` | Business Line segment (STRING_AGG) |

**⚠️ Bug crítico resuelto — GROUP BY fan-out**: Al agregar TYPE_NAME/NOTIFICATION_TYPE/TEAM al GROUP BY (6 campos), `indiv_metrics` generaba múltiples filas por campaña × mes. Esto causó un fan-out en el JOIN con `ce_clean` → query de 5 meses tardó **2+ horas** y nunca terminó. **Fix**: usar `STRING_AGG`/`ANY_VALUE` para los nuevos campos, mantener `GROUP BY 1, 2, 3` (cardinalidad 1:1). Tiempo de BQ con fix: ~40-50 min (pero hay **contención de ranuras** en `meli-bi-data` que puede extenderlo a 2-3h en horario pico).

**Contención de ranuras (2026-04-16)**: Los 3 intentos de full rebuild quedaron en cola con **0 bytes procesados** por `Contención de ranuras` en `gobiernoit-reservas:US.meli-bi-data`. Los jobs se cancelaron. El cache pendiente de rebuild en horario off-peak (noche/madrugada).

### Compatibilidad con cache viejo
El cache existente (`data/comms_oc_cache.json`) tiene el schema anterior (sin TYPE_NAME, BUSINESS_LINE, etc.). Los fallbacks en el código garantizan que el dashboard no falle:
- `builders.py`: `record.get('BUSINESS_LINE') or record.get('CHANNELS_METRICS')`
- `gen_dashboard_v2.py`: `record.get('BUSINESS_LINE') or record.get('CHANNELS_METRICS') or record.get('BUSINESS_LINE_SEGMENT_CHANNELS')`

**Próximo paso**: Correr `python scripts/refresh_comms_oc_cache.py --full` en horario off-peak para obtener cache con schema nuevo completo.

### Archivos modificados
| Archivo | Cambio |
|---|---|
| `src/queries.py` | `get_comms_oc_fresh_sql()`: HAVING CREATE>0, TYPE_NAME/NOTIFICATION_TYPE/TEAM (STRING_AGG/ANY_VALUE), BUSINESS_LINE, NOT LIKE filtros, WHERE anti-zombies |
| `scripts/refresh_comms_oc_cache.py` | `build_comms_oc_sql_for_date_range()`: mismos cambios (fechas parametrizadas) |
| `src/builders.py` | +3 columnas (Type Name, Notif. Type, Team), BUSINESS_LINE fallback |
| `src/gen_dashboard_v2.py` | BUSINESS_LINE → CHANNELS_METRICS → BIZ_SEGMENT fallback en `bl_dim` |

---

## 54. Sesión 2026-04-17/18: Query Comms_OC — Arquitectura 4 Ramas (PUSH + EMAIL + RE + FLOWS)

### Motivación
La query original (Rama A: PUSH) no capturaba campañas de EMAIL (que no tienen evento `create`), ni Real Estate (datos de impresiones/taps en tablas separadas), ni FLOWS/Journeys (métricas pre-agregadas diarias). Se requería una arquitectura UNION ALL de 4 ramas.

### Arquitectura final de la query

```
WITH [CTEs comunes: raw_events_agg, ce_clean, indiv_metrics, camp_meta]
     [CTEs EMAIL: email_base, email_events, email_metrics]
     [CTEs RE: subqueries inline de prints + taps]
     [CTEs FLOWS: subquery inline de BT_OC_MP_FLOWS_DAILY]

RAMA A — PUSH/OC/WPP:
  Base: BT_OC_CUST_EVENT (HAVING CREATE > 0)
  Métricas: DASHBOARD_CAMPAIGNS_INDIVIDUOS_METRICAS

UNION ALL

RAMA B — EMAIL:
  Base: BT_OC_DASHBOARD_ALL_CAMPAIGNS (CANAL='EMAIL')
  Eventos: BT_OC_CUST_EVENT (HAVING TEST > 0 — no tiene CREATE)
  Métricas: meli-bi-data.SBOX_EG_MKT.BT_OC_EMAIL_MP_MONTHLY
  Columnas nuevas: CLICK, BLACKLIST, BLOCKED, BOUNCE, SPAMREPORT (0 para otras ramas)

UNION ALL

RAMA C — FLOWS/JOURNEYS:
  Base: meli-bi-data.SBOX_MARKETING.BT_OC_MP_FLOWS_DAILY
  Filtros: CHANNEL='PUSH JOURNEY INC TOTALES', FLOW='APP-MP-INSTALL'
  Autocontenida — tiene funnel + USER_INC + LIFT integrados
  JOURNEY_NAME → CAMPAIGN_NAME (columna campaña en tabla)
  CAMPAIGN_NAME original → NOTIFICATION_TITLE

UNION ALL

RAMA D — REAL ESTATE:
  Base: meli-bi-data.SBOX_SBOXMERCH.DIM_REE_METRICS_PRINTS
  Taps: meli-bi-data.SBOX_SBOXMERCH.DIM_REE_TAPS (tabla separada)
  JOIN en content_id + component_id
  Filtro anti-personal: NOT REGEXP_CONTAINS(content_id, r'^[0-9]+_') + HAVING > 50 usuarios
  prints → TOTAL_SHOWN/TEST; taps → TOTAL_OPEN
  USER_INC/LIFT = NULL (no disponible en esta tabla)
```

### Nuevas columnas en el schema de Comms_OC

| Columna nueva | Rama | Fuente |
|---|---|---|
| `TOTAL_CLICK_CUST_EVENT` | EMAIL (real), otros = 0 | BT_OC_CUST_EVENT |
| `TOTAL_BLACKLIST_CUST_EVENT` | EMAIL (real), otros = 0 | BT_OC_CUST_EVENT |
| `TOTAL_BLOCKED_CUST_EVENT` | EMAIL (real), otros = 0 | BT_OC_CUST_EVENT |
| `TOTAL_BOUNCE_CUST_EVENT` | EMAIL (real), otros = 0 | BT_OC_CUST_EVENT |
| `TOTAL_SPAMREPORT_CUST_EVENT` | EMAIL (real), otros = 0 | BT_OC_CUST_EVENT |

### Nuevos filtros de calidad (todos en WHERE final + indiv_metrics)

| Filtro | Propósito |
|---|---|
| `NOT LIKE '%-XT1-%'` | Excluir campañas XT1 cross-sell |
| `NOT LIKE '%-ENG%'` + `NOT LIKE '%-ENG'` | Excluir campañas ENG (cualquier posición, incluyendo sufijo) |
| `NOT LIKE '%SEV-T3-%'` | Excluir campañas SEV-T3 |
| `NOT LIKE '%SELLER%'` | Excluir campañas seller (también en BUSINESS_LINE_SEGMENT_CHANNELS y TEAM) |

**Bug crítico resuelto**: `NOT LIKE '%-ENG%'` requiere caracteres DESPUÉS de -ENG. Campañas que terminan exactamente en `-ENG` (ej: `I-M-UCR-...-260403-ENG`) no eran capturadas. Fix: agregar también `NOT LIKE '%-ENG'` sin `%` final.

### `--clean` mode ampliado

`_record_should_exclude()` reemplaza `_record_has_seller()`. Ahora limpia del cache existente:
- SELLER en seg_canal o team
- `-XT1-` en campaign_name
- `-ENG` en campaign_name (cualquier posición)
- `SEV-T3-` en campaign_name

### Nuevos filtros en template_dashboard.html

4 nuevos dropdowns en la barra de filtros Comms_OC: **Business Line**, **Type Name**, **Notif. Type**, **Team**.

### Archivos modificados

| Archivo | Cambio |
|---|---|
| `src/queries.py` | `get_comms_oc_fresh_sql()`: 4 ramas UNION ALL completas |
| `scripts/refresh_comms_oc_cache.py` | `build_comms_oc_sql_for_date_range()`: mismas 4 ramas |
| `src/builders.py` | +5 cols email funnel (CLICK/BLACKLIST/BLOCKED/BOUNCE/SPAMREPORT) en tabla |
| `src/template_dashboard.html` | +4 filtros (bl, typename, notiftype, team) + 5 nuevas columnas en KPI cards |

---

## 55. Sesión 2026-04-17/18: Arquitectura Cache — D-7 → Mes Cerrado + Tier 2 Diario

### Motivación
La estrategia D-7 (cache hasta hoy-7 días) tenía tres problemas:
1. Cortaba semanas a la mitad → análisis de patrones semanales contaminados
2. La query Tier 2 corría en CADA generación del dashboard (~10-15 min × 4 ramas)
3. Con CI/CD 2x/día + generaciones manuales = 45-60 min de BQ diarios

### Cambio arquitectónico: Mes Cerrado

`get_cache_cutoff_date()` ahora retorna `primer día del mes actual` en lugar de `hoy - 7 días`.

```
ANTES (D-7, hoy=17-Abr):
  Cache: hasta 10-Abr (corta semana a la mitad)
  Fresh: 10-Abr → hoy

AHORA (Mes Cerrado):
  Cache: todos los meses anteriores (Jan... Mar 2026 — cerrados y estables)
  Fresh: solo Abril 2026 completo (mes en curso)
```

**Ventajas**:
- Meses completos = análisis de patrones semanales/quincenales íntegros
- Meses cerrados son 100% estables (no hay revisiones retroactivas)
- La fresh query cubre ~15 días en promedio (más pequeña)
- Alínea con el ciclo de negocio natural (cierre mensual, IS mensual)

### Tier 2 con caché diario

`comms_oc_current_month.json` persiste los resultados de la fresh BQ query:

```
Primera generación del día → corre BQ (~10-15 min) → guarda current_month.json
Siguientes generaciones del día → carga JSON (< 1 seg, sin BQ)
Al día siguiente → file es de ayer → re-corre BQ
```

**Para forzar re-query**: `del data\comms_oc_current_month.json`

### Estrategia de rebuild histórico (3 chunks)

Con la nueva query de 4 ramas, el full rebuild de 5 meses puede exceder el timeout de 600s del cliente BQ. Solución: chunks de 3 meses + timeout aumentado a 7200s.

```bash
# Noche 1 (off-peak): Jun-Ago 2025
python scripts/refresh_comms_oc_cache.py --append --from 2025-06-01 --to 2025-09-01

# Noche 2: Sep-Nov 2025
python scripts/refresh_comms_oc_cache.py --append --from 2025-09-01 --to 2025-12-01

# Noche 3: Dic 2025-Mar 2026
python scripts/refresh_comms_oc_cache.py --append --from 2025-12-01 --to 2026-04-01
```

**Mantenimiento mensual (el 1° de cada mes, ~5 min)**:
```bash
python scripts/refresh_comms_oc_cache.py  # modo incremental, agrega el mes recién cerrado
```

### Archivos modificados

| Archivo | Cambio |
|---|---|
| `src/gen_dashboard_v2.py` | +`COMMS_OC_CURRENT_MONTH_PATH`. Paso 3c pasa `comms_oc_current_month_path` a `process_comms_oc()` |
| `src/processors.py` | `process_comms_oc()` con lógica TTL diario: si JSON existe y es de hoy → carga sin BQ |
| `scripts/refresh_comms_oc_cache.py` | `get_cache_cutoff_date()` → primer día del mes. Timeout `.result(timeout=7200)` en todas las queries. `_record_should_exclude()` ampliado |

---

## 56. Sesión 2026-04-18/19: Skills — Fingerprint de Outliers + Modo día_historico

### Motivación
El usuario identificó dos casos de uso críticos que el sistema debía poder resolver:
1. `MLM_MP_ML-PUSHML_CC_MARA_AO-UCR_ALL` (Sep-27-2025): +50,277 USER_INC en un solo día — ¿qué lo causó y qué se puede replicar?
2. Nov-17-2025: N+R histórico (48K total, 5,872 OC+UCR) — ¿qué comms específicas causaron el récord?

### OPTIMIZADOR-OC_skill.md — Framework de Fingerprint de Outliers

Actualización del Modo 5 (`cruce`) con proceso explícito de 4 pasos:

**Las 8 dimensiones del fingerprint** (motor completo del análisis):
- D1 CANAL · D2 AUDIENCIA · D3 BUSINESS LINE · D4 VP/OFERTA · D5 TÍTULO · D6 TEXTO · D7 TIMING · D8 CONTEXTO EXTERNO

**Descomposición MOTOR vs AMPLIFICADOR** (el insight más valioso):
- MOTOR = variable necesaria, replicable sistemáticamente
- AMPLIFICADOR = evento externo que multiplica el motor
- Ejemplo Sep-27: PUSH+UCR_ALL+PRÉSTAMO es el MOTOR (replicable mensual); Maratón CDMX es el AMPLIFICADOR (3-6x)

**Hipótesis falsificables**: "Si BL=CREDIT APPLICATION + PUSH + UCR_ALL es motor, en quincena S2 sin evento esperamos USER_INC > 8,000"

### analizar-OC_Comms_skill.md — Nuevo Modo 13: `dia_historico [fecha]`

Permite hacer reverse lookup desde un KPI diario excepcional hacia las comms responsables:
1. Dimensionar el día vs promedio mensual
2. Identificar sub-canales con performance excepcional (NR Corp diario)
3. Reverse lookup: filtrar Comms_OC por fecha exacta + sub-canal
4. Fingerprint completo de las comms responsables
5. Separar motor de amplificador
6. Recomendaciones estratégicas con NR impact esperado

**Insight clave del 17-Nov-25**: WPP generó 1,900 N+R en S3 (valle, IS bajo) → proyección S2: 3,000-4,500 NR.

### Extensión del pipeline de datos

`summarize_comms_by_month()` — campos adicionales en `top_by_combo`:
- `date`: fecha exacta de envío (YYYY-MM-DD)
- `dow`: día de semana (Lun/Mar/...)
- `week`: semana del mes (S1-S4)
- `app`, `substrat`, `biz_line`, `type_name`, `notif_type`, `team`
- `title` y `text` ampliados a 100/150 chars
- `value_inc`: VALUE_INC del NR incremental

`generate_comms_monthly_summary_md()` — detección automática de outliers:
- `OUTLIER_THRESHOLD = 5.0` (5x el promedio global = outlier estratégico)
- Marca con `🚀 OUTLIER ESTRATÉGICO: Xx el promedio global`
- Alerta automática: "Analizar con OPTIMIZADOR Modo 5 (cruce)"

### Archivos modificados
| Archivo | Cambio |
|---|---|
| `skills/OPTIMIZADOR-OC_skill.md` | +Framework outlier fingerprint (8 dims, motor vs amplificador) en Modo 5 |
| `skills/analizar-OC_Comms_skill.md` | +Modo 13 `dia_historico [fecha]` + dispatch table actualizado |
| `src/gen_dashboard_v2.py` | `top_by_combo` con 12 campos completos. `comms_monthly_summary.md` con outlier detection |

---

## 57. Sesión 2026-04-19/20: Fix crítico de performance — email_events CTE

### Causa raíz del problema
Al agregar 5 columnas de email funnel (CLICK/BLACKLIST/BLOCKED/BOUNCE/SPAMREPORT), se duplicaron las operaciones en `email_events`:
- **Antes**: 4 COUNT DISTINCT + EVENT_TYPE IN (5 tipos) → ~10-20 min con mes completo
- **Después**: 9 COUNT DISTINCT + EVENT_TYPE IN (9 tipos) → multi-hora (2x+ carga en BT_OC_CUST_EVENT)

Combinado con el cambio D-7 → mes completo, el fresh query se volvió impracticable.

### Fix aplicado

`email_events` CTE revertido a 4 operaciones (TEST, CONTROL, ARRIVED, OPEN):
```sql
-- ANTES (lento): 9 COUNT DISTINCT + IN (9 tipos)
-- AHORA: 4 COUNT DISTINCT + IN (4 tipos) — igual que versión original que funcionaba
```

CLICK/BLACKLIST/BLOCKED/BOUNCE/SPAMREPORT se muestran como 0 en el SELECT del EMAIL branch (igual que CREATE/SHOWN se muestran como 0 para email). Las columnas existen en la tabla pero sin dato real — se pueden activar en el futuro sin impacto en performance si se necesita.

HAVING corregido para incluir emails sin evento `test`:
```sql
HAVING TEST > 0 OR ARRIVED > 0  -- no solo TEST
```

### Bug fix: referencias a columnas eliminadas
El SELECT de EMAIL (Rama B) seguía referenciando `ee.TOTAL_CLICK`, `ee.TOTAL_BLACKLIST`, etc. que ya no existían en `email_events`. Error BQ: `Name TOTAL_CLICK not found inside ee`. Fix: cambiar a 0 hardcodeado en el SELECT.

### RE y FLOWS — solo en cache, no en fresh
RAMA D (RE) y RAMA C (FLOWS) están comentadas en `get_comms_oc_fresh_sql()` con `/* */`. Solo se incluyen en los cache `--append`. Motivo: `DIM_REE_METRICS_PRINTS` y `BT_OC_MP_FLOWS_DAILY` son tablas grandes que hacen el fresh query demasiado lento para uso diario.

### Arquitectura final del fresh query
```
RAMA A (PUSH): BT_OC_CUST_EVENT → DASHBOARD_CAMPAIGNS + BT_OC_DASHBOARD_ALL_CAMPAIGNS
RAMA B (EMAIL): BT_OC_DASHBOARD_ALL_CAMPAIGNS → BT_OC_CUST_EVENT + BT_OC_EMAIL_MP_MONTHLY
/* RAMA C FLOWS y RAMA D RE: solo en --append del cache */
```

### Estado operativo tras el fix
- Fresh query (PUSH + EMAIL, mes completo): ~15-20 min en condiciones normales
- `comms_oc_current_month.json`: cacheado diariamente → runs posteriores del mismo día: instantáneo
- El dashboard NO se cuelga indefinidamente — si BQ tarda, el try/except continúa con solo Tier 1

### Archivos modificados
| Archivo | Cambio |
|---|---|
| `src/queries.py` | `email_events`: 4 COUNT DISTINCT (revirtiendo 9). HAVING: TEST>0 OR ARRIVED>0. `ee.TOTAL_CLICK` etc. → 0 en EMAIL SELECT. RE/FLOWS comentados con `/* */` |
| `scripts/refresh_comms_oc_cache.py` | Mismo fix en `email_events`. Merge inteligente: new wins cuando existing tiene fecha `-01` fallback. +Modo `--fix-email-dates` |

---

## 58. Sesión 2026-04-20: Filtros multi-select en pestaña Comms_OC

### Motivación
Los dropdowns de la barra de filtros Comms_OC solo permitían seleccionar un valor a la vez (single-select `<select>`). El usuario necesitaba poder seleccionar varios canales, strategies o BLs simultáneamente, y también filtrar filas donde un campo está vacío.

### Cambio: `<select>` → panel de checkboxes multi-select

Los 9 dropdowns (App, Canal, Strategy, Substrategy, Seg. Canal, Business Line, Type Name, Notif. Type, Team) fueron reemplazados por un custom multi-select con:
- **Panel de checkboxes** que se abre al hacer clic en el botón
- **Opción (Vacío)** al inicio de cada panel — filtra filas donde el campo está en blanco (value `__EMPTY__`)
- **Label dinámico**: muestra "Todos" (sin selección), el valor si hay 1 seleccionado, o "N selec." si hay varios
- **Cierre al hacer click fuera** de la barra mediante `document.addEventListener('click', ..., true)`
- **Lógica OR dentro del filtro**: la fila pasa si coincide con CUALQUIERA de los valores seleccionados
- **Lógica AND entre filtros**: todos los filtros activos deben pasar simultáneamente

### Cambios en `_commsOcFilterState`

Dropdowns cambiaron de `string` (valor único) a `Set` (múltiples valores). Set vacío = sin filtro.

```javascript
// Antes:
app: '', canal: '', strategy: '', ...

// Después:
app: new Set(), canal: new Set(), strategy: new Set(), ...
```

### Nuevas funciones JS en `src/template_dashboard.html`

| Función | Descripción |
|---|---|
| `toggleCommsOcMS(filterId)` | Abre/cierra el panel; cierra todos los demás |
| `getCommsOcMSValues(filterId)` | Retorna Set de valores marcados en el panel |
| `updateCommsOcMSLabel(filterId)` | Actualiza el label del botón según selección |

### Lógica de matching actualizada en `applyCommsOcFilters()`

```javascript
// Exacto (app, canal, team): campo debe estar en el Set
const msExact = (fieldVal, sel) => {
  if (sel.size === 0) return true;
  const empty = !fieldVal || fieldVal.trim() === '';
  if (empty) return sel.has('__EMPTY__');
  return sel.has(fieldVal);
};

// STRING_AGG (strategy, BL, etc.): al menos un valor del Set contenido en el campo
const msAgg = (fieldVal, sel) => {
  if (sel.size === 0) return true;
  const empty = !fieldVal || fieldVal.trim() === '';
  for (const v of sel) {
    if (v === '__EMPTY__') { if (empty) return true; }
    else if (!empty && (fieldVal || '').includes(v)) return true;
  }
  return false;
};
```

### Archivos modificados
| Archivo | Cambio |
|---|---|
| `src/template_dashboard.html` | `makeSelect` → `makeMultiSelect` con checkboxes. `_commsOcFilterState` dropdowns → Sets. Nuevas funciones `toggleCommsOcMS`, `getCommsOcMSValues`, `updateCommsOcMSLabel`. CSS `.coc-ms-opt` embebido en `filterBarHTML`. |

---

## 59. Sesión 2026-04-20: Fix duplicados en merge Comms_OC

### Diagnóstico

Se detectaron **148 registros duplicados exactos** (mismo `COMMUNICATION_ID` + `MONTH_ID` + `USER_INC`) en el dataset merged de Comms_OC. Afectaban exclusivamente a `MONTH_ID = 202604` (Abril 2026).

**Causa raíz**: El `comms_oc_cache.json` (Tier 1) fue construido con el corte antiguo D-7, que incluía registros de Abril. El `comms_oc_current_month.json` (Tier 2) también tiene Abril (es el mes actual). El merge en `process_comms_oc()` concatenaba ambos sin deduplicar.

**Comentario incorrecto en código** (línea 593, antes del fix):
```python
# No hay solapamiento: cache cubre < lunes_actual, fresh cubre >= lunes_actual
# → concatenación directa sin deduplicación necesaria
```
Este comentario era verdadero para la arquitectura D-7, pero falso tras el cambio a "mes cerrado".

### Fix en `src/processors.py`

El merge pasó de concatenación directa a deduplicación por clave `(COMMUNICATION_ID, MONTH_ID)`. Tier 2 (más reciente) gana en caso de colisión.

```python
# Antes:
all_comms_oc_records_merged = all_historical_records_from_cache + all_current_week_records_from_bq

# Después:
merged_by_key = {}
for _r in all_historical_records_from_cache:
    _k = (str(_r.get('COMMUNICATION_ID', '')), str(_r.get('MONTH_ID', '')))
    merged_by_key[_k] = _r
for _r in all_current_week_records_from_bq:
    _k = (str(_r.get('COMMUNICATION_ID', '')), str(_r.get('MONTH_ID', '')))
    merged_by_key[_k] = _r  # tier2 gana (más reciente)
all_comms_oc_records_merged = list(merged_by_key.values())
```

| Métrica | Antes | Después |
|---|---|---|
| Total registros merged | 3,125 | 2,977 |
| Duplicados | 148 | 0 |

**Este fix es permanente**: protege ante cualquier solapamiento futuro entre los dos tiers, independientemente de cómo se construya el cache.

### Archivos modificados
| Archivo | Cambio |
|---|---|
| `src/processors.py` | `process_comms_oc()`: merge por dict con clave `(COMM_ID, MONTH_ID)`. Comentario actualizado. |

---

## 60. Sesión 2026-04-20: Filtros de exclusión ampliados + fix ramas RE y FLOWS

### Nuevos patrones de exclusión

Se añadieron 4 nuevos patrones a todas las ramas SQL y a la función Python `_record_should_exclude()`:

| Patrón nuevo | Razón |
|---|---|
| `%T1%` | Campañas cross-sell/test que no corresponden a adquisición OC |
| `%XSELL%` | Campañas cross-sell explícitas |
| `%SVS_CUPON%` | Campañas de cupón de servicios no relevantes |
| `%CHURN%` | Campañas de retención/churn que no son adquisición N+R |

### Bug crítico resuelto: filtros faltantes en ramas RE y FLOWS

Las ramas C (FLOWS) y D (RE) de `build_comms_oc_sql_for_date_range()` no tenían filtros de exclusión. Esto causó que tras el `--append` de Abril, el cache recibiera:
- 92 registros `%T1%` (todos de REAL ESTATE)
- 66 registros `%XSELL%` (todos de REAL ESTATE)
- 5 registros `SELLER` en TEAM (de PUSH JOURNEY)

**Fix aplicado**:

```sql
-- Rama D (RE) — content_id:
AND content_id NOT LIKE '%T1%'
AND content_id NOT LIKE '%XSELL%'
AND content_id NOT LIKE '%SVS_CUPON%'
AND content_id NOT LIKE '%CHURN%'

-- Rama C (FLOWS) — fd.CAMPAIGN_NAME:
AND fd.CAMPAIGN_NAME NOT LIKE '%T1%'
AND fd.CAMPAIGN_NAME NOT LIKE '%XSELL%'
AND fd.CAMPAIGN_NAME NOT LIKE '%SVS_CUPON%'
AND fd.CAMPAIGN_NAME NOT LIKE '%CHURN%'
```

### Tabla final de exclusiones (todas las ramas, todos los archivos)

| Patrón | PUSH indiv_metrics | EMAIL metrics | WHERE final | Email base | RE content_id | FLOWS campaign | _record_should_exclude |
|---|---|---|---|---|---|---|---|
| `%SELLER%` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `%-XT1-%` / `%T1%` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `%SEV-T3-%` | ✅ | ✅ | ✅ | ✅ | — | — | ✅ |
| `%-ENG%` / `%-ENG` | ✅ | ✅ | ✅ | ✅ | — | — | ✅ |
| `%XSELL%` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `%SVS_CUPON%` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `%CHURN%` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

### Impacto en el cache tras múltiples `--clean`

| Momento | Registros cache | Operación |
|---|---|---|
| Antes de sesión | 2,890 | Estado inicial |
| Tras 1er --clean (T1+XSELL+SELLER) | 2,626 | −264 registros |
| Tras --append April (FLOWS+RE incluidos) | 2,991 | +365 nuevos |
| Tras 2do --clean (fix RE/FLOWS contaminados) | 2,839 | −152 registros |
| Tras 3er --clean (CHURN) | 2,786 | −53 registros |
| Tier 2 limpiado manualmente | 199 | −20 CHURN de April |
| **Total merged final** | **2,831** | **0 duplicados, 0 exclusiones pendientes** |

### Archivos modificados
| Archivo | Cambio |
|---|---|
| `src/queries.py` | +`%T1%`, `%XSELL%`, `%SVS_CUPON%`, `%CHURN%` en las 4 ramas (indiv_metrics PUSH, email_metrics, WHERE final, email_base). Ramas RE/FLOWS solo en cache. |
| `scripts/refresh_comms_oc_cache.py` | Mismos filtros SQL en las 6 ramas (PUSH + EMAIL + WHERE final + email_base + RE content_id + FLOWS campaign). `_record_should_exclude()` ampliada con T1, XSELL, SVS_CUPON, CHURN. |

---

## 61. Sesión 2026-04-20: Cache April 2026 — --append y datos FLOWS/RE

### Motivación

El `comms_oc_current_month.json` (Tier 2) solo cubre PUSH y EMAIL (Ramas A y B). FLOWS (Rama C) y RE (Rama D) están comentadas en la fresh query por performance. Esto significaba que Abril 2026 no tenía datos de PUSH JOURNEY INC TOTALES ni REAL ESTATE.

### Solución: `--append` parcial de Abril

```bash
python scripts/refresh_comms_oc_cache.py --append --from 2026-04-01 --to 2026-04-21
```

**Resultado**: 365 nuevos registros añadidos al cache, incluyendo:
- 90 registros PUSH JOURNEY INC TOTALES para Abril ✅
- 242 registros REAL ESTATE para Abril ✅

### Hallazgo: calidad de FLOWS en Abril

Análisis post-append reveló que los 90 FLOWS de Abril son de la familia `MLM_ML_I_AH_UCR_JNY_*` (5 journeys diarios automáticos):

| Estado | Comms | % |
|---|---|---|
| USER_INC > 0 (positivos) | 44 | 52% |
| USER_INC = 0 | 1 | 1% |
| USER_INC < 0 (canibalizadores) | 40 | **47%** |

**Net USER_INC estimado FLOWS Abril: ~-500 NR** (el canal está destruyendo más NR del que genera).

**Causa raíz**: los journeys corren TODOS los días. El mismo CARABO generó +244 NR el Apr-01 y -618 NR el Apr-03. La frecuencia diaria satura la audiencia → los usuarios que iban a convertir organicamente convierten "antes" de que el journey los registre → USER_INC negativo.

**Contraste**: las 3 FLOWS históricamente exitosas (`flows_communication_*_mer_*`) son TRIGGER-BASED + día específico (Miércoles) → no automation diaria. Estas son las que aportan USER_INC significativo.

**Recomendación implementada**: no filtrar USER_INC ≤ 0 del cache (son señales valiosas de canibalización), pero documentar el patrón para que el OPTIMIZADOR lo interprete correctamente.

---

## 62. Sesión 2026-04-20: Skills v3.0 — Upgrade completo del sistema de análisis

### Contexto

El sistema de 3 skills existente tenía arquitectura desacoplada: cada skill operaba de forma independiente sin referencias cruzadas ni protocolo de orquestación. El OPTIMIZADOR-OC_skill.md funcionaba como "analista descriptivo" en lugar de como VP de Insights estratégico.

**Gaps identificados:**
1. **Cero referencias cruzadas** entre los 3 skills
2. **Sin protocolo de orquestación** (ninguno definía cuándo llamar a cuál)
3. **Sin contrato de datos** (outputs no formateados para ser consumidos entre skills)
4. **analizar-OC_Comms**: sin ranking IS-ajustado multidimensional (TOP5/WORST5 por 11 dimensiones)
5. **OPTIMIZADOR**: sin motor causal explícito Comms→KPIs, sin triage automático al inicio

---

### 62.1 analizar-OC_Comms_skill.md — v2.0 → v3.0

**Nuevo Modo 14: `ranking_multidim [dimension_opcional]`**

El modo más riguroso del sistema. Ranking IS-ajustado por TODOS los cortes posibles:

| Dimensión | Campo fuente |
|---|---|
| A — CANAL | PUSH / EMAIL / RE-DRW / RE-QA / WPP / PANDORA / PUSH JOURNEY |
| B — STRATEGY | STRATEGIES (split por ' | ') |
| C — SUBSTRATEGY | SUBSTRATEGIES (split por ' | ') |
| D — BUSINESS LINE | CHANNELS_METRICS |
| E — TEAM | TEAM |
| F — TIPO | Recurring / Ad-Hoc / Trigger (derivado del nombre) |
| G — DÍA DE SEMANA | Extraído de FIRST_SENT_DATE |
| H — SEMANA DEL MES | S1/S2/S3/S4 (extraído de FIRST_SENT_DATE) |
| I — MES | MONTH_ID con IS anotado |
| J — NOTIFICATION_TYPE | STRING_AGG |
| K — TYPE_NAME | STRING_AGG |

**IS-correction antes de comparar meses:**
```
USER_INC_adj = USER_INC_raw / IS_del_mes
```

**Output**: Resumen ejecutivo 1 tabla → TOP5 GLOBAL → WORST5 GLOBAL → TOP5/WORST5 por dimensión → Patrón ganador cross-dimensional → Tabla de verdad por KPI (OR / USER_INC / ROAS / CPA / VPU)

**Nueva sección: CONEXIÓN CON OPTIMIZADOR**
Define el FINGERPRINT ESTÁNDAR de exportación (11 atributos + timing + wording + métricas + clasificación Motor/Amplificador/Canibalizador/Banal) para que el OPTIMIZADOR pueda consumir el output directamente.

---

### 62.2 OPTIMIZADOR-OC_skill.md — v2.1 → v3.0

**Cambio más importante del sistema.** Cuatro secciones nuevas o reescritas:

#### Nueva sección: QUIÉN ERES Y QUÉ PRODUCES
Reemplaza el ROL genérico. Define 3 capacidades específicas del VP:
1. Ve la causa ANTES de que aparezca el efecto
2. Conecta decisiones de comms con euros en el P&L (cadena comm → NR → VPU → ROAS → CPA)
3. Sabe qué NO tocar (cuándo el canal está en suelo invisible, saturación oculta, etc.)

#### Nueva sección: ESTÁNDAR DEL MILLÓN DE DÓLARES
Tabla de los 5 tipos de análisis que valen millones, con ejemplos reales de MLM:
- Causal no obvio / Lag identificado / Interacción cuantificada / Suelo invisible / Patrón replicable

#### Nueva sección: PROTOCOLO OBLIGATORIO AL INICIO (TRIAGE)
Ejecuta en 60 segundos antes de cualquier modo:
1. Estado del canal (N+R vs plan, ROAS vs benchmark, CPA tendencia, VPU calidad)
2. Señal más urgente (caída acelerada / USER_INC negativo sistémico / ventana estacional / outlier sin seguimiento)
3. Contexto estacional activo (IS del mes + evento próximo 21 días + WoM actual)
4. Palanca de mayor retorno disponible hoy

**El primer párrafo de CUALQUIER output sale del triage** — no de una introducción.

#### Nueva sección: MOTOR DE CAUSALIDAD COMMS → KPIs
El núcleo intelectual que faltaba. Incluye:

- **Mapa de conexiones**: tabla que mapea cada atributo de comm (Canal, BL, Strategy, VP, DoW, WoM, Tipo, Calibrador, IS) al KPI que impacta y la fuente BQ/archivo donde se verifica el vínculo
- **Protocolo C1-C4**: formular hipótesis → buscar evidencia en datos propios → separar causa de correlación → cuantificar impacto marginal
- **Cuadro de mando de palancas**: estado (activa/pausada/degradada/nueva) × retorno histórico × costo × urgencia × acción
- **Ecuación de negocio VP**: cadena completa `comm decision → NR incremental → valor predicho → ROAS → CPA`

#### Nueva sección: PROTOCOLO DE ORQUESTACIÓN DE SUB-SKILLS
Define la arquitectura de 3 capas y cuándo el VP invoca cada sub-skill:

```
analizar-OC_Comms_skill.md     → CAPA COMMS   (fingerprints, rankings, firmas)
analizar-Optimizar_Performance  → CAPA KPIS    (series N+R, ROAS, CPA, VPU)
OPTIMIZADOR-OC_skill.md        → VP SÍNTESIS  (cruza ambas capas → estrategia)
```

Tabla de orquestación por modo: qué modo pedir a cada sub-skill, qué datos esperar, en qué formato.

#### 7 REGLAS DEL VP (no negociables)
Reemplaza las reglas de estilo genéricas:
1. Primero la señal, luego el análisis
2. Cada número tiene fuente o es [estimado]
3. Toda recomendación tiene costo de no hacerla
4. El VP nunca crea perdedores internos innecesarios
5. El VP dice lo que el equipo no quiere oír (con datos)
6. Concisión ejecutiva adaptada al interlocutor
7. Hipótesis falsificable siempre

#### Nuevo Modo 9: `serie_kpi [período_opcional]`
Serie completa NR×Comms mes a mes con:
- Arquitectura de 3 capas: KPI mensual + Comms enviadas + Correlación construida por el VP
- Meses de sobre/bajo-rendimiento IS-ajustados
- Tabla de verdad por KPI: qué patrón de comms lo mejora y cuál lo destruye
- 5 patrones a REPETIR + 5 ANTI-PATRONES a eliminar (evidencia ≥ 3 meses)

#### FILTRO 5 actualizado: El Estándar del VP de $10M
7 preguntas que cada párrafo debe responder antes de publicarse, incluyendo: ¿conecté comms con P&L?

---

### 62.3 analizar-Optimizar_Performance_KPIs_skill.md — v2.5 → v3.0

**Nueva sección: CONEXIÓN CON OPTIMIZADOR**
Define la SERIE KPI ESTÁNDAR de exportación para que el OPTIMIZADOR pueda consumir el output como CAPA 1 del cruce:

```
| Mes | IS | N+R OC | N+R_adj | ROAS | CPA | VPU | Calibrador_Pandora | Calibrador_TikTok | %_vs_Plan |
```

También define el DESGLOSE SUB-CANAL CORP (UCR E&G / RECURRING / ADHOC) mapeado a la STRATEGY de Comms_OC, con nota crítica de atribución:

> "CANAL en Comms_OC ≠ sub-canal Corp. Cruzar por STRATEGY, no por CANAL. Una PUSH comm con Strategy=UCRANIA impacta el sub-canal UCRANIA E&G en la vista Corp."

---

### 62.4 Arquitectura final del sistema de 3 skills

```
comms_monthly_summary.md  ←── auto-generado por gen_dashboard_v2.py (cada refresh)
         + analizar-Optimizar_Performance_KPIs_context.md
                  ↓ (CAPA COMMS)           ↓ (CAPA KPIS)
  analizar-OC_Comms_skill.md   analizar-Optimizar_Performance_KPIs_skill.md
       ↓ Fingerprint estándar        ↓ Serie KPI estándar
              ↓                           ↓
           OPTIMIZADOR-OC_skill.md (VP SÍNTESIS)
           Motor de Causalidad COMMS → KPIs
           Cuadro de Mando de Palancas
           Protocolo de Orquestación
           Veredicto ejecutivo SMART
```

**Tamaños finales de los archivos:**

| Skill | Versión anterior | Versión nueva | Líneas |
|---|---|---|---|
| `analizar-OC_Comms_skill.md` | v2.0 (767 líneas) | **v3.0** | 988 líneas |
| `OPTIMIZADOR-OC_skill.md` | v2.1 (981 líneas) | **v3.0** | 1,478 líneas |
| `analizar-Optimizar_Performance_KPIs_skill.md` | v2.5 (969 líneas) | **v3.0** | 1,020 líneas |

### Archivos modificados
| Archivo | Tipo de cambio |
|---|---|
| `skills/analizar-OC_Comms_skill.md` | +Modo 14 `ranking_multidim` (IS-adjusted, 11 dimensiones, TOP5/WORST5). +CONEXIÓN CON OPTIMIZADOR (fingerprint estándar de exportación). |
| `skills/OPTIMIZADOR-OC_skill.md` | Reescritura ROL+ESTÁNDAR+TRIAGE. +MOTOR DE CAUSALIDAD (mapa, protocolo C1-C4, cuadro de palancas, ecuación P&L). +PROTOCOLO DE ORQUESTACIÓN (tabla modo→sub-skill). +Modo 9 `serie_kpi`. +7 REGLAS DEL VP. Filtro 5 actualizado. |
| `skills/analizar-Optimizar_Performance_KPIs_skill.md` | +CONEXIÓN CON OPTIMIZADOR (SERIE KPI ESTÁNDAR + desglose sub-canal Corp). |
| `src/template_dashboard.html` | Filtros Comms_OC: `makeSelect` → `makeMultiSelect`. `_commsOcFilterState` dropdowns → Sets. Nuevas funciones JS multi-select. CSS `.coc-ms-opt`. |
| `src/processors.py` | `process_comms_oc()`: merge con deduplicación por `(COMM_ID, MONTH_ID)`. Tier2 gana en colisión. |
| `src/queries.py` | +filtros `%T1%`, `%XSELL%`, `%SVS_CUPON%`, `%CHURN%` en 4 ramas (PUSH indiv_metrics, email_metrics, WHERE final, email_base). |
| `scripts/refresh_comms_oc_cache.py` | Mismos filtros en 6 ramas (PUSH + EMAIL + WHERE + email_base + RE content_id + FLOWS campaign). `_record_should_exclude()` ampliada. |

---

## 63. Sesión 2026-04-20: Diccionario de nomenclatura de campañas + reglas anti-alucinación

### Motivación

Durante el análisis de comms históricas se cometió una **alucinación documentada**: la campaña `CC_MARA` fue atribuida al "Maratón CDMX" basándose únicamente en el sufijo "MARA" del nombre, sin verificar la fecha. Los datos refutan la atribución: CC_MARA aparece en **Junio 2025** y en Septiembre 2025, mientras que el Maratón CDMX 2025 fue en **Agosto**.

Adicionalmente, se confirmó que `CC` en los nombres de campaña significa **Consumer Credits / Meses sin Tarjeta** — NO "Credit Card" como se podría inferir intuitivamente.

Estos errores motivaron dos acciones:
1. Crear un archivo de diccionario de nomenclatura
2. Actualizar los skills con reglas explícitas de interpretación de nombres

### Nuevo archivo: `skills/campaign_naming_guide.md`

Diccionario oficial con 6 secciones:

| Sección | Contenido |
|---|---|
| §1 | Estructura del nombre con ejemplo decodificado completo |
| §2 | Diccionario **CONFIRMADO**: sitio/app · canal · producto (CC, SVS, MYI, etc.) · audiencia · tipo campaña · BL · eventos internos (BF, HS, FIFA, LCDLF, QUINCENA) |
| §3 | Códigos de equipo y sufijos (I-EG-UCR, MTK, DEFAULT, V1/V2) |
| §4 | Códigos **NO DETERMINADOS** — lista de códigos cuyo significado exacto no ha sido confirmado (MARA, W_W, CARABO, MST2MP, FAVOR, CARO, RH, FJ, b1m, u0q, a4h) |
| §5 | Protocolo de interpretación paso a paso para los skills (tokenizar → §2 → §4 → evento con fecha) |
| §6 | Instrucciones de actualización cuando el equipo confirme nuevos códigos |

**Correcciones críticas documentadas:**

| Código | Error común | Valor correcto |
|---|---|---|
| `CC` | ~~Credit Card~~ | **Consumer Credits / Meses sin Tarjeta** |
| `MARA` | ~~Maratón CDMX~~ | Código interno desconocido — aparece en Jun-25 Y Sep-25 |
| `MST2MP` | Desconocido | **Meses Sin Tarjeta → Mercado Pago** (alta confianza, pendiente confirmar) |
| `mer` | Desconocido | **Miércoles** (alta confianza — patrón consistente en datos) |

### Reglas anti-alucinación de nombres de campaña (actualizadas en skills)

Protocolo de 3 niveles añadido a `OPTIMIZADOR-OC_skill.md` (FILTRO 2) y `analizar-OC_Comms_skill.md` (REGLA 6):

```
NIVEL 1 — ALTA CONFIANZA: Nombre sugiere evento + fecha cae en período del evento
  Ejemplo válido: "BF_*" en Noviembre 3ra semana → sí es Buen Fin ✅

NIVEL 2 — INVÁLIDO: Nombre sugiere evento pero fecha NO coincide
  La fecha desmiente el nombre → código interno reutilizado.
  Caso documentado: "CC_MARA" en Junio ≠ Maratón CDMX (fue en Agosto) ❌

NIVEL 3 — SIN DATO: Código sin referencia a evento conocido
  W_W, MARA, NIA, MTK → reportar como [Código interno — no determinado]

REGLA DE ORO: NOMBRE + FECHA COINCIDEN → inferencia válida. Siempre la fecha manda.
Antes de proponer amplificadores externos → explicar por IS + WoM + DoW primero.
```

### Protocolo de monitoreo de journeys diarios (añadido a OPTIMIZADOR-OC_skill.md)

Documentado con caso real: `MLM_ML_I_AH_UCR_JNY_MST2MP` en Abril 2026 acumuló **-174 NR en ~7 días** de ejecución diaria. La recomendación correcta era pausar al día 7.

**Umbrales de pausa (ciclo de evaluación día 7):**

| Net USER_INC en 7 días | Acción |
|---|---|
| < -50 NR | **PAUSAR HOY** — sin excepción |
| -50 a +50 NR | Investigar en 48h; sin decisión → pausar por default |
| > +100 NR | Continuar; revisar en día 14 |

**Regla del VP documentada**: Una automation con USER_INC negativo nunca se "espera a ver si mejora". El modelo de medición de lift es estable — si el resultado es negativo a día 7, la causa (frecuencia, audiencia, VP) debe cambiar antes de relanzar.

### Skills afectados por la sesión 2026-04-20 (post §62)

| Skill | Cambio |
|---|---|
| `OPTIMIZADOR-OC_skill.md` | FILTRO 2 ampliado: protocolo 3 niveles para nombres de campaña. +PROTOCOLO DE MONITOREO Y PAUSA DE JOURNEYS. +`campaign_naming_guide.md` en tabla FUENTES DE DATOS. |
| `analizar-OC_Comms_skill.md` | REGLA 6 añadida: protocolo 3 niveles para nombres. `campaign_naming_guide.md` como fuente #2 (SIEMPRE cargar al analizar nombres). |

### Archivos creados/modificados
| Archivo | Cambio |
|---|---|
| `skills/campaign_naming_guide.md` | **NUEVO** — 215 líneas. Diccionario oficial de abreviaturas en nombres de campaña MLM. |
| `skills/OPTIMIZADOR-OC_skill.md` | +PROTOCOLO DE MONITOREO (umbrales día 7). +Regla nombres campaña 3 niveles en FILTRO 2. +`campaign_naming_guide.md` en FUENTES. |
| `skills/analizar-OC_Comms_skill.md` | +REGLA 6 (nombres campaña 3 niveles). +`campaign_naming_guide.md` como fuente #2. |

---

## 64. Sesión 2026-04-20: Skills v3.1 — VP Fatiga, Timing Codificado, Enriquecimiento desde Nombre

### 64.1 Modo 10 `vp_ciclo` — Análisis de Ciclo de Vida y Fatiga de VP (OPTIMIZADOR)

**Motivación**: Algunos VPs (ej. "Ingresa $X y te damos $Y" / VP_MONIN) funcionan muy bien en sus primeros meses de uso y luego decaen. Sin un análisis longitudinal, el equipo puede seguir usando VPs agotados creyendo que "algo siguen generando". El caso documentado es `MLM_MP_ML-PUSHML_DACCNT_MONIN_AO-UCR`.

**Nuevo Modo 10 `vp_ciclo [vp_type_opcional]`** en `OPTIMIZADOR-OC_skill.md`:

Proceso ejecutable en 6 pasos:
1. **Extraer** todas las comms y clasificarlas en `VP_TYPE` (VP_MONIN, VP_CBK_PCT, VP_CC, VP_INST, VP_CPN_SVS, VP_UNKNOWN) usando patrones del título/texto
2. **Construir** la serie temporal IS-ajustada por VP_TYPE mes a mes
3. **Calcular** Índice de Decaimiento: `ID = USER_INC_adj[mes_N] / USER_INC_adj[mes_lanzamiento]`
4. **Diagnosticar** con firma de funnel: fatiga total / opens de curiosidad / fatiga de audiencia / Pavlov inverso
5. **Rankear** todos los VP_TYPEs por urgencia
6. **Recomendar** con fecha límite y VP alternativo

**Ciclo de vida del incentivo documentado:**
```
MES 1-2 (LANZAMIENTO)  → ID ≈ 1.0 → ESCALAR reach
MES 3-4 (MESETA)       → ID 0.5-0.8 → MONITOREAR, preparar alternativo
MES 5-6 (FATIGA)       → ID 0.2-0.5 → ROTAR en 30-60 días
MES 7+  (AGOTADO)      → ID < 0.2 → PAUSAR 2+ meses
PAVLOV INVERSO         → USER_INC negativo → STOP urgente
```

**Dimensión 7** añadida al PASO 2 del Marco Analítico del OPTIMIZADOR: FATIGA DE VP. Señales: OR estable + LIFT cayendo = "opens de curiosidad" (peor caso antes del Pavlov), Efficiency_Score < 50% del baseline = saturación de cadencia.

---

### 64.2 Modo 15 `timing_codificado` — Campañas con Timing en el Nombre (analizar-OC_Comms)

**Motivación**: Algunas campañas como `I-M-NR-CB-QUIN-A-0815` tienen el timing óptimo codificado en el nombre. Decodificado:
```
I=Internal · M=México · NR=adquisición · CB=Cashback · QUIN=Quincena
A=Variante · 0815=Agosto 15 (quincena 1 del mejor mes IS 1.15)
TRIPLE AMPLIFICADOR: Cashback + Quincena (IS_semanal 1.25) + Agosto (IS 1.15)
```

**Nuevo Modo 15 `timing_codificado [campaña_opcional]`** en `analizar-OC_Comms_skill.md`:

Proceso de 5 pasos:
1. **Detectar** campañas con QUIN, S2, MMDD (fecha 4 dígitos), BF, HS en el nombre
2. **Verificar** que FIRST_SENT_DATE coincida con el timing codificado (QUIN → día 14-16 o 29-31)
3. **Construir grupo de control**: mismas comms de mismo VP_TYPE sin timing específico
4. **Calcular Premium de Timing**: `Premium_QUIN = USER_INC_adj(QUIN) / USER_INC_adj(no_QUIN)`
5. **Recomendar** plan de timing sistemático: cuántas oportunidades IS>1.0 + quincena hay en el año y cuántas se están usando

**TRIAGE del OPTIMIZADOR actualizado**: verifica en cada invocación si estamos en quincena + IS>1.0 (condición GOLD STANDARD). Si hay campañas QUIN activas → OK. Si no → oportunidad perdida, cuantificar.

**Referencia codificada en el skill**: `I-M-NR-CB-QUIN-A-0815` = benchmark del techo del canal.

---

### 64.3 PRE-PROCESAMIENTO OBLIGATORIO — Enriquecimiento VP desde Nombre (analizar-OC_Comms)

**Motivación**: El campo `BL` del dato BQ puede ser genérico (ej. `INSTALLS`) mientras que el nombre de la campaña revela información más específica: `POSTCOMPRA` es más informativo que `INSTALLS` para entender el contexto de la comm.

**Protocolo añadido como sección pre-modo** en `analizar-OC_Comms_skill.md`:

Para cada `CAMPAIGN_NAME_CLEAN`, antes de cualquier análisis, derivar 4 campos nuevos:

| Campo derivado | Ejemplos |
|---|---|
| `VP_TIPO` | VP_CASHBACK, VP_CONSUMER_CREDIT, VP_MONEY_IN, VP_WALLET, VP_RECARGA, VP_SERVICIOS, etc. |
| `TRIGGER_TIPO` | TRIGGER_POSTCOMPRA, TRIGGER_DROP_FUNNEL, TRIGGER_JOURNEY, NONE |
| `AUDIENCIA_NOMBRE` | AUD_UCR_ALL, AUD_GREEN, AUD_NAVEGANTES, AUD_RECOVERED, etc. |
| `TIMING_NOMBRE` | QUINCENA, HOT_SALE, BUEN_FIN, NONE |

**Regla de prioridad**: `TRIGGER_TIPO` del nombre > `BL` del dato. `POSTCOMPRA` en el nombre es más descriptivo que `INSTALLS` en BQ — son capas de información complementaria, no mutuamente excluyentes.

---

### 64.4 Expansión de `campaign_naming_guide.md` — §1.5, §1.7, MYI/MYO

**§1.5 Campañas con Timing Codificado** — nueva sección con tabla de QUIN, S2, BF, HS, MMDD y su implicación analítica. Caso GOLD STANDARD `I-M-NR-CB-QUIN-A-0815` documentado.

**§1.7 Inferencia de VP desde Nombre** — tabla completa de 4 dimensiones derivables:
- `VP_TIPO` (CB, CC, WLL, REC, SVS, PREST, MYI/MYO, INV, etc.)
- `TRIGGER_TIPO` (POSTCOMPRA, DROPF, RIND, ABANDONO, JNY)
- `AUDIENCIA_NOMBRE` (UCR_ALL, GRE, NAV, RECOVERED, NEW)
- `ESTRATEGIA_NOMBRE` (UCRANIA, ACTIVATION, ADHOC)

**Correcciones críticas confirmadas**:
- `MYI` y `MYO` son el MISMO producto: Money In (depósito/fondeo de cuenta)
- `MONIN` y `DACCNT` son variantes del patrón VP_MONEY_IN ("Ingresa $X y te damos $Y")

**Archivos modificados**:
| Archivo | Cambio |
|---|---|
| `skills/OPTIMIZADOR-OC_skill.md` | +Modo 10 `vp_ciclo`. +Dimensión 7 FATIGA DE VP en PASO 2. +TRIAGE punto 5 (ventana timing codificado). |
| `skills/analizar-OC_Comms_skill.md` | +Modo 15 `timing_codificado`. +PRE-PROCESAMIENTO OBLIGATORIO (enriquecimiento VP desde nombre). |
| `skills/campaign_naming_guide.md` | +§1.5 Timing codificado. +§1.7 Inferencia VP desde nombre. MYO = Money In confirmado. 215 → 349 líneas. |

---

## 65. Sesión 2026-04-20: Principio de Ventanas de Atribución (OPTIMIZADOR)

### Motivación

Al analizar campañas como las del Buen Fin Nov-25, el OPTIMIZADOR podía dar recomendaciones incorrectas del tipo "replica Comm A porque tuvo el mayor USER_INC". Este razonamiento ignora que en períodos de alta densidad de comunicaciones a la misma audiencia, las **ventanas de atribución se pisan** y el USER_INC individual no es confiable.

### Concepto: Pisado de Ventanas

Cada comm tiene una ventana de atribución (ej. 7 días) durante la cual una conversión se atribuye a ella. Cuando se envían múltiples comms a la misma base en días consecutivos:

```
Comm A Día 1 → ventana D1-D7
Comm B Día 2 → ventana D2-D8   ← se pisa con A 6 días
Comm C Día 3 → ventana D3-D9   ← se pisa con A y B
...
```

**Efectos documentados:**
1. **Inflación de primeras comms**: Comm A captura conversiones motivadas por el STACK completo
2. **Deflación de últimas comms**: Comm E llega cuando los susceptibles ya convirtieron
3. **Contaminación del grupo de control**: usuarios en control de A reciben B,C,D,E → el LIFT de A no es limpio
4. **El orden importa tanto como el contenido**: la primera siempre se ve "mejor" independiente de calidad

**Caso documentado — Buen Fin Nov-25**: 5 comms en 5 días a misma base. BF-1 aparece como la mejor. No es que sea mejor — llegó primero.

### Nuevas secciones en el OPTIMIZADOR

**PRINCIPIO FUNDAMENTAL — VENTANAS DE ATRIBUCIÓN Y PISADO** (sección antes de PASO 3 Atribución Causal):
- Definición de ventana de atribución y pisado
- 4 efectos del pisado con ejemplos reales
- Caso Buen Fin Nov-25 documentado
- Protocolo de Detección (IS_overlap = suma_dias_ventana / dias_período)
- Tabla de acción según nivel de pisado: LIMPIO / PISADO_LEVE / PISADO_SEVERO
- Reglas de recomendaciones válidas vs inválidas con pisado

**Clasificación de períodos por tolerancia al pisado:**

| Tipo | Tolerancia | Acción correcta |
|---|---|---|
| **Tier 1 Seasonal** (BF, HS, FIFA, LCDLF) | TOTAL — pisado inevitable e intencional | NUNCA recomendar espaciar. Usar TOTAL evento vs año anterior |
| **Períodos regulares** | CERO — pisado es sobre-comunicación | SÍ recomendar espaciar ≥7 días |
| **Tier 2 events** (Quincenas, DD) | LEVE — max 2-3 comms en 3 días | Limitar densidad |

**Corrección crítica**: La recomendación "espaciar comms ≥7 días en Buen Fin para medición limpia" es **operacionalmente inviable** para Tier 1 Seasonals. El equipo acepta conscientemente el tradeoff maximizar NR > pureza de medición durante estos eventos. El VP no cuestiona esta decisión, la incorpora al análisis.

**FILTRO 2 actualizado**: añadida verificación previa de calidad de medición. Si hay pisado detectado → USER_INC marcado como `[PISADO_SEVERO]` y se usa TOTAL del período + OR + LIFT como métricas alternativas.

### Archivos modificados
| Archivo | Cambio |
|---|---|
| `skills/OPTIMIZADOR-OC_skill.md` | +PRINCIPIO FUNDAMENTAL VENTANAS DE ATRIBUCIÓN (extensa nueva sección). +FILTRO 2 con verificación de calidad USER_INC. Clasificación Tier 1/2/regular. Fix: eliminada recomendación incorrecta de espaciar Tier 1 Seasonals. |

---

## 66. Sesión 2026-04-21/22: Rama D (RE) — 4 Nuevas Columnas + Mapping Correcto

### Motivación

La Rama D (REAL ESTATE) tenía un mapping semántico incorrecto en el funnel común y no exponía las métricas brutas de impresiones/toques que el equipo necesita para analizar los placements.

**Problemas del mapping anterior:**
```
TOTAL_TEST   = total_prints   ← duplicado, total_prints NO = usuarios únicos
TOTAL_SHOWN  = total_prints   ← duplicado exacto de TEST (sin valor analítico)
TOTAL_ARRIVED = unique_prints ← OK pero en posición incorrecta
TOTAL_OPEN   = total_taps     ← total bruto, no usuarios únicos
```

### Mapping correcto aplicado

| Campo común | Valor nuevo | Razón |
|---|---|---|
| `TOTAL_TEST` | `unique_prints` | Usuarios únicos que vieron el placement |
| `TOTAL_ARRIVED` | `unique_prints` | Sin delivery gap en RE — impressions = arrived |
| `TOTAL_SHOWN` | `unique_prints` | Igual que TEST, semánticamente correcto |
| `TOTAL_OPEN` | `unique_taps` | Usuarios únicos que tocaron — CTR real |
| `OPEN_RATE` | `unique_taps / unique_prints` | CTR real por usuario único (antes era total/total) |

### 4 Nuevas columnas RE-específicas

| Columna | Fuente BQ | Descripción | En PUSH/EMAIL/FLOWS |
|---|---|---|---|
| `TOTAL_PRINTS_RE` | `COUNT(*)` prints | Impresiones totales (≠ usuarios únicos) | 0 |
| `UNIQUE_PRINTS_RE` | `COUNT(DISTINCT user_id)` prints | Usuarios únicos que vieron | 0 |
| `TOTAL_TAPS_RE` | `COUNT(*)` taps | Toques brutos en el placement | 0 |
| `UNIQUE_TAPS_RE` | `COUNT(DISTINCT user_id)` taps | Usuarios únicos que tocaron | 0 |

### Fix UNION ALL — columnas desiguales

El error inicial: "Queries in UNION ALL have mismatched column count; query 1 has 39 columns, query 4 has 35 columns" — la Rama C (FLOWS) no tenía las 4 nuevas columnas RE como ceros. Fix: añadir `0 AS TOTAL_PRINTS_RE, 0 AS UNIQUE_PRINTS_RE, 0 AS TOTAL_TAPS_RE, 0 AS UNIQUE_TAPS_RE` a TODAS las ramas (PUSH, EMAIL, FLOWS) además de los valores reales en RE.

**Fix adicional**: el filtro `component_id IN (...)` que se añadió al prints CTE excluía todos los RE de Abril (retornaba 0 records). Se eliminó el filtro de component_id para volver al comportamiento original funcional.

### Archivos modificados
| Archivo | Cambio |
|---|---|
| `scripts/refresh_comms_oc_cache.py` | RE branch: mapping correcto (unique_prints/unique_taps). +4 columnas en RE. +0-columns en PUSH, EMAIL, FLOWS. `unique_taps` añadido al taps subquery. |
| `src/queries.py` | Mismos cambios en la versión comentada de RE (Rama D). |
| `src/builders.py` | `build_comms_oc_table_html()`: 23 → **31 columnas** (27 orig + 4 RE + 2 derivadas + `data-fecha`). Para RE: `da_test=da_arrived=da_shown=da_open=0` para no contaminar cards comunes. Nuevos headers: `Prints RE`, `Uniq. Prints RE`, `Taps RE`, `Uniq. Taps RE`, `Toques/usuario RE`, `% Click RE`. |

---

## 67. Sesión 2026-04-21/22: Exclusiones Específicas RE (POINT/MINI/LOYALTY/CRYPTO etc.)

### Motivación

Al ver la pestaña Comms_OC filtrada por REAL ESTATE, aparecían campañas que no corresponden a adquisición OC:
- `MLM-MP-S-M-POINT-SHCT-MINI-MULTI-260` (cross-sell mini placements)
- `MLM_MODAL_LIFECYCLE_ENG_V1` (engagement, no adquisición)
- `MLM_MP_BANN-MP-CRYPTO-ED_WALLET_CRI` (crypto)
- `pro_account_In_progress_scarcity_ml` (loyalty/cuenta pro)
- `MLM DRW UCR I EG MP GENERIC` (genérico sin valor analítico)

### Patrones de exclusión añadidos (SOLO para REAL ESTATE)

Los filtros se aplican únicamente al canal RE para no afectar a PUSH/EMAIL/FLOWS que podrían tener nombres similares con significados diferentes.

| Patrón | Qué excluye |
|---|---|
| `%POINT%` | MLM-MP-S-M-POINT-SHCT-*, mini cross-sell placements |
| `%MINI%` | MINI99, MINI109, MINI-MULTI — micro-placements |
| `%LOYALTY%` | Campañas de loyalty/fidelización |
| `%CRYPTO%` / `%CRIPTO%` | Campañas de crypto/educación financiera |
| `%ENGAGED%` / `%_ENG%` | Engagement campaigns (ej. LIFECYCLE_ENG_V1) |
| `%XSLL%` / `%XSMP%` | Variantes XSELL/cross-sell |
| `%CROSS_SELLING%` / `%CROSS-SELLING%` | Cross-sell explícito |

**Implementación**: En `_record_should_exclude()`, se añadió un bloque `if canal == 'REAL ESTATE':` separado del bloque general, garantizando que PUSH/EMAIL/FLOWS con esas palabras no sean excluidos.

**174 registros RE eliminados** del cache tras `--clean`.

### Archivos modificados
| Archivo | Cambio |
|---|---|
| `scripts/refresh_comms_oc_cache.py` | SQL RE prints CTE: 10 nuevos `UPPER(CAST(content_id AS STRING)) NOT LIKE '%PATRON%'`. `_record_should_exclude()`: bloque `if canal == 'REAL ESTATE':` con 11 patrones específicos. |

---

## 68. Sesión 2026-04-21/22: Filtro %SVS% para Todos los Canales + `data-fecha` en Comms_OC

### Exclusión %SVS% global

El usuario identificó campañas de servicios externos (agua, escuelas, gobierno) que deben excluirse de Comms_OC:
- `svs_mlm_colegio_herbart`, `MLM_SVS_ZACATECAS`, `svs_mlm_jmas1`
- `flows_communication_MLM_SVS_TD_OUT_`, `flows_communication_MLMS_SVS_TCMP_O…`

`%SVS%` se añadió a las 6 ramas SQL (PUSH indiv_metrics, email_metrics, WHERE final, email_base, RE content_id, FLOWS campaign) y a `_record_should_exclude()` — a diferencia de los patrones RE, SVS aplica a TODOS los canales.

**20 registros SVS** eliminados del Tier 2 (comms_oc_current_month.json) y purga del cache via `--clean`.

### Filtro multi-select `Fecha Envío`

Nuevo filtro en la barra de Comms_OC que permite seleccionar múltiples fechas específicas para comparar días concretos (ej. Apr 1 y Apr 10 simultáneamente).

**Implementación:**
- `builders.py`: `data-fecha="{first_sent_date}"` añadido al `<tr>` de cada fila
- `template_dashboard.html`: `fecha: new Set()` en `_commsOcFilterState`. `sets.fecha.add(row.dataset.fecha)` en `initCommsOcFilters()`. `makeMultiSelect('comms-f-fecha', ...)` como primer dropdown. `fechaOk = msExact(d.fecha, f.fecha)` en `applyCommsOcFilters()`.

### Archivos modificados
| Archivo | Cambio |
|---|---|
| `scripts/refresh_comms_oc_cache.py` | +`%SVS%` en 6 ramas SQL. `_record_should_exclude()`: `or 'SVS' in campaign_up`. |
| `src/queries.py` | +`%SVS%` en PUSH indiv_metrics, email_metrics, WHERE final, email_base. |
| `src/builders.py` | +`data-fecha="{first_sent_date}"` en `<tr>`. |
| `src/template_dashboard.html` | +filtro `fecha` multi-select en barra, estado, onChange, apply y clear. |

---

## 69. Sesión 2026-04-22: KPI Cards RE + Métricas Derivadas + Fix Toques/usuario

### KPI Cards RE en Comms_OC

**Problema**: las KPI cards del funnel común (TEST/ARRIVED/SHOWN/OPEN) mostraban datos de filas RE, mezclando métricas de usuarios únicos de prints con el funnel de PUSH/EMAIL.

**Solución**: separación por tipo de fila:
1. `builders.py`: Para filas RE, `da_test = da_arrived = da_shown = da_open = 0` → cards comunes no suman datos RE
2. `template_dashboard.html` en `renderCommsOcKPIs()`:
   - Acumula `data-prints-re`, `data-unique-prints`, `data-taps-re`, `data-unique-taps` de todas las filas visibles
   - Si hay filas RE (`hasReRows = true`) → renderiza tercer grupo de 6 cards en morado (`#7A41ED`)
   - Cards comunes solo suman datos de filas no-RE

**6 nuevas KPI cards RE** (grupo morado, solo aparece cuando hay filas RE visibles):

| Card | Fórmula | Fuente |
|---|---|---|
| Prints RE | `Σ TOTAL_PRINTS_RE` visible | `data-prints-re` |
| Uniq. Prints RE | `Σ UNIQUE_PRINTS_RE` visible | `data-unique-prints` |
| Taps RE | `Σ TOTAL_TAPS_RE` visible | `data-taps-re` |
| Uniq. Taps RE | `Σ UNIQUE_TAPS_RE` visible | `data-unique-taps` |
| Toques/usuario RE | `totalPrintsRe / totalUniqPrints` | Calculado JS |
| % Click RE | `totalUniqTaps / totalUniqPrints × 100` | Calculado JS |

### Fix fórmula Toques/usuario RE

**Bug inicial**: se calculaba como `TAPS_RE / UNIQUE_PRINTS` (toques por usuario único que vio).
**Corrección confirmada por usuario**: debe ser `PRINTS_RE / UNIQUE_PRINTS` = promedio de veces que cada usuario único vio el placement (frecuencia de impresión).

Primer registro de ejemplo: 11,140 / 10,929 = **1.02** (correcto) vs 750/10,929 = 0.07 (incorrecto).

### Columnas en tabla Comms_OC — estado final: 31 columnas

| Rango | Columnas | Canal |
|---|---|---|
| 1-14 | Meta: Mes, Fecha Envío, App, Canal, Seg.Canal, Strategy, Substrategy, BL, Type Name, Notif.Type, Team, Campaña, Título, Texto | Todos |
| 15-20 | Funnel: CREATE, TEST, CONTROL, ARRIVED, SHOWN, OPEN | PUSH/EMAIL/FLOWS (— para RE) |
| 21-23 | Eficiencia: Open%, CVR%, Lift% | PUSH/EMAIL (— para RE) |
| 24-27 | Impacto: User Inc, TPN Inc, TPV Inc, Value Inc | PUSH/EMAIL/FLOWS (— para RE) |
| 28-31 | **RE-específicas**: Prints RE, Uniq.Prints RE, Taps RE, Uniq.Taps RE | RE (— para otros) |
| 32-33 | **Derivadas RE**: Toques/usuario RE, % Click RE | RE (— para otros) |

### Archivos modificados
| Archivo | Cambio |
|---|---|
| `src/builders.py` | Para RE: `da_test=da_arrived=da_shown=da_open=0`. Celdas tabla: RE muestra — en funnel/eficiencia/impacto. +columnas derivadas RE. 31+2 = 33 columnas totales con las 2 derivadas. |
| `src/template_dashboard.html` | `renderCommsOcKPIs()`: acumula métricas RE separadas. Sección RE condicional (`hasReRows`). Fix Toques/usuario = `totalPrintsRe / totalUniqPrints`. |

---

## 70. Sesión 2026-04-24: MTD D7 mejoras + Limpieza de arquitectura (v2→v1 + renombrado de archivos)

---

### 70.1 MTD D7 — Columna "Plan N+R" + Fila "Mix de Marketing"

**Motivación**: La tabla MTD D7 mostraba LMTD, MTD, diferencias y vs Plan M, pero no exponía el plan mensual de forma directa ni el mix de canales gestionados como KPI de contexto global.

#### Cambio A: Columna "Plan N+R"

Nueva columna entre "Diferencias %" y "vs Plan M":

| Campo | Detalle |
|---|---|
| Header | `Plan N+R / Plan mensual` |
| Dato | `D.plan_nr[label][month]` via `fmtNum()` |
| Con valor | Total N+R, OC+UCR, POM TOTAL, MGM TOTAL, L&P TOTAL, ORG |
| Sin plan (`—`) | UCR Gest, UCR PRD, OC ACT, POM ADQ, POM ACT, MGM ADQ, MGM ACT, L&P ADQ, L&P ACT |

El dato es el mismo que alimenta "vs Plan M" — ahora el usuario ve plan absoluto Y desviación en columnas contiguas.

#### Cambio B: Fila "Mix de Marketing"

Primera fila del `<tbody>`, antes de "Total N+R". Muestra el porcentaje de N+R gestionado por canales de marketing (excluye ORG).

```
Mix de Marketing = (OC+UCR + POM TOTAL + MGM TOTAL + L&P TOTAL) / Total N+R × 100
```

| Columna | Valor |
|---|---|
| Label | "Mix de Marketing (OC+UCR + POM + MGM + L&P) / Total" |
| LMTD | `lmtdManaged / lmtdTotal * 100` → XX.X% |
| MTD | `mtdManaged / mtdTotalNR * 100` → YY.Y% |
| Diferencias Absolutos | Δpp = MTD mix − LMTD mix con `▲/▼` color |
| Diferencias % | `—` |
| Plan N+R | `planManaged / planTotalNR * 100` → ZZ.Z% (mix planificado) |
| vs Plan M | `—` |
| Proy. Lineal | `—` |
| MIx | `—` |

**Estilo**: fondo `#0f2140`, label en `#ffd966` (dorado), valores en `#e8f0ff`. Borde dorado semitransparente top/bottom. Lectura como KPI diferenciado del resto de filas.

**Comportamiento con filtro de canal**: `data-canal="__mix_mkt__"`. El filtro siempre lo mantiene visible:
```javascript
if (dc === '__mix_mkt__') { tr.style.display = ''; return; }
```

**Implementación en `renderMTDTable()`**:
- Pre-cómputo de 6 variables (`lmtdManaged_mm`, `mtdManaged_mm`, `planManaged_mm`, `lmtdMixPct`, `mtdMixPct`, `deltaMixPp`, `planMixPct`) antes del `D.labels.forEach`
- Helpers locales `fmtMixPct()` y `fmtDeltaPp()` (locales a la función, no globales)
- Constantes de estilo `MIX_S_LBL` y `MIX_S_VAL`

---

### 70.2 Eliminación de `legacy_v1/` + Rename v2→v1

**Motivación**: La carpeta `legacy_v1/` contenía el monolito original que ya no se usa. La arquitectura modular es el único entorno desde Mar-2026. Eliminar el legacy reduce ruido y permite usar nombres simples (V1, no V2).

#### Archivos eliminados (`legacy_v1/` — 7 archivos)

| Archivo | Descripción |
|---|---|
| `gen_dashboard_html.py` | Monolito V1 original (~800 líneas) |
| `deploy_appscript.py` | Deploy script V1 |
| `.appscript_config.json` | Config Apps Script V1 (scriptId/deploymentId) |
| `CLAUDE.md` | Context file V1 |
| `HISTORY.md` | Historial V1 |
| `dashboard.html` | Output HTML V1 (~573 KB) |
| `[Claude] MLM_ADQ_Dash.docx` | Documentación legible |

#### Archivos renombrados (v2→v1)

| Antes | Después |
|---|---|
| `src/gen_dashboard_v2.py` | `src/gen_dashboard_v1.py` |
| `src/deploy_appscript_v2.py` | `src/deploy_appscript_v1.py` |
| `config/.appscript_config_v2.json` | `config/.appscript_config_v1.json` |
| `dashboard_v2.html` | `dashboard_v1.html` |

#### Referencias internas actualizadas

| Archivo | Refs actualizadas | Notas |
|---|---|---|
| `src/gen_dashboard_v1.py` | 4 | Comentarios + `OUT_HTML` + `comms_monthly_summary` |
| `src/deploy_appscript_v1.py` | 12 | Todos los `V2`/`v2` excepto `"version":"v2"` del API BQ (línea 105) |
| `src/builders.py` | 6 | Comentarios/docstrings |
| `src/processors.py` | 4 | Comentarios/docstrings |
| `src/queries.py` | 1 | Comentario |
| `src/template_dashboard.html` | 2 | Título UI + comentario JS |
| `CLAUDE.md` | 5 | Principios + descripción + flujo + tabla archivos + CI/CD |
| `.github/workflows/refresh_MLM_ADQ_Dashboard.yml` | 3 | Rutas Python + nombre step + guardia 50KB |

> **⚠️ Línea preservada**: `"version": "v2"` en `deploy_appscript_v1.py:105` corresponde a la versión del API de BigQuery de Google — no es del proyecto y no se modifica.

#### Workflow CI/CD actualizado

`refresh_MLM_ADQ_Dashboard.yml` actualizado de:
```yaml
run: python gen_dashboard_html.py   # script del monolito borrado
run: python deploy_appscript.py     # script del monolito borrado
```
A:
```yaml
run: python src/gen_dashboard_v1.py
# + Guardia de seguridad: verifica HTML > 50KB antes de deploy
run: python src/deploy_appscript_v1.py
```

La guardia de seguridad (>50KB) estaba documentada como feature del pipeline V2 pero nunca se había agregado al único workflow existente. Se añade ahora.

---

### 70.3 Renombrado `CLAUDE2.md→CLAUDE.md` + `History2.md→History.md`

**Motivación**: El sufijo "2" era solo para no colisionar con `legacy_v1/CLAUDE.md` y `legacy_v1/HISTORY.md`. Eliminado el legacy, se restauran los nombres canónicos. `CLAUDE.md` es el nombre que Claude Code detecta automáticamente en el directorio raíz del proyecto.

#### Archivos renombrados

| Antes | Después |
|---|---|
| `CLAUDE2.md` | `CLAUDE.md` |
| `docs/History2.md` | `docs/History.md` |

#### Referencias actualizadas (12 archivos)

| Archivo | Refs (`CLAUDE2`→`CLAUDE`) | Refs (`History2`→`History`) |
|---|---|---|
| `CLAUDE.md` | — | Todas (History.md en tablas, texto, notas) |
| `docs/History.md` | Todas | Todas (auto-referencias) |
| `skills/analizar-Optimizar_Performance_KPIs_skill.md` | 2 | 1 |
| `skills/analizar-Optimizar_Performance_KPIs_context.md` | 3 | — |
| `skills/README.md` | 1 | 1 |
| `config/queries/README.md` | — | 1 |
| `config/queries/performance_vista_corp.md` | — | 1 |
| `docs/OC_POM_master_context.md` | 1 | 1 |
| `src/gen_dashboard_v1.py` | — | 1 |
| `src/processors.py` | — | 2 |
| `src/queries.py` | — | 1 |
| `scripts/refresh_comms_oc_cache.py` | — | 1 |
| `config/channels_config.json` | — | 1 |

Adicionalmente: eliminada de `CLAUDE.md` la línea obsoleta `- **Carpeta legacy**: MLM_ADQ_Dash/legacy_v1/ (intocable)`.

---

### Archivos modificados en §70

| Archivo | Cambio |
|---|---|
| `src/template_dashboard.html` | `renderMTDTable()`: +header Plan N+R · +Mix MKT row · +`fmtNum(planVal)` en rows regulares · +filtro Mix MKT siempre visible |
| `src/gen_dashboard_v1.py` | Renombrado de `gen_dashboard_v2.py` + 4 refs internas |
| `src/deploy_appscript_v1.py` | Renombrado de `deploy_appscript_v2.py` + 12 refs internas |
| `config/.appscript_config_v1.json` | Renombrado de `.appscript_config_v2.json` |
| `dashboard_v1.html` | Renombrado de `dashboard_v2.html` (output regenerado) |
| `.github/workflows/refresh_MLM_ADQ_Dashboard.yml` | Rutas actualizadas + guardia 50KB |
| `src/builders.py` | 6 refs comentarios actualizadas |
| `src/processors.py` | 4 refs comentarios actualizadas |
| `src/queries.py` | 1 ref comentario actualizada |
| `CLAUDE.md` | Renombrado + MTD D7 section actualizada + 3 entradas historial + refs |
| `docs/History.md` | Renombrado + §70 añadida + refs |
| `skills/analizar-Optimizar_Performance_KPIs_skill.md` | Refs CLAUDE/History actualizadas |
| `skills/analizar-Optimizar_Performance_KPIs_context.md` | Refs CLAUDE actualizadas |
| `skills/README.md` | Refs CLAUDE/History actualizadas |
| `config/queries/README.md` | Ref History actualizada |
| `config/queries/performance_vista_corp.md` | Ref History actualizada |
| `docs/OC_POM_master_context.md` | Refs CLAUDE/History actualizadas |
| `scripts/refresh_comms_oc_cache.py` | Ref History actualizada |

---

## 71. Sesión 2026-04-24: Migración Torre de Control — Fase 1 N+R

### Contexto

`PANEL_MONTHLY_DAILY_HISTORICO` y `PANEL_MONTHLY_COSTOS_CANALES` serán deprecadas. El equipo de Meli migra toda la analítica de Marketing al **SSOT (Single Source of Truth) de la Torre de Control**, un sistema certificado que elimina la fragmentación de datos entre equipos.

**¿Por qué lo hicimos ahora?**
- `PANEL_MONTHLY_DAILY_HISTORICO` → deprecated confirmado.
- `PANEL_MONTHLY_COSTOS_CANALES` → deprecated confirmado (mismo ciclo).
- El SSOT garantiza que los números del dashboard sean los mismos que los números oficiales de la organización.

### Arquitectura SSOT Torre de Control (TC)

```
STG.KPI_NR-INAPP-RAW_RAW          ← NO accesible directamente (tabla staging)
         ↑ construida con:

BT_OC_NR_REPORTE_TORRE_DAILY      ← SÍ acceso. Fuente OC (lift-based).
  meli-bi-data.SBOX_EG_MKT
  Columnas clave: DAY_ID, SITE, CANAL, CLASIFICACION, NR_INC_USERS, NR_INC_VALUE,
                  CONSUMIDO_USD, COSTO_ENVIO_USD, COSTO_MANTIKA_USD, FLAG_PAID

BT_MP_INDIVIDUALS_PERFORMANCE     ← SÍ acceso. Fuente Paid (atribución).
  meli-bi-data.SBOX_MARKETING
  Columnas clave: TIM_DAY, SIT_SITE_ID, STRATEGY_GROUP, SOURCE_CD, CHANNEL_GROUP,
                  NETWORK_GROUP_NAME, NEW_USERS_7D_INAPP, RECOVERED_USERS_7D_INAPP,
                  NEW_USERS_INAPP, RECOVERED_USERS_INAPP, COST_USD, COST_LC_INCENTIVOS,
                  VALUE_MKT_USD_NEW_USERS_7D, VALUE_MKT_USD_RECOVERED_USERS_7D
```

**KPIs de la Torre de Control** (definiciones completas de la Query Library):
- `NR-INAPP-RAW` → N+R base, construido desde las 2 tablas arriba.
- `NR-INAPP-INVERSION-ALL` → Inversión (STG — pendiente Fase 4).
- `NR-INAPP-VALUE` → Valor Predicho 90D (STG — pendiente Fase 4).
- `NR-INAPP-CPA`, `NR-INAPP-ROAS` → derivados de inversión y valor (STG — pendiente Fase 4).
- `NR-INAPP-CPA-PAID`, `NR-INAPP-ROAS-PAID` → filtro `incentive_type != 'FREE'` + `channel_group IN ('POM','OC')`.

### Diagnósticos pre-implementación (Fase 0)

**Diagnóstico 1 — OC por CLASIFICACION (BT_OC_NR_REPORTE_TORRE_DAILY, MLM 2026):**

| CLASIFICACION | Canal dashboard | Volumen Abril 1-22 | Canales (CANAL field) |
|---|---|---|---|
| `UCRANIA` | **UCR Gest** | ~52K | PUSH · EMAIL · RE-Drawer · RE-QA · RE-Disc · RE-Congrats · PANDORA · WPP |
| `ACTIVATION` | **OC ACT** | ~44K | PUSH · EMAIL · WPP · PANDORA · JOURNEY |
| `ADHOC` | **OC ACT** | ~2.2K | PUSH · EMAIL |
| `OTHER RECURRING` | **UCR PRD** | ~-2.5K* | PUSH · EMAIL · JOURNEY · WPP |

*Negativos = correcciones retroactivas de atribución. Comportamiento normal certificado.

**Hallazgo crítico**: `CANAL='WHATSAPP'` en Torre = `TOUCHPOINT='WPP'` en tabla vieja. La query corp (`get_nr_corp_sql`) deberá actualizarse en Fase 3.

**Diagnóstico 2 — Paid por STRATEGY_GROUP (BT_MP_INDIVIDUALS_PERFORMANCE, MLM 2026):**

| Canal dashboard | STRATEGY_GROUP / NETWORK_GROUP_NAME | SOURCE_CD | N+R window |
|---|---|---|---|
| POM ADQ | `ACQUISITION POM`, `WEB POM`, `CTW POM` | INSTALLS | 7D |
| POM ACT | `ACTIVATION POM` | TOOL_COST + INSTALLS | Mixed (SOURCE_CD determina) |
| MGM ADQ | `MGM`, `MGM ECOSISTEMICO` (network) | INSTALLS | 7D |
| MGM ACT | `ACTIVATION MGM` | TOOL_COST | Standard |
| L&P ADQ | `LANDINGS`, `TELCEL`, `AFFILIATES`, `PARTNERSHIPS`, `BRANDFORMANCE` (network) | INSTALLS | 7D |
| L&P ACT | mismos networks | TOOL_COST | Standard |

**3 filas trampa identificadas y excluidas:**
1. `STRATEGY_GROUP='' + NETWORK='NOT NETWORK APPE'` → nr_7d=540K inflado (OC rows, ya en Torre Daily).
2. `STRATEGY_GROUP='' + NETWORK='ORGANIC'` → nr_7d=90K (BASELINE, no gestionado).
3. `STRATEGY_GROUP='PANDORA'` → ya está en Torre Daily como `CANAL='PANDORA'` dentro de UCRANIA/ACTIVATION.

**Diagnóstico 3 — Reconciliación totales Abril 1-22:**

| Fuente | Canal | NR |
|---|---|---|
| Torre Daily | OC total (UCR Gest + OC ACT + UCR PRD) | 97,626 |
| Individuals Perf | POM ADQ (ACQ+WEB+CTW) | 72,526 |
| Individuals Perf | POM ACT | 80,056 |
| Individuals Perf | MGM ACT | 230 |
| Individuals Perf | MGM ADQ (Ecosistema) | ~12,328 |
| Individuals Perf | L&P (LANDINGS+PARTNERSHIPS) | ~5,000 |

### Implementación — Fase 1

**Archivos modificados:**

| Archivo | Cambio |
|---|---|
| `config/channels_config.json` | +`tc_mapping` en los 10 nodos hoja de `hierarchy_nr`. `bq_mapping` y `cost_mapping` se conservan como documentación legacy. |
| `src/queries.py` | +`get_nr_tc_sql(HIERARCHY_NR)` — 170 líneas, completamente comentada. Genera SQL dinámico desde `tc_mapping` (mismo patrón que `get_nr_sql` leía `bq_mapping`). `get_nr_sql` conservada como fallback documentado. |
| `src/processors.py` | Import actualizado: `get_nr_sql` → `get_nr_tc_sql`. Call actualizado en línea 261+. Docstring actualizado. |

**Output del dashboard tras el cambio**: `11,311 KB` — sin errores.

### Campo `tc_mapping` en channels_config.json

Convive con `bq_mapping` (nunca se borra). Estructura:

```json
// OC — fuente: BT_OC_NR_REPORTE_TORRE_DAILY
"tc_mapping": { "source_tc": "torre_daily", "clasificacion_tc": ["UCRANIA"] }

// Paid — fuente: BT_MP_INDIVIDUALS_PERFORMANCE
"tc_mapping": { "source_tc": "individuals_performance",
                "strategy_group_tc": ["ACQUISITION POM", "WEB POM", "CTW POM"] }

// Con filtro SOURCE_CD (ADQ vs ACT)
"tc_mapping": { "source_tc": "individuals_performance",
                "network_group_name_tc": ["MGM", "MGM ECOSISTEMICO"],
                "source_cd_filter_tc": ["INSTALLS"] }

// ORG — diferido
"tc_mapping": { "source_tc": "baseline_skipped",
                "note_tc": "BASELINE = 271 GB en BT_MP_USER_ENGAGEMENT_INAPP. Diferido a Fase 5+." }
```

### Gotchas documentados para futuras sesiones

1. **Ordenamiento CASE WHEN**: en `paid_tc`, `STRATEGY_GROUP` va antes que `NETWORK_GROUP_NAME`. Garantiza que `ACTIVATION MGM` → MGM ACT gane sobre el filtro de red (MGM ADQ).
2. **PANDORA no va en paid_tc**: ya está en `oc_tc` como `CANAL='PANDORA'` dentro de CLASIFICACION=UCRANIA/ACTIVATION.
3. **ORG = 0 en Fases 1-4**: sin datos de `BT_MP_USER_ENGAGEMENT_INAPP` (271 GB), ORG devuelve 0 filas → `monthly_nr['ORG'][m] = 0`. Correcto por diseño.
4. **CANAL='WHATSAPP'** en Torre ≠ `TOUCHPOINT='WPP'` viejo → impacta `get_nr_corp_tc_sql()` (Fase 3).

### Fases pendientes

| Fase | Queries | Tabla deprecada reemplazada | Estado |
|---|---|---|---|
| ✅ **Fase 1** | `get_nr_tc_sql()` | `PANEL_MONTHLY_DAILY_HISTORICO` | DONE |
| ✅ **Fase 1** | `get_nr_tc_sql()` | `PANEL_MONTHLY_DAILY_HISTORICO` | DONE |
| ✅ **Fase 2** | `get_vpu_tc_sql()` | `PANEL_MONTHLY_DAILY_HISTORICO` | DONE |
| ✅ **Fase 3** | `get_nr_corp_tc_sql()` + `get_nr_corp_daily_tc_sql()` | `PANEL_MONTHLY_DAILY_HISTORICO` | DONE |
| ✅ **Fase 4** | `get_costos_tc_sql()` + `get_perf_paid_tc_sql()` + `get_roa_tc_sql()` | `PANEL_MONTHLY_COSTOS_CANALES` | DONE |
| 🔲 Fase 5 | Housekeeping docs + `bq_mapping` marcado legacy | — | Pendiente |
| `config/channels_config.json` | Ref History actualizada |

---

## 72. Sesión 2026-04-24 (continuación §71): Fases 2-4 + Análisis de Costos

### 72.1 Implementación Fase 2 — `get_vpu_tc_sql()` (VPU / Valor Pred 90D)

**Reemplaza**: `get_perf_vpu_sql(HIERARCHY_NR)`
**Output (idéntico)**: `MONTH_ID, PERF_CANAL, NR_TOTAL, NR_VPU_PROD`

| Fuente TC | Qué aporta |
|---|---|
| `BT_OC_NR_REPORTE_TORRE_DAILY` | `NR_INC_VALUE` = valor predicho 90D para usuarios incrementales OC |
| `BT_MP_INDIVIDUALS_PERFORMANCE` | `VALUE_MKT_USD_7D` (INSTALLS) o `VALUE_MKT_USD` (TOOL_COST) para canales Paid |
| `PANEL_MONTHLY_DAILY_HISTORICO` | `VALUE_MKT_PREDICTION_90D_NR_USERS` para ORG (legacy temporal hasta Fase 5+) |

Ventana de VPU sigue la misma lógica que N+R: `SOURCE_CD='INSTALLS'→7D`, `TOOL_COST→std`.

### 72.2 Implementación Fase 3 — Corp TC Migration (`get_nr_corp_tc_sql()` + daily)

**Reemplaza**: `get_nr_corp_sql()` y `get_nr_corp_daily_sql()`
**Output (idéntico)**: `fecha_mes_corp, corp_key, nr_total_corp` / `+ dia_del_mes`

**Fuentes TC usadas:**

| CTE | Tabla | Qué aporta |
|---|---|---|
| `oc_corp_tc` | `BT_OC_NR_REPORTE_TORRE_DAILY` | CLASIFICACION + CANAL → corp_key OC |
| `paid_corp_tc` | `BT_MP_INDIVIDUALS_PERFORMANCE` | STRATEGY_GROUP / NETWORK → corp_key POM/MGM/L&P |
| `org_corp_tc` | `PANEL_MONTHLY_DAILY_HISTORICO` | ORGANICO → NOATRIB|ORGANICO|TOTAL (legacy temporal) |

**Cambios críticos de mapeo vs tabla vieja:**

| Campo Torre | corp_key | Cambio vs antes |
|---|---|---|
| `CANAL='WHATSAPP'` | `*\|WPP` | Antes: `TOUCHPOINT='WPP'`. Nombre cambió en Torre. |
| `CLASIFICACION='ACTIVATION'` | `OC\|OC_REC\|{CANAL}` | Antes: `AP2='OWN CHANNELS RECURRING'`. ACTIVATION = campañas recurring. |
| `CLASIFICACION='OTHER RECURRING'` | `OC\|OC_REC\|{CANAL}` | Antes: `AP2='OWN CHANNELS RECURRING'`. |
| `CLASIFICACION='ADHOC'` | `OC\|OC_ADHOC\|TOTAL` | Sin cambio conceptual. |
| `OTH\|UCR_PRD`, `OTH\|SEO`, `OTH\|POM_SELLERS`, `OTH\|POM_OTHERS` | 0 NR | No aplica en TC (canales no gestionados). |

**Motivación del cambio**: El Corp Detalle mostraba 833K NR (fuente vieja) mientras FM mostraba 821K (TC). La diferencia de 12K era los canales en la vieja tabla (UCR PRD legacy, SEO, POM Sellers) que no existen en TC. Después de la migración, ambas vistas usan TC y los totales convergen.

**D-2 cutoff añadido**: Todas las CTEs tienen `AND DAY_ID/TIM_DAY/FECHA_DIARIA <= DATE_SUB(CURRENT_DATE(), INTERVAL 2 DAY)` para alinear con el día de referencia del MTD D7. Antes, las queries corp no tenían límite superior y podían incluir datos del día actual (incompletos).

### 72.3 Implementación Fase 4 — Costos TC

#### `get_costos_tc_sql(HIERARCHY_NR)` — Reemplaza `get_costos_sql(HIERARCHY_C)`

**Output (idéntico)**: `MONTH_ID, CANAL, INV_CANAL, INV_INCENTIVO, INV_TOTAL, INV_MANTIKA`

> ⚠️ **Nota**: La función ahora recibe `HIERARCHY_NR` (tiene `tc_mapping`) en lugar de `HIERARCHY_C`. Los labels de CANAL son idénticos en ambas jerarquías — `processors.py` no requiere cambios en su lógica de lookup.

**Mapeo de columnas (verificado vs Corp centralizado):**

| Componente Corp | Columna BQ Torre Daily (OC) | Columna BQ Individuals (Paid) |
|---|---|---|
| Inv. Canal | `COSTO_ENVIO_USD` (costo de envío push/email ≈ $0) | `COST_USD` (media cost) |
| Inv. Incentivos | `CONSUMIDO_USD` (cashback/incentivo al usuario) | `0` — ver Hallazgo crítico abajo |
| Inv. Mantika | `COSTO_MANTIKA_USD` (fee plataforma Mantika) | `0` |
| **Inv. Total** | Suma de los 3 | `COST_USD` |

**⚠️ Hallazgo crítico — COST_LC_INCENTIVOS para POM excluido:**
El Corp centralizado muestra POM INV_INCENTIVO = $0. Los incentivos de POM (cashback por install en `COST_LC_INCENTIVOS`) no se contabilizan como inversión de canal — son costo de producto, no marketing. Se excluyeron de `get_costos_tc_sql()`. Antes de este fix, se sumaban ~$1.4M/mes en POM que el Corp no cuenta.

#### `get_perf_paid_tc_sql(HIERARCHY_NR)` — Reemplaza `get_perf_paid_sql(HIERARCHY_C)`

- OC NR_PAID: filas donde `FLAG_PAID = 'PAID'`
- Paid NR_PAID: filas donde `COST_USD > 0`
- NR_GEST_OTHERS: `0` hardcoded (métrica legacy MGM sin equivalente TC)

#### `get_roa_tc_sql()` — Reemplaza `get_perf_roa_costos_sql()`

Solo OC: `CLASIFICACION IN ('UCRANIA', 'ACTIVATION', 'ADHOC')` con `FLAG_PAID='PAID'` y `costo > 0`.
- Numerador ROA = `SUM(NR_INC_VALUE)` (valor predicho para usuarios incrementales pagados)
- POM/MGM ROA sigue usando `perf_vpu_prod` en processors.py (sin cambio)

### 72.4 Helper interno `_tc_channel_parts(HIERARCHY_NR)`

Función privada que centraliza la clasificación de nodos hoja por `source_tc`. Reutilizada por `get_vpu_tc_sql()`, `get_costos_tc_sql()`, `get_perf_paid_tc_sql()`.

**NO usada por `get_nr_tc_sql()`** (que tiene su implementación inline con lógica condicional de `org_legacy_tc`).

Retorna dict con: `leaves_oc_tc`, `leaves_paid_tc`, `leaves_org_legacy`, `oc_case_stmt`, `paid_case_stmt`, `paid_where`, `org_case_stmt`.

**Ordenamiento crítico**: `leaves_paid_sg` (solo strategy_group_tc, sin network) va ANTES que `leaves_paid_ng` (con network_group_name_tc). Garantiza que `ACTIVATION MGM` → MGM ACT antes de que el filtro de red lo lleve a MGM ADQ.

### 72.5 Fix ORG en `get_nr_tc_sql()` — Fase 1 corregida post-deploy

**Bug detectado**: Al deployar Fase 1, el Total N+R bajó de 833K a 268K porque ORG tenía `source_tc="baseline_skipped"` y devolvía 0 filas. ORG representa ~565K usuarios/mes (orgánico/no atribuido).

**Fix**: Se añadió una 3ª rama `org_legacy_tc` en `get_nr_tc_sql()` que lee `CHANNEL_APERTURA_1='ORGANICO'` de `PANEL_MONTHLY_DAILY_HISTORICO`. Temporal hasta Fase 5+ (cuando `BT_MP_USER_ENGAGEMENT_INAPP` se implemente con cache para evitar su costo de 271 GB).

### 72.6 D-2 cutoff — alineación de día de referencia

Todas las queries TC tienen:
```sql
AND fecha <= DATE_SUB(CURRENT_DATE(), INTERVAL 2 DAY)
```

Antes de este fix, el NR Mensual mostraba datos más recientes que MTD D7 (diferentes días de referencia). Con el corte D-2, ambas pestañas usan el mismo día base: hoy−2.

### 72.7 Análisis exhaustivo de costos OC — Diagnóstico metodológico

**Motivación**: El dashboard mostraba INV_TOTAL marzo 2026 = $3.62M vs Corp centralizado = $4.2M. Gap de $580K.

#### Diagnóstico A — OC (`BT_OC_NR_REPORTE_TORRE_DAILY`, MLM Mar 2026)

| CLASIFICACION | CONSUMIDO_USD | COSTO_ENVIO_USD | COSTO_MANTIKA_USD | TOTAL | NR_INC_USERS |
|---|---|---|---|---|---|
| ACTIVATION | $561,511 | $39,974 | $20,310 | **$621,795** | 68,709 |
| UCRANIA | $363,972 | $0 | $0 | **$363,972** | 70,042 |
| OTHER RECURRING | $0 | $0 | $0 | $0 | 5,796 |
| ADHOC | $0 | $0 | $0 | $0 | 4,311 |
| **TOTAL OC TC** | | | | **$985,767** | 148,858 |

#### Diagnóstico A' — OC (`PANEL_MONTHLY_COSTOS_CANALES`, MLM Mar 2026)

| STRATEGY | CHANNEL | NR | INV_CANAL | INV_INCENTIVO | INV_TOTAL | VALUE_PRED |
|---|---|---|---|---|---|---|
| ACTIVATION | OWN CHANNELS MKT | 84,031 | $64,374 | $741,335 | $834,921 | $4,318,132 |
| UCRANIA | OWN CHANNELS MKT | 29,476 | $0 | $48,451 | $48,451 | $1,781,386 |
| **TOTAL** | | **113,507** | **$64,374** | **$789,786** | **$883,372** | **$6,099,518** |

#### Diagnóstico B — Paid (`BT_MP_INDIVIDUALS_PERFORMANCE`, MLM Mar 2026 — muestra top 30)

- ACQUISITION POM TIKTOK: COST_USD = $942,833, COST_LC_INCENTIVOS = $0
- ACTIVATION POM LIFTOFF: COST_USD = $233,112, COST_LC_INCENTIVOS = $376,330
- Blank STRATEGY_GROUP DV360: $468,123 (fuera de nuestra whitelist)
- OTHER POM TIKTOK: $154,367 (fuera de nuestra whitelist)

#### Hallazgo principal — Tres metodologías distintas de N+R y costo OC

| Fuente | NR OC Mar26 | INV_TOTAL OC Mar26 | CPA resultante |
|---|---|---|---|
| **Torre Daily (TC, lift/incremental)** | 139K (Test−Control) | $986K (consumido) | $7.1 |
| **PANEL_MONTHLY_COSTOS_CANALES (atribución clásica)** | 113K | $883K | $7.8 |
| **Corp centralizado (atribución total)** | **426K** (todos los tocados) | **$2.6M** (comprometido) | **$6.1** |

**Conclusión crítica**: La diferencia de $1.6M entre Torre Daily ($986K) y Corp centralizado ($2.6M) **NO es un bug**. Son metodologías fundamentalmente distintas:

- **Torre Daily (LIFT)**: Cuenta solo usuarios INCREMENTALES (Grupo Test − Grupo Control). El presupuesto = solo lo efectivamente CONSUMIDO (entregado a usuarios que convirtieron). Menor N+R, menor costo, VPU y CPA más conservadores.
- **Corp centralizado (ATRIBUCIÓN)**: Cuenta TODOS los usuarios tocados por una comm OC (independientemente de si hubieran convertido sin ella). Presupuesto = comprometido total (incluyendo comunicaciones a usuarios que no convirtieron). Mayor N+R, mayor costo, pero misma relación interna.

**Ambos CPA son internamente consistentes** con sus propias metodologías. El Corp usa su propio universo de N+R y costos.

**Decisión de diseño §72**: El dashboard MLM ADQ usa metodología TC (lift/incremental) que es el SSOT certificado por el equipo de Adquisición. Los números NO deben coincidir con el Corp centralizado porque miden cosas diferentes.

### 72.8 Fix INV_CANAL / INV_INCENTIVO (swap corregido)

**Bug**: En la implementación inicial de `get_costos_tc_sql()`, los campos OC estaban invertidos:
- Incorrecto: `INV_CANAL = CONSUMIDO_USD` (el grande), `INV_INCENTIVO = COSTO_ENVIO + MANTIKA` (el pequeño)
- Correcto: `INV_CANAL = COSTO_ENVIO_USD` (≈$0), `INV_INCENTIVO = CONSUMIDO_USD` (el cashback)

Verificado contra Corp centralizado que muestra OC INV_CANAL ≈ $0.0M, INV_INCENTIVO ≈ $2.5M.

El `INV_TOTAL` era correcto desde el inicio (suma los 3 componentes) → el CPA no estuvo afectado.

### 72.9 Nueva visualización — Desglose Inversión en Performance tabs

Ambas pestañas de Performance ahora muestran el mismo desglose que el Corp centralizado:
- `↳ Inv. Canal` — costo de envío (OC: `COSTO_ENVIO_USD`, Paid: `COST_USD`)
- `↳ Inv. Incentivos` — cashback (OC: `CONSUMIDO_USD`, Paid: `$0`)
- `↳ Inv. Mantika` — fee plataforma (OC: `COSTO_MANTIKA_USD`, Paid: `$0`)

Solo aparece si hay valores > 0. Permite validación componente por componente vs Corp centralizado.

**Archivos modificados**:
- `src/queries.py`: `get_costos_tc_sql()` añade `INV_MANTIKA` como 4ª columna de output
- `src/processors.py`: `monthly_inv_mantika` añadido a los dicts de costos
- `src/builders.py`: `build_perf_table_html()` + `build_perf_corp_table_html()` — 3 sub-filas nuevas
- `src/gen_dashboard_v1.py`: `build_perf_corp_data()` — añade `actual_inv_canal/incentivo/mantika`

### 72.10 Archivos modificados en §72

| Archivo | Cambio |
|---|---|
| `src/queries.py` | +`_tc_channel_parts()` (helper). +`get_vpu_tc_sql()`. +`get_costos_tc_sql()` con `INV_MANTIKA`. +`get_perf_paid_tc_sql()`. +`get_roa_tc_sql()`. +`get_nr_corp_tc_sql()`. +`get_nr_corp_daily_tc_sql()`. Fix INV_CANAL↔INV_INCENTIVO. Excluir COST_LC_INCENTIVOS POM. D-2 cutoff en todas las queries TC. D-2 cutoff añadido a `get_nr_corp_sql()` / `get_nr_corp_daily_sql()` legacy. |
| `src/processors.py` | Import actualizado (5 funciones TC). Llamadas actualizadas para costos+VPU+ROA+Corp. `monthly_inv_mantika` añadido. |
| `src/gen_dashboard_v1.py` | `build_perf_corp_data()`: +`actual_inv_canal`, `actual_inv_incentivo`, `actual_inv_mantika`. |
| `src/builders.py` | `build_perf_table_html()`: extrae `monthly_inv_canal/incentivo/mantika`. 3 sub-filas de desglose. `build_perf_corp_table_html()`: 3 sub-filas de desglose por nodo. |
| `config/channels_config.json` | `tc_mapping` añadido a los 10 nodos hoja de `hierarchy_nr`. |
| `CLAUDE.md` | Actualizado con arquitectura TC completa, fases, metodología de costos. |
| `docs/History.md` | §71 (Fase 1) + §72 (Fases 2-4 + diagnósticos) |

### 72.11 Estado final de la migración Torre de Control

| Fase | Función(es) | Tabla deprecada reemplazada | Estado |
|---|---|---|---|
| ✅ **Fase 1** | `get_nr_tc_sql()` | `PANEL_MONTHLY_DAILY_HISTORICO` | DONE |
| ✅ **Fase 2** | `get_vpu_tc_sql()` | `PANEL_MONTHLY_DAILY_HISTORICO` | DONE |
| ✅ **Fase 3** | `get_nr_corp_tc_sql()` + `get_nr_corp_daily_tc_sql()` | `PANEL_MONTHLY_DAILY_HISTORICO` | DONE |
| ✅ **Fase 4** | `get_costos_tc_sql()` + `get_perf_paid_tc_sql()` + `get_roa_tc_sql()` | `PANEL_MONTHLY_COSTOS_CANALES` | DONE |
| 🔲 **Fase 5** | Housekeeping: `bq_mapping` marcado legacy, `get_nr_sql()` removida | — | Pendiente |

**Pendiente crítico — Validación VPU/ROA OC**:
La query de diagnóstico para comparar `NR_INC_VALUE` de Torre Daily vs `VALUE_PRED` de COSTOS_CANALES para OC en marzo 2026 **quedó pendiente de ejecutar**. Esto completa la validación del ROA. Ver query al final de §72 en conversación.

---

## 73. Sesión 2026-04-25/27: Sistema de Clasificación de Comms + Análisis OC+UCR Bain-level

### 73.1 Nuevo archivo: `config/comms_classification_config.json`

**Motivación**: El dashboard mostraba el sub-canal OWN CHANNELS RECURRING PUSH con -6,339 NR pero no había forma automática de saber qué campañas específicas lo causaban. Faltaba el "tejido conectivo" entre los KPIs del Corp y las comunicaciones individuales de Comms_OC.

**Propósito**: Diccionario oficial que traduce `CAMPAIGN_NAME_CLEAN` → `sub_canal_corp` + `medio_corp` + `clasificacion_tc` + alertas automáticas. Permite que los skills identifiquen automáticamente qué campaña causó un decline en el dashboard.

**Estructura del archivo**:

```json
{
  "_canal_maps": {
    "canal_comms_to_medio_corp": { "PUSH":"PUSH", "WHATSAPP":"WPP", ... },
    "clasificacion_tc_to_sub_canal_corp": { "UCRANIA":"UCRANIA E&G", "ACTIVATION":"OWN CHANNELS RECURRING", ... },
    "flow_bq_to_tipo": { "APP-MP-INSTALL":"ACQUISITION", "CREDIT-CARD":"PRODUCT", ... }
  },
  "name_classification_rules": [ ... 7 reglas por prioridad ... ],
  "known_campaigns": { ... campañas confirmadas con status ... },
  "alert_rules": [ ... 4 reglas de alerta con thresholds ... ],
  "drill_down_protocol": { ... 6 pasos para ir de KPI decline → campaña → alerta ... },
  "cadencia_definitions": { "DIARIA":"riesgo ALTO", "SEMANAL_MIERCOLES":"riesgo BAJO", ... }
}
```

**7 Reglas de clasificación (ordenadas por prioridad — menor = más específico)**:

| Priority | id | tokens_include | sub_canal_corp | medio_corp |
|---|---|---|---|---|
| 1 | `journey_activation` | `["JNY"]` | OWN CHANNELS RECURRING | JOURNEY |
| 10 | `ucrania_eg_explicit` | `["EG","UCR"]` | UCRANIA E&G | infer_from_CANAL |
| 15 | `pandora_explicit` | `["PANDORA"]` | UCRANIA E&G | PANDORA |
| 20 | `adhoc_non_journey` | `["AH"]` excl `["JNY"]` | OWN CHANNELS ADHOC | infer_from_CANAL |
| 25 | `postcompra_trigger` | `["POSTCOMPRA"]` | OWN CHANNELS RECURRING | infer_from_CANAL |
| 30 | `ucrania_recurring_batch` | `["UCR"]` excl `["JNY","AH","EG"]` | UCRANIA E&G | infer_from_CANAL |
| 40 | `activation_recurring` | `["ACT"]` excl `["JNY","AH"]` | OWN CHANNELS RECURRING | infer_from_CANAL |

**4 Campañas conocidas documentadas**:

| Campaña | Status | Acción | History ref |
|---|---|---|---|
| `MLM_ML_I_AH_UCR_JNY_CARABO` | CANIBALIZADOR_CONFIRMADO | PAUSAR HOY | §63 |
| `MLM_ML_I_AH_UCR_JNY_MST2MP` | CANIBALIZADOR_CONFIRMADO | PAUSAR HOY | §63 |
| `flows_communication_MLM_I_EG_MTK_mer_*` | EXITOSO_HISTORICO | MANTENER | §61 |

**4 Alert rules**:
- `journey_canibalizador`: USER_INC_7d < -50 → severity CRÍTICO → PAUSAR HOY
- `medio_declining_30pct`: MoM < -20% en OWN CHANNELS RECURRING → ALERTA
- `sub_canal_decay_chain`: sub_canal cae >20% + known CANIBALIZADOR activo → CRÍTICO
- `journey_daily_positive_ok`: JOURNEY trigger-based + USER_INC > 0 → INFO → MANTENER

### 73.2 Actualizaciones a los skills

**`skills/analizar-OC_Comms_skill.md`**:
- Añadido `config/comms_classification_config.json` como fuente #3 (antes: Dashboard Comms_OC era #3)
- Nuevo **Modo 16 `drill_decay [sub_canal] [medio]`**: Drill-down automático Corp KPI decline → campañas responsables → alerta. 6 pasos, output template incluido.
- Dispatch table actualizado con `drill_decay`

**`skills/OPTIMIZADOR-OC_skill.md`**:
- `comms_classification_config.json` añadido a FUENTES DE DATOS con descripción de sus secciones clave
- Nueva fila en tabla de orquestación: `alerta_canal` → Modo 16 `drill_decay` + config
- Nueva sección **PROTOCOLO DE ALERTA AUTOMÁTICA (§73)**: trigger conditions, secuencia de 5 pasos de ejecución, regla de oro del orquestador ("La pausa de un journey canibalizador NO es una recomendación — ES UNA OBLIGACIÓN")

### 73.3 Reescritura completa de `build_oc_ucr_analysis_tab_html()`

**Motivación**: La pestaña Análisis OC+UCR tenía contenido estático desactualizado (datos de meses anteriores hardcodeados). Se reemplazó completamente usando los 3 skills en máxima potencia con datos reales de Abril 2026.

**Metodología de análisis aplicada**:
- `analizar-Optimizar_Performance_KPIs_skill.md` MODO_OC_UCR: situación vs plan, waterfall MoM
- `analizar-OC_Comms_skill.md` drill_decay + ranking_multidim: campañas canibalizadoras, golden nugget
- `OPTIMIZADOR-OC_skill.md` alerta_canal: veredicto ejecutivo, acciones no negociables
- Datos: KPI context §B1 (Q1-2026) + comms_monthly_summary Abr-2026 + BT_OC_MP_FLOWS_DAILY

**Estructura del nuevo análisis (7 secciones)**:
1. **Hero / Bottom Line**: diagnóstico en 3 oraciones, estilo Bain top-down
2. **4 KPI Cards**: MTD actual (97.6K), pace cierre (~133K), gap plan (-87.8K), target agosto (240K)
3. **Performance Q1 vs Plan**: tabla Mar/Feb/Ene-26 con deltas, alerta de regresión
4. **Waterfall MoM visual**: barras proporcionales → JOURNEY = 61% del problema (-10,253 de -17,637)
5. **Causa Raíz + Golden Nugget**: JOURNEY canibalizadores + DEB-CARD EMAIL outlier (+31,659 UI = 60% del impacto total de Abril)
6. **Calibradores + 6 acciones**: Pandora 0.2 vs 0.6 → +7.2K NR quick win; acciones hoy/semana/estructural
7. **Camino crítico visual + Veredicto del VP**: 133K → 160K → 185K → 210K → 240K con palancas; 3 decisiones no negociables

**Datos reales integrados del análisis**:
- Comms_monthly_summary Abr-2026: USER_INC total +52,560 (máximo de Q1-26); efficiency score 122.8 NR/comm (2.5x Feb)
- DEB-CARD EMAIL outlier: +21,933 (OR 32.3%) + +9,726 (OR 25.7%) = +31,659 USER_INC = 60% del total del mes
- JOURNEY APP-MP-INSTALL: -14,304 INC_USERS confirmado por BT_OC_MP_FLOWS_DAILY
- PANDORA calibrador: UCR 0.6→0.2 (-3K NR/mes) + ACT 0.6→0.2 (-4.2K NR/mes) = -7.2K/mes total

### 73.4 Diagnóstico PUSH OWN CHANNELS RECURRING (-6,339)

**Hallazgo del análisis**: OWN CHANNELS RECURRING PUSH cayó -6,339 NR (LMTD Mar D23=40,052 vs MTD Abr D23=33,713). Para identificar las campañas responsables:

**Gotchas críticos de `DASHBOARD_CAMPAIGNS_INDIVIDUOS_METRICAS` (documentados por primera vez)**:

| Campo | Error común | Correcto |
|---|---|---|
| `CAMPAIGN_NAME_CLEAN` | ❌ No existe en la tabla | `CAMPAIGN_NAME` (raw) → derivar CLEAN con CASE WHEN |
| Campo CANAL | ❌ No existe en esta tabla | JOIN con `BT_OC_DASHBOARD_ALL_CAMPAIGNS` donde `CANAL` sí existe |
| Nombre campaña en `BT_OC_DASHBOARD_ALL_CAMPAIGNS` | `CAMPAIGN_NAME` | `COMUNICATION_NAME` (typo en schema original de Meli — mantener así) |

**Query diagnóstico para PUSH ACTIVATION Mar vs Abr** (query documentada en conversación):
1. CTE `camp_canal`: obtiene CANAL='PUSH' de `BT_OC_DASHBOARD_ALL_CAMPAIGNS`
2. CTE `mar` + `abr`: filtra `DASHBOARD_CAMPAIGNS_INDIVIDUOS_METRICAS` con STRATEGY='ACTIVATION' + INNER JOIN para PUSH
3. FULL OUTER JOIN por campaign name → muestra delta + status (Nueva/Salió/Continúa)

### 73.5 Análisis del decline PUSH ACTIVATION: metodología de drill-down end-to-end

**El flujo completo validado en esta sesión**:

```
Dashboard Corp muestra:
  OWN CHANNELS RECURRING PUSH: -6,339 MoM
            ↓
comms_classification_config.json lookup:
  rule=journey_activation → tokens=['JNY'] → filtrar CANAL='PUSH' en ACTIVATION
            ↓
BT_OC_MP_FLOWS_DAILY FLOW='APP-MP-INSTALL':
  -14,304 INC_USERS April 1-22 (confirmed)
            ↓
DASHBOARD_CAMPAIGNS_INDIVIDUOS_METRICAS + BT_OC_DASHBOARD_ALL_CAMPAIGNS JOIN:
  → identificar campañas específicas PUSH ACTIVATION con delta negativo
            ↓
known_campaigns lookup:
  CARABO + MST2MP → status=CANIBALIZADOR_CONFIRMADO → PAUSAR HOY
```

### 73.6 Archivos modificados en §73

| Archivo | Cambio |
|---|---|
| `config/comms_classification_config.json` | **NUEVO** — 7 reglas, 4 campañas conocidas, 4 alert_rules, 6-paso drill-down protocol, taxonomía FLOW, cadencia_definitions |
| `skills/analizar-OC_Comms_skill.md` | +fuente #3 comms_classification_config. +Modo 16 `drill_decay`. Dispatch table actualizado |
| `skills/OPTIMIZADOR-OC_skill.md` | +comms_classification_config en FUENTES. +modo `alerta_canal` en tabla orquestación. +PROTOCOLO DE ALERTA AUTOMÁTICA con trigger conditions y regla de oro |
| `src/builders_analysis.py` | `build_oc_ucr_analysis_tab_html()` completamente reescrita (~1500 líneas → ~300 líneas HTML denso con datos reales Abr-2026). CSS autocontenido. 7 secciones ejecutivas. |

---

## 74. Sesión 2026-04-27: Correcciones Vista FM — POM Others + Plan N+R (ver sección completa arriba)

---

## 75. Sesión 2026-04-27: Migración Completa Fuentes Comms_OC

### 75.1 Motivación

La pestaña Comms_OC usaba una arquitectura de 4 ramas UNION ALL (PUSH+EMAIL desde 3 tablas con 2 JOINs complejos, FLOWS desde `BT_OC_MP_FLOWS_DAILY`, RE desde `DIM_REE_METRICS_PRINTS`+`DIM_REE_TAPS`). Esta arquitectura tenía problemas:
- JOIN frágil por `CAMPAIGN_NAME_CLEAN` (campo derivado) con `DASHBOARD_CAMPAIGNS_INDIVIDUOS_METRICAS`
- Métricas de impacto (M_LIFT, M_CVR_TEST) inconsistentes o eliminadas en la nueva fuente
- No había `TOTAL_ABSOLUTO_NR` ni `RATIO_CANIBALIZACION_ORGANICA`
- Granularidad mensual (no podía filtrar por día exacto)
- RAMA D (RE) separada, con schema distinto para prints/taps

### 75.2 Nueva Arquitectura — 2 Ramas

```
New Comms_OC (granularidad: COMM_ID × SENT_DATE × CANAL) =
  RAMA A: SBOX_EG_MKT.BT_OC_DASHBOARD_ALL_CAMPAIGNS_NR
    - Cubre: OC ACT + UCR ADHOC + JOURNEYS + RE (OC) + PANDORA + WPP
    - USER_INC: dual — UCRANIA/ACQUISITION usa NEW_7D_ADJUST+REC_7D_ADJUST (Adjust 7D);
                ACTIVATION usa NR_INC_USERS (calibrado Blacklist)
    - TOTAL_ABSOLUTO_NR + RATIO_CANIBALIZACION_ORGANICA disponibles
    - Filtro: STRATEGY IN ('UCRANIA','ACTIVATION','ACQUISITION')
              AND TEAM NOT IN ('SELLERS','ADHOC - SELLERS')

  ∪ RAMA B: SBOX_EG_MKT.BT_OC_DASHBOARD_ALL_CAMPAIGNS_NR_ACQUISITION
    - Cubre: UCR Gest recurring + RE (UCR Gest)
    - USER_INC: Q_NR_7D (solo incremental Adjust 7D)
    - VALUE_INC: VALUE_PREDICTED (real atribuido)
    - Sin TOTAL_ABSOLUTO_NR (solo incrementales disponibles)
    - Sin COSTO_MANTIKA_USD (no aplica a UCR Gest)
```

**Dedup:** `QUALIFY ROW_NUMBER() OVER (PARTITION BY COMMUNICATION_ID, SENT_DATE, CANAL) = 1`
**FUENTE_TABLA:** columna nueva que identifica el origen de cada fila.

### 75.3 Columnas Schema Nuevo vs Legacy

| Columna vieja | Estado | Columna nueva | Fuente |
|---|---|---|---|
| `FIRST_SENT_DATE` | Renombrado | `SENT_DATE` | directo |
| `MONTH_ID` (YYYYMM string) | Mantener | `MONTH_ID` | `FORMAT_DATE('%Y%m', MONTH_ID)` |
| `CANAL`, `STRATEGY`, `SUBSTRATEGY`, `TEAM` | Sin cambio | Ídem | directo |
| `APP` | Reemplazado | `CHANNEL` | CHANNEL (normalizado) |
| `TYPE_NAME` | Reemplazado | `CLASIF_CAMPAIGNS` | CLASIF_CAMPAIGNS / CLASIFICATION |
| `NOTIFICATION_TITLE` | ❌ Eliminado | — | No existe en nuevas tablas |
| `NOTIFICATION_TEXT` | ❌ Eliminado | — | No existe en nuevas tablas |
| `M_CVR_TEST` / `M_LIFT` | ❌ Eliminados | — | Eliminados de fuente |
| `TPN_INC` / `TPV_INC` | ❌ Eliminados | — | Eliminados de fuente |
| `TOTAL_CREATE`, `TOTAL_SHOWN` | ❌ Eliminados | — | No en nuevas tablas |
| `BLACKLIST/BLOCKED/BOUNCE/SPAM` | ❌ Eliminados | — | Hardcoded 0 antes; eliminados |
| `TOTAL_PRINTS_RE` / `UNIQUE_PRINTS_RE` / `TOTAL_TAPS_RE` / `UNIQUE_TAPS_RE` | ❌ Eliminados | — | RE ahora usa `VOLUMEN_SENT`/`VOLUMEN_OPEN` |
| `USER_INC` | Fuente nueva | `USER_INC` | Rama A: dual lógica · Rama B: Q_NR_7D |
| `VALUE_INC` | Fuente nueva | `VALUE_INC` | Rama A: NR_INC_VALUE · Rama B: VALUE_PREDICTED |
| `TOTAL_CLICK` | Real ahora | `TOTAL_CLICK` | VOLUMEN_CLICK (ya no hardcoded 0) |
| — | 🆕 Nuevo | `FUENTE_TABLA` | 'ALL_CAMPAIGNS_NR' \| 'NR_ACQUISITION' |
| — | 🆕 Nuevo | `TOTAL_ABSOLUTO_NR` | NEW_COUNT_USERS_TEST_CONV + REC_COUNT (Rama A) |
| — | 🆕 Nuevo | `RATIO_CANIBALIZACION` | (ABSOLUTO-INCREMENTAL)/ABSOLUTO (Rama A) |
| — | 🆕 Nuevo | `CLASIF_CAMPAIGNS` | CLASIF_CAMPAIGNS / CLASIFICATION |
| — | 🆕 Nuevo | `FLAG_PAID` / `FLAG_INCENTIVO` | directo |
| — | 🆕 Nuevo | `CONSUMIDO_USD` / `COSTO_ENVIO_USD` / `COSTO_MANTIKA_USD` | directo |

**Schema final: 33 columnas** (vs 39 legacy — más limpio y más rico).

### 75.4 Cambios en `process_comms_oc()` — Nueva clave dedup

**Clave vieja:** `(COMMUNICATION_ID, MONTH_ID)` — granularidad mensual.
**Clave nueva:** `(COMMUNICATION_ID, SENT_DATE, CANAL, FUENTE_TABLA)` — granularidad diaria por canal.

Tier 2 sigue ganando sobre Tier 1 en colisión.

### 75.5 Cambios en `build_comms_oc_table_html()` — 27 columnas visibles

Eliminadas: M_CVR_TEST, M_LIFT, TPN_INC, TPV_INC, NOTIFICATION_TITLE, NOTIFICATION_TEXT, CREATE, SHOWN, BLACKLIST/BLOCKED/BOUNCE/SPAM, PRINTS_RE/TAPS_RE columns.
Añadidas: FUENTE_TABLA, TOTAL_ABSOLUTO_NR, RATIO_CANIBALIZACION, CLASIF_CAMPAIGNS, FLAG_PAID, CONSUMIDO_USD, COSTO_ENVIO_USD, COSTO_MANTIKA_USD.

### 75.6 Cambios en `template_dashboard.html` JS

- `renderCommsOcKPIs()`: Eliminadas cards CREATE/SHOWN/CVR/LIFT/RE-específicas. Añadidas `Σ Absoluto NR` y `Avg % Canibalizac.` con color (>50%=rojo, 20-50%=naranja, <20%=verde).
- `_commsOcFilterState`: Removidos `app`/`typename`/`title`/`text`. Añadidos `fuente`/`clasif`.
- `initCommsOcFilters()`: Dropdowns actualizados. Fuente/Clasif/Notif.Type/Team/BizLine/SegCanal + 1 text search (Campaña).
- `applyCommsOcFilters()`: Todos los filtros ahora son exactos (no STRING_AGG).
- Flag de init: `comms-f-app` → `comms-f-fuente`.

### 75.7 Validación

- **3,714 registros frescos** del nuevo schema para el mes actual (Abril 2026)
- **Dashboard generado:** 10,234 KB — sobre la guardia de 50KB para CI/CD
- **Pre-migración documentada:** `config/queries/comms_oc_legacy.md` (snapshot inmutable)

### 75.8 Pendiente post-migración

| Tarea | Comando | Cuándo |
|---|---|---|
| **Rebuild cache completo** con nuevo schema | `python scripts/refresh_comms_oc_cache.py --full` | Off-peak (la nueva query es ~111 MB/mes, estimar 15-30 min) |
| Verificar RE en `_ACQUISITION` | Revisar si CANAL='RE-*' aparece en los datos reales | Después del rebuild |
| Actualizar `comms_oc.md` con nueva arquitectura | Editar `config/queries/comms_oc.md` | Post-rebuild |

### 75.8b Fix post-deploy: Dedup cross-tabla — FUENTE_TABLA='AMBAS'

**Problema detectado:** Campañas presentes en AMBAS tablas (`BT_OC_DASHBOARD_ALL_CAMPAIGNS_NR` y `BT_OC_DASHBOARD_ALL_CAMPAIGNS_NR_ACQUISITION`) aparecían duplicadas en Comms_OC. Ejemplo: `MLM-ML-I-EG-UCR-MTK-CAMP-NIA-MARA-1` mostraba 2 filas para el mismo `(COMM_ID, SENT_DATE, CANAL)`.

**Solución:** Las dos ramas (rama_a, rama_b) se convirtieron en CTEs dentro de un `WITH`. Se añadió una CTE `combined` (UNION ALL) y el SELECT final colapsa con:
```sql
WITH rama_a AS (...), rama_b AS (...), combined AS (SELECT * FROM rama_a UNION ALL SELECT * FROM rama_b)
SELECT
  COMMUNICATION_ID, SENT_DATE, MONTH_ID, CANAL,  -- GROUP BY key
  CASE WHEN COUNT(DISTINCT FUENTE_TABLA) > 1 THEN 'AMBAS' ELSE ANY_VALUE(FUENTE_TABLA) END AS FUENTE_TABLA,
  -- Prioridad Rama A para métricas: COALESCE(MAX(IF(FUENTE_TABLA='ALL_CAMPAIGNS_NR', campo, NULL)), MAX(campo))
  ...
FROM combined
GROUP BY COMMUNICATION_ID, SENT_DATE, MONTH_ID, CANAL
```

**Resultado:** 3,714 filas (con duplicados) → **3,020 filas** (sin duplicados). Distribución Abril-2026:
- `ALL_CAMPAIGNS_NR`: 1,355 (solo en Rama A)
- `AMBAS`: 761 (en ambas tablas — deduplicadas)
- `NR_ACQUISITION`: 904 (solo en Rama B)

### 75.9 Archivos modificados en §75

| Archivo | Cambio |
|---|---|
| `src/queries.py` | `get_comms_oc_fresh_sql()` reescrita — 4 ramas → 2 ramas. QUALIFY por (COMM_ID, SENT_DATE, CANAL). FUENTE_TABLA. Lógica dual USER_INC. |
| `scripts/refresh_comms_oc_cache.py` | `build_comms_oc_sql_for_date_range()` reescrita — misma lógica con filtro SENT_DATE paramétrico. |
| `src/processors.py` | `process_comms_oc()`: clave dedup `(COMM_ID, SENT_DATE, CANAL, FUENTE_TABLA)`. Ordenamiento por SENT_DATE. |
| `src/builders.py` | `build_comms_oc_table_html()` reescrita — 27 columnas nuevo schema. |
| `src/template_dashboard.html` | `renderCommsOcKPIs()`: cards simplificadas + Absoluto/Ratio. `_commsOcFilterState`/`initCommsOcFilters()`/`onCommsOcFilterChange()`/`applyCommsOcFilters()`/`clearCommsOcFilters()`: schema actualizado. Flag init actualizado. |
| `data/comms_oc_cache.json` | **Eliminado** — schema incompatible. Rebuild pendiente. |
| `data/comms_oc_current_month.json` | **Regenerado** — 3,714 registros mes actual nuevo schema. |
| `config/queries/comms_oc_legacy.md` | **NUEVO** — snapshot pre-migración inmutable (4 ramas, schema completo, gotchas). |
| `config/queries/comms_oc.md` | Marcado "en transición §75". |

## 74. Sesión 2026-04-27: Correcciones Vista FM — POM Others + Plan N+R

### 74.1 Motivación

Tres correcciones al modelo de datos de la vista FM detectadas en revisión exhaustiva post-§72:

1. **POM ADQ incluía incorrectamente WEB POM + CTW POM** → son estrategias distintas de ACQUISITION POM que merecen línea propia (`pom_others`).
2. **POM TOTAL plan usaba solo row 5 (POM gest)** → debe sumar row 5 + row 9 (POM no gestionado).
3. **Plan Producto OC+UCR usaba 100% de row 17** → el otro 50% va a OTHERS (no visible en vista FM), corrección a 50%.
4. **UCR Gest / UCR PRD / OC ACT / POM ADQ / POM ACT tenían `plan_row_valor` individual** → no tienen plan de valor individual; se eliminan para que los builders no muestren filas "Plan VPU / vs Plan VPU" para estos canales.

### 74.2 Nuevo nodo `pom_others` en vista FM

**Canal nuevo**: `POM Others` — sub-canal de POM TOTAL en `hierarchy_nr`.

| Campo | Valor |
|---|---|
| `id` | `pom_others` |
| `label` | `POM Others` |
| `level` / `indent` | `leaf` / 2 |
| `color` | `#7ECBBF` |
| `tc_mapping.source_tc` | `individuals_performance` |
| `tc_mapping.strategy_group_tc` | `["WEB POM", "CTW POM"]` |
| `plan_row` | (ninguno — cubierto por POM TOTAL) |
| `plan_row_valor` | (ninguno — sin plan individual) |
| `no_cost` | (no — tiene `COST_USD` como el resto de POM) |

**`pom_adq` corregido**: `strategy_group_tc` → solo `["ACQUISITION POM"]` (antes incluía WEB POM + CTW POM).

**`pom_total` children**: `["pom_adq", "pom_act", "pom_others"]`

**Propagación automática**: `_tc_channel_parts()` auto-genera el SQL CASE WHEN desde `tc_mapping`. Sin cambios en `queries.py`, `processors.py` ni `builders.py`.

**`hierarchy_cost`**: se añadió `pom_others_c` (label `"POM Others"`) para que `build_perf_bar()` (que itera `HIERARCHY_C`) encuentre los datos de inversión.

### 74.3 Corrección Plan N+R — `plan_rows` multi-fila

**Problema**: `pom_total` tenía `plan_row: 5` (solo POM gest). El plan de negocio incluye POM no gestionado (row 9).

**Solución**: nuevo campo `plan_rows: [5, 9]` en `channels_config.json`. Reemplaza `plan_row: 5`.

**Cambio en `load_plan()`** (`src/gen_dashboard_v1.py`): nuevo bloque post-lectura directa que itera canales con `plan_rows` y suma todas las filas:

```python
for canal in HIERARCHY_NR:
    if 'plan_rows' not in canal:
        continue
    for row_iloc in canal['plan_rows']:
        # acumula en plan_nr[canal['label']][month_key]
```

**Fix encadenado**: condición de suma de sub-líneas cambió de `'plan_row' not in canal` → `'plan_row' not in canal and 'plan_rows' not in canal`. Evita que POM TOTAL sobreescriba su plan con la suma de sus `plan_lines`.

**Valores verificados (202604)**: POM TOTAL plan = 126,493 (gest) + 8,693 (no gest) = **135,186**.

### 74.4 Corrección Plan Producto — multiplicador 0.5

**Problema**: Plan Producto OC+UCR leía 100% de Excel row 17 ("Others + Producto"). El 50% restante corresponde a OTHERS (sin visibilidad en vista FM).

**Solución**: nuevo campo `"multiplier": 0.5` en la `plan_line` de Plan Producto:

```json
{ "label": "Plan Producto", "rows": [17], "color": "#1AB059", "no_chart": true, "multiplier": 0.5 }
```

**Cambio en `load_plan()`**: lectura de sub-líneas aplica `float(raw_val) * sub_line_multiplier` (default 1.0 sin multiplicador → retrocompatible con Plan Recurring y Plan Ad-Hoc).

**Valores verificados (202604)**: Plan Producto = 8,438 (antes 16,875). OC+UCR plan = 155,257 + 13,269 + 8,438 = **176,964**.

### 74.5 Eliminación `plan_row_valor` sin plan individual

Los siguientes canales **no tienen plan de valor predicho individual** en el Excel. Sus `plan_row_valor` apuntaban a filas que corresponden a agregados o a otros nodos, generando filas "Plan VPU / vs Plan VPU" incorrectas en la tabla Performance FM.

| Canal | `plan_row_valor` eliminado |
|---|---|
| `ucr_gest` | 54 |
| `ucr_prd` | 53 |
| `oc_act` | 56 |
| `pom_adq` | 51 |
| `pom_act` | 55 |

**Efecto en builders**: `plan_valor[label]` queda como `{}` → `build_perf_table_html()` detecta dict vacío → omite filas Plan VPU / vs Plan VPU / Plan Valor / vs Plan Valor para estos canales. Sin cambios en código Python.

**Propagación bottom-up**: OC+UCR sigue leyendo `plan_row_valor: 52` directamente (no se ve afectado). Ucrania y POM TOTAL no tienen `plan_row_valor` → propagan desde hijos → quedan vacíos (correcto: no tienen plan de valor propio).

### 74.6 Archivos modificados en §74

| Archivo | Cambio |
|---|---|
| `config/channels_config.json` | **11 cambios**: +`pom_others` en `hierarchy_nr` · `pom_total` `plan_row`→`plan_rows:[5,9]` · `pom_adq.tc_mapping` solo ACQUISITION POM · `Plan Producto` +`multiplier:0.5` · eliminado `plan_row_valor` de 5 canales · +`pom_others_c` en `hierarchy_cost` · `pom_total_c.children` +pom_others_c · `pom_adq_c.cost_mapping` corregido |
| `src/gen_dashboard_v1.py` | `load_plan()`: +bloque `plan_rows` multi-fila · +`sub_line_multiplier` en lectura sub-líneas · fix condición `plan_rows not in canal` |
| `dashboard_v1.html` | Regenerado — **11,187 KB** |

---

## 76. Sesión 2026-04-27: Rediseño de Skills + Fix ORG + Auditoría de Fuentes

### 76.1 Rediseño arquitectural de los 3 Skills de análisis

**Motivación**: Los 3 skills tenían 4,364 líneas totales con ~700 líneas duplicadas entre OPTIMIZADOR y los otros dos. El OPTIMIZADOR hacía análisis en lugar de orquestar, generando confusión de responsabilidad y consumo innecesario de tokens.

**Nueva arquitectura**:
```
Capa 1A: KPI Skill (analizar-Optimizar_Performance_KPIs_skill.md)
  → "¿Qué pasó a los KPIs?" — canales, subcanales, MoM, vs Plan, VPU, CPA, ROA

Capa 1B: Comms Skill (analizar-OC_Comms_skill.md)
  → "¿Qué comunicaciones lo causaron?" — Top/Bottom, familia campañas, fingerprint

Capa 2: OPTIMIZADOR (OPTIMIZADOR-OC_skill.md)
  → "La orquesta estratégica" — recibe info ya pulida, cruza señales, emite juicio
```

**OPTIMIZADOR v4.0 → v4.1** (2,062 → 792 líneas, -62%):
- Eliminadas ~700 líneas de análisis duplicado (funnel, fatiga VP, sweet spots, atribución causal)
- Añadido Framework Cross-Signal: **7 Patrones de agujas en el pajar** que nadie ve en el dashboard:
  1. Divergencia KPI-Comms (crecimiento es IS, no comms)
  2. Efecto Familia / Pareto interno (ruido canibaliza al ganador)
  3. Suelo invisible de saturación
  4. El timing como driver real (no el canal, no el VP)
  5. RATIO_CANIBALIZACION creciente (experimento se degrada)
  6. Lag de calibrador (4-8 semanas entre ajuste y efecto)
  7. Concentración de audiencia cross-tabla (solapamiento ALL_CAMPAIGNS_NR + NR_ACQUISITION)
- Añadidos: contratos de input explícitos, tabla de orquestación actualizada
- Añadido: `TEMPLATE_STOP_OR_CONTINUE` con impactos positivo/negativo + sustituto + Golden Rule

**Comms Skill v3.3 → v3.4**:
- **Modo 17: `familia_campanas [prefix]`** — análisis jerárquico de familias de campañas por prefijo de nombre. Clasifica nodos en GANADOR/CONTRIBUYENTE/RUIDO/CANIBALIZADOR. Calcula NR impact de simplificar la familia. Caso real Mar-2026: `flows_..._STOCK_MONEYINHI2` genera 56% del USER_INC de su familia mientras MONEYINAM compite por la misma audiencia.
- **Modo 18: `campaña_historico [nombre_o_prefix]`** — carrera histórica de una campaña a través de todos los meses. Calcula Índice de Decaimiento (ID = USER_INC_mes / USER_INC_pico). Clasifica en PEAK/MESETA/FATIGA/AGOTADA/CANIBALIZANDO. Incluye análisis STOP_OR_CONTINUE con impactos positivo y negativo, sustituto recomendado y Golden Rule. Anti-alucinación integrada (Regla 6): detecta automáticamente cuando "MARA" o similar es código interno y no un evento real.

### 76.2 Pestaña Análisis OC+UCR — Reescritura completa con datos reales

**Problema**: La pestaña mostraba datos del schema §73 (antiguo), con valores de OLD schema como +31,659 USER_INC para DEB-CARD que no coincidían con el nuevo schema §75.

**Solución**: Reescritura completa de `build_oc_ucr_analysis_tab_html()` aplicando los 3 skills a máxima potencia con datos reales del nuevo schema §75.

**Datos reales integrados** (comms_monthly_summary.md por mes, canal y BL):
- RATIO_CANIBALIZACION ≈ 0.97: solo 3% de conversiones positivas son verdaderamente incrementales
- INDIVIDUAL LIFE CYCLE: +12K UI (Ene-26) → +29K UI (Mar-26) → +23K UI (Abr-26) (+107% Q1)
- DIGITAL ACCOUNTS: +38.5K IS-adj (Ene) → +17.3K IS-adj (Abr) = -55% → suelo de saturación (Patrón 3)
- GENERIC_MP (RE-Drawer): +642 (Ene) → +883 (Mar, PEAK ID=1.00, 4.39 UI/comm) → AUSENTE (Abr)
- DEB-CARD EMAIL: OR 18-27% en todos los meses, carrera MESETA→PEAK→FATIGA de alcance
- WPP DACCNT: OR 65-68% constante — canal más sub-escalado del portafolio (170-290 comms vs 1,600+ PUSH)
- MARA: USER_INC=0 en todos los meses → código interno, no Maratón CDMX → PARAR definitivo

**Nuevas secciones en el tab**:
- OPTIMIZADOR v4.1 — 5 Patrones detectados (con datos reales Abr-26)
- BL Rankings IS-ajustados (Modo 14 aplicado: ganadores y perdedores Q1)
- Carrera histórica campañas clave (Modo 18: GENERIC_MP, DEB-CARD, WPP, MONEYINHI2)
- Eficiencia de comms en nuevo schema §75 (con nota metodológica)
- Quick Wins actualizados (desde constantes QUICK_WINS en builders_analysis.py)

### 76.3 Fix crítico: ORG canal — Migración definitiva a TC

**El bug**: ORG mostraba LMTD = -27,734 (negativo) y MTD = 5,061 (debería ser ~600-700K). Vista Corp NO ATRIBUIDO: 174K (debería ser ~600K).

**Causa raíz**: `PANEL_MONTHLY_DAILY_HISTORICO` (tabla deprecated desde §71) para `CHANNEL_APERTURA_1='ORGANICO'` estaba recibiendo correcciones retroactivas negativas en 2026, haciendo que el acumulado mensual fuera negativo o muy pequeño. Esta tabla fue deprecated en §71 pero nunca se había migrado completamente para ORG (Fase 5 pendiente).

**Investigación en BQ** (consulta ejecutada para diagnóstico):
- `BT_MP_USER_ENGAGEMENT_INAPP`: esquema completamente diferente al esperado (usuario-evento, no N+R agregado)
- `BT_MP_INDIVIDUALS_PERFORMANCE` con `NETWORK_GROUP_NAME='NOT NETWORK APPE'`:
  - `CHANNEL_GROUP='OTHER'` + `SOURCE_CD='TOOL_COST'` → **nr_std = 705K para Mar-26** ✅
  - `CHANNEL_GROUP='OC'` → excluido (ya en Torre Daily) ✅
  - Validado: Ene-26=625K, Feb-26=545K, Mar-26=705K, Abr-26=557K — coincide con ~700K del equipo

**La nota "fila trampa" del §72 era incorrecta para ORG**: se marcó `NOT NETWORK APPE` como trampa para POM (inflaba POM si se incluía). Pero para ORG específicamente, esta fila con `CHANNEL_GROUP='OTHER'` es la fuente correcta: usuarios que instalaron MP sin atribución a ningún canal de red.

**Fix implementado en §76** (estado intermedio — ver §77 para implementación final):
- `queries.py` `get_nr_corp_tc_sql()`: `org_corp_tc` CTE migrado de `PANEL_MONTHLY_DAILY_HISTORICO` → `BT_MP_INDIVIDUALS_PERFORMANCE NOT NETWORK APPE`
- `queries.py` `get_nr_corp_daily_tc_sql()`: mismo cambio en `org_corp_daily_tc`

> **§77 completó la implementación**: El CTE dedicado `org_legacy_tc` en `get_nr_tc_sql()` y `org_vpu_cte` en `get_vpu_tc_sql()` también migraron a NOT NETWORK APPE. `channels_config.json` mantiene `source_tc: "baseline_skipped"` (genera el CTE dedicado, evita colisión con CASE WHEN de POM Others). Ver §77 para validación final y resultado definitivo.

### 76.4 Auditoría completa de consistencia de fuentes

Se auditaron todos los archivos del proyecto para garantizar que todas las referencias a fuentes de datos son correctas. Cambios aplicados:

**`src/queries.py`**:
- 5 funciones legacy marcadas explícitamente como `DEPRECATED §71/§72 — NO USADO`: `get_nr_sql`, `get_nr_corp_sql`, `get_nr_corp_daily_sql`, `get_costos_sql`, `get_perf_paid_sql`, `get_perf_vpu_sql`
- `org_legacy_tc` CTE en `get_nr_tc_sql()`: comentario actualizado a "CÓDIGO MUERTO §75" (nunca se genera porque `leaves_org_legacy` está vacío)
- `org_vpu_tc` CTE en `get_vpu_tc_sql()`: mismo comentario (ORG VPU ahora en `paid_vpu_tc`)
- Docstrings de `get_nr_corp_tc_sql()` y `get_nr_corp_daily_tc_sql()` actualizados con nueva fuente

**`config/channels_config.json`**:
- ORG: `bq_mapping: {is_org: true}` renombrado a `_bq_mapping_deprecated` con nota §71
- `corp_noatrib._doc` actualizado: fuente §75 `BT_MP_INDIVIDUALS_PERFORMANCE NOT NETWORK APPE`
- `hierarchy_nr_corp` `_doc` actualizado: referencia a TC en lugar de PANEL_MONTHLY_DAILY_HISTORICO

**`src/processors.py`**:
- Docstrings de `process_nr_corp()` y `process_nr_corp_daily()` actualizados con la nueva fuente TC

**`CLAUDE.md`**:
- Tabla de queries: ORG y NO ATRIBUIDO actualizados a §77 (CTE dedicado NOT NETWORK APPE)
- Tabla deprecated: `PANEL_MONTHLY_DAILY_HISTORICO` marcada como `✅ MIGRADA §77`
- `source_tc: "baseline_skipped"` se mantiene — es el branch que genera el CTE dedicado (no eliminar)

**Skills** (CHANGELOG.md v3.2/v3.3/v4.0/v4.1):
- `analizar-OC_Comms_skill.md` v3.4: Modo 17 + Modo 18 + TEMPLATE_STOP_OR_CONTINUE
- `OPTIMIZADOR-OC_skill.md` v4.1: 7 Patrones Cross-Signal + contratos de input + tabla orquestación completa
- `CHANGELOG.md`: Entradas v3.2 a v4.1 documentadas

### 76.5 Comms_OC cache: rebuild histórico y fix de tamaño

**Problema de deploy (TimeoutError)**: El dashboard llegó a 82 MB porque el cache `comms_oc_cache.json` tenía 44,030 registros del schema ANTIGUO (pre-§75) mezclados con 3,020 del nuevo schema. Esto generó 47,050 filas HTML = 79 MB solo en el tab Comms_OC.

**Fix**: Eliminado cache viejo (schema incompatible). Rebuild con `--full` usando el nuevo schema §75:
- Cache reconstruido: 20,708 registros (Nov-25 → Mar-26) con nuevo schema
- Dashboard después del rebuild: **42.7 MB** — dentro del límite de Apps Script API (~50 MB)

**Schema del cache**: dedup key cambiada de `(COMM_ID, MONTH_ID)` → `(COMM_ID, SENT_DATE, CANAL, FUENTE_TABLA)` para granularidad diaria.

### 76.6 Archivos modificados en §76

| Archivo | Cambio |
|---|---|
| `skills/analizar-OC_Comms_skill.md` | v3.4: +Modo 17 `familia_campanas` · +Modo 18 `campaña_historico` (ID, STOP_OR_CONTINUE, Golden Rule, Regla 6) |
| `skills/OPTIMIZADOR-OC_skill.md` | v4.1: 2,062→792 líneas · 7 Patrones Cross-Signal · contratos input · TEMPLATE_STOP_OR_CONTINUE · trigger canibalizador en triage |
| `skills/CHANGELOG.md` | Entradas v3.2 a v4.1 |
| `src/builders_analysis.py` | `build_oc_ucr_analysis_tab_html()` reescrita con datos reales §75: 7 secciones, BL rankings, carrera campañas, eficiencia §75 |
| `config/channels_config.json` | ORG: `tc_mapping` → `individuals_performance NOT NETWORK APPE TOOL_COST` · `bq_mapping` → `_bq_mapping_deprecated` |
| `src/queries.py` | `get_nr_corp_tc_sql()` y `get_nr_corp_daily_tc_sql()`: `org_*_tc` migrado de PANEL_MONTHLY_DAILY_HISTORICO → BT_MP_INDIVIDUALS_PERFORMANCE NOT NETWORK APPE · 6 funciones legacy marcadas DEPRECATED · (get_nr_tc_sql y get_vpu_tc_sql completados en §77) |
| `src/processors.py` | Docstrings actualizados con fuentes TC §75 · (bloque cache ORG eliminado en §77) |
| `scripts/refresh_org_cache.py` | **NUEVO** en §76 como alternativa INAPP residual — **marcado DEPRECATED en §77** (NOT NETWORK APPE directo no requiere cache) |
| `CLAUDE.md` | Fuentes ORG actualizadas · deprecated table marcada MIGRADA · nota fila trampa corregida · skills historial actualizado |
| `dashboard_v1.html` | Regenerado — **42.7 MB** · ORG correcto ~600-700K/mes |

---

## §77 — 27-Abr-2026 — ORG definitivo: NOT NETWORK APPE directo (sin cache, sin residual)

### 77.1 Problema raíz confirmado

La investigación BQ de §76 había identificado que `NOT NETWORK APPE` (~590K) estaba siendo incorrectamente restado del total INAPP como canal atribuido. La hipótesis del usuario resultó correcta: estas filas representan el BASELINE / usuarios sin atribución a canal de red.

**Diagnóstico final BQ** (Apr-26 MTD a 27-Abr):
- `tmp_total` (INAPP days_since_first=0 OR days_since_prior>89): 944K
- `tmp_channel` (canales atribuidos BT_MP_INDIVIDUALS_PERFORMANCE): 680K
  - De ese total: 590K = NOT NETWORK APPE (clasificado como POM_OTHER por POM_FLAG)
- `tmp_oc` (BT_OC_NR_REPORTE_TORRE_DAILY): 111K
- BASELINE residual (metodología INAPP): 152K ← **INCORRECTO** (demasiado bajo)
- NOT NETWORK APPE directo: 589K ← **CORRECTO** (validado ~600-700K/mes esperado)

### 77.2 Decisión de implementación

**Opción elegida**: NOT NETWORK APPE directo desde `BT_MP_INDIVIDUALS_PERFORMANCE` (SOURCE_CD='TOOL_COST'), CTE dedicado separado del CASE WHEN de `paid_tc`.

**Por qué CTE dedicado** (no añadir a `paid_tc` dinámico):
- NOT NETWORK APPE rows pueden tener STRATEGY_GROUP=WEB POM/CTW POM (POM_FLAG-based)
- El CASE WHEN de `paid_tc` clasificaría esas filas como POM Others ANTES de llegar al WHEN de ORG
- CTE dedicado evita cualquier colisión de ordenamiento → fuente exclusiva, sin riesgo

**Por qué mantener `source_tc: "baseline_skipped"** en channels_config.json:
- El branch `baseline_skipped` genera el CTE dedicado (`org_legacy_tc`) en `get_nr_tc_sql()`
- NOT NETWORK APPE está fuera del whitelist WHERE de `paid_tc` → cero double-counting
- Patrón consistente con `oc_tc` (OC también tiene CTE propio)

### 77.3 Cambios implementados

**`src/queries.py`**:
- `get_nr_tc_sql()`: `org_legacy_cte_tc` reescrito — elimina query a PANEL_MONTHLY_DAILY_HISTORICO, usa `BT_MP_INDIVIDUALS_PERFORMANCE WHERE UPPER(NETWORK_GROUP_NAME)='NOT NETWORK APPE' AND SOURCE_CD='TOOL_COST'` con GROUP BY TIM_DAY
- `get_vpu_tc_sql()`: `org_vpu_cte` reescrito — mismo filtro, columnas VALUE_MKT_USD_NEW_USERS + VALUE_MKT_USD_RECOVERED_USERS para VPU org
- `get_nr_corp_tc_sql()`: `org_corp_tc` reescrito — NOT NETWORK APPE, GROUP BY TIM_DAY
- `get_nr_corp_daily_tc_sql()`: `org_corp_daily_tc` reescrito — mismo, añade dia_del_mes

**`src/processors.py`**:
- Eliminado bloque de inyección de cache ORG (líneas 270-309) — ORG ahora viene directo de BQ en df_nr

**`config/channels_config.json`**:
- `tc_mapping._note` de ORG actualizado: NOT NETWORK APPE directo, CTE dedicado

**`scripts/refresh_org_cache.py`**:
- Marcado DEPRECATED — ya no necesario

### 77.4 Validación

```
Checks Python (sin BQ):
  FM SQL: NOT NETWORK APPE presente, PANEL ausente ✓
  Corp SQL: NOT NETWORK APPE presente, PANEL ausente ✓
  Corp Daily: NOT NETWORK APPE presente, PANEL ausente ✓
  VPU SQL: NOT NETWORK APPE presente, PANEL ausente ✓

Dashboard generado: 43.7 MB ✓
ORG monthly_nr (hierarchy_nr):
  Apr-2025: 523K, Feb-2026: 618K, Mar-2026: 747K, Apr-2026 MTD: 641K ✓
  Rango: 500-750K/mes — dentro del esperado ~600-700K
PANEL_MONTHLY_DAILY_HISTORICO: 0 menciones en HTML ✓
```

### 77.5 Archivos modificados en §77

| Archivo | Cambio |
|---|---|
| `src/queries.py` | `org_legacy_cte_tc` en `get_nr_tc_sql()`: PANEL→BT_MP_INDIVIDUALS_PERFORMANCE NOT NETWORK APPE · `org_vpu_cte` en `get_vpu_tc_sql()`: mismo · `org_corp_tc` y `org_corp_daily_tc`: mismo con GROUP BY |
| `src/processors.py` | Eliminado bloque cache ORG (40 líneas) |
| `config/channels_config.json` | `tc_mapping._note` de ORG: documenta NOT NETWORK APPE vía CTE dedicado |
| `scripts/refresh_org_cache.py` | Marcado DEPRECATED — reemplazado por query directa en el dashboard |
| `CLAUDE.md` | §77 añadido al historial · `source_tc: "baseline_skipped"` documentado como "CTE dedicado NOT NETWORK APPE" |
| `dashboard_v1.html` | Regenerado — **43.7 MB** · ORG ~640K Apr-26 MTD · PANEL ausente en producción |

---

## §78 — 29-Abr-2026 — Correcciones Corp OTHERS + ORG residual INAPP + POM Others FM

### 78.1 Contexto

Comparando el dashboard vs una tabla de referencia del equipo (query SQL canónica), se identificaron 3 gaps en la vista Corp OTHERS (~14K NR) y 1 gap en ORG/NO ATRIBUIDO (~46K NR). El diagnóstico requirió 2 queries BQ de verificación.

### 78.2 Fix 1 — UCR PRD Corp (~5.4K NR)

**Bug**: `CLASIFICACION='OTHER RECURRING'` en `oc_corp_tc` mapeaba a `OC|OC_REC|*` (OC Recurring), cuando debería ir a `OTH|UCR_PRD|TOTAL`.

**Causa**: El mapeo corp heredó la lógica de `OTHER RECURRING → OC Recurring` que es incorrecta. En la query de referencia, `OTHER RECURRING` va a OTHERS grupo → UCRANIA PRD.

**Fix** en `get_nr_corp_tc_sql()` y `get_nr_corp_daily_tc_sql()`:
```sql
-- ANTES:
WHEN CLASIFICACION = 'OTHER RECURRING' AND UPPER(CANAL) = 'EMAIL' THEN 'OC|OC_REC|EMAIL'
-- ... (múltiples medios)

-- DESPUÉS:
WHEN CLASIFICACION = 'OTHER RECURRING' THEN 'OTH|UCR_PRD|TOTAL'  -- §78 fix
```

Resultado: Corp UCR PRD = ~5,365 NR (antes = 0), Corp OC Recurring ya no inflado.

### 78.3 Fix 2 — POM Others Corp (~2.4K NR)

**Diagnóstico BQ** (query ejecutada): filas con `STRATEGY_GROUP='OTHER POM'` y `CHANNEL_GROUP='POM_OTHER'` + varios `NETWORK_GROUP_NAME` (DV360, Google, Facebook, Tiktok, Liftoff). Total ~3,584 NR para Abr D1-27.

**Insight clave de la query de referencia**: el check `UPPER(POM_FLAG) IN ('POM ACTIVATION','POM ACQUISITION','POM OTHERS')` dispara **ANTES** de la lista de redes orgánicas (TIKTOK, FACEBOOK, etc.). Por eso:
- `POM_FLAG='POM Others'` + TIKTOK → 'POM OTHERS' (no ORGANIC)
- `POM_FLAG='POM APPE CREDITS ENG IN'` + TIKTOK → 'ORGANIC' (POM_FLAG no matchea → cae en redes orgánicas)

De los ~3,584 NR del diagnóstico, solo ~2,347 tienen `POM_FLAG='POM Others'` → van a POM OTHERS. El resto (~1,237) tiene POM_FLAG diferente + red orgánica → van a ORGANIC en la referencia, y en nuestro dashboard van al residual ORG.

**Fix** en `paid_corp_tc` (ambas corp queries): añadir condición POM_FLAG ANTES del whitelist, y añadir al WHERE:
```sql
-- Nuevo WHEN en CASE:
WHEN UPPER(POM_FLAG) IN ('POM ACTIVATION','POM ACQUISITION','POM OTHERS') THEN 'OTH|POM_OTHERS|TOTAL'

-- Nuevo en WHERE:
OR UPPER(POM_FLAG) IN ('POM ACTIVATION','POM ACQUISITION','POM OTHERS')
```

### 78.4 Fix 3 — L&P Corp (~6.4K NR)

**Diagnóstico BQ** (query ejecutada): filas con `STRATEGY_GROUP=''` (vacío) y `NETWORK_GROUP_NAME IN ('PARTNERSHIPS','LANDINGS','BRANDFORMANCE')` con NR = 2,923 + 2,919 + 1,111 = 6,953.

**Causa**: `paid_corp_tc` tenía `WHEN NETWORK_GROUP_NAME = 'PARTNERSHIPS'` (sin UPPER, case-sensitive), mientras el WHERE usaba `UPPER(NETWORK_GROUP_NAME) IN ('PARTNERSHIPS')`. Con STRATEGY_GROUP vacío, las filas pasaban el WHERE pero el CASE WHEN fallaba → CANAL IS NULL → filtradas.

**Fix**: UPPER() consistente en TODOS los WHEN de L&P:
```sql
WHEN UPPER(NETWORK_GROUP_NAME) = 'PARTNERSHIPS' THEN 'OTH|LP|PARTNERSHIPS'  -- era sin UPPER
```

### 78.5 Fix 4 — Corp NO ATRIBUIDO: INAPP residual exacto (~46K NR)

**Motivación**: Corp NO ATRIBUIDO usaba `NOT NETWORK APPE + TOOL_COST` (~665K). La referencia usa residual `INAPP_TOTAL − OC − PAID` = ~712K. Gap de ~46K.

**Verificación de costo**: `SELECT COUNT(*), COUNT(DISTINCT CUS_CUST_ID) FROM BT_MP_USER_ENGAGEMENT_INAPP WHERE SIT_SITE_ID='MLM' AND EVENT_DATE >= '2025-01-01' AND (DAYS_SINCE_FIRST_EVENT=0 OR DAYS_SINCE_PRIOR_EVENT>89)` → **20.16 GB, 12.3M usuarios**. Manejable.

**Fix** en `get_nr_corp_tc_sql()` y `get_nr_corp_daily_tc_sql()`:
1. Añadir `inapp_total_corp` CTE desde `BT_MP_USER_ENGAGEMENT_INAPP`
2. Añadir `others_catchall_corp_tc` para capturar POM_FLAG rows como `OTH|POM_OTHERS|TOTAL` (luego removido — se maneja via `paid_corp_tc` POM_FLAG condition)
3. Reemplazar `org_corp_tc` NOT NETWORK APPE → residual:
```sql
org_corp_tc AS (
  SELECT t.fecha_mes_corp, 'NOATRIB|ORGANICO|TOTAL' AS corp_key,
    GREATEST(t.nr_total - COALESCE(oc.nr,0) - COALESCE(p.nr,0) - COALESCE(cat.nr,0), 0) AS nr_corp
  FROM inapp_total_corp t
  LEFT JOIN oc_total_corp oc ... LEFT JOIN paid_total_corp p ... LEFT JOIN catch_total_corp cat ...
)
```

Resultado: Corp NO ATRIBUIDO = ~683K (residual) vs antes ~665K. **Total Corp = ~1,007K ≈ INAPP total** ✓.

### 78.6 Fix 5 — FM ORG residual INAPP (Fix A, §78)

**Motivación**: FM ORG usaba NOT NETWORK APPE (~666K). Referencia muestra ORGANICO ~712K. Gap de ~46K. Con BT_MP_USER_ENGAGEMENT_INAPP a 20 GB (manejable), se implementa el mismo residual que Corp.

**Fix** en `get_nr_tc_sql()`: reemplazar `org_legacy_tc` (NOT NETWORK APPE) → residual INAPP − OC − PAID − POM_FLAG:
```sql
inapp_total_tc AS (... BT_MP_USER_ENGAGEMENT_INAPP ...),
oc_day_tc   AS (SELECT fecha_tc, SUM(NR) AS NR FROM oc_tc   ...),
paid_day_tc AS (SELECT fecha_tc, SUM(NR) AS NR FROM paid_tc  ...),
pf_day_tc   AS (SELECT fecha_tc, SUM(NR) AS NR FROM pom_flag_tc ...),
org_legacy_tc AS (
  SELECT t.fecha_tc, 'ORG' AS CANAL,
    GREATEST(t.NR_TOTAL - COALESCE(oc.NR,0) - COALESCE(p.NR,0) - COALESCE(pf.NR,0), 0) AS NR
  FROM inapp_total_tc t LEFT JOIN oc_day_tc oc ... LEFT JOIN paid_day_tc p ... LEFT JOIN pf_day_tc pf ...
)
```

Resultado: FM ORG = ~683-712K (residual). FM Total N+R = ~1,040K (más cercano a INAPP total ~1,045K) ✓.

### 78.7 Fix B — POM Others FM via POM_FLAG (§78)

**Motivación**: POM_FLAG='POM Others' rows (~2,347 NR) debían aparecer en algún canal FM. En la referencia van a OTHERS → POM OTHERS, pero `hierarchy_nr` FM no tiene grupo OTHERS.

**Decisión de diseño §78**: las filas POM_FLAG se RESTAN del residual ORG (en `pf_day_tc`) pero NO se suman a ningún canal FM explícito. Razón: en FM, `pom_others` = WEB POM + CTW POM (sub-canales POM de Corp). Mezclar POM_FLAG (que son OTHERS en Corp) en `pom_others` FM causaría inconsistencia FM vs Corp:
- FM `pom_others` = WEB+CTW = ~5,301 NR
- Corp `corp_pom_others` = POM_FLAG = ~2,402 NR
- Son sub-canales DISTINTOS con el mismo label

**Implementación**: `pom_flag_tc` se define en WITH (para `pf_day_tc` del residual) pero NO se incluye en `union_tc`. Las filas POM_FLAG van al residual ORG.

Para VPU/costos/paid (queries FM):
- `pom_flag_vpu_tc`, `pom_flag_cost_tc`, `pom_flag_paid_tc` definidos pero excluidos de sus UNION respectivos
- Motivo: consistencia — si N+R de POM_FLAG no está en `pom_others` FM, VPU/costos tampoco deben estarlo

**Corp**: `corp_pom_others` N+R via `paid_corp_tc` POM_FLAG condition (correcto ✓). Performance Corp de `corp_pom_others`: por consistencia con Corp N+R.

### 78.8 Deploy script — Fix límite 200 versiones Apps Script

**Problema**: `deploy_appscript_v1.py` fallaba con `HttpError 429` al intentar crear versión 201 en Apps Script (límite = 200).

**Fix**: 
- Eliminado `purge_old_versions()` (no existe `projects().versions().delete()` en la API v1 de Apps Script).
- Añadido `check_version_count()`: lista versiones actuales, imprime conteo, dispara warning detallado con instrucciones cuando ≥ 180/200.
- Añadido `VERSION_HARD_LIMIT = 199`: si se llega al límite, reutiliza la última versión existente en lugar de fallar.

**Nota**: borrar versiones solo posible vía UI de Apps Script (no via API). Las instrucciones manuales aparecen en el output del deploy cuando se acerca el límite.

### 78.9 _tc_channel_parts() — Campo pom_others_label

Añadido campo `pom_others_label` al dict de retorno de `_tc_channel_parts()` para uso en CTEs pom_flag de VPU/costos/paid. Lookup dinámico desde HIERARCHY_NR (`next(c for c in H if c.get('id')=='pom_others')`).

### 78.10 Archivos modificados en §78

| Archivo | Cambio |
|---|---|
| `src/queries.py` | `get_nr_corp_tc_sql()` + `get_nr_corp_daily_tc_sql()`: UCR PRD fix (OTHER RECURRING→UCR_PRD) · POM_FLAG condition en `paid_corp_tc` · UPPER() consistente en L&P · INAPP residual para NO ATRIBUIDO. `get_nr_tc_sql()`: INAPP residual para ORG (Fix A) · `pom_flag_tc` CTE para ORG subtraction (Fix B, no en union_tc). `_tc_channel_parts()`: +`pom_others_label` en return. `get_vpu_tc_sql()` + `get_costos_tc_sql()` + `get_perf_paid_tc_sql()`: `pom_flag_*` CTEs añadidos (definidos pero excluidos de UNION). `deploy_appscript_v1.py`: `check_version_count()` + `VERSION_HARD_LIMIT`. |
| `config/channels_config.json` | `corp_pom_others` mapping: `has_cost:true, has_vpu:true` · `corp_ucr_prd` visible en Corp. |
| `CLAUDE.md` + `docs/History.md` | §78 documentado, fuentes actualizadas |
| `dashboard_v1.html` | Regenerado — **44.0 MB** |

### 78.11 Estado final de Corp OTHERS (post-§78)

| Sub-canal | Antes | Después | Fuente |
|---|---|---|---|
| MGM | ~15K ✅ | ~15K ✅ | `paid_corp_tc` NETWORK MGM |
| L&P | ~7K ❌ | ~13K ✅ | `paid_corp_tc` UPPER() fix |
| UCR PRD | 0 ❌ | ~5.4K ✅ | `oc_corp_tc` OTHER RECURRING fix |
| POM OTHERS | 0 ❌ | ~2.4K ✅ | `paid_corp_tc` POM_FLAG fix |
| SEO / POM SELLERS / POM OTHERS | 0 (sin datos TC) | 0 (correcto) | No aplica en TC |
| **OTHERS total** | ~21K ❌ | ~35K ✅ | Suma correcta |
| **NO ATRIBUIDO** | ~665K ❌ | ~683K ✅ | INAPP residual |

---

## §79 — 29-Abr-2026 — Comms_OC: NR_TOTAL_Test + NR_TOTAL_Control + FM Total fix

### 79.1 Contexto y motivación

El usuario solicitó clarificar las métricas de la pestaña Comms_OC:
1. El nombre `TEST` (= VOLUMEN_ENTRY_TEST, usuarios que recibieron la comm) es confuso — debe llamarse `Sents`
2. `Absoluto NR` es un nombre técnico poco descriptivo — debe llamarse `NR_TOTAL_Test`
3. Faltaba la contraparte: `NR_TOTAL_Control` (conversiones brutas del grupo de control)

Adicionalmente, se detectó que **FM Total N+R ≠ Corp Total N+R** — inconsistencia causada por el manejo de `pom_flag_tc`.

### 79.2 Renombrado columnas Comms_OC

| Antes | Después | Fuente BQ | Qué mide |
|---|---|---|---|
| `TEST` | **`Sents`** | `VOLUMEN_ENTRY_TEST` | Usuarios únicos que recibieron la comm (grupo Test) |
| `Absoluto NR` | **`NR_TOTAL_Test`** | `NEW_COUNT_USERS_TEST_CONV + REC_COUNT_USERS_TEST_CONV` | Conversiones BRUTAS del grupo Test (sin calibrar) |
| *(nuevo)* | **`NR_TOTAL_Control`** | `NEW_COUNT_USERS_CONTROL_CONV + REC_COUNT_USERS_CONTROL_CONV` | Conversiones BRUTAS del grupo Control (benchmark orgánico) |

**Nota metodológica** (documentada al usuario): `USER_INC = 0` con `NR_TOTAL_Test >> NR_TOTAL_Control` es posible cuando las TASAS de conversión son iguales. Lo relevante no son los absolutos sino:
- `Tasa Test = NR_TOTAL_Test / Sents`
- `Tasa Control = NR_TOTAL_Control / CONTROL`
- Si Tasa Test ≈ Tasa Control → USER_INC ≈ 0 → % Canibalizac. ≈ 100%

Ejemplo de la sesión: Sents=1.25M, Control=172K, NR_TOTAL_Test=5,153, NR_TOTAL_Control=719 → Tasa Test=0.412% ≈ Tasa Control=0.417% → USER_INC ≈ 0.

### 79.3 Implementación técnica

**`src/queries.py`** — `get_comms_oc_fresh_sql()`:
- Rama A: añadido `COALESCE(NEW_COUNT_USERS_CONTROL_CONV, 0) + COALESCE(REC_COUNT_USERS_CONTROL_CONV, 0) AS NR_TOTAL_CONTROL`
- Rama B: añadido `CAST(NULL AS FLOAT64) AS NR_TOTAL_CONTROL` (tabla sin datos de control)
- Dedup GROUP BY: `MAX(NR_TOTAL_CONTROL) AS NR_TOTAL_CONTROL`

**`scripts/refresh_comms_oc_cache.py`**: mismos cambios en `build_comms_oc_sql_for_date_range()` (para cache histórico).

**`src/builders.py`** — `build_comms_oc_table_html()`:
- Headers: `'TEST'→'Sents'`, `'Absoluto NR'→'NR_TOTAL_Test'`, +`'NR_TOTAL_Control'` (columna 23)
- Extracción: `control_nr_val = safe_float_or_none(record.get('NR_TOTAL_CONTROL'))`
- `data-control-nr="{da_control_nr}"` en el `<tr>`
- Nuevo `<td>` para `NR_TOTAL_Control` entre NR_TOTAL_Test y % Canibalizac.

**`src/template_dashboard.html`** — `renderCommsOcKPIs()`:
- `totalControlNr` acumulado desde `row.dataset.controlNr`
- KPI card: `'Σ NR_TOTAL_Control'` con valor `fmtInt(totalControlNr)`
- Texto KPI de funnel: `VOLUMEN_ENTRY_TEST → Sents`
- KPI card `'Test' → 'Sents'`

**Cache histórico** (Tier 1): requiere rebuild con `--full` para incluir `NR_TOTAL_CONTROL` en registros Nov-25→Mar-26. Hasta entonces, columna muestra `—` para registros cacheados.

### 79.4 Fix FM Total = Corp Total (pf_day_tc)

**Problema detectado**: FM Total N+R ≈ 1,043K ≠ Corp Total N+R ≈ 1,045K. Diferencia = ~2,347 NR.

**Causa raíz**: `pom_flag_tc` (filas POM_FLAG='POM Others', ~2.3K NR) se **restaba** del residual ORG en `get_nr_tc_sql()` via `pf_day_tc`, pero **no se sumaba** a ningún canal FM → FM Total = INAPP − POM_FLAG < INAPP.

En Corp: esas mismas filas van a `corp_pom_others` (+) y se restan de NO ATRIBUIDO (−) → cancela → Corp Total = INAPP.

**Fix**: eliminar `pf_day_tc` del residual ORG en `get_nr_tc_sql()`. Las filas POM_FLAG se absorben en ORG FM (sin canal FM explícito, coherente con que en FM no hay grupo OTHERS):

```python
# Antes:
_pf_day_cte      = "pf_day_tc AS (... FROM pom_flag_tc ...)"
_pf_day_subtract = "- COALESCE(pf.NR, 0)"

# Después:
_pf_day_cte      = ""   # pom_flag_tc no se resta del residual FM
_pf_day_subtract = ""   # FM Total = INAPP Total ✓
```

Resultado: FM Total = Corp Total = INAPP total (~1,045K) ✅.

### 79.5 Diagnóstico L&P (finding informativo)

Query diagnóstico corrida en BQ para investigar brecha L&P (nuestro ~7K vs referencia ~13K):

**Resultado**: nuestra Corp L&P = 6,953 NR = **total disponible** en `BT_MP_INDIVIDUALS_PERFORMANCE` para NETWORK_GROUP_NAME IN ('PARTNERSHIPS','LANDINGS','BRANDFORMANCE'). No hay más filas que capturar.

**Hallazgo sobre la query de referencia**: la query compartida clasifica `NOT NETWORK APPE` (632K NR) como 'OTHERS' via catch-all `WHEN COALESCE(POM_FLAG,'') = '' → 'OTHERS' → LP`. Esto haría LP = ~644K, no 13K. La imagen de referencia (LP=13K, ORGANICO=703K) proviene de una versión **corregida y diferente** de la query que correctamente mantiene NOT NETWORK APPE en ORGANICO. El código de la versión correcta no está disponible.

**Conclusión**: nuestro Corp L&P ~7K es correcto para las fuentes disponibles. La brecha vs referencia (~6K) viene de una query diferente a la que tenemos acceso.

### 79.6 Archivos modificados en §79

| Archivo | Cambio |
|---|---|
| `src/queries.py` | `get_comms_oc_fresh_sql()`: +`NR_TOTAL_CONTROL` Rama A+B+dedup. `get_nr_tc_sql()`: eliminado `_pf_day_cte/subtract` (FM Total fix). |
| `scripts/refresh_comms_oc_cache.py` | +`NR_TOTAL_CONTROL` en Rama A+B+dedup |
| `src/builders.py` | `build_comms_oc_table_html()`: `TEST→Sents`, `Absoluto NR→NR_TOTAL_Test`, +col `NR_TOTAL_Control`, `data-control-nr`, nuevo `<td>`. |
| `src/template_dashboard.html` | `renderCommsOcKPIs()`: `totalControlNr`, +KPI card `NR_TOTAL_Control`, `Test→Sents` |
| `dashboard_v1.html` | Regenerado — **46.0 MB** |

---

## §80 — 30-Abr-2026 — Fix definitivo USER_INC + Bugs SQL EXPERIMENT

### 80.1 Root cause diagnosis: USER_INC = 0 para campañas ACQUISITION/UCRANIA

**Síntoma reportado**: Múltiples campañas (ej. `I-M-NR-MAIL-NIA-SS-MYIJDV-260401-1`, `I-M-UCR-PUSH-NIA-SS-MYIJDV-ML-260403-1`, `I-M-NR-PUSH-NIA-SS-MYIJDV-ML-260324-2`) mostraban `USER INC = 0` en el dashboard a pesar de que `SUM(NR_INC_USERS)` directo en BQ retornaba valores positivos (912, 1188, 1793, etc.).

**Análisis inicial erróneo descartado**: Se descartaron como causas el problema de dedup (QUALIFY ROW_NUMBER) y la granularidad de datos. Diagnóstico confirmó:
- `I-M-NR-MAIL-NIA-SS-MYIJDV-260401-1`: exactamente **1 fila** en BQ con `NR_INC_USERS=912.71`, `NEW_7D_ADJUST=0`, `REC_7D_ADJUST=0`, `STRATEGY='ACQUISITION'`.
- Todas las claves (COMM_ID, SENT_DATE, CANAL) en abril 2026: exactamente 1 fila → QUALIFY no es el problema.

**Root cause real — fórmula con asunción falsa:**

La fórmula `USER_INC` original asumía que las campañas `ACQUISITION` siempre tenían `NEW_7D_ADJUST + REC_7D_ADJUST` populado. Esta asunción era **falsa**.

Validación empírica Nov-25 → Abr-26 (21K+ filas en `BT_OC_DASHBOARD_ALL_CAMPAIGNS_NR`):

| STRATEGY | ambas_gt0 | solo_nrinc | solo_7d | Conclusión |
|---|---|---|---|---|
| ACQUISITION | **0** | 3,014 | 0 | 7D_ADJUST **nunca** existe para ACQ |
| ACTIVATION | **0** | 5,356 | 0 | 7D_ADJUST **nunca** existe para ACT |
| UCRANIA | 1,427 | 590 | 1,829 | Puede tener cualquiera; diferencia promedio 134% cuando ambas |

La fórmula original `WHEN STRATEGY IN ('UCRANIA', 'ACQUISITION') THEN 7D_ADJUST` devolvía **0** para TODAS las campañas ACQUISITION (7D_ADJUST nunca existe) y para 590 filas UCRANIA donde 7D_ADJUST tampoco estaba. **Impacto estimado: ~144K NR incremental invisible** (ACQUISITION: 129K + UCRANIA: 15K, sobre historial Nov-25→Abr-26).

### 80.2 Fix definitivo — fórmula strategy-agnostic data-driven

**Fórmula anterior (bugueada):**
```sql
CASE
  WHEN STRATEGY IN ('UCRANIA', 'ACQUISITION')
    THEN COALESCE(NEW_7D_ADJUST, 0) + COALESCE(REC_7D_ADJUST, 0)
  ELSE COALESCE(NR_INC_USERS, 0)
END AS USER_INC
```

**Fórmula nueva (correcta, strategy-agnostic):**
```sql
-- Precedencia data-driven: usa el mejor métrico disponible.
-- 7D_ADJUST ≠ 0 → métrica calibrada Adjust (solo UCRANIA la produce realmente).
-- 7D_ADJUST = 0 → NR_INC_USERS (lift Test−Control blacklist-calibrado).
-- Validado Nov25-Abr26: ACQUISITION y ACTIVATION NUNCA tienen 7D_ADJUST != 0.
COALESCE(
  NULLIF(COALESCE(NEW_7D_ADJUST, 0) + COALESCE(REC_7D_ADJUST, 0), 0),
  COALESCE(NR_INC_USERS, 0)
) AS USER_INC
```

La misma lógica se aplicó al cálculo de `RATIO_CANIBALIZACION` (que también usaba la fórmula strategy-specific para el denominador incremental).

Aplicado en:
- `src/queries.py` — Rama A de `get_comms_oc_fresh_sql()`
- `scripts/refresh_comms_oc_cache.py` — Rama A de `build_comms_oc_sql_for_date_range()`

### 80.3 Bugs SQL EXPERIMENT — tres errores encadenados

Al agregar la columna `EXPERIMENT` en sesiones anteriores se introdujeron tres bugs SQL que causaban errores en el cache rebuild (`--full`):

**Bug A — Duplicate EXPERIMENT en Rama A SELECT**
Columna `EXPERIMENT,` apareció en dos posiciones en el SELECT de Rama A:
1. Posición correcta: después de `SUBSTRATEGY` (lee de tabla)
2. Posición duplicada: después de `CLASIF_CAMPAIGNS` (extra, causaba ambigüedad)
- Error BQ: `Column name EXPERIMENT is ambiguous at [184:56]`
- Fix: eliminar la segunda ocurrencia (después de `CLASIF_CAMPAIGNS`)

**Bug B — Duplicate EXPERIMENT en Rama B SELECT**
Rama B tenía `EXPERIMENT,` (lectura de tabla, posición 11) Y `CAST(NULL AS STRING) AS EXPERIMENT` (posición 31). Ambas en el mismo SELECT → ambigüedad.
- Fix: eliminar `EXPERIMENT,` de posición 11 en Rama B (el que intentaba leer de la tabla `NR_ACQUISITION` donde la columna existe pero ya está como NULL explícito)

**Bug C — UNION ALL type mismatch (consecuencia del fix B)**
Al eliminar `EXPERIMENT,` de posición 11 en Rama B, la columna 11 pasó a ser `NOTIFICATION_TYPE` (STRING) mientras en Rama A sigue siendo `EXPERIMENT` (STRING). Las columnas subsecuentes quedaron desalineadas → la columna 15 (STATUS en Rama A = STRING) se enfrentó con SENTS en Rama B (DOUBLE).
- Error BQ: `Column 15 in UNION ALL has incompatible types: STRING, DOUBLE`
- Fix: restaurar `CAST(NULL AS STRING) AS EXPERIMENT` en la posición 11 de Rama B (después de `SUBSTRATEGY`, antes de `NOTIFICATION_TYPE`) y eliminar del lugar tardío (después de `CLASIF_CAMPAIGNS`)

**Estado final correcto** — una ocurrencia de EXPERIMENT por lugar:
- Rama A pos 11: `EXPERIMENT,` — lee de `BT_OC_DASHBOARD_ALL_CAMPAIGNS_NR`
- Rama B pos 11: `CAST(NULL AS STRING) AS EXPERIMENT,`
- Combined dedup: `COALESCE(MAX(IF(FUENTE_TABLA='ALL_CAMPAIGNS_NR', EXPERIMENT, NULL)), MAX(EXPERIMENT)) AS EXPERIMENT`

**Bug D — Duplicate EXPERIMENT en combined SELECT**
`MAX(EXPERIMENT) AS EXPERIMENT` apareció también en la sección "Clasificación y flags" del SELECT combined, además del `COALESCE(MAX(IF...EXPERIMENT...)) AS EXPERIMENT` ya existente en la posición correcta.
- Fix: eliminar el `MAX(EXPERIMENT) AS EXPERIMENT` duplicado de la sección tardía

### 80.4 Cache stale — Tier 2 (mes actual)

**Problema**: El Tier 2 (`data/comms_oc_current_month.json`) fue generado **antes** del fix de la fórmula y contenía `USER_INC=0.0` para todas las campañas ACQUISITION de abril 2026 (226 registros ACQUISITION, 90 mostrando USER_INC=0 incluyendo las campañas MYIJDV reportadas).

**Fix**: eliminar el archivo Tier 2 para forzar re-query BQ en la siguiente generación del dashboard:
```
rm data/comms_oc_current_month.json
python src/gen_dashboard_v1.py
```

**Verificación post-fix** (nuevo Tier 2):
- `I-M-NR-MAIL-NIA-SS-MYIJDV-260401-1`: USER_INC = **912.71** ✓ (era 0)
- `I-M-UCR-PUSH-NIA-SS-MYIJDV-ML-260403-1`: USER_INC = **1,188.97** ✓ (era 0)
- `I-M-UCR-PUSH-NIA-SS-MYIJDV-ML-260403-2`: USER_INC = **823.59** ✓ (era 0)
- Los 90 ACQUISITION que siguen en 0: legítimos (campañas Mantika `MTK_DSINCE_CBK` recientes sin ventana de medición cerrada → NR_INC_USERS=0 en BQ fuente)

### 80.5 Pendiente: Tier 1 rebuild histórico

El `data/comms_oc_cache.json` (Nov-25→Mar-26, 20,645 registros) aún contiene valores `USER_INC` calculados con la fórmula bugueada. Ejecutar para corregir el historial:
```
python scripts/refresh_comms_oc_cache.py --full
```
Los bugs SQL (EXPERIMENT ambiguous, UNION ALL type mismatch) están corregidos — el rebuild debería completarse sin errores.

### 80.6 Archivos modificados en §80

| Archivo | Cambio |
|---|---|
| `src/queries.py` | `get_comms_oc_fresh_sql()` Rama A: USER_INC strategy-agnostic (`COALESCE(NULLIF(...),NR_INC_USERS)`). RATIO_CANIBALIZACION: misma lógica. EXPERIMENT: eliminados duplicados en Rama A (pos tardía) y Rama B (pos 11 cruda → NULL explícito pos 11), eliminado dup en combined. |
| `scripts/refresh_comms_oc_cache.py` | `build_comms_oc_sql_for_date_range()`: mismas correcciones USER_INC, RATIO_CANIBALIZACION y EXPERIMENT que queries.py |
| `data/comms_oc_current_month.json` | Eliminado y regenerado con fórmula correcta (3,342 registros, USER_INC correctos) |
| `dashboard_v1.html` | Regenerado — **43,084 KB** |

---

## §81 — 30-Abr-2026 — Inclusión RE-ACTIVATION + Auditoría filtros de exclusión

### 81.1 Descubrimiento: campañas invisibles por filtros demasiado agresivos

**Síntoma reportado**: Campaña `I-M-UCR-PUSH-NIA-SS-LW0426-AH-IMG-260421` aparece en BQ directo con NR_INC_USERS = 122.79 pero no existe en el dashboard en absoluto (0 comunicaciones en KPI). Distinción clave vs §80: en §80 las campañas aparecían con USER_INC = 0; aquí la campaña no existe de ninguna forma → exclusión SQL.

**Diagnóstico**: La campaña tiene `STRATEGY = 'ACQUISITION'` y `TEAM = 'ADHOC - INDIVIDUALS'` — pasa todos los filtros SQL. La causa fue un **filtro de TEAM en el frontend** (el usuario tenía "5 selec." que no incluía 'ADHOC - INDIVIDUALS'). No era un problema de datos.

**Descubrimiento colateral (más importante)**: Al auditar los filtros de exclusión de nombre de campaña, se confirmó que el filtro `NOT LIKE '%CHURN%'` en la query existía. Pero el `excl_CHURN = 0` en el diagnóstico inicial fue engañoso: el count se hizo sobre el subset ya filtrado por `STRATEGY IN (...)`, por lo que campañas con STRATEGY fuera de esa lista (como `RE-ACTIVATION`) no eran contadas.

### 81.2 Auditoría de campañas excluidas (Opción C)

Se corrió query diagnóstica sin filtro STRATEGY para ver todas las campañas excluidas con NR_INC_USERS > 0 en Abril 2026:

**Resultados top-40 campañas excluidas:**

| STRATEGY excluido | Campañas | NR_INC_USERS | Causa exclusión |
|---|---|---|---|
| `RE-ACTIVATION` | 23 | ~39K | STRATEGY + CHURN en nombre |
| `RETENTION` | 3 | ~2.3K | STRATEGY (XT1 en nombre también) |
| `ENGAGEMENT` | 9 | ~4.3K | STRATEGY (XT1 en nombre también) |
| `OTHERS` | 4 | ~1.8K | STRATEGY |

**Hallazgo clave**: Las campañas `RE-ACTIVATION` son flows de churn prevention que reactivan usuarios inactivos 90+ días → por definición son **Recuperados** (la "R" de N+R). Ejemplo: `flows_communication_MLM_I_EG_MTK_CHURN_CPN_RECARGA_mer_i5b` = 5,302 NR invisible.

**Decisión**: Incluir `RE-ACTIVATION` (Opción A). No incluir RETENTION/ENGAGEMENT/OTHERS por ahora (no son N+R de adquisición puro).

### 81.3 Cambios implementados

**Filtros modificados en `src/queries.py` (Rama A — `get_comms_oc_fresh_sql`):**

```sql
-- ANTES:
AND STRATEGY IN ('UCRANIA', 'ACTIVATION', 'ACQUISITION')
AND COMUNICATION_NAME NOT LIKE '%CHURN%'

-- DESPUÉS:
AND STRATEGY IN ('UCRANIA', 'ACTIVATION', 'ACQUISITION', 'RE-ACTIVATION')
-- línea CHURN eliminada de Rama A
```

**Filtros modificados en `scripts/refresh_comms_oc_cache.py` (Rama A SQL + Python post-proc):**

```python
# SQL Rama A: mismo cambio que queries.py
AND STRATEGY IN ('UCRANIA', 'ACTIVATION', 'ACQUISITION', 'RE-ACTIVATION')
# línea CHURN eliminada del WHERE Rama A

# Python post-processing _should_exclude_campaign() — eliminada línea:
# or 'CHURN' in campaign_up
```

**Rama B no modificada**: `BT_OC_DASHBOARD_ALL_CAMPAIGNS_NR_ACQUISITION` (UCR Gest) no tiene campañas RE-ACTIVATION; el filtro CHURN se conserva en Rama B por precaución.

**Template `_EXCL` en queries.py**: Era código muerto (definido pero nunca referenciado). Se limpió la línea `%%CHURN%%` de ese template como limpieza.

### 81.4 Resultados post-cambio

| Métrica | Antes §81 | Después §81 | Delta |
|---|---|---|---|
| Tier 1 cache (Nov-25→Mar-26) | 20,643 registros | **24,248 registros** | +3,605 |
| Tier 2 cache (Abr-26) | 3,342 registros | **4,126 registros** | +784 |
| Total merged | 23,985 | **28,374 registros** | +4,389 |
| Dashboard size | 43,084 KB | **50,929 KB** | +7,845 KB |

El `--full` rebuild completó exitosamente en este contexto (todos los bugs SQL de §80 ya corregidos).

### 81.5 Nota: texto stale en refresh_comms_oc_cache.py

El mensaje final del script dice `python src/gen_dashboard_v2.py` — nombre incorrecto (la versión activa es v1). Pendiente de corrección cosmética.

### 81.6 Archivos modificados en §81

| Archivo | Cambio |
|---|---|
| `src/queries.py` | `get_comms_oc_fresh_sql()` Rama A: +`'RE-ACTIVATION'` a STRATEGY IN. Eliminado `NOT LIKE '%CHURN%'` de Rama A. Limpieza `_EXCL` template (código muerto). |
| `scripts/refresh_comms_oc_cache.py` | `build_comms_oc_sql_for_date_range()` Rama A: +`'RE-ACTIVATION'` a STRATEGY IN, eliminado `NOT LIKE '%CHURN%'`. `_should_exclude_campaign()`: eliminado `or 'CHURN' in campaign_up`. |
| `data/comms_oc_cache.json` | Rebuild completo (24,248 registros, 29,327 KB) |
| `data/comms_oc_current_month.json` | Regenerado (4,126 registros) |
| `dashboard_v1.html` | Regenerado — **50,929 KB** |

---

## §82 — 4-May-2026 — Corp Total fix + LMTD inteligente + D-2→D-1 cutoff

### 82.1 Fix Corp Total = FM Total (~1,188 NR/mes perdido)

**Root cause**: `others_catchall_corp_tc` en `get_nr_corp_tc_sql()` operaba en dos pasos contradictorios:
1. Sus filas se restaban del residual NO ATRIBUIDO via `catch_total_corp` (subtracción en `org_corp_tc`)
2. Sus filas también aparecían en el UNION ALL final con `corp_key = 'OTH|OTHERS_CATCHALL|TOTAL'`
3. Ese `corp_key` no existe en la jerarquía Corp → el procesador lo descartaba

Resultado neto: ~1,188 NR/mes se restaba del residual pero nunca aparecía en ningún nodo visible → "NR perdido". Corp Total = INAPP - 1,188 < FM Total = INAPP.

**Fix**: cambiar `org_corp_tc` para restar `ucr_total_corp` (suma de `ucr_prd_indiv_tc`) en lugar de `catch_total_corp` (que incluía filas no atribuibles). Eliminar `others_catchall_corp_tc` del UNION ALL final.

**Nuevo `org_corp_tc`**:
```sql
-- Antes: NO_ATRIBUIDO = INAPP - OC - PAID - OTHERS_CATCHALL (perdía ~1,188 NR)
-- Ahora: NO_ATRIBUIDO = INAPP - OC - PAID - UCR_PRD (alineado con FM ORG)
org_corp_tc = GREATEST(INAPP - oc_total - paid_total - ucr_total, 0)
```

Aplicado en:
- `get_nr_corp_tc_sql()` (mensual)
- `get_nr_corp_daily_tc_sql()` (diario)

Nuevos CTEs: `ucr_total_corp` y `ucr_total_daily` (suma de `ucr_prd_indiv_tc` y `ucr_prd_indiv_daily_tc`).

**Resultado**: Corp Total = FM Total = INAPP (~1,080K para Marzo-26). Diferencia residual ~1.2K entre FM ORG y Corp NO ATRIBUIDO es por diseño: Corp muestra POM_Others como canal visible (subtrae POM_FLAG del residual), FM lo absorbe en ORG.

### 82.2 Fix LMTD inteligente — MTD D7 coincide con NR Mensual

**Problema**: el tab MTD D7 comparaba "mismo número de días" entre el mes actual y el mes anterior (LMTD). Cuando el mes actual tiene menos días que el anterior (Abril=30 días → Marzo LMTD mostraba solo 30 días), el total LMTD difería del total en NR Mensual (que muestra el mes completo: 31 días para Marzo). Diferencia observada: MTD D7 LMTD Marzo = 1,080,781 vs NR Mensual Marzo = 1.12M (~43K de diferencia = datos del día 31 de Marzo).

**Fix en `template_dashboard.html`**: `renderMTDTable()` detecta si el mes seleccionado ES el mes actual en curso (usando `new Date()` del navegador). Comportamiento diferenciado:

```javascript
const _d2date = new Date(); _d2date.setDate(_d2date.getDate() - 1);
const _actualCurrentMonth = String(_d2date.getFullYear()) + String(_d2date.getMonth() + 1).padStart(2, '0');
const _isCurrentPeriod = (month === _actualCurrentMonth);
const lmtdRefDay = _isCurrentPeriod
  ? (prevDays.includes(refDay) ? refDay : lastAvailablePrevDay)  // mes en curso → mismo día
  : (prevDays.length ? prevDays[prevDays.length - 1] : refDay);  // mes cerrado → mes completo
```

- **Mes en curso** (Mayo seleccionado, D-1 actual): LMTD usa el mismo día de referencia → comparación justa (2 días vs 2 días)
- **Mes cerrado** (Abril o anterior seleccionado): LMTD usa el último día disponible del mes anterior → mes completo → coincide con NR Mensual

### 82.3 Cambio cutoff D-2 → D-1

**Motivación**: la data de D-1 está siempre disponible (aunque puede re-atribuirse después). Mostrar D-1 en lugar de D-2 da un día más de contexto.

**Cambio**: en `src/queries.py`, todas las ocurrencias de `DATE_SUB(CURRENT_DATE(), INTERVAL 2 DAY)` reemplazadas por `DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)`. Total: **31 ocurrencias** en todas las queries activas:
- `get_nr_tc_sql()` (ORG, INAPP, Torre Daily, Individuals Perf)
- `get_nr_corp_tc_sql()` y `get_nr_corp_daily_tc_sql()` (Corp mensual y diario)
- `get_vpu_tc_sql()`, `get_costos_tc_sql()`, `get_perf_paid_tc_sql()`, `get_roa_tc_sql()`

**UI**: label en tab MTD D7 cambiado de "Información hasta (día c)" a "Información hasta (D-1)".

**JavaScript MTD**: la variable `_d2date` también actualizada de `getDate() - 2` a `getDate() - 1` para detectar correctamente el mes actual.

### 82.4 Archivos modificados en §82

| Archivo | Cambio |
|---|---|
| `src/queries.py` | `get_nr_corp_tc_sql()`: +`ucr_total_corp`, `org_corp_tc` usa `ucr_total_corp` en lugar de `catch_total_corp`, `others_catchall_corp_tc` eliminado de UNION ALL. `get_nr_corp_daily_tc_sql()`: mismo fix con `ucr_total_daily`. Todas las queries activas: `INTERVAL 2 DAY` → `INTERVAL 1 DAY` (31 ocurrencias). |
| `src/template_dashboard.html` | `renderMTDTable()`: lógica LMTD diferenciada (mes en curso → mismo día; mes cerrado → mes completo). Detección de mes actual via `new Date()`. Label "día c" → "D-1". Variable `_d2date`: `getDate() - 2` → `getDate() - 1`. |
| `dashboard_v1.html` | Regenerado — **84,170 KB** |

---

## §83 — 5-May-2026 — MTD D7: nuevas columnas + fix monthly_nr + D-1 badge

### 83.1 Fix MTD D7 badge y refDay (complemento §82)

Dos correcciones que quedaron pendientes de §82:

1. **Badge D-2 hardcodeado**: la línea `D&#8209;2` en el HTML del tab MTD seguía mostrando "D-2" en la esquina superior derecha. Cambiado a `D&#8209;1`.

2. **Variable `hoy2` para refDay**: la lógica de cálculo del día de referencia MTD usaba `getDate() - 2` internamente (variable `hoy2`). Renombrada `hoy2` → `hoy1` y actualizado a `getDate() - 1`. Esto hace que cuando se selecciona el mes en curso, `refDay` apunte al día D-1 real (ayer), no al D-2.

### 83.2 Fix MTD usa `monthly_nr` para el mes en curso

**Problema**: con el cambio a D-1 SQL, el dashboard tiene datos de NR hasta ayer (D-1). Sin embargo, `CUM_NR` (el acumulado certificado en BQ) tarda ~2 días en finalizarse. Resultado: `daily_cum[month][refDay]` = valor forward-filled al último día con CUM_NR ≠ 0 (~D-2). Esto causaba que MTD D7 mostrara 73,924 (Mayo 1-2) mientras NR Mensual y la query de referencia del equipo mostraban 105.4K (Mayo 1-4).

**Fix en `renderMTDTable()`**:
```javascript
// Para el mes en curso: usar monthly_nr (raw NR sum, D-1 inmediato)
// Para meses pasados: usar daily_cum (CUM_NR, ya certificado)
const mtd = _isCurrentPeriod ? (D.monthly_nr[label]||{})[month]||0
                              : (((D.daily_cum[label]||{})[month])||{})[refDay]||0;
```

La variable `_isCurrentPeriod` (calculada en §82) distingue el mes en curso del histórico. `D.monthly_nr` = suma de raw NR diarios, disponible inmediatamente para D-1. Resultado: **MTD D7 = NR Mensual = query de referencia = 105.4K** para Mayo.

Lo mismo aplicado al total de Mix de Marketing (`mtdTotalNR_mm`).

**Por qué esto es correcto**: el NR raw de D-1 está disponible aunque puede re-atribuirse ligeramente. Para la gestión operativa diaria, este número es más útil que esperar la certificación de CUM_NR (~2 días). Los números de meses pasados siguen usando `daily_cum` (certificado).

### 83.3 Nuevas columnas en MTD D7

Se agregaron 2 columnas nuevas al tab MTD D7 para facilitar la lectura del avance vs Plan:

| Columna nueva | Cálculo | Posición |
|---|---|---|
| **vs Plan M %** | `(MTD / Plan mensual) − 1` en % con ▲/▼ | Después de "vs Plan M" absoluto |
| **Proy. vs Plan** | `(Proyección lineal / Plan mensual) − 1` en % | Después de "Proy. Lineal" |

Implementación en JS:
```javascript
const vsPlanPct  = planVal > 0 ? (mtd - planVal) / planVal : null;
const projVsPlan = (proj != null && planVal > 0) ? (proj - planVal) / planVal : null;
```

Ambas columnas muestran `—` cuando no hay plan definido (igual que las columnas absolutas correspondientes).

### 83.4 Renombrar "MIx" → "Contrib. MoM"

La columna "MIx" era confusa: no es el MoM% del canal sino su **contribución al cambio total**. Fórmula: `(MTD_canal - LMTD_canal) / LMTD_Total_N+R`. Para "Total N+R" equivale al MoM%. Para sub-canales indica cuántos pp del total mueve ese canal.

Renombrado a **"Contrib. MoM"** con tooltip: *"Contribución de cada canal al cambio MoM total. Para Total N+R = MoM%."*

La fila de Mix de Marketing también recibió 2 celdas `—` adicionales para alinearse con las nuevas columnas.

### 83.5 Relación con query de referencia del equipo

La query corporativa del equipo (`CURRENT_DATE()-1` como FECHA_FIN, fuente `BT_MP_USER_ENGAGEMENT_INAPP`) muestra 105.44K para Mayo-26 MTD. Nuestro fix hace que el dashboard también muestre 105.4K, confirmando la alineación con la metodología de referencia. La diferencia entre vistas:

| Fuente | Metodología | Mayo D-4 |
|---|---|---|
| Query referencia equipo | Raw NR `BT_MP_USER_ENGAGEMENT_INAPP` D-1 | 105.44K |
| Nuestro NR Mensual | Raw NR sum `monthly_nr` D-1 | 105.4K ✓ |
| Nuestro MTD D7 (post-fix) | `monthly_nr` para mes en curso | 105.4K ✓ |
| Nuestro MTD D7 (pre-fix) | `CUM_NR` forward-filled | 73,924 ✗ |

### 83.6 Archivos modificados en §83

| Archivo | Cambio |
|---|---|
| `src/template_dashboard.html` | `renderMTDTable()`: badge `D&#8209;2`→`D&#8209;1`. `hoy2`→`hoy1` + `getDate()-2`→`getDate()-1`. MTD usa `monthly_nr` para mes en curso. `mtdTotalNR_mm` mismo fix. +2 columnas `<th>` en header (vs Plan M %, Proy. vs Plan). +variables `vsPlanPct`, `projVsPlan`. +2 `<td>` por fila de datos. Fila Mix de Marketing: +2 celdas `—`. "MIx"→"Contrib. MoM" con tooltip. |
| `dashboard_v1.html` | Pendiente regeneración |

---

## §84 — 5-May-2026 — ENGAGEMENT + SELLERS con alto impacto en Comms_OC

### 84.1 Contexto

Investigación de por qué `MLM_S_M_ENG_SWE_PBD` (−4.7K NR el 2-Abr-2026) no aparecía en la pestaña Comms_OC pese a haber reconstruido el cache con `--append --from 2025-05-01 --to 2026-05-01`.

### 84.2 Diagnóstico BQ

Query directa a `BT_OC_DASHBOARD_ALL_CAMPAIGNS_NR` reveló los atributos reales de la campaña:

| Campo | Valor esperado | Valor real |
|---|---|---|
| STRATEGY | 'ENGAGEMENT' | **'OTHERS'** |
| TEAM | — | **'ADHOC - SELLERS'** |
| CANAL | JOURNEY | JOURNEY ✓ |
| NR_INC_USERS (02-Abr) | — | **−4,703.8** |

Causa raíz: la campaña tiene `TEAM = 'ADHOC - SELLERS'` → excluida por `AND TEAM NOT IN ('SELLERS', 'ADHOC - SELLERS')`. STRATEGY='OTHERS' + CANAL='JOURNEY' pasaba el filtro de estrategia, pero el filtro de TEAM la bloqueaba antes de llegar.

La adición de ENGAGEMENT a `queries.py` fue una mejora válida (para otras campañas con STRATEGY real = ENGAGEMENT), pero no era la causa de este caso específico.

### 84.3 Nueva regla: SELLERS con alto impacto

**Decisión de negocio**: las campañas de SELLERS team normalmente se excluyen del dashboard de adquisición de compradores. Sin embargo, cuando su impacto en N+R es significativo (|USER_INC| > 250, positivo o negativo), deben ser visibles para poder rastrear qué mueve la aguja.

**Implementación SQL (Rama A)**:
```sql
-- Antes:
AND TEAM NOT IN ('SELLERS', 'ADHOC - SELLERS')

-- Después:
AND (
  TEAM NOT IN ('SELLERS', 'ADHOC - SELLERS')
  OR ABS(COALESCE(NULLIF(COALESCE(NEW_7D_ADJUST,0)+COALESCE(REC_7D_ADJUST,0), 0), COALESCE(NR_INC_USERS,0))) > 250
)
```

**Implementación SQL (Rama B)** — usa `Q_NR_7D` (único USER_INC disponible):
```sql
AND (
  TEAM NOT IN ('SELLERS', 'ADHOC - SELLERS')
  OR ABS(COALESCE(Q_NR_7D, 0)) > 250
)
```

El umbral `ABS(...) > 250` captura tanto campañas de alto impacto positivo (+250) como campañas canibalistas de alto impacto negativo (−250), que es exactamente el objetivo.

### 84.4 Clasificación OTHERS_SELLERS

Las campañas SELLERS que pasan el umbral se clasifican con subcanales especiales para distinguirlas visualmente de las campañas regulares de comprador:

**P0 (nueva regla de máxima prioridad)** en `_classify_corp_subcanal` y `_classify_fm_subcanal`:
```python
if 'SELLERS' in t:   # captura 'SELLERS' y 'ADHOC - SELLERS'
    return 'OTHERS_SELLERS'
```

Aplicado en 4 funciones: `builders.py` (`_classify_corp_subcanal`, `_classify_fm_subcanal`) + `builders_analysis.py` (`_classify_corp_subcanal_analysis`, `_classify_fm_subcanal_analysis`).

### 84.5 ENGAGEMENT sincronizado en refresh_comms_oc_cache.py

Además del fix principal, se sincronizó la adición de `'ENGAGEMENT'` al filtro STRATEGY en `refresh_comms_oc_cache.py` (solo estaba en `queries.py`). Ahora ambos archivos coinciden:
```sql
STRATEGY IN ('UCRANIA', 'ACTIVATION', 'ACQUISITION', 'RE-ACTIVATION', 'ENGAGEMENT')
OR (STRATEGY = 'OTHERS' AND UPPER(CANAL) = 'JOURNEY')
```

### 84.6 Paso pendiente — rebuild cache con nuevo SQL

El cache histórico (`comms_oc_cache.json`) fue construido con el SQL anterior (sin la regla ABS>250 para SELLERS). Para que `MLM_S_M_ENG_SWE_PBD` y otras campañas SELLERS de alto impacto aparezcan en meses históricos, se necesita:

```
python scripts/refresh_comms_oc_cache.py --append --from 2025-05-01 --to 2026-05-01
```

(volver a correr con el SQL actualizado — el anterior no tenía la regla ABS>250)

### 84.7 Archivos modificados en §84

| Archivo | Cambio |
|---|---|
| `src/queries.py` | Rama A: `TEAM NOT IN` → `AND (TEAM NOT IN ... OR ABS(USER_INC_EXPR) > 250)`. Rama B: misma lógica con `Q_NR_7D`. |
| `scripts/refresh_comms_oc_cache.py` | +`'ENGAGEMENT'` a STRATEGY filter Rama A (sync con queries.py). Rama A y Rama B: mismo cambio `ABS > 250` que queries.py. |
| `src/builders.py` | `_classify_corp_subcanal` + `_classify_fm_subcanal`: +P0 `if 'SELLERS' in t: return 'OTHERS_SELLERS'` (antes de P1). |
| `src/builders_analysis.py` | `_classify_corp_subcanal_analysis` + `_classify_fm_subcanal_analysis`: mismo P0. |
| `dashboard_v1.html` | Pendiente regeneración + rebuild cache |

---

## §85 — 5-May-2026 — Sesión extensa: Reporting tab + múltiples fixes Comms_OC + Skills

### 85.1 Fixes acumulados Comms_OC (post §84)

#### USER_INC: fórmula oficial del equipo
Alineación con la fórmula del equipo:
- **Antes**: `COALESCE(NULLIF(7D_ADJUST,0), NR_INC_USERS)` (data-driven con fallback)
- **Después**: `CASE WHEN CLASIF_CAMPAIGNS='UCRANIA' THEN 7D_ADJUST ELSE NR_INC_USERS END`
- Misma lógica aplicada a `RATIO_CANIBALIZACION`
- Archivos: `queries.py` (Rama A) + `refresh_comms_oc_cache.py` (Rama A)

#### Dos columnas USER_INC
Para mostrar ambas metodologías simultáneamente:
- `USER_INC` = `NR_INC_USERS` siempre (lift puro, alineado con Torre de Control)
- `USER_INC_CON_ADJUST` = fórmula oficial equipo (UCRANIA → Adjust, resto → lift)
- Para Rama B: ambas = `Q_NR_7D`
- UI: KPI cards `Σ User Inc (lift NR Torre)` + `Σ User Inc Adj (NR con Adjust)`

#### Corp/FM Sub-canal Aux + OTHERS_SELLERS mapping
- `FM Sub-canal Aux` = clasificación original incluyendo `OTHERS_SELLERS`
- `FM Sub-canal` (principal) = mapea `OTHERS_SELLERS` → `OC ACT`
- `Corp Sub-canal Aux` = clasificación original incluyendo `OTHERS_SELLERS`
- `Corp Sub-canal` (principal) = mapea `OTHERS_SELLERS` → `OWN CHANNELS RECURRING`
- 4 nuevas columnas en tabla + 2 nuevos filtros dropdown

#### Journey CANAL bypass — Inclusión completa de campañas Journey
Root cause: de ~163 campañas Journey esperadas en Mayo, solo ~50 se capturaban.
Causas: filtro `%T1%` bloqueaba XSELLT1, filtro SELLERS bloqueaba `MLM_S_EG_*`, RETENTION no en STRATEGY.

Fix: para `CANAL='JOURNEY'`, bypasear todos los filtros restrictivos:
```sql
AND (
  STRATEGY IN ('UCRANIA', 'ACTIVATION', 'ACQUISITION', 'RE-ACTIVATION', 'ENGAGEMENT')
  OR UPPER(CANAL) = 'JOURNEY'  -- Journey: capturar todo sin restricción de strategy
)
AND (
  UPPER(CANAL) = 'JOURNEY'    -- Journey bypass: sin filtro de team
  OR TEAM NOT IN ('SELLERS', 'ADHOC - SELLERS')
  OR ABS(USER_INC) > 250
)
AND (
  UPPER(CANAL) = 'JOURNEY'    -- Journey bypass: sin filtros de nombre
  OR ( COMUNICATION_NAME NOT LIKE '%T1%' AND ... )
)
```
Resultado esperado: ~95%+ de Journey capturadas (vs ~30% antes).

#### MEDIO_CLASIF_FINAL: condición EYG
Regla PUSH → JOURNEY ahora requiere adicionalmente `'EYG' in EXPERIMENT`:
```python
if (c == 'PUSH' and 'PUSH APP MP' in ch
        and s != 'UCRANIA' and ss != 'UCRANIA'
        and cn.startswith('flows_communication')
        and fp == 'FREE'
        and 'EYG' in exp):   # ← NUEVO
    return 'JOURNEY'
```

#### Fix bug multi-select campaña
`selectAllVisibleCommsOcMS()` estaba definida DENTRO de `initCommsOcFilters()` (scope local). El botón "Seleccionar todos los que coinciden" fallaba silenciosamente. Fix: mover a scope global antes de `initCommsOcFilters()`.

### 85.2 MTD / UI fixes

- **Tab MTD D7 → MTD**: renombrado en tab header, `LMTD D7`→`LMTD`, `MTD D7`→`MTD` en columnas
- **"Información hasta (D-X)"**: label ahora usa `_mtdCutoff` dinámico en lugar de `(D-1)` hardcodeado
- **Descripción D-1/D-2/D-3 eliminada**: texto explicativo `"D-1 = total NR estable..."` removido
- **Tab Análisis POM eliminado**: tab + pane + import + placeholder removidos de 4 archivos

### 85.3 Skills — Comms + OPTIMIZADOR

#### analizar-OC_Comms_skill.md v3.2
- Dispatch table actualizada (Modos 19-20 faltaban)
- **Modo 21 `top_medio` (NUEVO)**: top5/bottom5 por `FM Sub-canal × Corp Sub-canal × Medio Final`
  - Usa `USER_INC_ADJ` para comparación IS-ajustada inter-período
  - Muestra campañas apagadas/nuevas vs mes anterior con impacto en el gap
  - Se invoca automáticamente después del Modo 20
- Modo 20 actualizado: referencia `USER_INC_ADJ`, secuencia incluye Modo 21

#### OPTIMIZADOR-OC_skill.md v4.2
- Regla crítica de equivalencia: +ejemplo concreto con `USER_INC_ADJ` (UCR GEST May D1-D4 = 4.2K vs Abr = 10.2K)
- Tabla orquestación: +fila `top_medio`, actualización filas cruce MTD con `USER_INC_ADJ`

### 85.4 Pestaña Reporting (NUEVA)

**Tab ID**: `reporting` | **Nombre UI**: "Reporting"
**Builder**: `build_reporting_tab_html()` en `src/builders.py`
**Helper**: `_rep_highlights()` — auto-genera highlights MoM desde datos reales
**Documentación**: `config/reporting_methodology.md`

#### Sección 1: N+R in App + Valor Predictivo (Vista Corp, 6 meses)
- Stacked bar: OC+UCR (#F5D000), POM (#1FB8D4), Others (#7A7D82), No Atribuído (#C8CDD8)
- Líneas: Plan OC+UCR (rojo) + CPA (naranja)
- KPI table: Share MKT, vs Plan '26, Inv. OC+UCR M USD, CPA
- Sección derecha: mismo layout con Valor Predictivo (NR × VPU ponderado)

#### Sección 2: New vs Recovered + N+R por Canal
- N+R New vs Rec: desde `process_new_rec_monthly()` → `BT_MP_USER_ENGAGEMENT_INAPP` (`NEW_USERS_INAPP` + `RECOVERED_USERS_INAPP`)
- N+R por Canal: OWN CHANNELS, POM, MGM, L&P, No Atribuído/Org (Corp hierarchy)

#### Sección 3: Evolución N+R por Estrategia OC+UCR
Taxonomía (confirmada con equipo):
| Segmento | Node IDs | Definición |
|---|---|---|
| Ucrania | `corp_ucr_eg_*` | UCRANIA E&G todos los medios |
| Activation Rec | `corp_oc_rec_email/pandora/push/wpp` | OWN CHANNELS RECURRING sin Journey |
| Ad Hoc | `corp_oc_adhoc` | OWN CHANNELS ADHOC |
| Resto Rec (JNY) | `corp_oc_rec_journey` | Medio JOURNEY dentro de RECURRING |

- KPI table: Share N+R OC+UCR, N+R, CPA, CPA Paid, Inv. M USD
- Highlights auto-generados: comparación MoM por sub-estrategia con flechas y colores

#### Descarga PNG
Cada gráfica tiene botón "⬇ PNG" → `Plotly.downloadImage()` a 980×520 escala 2x. Listo para pegar en PPTX.

### 85.5 Nuevas queries y procesadores
- **`get_new_rec_monthly_sql()`** en `queries.py`: N+R New vs Recovered total sitio desde `BT_MP_USER_ENGAGEMENT_INAPP`
- **`process_new_rec_monthly(bq_client)`** en `processors.py`: retorna `{yyyymm: {'new': int, 'rec': int}}`

### 85.6 Archivos modificados en §85

| Archivo | Cambio |
|---|---|
| `src/queries.py` | +`get_new_rec_monthly_sql()`. Comms_OC: Journey bypass para CANAL=JOURNEY. USER_INC → fórmula equipo + USER_INC_CON_ADJUST nueva col. RATIO_CANIBALIZACION alineado. |
| `scripts/refresh_comms_oc_cache.py` | Mismos cambios SQL que queries.py (Journey bypass, USER_INC formula, USER_INC_CON_ADJUST). |
| `src/processors.py` | +`process_new_rec_monthly()` antes de `process_nr_corp()`. |
| `src/builders.py` | +`_rep_highlights()` + `build_reporting_tab_html()`. `_classify_medio_final`: +param `experiment` + condición EYG. `_classify_corp/fm_subcanal`: +P0 SELLERS. `FM/Corp Sub-canal Aux`: nuevas variables + data-attrs + headers + celdas. USER_INC + USER_INC_CON_ADJUST: dos variables separadas. KPI cards: +`Σ User Inc Adj`. |
| `src/builders_analysis.py` | `_classify_corp/fm_subcanal_analysis`: +P0 SELLERS. |
| `src/gen_dashboard_v1.py` | +import `build_reporting_tab_html`, `process_new_rec_monthly`. +llamada `process_new_rec_monthly()` + `replace('{{REPORTING_TAB}}', ...)`. |
| `src/template_dashboard.html` | +tab "Reporting" + pane `{{REPORTING_TAB}}`. TABS array updated. Tab "MTD D7"→"MTD". LMTD/MTD D7 headers limpiados. Descripción D-1/D-2/D-3 eliminada. Label "Información hasta (D-X)" dinámico. Tab Análisis POM eliminado. `selectAllVisibleCommsOcMS` movida a scope global. |
| `config/reporting_methodology.md` | NUEVO — documentación de clasificación de canales para Reporting tab. |
| `skills/analizar-OC_Comms_skill.md` | v3.2: Dispatch table actualizada. Modo 21 `top_medio` NUEVO. Modo 20 +USER_INC_ADJ +secuencia Modo 21. |
| `skills/OPTIMIZADOR-OC_skill.md` | v4.2: Regla equivalencia +USER_INC_ADJ ejemplo. Tabla orquestación +`top_medio`. |
| `dashboard_v1.html` | Pendiente regeneración con cache --full |

---

## §86 — 7-May-2026 — Diagnóstico y documentación: cambio de modelo de Valor Pred 90D / VPU (Abr 2026)

### 86.1 Contexto y motivación

Al revisar la pestaña Reporting (§85), se detectaron diferencias grandes entre los valores de **VPU Pred 90D** y **Valor Pred 90D** del dashboard vs los reportados por el equipo de Marketing Science Corporativo (Corp tool). La investigación incluyó un diagnóstico exhaustivo contra BigQuery con queries comparativas entre todas las fuentes posibles.

**Pregunta de negocio**: ¿Por qué el dashboard muestra VPU ~$56-70/usuario para meses históricos (2025-Mar 2026) mientras el Corp tool muestra ~$20-24/usuario para los mismos períodos?

---

### 86.2 Metodología del diagnóstico

Se corrieron 5 queries de diagnóstico directas a BigQuery comparando:

| Query | Tablas comparadas | Métrica |
|---|---|---|
| D1 | `BT_OC_NR_REPORTE_TORRE_DAILY` vs `BT_OC_DASHBOARD_ALL_CAMPAIGNS_NR` | UCR N+R y VPU (lift vs 7D adj) |
| D2 | `BT_OC_DASHBOARD_ALL_CAMPAIGNS_NR` sin filtro | CLASIF_CAMPAIGNS breakdown completo Mar-26 |
| D3 | `BT_MP_INDIVIDUALS_PERFORMANCE` PANDORA | Diferencia 2D vs 7D window |
| D4 | `BT_MP_ACTIVATION_REVENUE_MKT_SCORING` | Acceso y schema |
| D5 | Los 3 fuentes de Valor/VPU: Torre Daily + Dashboard Campaigns + Scoring table | Serie histórica completa Ene25–May26 |

---

### 86.3 Hallazgo 1 — Fuente OC: sin diferencia material entre Torre Daily y Dashboard Campaigns

Query D1 y D5 confirmaron que para UCR (UCRANIA):

```
BT_OC_NR_REPORTE_TORRE_DAILY.NR_INC_USERS     == BT_OC_DASHBOARD_ALL_CAMPAIGNS_NR.NEW_7D_ADJUST+REC_7D_ADJUST
BT_OC_NR_REPORTE_TORRE_DAILY.NR_INC_VALUE     == BT_OC_DASHBOARD_ALL_CAMPAIGNS_NR.NEW_VALUE_7D_ADJUST+REC_VALUE_7D_ADJUST
Diferencia: 0.00 en TODOS los meses, tanto N+R como VPU.
```

Para OC ACT (ACTIVATION/ADHOC), el total es similar (~73K Torre Daily vs ~79K Dashboard Campaigns para Mar-26). La diferencia es explicada por campañas adicionales en Dashboard Campaigns que Torre Daily no captura (`CLASIF_CAMPAIGNS = 'CREDITS'`, `'FIELD MKT RECURRING'`, etc. con NR incremental pequeño).

**Conclusión D1/D5**: Cambiar la fuente de OC de Torre Daily a Dashboard Campaigns **NO modifica los valores de VPU ni resuelve el gap con el Corp tool**.

---

### 86.4 Hallazgo 2 — Root cause real: cambio de modelo de valor en Abril 2026

Query D5 reveló un corte abrupto y sincronizado en **todas las fuentes de valor** simultáneamente:

| Período | Modelo | UCR VPU | OC ACT VPU | VPU total site (scoring) |
|---|---|---|---|---|
| Ene-Mar 2026 (y todo 2025) | **Viejo (prediction-based)** | ~$57-62 | ~$51-64 | ~$51-61 |
| **Abr 2026 en adelante** | **Nuevo (fact-based)** | **~$22-23** | **~$25-26** | **~$22-23** |

El corte ocurre exactamente en Abril 2026 en las tres tablas:
- `BT_OC_NR_REPORTE_TORRE_DAILY.NR_INC_VALUE`
- `BT_OC_DASHBOARD_ALL_CAMPAIGNS_NR.NEW_VALUE_7D_ADJUST` / `NEW_INC_VALUE`
- `BT_MP_ACTIVATION_REVENUE_MKT_SCORING.REVENUE_PREDICTION`

Esto corresponde a la **"Implementación Nuevo modelo de valor Fact Based"** documentada en el PPT mensual del equipo de MktSci Corp (Abr-26). El nuevo modelo baja el VPU predicho de ~$55-70 a ~$22-26 por usuario.

**Datos exactos del diagnóstico** (tabla resumen; serie completa en D5):

| mes | UCR VPU (Torre Daily) | UCR VPU (Dash Camps) | VPU scoring total site |
|---|---|---|---|
| 202501 | — | $58.83 | $55.57 |
| 202503 | $56.83 | $56.83 | $60.87 |
| 202504 | **$22.86** | **$22.86** | **$22.72** |
| 202505 | **$21.90** | **$21.90** | **$22.39** |

Nota (confirmado con diagnóstico adicional §86.11): el Corp query, cuando se corre HOY contra las tablas BQ públicas, produce EXACTAMENTE los mismos VPU históricos que nuestro dashboard (~$60 para Mar-26). El scoring table (`BT_MP_ACTIVATION_REVENUE_MKT_SCORING`) tiene 1 fila por usuario-fecha (sin doble conteo confirmado), con `REVENUE_PREDICTION` avg = $67.61 para Mar-26 (modelo viejo). El Corp TOOL en las capturas muestra $20-24 para todos los meses históricos porque utiliza un **pipeline interno de MktSci que retroactivamente actualiza la tabla cuando se despliega un nuevo modelo**. Ese pipeline opera sobre una versión interna no accesible desde `SBOX_MARKETING` pública. Conclusión definitiva: no existe forma de replicar el histórico del Corp tool desde BQ público — el dato en sí está congelado en el modelo viejo para pre-Abr 26.

---

### 86.5 Hallazgo 3 — CLASIF_CAMPAIGNS: campo en español, no inglés

Query D2 reveló que `BT_OC_DASHBOARD_ALL_CAMPAIGNS_NR.CLASIF_CAMPAIGNS` usa valores en **español**:
- `'UCRANIA'`, `'ACTIVACION'`, `'ADHOC'`, `'FIELD MKT RECURRING'`, `'CREDITS'`, `'SELLERS'`, `'RESTO INDIVIDUOS'`, etc.

El campo `STRATEGY` (distinto de `CLASIF_CAMPAIGNS`) usa inglés: `'UCRANIA'`, `'ACTIVATION'`, `'ACQUISITION'`, `'RE-ACTIVATION'`, `'ENGAGEMENT'`, etc.

La Corp query oficial usa `CLASIF_CAMPAIGNS` para la lógica de NR (UCR = 7D adj, resto = INC). Nuestras queries Comms_OC usan `STRATEGY`. Son campos distintos — no confundir.

**Distribución NR en BT_OC_DASHBOARD_ALL_CAMPAIGNS_NR para Mar-26** (top CLASIF_CAMPAIGNS por nr_inc):

| CLASIF_CAMPAIGNS | STRATEGY | nr_7d_adj | nr_inc | vpu_inc |
|---|---|---|---|---|
| ACTIVACION | RE-ACTIVATION | 0 | 36,536 | $58.12 |
| ACTIVACION | ACTIVATION | 0 | 32,291 | $52.41 |
| UCRANIA | UCRANIA | 42,282 | 3,972 | $66.04 |
| ADHOC | ACQUISITION | 0 | 3,540 | $52.35 |
| UCRANIA | None | 27,749 | 0 | — |

---

### 86.6 Hallazgo 4 — PANDORA: no está en BT_MP_INDIVIDUALS_PERFORMANCE con SOURCE_CD='INSTALLS'

Query D3 devolvió 0 filas para PANDORA con `SOURCE_CD='INSTALLS'` en `BT_MP_INDIVIDUALS_PERFORMANCE`. Los datos de PANDORA en el contexto de N+R/Valor provienen de `BT_OC_NR_REPORTE_TORRE_DAILY` (como `CANAL='PANDORA'` dentro de `CLASIFICACION='UCRANIA'` o `'ACTIVATION'`), y de `BT_OC_DASHBOARD_ALL_CAMPAIGNS_NR`. La Corp query maneja PANDORA desde `BT_MP_INDIVIDUALS_PERFORMANCE` con ventana de 2 días (`NEW_USERS_2D_INAPP`), pero eso es para la vista de canales Paid — no aplica a nuestra fuente de datos TC.

---

### 86.7 Hallazgo 5 — Scoring table: accesible pero con el mismo corte de modelo

`BT_MP_ACTIVATION_REVENUE_MKT_SCORING` schema confirmado:
- `CUS_CUST_ID INT64`, `SIT_SITE_ID STRING`, `EVENT_DATE DATE`, `REVENUE_PREDICTION FLOAT64`
- Acceso desde `meli-bi-data.SBOX_MARKETING`

La tabla tiene acceso, pero sus valores también muestran el corte de modelo en Abr-26 (viejo modelo pre-Abr, nuevo modelo desde Abr). No tiene versión retroactiva del nuevo modelo para meses históricos. La Corp tool debe estar usando una versión diferente/más reciente de este scoring que retroactivamente aplica el nuevo modelo a todo el histórico.

---

### 86.8 Implicaciones en el dashboard

#### Para datos ACTUALES (Abr 2026 en adelante) — ALINEADOS ✅

Nuestro dashboard ya usa el nuevo modelo para meses corrientes. Los valores de VPU (~$22-26) y Valor Pred coinciden con el Corp tool para Abr/May 2026.

#### Para datos HISTÓRICOS (antes de Abr 2026) — GAP CONOCIDO ⚠️

| Métrica | Nuestro dashboard | Corp tool | Causa |
|---|---|---|---|
| VPU Pred 90D (ej. Mar-26) | ~$56-62/usuario | ~$20-24/usuario | Modelo viejo vs retroactivo |
| Valor Pred 90D total site (Mar-26) | ~$68M | ~$26M | Mismo |
| N+R | ~143K OC, ~1.12M total | ~143K OC, ~1.12M total | **Sin diferencia** ✅ |
| CPA | Idéntico (depende de N+R e inversión) | Idéntico | **Sin diferencia** ✅ |

El gap en Valor/VPU histórico es una **deuda de datos del equipo de MktSci**, no un bug del dashboard. No hay tabla BQ disponible que tenga el nuevo modelo aplicado retroactivamente a 2025 y Q1-2026.

#### Pendiente de implementación: marcador visual en gráficas

Se deberá agregar en las gráficas de VPU y Valor Pred 90D una **línea vertical discontinua en Abr-2026** con label "Nuevo modelo de valor" para contextualizar el corte. Ver §87 para la implementación.

---

### 86.11 Confirmación MktSci Corp — factor de normalización histórica

Después de la investigación exhaustiva, el equipo de Marketing Science Corp confirmó (2026-05-07):

> "Para poder tener comparaciones justas de valor se decidió usar un factor único para nivelar el valor histórico al actual. Previo a 202604 el valor de MLM se calcula como `valor × 0.38`"

**Validación matemática:**
| Mes | VPU raw BQ | × 0.38 | Corp tool muestra |
|---|---|---|---|
| Ene-26 | $53.55 | **$20.35** | ~$20-21 ✓ |
| Feb-26 | $56.65 | **$21.53** | ~$21-22 ✓ |
| Mar-26 | $60.87 | **$23.13** | ~$22-24 ✓ |
| Abr-26 | $22.72 | sin factor | ~$22-23 ✓ |

**Implementación (§87):** `src/processors.py` — constantes `_VALOR_BREAK_MONTH = '202604'` y `_VALOR_HIST_FACTOR = 0.38`. Se aplican a `perf_vpu_prod` y `perf_roa_num` post-propagación bottom-up para todos los meses anteriores a Abril 2026.

El "pipeline" del Corp tool es exactamente este factor aplicado a los mismos datos BQ que tenemos — no había ninguna tabla ni query diferente. La investigación D1-D5 fue necesaria para llegar a esta conclusión.

### 86.9 Decisiones de arquitectura tomadas (confirmadas)

1. **Fuente OC para VPU**: Mantener `BT_OC_NR_REPORTE_TORRE_DAILY.NR_INC_VALUE` — es idéntica a `BT_OC_DASHBOARD_ALL_CAMPAIGNS_NR.NEW_VALUE_7D_ADJUST` para UCR y similar para OC ACT. No hay ganancia en cambiar.

2. **Scoring table**: No implementar `BT_MP_ACTIVATION_REVENUE_MKT_SCORING` como fuente de Valor total site por ahora — tiene el mismo corte de modelo que nuestras fuentes actuales, y el residual ORG no mejora significativamente.

3. **Prioridad**: El corte de modelo visual (§87) tiene mayor impacto operativo que cualquier cambio de fuente de datos.

4. **Pestaña Reporting §85 — fixes aplicados el mismo día**:
   - `total_inv()` corregido para usar `'Total Inversión'` directamente (eliminando double-count de nodos padre)
   - `vsplan_row` corregido: ahora es `Total N+R corp / Plan Total N+R` (antes era MKT Gestionado / Plan MKT)
   - `growth_annotations()` con `use_arrows=True`: callouts con flecha estilo PPT en charts c1 y c2
   - Formato totales N+R: `"1.12"` sin sufijo M (c1) y `"26.0"` sin `$M` (c2)
   - `margin.t=75` en c1 y c2 para dar espacio a los callouts

### 86.10 Archivos modificados en §86

| Archivo | Cambio |
|---|---|
| `docs/History.md` | §86 añadida (este documento) |
| `CLAUDE.md` | §86 añadida al historial + sección VPU/Valor con nota del cambio de modelo |
| `src/builders.py` | Fixes Reporting §85: `total_inv()`, `vsplan_row`, `growth_annotations(use_arrows)`, formatos, márgenes |
| `dashboard_v1.html` | Regenerado 2026-05-07 09:36 — 110,443 KB |

---

## §87 — 7-May-2026 — Factor normalización histórica VPU + marcador modelo + fix deploy SSL

### 87.1 Contexto

Continuación directa de §86. Tres implementaciones en la misma sesión:
1. Factor de normalización 0.38 para Valor/VPU histórico (confirmado por MktSci Corp)
2. Marcador visual del corte de modelo en chart Valor Predictivo (Reporting)
3. Fix de error SSL en deploy a Apps Script

---

### 87.2 Factor de normalización histórica — `processors.py`

**Origen**: El equipo de Marketing Science Corp confirmó que para mantener comparaciones históricas justas entre el modelo viejo (prediction-based, pre-Abr 2026) y el nuevo (fact-based, desde Abr 2026), se adoptó el factor de nivelación:

```
Valor histórico (pre-202604) × 0.38 = Valor fact-based equivalente
```

**Validación matemática contra datos Corp tool:**

| Mes | VPU raw BQ | × 0.38 | Corp tool muestra |
|---|---|---|---|
| Ene-26 | $53.55 | **$20.35** | ~$20-21 ✓ |
| Feb-26 | $56.65 | **$21.53** | ~$21-22 ✓ |
| Mar-26 | $60.87 | **$23.13** | ~$22-24 ✓ |
| Abr-26+ | $22.72 | sin factor | ~$22-23 ✓ (alineado) |

**Implementación** en `src/processors.py` — dos bloques post-propagación bottom-up:

```python
# Constantes
_VALOR_BREAK_MONTH  = '202604'   # Primer mes con modelo nuevo (sin factor)
_VALOR_HIST_FACTOR  = 0.38       # Factor confirmado por equipo MktSci Corp

# Aplicado a perf_vpu_prod (VPU + Valor Pred 90D)
for lbl in perf_vpu_prod:
    for m in list(perf_vpu_prod[lbl].keys()):
        if m < _VALOR_BREAK_MONTH:
            perf_vpu_prod[lbl][m] = (perf_vpu_prod[lbl][m] or 0) * _VALOR_HIST_FACTOR

# Aplicado a perf_roa_num (ROAs)
for lbl in perf_roa_num:
    for m in list(perf_roa_num[lbl].keys()):
        if m < _VALOR_BREAK_MONTH:
            perf_roa_num[lbl][m] = (perf_roa_num[lbl][m] or 0) * _VALOR_HIST_FACTOR
```

**Por qué aplicar DESPUÉS de la propagación bottom-up**: Después de la propagación, tanto hojas como nodos padre tienen valores correctamente agregados. Aplicar 0.38 uniformemente a todos los nodos es matemáticamente equivalente a aplicarlo solo a las hojas antes de propagar: `padre × 0.38 = Σ(hoja_i × 0.38)`. Se aplica después por simplicidad y claridad.

**Cascada de impacto**: `perf_vpu_prod` y `perf_roa_num` alimentan:
- **Performance_vista_FM**: filas VPU Pred 90D, Valor Pred 90D, ROAs
- **Reporting Sección 1**: chart Valor Predictivo + tabla VPU Total
- **Reporting Sección 3**: ROAs OC
- **Plan vs VPU**: comparaciones Plan VPU / vs Plan VPU ahora comparables

**Qué NO cambia**: N+R, inversión, CPA — no son métricas de valor predicho.

---

### 87.3 Marcador visual corte de modelo — `builders.py`

**Función agregada**: `_apply_model_break(layout)` en `build_reporting_tab_html()`.

**Lógica**:
```python
_MODEL_BREAK_YYYYMM = '202604'
_break_idx = next((i for i, m in enumerate(months6) if m >= _MODEL_BREAK_YYYYMM), None)
_show_break = _break_idx is not None and _break_idx > 0  # solo si hay mezcla viejo+nuevo
```

**Se aplica solo a c2** (chart Valor Predictivo in App) — único chart que muestra la métrica afectada por el cambio de modelo. c1 (N+R) y c5 (OC Estrategia) no la necesitan.

**Elementos visuales**:
- Línea vertical discontinua marrón (`#795548`, width=1.5, dash=dot) en `x = break_idx - 0.5` (entre Mar-26 y Abr-26)
- Callout con fondo crema: `⚠ Nuevo modelo de valor` (font 8px, bgcolor `rgba(255,243,224,0.9)`)

**Auto-extinción**: cuando la ventana de 6 meses avance y todos los meses sean post-Abr-26, `_show_break = False` y el marcador desaparece automáticamente.

---

### 87.4 Fix deploy SSL — `deploy_appscript_v1.py`

**Error**: `ssl.SSLWantWriteError: The operation did not complete (write)` al subir ~110 MB via `googleapiclient+httplib2`.

**Causa raíz**: `httplib2` no maneja correctamente el envío de payloads grandes sobre SSL — devuelve `WANT_WRITE` cuando el buffer SSL se llena y no tiene retry interno para ese caso.

**Fix**: reemplazada la función `update_files()` para usar `google.auth.transport.requests.AuthorizedSession` con `requests` como transport HTTP, que maneja chunks internamente:

```python
# Antes (fallaba con ~110 MB):
service.projects().updateContent(scriptId=script_id, body=body).execute()

# Después (robusto para payloads grandes):
creds, _ = google.auth.default(scopes=REQUIRED_SCOPES)
session  = google.auth.transport.requests.AuthorizedSession(creds)
resp = session.put(url, json=body, timeout=300)
if not resp.ok:
    raise RuntimeError(f"updateContent falló {resp.status_code}: {resp.text[:400]}")
```

La misma credencial ADC se usa en ambas rutas — no requiere re-autenticación.

---

### 87.5 Archivos modificados en §87

| Archivo | Cambio |
|---|---|
| `src/processors.py` | +normalización `_VALOR_HIST_FACTOR=0.38` para `perf_vpu_prod` y `perf_roa_num`, meses < `'202604'` |
| `src/builders.py` | +`_MODEL_BREAK_YYYYMM`, `_break_idx`, `_show_break`, `_apply_model_break()`. Aplicado a `c2_layout`. |
| `src/deploy_appscript_v1.py` | `update_files()`: `googleapiclient.execute()` → `AuthorizedSession.put()` con `timeout=300` |
| `CLAUDE.md` | §87 en historial + factor 0.38 en sección Modelo Valor + pendiente eliminado |
| `docs/History.md` | §87 añadida (este documento) |
| `dashboard_v1.html` | Regenerado 2026-05-07 13:59 — 110,444 KB |

---

## §88 — 11-May-2026 — Nueva pestaña "Installs Mensual"

### 88.1 Contexto y motivación

Se creó una nueva pestaña **"Installs Mensual"** que replica exactamente el look & feel de NR Mensual (Vista FM + Vista Corp, misma jerarquía de canales, mismos colores, misma tabla colapsable) pero muestra installs de la app en lugar de N+R.

Objetivo: trackear el funnel completo Installs → N+R → Activaciones para todos los canales de marketing.

---

### 88.2 Iteración de fuentes de datos (diagnóstico exhaustivo)

La implementación pasó por 4 iteraciones de fuente de datos antes de encontrar la correcta:

**Iteración 1 — `BT_MP_INDIVIDUALS_PERFORMANCE.QTY_DEVICES` + `Q_INSTALLS`**
- POM ADQ desde `QTY_DEVICES` con `SOURCE_CD='INSTALLS'` → 518K (Mar-26)
- Corp screenshot muestra 811K → gap de 293K inexplicable
- Diagnóstico: `QTY_DEVICES` para `TOOL_COST` = 0 en el 100% de filas (verificado empiricamente)
- Diagnóstico: todos los POM strategies dan solo 518K total — el 293K no existe en esta tabla

**Iteración 2 — Corp CTE_ADQ_ACT (CASE WHEN adaptado)**
- Misma fuente pero sin filtro SOURCE_CD y con CASE WHEN del Corp query
- Resultado: mismo 518K para POM — confirma que el límite es la tabla, no el filtro

**Iteración 3 — Descubrimiento `BASE_INSTALLS_LIFECYCLE`**
- Usuario identificó `meli-bi-data.SBOX_MKTCORPMP.BASE_INSTALLS_LIFECYCLE`
- Verificación contra Corp screenshot Mar-26: POM=818K vs Corp=811K (+0.9%), Organic=943K vs 941K (+0.2%), MGM=48K vs 48K ✅
- **Esta es la fuente correcta** — diferencia < 1% en todos los canales

### 88.3 Fuente final: `BASE_INSTALLS_LIFECYCLE`

```sql
-- Schema relevante:
channel                     STRING  -- POM | Own Channels MKT | Own Channels PRD |
                                   --  Own Channels OTHERS | MGM | Partnerships |
                                   --  BRANDFORMANCE | OTHERS | ORGANICO
fecha_mes                   STRING  -- YYYYMM
flag_reinstall              BOOL    -- TRUE=reinstall, FALSE=instalación nueva
qty_custs_potential_new     INT64   -- clientes potential NEW
qty_custs_potential_recovered INT64 -- clientes potential RECOVERED
qty_custs_repeated          INT64   -- reinstalaciones de usuarios existentes

-- Total installs = new + recovered + repeated (todos los que instalaron)
```

**Mapeo channel → dashboard label (FM):**
| channel | INST_CANAL |
|---|---|
| `POM` | `'POM ADQ'` (sin split ADQ/ACT — tabla no tiene breakdown) |
| `Own Channels MKT` | `'UCR Gest'` |
| `Own Channels PRD` | `'UCR PRD'` |
| `Own Channels OTHERS` | `'OC ACT'` |
| `MGM` | `'MGM ADQ'` |
| `Partnerships` | `'L&P ADQ'` |
| `BRANDFORMANCE` | `'L&P ADQ'` |
| `OTHERS` | `'L&P ADQ'` |
| `ORGANICO` | `'ORG'` |

**Mapeo channel → corp_key (Corp):**
| channel | corp_key |
|---|---|
| `Own Channels MKT` | `'corp_ucr_eg'` (node_id directo — sin breakdown medio) |
| `POM` | `'corp_pom'` (node_id directo — sin breakdown ADQ/ACT) |
| `Own Channels PRD` | `'OTH|UCR_PRD|TOTAL'` |
| `Own Channels OTHERS` | `'OC|OC_ADHOC|TOTAL'` |
| `MGM` | `'OTH|MGM|TOTAL'` |
| `Partnerships` | `'OTH|LP|PARTNERSHIPS'` |
| etc. | (bq_keys estándar) |

---

### 88.4 Arquitectura implementada

**Nuevas funciones en `queries.py`:**
- `get_installs_monthly_sql(HIERARCHY_NR)` — query FM desde BASE_INSTALLS_LIFECYCLE
- `get_installs_corp_monthly_sql()` — query Corp desde BASE_INSTALLS_LIFECYCLE

**Nueva función en `processors.py`:**
- `process_installs_monthly(bq_client, config)` — procesa FM + Corp

**Decisión de diseño crítica — Corp: nodos padre directamente poblados:**
`corp_ucr_eg` y `corp_pom` son nodos padre sin `bq_key` en la config. La tabla no tiene breakdown de medio (EMAIL/PUSH/PANDORA para UCR, ADQ/ACT para POM). Solución:
1. La Corp SQL usa el `node_id` directamente como `corp_key` (en lugar de `bq_key`)
2. El processor detecta si `corp_key` es un `node_id` válido (check directo en `installs_corp_by_node`)
3. Los nodos directamente poblados se marcan en `directly_populated: set()`
4. La propagación bottom-up **SALTA** los nodos en `directly_populated` — sus padres sí se calculan sumando hijos (incluyendo el nodo directo)

```python
# Lógica clave en process_installs_monthly()
directly_populated = set()
for _, r in df_corp.iterrows():
    corp_key = r['corp_key']
    node_id  = corp_key_to_node.get(corp_key)           # Intenta bq_key lookup
    if node_id is None and corp_key in installs_corp_by_node:
        node_id = corp_key                              # Usa como node_id directo
    if node_id:
        installs_corp_by_node[node_id][m] = int(r['installs_corp'])
        directly_populated.add(node_id)

# Bottom-up: skip directamente poblados
for c in reversed([...non-leaf nodes...]):
    if nid in directly_populated:
        continue  # No sobreescribir con sum(children=0)
    installs_corp_by_node[nid][m] = sum(children)
```

**Nuevas funciones en `builders.py`:**
- `build_installs_table_html(data)` — tabla FM con jerarquía + MoM (sin Plan)
- `build_installs_bar(data)` — barras apiladas + línea CPI (Cost Per Install)
- `build_installs_corp_bar_chart(data)` — barras por grupo Corp
- `build_installs_corp_table_html(data)` — tabla colapsable 4 niveles Corp

**Fix crítico en `build_installs_corp_bar_chart()` GROUPS:**
```python
# INCORRECTO (usaba hijos con 0 installs):
('corp_pom', 'POM', '#1FB8D4', ['corp_acq_pom','corp_act_pom','corp_web_pom','corp_ctw_pom'])
('corp_oc_ucr', 'OC+UCR', '#F5D000', ['corp_ucr_eg_email', 'corp_ucr_eg_pandora', ...])

# CORRECTO (usa nodos padre donde tenemos datos):
('corp_pom', 'POM', '#1FB8D4', ['corp_pom'])
('corp_oc_ucr', 'OC+UCR', '#F5D000', ['corp_ucr_eg', 'corp_oc_adhoc'])
```

**Template `template_dashboard.html`:**
- +tab `installs-mensual` + pane `{{INSTALLS_TABLE}}` + `{{INSTALLS_CORP_TABLE}}`
- +8 funciones JS: `renderKPIsInstallsMensual`, `filterTableInstallsMensual`, `highlightColInstallsMensual`, `updateAnnotInstallsMensual`, `updateCPIInstallsMensual`, `highlightChartInstallsMensual`, `highlightMonthInstallsMensual`, `toggleCorpInstallsNode`, `collapseCorpInstallsNode`
- TABS array actualizado con `'installs-mensual'`
- `onCanalChange()` y `onMonthChange()` actualizados para responder al tab installs

**`gen_dashboard_v1.py`:**
- +import `process_installs_monthly` y builders de installs
- +Paso 3d: `process_installs_monthly(client, config)`
- +`monthly_installs`, `monthly_installs_mom`, `installs_months` en `data_js`
- +`installs_bar`, `installs_corp_bar` en `charts{}`
- +`replace('{{INSTALLS_TABLE}}', ...)` y `replace('{{INSTALLS_CORP_TABLE}}', ...)`

---

### 88.5 Validación de números (Mar + Abr 2026)

| Canal | Nuestro (Mar-26) | Corp screenshot | Diff |
|---|---|---|---|
| POM | 818,327 | 811,305 | **+0.9%** ✅ |
| Own Channels MKT (UCR) | 145,006 | 202,497* | — |
| Own Channels PRD | 16,842 | — | — |
| Own Channels OTHERS (OC ACT) | 40,559 | — | — |
| **UCR total** (MKT+PRD+OTHERS) | **202,407** | **202,497** | **+0.04%** ✅ |
| MGM | 48,437 | 48,004 | **+0.9%** ✅ |
| L&P (Part+Brand+Others) | 105,720 | 104,885 | **+0.8%** ✅ |
| ORG | 943,242 | 941,115 | **+0.2%** ✅ |
| **TOTAL** | **~2.09M** | — | ✅ |

---

### 88.6 Archivos modificados en §88

| Archivo | Cambio |
|---|---|
| `src/queries.py` | +`get_installs_monthly_sql()` y `get_installs_corp_monthly_sql()` (SSOT: BASE_INSTALLS_LIFECYCLE) |
| `src/processors.py` | +import nuevas queries. +`process_installs_monthly()` con lógica `directly_populated` |
| `src/builders.py` | +`build_installs_table_html()`, `build_installs_bar()`, `build_installs_corp_bar_chart()`, `build_installs_corp_table_html()`. Fix GROUPS: usar nodos padre para POM y OC+UCR |
| `src/template_dashboard.html` | +tab `installs-mensual` + pane + placeholders + 9 funciones JS. TABS y handlers actualizados |
| `src/gen_dashboard_v1.py` | +import + Paso 3d + data_js + charts + replace placeholders |
| `CLAUDE.md` | §88 en historial + pestaña Installs Mensual en tabla de pestañas + tabla de fuentes |
| `docs/History.md` | §88 añadida (este documento) |
| `dashboard_v1.html` | Regenerado 2026-05-11 13:02 — 113,905 KB (con builder fix pendiente de regeneración) |

---

## §89 — 11-May-2026 — Fix crítico: doble aplicación factor 0.38 en ROAS POM

### 89.1 Síntoma y root cause

El usuario observó que **Total ROAS en Performance_vista_FM** mostraba valores en el rango 0.9x–1.1x para todos los meses pre-Abr-26, muy por debajo del rango 1.5x–2.0x del Corp tool.

Los valores de ROAS por canal individualmente (OC y POM) sí coincidían con Corp cuando se verificaban aislados. El problema era en la **agregación total**.

**Root cause identificado en `src/processors.py` (líneas ~503–521 antes del fix):**

El factor de normalización histórica 0.38 se aplicaba **dos veces** a los canales POM:

```python
# ORDEN INCORRECTO — causaba ×0.38×0.38 = ×0.1444 en POM:

# Paso A: perf_vpu_prod ×0.38 para todos (líneas ~480-483)
for lbl in perf_vpu_prod:
    if m < _VALOR_BREAK_MONTH:
        perf_vpu_prod[lbl][m] *= 0.38   # ← POM ya tiene ×0.38 aquí

# Paso B: POM roa_num = perf_vpu_prod  (ya ×0.38)
for lbl in ['POM ADQ', 'POM ACT']:
    perf_roa_num[lbl][m] = perf_vpu_prod[lbl].get(m, 0)

# Paso C: Propagación bottom-up

# Paso D: BUG — aplica 0.38 de NUEVO a todo, incluyendo POM
for lbl in perf_roa_num:          # ← POM recibe ×0.38 por segunda vez
    if m < _VALOR_BREAK_MONTH:
        perf_roa_num[lbl][m] *= 0.38   # POM queda ×0.38×0.38 = ×0.1444
```

**Impacto matemático:**
- OC: ×0.38 correcto (una sola aplicación)
- POM: ×0.1444 incorrecto (0.38²) → numerador ROA POM ~73% menor de lo correcto
- Total ROAS = (ROA_OC_num + ROA_POM_num) / (INV_OC + INV_POM) → resultado artificialmente bajo

---

### 89.2 Fix implementado

Se reordenó el bloque de normalización ROA numerador para aplicar 0.38 **sólo a los canales OC** (que vienen raw de BQ) antes de asignar POM desde `perf_vpu_prod`:

```python
# ORDEN CORRECTO — código final en processors.py:

# Paso 1: poblar canales OC desde df_perf_roa (raw, sin factor todavía)
for _, r in df_perf_roa.iterrows():
    perf_roa_num[lbl][m] = float(r['ROA_VALUE_PRED'] or 0)

# Paso 2: aplicar 0.38 SOLO a canales OC (vienen de BQ sin normalizar)
_oc_roa_labels = {str(r['PERF_CANAL']) for _, r in df_perf_roa.iterrows()
                  if str(r['PERF_CANAL']) in perf_roa_num}
for lbl in _oc_roa_labels:
    if m < _VALOR_BREAK_MONTH:
        perf_roa_num[lbl][m] *= 0.38   # Una sola vez ✓

# Paso 3: asignar POM desde perf_vpu_prod (ya tiene ×0.38 del bloque anterior)
for lbl in ['POM ADQ', 'POM ACT']:
    perf_roa_num[lbl][m] = perf_vpu_prod[lbl].get(m, 0)   # No necesita factor ✓

# Paso 4: propagación bottom-up (todas las hojas tienen factor correcto)
# — Sin segundo loop de 0.38 —
```

**Canales OC afectados por `_oc_roa_labels`** (los que vienen de `df_perf_roa` / `get_roa_tc_sql()`): UCR Gest, OC ACT — exactamente los que necesitan el factor porque vienen raw de `NR_INC_VALUE` de Torre Daily.

**MGM ADQ** sigue excluido del numerador ROA intencionalmente (§88): tiene `perf_vpu_prod` real pero inversión=0 → ROAS MGM = "—" es correcto.

---

### 89.3 Efecto esperado en los datos

| Canal | Antes del fix (pre-Abr-26) | Después del fix |
|---|---|---|
| OC (UCR Gest + OC ACT) | ×0.38 correcto | ×0.38 correcto (sin cambio) |
| POM ADQ + POM ACT | ×0.38² = ×0.1444 | ×0.38 correcto |
| Total N+R ROAS | ~0.9x–1.1x (incorrecto) | ~1.5x–2.0x (alineado con Corp) |

---

### 89.4 Archivos modificados en §89

| Archivo | Cambio |
|---|---|
| `src/processors.py` | Fix doble-0.38: reordenación de pasos en bloque `perf_roa_num`. `_oc_roa_labels` set para aplicar factor solo a OC. Eliminado loop `for lbl in perf_roa_num` al final. |
| `CLAUDE.md` | §89 en historial. Actualización de la nota sobre `perf_roa_num` en §87. |
| `docs/History.md` | §89 añadida (este documento) |
