"""
Script de diagnóstico: encuentra el Script ID real y deployments del proyecto
'MLM ADQ N+R Dashboard v1'. No modifica nada.

INSTRUCCIONES:
  1. Abre script.google.com → abre el proyecto 'MLM ADQ N+R Dashboard v1'
  2. Clic en el ícono de engranaje (⚙️ Configuración del proyecto)
  3. Copia el campo "ID del script" y pégalo en SCRIPT_ID abajo
  4. Corre: python scripts/discover_deployment.py

Run desde MLM_ADQ_Dash/:
    python scripts/discover_deployment.py
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import google.auth
from google.auth.transport.requests import Request as GoogleRequest
from googleapiclient.discovery import build

REQUIRED_SCOPES = [
    'https://www.googleapis.com/auth/cloud-platform',
    'https://www.googleapis.com/auth/script.projects',
    'https://www.googleapis.com/auth/script.deployments',
]

# ─── PON AQUÍ EL ID DEL SCRIPT (desde ⚙️ Configuración del proyecto) ───────
SCRIPT_ID = '1lPA8MndfCRUQpepn66pSDvcRh_Pz_0dSrFiqFLSKOxm_x7rJ3rf1xoov'
# ─────────────────────────────────────────────────────────────────────────────

def main():
    if not SCRIPT_ID:
        print("ERROR: Completa el campo SCRIPT_ID en este script.")
        print("  1. Ve a script.google.com → abre 'MLM ADQ N+R Dashboard v1'")
        print("  2. Clic en ⚙️ → copia 'ID del script'")
        print("  3. Pégalo en SCRIPT_ID = '' arriba")
        sys.exit(1)

    creds, _ = google.auth.default(scopes=REQUIRED_SCOPES)
    creds.refresh(GoogleRequest())
    print(f"Auth OK: {getattr(creds, 'service_account_email', 'user account')}")

    service = build('script', 'v1', credentials=creds, cache_discovery=False)

    # Info del proyecto
    proj = service.projects().get(scriptId=SCRIPT_ID).execute()
    print(f"\nProyecto : {proj.get('title')}")
    print(f"scriptId : {proj.get('scriptId')}")

    # Versiones
    v_resp   = service.projects().versions().list(scriptId=SCRIPT_ID).execute()
    versions = v_resp.get('versions', [])
    print(f"\nVersiones ({len(versions)}/200):")
    for v in sorted(versions, key=lambda x: x['versionNumber'], reverse=True)[:5]:
        print(f"  v{v['versionNumber']} — {v.get('description','(sin desc)')}")

    # Deployments
    d_resp      = service.projects().deployments().list(scriptId=SCRIPT_ID).execute()
    deployments = d_resp.get('deployments', [])
    print(f"\nDeployments ({len(deployments)}):")
    for d in deployments:
        dep_id = d.get('deploymentId')
        cfg    = d.get('deploymentConfig', {})
        desc   = cfg.get('description', '(sin desc)')
        ver    = cfg.get('versionNumber', '?')
        url    = f"https://script.google.com/a/macros/mercadolibre.com.mx/s/{dep_id}/exec"
        print(f"\n  deploymentId : {dep_id}")
        print(f"  descripcion  : {desc}")
        print(f"  version      : v{ver}")
        print(f"  URL          : {url}")

    print("\n" + "="*60)
    print("Con estos datos actualiza config/.appscript_config_v1.json")
    print("="*60)

if __name__ == '__main__':
    main()
