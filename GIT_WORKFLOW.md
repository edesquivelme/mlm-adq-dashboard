# GIT_WORKFLOW.md — MLM ADQ N+R Dashboard

Guía operativa del flujo Git para actualización y sincronización del dashboard.

---

## Contexto del setup (completado el 13-Jul-2026)

- **Fork creado**: repo original de Sergio → cuenta de Edgar (`edesquivelme`)
- **Repo activo**: `https://github.com/edesquivelme/mlm-adq-dashboard.git`
- **Rama de trabajo**: `main` (rama única — no hay branches adicionales)
- **Carpeta local correcta**: `C:\Edgar_Field_MP\Dashboards\Dash-Adq-Ed\mlm-adq-dashboard\`

---

## Ciclo diario — Actualizar dashboard

**Paso 1 — Generar y deployar** (PowerShell, desde la raíz del proyecto):
```powershell
.\actualizar_dashboard.ps1
```
Hace dos cosas: genera `dashboard_v1.html` consultando BigQuery y lo sube a Apps Script. Tarda ~10-15 min.

**Paso 2 — Validar que la actualización fue exitosa:**
- Abrir el dashboard y verificar que D-1, D-2 y D-3 muestran datos distintos entre sí
- Si los totales no cambian entre días → algo falló en BQ
- Si el HTML pesa < 50KB → el deploy fue bloqueado automáticamente (guardia de seguridad)

---

## Ciclo git — Sincronizar cambios al repositorio

Correr en la terminal después de cada actualización del dashboard:

```bash
git add .
git commit -m "Actualización dashboard YYYY-MM-DD"
git push origin main
```

- `git add .` → prepara todos los archivos modificados
- `git commit -m "..."` → registra el cambio con un mensaje descriptivo
- `git push origin main` → sube al GitHub de Edgar

**Señal de que hay cambios sin subir**: el ícono de fork en VS Code muestra un número — significa que la versión local y GitHub no están sincronizadas.

---

## Para otros miembros del equipo (Cami, Vic)

**Quién hace qué**: Edgar comparte la URL de su repo. El nuevo miembro hace todo lo demás en su propia computadora.

**Setup único — en este orden:**

**① En el navegador** — crear cuenta GitHub:
- Ir a github.com → Sign up con correo `@mercadolibre.com.mx`

**② En el navegador** — hacer fork del repo de Edgar:
- Abrir `https://github.com/edesquivelme/mlm-adq-dashboard`
- Clic en **Fork** → **Create fork** (queda en su propia cuenta de GitHub)

**③ En la terminal** (Git Bash o PowerShell) — configurar identidad y clonar:
```bash
git config --global user.name "Tu Nombre"
git config --global user.email "tu@mercadolibre.com.mx"
git clone https://github.com/<su-usuario>/mlm-adq-dashboard.git
```

**④ En la terminal** — instalar dependencias Python:
```bash
cd mlm-adq-dashboard
python -m venv vEnv_Meli_Code1
.\vEnv_Meli_Code1\Scripts\pip install -r requirements.txt
```

**Para bajar la última versión** (después del setup, cuando Edgar ya subió cambios):
```bash
# En la terminal, dentro de la carpeta mlm-adq-dashboard
git pull origin main
```
Luego correr `.\actualizar_dashboard.ps1` normalmente.

---

## Troubleshooting

| Síntoma | Causa probable | Fix |
|---|---|---|
| `Permission denied (403)` en push | Credenciales de otra cuenta cacheadas | Limpiar caché de credenciales Windows + re-autenticar con cuenta @mercadolibre |
| Dashboard < 50KB generado | BQ falló en alguna query | Revisar output del script, re-correr |
| D-1/D-2/D-3 sin cambio en datos | BQ sin datos nuevos o error silencioso | Revisar logs en terminal |
| Push exitoso pero GitHub no actualiza | Demora normal | Refrescar la página del repo en el navegador |
| `comms_oc_cache.json` not found | Cache Tier 1 faltante | Correr: `.\vEnv_Meli_Code1\Scripts\python.exe scripts/refresh_comms_oc_cache.py --full` (~30-50 min, no requiere Claude) |
