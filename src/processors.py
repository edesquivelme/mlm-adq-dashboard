"""
processors.py — Procesamiento de datos para MLM ADQ Dashboard V1
═════════════════════════════════════════════════════════════════
CONEXIONES:
  · Entrada  : config/channels_config.json (vía parámetro 'config')
               └─ config['hierarchy_nr']   → HIERARCHY_NR
               └─ config['hierarchy_cost'] → HIERARCHY_C
  · Llama a  : queries.py → get_nr_tc_sql (TC), get_costos_sql, get_perf_paid_sql, get_perf_vpu_sql
  · Salida   : dict 'data' con todos los datos procesados
               └─ consumido por builders.py → build_*()
               └─ consumido por gen_dashboard_v1.py → data_js (payload JS del dashboard)

CONVENCIÓN DE NOMBRES:
  HIERARCHY_NR  = config['hierarchy_nr']   (canales N+R — fuente TC §71)
  HIERARCHY_C   = config['hierarchy_cost'] (canales Costos, fuente COSTOS_CANALES)
"""

import os
import json
import time
import pandas as pd
from queries import (
    get_nr_tc_sql,                             # TC §71: reemplaza get_nr_sql
    get_vpu_tc_sql,                            # TC §71: reemplaza get_perf_vpu_sql
    get_costos_tc_sql,                         # TC §71: reemplaza get_costos_sql
    get_perf_paid_tc_sql,                      # TC §71: reemplaza get_perf_paid_sql
    get_roa_tc_sql,                            # TC §71: reemplaza get_perf_roa_costos_sql
    get_nr_corp_tc_sql, get_nr_corp_daily_tc_sql,  # TC §71 Fase 3: reemplaza corp legacy
    get_comms_oc_fresh_sql,                    # Two-Tier Tier 2: semana actual (History.md §45)
    get_installs_monthly_sql,                  # §88: installs FM por canal
    get_installs_corp_monthly_sql,             # §88: installs Corp por corp_key
)


# ── Helpers de formato de fechas ──────────────────────────────

def fmt_month(yyyymm):
    months_dict = {'01':'Ene','02':'Feb','03':'Mar','04':'Abr','05':'May','06':'Jun',
                   '07':'Jul','08':'Ago','09':'Sep','10':'Oct','11':'Nov','12':'Dic'}
    return f"{months_dict[yyyymm[4:6]]} {yyyymm[:4]}"


def prior_months_list(yyyymm, n=2):
    y, m = int(yyyymm[:4]), int(yyyymm[4:])
    res = []
    for _ in range(n):
        m -= 1
        if m == 0: m = 12; y -= 1
        res.append(f'{y:04d}{m:02d}')
    return res


# ── Helper BigQuery ───────────────────────────────────────────

def bq_query(client, sql, retries=3, wait=120):
    """Ejecuta SQL en BQ con reintentos por cuota."""
    for attempt in range(1, retries + 1):
        try:
            return client.query(sql).to_dataframe()
        except Exception as e:
            if 'quotaExceeded' in str(e).lower() or '403' in str(e):
                print(f"  Quota BQ excedida. Reintento {attempt}/{retries} en {wait}s...")
                time.sleep(wait)
            else:
                raise
    raise Exception("BQ Retries exhausted")


# ── Helpers de jerarquía ──────────────────────────────────────

def get_descendants(node_id, HIERARCHY_NR):
    """Devuelve labels de todos los nodos hoja bajo node_id (hierarchy_nr)."""
    node = next(x for x in HIERARCHY_NR if x['id'] == node_id)
    res = []
    for cid in node.get('children', []):
        ch = next(x for x in HIERARCHY_NR if x['id'] == cid)
        if ch.get('is_leaf'): res.append(ch['label'])
        else: res.extend(get_descendants(cid, HIERARCHY_NR))
    return res


def get_cost_descendants(node_id, HIERARCHY_C):
    """Devuelve labels de todos los nodos hoja bajo node_id (hierarchy_cost)."""
    node = next(x for x in HIERARCHY_C if x['id'] == node_id)
    res = []
    for cid in node.get('children', []):
        ch = next(x for x in HIERARCHY_C if x['id'] == cid)
        if ch.get('is_leaf'): res.append(ch['label'])
        else: res.extend(get_cost_descendants(cid, HIERARCHY_C))
    return res


# ── New vs Recovered mensual (para pestaña Reporting) ────────

def process_new_rec_monthly(bq_client):
    """Retorna {yyyymm: {'new': int, 'rec': int}} desde BT_MP_USER_ENGAGEMENT_INAPP.
    Misma fuente que el total N+R del dashboard. Cutoff D-1."""
    from queries import get_new_rec_monthly_sql
    sql = get_new_rec_monthly_sql()
    try:
        df = bq_client.query(sql).result(timeout=300).to_dataframe()
    except Exception as e:
        print(f"  WARN process_new_rec_monthly BQ error: {e} — retornando vacío")
        return {}
    result = {}
    for _, row in df.iterrows():
        m = str(row.get('MONTH_ID', ''))
        if m:
            result[m] = {
                'new': int(row.get('new_nr') or 0),
                'rec': int(row.get('rec_nr') or 0),
            }
    return result


# ── Procesamiento tabla corporativa N+R ──────────────────────

def process_nr_corp(config, bq_client, all_nr_months):
    """Ejecuta get_nr_corp_sql() y construye monthly_nr_corp_by_node.

    Fuente BQ: BT_OC_NR_REPORTE_TORRE_DAILY (OC) + BT_MP_INDIVIDUALS_PERFORMANCE (Paid+ORG) → get_nr_corp_tc_sql() §75
    Config:    config['hierarchy_nr_corp_detail'] → HIERARCHY_NR_CORP

    Retorna:
      monthly_nr_corp_by_node: dict { node_id: { yyyymm: nr_int } }
        Cubre TODOS los nodos de HIERARCHY_NR_CORP, incluyendo padres calculados
        bottom-up desde los nodos hoja (is_leaf=True con bq_key).
    """
    HIERARCHY_NR_CORP = config.get('hierarchy_nr_corp_detail', [])
    if not HIERARCHY_NR_CORP:
        return {}

    # Paso 1: ejecutar query corp TC (§71 — fuentes Torre de Control)
    df_nr_corp = bq_query(bq_client, get_nr_corp_tc_sql(config.get('hierarchy_nr', [])))

    # Paso 2: construir dict plano por corp_key
    # corp_key → { yyyymm: nr_total_corp }
    nr_corp_flat_by_key = {}
    for _, row in df_nr_corp.iterrows():
        corp_key          = str(row['corp_key'])
        fecha_mes_corp    = str(row['fecha_mes_corp'])
        nr_value          = float(row['nr_total_corp'] or 0)
        if corp_key not in nr_corp_flat_by_key:
            nr_corp_flat_by_key[corp_key] = {}
        nr_corp_flat_by_key[corp_key][fecha_mes_corp] = (
            nr_corp_flat_by_key[corp_key].get(fecha_mes_corp, 0) + nr_value
        )

    # Paso 3: inicializar dict de nodos con todos los meses en 0
    monthly_nr_corp_by_node = {}
    for corp_node in HIERARCHY_NR_CORP:
        node_id = corp_node['id']
        monthly_nr_corp_by_node[node_id] = {m: 0 for m in all_nr_months}

    # Paso 4: asignar nodos hoja desde nr_corp_flat_by_key
    # Los nodos hoja tienen bq_key = CORP_KEY del SQL
    # Los nodos 'OTROS' (residuos de TOUCHPOINT no mapeados) se ignoran — tiny volume
    for corp_node in HIERARCHY_NR_CORP:
        if not corp_node.get('is_leaf'):
            continue
        node_id       = corp_node['id']
        bq_key_value  = corp_node.get('bq_key', '')
        flat_data_for_key = nr_corp_flat_by_key.get(bq_key_value, {})
        for month in all_nr_months:
            monthly_nr_corp_by_node[node_id][month] = int(round(flat_data_for_key.get(month, 0)))

    # Paso 5: propagar bottom-up → nodos padre = suma de sus hijos
    # reversed() garantiza que todos los hijos estén calculados antes que sus padres
    corp_node_id_to_node = {c['id']: c for c in HIERARCHY_NR_CORP}
    for corp_node in reversed(HIERARCHY_NR_CORP):
        if corp_node.get('is_leaf'):
            continue  # Los nodos hoja ya fueron asignados en Paso 4
        node_id      = corp_node['id']
        child_ids    = corp_node.get('children', [])
        for month in all_nr_months:
            monthly_nr_corp_by_node[node_id][month] = sum(
                monthly_nr_corp_by_node.get(child_id, {}).get(month, 0)
                for child_id in child_ids
            )

    return monthly_nr_corp_by_node


def process_nr_corp_daily(config, bq_client, all_nr_months):
    """Ejecuta get_nr_corp_daily_sql() y construye daily_nr_corp_by_node.

    Diferencia con process_nr_corp():
      · process_nr_corp()       → agrega por mes    → monthly_nr_corp_by_node {node: {yyyymm: nr}}
      · process_nr_corp_daily() → agrega por día    → daily_nr_corp_by_node   {node: {yyyymm: {dia: nr}}}

    Fuente BQ: BT_OC_NR_REPORTE_TORRE_DAILY (OC) + BT_MP_INDIVIDUALS_PERFORMANCE (Paid+ORG) → get_nr_corp_daily_tc_sql() §75
    Config:    config['hierarchy_nr_corp_detail'] → HIERARCHY_NR_CORP

    Retorna:
      daily_nr_corp_by_node: dict { node_id: { yyyymm: { dia_str: nr_int } } }
        · dia_str = str(int), ej. "1", "15", "31"
        · Cubre TODOS los nodos incluyendo padres calculados bottom-up por día.

    Flujo:
      1. Ejecutar get_nr_corp_daily_sql() → df_nr_corp_daily
      2. Construir nr_corp_daily_flat_by_key { corp_key: { yyyymm: { dia_str: nr_float } } }
      3. Inicializar daily_nr_corp_by_node con dicts vacíos por mes y día
      4. Asignar nodos hoja desde nr_corp_daily_flat_by_key
      5. Propagar bottom-up por cada mes y cada día (reversed HIERARCHY_NR_CORP)
    """
    HIERARCHY_NR_CORP = config.get('hierarchy_nr_corp_detail', [])
    if not HIERARCHY_NR_CORP:
        return {}

    # Paso 1: ejecutar query daily corp TC (§71 — fuentes Torre de Control)
    df_nr_corp_daily = bq_query(bq_client, get_nr_corp_daily_tc_sql(config.get('hierarchy_nr', [])))

    # Paso 2: construir dict plano { corp_key: { yyyymm: { dia_str: nr_acumulado } } }
    # Se usa nr_acumulado para manejar múltiples filas con la misma (key, mes, día)
    nr_corp_daily_flat_by_key = {}
    for _, row in df_nr_corp_daily.iterrows():
        corp_key          = str(row['corp_key'])
        fecha_mes_corp    = str(row['fecha_mes_corp'])
        dia_str           = str(int(row['dia_del_mes']))
        nr_dia_value      = float(row['nr_dia_corp'] or 0)

        if corp_key not in nr_corp_daily_flat_by_key:
            nr_corp_daily_flat_by_key[corp_key] = {}
        if fecha_mes_corp not in nr_corp_daily_flat_by_key[corp_key]:
            nr_corp_daily_flat_by_key[corp_key][fecha_mes_corp] = {}

        existing_nr = nr_corp_daily_flat_by_key[corp_key][fecha_mes_corp].get(dia_str, 0)
        nr_corp_daily_flat_by_key[corp_key][fecha_mes_corp][dia_str] = existing_nr + nr_dia_value

    # Paso 3: inicializar daily_nr_corp_by_node — estructura vacía por nodo/mes/día
    daily_nr_corp_by_node = {}
    for corp_node in HIERARCHY_NR_CORP:
        if 'id' not in corp_node:
            continue
        node_id = corp_node['id']
        daily_nr_corp_by_node[node_id] = {month: {} for month in all_nr_months}

    # Paso 4: asignar nodos hoja desde nr_corp_daily_flat_by_key
    for corp_node in HIERARCHY_NR_CORP:
        if not corp_node.get('is_leaf') or 'id' not in corp_node:
            continue
        node_id            = corp_node['id']
        bq_key_value       = corp_node.get('bq_key', '')
        flat_data_for_key  = nr_corp_daily_flat_by_key.get(bq_key_value, {})

        for month in all_nr_months:
            dias_for_month_for_key = flat_data_for_key.get(month, {})
            for dia_str, nr_float_value in dias_for_month_for_key.items():
                daily_nr_corp_by_node[node_id][month][dia_str] = int(round(nr_float_value))

    # Paso 5: propagar bottom-up por mes y por día
    # reversed() garantiza que los hijos estén calculados antes que sus padres
    corp_node_id_to_node = {c['id']: c for c in HIERARCHY_NR_CORP if 'id' in c}
    for corp_node in reversed(HIERARCHY_NR_CORP):
        if corp_node.get('is_leaf') or 'id' not in corp_node:
            continue  # Hojas ya fueron asignadas en Paso 4
        node_id   = corp_node['id']
        child_ids = corp_node.get('children', [])

        for month in all_nr_months:
            # Recopilar todos los días que aparecen en cualquier hijo
            all_days_in_month = set()
            for child_id in child_ids:
                all_days_in_month.update(daily_nr_corp_by_node.get(child_id, {}).get(month, {}).keys())

            for dia_str in all_days_in_month:
                daily_nr_corp_by_node[node_id][month][dia_str] = sum(
                    daily_nr_corp_by_node.get(child_id, {}).get(month, {}).get(dia_str, 0)
                    for child_id in child_ids
                )

    return daily_nr_corp_by_node


# ── Función principal ─────────────────────────────────────────

def process_all(config, client, n_prior=2):
    """Ejecuta todas las queries BQ y procesamiento.
    Devuelve dict 'data' con todos los datos listos para builders.py y data_js.
    """
    HIERARCHY_NR = config['hierarchy_nr']
    HIERARCHY_C  = config['hierarchy_cost']
    LABELS       = [c['label'] for c in HIERARCHY_NR]
    COST_LABELS  = [c['label'] for c in HIERARCHY_C]
    PLAN_ROW_MAP = {c['plan_row']: c['label'] for c in HIERARCHY_NR if 'plan_row' in c}

    # ── 3a. N+R diario — Torre de Control TC (§71 History.md) ───────────────
    # Fuente: BT_OC_NR_REPORTE_TORRE_DAILY (OC) + BT_MP_INDIVIDUALS_PERFORMANCE (Paid+ORG).
    # ORG = NOT NETWORK APPE + SOURCE_CD=TOOL_COST (§76). Sin cache adicional.
    # Reemplaza PANEL_MONTHLY_DAILY_HISTORICO (deprecated).
    # Output schema idéntico: CANAL, FECHA_MES, DIA, NR, COST, CUM_NR.
    print(">>> Paso 1: Consultando BigQuery — N+R Torre de Control (TC)...")
    df_nr = bq_query(client, get_nr_tc_sql(HIERARCHY_NR))
    df_nr[['NR', 'CUM_NR', 'COST']] = df_nr[['NR', 'CUM_NR', 'COST']].astype(float)

    months = sorted(df_nr['FECHA_MES'].unique().tolist())

    monthly_nr   = {l: {} for l in LABELS}
    monthly_mom  = {l: {} for l in LABELS}
    monthly_cost = {l: {} for l in LABELS}
    daily_cum    = {l: {} for l in LABELS}
    daily_cost   = {l: {} for l in LABELS}
    avg_cum      = {l: {} for l in LABELS}
    vs_prom_cum  = {l: {} for l in LABELS}

    # Canales cuyo CUM_NR viene como NR diario del cache (no como acumulado de BQ)
    # Para estos hay que acumular NR día a día en lugar de leer CUM_NR=0
    _canales_cum_desde_nr = {'ORG'}

    print(">>> Paso 2: Procesando N+R...")
    for m in months:
        df_m = df_nr[df_nr['FECHA_MES'] == m]
        for c in HIERARCHY_NR:
            lbl = c['label']
            if c.get('is_leaf'):
                slice_df = df_m[df_m['CANAL'] == lbl]
            elif lbl == 'Total N+R':
                slice_df = df_m
            else:
                slice_df = df_m[df_m['CANAL'].isin(get_descendants(c['id'], HIERARCHY_NR))]

            monthly_nr[lbl][m]   = int(slice_df['NR'].sum())
            monthly_cost[lbl][m] = round(slice_df['COST'].sum(), 2)
            daily_cum[lbl][m]    = {}
            daily_cost[lbl][m]   = {}

            _acum_desde_nr = lbl in _canales_cum_desde_nr
            _cum = 0
            for d in sorted(df_m['DIA'].unique()):
                d_df = slice_df[slice_df['DIA'] == d]
                daily_cost[lbl][m][str(d)] = round(d_df['COST'].sum(), 2)
                if _acum_desde_nr:
                    # ORG cache: NR diario → acumular manualmente
                    _cum += int(d_df['NR'].sum())
                    daily_cum[lbl][m][str(d)] = _cum
                else:
                    daily_cum[lbl][m][str(d)] = int(d_df['CUM_NR'].sum())

    # Forward-fill acumulados (Bug 1 fix: días sin datos heredan el valor anterior)
    for lbl in [c['label'] for c in HIERARCHY_NR if c.get('is_leaf')]:
        for m in months:
            last_v = 0
            for d_str in sorted(daily_cum[lbl][m], key=int):
                v = daily_cum[lbl][m][d_str]
                if v == 0 and last_v > 0: daily_cum[lbl][m][d_str] = last_v
                elif v != 0: last_v = v

    # Recalcular nodos agregados bottom-up (reversed garantiza hijos antes que padres)
    for m in months:
        for c in reversed([x for x in HIERARCHY_NR if not x.get('is_leaf')]):
            lbl        = c['label']
            child_lbls = [next(x['label'] for x in HIERARCHY_NR if x['id'] == cid) for cid in c.get('children', [])]
            for d_str in daily_cum[lbl][m]:
                daily_cum[lbl][m][d_str] = sum(daily_cum[cl][m].get(d_str, 0) for cl in child_lbls)

    # MoM y promedios históricos
    for lbl in LABELS:
        for i, m in enumerate(months):
            avg_cum[lbl][m] = {}; vs_prom_cum[lbl][m] = {}
            if i > 0:
                prev = monthly_nr[lbl][months[i-1]]
                monthly_mom[lbl][m] = round((monthly_nr[lbl][m] - prev) / prev, 4) if prev else None
            priors = [p for p in prior_months_list(m, n_prior) if p in months]
            for d_str in daily_cum[lbl][m]:
                vals = [daily_cum[lbl][p][d_str] for p in priors if d_str in daily_cum[lbl].get(p, {})]
                avg  = round(sum(vals) / len(vals)) if vals else None
                avg_cum[lbl][m][d_str] = avg
                if avg: vs_prom_cum[lbl][m][d_str] = round((daily_cum[lbl][m][d_str] - avg) / avg, 4)

    # ── 3b. Costos — Torre de Control TC (§71 History.md) ───────────────────
    # Fuente: BT_OC_NR_REPORTE_TORRE_DAILY (OC) + BT_MP_INDIVIDUALS_PERFORMANCE (Paid).
    # Reemplaza PANEL_MONTHLY_COSTOS_CANALES (deprecated).
    # HIERARCHY_NR en lugar de HIERARCHY_C: usa tc_mapping (labels idénticos, sin cambio downstream).
    print(">>> Paso 1b: Consultando BigQuery — Costos Torre de Control (TC)...")
    df_cost = bq_query(client, get_costos_tc_sql(HIERARCHY_NR))
    df_cost[['INV_CANAL', 'INV_INCENTIVO', 'INV_TOTAL', 'INV_MANTIKA']] = \
        df_cost[['INV_CANAL', 'INV_INCENTIVO', 'INV_TOTAL', 'INV_MANTIKA']].fillna(0).astype(float)
    cost_months = sorted(df_cost['MONTH_ID'].unique().tolist())

    monthly_inv_canal     = {l: {} for l in COST_LABELS}
    monthly_inv_incentivo = {l: {} for l in COST_LABELS}
    monthly_inv_total     = {l: {} for l in COST_LABELS}
    monthly_inv_mantika   = {l: {} for l in COST_LABELS}   # Mantika platform fee (OC only)
    monthly_inv_mom       = {l: {} for l in COST_LABELS}

    print(">>> Paso 2b: Procesando Costos...")
    for m in cost_months:
        df_cm = df_cost[df_cost['MONTH_ID'] == m]
        for c in HIERARCHY_C:
            lbl = c['label']
            if c.get('no_cost'):
                monthly_inv_canal[lbl][m]     = None
                monthly_inv_incentivo[lbl][m] = None
                monthly_inv_total[lbl][m]     = None
                monthly_inv_mantika[lbl][m]   = None
                continue
            if c.get('is_leaf') and 'cost_mapping' in c:
                slice_df = df_cm[df_cm['CANAL'] == lbl]
            elif lbl == 'Total Inversión':
                slice_df = df_cm
            else:
                desc       = get_cost_descendants(c['id'], HIERARCHY_C)
                valid_desc = [d for d in desc if not next(x for x in HIERARCHY_C if x['label'] == d).get('no_cost')]
                slice_df   = df_cm[df_cm['CANAL'].isin(valid_desc)]
            monthly_inv_canal[lbl][m]     = round(float(slice_df['INV_CANAL'].sum()), 0)
            monthly_inv_incentivo[lbl][m] = round(float(slice_df['INV_INCENTIVO'].sum()), 0)
            monthly_inv_total[lbl][m]     = round(float(slice_df['INV_TOTAL'].sum()), 0)
            monthly_inv_mantika[lbl][m]   = round(float(slice_df['INV_MANTIKA'].sum()), 0)

    # MoM inversión
    for lbl in COST_LABELS:
        ms = sorted(monthly_inv_total[lbl].keys())
        for i, m in enumerate(ms):
            if i > 0:
                prev = monthly_inv_total[lbl][ms[i-1]]
                curr = monthly_inv_total[lbl][m]
                if prev and prev != 0 and curr is not None:
                    monthly_inv_mom[lbl][m] = round((curr - prev) / prev, 4)

    # CPA Total & Paid: cruce N+R (HIERARCHY_NR) × Inversión (HIERARCHY_C)
    # COST_CHANNELS_NR: canales leaf con cost_mapping (tienen inversión real)
    COST_CHANNELS_NR  = [c['label'] for c in HIERARCHY_C if c.get('is_leaf') and 'cost_mapping' in c]
    monthly_nr_paid   = {}
    monthly_cpa_total = {}
    monthly_cpa_paid  = {}
    for m in cost_months:
        inv_total = monthly_inv_total['Total Inversión'].get(m) or 0
        nr_total  = monthly_nr.get('Total N+R', {}).get(m, 0) or 0
        nr_paid   = sum(monthly_nr.get(lbl, {}).get(m, 0) or 0 for lbl in COST_CHANNELS_NR) if m in months else 0
        monthly_nr_paid[m]   = int(nr_paid)
        monthly_cpa_total[m] = round(inv_total / nr_total, 2) if nr_total > 0 else None
        monthly_cpa_paid[m]  = round(inv_total / nr_paid,  2) if nr_paid  > 0 else None

    # ── 3c. Performance: Paid/Free split + VPU + ROA — Torre de Control TC (§71) ──
    # Paid/Free: FLAG_PAID en Torre Daily / COST_USD > 0 en Individuals Performance.
    # VPU:       NR_INC_VALUE (OC) + VALUE_MKT_USD_* (Paid) + legacy (ORG).
    # ROA:       NR_INC_VALUE / costo OC donde FLAG_PAID='PAID' y cost > 0.
    # Reemplaza: get_perf_paid_sql, get_perf_vpu_sql, get_perf_roa_costos_sql (todos deprecated).
    print(">>> Paso 1c: Consultando BigQuery — Performance TC (Paid/VPU/ROA)...")
    df_perf_paid = bq_query(client, get_perf_paid_tc_sql(HIERARCHY_NR))
    df_perf_vpu  = bq_query(client, get_vpu_tc_sql(HIERARCHY_NR))
    df_perf_roa  = bq_query(client, get_roa_tc_sql())

    perf_nr_paid  = {l: {} for l in LABELS}
    perf_nr_go    = {l: {} for l in LABELS}  # Gest Others (ACTIVATION_OTHER_TEAM)
    perf_vpu_prod = {l: {} for l in LABELS}  # NR × VPU pre-multiplicado por fila BQ

    for _, r in df_perf_paid.iterrows():
        lbl = r['PERF_CANAL']; m = str(r['MONTH_ID'])
        if lbl in perf_nr_paid:
            perf_nr_paid[lbl][m] = int(r['NR_PAID']        or 0)
            perf_nr_go[lbl][m]   = int(r['NR_GEST_OTHERS'] or 0)

    # POM = todo paid por definición (medio 100% pago)
    for lbl in ['POM ADQ', 'POM ACT']:
        for m in months:
            perf_nr_paid[lbl][m] = monthly_nr[lbl].get(m, 0)

    for _, r in df_perf_vpu.iterrows():
        lbl = r['PERF_CANAL']; m = str(r['MONTH_ID'])
        if lbl in perf_vpu_prod:
            perf_vpu_prod[lbl][m] = float(r['NR_VPU_PROD'] or 0)

    # Propagar a nodos agregados bottom-up (mismo patrón que daily_cum)
    for m in months:
        for c in reversed([x for x in HIERARCHY_NR if not x.get('is_leaf')]):
            lbl    = c['label']
            leaves = get_descendants(c['id'], HIERARCHY_NR) if lbl != 'Total N+R' else [x['label'] for x in HIERARCHY_NR if x.get('is_leaf')]
            perf_nr_paid[lbl][m]  = sum(perf_nr_paid[l].get(m, 0)  for l in leaves)
            perf_nr_go[lbl][m]    = sum(perf_nr_go[l].get(m, 0)    for l in leaves)
            perf_vpu_prod[lbl][m] = sum(perf_vpu_prod[l].get(m, 0) for l in leaves)

    # ── Normalización histórica Valor Pred 90D — factor 0.38 para pre-Abr-2026 (§87) ──
    # MktSci Corp confirmó: el cambio al modelo "Fact Based" (Abr-2026) adoptó un
    # factor de nivelación para comparaciones históricas justas: valor_hist × 0.38.
    # Se aplica a todos los canales y nodos (hoja + padre) para meses < '202604'.
    # Matemáticamente correcto: padre × 0.38 = Σ(hojas × 0.38) post-propagación.
    _VALOR_BREAK_MONTH  = '202604'   # Primer mes con modelo nuevo (sin factor)
    _VALOR_HIST_FACTOR  = 0.38       # Factor confirmado por equipo MktSci Corp
    for lbl in perf_vpu_prod:
        for m in list(perf_vpu_prod[lbl].keys()):
            if m < _VALOR_BREAK_MONTH:
                perf_vpu_prod[lbl][m] = (perf_vpu_prod[lbl][m] or 0) * _VALOR_HIST_FACTOR

    # ── Numerador ROA por canal (fuente varía según canal, §5 metrics_logic.md) ─
    # UCR Gest, OC ACT  : VALUE_PRED de COSTOS_CANALES filtrado por INV > 0
    # POM ADQ, POM ACT  : VALUE_MKT_PREDICTION_90D_NR_USERS de DAILY_HISTORICO
    # MGM ADQ            : EXCLUIDO del numerador ROA (§88 fix) — tiene valor predicho real
    #                       pero inversión = 0 en Corp methodology (Incentive Engine = 0).
    #                       Incluirlo inflaría el Total ROAS en ~0.1x vs Corp.
    #                       ROAS MGM = "—" es correcto (no hay inversión medible).
    # MGM ACT, UCR PRD, L&P, ORG: 0 (sin inversión directa → ROA = —)
    # Verificado: sin MGM → Total ROAS Apr-26 = 1.71x ≈ Corp 1.7x ✓
    perf_roa_num = {l: {} for l in LABELS}

    # Paso 1: poblar canales OC desde df_perf_roa (raw, sin factor todavía)
    for _, r in df_perf_roa.iterrows():
        lbl = r['PERF_CANAL']; m = str(r['MONTH_ID'])
        if lbl in perf_roa_num:
            perf_roa_num[lbl][m] = float(r['ROA_VALUE_PRED'] or 0)

    # Paso 2: aplicar 0.38 SOLO a los canales OC (vienen de BQ sin normalizar).
    # POM se asigna en el siguiente paso desde perf_vpu_prod (ya tiene 0.38).
    # Aplicar aquí — antes de la asignación POM — evita la doble aplicación (§89 fix).
    _oc_roa_labels = {str(r['PERF_CANAL']) for _, r in df_perf_roa.iterrows()
                      if str(r['PERF_CANAL']) in perf_roa_num}
    for lbl in _oc_roa_labels:
        for m in list(perf_roa_num[lbl].keys()):
            if m < _VALOR_BREAK_MONTH:
                perf_roa_num[lbl][m] = (perf_roa_num[lbl][m] or 0) * _VALOR_HIST_FACTOR

    # Paso 3: asignar POM desde perf_vpu_prod (ya normalizado ×0.38 en paso anterior).
    # MGM ADQ excluido intencionalmente (§88): su valor inflaría el Total ROAS
    # ya que tiene perf_vpu_prod real pero inversión=0 → ROAS MGM = "—" es correcto.
    for lbl in ['POM ADQ', 'POM ACT']:
        for m in months:
            perf_roa_num[lbl][m] = perf_vpu_prod[lbl].get(m, 0)

    # Paso 4: propagar nodos agregados bottom-up (todas las hojas ya tienen factor correcto)
    for m in months:
        for c in reversed([x for x in HIERARCHY_NR if not x.get('is_leaf')]):
            lbl    = c['label']
            leaves = get_descendants(c['id'], HIERARCHY_NR) if lbl != 'Total N+R' else [x['label'] for x in HIERARCHY_NR if x.get('is_leaf')]
            perf_roa_num[lbl][m] = sum(perf_roa_num[l].get(m, 0) for l in leaves)

    # ── Devolver todo en un dict plano para builders.py y data_js ──
    return dict(
        # Jerarquías (pasadas a builders para iterar canales)
        HIERARCHY_NR=HIERARCHY_NR, HIERARCHY_C=HIERARCHY_C,
        LABELS=LABELS, COST_LABELS=COST_LABELS, PLAN_ROW_MAP=PLAN_ROW_MAP,
        COST_CHANNELS_NR=COST_CHANNELS_NR,
        # Periodos disponibles en BQ
        months=months, cost_months=cost_months,
        # N+R (fuente DAILY_HISTORICO)
        monthly_nr=monthly_nr, monthly_mom=monthly_mom, monthly_cost=monthly_cost,
        daily_cum=daily_cum, daily_cost=daily_cost,
        avg_cum=avg_cum, vs_prom_cum=vs_prom_cum,
        # Costos (fuente COSTOS_CANALES)
        monthly_inv_canal=monthly_inv_canal, monthly_inv_incentivo=monthly_inv_incentivo,
        monthly_inv_total=monthly_inv_total, monthly_inv_mantika=monthly_inv_mantika,
        monthly_inv_mom=monthly_inv_mom,
        monthly_nr_paid=monthly_nr_paid, monthly_cpa_total=monthly_cpa_total, monthly_cpa_paid=monthly_cpa_paid,
        # Performance (cruce de ambas fuentes)
        perf_nr_paid=perf_nr_paid, perf_nr_go=perf_nr_go, perf_vpu_prod=perf_vpu_prod,
        perf_roa_num=perf_roa_num,
    )


# ══════════════════════════════════════════════════════════════════════════════
# process_comms_oc — Carga comunicaciones OC (Two-Tier Caching)
# ══════════════════════════════════════════════════════════════════════════════

def process_comms_oc(bq_client_for_fresh_query, comms_oc_cache_file_path,
                     comms_oc_current_month_path=None):
    """Carga el historial de comunicaciones OC fusionando cache + query BQ de semana actual.

    ══════════════════════════════════════════════════════════════════
    ARQUITECTURA TWO-TIER (ver History.md §45)
    ══════════════════════════════════════════════════════════════════

    TIER 1 — Cache histórico (data/comms_oc_cache.json):
      · Contiene comunicaciones con SENT_DATE < inicio de semana actual (lunes)
      · Generado UNA VEZ y actualizado semanalmente por:
          python scripts/refresh_comms_oc_cache.py
      · Si no existe el archivo → mensaje de error claro (no falla silenciosamente)
      · Formato: lista de dicts JSON (strings para fechas, None para nulos)

    TIER 2 — Datos frescos (get_comms_oc_fresh_sql() en queries.py):
      · Contiene comunicaciones con SENT_DATE >= inicio de semana actual
      · Máximo 7 días de datos → query ultra-rápida en BQ
      · Corre en CADA refresh del dashboard (2x/día vía gen_dashboard_v1.py)
      · Si falla (ej. permisos SBOX_EG_MKT no disponibles en GitHub Actions):
          → Error VISIBLE en stdout (no silencioso — principio #5 del proyecto)
          → Dashboard continúa mostrando solo datos del cache Tier 1
          → La pestaña Comms_OC sigue funcionando con datos de hasta la semana pasada

    MERGE:
      · Tier 1 + Tier 2 se concatenan (no hay solapamiento por definición del corte)
      · Ordenados por FIRST_SENT_DATE desc (comunicaciones más recientes primero)

    ══════════════════════════════════════════════════════════════════
    PARÁMETROS
    ══════════════════════════════════════════════════════════════════
    bq_client_for_fresh_query : google.cloud.bigquery.Client
        Cliente BQ ya autenticado (el mismo que usa process_all() en gen_dashboard_v1.py)
    comms_oc_cache_file_path : str
        Ruta absoluta a data/comms_oc_cache.json
        Definida en gen_dashboard_v1.py como COMMS_OC_CACHE_PATH

    ══════════════════════════════════════════════════════════════════
    RETORNO
    ══════════════════════════════════════════════════════════════════
    list[dict] — Lista de registros de comunicaciones OC, ordenada por
    FIRST_SENT_DATE desc (comunicación más reciente primero).

    Cada dict contiene las columnas del SELECT final de queries.get_comms_oc_fresh_sql():
      FIRST_SENT_DATE (str 'YYYY-MM-DD'), MONTH_ID (str 'YYYYMM'),
      COMMUNICATION_ID (str), CAMPAIGN_NAME (str), CAMPAIGN_NAME_CLEAN (str),
      CANAL (str|None), APP (str|None), NOTIFICATION_TITLE (str|None),
      TOTAL_*_CUST_EVENT (int|None), STRATEGIES (str|None),
      SENTS (float|None), OPEN_RATE (float|None), M_CVR_TEST (float|None),
      M_LIFT (float|None), USER_INC (float|None), VALUE_INC (float|None)

    Consumida por: builders.build_comms_oc_table_html() a través de data['comms_oc_records']
    """

    # ── TIER 1: Cargar cache histórico desde JSON ───────────────────────────
    # El cache cubre SENT_DATE < inicio_semana_actual → datos estables, no re-consultables

    all_historical_records_from_cache = []

    if os.path.exists(comms_oc_cache_file_path):
        with open(comms_oc_cache_file_path, 'r', encoding='utf-8') as cache_file:
            all_historical_records_from_cache = json.load(cache_file)
        print(f"  OK Comms_OC cache Tier 1: {len(all_historical_records_from_cache)} registros"
              f" desde {os.path.basename(comms_oc_cache_file_path)}")
    else:
        # Error visible — no silencioso. El usuario necesita saber que falta el cache.
        print(f"  ⚠️  Comms_OC Tier 1: cache NOT FOUND en {comms_oc_cache_file_path}")
        print(f"      La pestaña Comms_OC mostrará solo datos de la semana actual.")
        print(f"      Para generar el cache histórico:")
        print(f"      python scripts/refresh_comms_oc_cache.py")

    # ── TIER 2: Mes actual — con caché diario para evitar re-query en cada generación ─
    # Lógica: si comms_oc_current_month.json existe y fue creado HOY → usarlo directamente.
    # Si no existe o es de ayer → correr BQ, guardar para el resto del día.
    # Para forzar re-query: borrar data/comms_oc_current_month.json

    import datetime as _dt

    all_current_week_records_from_bq = []
    today_str = _dt.date.today().isoformat()   # 'YYYY-MM-DD'

    # Verificar si el Tier 2 cache del día existe y es de hoy
    tier2_cache_valid = False
    if comms_oc_current_month_path and os.path.exists(comms_oc_current_month_path):
        try:
            mtime_date = _dt.date.fromtimestamp(os.path.getmtime(comms_oc_current_month_path))
            if mtime_date.isoformat() == today_str:
                tier2_cache_valid = True
        except Exception:
            tier2_cache_valid = False

    if tier2_cache_valid:
        # Cargar desde cache diario (instantáneo — sin BQ)
        with open(comms_oc_current_month_path, 'r', encoding='utf-8') as _f:
            all_current_week_records_from_bq = json.load(_f)
        print(f"  OK Comms_OC Tier 2 (cache diario, sin BQ): "
              f"{len(all_current_week_records_from_bq)} registros del mes actual")
    else:
        # Cache diario inexistente o desactualizado → correr BQ
        if comms_oc_current_month_path:
            print(f"  Comms_OC Tier 2: cache diario no disponible → consultando BQ...")
        try:
            dataframe_current_week_comms = bq_query(
                bq_client_for_fresh_query,
                get_comms_oc_fresh_sql()
            )
            all_current_week_records_from_bq = dataframe_current_week_comms.to_dict(orient='records')
            print(f"  OK Comms_OC fresh Tier 2: {len(all_current_week_records_from_bq)} registros"
                  f" del mes actual")

            # Guardar como cache diario para re-usos del mismo día
            if comms_oc_current_month_path:
                with open(comms_oc_current_month_path, 'w', encoding='utf-8') as _f:
                    json.dump(all_current_week_records_from_bq, _f,
                              ensure_ascii=False, default=str)
                print(f"  OK Comms_OC Tier 2 guardado en cache diario "
                      f"({os.path.basename(comms_oc_current_month_path)})")

        except Exception as fresh_query_exception:
            print(f"  ⚠️  Comms_OC Tier 2 FALLÓ — query mes actual no ejecutada:")
            print(f"      Error: {fresh_query_exception}")
            print(f"      Dashboard mostrará solo datos históricos del cache (Tier 1).")
            print(f"      Si el error es 403/acceso: verificar permisos ADC en SBOX_EG_MKT.")

    # ── MERGE: deduplicar por (COMMUNICATION_ID, SENT_DATE, CANAL, FUENTE_TABLA) ─
    # §75: granularidad diaria — clave nueva vs legacy (COMM_ID, MONTH_ID).
    # Tier2 sobreescribe Tier1 en caso de colisión (datos más frescos del día).
    # FUENTE_TABLA distingue ALL_CAMPAIGNS_NR de NR_ACQUISITION para el mismo COMM_ID+día.
    merged_by_key = {}
    for _r in all_historical_records_from_cache:
        _k = (
            str(_r.get('COMMUNICATION_ID', '')),
            str(_r.get('SENT_DATE', '')),
            str(_r.get('CANAL', '')),
            str(_r.get('FUENTE_TABLA', '')),
        )
        merged_by_key[_k] = _r
    for _r in all_current_week_records_from_bq:
        _k = (
            str(_r.get('COMMUNICATION_ID', '')),
            str(_r.get('SENT_DATE', '')),
            str(_r.get('CANAL', '')),
            str(_r.get('FUENTE_TABLA', '')),
        )
        merged_by_key[_k] = _r  # tier2 gana (más reciente)

    all_comms_oc_records_merged = list(merged_by_key.values())

    # Ordenar por SENT_DATE desc (string 'YYYY-MM-DD' ordena correctamente lexicográficamente)
    all_comms_oc_records_merged.sort(
        key=lambda record: str(record.get('SENT_DATE', '')),
        reverse=True   # más reciente primero
    )

    # Ventana temporal para el builder HTML: solo los últimos COMMS_OC_MONTHS_WINDOW meses.
    # El cache completo se conserva en disco; solo filtramos lo que se pasa al HTML.
    # Esto evita que el builder itere 70K+ registros y tarde horas en Paso 4.
    import datetime as _dt2
    COMMS_OC_MONTHS_WINDOW = 9  # meses hacia atrás desde hoy
    _cutoff = _dt2.date.today().replace(day=1)
    for _ in range(COMMS_OC_MONTHS_WINDOW - 1):
        _cutoff = (_cutoff - _dt2.timedelta(days=1)).replace(day=1)
    _cutoff_str = _cutoff.isoformat()  # 'YYYY-MM-DD'
    _before = len(all_comms_oc_records_merged)
    all_comms_oc_records_merged = [
        r for r in all_comms_oc_records_merged
        if str(r.get('SENT_DATE', '')) >= _cutoff_str
    ]
    print(f"  OK Comms_OC ventana {COMMS_OC_MONTHS_WINDOW}m (desde {_cutoff_str}): "
          f"{len(all_comms_oc_records_merged)} registros "
          f"(de {_before} totales en cache)")

    total_records_after_merge = len(all_comms_oc_records_merged)
    print(f"  OK Comms_OC total merged: {total_records_after_merge} registros"
          f" (cache={len(all_historical_records_from_cache)}"
          f" + fresh={len(all_current_week_records_from_bq)})")

    return all_comms_oc_records_merged


# ══════════════════════════════════════════════════════════════════════════════
# process_installs_monthly — Installs mensuales FM + Corp (§88)
# ══════════════════════════════════════════════════════════════════════════════

def process_installs_monthly(bq_client, config):
    """Installs mensuales por canal — SSOT: BASE_INSTALLS_LIFECYCLE (§88).

    Fuente: meli-bi-data.SBOX_MKTCORPMP.BASE_INSTALLS_LIFECYCLE
    Verificado contra Corp screenshot: diferencia < 1% en todos los canales.

    FM:   get_installs_monthly_sql()       → por label de hierarchy_nr
    Corp: get_installs_corp_monthly_sql()  → por corp_key / node_id

    NOTA Corp: corp_ucr_eg y corp_pom son nodos padre sin bq_key.
    La query devuelve su node_id directamente como corp_key.
    El processor detecta si el corp_key es un node_id válido (no bq_key)
    y lo popula directamente, marcándolo como 'directly_populated' para
    que la propagación bottom-up no lo sobreescriba con la suma de sus
    hijos (que están vacíos porque la tabla no tiene breakdown de medio).

    Retorna dict con:
      monthly_installs         {label: {yyyymm: int}}
      monthly_installs_mom     {label: {yyyymm: float}}
      installs_months          list[str]
      installs_corp_by_node    {corp_node_id: {yyyymm: int}}
    """
    HIERARCHY_NR      = config['hierarchy_nr']
    HIERARCHY_NR_CORP = config.get('hierarchy_nr_corp_detail', [])
    LABELS = [c['label'] for c in HIERARCHY_NR]

    # ── 1. Query FM ──────────────────────────────────────────────────────────
    print("  Consultando BQ — Installs FM (BASE_INSTALLS_LIFECYCLE)...")
    df_inst = bq_query(bq_client, get_installs_monthly_sql(HIERARCHY_NR))

    monthly_installs = {l: {} for l in LABELS}

    for _, r in df_inst.iterrows():
        lbl = r['INST_CANAL']
        m   = str(r['MONTH_ID'])
        if lbl in monthly_installs:
            monthly_installs[lbl][m] = int(r['INSTALLS'] or 0)

    installs_months = sorted({m for d in monthly_installs.values() for m in d})

    # Propagación bottom-up FM
    for m in installs_months:
        for c in reversed([x for x in HIERARCHY_NR if not x.get('is_leaf')]):
            lbl    = c['label']
            leaves = (get_descendants(c['id'], HIERARCHY_NR)
                      if lbl != 'Total N+R'
                      else [x['label'] for x in HIERARCHY_NR if x.get('is_leaf')])
            monthly_installs[lbl][m] = sum(
                monthly_installs[l].get(m, 0) for l in leaves
            )

    # MoM
    monthly_installs_mom = {}
    for lbl, by_month in monthly_installs.items():
        monthly_installs_mom[lbl] = {}
        ms = sorted(by_month)
        for i, m in enumerate(ms):
            if i > 0:
                prev = by_month.get(ms[i - 1], 0)
                curr = by_month.get(m, 0)
                monthly_installs_mom[lbl][m] = (
                    round((curr - prev) / prev, 4) if prev else None
                )

    # ── 2. Query Corp ────────────────────────────────────────────────────────
    print("  Consultando BQ — Installs Corp (BASE_INSTALLS_LIFECYCLE)...")
    df_corp = bq_query(bq_client, get_installs_corp_monthly_sql())

    all_corp_ids = [c['id'] for c in HIERARCHY_NR_CORP if 'id' in c]
    installs_corp_by_node = {nid: {} for nid in all_corp_ids}

    # Mapeo bq_key → node_id (para nodos con bq_key en el config)
    corp_key_to_node = {c['bq_key']: c['id']
                        for c in HIERARCHY_NR_CORP
                        if 'id' in c and 'bq_key' in c}

    # Set de nodos que se poblan directamente (no sobreescribir en bottom-up)
    directly_populated = set()

    for _, r in df_corp.iterrows():
        corp_key = r['corp_key']
        m        = str(r['fecha_mes_corp'])

        # Prioridad 1: lookup bq_key → node_id
        node_id = corp_key_to_node.get(corp_key)

        # Prioridad 2: corp_key ES directamente un node_id válido
        # (usado para nodos padre sin bq_key: corp_ucr_eg, corp_pom)
        if node_id is None and corp_key in installs_corp_by_node:
            node_id = corp_key

        if node_id and node_id in installs_corp_by_node:
            installs_corp_by_node[node_id][m] = int(r['installs_corp'] or 0)
            directly_populated.add(node_id)

    # Propagación bottom-up Corp
    # SKIP para nodos directamente poblados — su valor viene del query y es correcto.
    # Sus PADRES sí se calculan por suma de hijos (lo que incluye los directamente poblados).
    all_corp_months = sorted({
        m for nd in installs_corp_by_node.values() for m in nd
    })
    for m in all_corp_months:
        for c in reversed([x for x in HIERARCHY_NR_CORP
                           if 'id' in x and not x.get('is_leaf')]):
            nid = c['id']
            if nid in directly_populated:
                # Valor poblado directamente desde el query — no sobreescribir
                continue
            children = [x['id'] for x in HIERARCHY_NR_CORP
                        if 'id' in x and x.get('parent') == nid]
            if not children:
                continue
            installs_corp_by_node[nid][m] = sum(
                installs_corp_by_node.get(ch, {}).get(m, 0) for ch in children
            )

    return {
        'monthly_installs':      monthly_installs,
        'monthly_installs_mom':  monthly_installs_mom,
        'installs_months':       installs_months,
        'installs_corp_by_node': installs_corp_by_node,
    }
