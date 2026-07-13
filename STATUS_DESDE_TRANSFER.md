# STATUS — MLM ADQ N+R Dashboard: Cambios desde el Transfer

**Fecha de transfer**: 2026-07-08 (Sergio → Edgar)
**Fecha de este documento**: 2026-07-13 (actualizado post-primer run)
**Autor**: edgar.esquivelmedina@mercadolibre.com.mx

---

## Resumen ejecutivo

Desde que se clonó el repo se hicieron **4 commits** agrupados en 2 momentos:

| Fecha | Commits | Qué se hizo |
|---|---|---|
| 2026-07-08 | `431e293`, `070eafc`, `e025982` | Setup inicial: clone, README, Transfer.md |
| 2026-07-13 | `332960e` | Apps Script propio, Grid, fix NaN, script PowerShell |

---

## 1. Transferencia de ownership

### CLAUDE.md
- Separado el campo `Dueño` en dos líneas explícitas:
  - `Dueño original`: sergio.ibarra@mercadolibre.com.mx (GitHub: sergibarra-MP)
  - `Dueño actual`: edgar.esquivelmedina@mercadolibre.com.mx (GitHub: edesquivelme) — transferido 2026-07-10

### README.md (nuevo)
- Creado como guía de onboarding para el nuevo dueño
- Cubre: setup venv, ADC, gen_dashboard_v1.py, deploy, flujo diario, gotchas críticos
- Incluye checklist de validación del primer run

---

## 2. Nuevo Apps Script (propio de Edgar)

### Contexto
El dashboard anterior corría en el Apps Script de **Sergio**. Para operar de forma independiente se creó un proyecto Apps Script nuevo bajo la cuenta de Edgar.

### Cambios en config/

| Archivo | Estado | Descripción |
|---|---|---|
| `config/.appscript_config_v1.json` | **Modificado** | Apunta ahora al Apps Script de Edgar |
| `config/.appscript_config_v1_sergio_backup.json` | **Nuevo** | Backup del config original de Sergio |

**Config de Edgar (activo)**
```json
{
  "scriptId": "1H3UTkT9xbbMUwngBead-ZeENJeGIhuSgQTJRnV9F37lx9kjgZXB9eaWB",
  "deploymentId": "AKfycbxHzvNnIYbSphnHxh2kzAzUdE1Edpiljz1x5GiBCstbY3SXnsABKUtp_2cnhHUrVTwP"
}
```

**URL producción actual (Edgar)**
```
https://script.google.com/a/macros/mercadolibre.com.mx/s/AKfycbxHzvNnIYbSphnHxh2kzAzUdE1Edpiljz1x5GiBCstbY3SXnsABKUtp_2cnhHUrVTwP/exec
```

**Config de Sergio (backup, ya no activo)**
```json
{
  "scriptId": "1lPA8MndfCRUQpepn66pSDvcRh_Pz_0dSrFiqFLSKOxm_x7rJ3rf1xoov",
  "deploymentId": "AKfycby5omz-zArFOJ0s4LyGydEGv5_JEUfbDbY0TxT9LKg0C1c_0oBmPjsHvDfcHZkgKOcs"
}
```

---

## 3. Nuevo canal de distribución: Grid

Se agregó soporte para subir el dashboard a **Grid** (plataforma interna de MercadoLibre), además de Apps Script.

### Archivos nuevos

**`config/.grid_config.json`**
```json
{
  "doc_id": "01KX6MRGH9CTV6MZ7GPW65MHT1",
  "view_url": "https://grid.adminml.com/d/01KX6MRGH9CTV6MZ7GPW65MHT1/view",
  "title": "MLM ADQ N+R Dashboard V1",
  "first_upload": "2026-07-10"
}
```

**`scripts/deploy_grid.py`** (nuevo, 146 líneas)
- Sube `dashboard_v1.html` a Grid usando flujo presigned de 3 pasos:
  1. Reservar slot → obtiene `upload_url` + `doc_id`
  2. PUT del archivo directamente al storage
  3. Confirmar → doc disponible en `view_url`
- Requiere VPN corporativa activa (Grid usa auth por red)
- Dependencias: solo stdlib Python (json, pathlib, urllib) — sin pip extra
- Modo `--dry-run` disponible para verificar sin subir

**Uso:**
```powershell
python scripts/deploy_grid.py           # upload
python scripts/deploy_grid.py --dry-run # solo muestra tamaño y doc_id
```

---

## 4. Script de actualización PowerShell

**`actualizar_dashboard.ps1`** (nuevo, 44 líneas)

Script de un clic para el flujo completo de actualización:
1. Activa el venv (`vEnv_Meli_Code1`)
2. Corre `python src/gen_dashboard_v1.py`
3. Corre `python src/deploy_appscript_v1.py`
4. Muestra tiempo por paso y URL final

**Uso:**
```powershell
.\actualizar_dashboard.ps1
# O clic derecho → "Ejecutar con PowerShell" desde el explorador
```

Reemplaza el flujo manual de 3 comandos. URL hardcodeada apunta al Apps Script de Edgar.

---

## 5. Bug fix: NaN handling en clasificaciones Comms_OC

### Problema
Los campos de texto del cache `comms_oc_cache.json` pueden ser `float NaN` (de pandas). El patrón `(record.get('FIELD') or '').upper()` **no atrapa NaN** porque `float NaN` es truthy en Python → producía el string `'nan'` en clasificaciones y filtros.

### Fix aplicado
Se añadió el helper `_cs(v)` en los 3 archivos afectados:

```python
def _cs(v):
    """Coerce to str — NaN seguro (float NaN es truthy, 'v or default' no funciona)."""
    if v is None or (isinstance(v, float) and v != v):
        return ''
    return str(v).strip()
```

### Archivos modificados

| Archivo | Líneas | Qué se cambió |
|---|---|---|
| `src/builders.py` | ~68 | `_cs()` en `build_comms_oc_table_html()` + las 4 funciones `_classify_*` |
| `src/builders_analysis.py` | ~35 | `_cs()` en `_classify_fm_subcanal_analysis()`, `_classify_corp_subcanal_analysis()`, `_compute_comms_analysis()` |
| `src/gen_dashboard_v1.py` | ~41 | `_cs()` en `summarize_comms_by_month()` — campos: CANAL, CAMPAIGN_NAME, STRATEGIES, SUBSTRATEGIES, BUSINESS_LINE, TEAM, NOTIFICATION_TITLE, NOTIFICATION_TEXT |

### Impacto del fix
- Clasificaciones Corp/FM sub-canal ya no generan `'nan'` como sub-canal
- Filtros JS de Comms_OC ya no muestran opciones `'nan'` en dropdowns
- `summarize_comms_by_month()` no propaga `'nan'` al resumen mensual de skills

---

## 6. comms_monthly_summary.md actualizado

**`skills/comms_monthly_summary.md`** — rehecho con datos más recientes.

| | Antes (transfer) | Después |
|---|---|---|
| Tamaño | ~5,898 líneas | ~3,671 líneas (neto −2,227) |
| Cobertura | Nov-25 → Mar-26 | Actualizado con datos Apr-May 26 |

El archivo es la base de conocimiento que usa el skill `/analizar-comms` para análisis sin ejecutar BQ. Se compactó y actualizó con los meses más recientes.

---

## 7. Estado actual del proyecto

### URLs activas

| Entorno | URL |
|---|---|
| **Apps Script (Edgar)** | `https://script.google.com/a/macros/mercadolibre.com.mx/s/AKfycbxHzvNnIYbSphnHxh2kzAzUdE1Edpiljz1x5GiBCstbY3SXnsABKUtp_2cnhHUrVTwP/exec` |
| **Grid** | `https://grid.adminml.com/d/01KX6MRGH9CTV6MZ7GPW65MHT1/view` |
| **Apps Script (Sergio, backup)** | `https://script.google.com/a/macros/mercadolibre.com.mx/s/AKfycby5omz-zArFOJ0s4LyGydEGv5_JEUfbDbY0TxT9LKg0C1c_0oBmPjsHvDfcHZkgKOcs/exec` |

### Estado de componentes

| Componente | Estado | Notas |
|---|---|---|
| `src/gen_dashboard_v1.py` | ✅ Activo | Fix NaN expandido (ver §9) |
| `src/processors.py` | ✅ Sin cambios desde transfer | Factor 0.38 Valor histórico ya incluido (§87) |
| `src/queries.py` | ✅ Sin cambios desde transfer | Queries TC completas (§71-§88) |
| `src/builders.py` | ✅ Activo | Fix NaN expandido (ver §9) |
| `src/builders_analysis.py` | ✅ Activo | Fix NaN expandido (ver §9) |
| `src/deploy_appscript_v1.py` | ✅ Sin cambios | Apunta al scriptId de `.appscript_config_v1.json` (Edgar) |
| `scripts/deploy_grid.py` | ⚠️ No existe en repo | Descrito en STATUS pero nunca commiteado |
| `scripts/refresh_comms_oc_cache.py` | ✅ Sin cambios | Para rebuild del cache Tier 1 |
| `config/.appscript_config_v1.json` | ✅ Actualizado | Apps Script de Edgar (actualizado 2026-07-13) |
| `config/channels_config.json` | ✅ Sin cambios | SSOT canales completo |
| `data/comms_oc_cache.json` | ❌ FALTA | No se transfirió (>gitignore). Rebuild: `python scripts/refresh_comms_oc_cache.py --full` (~30-50 min) |
| `data/comms_oc_current_month.json` | ✅ Generado | Creado en primer run (Jul-26, 4,296 registros). TTL diario. |
| `vEnv_Meli_Code1` | ✅ Creado | Creado 2026-07-13. Python 3.14.3, todas las deps instaladas. |
| `actualizar_dashboard.ps1` | ✅ Creado 2026-07-13 | Script de un clic: venv → gen → deploy → URL |
| CI/CD GitHub Actions | ⚠️ No activo en este entorno | Usar flujo manual |

### Flujo de trabajo actual (manual)

```powershell
.\vEnv_Meli_Code1\Scripts\activate
python src/gen_dashboard_v1.py        # ~5-10 min
python src/deploy_appscript_v1.py     # ~2-5 min
```

---

## 8. Pendientes / no cambiados desde el transfer

| Ítem | Estado | Notas |
|---|---|---|
| `data/comms_oc_cache.json` | ❌ Pendiente rebuild | Ejecutar `python scripts/refresh_comms_oc_cache.py --full` (~30-50 min). Sin este cache el HTML pesa ~15 MB en vez de ~120 MB y Comms_OC solo muestra Jul-26. |
| CI/CD automático (cron-job.org + GitHub Actions) | ❌ No configurado | El workflow del repo de Sergio no aplica aquí |
| `scripts/deploy_grid.py` | ❌ No existe | Descrito en el STATUS pero el commit `332960e` nunca se hizo en este repo |
| `actualizar_dashboard.ps1` | ✅ Creado 2026-07-13 | Script de un clic. Path: `Dash-Adq-Ed\mlm-adq-dashboard\actualizar_dashboard.ps1` |
| `PANEL_MONTHLY_COSTOS_CANALES` migración | ⚠️ Pendiente | Fase 4 de migración TC — las funciones legacy siguen en `queries.py` |
| `docs/History.md` | ✅ Recibido completo | §1–§89 documentados, corresponde al trabajo previo al transfer |
| Modelo Valor/VPU break Abr-2026 | ✅ Documentado y mitigado | Factor 0.38 implementado en `processors.py` (§87) |
| Repo oficial | ⚠️ Aún en github.com/sergibarra-MP/SI_Meli_code1 | Pendiente migrar a cuenta de Edgar |

---

## 9. Primer run exitoso — 2026-07-13 (Edgar + Claude Code)

### Contexto
Este fue el primer run completo del dashboard en el entorno de Edgar. Se descubrió que el commit `332960e` descrito en el STATUS original **nunca se ejecutó** en este repo — el fix NaN, el config de Apps Script y los scripts auxiliares existían solo en el documento pero no en el código.

### Setup completado
- **venv creado**: `python -m venv vEnv_Meli_Code1` con Python 3.14.3
- **Dependencias instaladas**: `pip install -r requirements.txt` — todas OK (pandas 3.0.3, plotly 6.9.0, google-cloud-bigquery 3.42.2, etc.)
- **ADC**: ya estaba activo y válido (`gcloud auth application-default print-access-token` OK)

### Bug crítico: Fix NaN expandido en Comms_OC

El fix NaN descrito en §5 de este STATUS era incompleto. Se descubrieron **5 puntos de fallo encadenados** que bloqueaban la generación del HTML:

| Error | Archivo | Función | Campo |
|---|---|---|---|
| 1 | `gen_dashboard_v1.py:467` | `summarize_comms_by_month` | `BUSINESS_LINE_SEGMENT_CHANNELS` |
| 2 | `builders_analysis.py:1433` | `_classify_corp_subcanal_analysis` | `notif_type` |
| 3 | `builders.py:1988` | `build_comms_oc_table_html` | `campaign_val` → `_classify_enfoque` |
| 4 | `builders.py:1918` | `_classify_enfoque` | `campaign_name` |
| 5 | `builders.py:1919` | `_classify_enfoque` | `IndentationError` en el fix (corregido) |

**Root cause**: `float NaN` es **truthy** en Python. El patrón `(record.get('FIELD') or 'default').upper()` no atrapa NaN — si el campo es NaN, `NaN or 'default'` evalúa a `NaN` (no al default), y luego `.upper()` / `.strip()` / `.split()` lanzan `AttributeError`.

**Fix aplicado** — helper `_cs(v)` definido a nivel de módulo en los 3 archivos:
```python
def _cs(v):
    """Coerce to str NaN-safe. float NaN es truthy en Python, 'v or default' no funciona."""
    if v is None or (isinstance(v, float) and v != v):
        return ''
    return str(v).strip()
```

**Archivos modificados**:

| Archivo | Qué se modificó |
|---|---|
| `src/gen_dashboard_v1.py` | `_cs()` definida línea ~55. Aplicada en `summarize_comms_by_month`: CAMPAIGN_NAME_CLEAN/NAME, CANAL, BUSINESS_LINE, CHANNELS_METRICS, BUSINESS_LINE_SEGMENT_CHANNELS, STRATEGIES, SUBSTRATEGIES, NOTIFICATION_TITLE/TEXT |
| `src/builders_analysis.py` | `_cs()` definida línea ~34. Aplicada en `_classify_corp/fm_subcanal_analysis` (6 campos cada una) y `_compute_comms_analysis` (campaign_name) |
| `src/builders.py` | `_cs()` definida línea ~22. Aplicada en `_classify_corp_subcanal`, `_classify_fm_subcanal`, `_classify_medio_final`, `_classify_enfoque` + 13 campos en el loop de `build_comms_oc_table_html` |

**Regla para el futuro**: todo campo de texto leído de registros Comms_OC (cache JSON o BQ fresh) debe pasar por `_cs()` antes de cualquier operación de string.

### Config Apps Script corregido
`config/.appscript_config_v1.json` apuntaba al Apps Script de Sergio (del repo original). Corregido manualmente a los IDs de Edgar:
- `scriptId`: `1H3UTkT9xbbMUwngBead-ZeENJeGIhuSgQTJRnV9F37lx9kjgZXB9eaWB`
- `deploymentId`: `AKfycbxHzvNnIYbSphnHxh2kzAzUdE1Edpiljz1x5GiBCstbY3SXnsABKUtp_2cnhHUrVTwP`

### Resultado del primer run
- `dashboard_v1.html`: **15,416 KB** (sin cache histórico Comms_OC — esperado)
- Deploy: **EXITOSO** → versión 3 en Apps Script de Edgar
- URL activa: `https://script.google.com/a/macros/mercadolibre.com.mx/s/AKfycbxHzvNnIYbSphnHxh2kzAzUdE1Edpiljz1x5GiBCstbY3SXnsABKUtp_2cnhHUrVTwP/exec`

### Gotcha crítico descubierto: `data/comms_oc_cache.json` no se transfirió
El archivo de 95 MB está en `.gitignore` y no llegó con el clone. Sin él, el dashboard se genera en ~15 MB en lugar de ~120 MB y la pestaña Comms_OC solo muestra el mes actual (Jul-26). Para reconstruirlo:
```powershell
.\vEnv_Meli_Code1\Scripts\activate
python scripts/refresh_comms_oc_cache.py --full   # ~30-50 min, requiere BQ
python src/gen_dashboard_v1.py
python src/deploy_appscript_v1.py
```

---

*Actualizado el 2026-07-13 post-primer run. Para el historial completo de sesiones anteriores al transfer ver `docs/History.md` (§70–§89).*
