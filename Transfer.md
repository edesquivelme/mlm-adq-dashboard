# MLM ADQ N+R Dashboard — Transfer Guide

**Proyecto**: MLM ADQ N+R Dashboard V1  
**Transferido por**: sergio.ibarra@mercadolibre.com.mx  
**Fecha de transferencia**: 2026-07-08  
**URL del dashboard en producción**: `https://script.google.com/a/macros/mercadolibre.com.mx/s/AKfycby5omz-zArFOJ0s4LyGydEGv5_JEUfbDbY0TxT9LKg0C1c_0oBmPjsHvDfcHZkgKOcs/exec`

---

## Qué es este proyecto

Dashboard web interactivo de N+R (Nuevos + Recuperados) para el equipo de Analytics de Adquisición de MercadoLibre México. Genera un HTML de ~120 MB con 10 pestañas de datos de performance de adquisición por canal. El HTML se sube a Google Apps Script y se sirve como web app.

El flujo completo es:
```
BigQuery (datos) + Excel (plan) → Python (genera HTML) → Apps Script (sirve como web)
```

---

## Paso 0 — ANTES de empezar: Sergio debe darte acceso

Antes de correr cualquier cosa, necesitas que Sergio haga **2 acciones en su lado**:

### Acción 1 — Acceso al proyecto Apps Script
1. Sergio abre [script.google.com/home](https://script.google.com/home)
2. Abre el proyecto `MLM ADQ N+R Dashboard v1`
3. Clic en el ícono de personas (👤+) → `Compartir` → Agrega tu email con rol **Editor**

Sin esto, el comando `python src/deploy_appscript_v1.py` te dará error 403.

### Acción 2 — Verificar tu acceso a BigQuery
Confirmar que tu cuenta tiene permisos de lectura en `meli-bi-data` sobre:
- `SBOX_EG_MKT` (tablas BT_OC_*)
- `SBOX_MARKETING` (tablas BT_MP_*)
- `SBOX_MKTCORPMP` (tabla BASE_INSTALLS_LIFECYCLE)
- `WHOWNER` (tabla LK_API_CURRENCY_CONVERSION)

---

## Paso 1 — Instalar Python y dependencias

Requiere **Python 3.10 o superior**.

```powershell
# Desde la carpeta raíz del proyecto (donde está este archivo)

# Crear entorno virtual
python -m venv vEnv_Meli_Code1

# Activar entorno virtual (Windows)
.\vEnv_Meli_Code1\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

---

## Paso 2 — Configurar Google Cloud ADC (autenticación)

El proyecto usa **Application Default Credentials (ADC)** — credenciales de tu cuenta personal de Google (`@mercadolibre.com.mx`). Las librerías Python (`google-cloud-bigquery`, `google-auth`) las leen automáticamente; no necesitas pasar ningún archivo de credenciales al código.

```powershell
# Autenticación COMPLETA (BigQuery + Apps Script API)
# ⚠️ Usar EXACTAMENTE este comando con todos los --scopes
gcloud auth application-default login --scopes="https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/script.projects,https://www.googleapis.com/auth/script.deployments,https://www.googleapis.com/auth/drive.file"
```

Abre el browser, autoriza con tu cuenta `@mercadolibre.com.mx`, y listo.

**Qué hace este comando:** crea el archivo `application_default_credentials.json` en:
```
C:\Users\[tu_usuario]\AppData\Roaming\gcloud\application_default_credentials.json
```

Ese archivo contiene un `refresh_token` vinculado a tu cuenta personal. **No compartas ese archivo** — quien lo tenga puede actuar en nombre de tu cuenta.

**Verificar que funcionó:**
```powershell
gcloud auth application-default print-access-token
# Debe imprimir un token largo. Si da error, el login no funcionó.
```

> **IMPORTANTE — scopes**: si solo corres `gcloud auth application-default login` sin `--scopes`, BigQuery funciona pero el deploy a Apps Script fallará con error de scopes insuficientes.

> **Nota**: el comando `gcloud config` puede mostrar una cuenta o proyecto diferente (service account de otro sistema). Eso es independiente del ADC — las librerías Python **solo leen el archivo ADC**, no la config de gcloud CLI.

---

## Paso 3 — Generar el dashboard

```powershell
# Desde la raíz del proyecto, con el venv activado
python src/gen_dashboard_v1.py
```

**Qué hace este comando:**
1. Consulta BigQuery (~5-10 min, dependiendo de cuotas)
2. Lee el plan de negocio de `data/Resumen Plan Acq 2026.xlsx`
3. Carga el cache de Comms_OC de `data/comms_oc_cache.json`
4. Genera `dashboard_v1.html` (~120 MB) en la raíz del proyecto

**Output esperado al final:**
```
>>> Paso 4: Ensamblando HTML Final...
  OK: dashboard_v1.html generado (XXXXX KB)
```

Si BigQuery excede cuota (error `Quota BQ excedida`), el script reintenta automáticamente 3 veces con 120s de espera.

---

## Paso 4 — Subir a Apps Script (deploy)

```powershell
python src/deploy_appscript_v1.py
```

**Output esperado al final:**
```
DEPLOY EXITOSO - ENTORNO V1
URL permanente: https://script.google.com/a/macros/mercadolibre.com.mx/s/AKfycby5omz-.../exec
```

La URL ya está compartida con el equipo — es la misma de siempre, no cambia con cada deploy.

> **Si el deploy falla con 403**: verifica que Sergio te haya dado acceso Editor al proyecto Apps Script (Paso 0).  
> **Si falla con error SSL**: el script reintenta 3 veces automáticamente (payload de ~120 MB).

---

## Paso 5 — Flujo de trabajo diario (lo que harás regularmente)

El CI/CD automático **no está activo** en tu entorno. Debes correr los comandos manualmente cuando necesites actualizar el dashboard.

### Actualización normal (diaria/cuando necesites)
```powershell
.\vEnv_Meli_Code1\Scripts\activate
python src/gen_dashboard_v1.py       # genera HTML (~10 min)
python src/deploy_appscript_v1.py    # sube a Apps Script (~2-5 min)
```

### Una vez por mes — actualizar cache de Comms_OC
El archivo `data/comms_oc_cache.json` tiene el histórico de comunicaciones OC (95 MB). Al inicio de cada mes nuevo, agregar el mes cerrado:
```powershell
python scripts/refresh_comms_oc_cache.py    # incremental ~2-5 min
```

Si el cache se corrompe o necesitas reconstruir desde cero:
```powershell
python scripts/refresh_comms_oc_cache.py --full    # ~30-50 min
```

---

## Estructura del proyecto

```
MLM_ADQ_Dash/
├── CLAUDE.md                    ← Contexto maestro para Claude Code (leer siempre primero)
├── requirements.txt             ← Dependencias Python
├── Transfer.md                  ← Este archivo
│
├── src/                         ← Código fuente principal
│   ├── gen_dashboard_v1.py      ← Motor principal — orquesta todo
│   ├── queries.py               ← Genera SQL dinámico para BigQuery
│   ├── processors.py            ← Consulta BQ, procesa DataFrames
│   ├── builders.py              ← Genera HTML de tablas + charts
│   ├── builders_analysis.py     ← Genera pestaña de análisis OC+UCR
│   ├── template_dashboard.html  ← Template HTML con {{PLACEHOLDERS}}
│   ├── dashboard.css            ← Estilos
│   └── deploy_appscript_v1.py  ← Sube el HTML a Google Apps Script
│
├── config/
│   ├── channels_config.json     ← SSOT: jerarquía de canales, colores, mapeos BQ
│   ├── .appscript_config_v1.json ← scriptId + deploymentId del proyecto Apps Script
│   ├── comms_classification_config.json ← Clasificación de campañas OC
│   ├── reporting_methodology.md ← Metodología de la pestaña Reporting
│   └── queries/                 ← Documentación SQL canónica (referencia)
│
├── data/
│   ├── Resumen Plan Acq 2026.xlsx  ← Plan de negocio (fuente de metas)
│   ├── comms_oc_cache.json         ← Cache histórico Comms_OC (95 MB, Nov-25→Jun-26)
│   └── comms_oc_cache_meta.json    ← Metadata del cache
│   [comms_oc_current_month.json]   ← Se crea automáticamente en el primer run
│
├── scripts/
│   ├── refresh_comms_oc_cache.py  ← Actualiza el cache de Comms_OC
│   └── discover_deployment.py     ← Diagnóstico: lista deployments Apps Script
│
├── skills/                        ← Base de conocimiento para análisis con Claude Code
│   ├── analizar-Optimizar_Performance_KPIs_skill.md
│   ├── analizar-Optimizar_Performance_KPIs_context.md
│   ├── analizar-OC_Comms_skill.md
│   ├── OPTIMIZADOR-OC_skill.md
│   └── campaign_naming_guide.md
│
├── docs/
│   ├── metrics_logic.md         ← FUENTE DE VERDAD de KPIs y fórmulas
│   ├── NR_impact_methodology.md ← Metodología de cálculo de impacto N+R
│   └── History.md               ← Historial detallado de cambios (§1–§89+)
│
└── .claude/commands/            ← Comandos slash para Claude Code
    ├── analizar-oc-pom.md       ← /analizar-oc-pom
    ├── analizar-comms.md        ← /analizar-comms
    ├── optimizar-oc.md          ← /optimizar-oc
    ├── deploy.md                ← /deploy
    └── refresh.md               ← /refresh
```

**Archivo que NO está en la carpeta pero que se genera:**
- `dashboard_v1.html` — el HTML final (~120 MB). Se genera con `python src/gen_dashboard_v1.py`. No está en el transfer porque pesa demasiado y se regenera siempre.

---

## Usar Claude Code con este proyecto

Este proyecto usa **Claude Code** como asistente de desarrollo. El archivo `CLAUDE.md` es el contexto maestro que Claude lee automáticamente al abrir el proyecto.

### Setup de Claude Code
1. Instalar Claude Code: [claude.ai/code](https://claude.ai/code) o extensión VS Code
2. Abrir la carpeta `MLM_ADQ_Dash/` en VS Code (o terminal con `claude`)
3. Claude leerá `CLAUDE.md` automáticamente

### Comandos slash disponibles
| Comando | Qué hace |
|---|---|
| `/analizar-oc-pom` | Analiza performance de canales OC+UCR y POM |
| `/analizar-comms` | Analiza comunicaciones OC desde Comms_OC |
| `/optimizar-oc` | Optimizador de presupuesto y estrategia OC |

### Primera sesión recomendada con Claude
Empieza con:
```
Lee el CLAUDE.md y dame un resumen del estado actual del proyecto y las 3 cosas más importantes que debo saber como nuevo dueño del dashboard.
```

---

## Apps Script — información del proyecto

| Campo | Valor |
|---|---|
| Nombre del proyecto | MLM ADQ N+R Dashboard v1 |
| Script ID | `1lPA8MndfCRUQpepn66pSDvcRh_Pz_0dSrFiqFLSKOxm_x7rJ3rf1xoov` |
| Deployment ID | `AKfycby5omz-zArFOJ0s4LyGydEGv5_JEUfbDbY0TxT9LKg0C1c_0oBmPjsHvDfcHZkgKOcs` |
| URL pública | `https://script.google.com/a/macros/mercadolibre.com.mx/s/AKfycby5omz-zArFOJ0s4LyGydEGv5_JEUfbDbY0TxT9LKg0C1c_0oBmPjsHvDfcHZkgKOcs/exec` |

La URL **no cambia** con cada deploy — es un deployment fijo que siempre sirve la versión más reciente.

---

## Fuentes de datos BigQuery — referencia rápida

| Tabla | Dataset | Qué contiene |
|---|---|---|
| `BT_OC_NR_REPORTE_TORRE_DAILY` | `meli-bi-data.SBOX_EG_MKT` | N+R y costos de Own Channels (lift-based) |
| `BT_MP_INDIVIDUALS_PERFORMANCE` | `meli-bi-data.SBOX_MARKETING` | N+R y costos de canales Paid (POM, MGM, L&P) |
| `BT_MP_USER_ENGAGEMENT_INAPP` | `meli-bi-data.SBOX_MARKETING` | Total N+R in-app (fuente del residual Orgánico) |
| `BASE_INSTALLS_LIFECYCLE` | `meli-bi-data.SBOX_MKTCORPMP` | Installs mensuales por canal |
| `BT_OC_DASHBOARD_ALL_CAMPAIGNS_NR` | `meli-bi-data.SBOX_EG_MKT` | Comms_OC (detalle por comunicación) |
| `BT_OC_DASHBOARD_ALL_CAMPAIGNS_NR_ACQUISITION` | `meli-bi-data.SBOX_EG_MKT` | Comms_OC Ucrania Adquisición |

> ⚠️ Las tablas de `SBOX_EG_MKT` **no llevan prefijo de proyecto** en el SQL — usan el proyecto por defecto del ADC.

---

## Gotchas críticos

1. **Siempre correr desde la raíz del proyecto** (`MLM_ADQ_Dash/`), no desde `src/`. Si corres `python src/gen_dashboard_v1.py` estando en `src/`, fallará.

2. **El dashboard pesa ~120 MB** — no abrirlo en el browser desde el explorador de archivos local. Usar la URL de Apps Script.

3. **`data/comms_oc_current_month.json` se regenera solo** — si quieres forzar re-query del mes actual (en caso de datos stale): `del data\comms_oc_current_month.json` y volver a correr `gen_dashboard_v1.py`.

4. **El modelo de VPU cambió en Abril 2026** — datos históricos (pre-Abr-26) tienen VPU más alto (~$55-70) vs. datos nuevos (~$22-26). Esto es esperado. Ver sección §86 en `docs/History.md` y la sección correspondiente en `CLAUDE.md`.

5. **`CLAUDE.md` tiene el dueño como `sergio.ibarra@mercadolibre.com.mx`** — actualizar ese campo con tu email cuando tomes ownership completo.

---

## Checklist de validación — primer run

- [ ] Activar venv: `.\vEnv_Meli_Code1\Scripts\activate`
- [ ] Verificar auth: `gcloud auth application-default print-access-token` (debe retornar un token)
- [ ] Correr dashboard: `python src/gen_dashboard_v1.py` (debe terminar sin errores)
- [ ] Verificar que se generó `dashboard_v1.html` (debe pesar >50 MB)
- [ ] Deploy: `python src/deploy_appscript_v1.py` (debe mostrar "DEPLOY EXITOSO")
- [ ] Abrir la URL de producción en el browser y verificar que carga

---

*Documento generado el 2026-07-08. Para dudas técnicas, consultar `docs/History.md` o usar Claude Code con el contexto de `CLAUDE.md`.*
