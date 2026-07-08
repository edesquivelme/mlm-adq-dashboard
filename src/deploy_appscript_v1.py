#!/usr/bin/env python3
"""
deploy_appscript_v1.py — Sube dashboard_v1.html a Google Apps Script (Entorno V1)

Flujo:
  1. OAuth (usa ADC de gcloud)
  2. Lee scriptId y deploymentId de config/.appscript_config_v1.json
  3. Sube Code.gs + dashboard_v1.html como index.html al proyecto
  4. Crea version nueva
  5. Actualiza deployment → URL permanente

Run (desde la raíz del proyecto):
    python src/deploy_appscript_v1.py
"""

import sys, os, json
sys.stdout.reconfigure(encoding='utf-8')

import google.auth
from google.auth.transport.requests import Request as GoogleRequest
from googleapiclient.discovery import build

# ═══════════════════════════════════════════════════════════════
# 1. CONFIGURACIÓN Y RUTAS (Dinámicas)
# ═══════════════════════════════════════════════════════════════
# BASE_DIR es la carpeta 'src/' donde vive este script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# PROJECT_ROOT sube un nivel para llegar a la raíz del proyecto (MLM_ADQ_Dash)
PROJECT_ROOT = os.path.dirname(BASE_DIR)

# Mapeo a las ubicaciones reales de la arquitectura V1
DASHBOARD = os.path.join(PROJECT_ROOT, 'dashboard_v1.html')
CFG_FILE  = os.path.join(PROJECT_ROOT, 'config', '.appscript_config_v1.json')

PROJECT_TITLE = 'MLM ADQ N+R Dashboard v1'

REQUIRED_SCOPES = [
    'https://www.googleapis.com/auth/cloud-platform',
    'https://www.googleapis.com/auth/script.projects',
    'https://www.googleapis.com/auth/script.deployments',
    'https://www.googleapis.com/auth/drive.file',
]

GCLOUD_CMD = (
    'gcloud auth application-default login --scopes='
    '"https://www.googleapis.com/auth/cloud-platform,'
    'https://www.googleapis.com/auth/script.projects,'
    'https://www.googleapis.com/auth/script.deployments,'
    'https://www.googleapis.com/auth/drive.file"'
)

CODE_GS_TEMPLATE = '''\
// Apps Script: solo sirve el HTML estático generado por Python.
// Entorno V1. Actualizado vía gen_dashboard_v1.py + deploy_appscript_v1.py.
function doGet() {
  return HtmlService.createHtmlOutputFromFile('index')
    .setTitle('MLM ADQ N+R Dashboard v1')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}
'''

def make_code_gs(dep_id=None):
    return CODE_GS_TEMPLATE

# ═══════════════════════════════════════════════════════════════
# AUTH
# ═══════════════════════════════════════════════════════════════
def get_credentials():
    try:
        creds, _ = google.auth.default(scopes=REQUIRED_SCOPES)
        creds.refresh(GoogleRequest())
        print(f"Credenciales ADC OK: {getattr(creds, 'service_account_email', 'user account')}")
        return creds
    except google.auth.exceptions.DefaultCredentialsError:
        print("\nERROR: No se encontraron Application Default Credentials.")
        print("\nEjecuta este comando (abre el navegador para autorizar):\n")
        print(f"  {GCLOUD_CMD}\n")
        sys.exit(1)
    except Exception as e:
        err = str(e)
        if 'invalid_grant' in err or 'unauthorized' in err.lower() or 'scope' in err.lower():
            print("\nERROR: Las credenciales ADC no tienen los scopes de Apps Script.")
            print("\nEjecuta este comando UNA SOLA VEZ (abre el navegador):\n")
            print(f"  {GCLOUD_CMD}\n")
            print("Luego vuelve a ejecutar: python src/deploy_appscript_v1.py")
            sys.exit(1)
        raise

def get_service(creds):
    return build('script', 'v1', credentials=creds, cache_discovery=False)

def create_project(service, title):
    print(f"Creando proyecto Apps Script: '{title}'...")
    result = service.projects().create(body={'title': title}).execute()
    script_id = result['scriptId']
    print(f"  OK: scriptId = {script_id}")
    return script_id

# Ojo: No usar json.dumps directo como argumento por defecto, se define string json crudo o variable
APPSSCRIPT_MANIFEST = json.dumps({
    "timeZone": "America/Mexico_City",
    "dependencies": {
        "enabledAdvancedServices": [
            {"userSymbol": "BigQuery", "serviceId": "bigquery", "version": "v2"}
        ]
    },
    "exceptionLogging": "STACKDRIVER",
    "runtimeVersion": "V8",
    "webapp": {
        "executeAs": "USER_ACCESSING",
        "access": "DOMAIN"
    }
}, indent=2)

def update_files(service, script_id, html_content, dep_id=''):
    """Sube archivos al proyecto Apps Script con reintento en SSLWantWriteError.

    Para payloads de ~114 MB en Windows, el SSL socket puede fallar a mitad
    del envío con SSLWantWriteError.  La sesión queda en estado roto y
    requests no reintenta por sí solo.  Estrategia:
      1. Pre-serializar el body UNA sola vez (evita re-serializar en cada reintento)
      2. Crear sesión SSL fresca en cada intento (nueva conexión, nuevo handshake)
      3. Hasta 3 intentos con backoff lineal (10s, 20s)
    """
    import json as _json
    import time
    import google.auth
    import google.auth.transport.requests as _ga_requests
    import requests as _req

    print("Subiendo archivos al proyecto V1...")
    body = {
        'files': [
            {'name': 'appsscript', 'type': 'JSON', 'source': APPSSCRIPT_MANIFEST},
            {'name': 'Code', 'type': 'SERVER_JS', 'source': make_code_gs(dep_id)},
            {'name': 'index', 'type': 'HTML', 'source': html_content},
        ]
    }

    url        = f'https://script.googleapis.com/v1/projects/{script_id}/content'
    body_bytes = _json.dumps(body).encode('utf-8')   # serializar una sola vez

    MAX_RETRIES = 3
    resp = None
    for attempt in range(MAX_RETRIES):
        try:
            # Sesión fresca cada intento — evita reutilizar un SSL socket roto
            creds, _ = google.auth.default(scopes=REQUIRED_SCOPES)
            session  = _ga_requests.AuthorizedSession(creds)
            resp = session.put(
                url,
                data=body_bytes,
                headers={'Content-Type': 'application/json'},
                timeout=300,
            )
            break  # éxito — salir del loop
        except _req.exceptions.SSLError as exc:
            if attempt == MAX_RETRIES - 1:
                raise
            wait = 10 * (attempt + 1)
            print(f"  ⚠ SSL write error (intento {attempt+1}/{MAX_RETRIES}), reintentando en {wait}s...")

    if resp.status_code == 404:
        raise FileNotFoundError(
            f"Proyecto Apps Script no encontrado (scriptId={script_id}). "
            "El proyecto fue eliminado. Se creará uno nuevo automáticamente."
        )
    if not resp.ok:
        raise RuntimeError(
            f"updateContent falló {resp.status_code}: {resp.text[:400]}"
        )
    print("  OK: archivos subidos")

VERSION_WARN_THRESHOLD = 180   # avisar cuando queden solo 20 slots
VERSION_HARD_LIMIT     = 199   # no intentar crear si ya estamos en el límite


def check_version_count(service, script_id):
    """Retorna el número de versiones actuales y el número de la más reciente.
    La Apps Script API v1 NO permite borrar versiones via API — solo desde la UI.
    Cuando se acerque al límite se imprime una advertencia accionable.
    """
    try:
        resp     = service.projects().versions().list(scriptId=script_id).execute()
        versions = resp.get('versions', [])
        count    = len(versions)
        latest   = max((v['versionNumber'] for v in versions), default=None)
    except Exception as e:
        print(f"  WARN: no se pudo consultar versiones: {e}")
        return 0, None

    if count >= VERSION_WARN_THRESHOLD:
        print(f"\n  ⚠️  ATENCIÓN: {count}/200 versiones usadas en este proyecto Apps Script.")
        print( "  Borra versiones antiguas manualmente para evitar que el deploy falle:")
        print( "  1. Abre https://script.google.com/home")
        print( "  2. Abre el proyecto → menú ⋮ → Historial de versiones")
        print( "  3. Selecciona y elimina versiones antiguas (deja las últimas ~10)\n")
    else:
        print(f"  Versiones Apps Script: {count}/200")

    return count, latest


def create_version(service, script_id, description):
    result = service.projects().versions().create(
        scriptId=script_id, body={'description': description}
    ).execute()
    version_num = result['versionNumber']
    print(f"  OK: version {version_num} creada")
    return version_num

def create_deployment(service, script_id, version_num, title):
    print("Creando deployment (web app)...")
    result = service.projects().deployments().create(
        scriptId=script_id,
        body={
            'versionNumber': version_num,
            'manifestFileName': 'appsscript',
            'description': title,
        }
    ).execute()
    dep_id  = result['deploymentId']
    web_url = f"https://script.google.com/a/macros/mercadolibre.com.mx/s/{dep_id}/exec"
    print(f"  OK: deploymentId = {dep_id}")
    return dep_id, web_url

def update_deployment(service, script_id, dep_id, version_num, description):
    print(f"Actualizando deployment {dep_id} -> version {version_num}...")
    service.projects().deployments().update(
        scriptId=script_id,
        deploymentId=dep_id,
        body={
            'deploymentConfig': {
                'versionNumber': version_num,
                'manifestFileName': 'appsscript',
                'description': description,
            }
        }
    ).execute()
    print("  OK: deployment actualizado")

# ═══════════════════════════════════════════════════════════════
# MAIN DEPLOY FLOW V1
# ═══════════════════════════════════════════════════════════════
def deploy():
    if not os.path.exists(DASHBOARD):
        print(f"ERROR: No se encontro {DASHBOARD}")
        print("Ejecuta primero: python src/gen_dashboard_v1.py")
        sys.exit(1)

    with open(DASHBOARD, 'r', encoding='utf-8') as f:
        html_content = f.read()
    size_kb = len(html_content) / 1024
    print(f"dashboard_v1.html cargado: {size_kb:.0f} KB")

    creds   = get_credentials()
    service = get_service(creds)
    print("Apps Script API: conectado")

    # Lectura del archivo desde la carpeta /config
    if os.path.exists(CFG_FILE):
        with open(CFG_FILE) as f:
            cfg = json.load(f)
        script_id = cfg['scriptId']
        dep_id    = cfg.get('deploymentId')
        print(f"Proyecto V1 existente: scriptId={script_id}")
    else:
        print(f"AVISO: No se encontro {CFG_FILE}. Creando proyecto nuevo...")
        script_id = create_project(service, PROJECT_TITLE)
        dep_id    = None
        cfg = {'scriptId': script_id}
        # Asegura que la carpeta config exista por si acaso
        os.makedirs(os.path.dirname(CFG_FILE), exist_ok=True)
        with open(CFG_FILE, 'w') as f:
            json.dump(cfg, f, indent=2)

    try:
        update_files(service, script_id, html_content, dep_id or '')
    except FileNotFoundError as e:
        print(f"\n  AVISO: {e}")
        print("  Creando proyecto Apps Script nuevo...")
        script_id = create_project(service, PROJECT_TITLE)
        dep_id    = None
        cfg = {'scriptId': script_id}
        os.makedirs(os.path.dirname(CFG_FILE), exist_ok=True)
        with open(CFG_FILE, 'w') as f:
            json.dump(cfg, f, indent=2)
        print(f"  Config actualizado: {CFG_FILE}")
        update_files(service, script_id, html_content, dep_id or '')

    import datetime
    desc = f"Dashboard V1 actualizado {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"

    # Verificar límite de versiones (API no permite borrar — solo avisa)
    version_count, latest_version = check_version_count(service, script_id)

    if version_count >= VERSION_HARD_LIMIT:
        # Límite alcanzado: reutilizar la última versión existente
        # El HTML subido a HEAD no se sirve hasta que se limpien versiones manualmente
        print(f"  ⛔ Límite de versiones alcanzado. Reutilizando versión {latest_version}.")
        print( "  ➡  Borra versiones desde la UI de Apps Script para recuperar deploy completo.")
        version_num = latest_version
    else:
        version_num = create_version(service, script_id, desc)

    if dep_id:
        update_deployment(service, script_id, dep_id, version_num, desc)
        web_url = f"https://script.google.com/a/macros/mercadolibre.com.mx/s/{dep_id}/exec"
    else:
        dep_id, web_url = create_deployment(service, script_id, version_num, PROJECT_TITLE)
        cfg['deploymentId'] = dep_id
        with open(CFG_FILE, 'w') as f:
            json.dump(cfg, f, indent=2)

    print("\n" + "="*60)
    print("DEPLOY EXITOSO - ENTORNO V1")
    print("="*60)
    print(f"  URL permanente: {web_url}")
    print("="*60)
    return web_url

if __name__ == '__main__':
    deploy()