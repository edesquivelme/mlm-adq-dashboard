# MLM ADQ N+R Dashboard V1

Dashboard web interactivo de N+R (Nuevos + Recuperados) para el equipo de Analytics de Adquisición de MercadoLibre México.

Genera un HTML de ~120 MB con 10 pestañas de performance de adquisición por canal y lo sirve como web app desde Google Apps Script.

**URL de producción:**
`https://script.google.com/a/macros/mercadolibre.com.mx/s/AKfycby5omz-zArFOJ0s4LyGydEGv5_JEUfbDbY0TxT9LKg0C1c_0oBmPjsHvDfcHZkgKOcs/exec`

---

## Requisitos previos

- Python 3.10 o superior
- [Google Cloud CLI (`gcloud`)](https://cloud.google.com/sdk/docs/install) instalado
- Git instalado
- Acceso de lectura a BigQuery en `meli-bi-data` (datasets: `SBOX_EG_MKT`, `SBOX_MARKETING`, `SBOX_MKTCORPMP`, `WHOWNER`)
- Acceso de **Editor** al proyecto Apps Script `MLM ADQ N+R Dashboard v1` (pedírselo a Sergio)

---

## Paso 0 — Pedir accesos (antes de empezar)

Necesitas que el dueño del proyecto haga **2 cosas**:

**a) Acceso al proyecto Apps Script**

El dueño abre [script.google.com/home](https://script.google.com/home), abre el proyecto `MLM ADQ N+R Dashboard v1`, clic en el ícono de personas → `Compartir` → agrega tu email con rol **Editor**.

Sin esto, el deploy falla con error 403.

**b) Verificar tu acceso a BigQuery**

Confirmar con el equipo de datos que tu cuenta `@mercadolibre.com.mx` tiene permisos de lectura en los datasets listados arriba.

---

## Paso 1 — Clonar el repositorio

```powershell
git clone https://github.com/sergibarra-MP/SI_Meli_code1.git
cd SI_Meli_code1\MLM_ADQ_Dash
```

> **Importante:** todo se corre desde la carpeta `MLM_ADQ_Dash/`. Si corres los scripts desde `src/` fallará.

---

## Paso 2 — Crear entorno virtual e instalar dependencias

```powershell
# Desde MLM_ADQ_Dash/
python -m venv vEnv_Meli_Code1

# Activar (Windows)
.\vEnv_Meli_Code1\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

---

## Paso 3 — Configurar credenciales Google (ADC)

Este es el paso más importante. El proyecto usa **Application Default Credentials (ADC)** — tus credenciales personales de Google. Las librerías Python (`google-cloud-bigquery`, `google-auth`, `deploy_appscript_v1.py`) las leen automáticamente desde un archivo local en tu máquina.

### Cómo funciona el sistema de credenciales

El proyecto usa **dos sistemas de credenciales independientes**. Es importante no confundirlos:

| Componente | Sistema | Identidad | Archivo |
|---|---|---|---|
| `bigquery.Client()` en Python | **ADC** (usuario personal) | tu cuenta `@mercadolibre.com.mx` | `AppData\Roaming\gcloud\application_default_credentials.json` |
| `deploy_appscript_v1.py` | **ADC** (usuario personal) | tu cuenta `@mercadolibre.com.mx` | mismo archivo |
| Comando `gcloud` en terminal | Config gcloud (service account) | cuenta de servicio del proyecto | `AppData\Roaming\gcloud\configurations\config_default` |

> **Nota clave:** las librerías Python **solo leen el archivo ADC**, no la configuración de `gcloud`. Son sistemas separados. El comando `gcloud config list` puede mostrar una service account — eso es normal e independiente.

### Generar tu archivo ADC

Ejecuta este comando exacto (todos los scopes son necesarios):

```powershell
gcloud auth application-default login --scopes="https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/script.projects,https://www.googleapis.com/auth/script.deployments,https://www.googleapis.com/auth/drive.file"
```

Se abrirá el browser. Autoriza con tu cuenta `@mercadolibre.com.mx`.

Esto genera el archivo:
```
C:\Users\[tu_usuario]\AppData\Roaming\gcloud\application_default_credentials.json
```

El archivo tiene esta estructura:

```json
{
  "type": "authorized_user",
  "quota_project_id": "meli-bi-data",
  "refresh_token": "..."
}
```

> ⚠️ **Nunca compartas este archivo.** Está atado a tu refresh token personal. Cada persona del equipo debe generar el suyo con el comando anterior.

### Verificar que funcionó

```powershell
gcloud auth application-default print-access-token
```

Debe imprimir un token largo. Si da error, el login no funcionó — vuelve a correr el comando de login.

> **Scopes incompletos:** si corres `gcloud auth application-default login` sin `--scopes`, BigQuery funcionará pero el deploy a Apps Script fallará con error de permisos insuficientes.

---

## Paso 4 — Generar el dashboard

```powershell
# Con el venv activado, desde MLM_ADQ_Dash/
python src/gen_dashboard_v1.py
```

Qué hace:
1. Consulta BigQuery (~5–15 min según cuotas)
2. Lee el plan de negocio de `data/Resumen Plan Acq 2026.xlsx`
3. Carga el cache de Comms_OC de `data/comms_oc_cache.json`
4. Genera `dashboard_v1.html` (~120 MB) en la raíz del proyecto

Output esperado al final:
```
>>> Paso 4: Ensamblando HTML Final...
  OK: dashboard_v1.html generado (XXXXX KB)
```

Si BigQuery excede cuota, el script reintenta automáticamente 3 veces con 120s de espera.

---

## Paso 5 — Subir a Apps Script (deploy)

```powershell
python src/deploy_appscript_v1.py
```

Output esperado:
```
DEPLOY EXITOSO - ENTORNO V1
URL permanente: https://script.google.com/a/macros/...
```

La URL no cambia con cada deploy — es un deployment fijo.

> Si falla con **403**: verifica que tengas acceso Editor al proyecto Apps Script (Paso 0a).
> Si falla con **error SSL**: el script reintenta 3 veces automáticamente (payload de ~120 MB).

---

## Flujo de trabajo regular

```powershell
# Activar venv (si no está activo)
.\vEnv_Meli_Code1\Scripts\activate

# Generar y subir
python src/gen_dashboard_v1.py       # ~10-15 min
python src/deploy_appscript_v1.py    # ~2-5 min
```

### Una vez por mes — actualizar cache de Comms_OC

El archivo `data/comms_oc_cache.json` contiene el histórico de comunicaciones OC. Al inicio de cada mes nuevo, agregar el mes cerrado:

```powershell
# Incremental (~2-5 min) — usa esto normalmente
python scripts/refresh_comms_oc_cache.py

# Solo si el cache se corrompe o necesitas reconstruir desde cero (~30-50 min)
python scripts/refresh_comms_oc_cache.py --full
```

---

## Estructura del proyecto

```
MLM_ADQ_Dash/
├── README.md                    ← Este archivo
├── CLAUDE.md                    ← Contexto maestro para Claude Code
├── Transfer.md                  ← Guía de transferencia detallada
├── requirements.txt             ← Dependencias Python
│
├── src/
│   ├── gen_dashboard_v1.py      ← Motor principal — orquesta todo
│   ├── queries.py               ← SQL dinámico para BigQuery
│   ├── processors.py            ← Consulta BQ, procesa DataFrames
│   ├── builders.py              ← Genera HTML de tablas + charts
│   ├── builders_analysis.py     ← Genera pestaña Análisis OC+UCR
│   ├── template_dashboard.html  ← Template HTML con {{PLACEHOLDERS}}
│   ├── dashboard.css            ← Estilos
│   └── deploy_appscript_v1.py  ← Sube el HTML a Google Apps Script
│
├── config/
│   ├── channels_config.json     ← SSOT: jerarquía de canales, colores, mapeos BQ
│   ├── .appscript_config_v1.json ← scriptId + deploymentId de Apps Script
│   ├── comms_classification_config.json
│   ├── reporting_methodology.md
│   └── queries/                 ← Documentación SQL de referencia
│
├── data/
│   ├── Resumen Plan Acq 2026.xlsx  ← Plan de negocio (metas por canal)
│   ├── comms_oc_cache.json         ← Cache histórico Comms_OC (~95 MB)
│   └── comms_oc_cache_meta.json
│   [comms_oc_current_month.json]   ← Se genera automáticamente en el primer run
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
└── docs/
    ├── metrics_logic.md         ← Fuente de verdad de KPIs y fórmulas
    ├── NR_impact_methodology.md
    └── History.md               ← Historial de cambios (§1–§89+)
```

> `dashboard_v1.html` no está en el repo (pesa ~120 MB). Se genera localmente con `gen_dashboard_v1.py`.

---

## Gotchas críticos

1. **Siempre correr desde `MLM_ADQ_Dash/`**, no desde `src/`.

2. **El dashboard pesa ~120 MB** — no abrirlo desde el explorador de archivos. Usar la URL de Apps Script.

3. **`data/comms_oc_current_month.json` se regenera automáticamente.** Para forzar re-query del mes actual:
   ```powershell
   del data\comms_oc_current_month.json
   ```

4. **El modelo de VPU cambió en Abril 2026.** Datos históricos pre-Abr-26 muestran VPU ~$55–70 (modelo viejo). Datos Abr-26 en adelante muestran ~$22–26 (modelo nuevo "Fact Based"). Esto es esperado — hay un factor de normalización 0.38 aplicado en el código. Ver `CLAUDE.md §Modelo Valor` para detalles.

5. **Tu archivo ADC es personal.** No puedes compartir `application_default_credentials.json` — está atado a tu refresh token. Cada miembro del equipo genera el suyo con el comando del Paso 3.

---

## Checklist primer run

- [ ] Acceso Editor al proyecto Apps Script pedido (Paso 0a)
- [ ] Acceso BigQuery confirmado (Paso 0b)
- [ ] Repo clonado
- [ ] venv creado y activado
- [ ] `pip install -r requirements.txt` completado
- [ ] `gcloud auth application-default login --scopes="..."` ejecutado con todos los scopes
- [ ] `gcloud auth application-default print-access-token` retorna un token
- [ ] `python src/gen_dashboard_v1.py` termina sin errores y genera `dashboard_v1.html` (>50 MB)
- [ ] `python src/deploy_appscript_v1.py` muestra "DEPLOY EXITOSO"
- [ ] URL de producción carga en el browser

---

## Apps Script — referencia

| Campo | Valor |
|---|---|
| Nombre del proyecto | MLM ADQ N+R Dashboard v1 |
| Script ID | `1lPA8MndfCRUQpepn66pSDvcRh_Pz_0dSrFiqFLSKOxm_x7rJ3rf1xoov` |
| Deployment ID | `AKfycby5omz-zArFOJ0s4LyGydEGv5_JEUfbDbY0TxT9LKg0C1c_0oBmPjsHvDfcHZkgKOcs` |
| URL pública | `https://script.google.com/a/macros/mercadolibre.com.mx/s/AKfycby5omz-zArFOJ0s4LyGydEGv5_JEUfbDbY0TxT9LKg0C1c_0oBmPjsHvDfcHZkgKOcs/exec` |

---

## Fuentes de datos BigQuery

| Tabla | Dataset | Qué contiene |
|---|---|---|
| `BT_OC_NR_REPORTE_TORRE_DAILY` | `meli-bi-data.SBOX_EG_MKT` | N+R y costos de Own Channels (lift-based) |
| `BT_MP_INDIVIDUALS_PERFORMANCE` | `meli-bi-data.SBOX_MARKETING` | N+R y costos de canales Paid (POM, MGM, L&P) |
| `BT_MP_USER_ENGAGEMENT_INAPP` | `meli-bi-data.SBOX_MARKETING` | Total N+R in-app (fuente del residual Orgánico) |
| `BASE_INSTALLS_LIFECYCLE` | `meli-bi-data.SBOX_MKTCORPMP` | Installs mensuales por canal |
| `BT_OC_DASHBOARD_ALL_CAMPAIGNS_NR` | `meli-bi-data.SBOX_EG_MKT` | Comms_OC detalle por comunicación |
| `BT_OC_DASHBOARD_ALL_CAMPAIGNS_NR_ACQUISITION` | `meli-bi-data.SBOX_EG_MKT` | Comms_OC Ucrania Adquisición |

> ⚠️ Las tablas de `SBOX_EG_MKT` no llevan prefijo de proyecto en el SQL — usan el proyecto por defecto del ADC.

---

## Usar Claude Code con este proyecto

Este proyecto usa Claude Code como asistente de desarrollo. El archivo `CLAUDE.md` es el contexto maestro que Claude lee automáticamente al abrir el proyecto.

**Comandos slash disponibles:**

| Comando | Qué hace |
|---|---|
| `/analizar-oc-pom` | Analiza performance de canales OC+UCR y POM |
| `/analizar-comms` | Analiza comunicaciones OC desde Comms_OC |
| `/optimizar-oc` | Optimizador de presupuesto y estrategia OC |
| `/deploy` | Genera y despliega el dashboard |
| `/refresh` | Dispara actualización manual vía GitHub Actions |

**Primera sesión recomendada con Claude:**
```
Lee el CLAUDE.md y dame un resumen del estado actual del proyecto y las 3 cosas más importantes que debo saber como nuevo dueño del dashboard.
```
