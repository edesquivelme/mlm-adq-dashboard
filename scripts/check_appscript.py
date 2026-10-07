#!/usr/bin/env python3
"""
check_appscript.py — Verificaciones de solo lectura contra la API de Apps Script.

Modos:
  --probe   Antes de generar. Mintea el token ADC y hace GET del proyecto.
            200 => el deploy va a pasar. 403 => ADC sin scopes de Apps Script
            (re-autenticar con los 2 comandos que imprime). Leer el JSON del ADC
            NO sirve para saberlo: los scopes viven en el refresh token.
  --verify  Despues del deploy. Lee el deployment activo y confirma la version
            servida y entryPointConfig == {access: DOMAIN, executeAs: USER_DEPLOYING}.
            Si un refactor revierte executeAs, parte del equipo vuelve a ver
            "No tienes acceso a esta aplicacion web" y Google no dice por que.

Exit codes: 0 OK · 2 credenciales/scopes · 3 config del web app distinta a la esperada.

Run (desde la raiz del proyecto):
    python scripts/check_appscript.py --probe
    python scripts/check_appscript.py --verify
"""

import sys, os, json
sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))
from deploy_appscript_v1 import REQUIRED_SCOPES, CFG_FILE, GCLOUD_CMD

import google.auth
from google.auth.transport.requests import Request as GoogleRequest, AuthorizedSession

API = 'https://script.googleapis.com/v1/projects'
EXPECTED_WEBAPP = {'access': 'DOMAIN', 'executeAs': 'USER_DEPLOYING'}
QUOTA_CMD = 'gcloud auth application-default set-quota-project meli-bi-data'


def session():
    creds, _ = google.auth.default(scopes=REQUIRED_SCOPES)
    creds.refresh(GoogleRequest())
    return AuthorizedSession(creds)


def fail_auth(resp):
    print(f"ERROR ADC: la API de Apps Script respondio {resp.status_code}")
    print(f"  {resp.text[:300]}")
    print("  Re-autenticar (siempre los dos, en orden):")
    print(f"    1. {GCLOUD_CMD}")
    print(f"    2. {QUOTA_CMD}")
    sys.exit(2)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ''
    if mode not in ('--probe', '--verify'):
        print(__doc__)
        sys.exit(1)

    with open(CFG_FILE) as f:
        cfg = json.load(f)
    script_id, dep_id = cfg['scriptId'], cfg.get('deploymentId')

    s = session()

    if mode == '--probe':
        r = s.get(f"{API}/{script_id}")
        if r.status_code != 200:
            fail_auth(r)
        print("ADC OK: Apps Script API responde 200")
        return

    r = s.get(f"{API}/{script_id}/deployments/{dep_id}")
    if r.status_code != 200:
        fail_auth(r)
    d = r.json()
    version = d.get('deploymentConfig', {}).get('versionNumber')
    webapp = next((ep.get('webApp', {}) for ep in d.get('entryPoints', [])
                   if ep.get('entryPointType') == 'WEB_APP'), {})
    conf = webapp.get('entryPointConfig', {})
    print(f"VERSION={version}")
    print(f"WEBAPP={json.dumps(conf)}")
    if conf != EXPECTED_WEBAPP:
        print(f"ERROR: config del web app distinta a la esperada {json.dumps(EXPECTED_WEBAPP)}")
        sys.exit(3)
    print("Web app OK: access DOMAIN, executeAs USER_DEPLOYING")


if __name__ == '__main__':
    main()
