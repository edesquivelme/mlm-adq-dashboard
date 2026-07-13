"""
gen_dashboard_v1.py — Orquestador MLM ADQ N+R Dashboard V1
═══════════════════════════════════════════════════════════
FLUJO COMPLETO:
  1. Carga config/channels_config.json
        └─ hierarchy_nr   → HIERARCHY_NR (canales N+R)
        └─ hierarchy_cost → HIERARCHY_C  (canales Costos)
  2. processors.process_all(config, client)
        └─ llama queries.py → ejecuta 4 SQLs en BQ
        └─ devuelve dict 'data' con todos los datos procesados
  3. load_plan() → lee Excel → plan_nr, plan_lines_data
  4. builders.py → genera HTML (tablas) + JSON (charts Plotly)
  5. Inyecta todo en template_dashboard.html vía {{PLACEHOLDERS}}
        └─ {{CSS}}         ← dashboard.css
        └─ {{TIMESTAMP}}   ← fecha de generación
        └─ {{MOM_TABLE}}   ← HTML tabla MoM
        └─ {{PERF_TABLE}}  ← HTML tabla Performance
        └─ {{DATA_JSON}}   ← datos para el JS del dashboard
        └─ {{CHARTS_JSON}} ← charts Plotly serializados
  6. Escribe dashboard_v1.html (output final autocontenido)

CONVENCIÓN DE NOMBRES (consistente en todos los módulos):
  HIERARCHY_NR  = config['hierarchy_nr']   (canales N+R, fuente DAILY_HISTORICO)
  HIERARCHY_C   = config['hierarchy_cost'] (canales Costos, fuente COSTOS_CANALES)
"""

import sys, os, json, warnings, datetime
import pandas as pd
from google.cloud import bigquery

sys.stdout.reconfigure(encoding='utf-8')
warnings.filterwarnings('ignore')

# ── Rutas ─────────────────────────────────────────────────────
BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
if PROJECT_ROOT not in sys.path: sys.path.append(PROJECT_ROOT)

CONFIG_PATH          = os.path.join(PROJECT_ROOT, 'config', 'channels_config.json')
TEMPLATE_PATH        = os.path.join(BASE_DIR,     'template_dashboard.html')
CSS_PATH             = os.path.join(BASE_DIR,     'dashboard.css')
PLAN_PATH            = os.path.join(PROJECT_ROOT, 'data', 'Resumen Plan Acq 2026.xlsx')
OUT_HTML             = os.path.join(PROJECT_ROOT, 'dashboard_v1.html')
# Tier 1: meses cerrados (update mensual via refresh_comms_oc_cache.py --append)
COMMS_OC_CACHE_PATH  = os.path.join(PROJECT_ROOT, 'data', 'comms_oc_cache.json')
# Tier 2: mes actual — se regenera 1 sola vez por día, luego se reutiliza.
# Eliminar manualmente para forzar re-query: del data\comms_oc_current_month.json
COMMS_OC_CURRENT_MONTH_PATH = os.path.join(PROJECT_ROOT, 'data', 'comms_oc_current_month.json')

def _cs(v):
    """Coerce to str NaN-safe. float NaN es truthy en Python, 'v or default' no funciona."""
    if v is None or (isinstance(v, float) and v != v):
        return ''
    return str(v).strip()

BQ_PROJECT = 'meli-bi-data'
N_PRIOR    = 2

# ── Imports locales ───────────────────────────────────────────
from processors        import (
    process_all,
    process_nr_corp,
    process_nr_corp_daily,
    process_comms_oc,          # Two-Tier: carga cache JSON + query BQ semana actual (History.md §45)
    process_installs_monthly,  # §88: installs FM + Corp
    fmt_month,
    get_descendants,
)
from builders          import (
    build_mom_bar, build_mom_table_html,
    build_perf_bar, build_perf_table_html,
    build_nr_corp_table_html, build_nr_corp_bar_chart,
    build_perf_corp_table_html, build_perf_corp_bar_chart,
    build_comms_oc_table_html,        # Tabla HTML de la pestaña Comms_OC
    build_installs_table_html,         # §88: tabla Installs Mensual (FM)
    build_installs_bar,               # §88: chart barras Installs + CPI
    build_installs_corp_bar_chart,    # §88: chart Corp installs
    build_installs_corp_table_html,   # §88: tabla colapsable Corp installs
    build_install_activation_tab_html, # §89: tab Install → Activation Rate
)
# builders_analysis: HTML estático de pestañas de análisis estratégico (independiente de BQ)
# Actualizar manualmente cuando llegue nuevo dato mensual de 2026
from builders_analysis import build_oc_ucr_analysis_tab_html
from builders        import build_reporting_tab_html
from processors      import process_new_rec_monthly


def load_plan(config, all_months):
    """Carga TODOS los datos de plan desde el Excel 'Resumen Plan Acq 2026.xlsx'.

    El Excel tiene bloques de KPIs separados (ver docs/metrics_logic.md §6):
      · Bloque N+R        → filas referenciadas por 'plan_row'       en channels_config.json
      · Bloque Valor      → filas referenciadas por 'plan_row_valor' en channels_config.json
      · Bloque Inversión  → filas referenciadas por 'plan_row_inv'   en channels_config.json
    Cada índice en channels_config.json es 0-based (pandas iloc).

    Retorna 4 dicts, todos con estructura {canal_label: {yyyymm: valor_int}}:
      · plan_nr         — Plan N+R: lecturas directas de Excel + suma de plan_lines (OC+UCR)
      · plan_lines_data — Sub-líneas del plan N+R (Recurring, Ad-Hoc...) — consumidas por
                          build_mom_table_html() y build_mom_bar() en builders.py
      · plan_valor      — Plan Valor Predicho 90D: lecturas directas + propagación bottom-up
                          para nodos sin fila propia (Ucrania, POM TOTAL suman sus hijos)
      · plan_inv        — Plan Inversión Total (USD): solo lecturas directas; el Excel ya
                          tiene los agregados por canal — sin propagación bottom-up
    Los 4 dicts se inyectan en data{} en assemble() para que builders.py los consuma.
    """
    HIERARCHY_NR = config['hierarchy_nr']
    ALL_CANAL_LABELS = [c['label'] for c in HIERARCHY_NR]
    ID_TO_NODE       = {c['id']: c for c in HIERARCHY_NR}

    # Mapeos iloc_fila → label_canal, uno por bloque KPI del Excel
    EXCEL_ROW_TO_LABEL_NR    = {c['plan_row']:       c['label'] for c in HIERARCHY_NR if 'plan_row'       in c}
    EXCEL_ROW_TO_LABEL_VALOR = {c['plan_row_valor']:  c['label'] for c in HIERARCHY_NR if 'plan_row_valor' in c}
    EXCEL_ROW_TO_LABEL_INV   = {c['plan_row_inv']:    c['label'] for c in HIERARCHY_NR if 'plan_row_inv'   in c}

    # Dicts resultado — separados por KPI de plan para claridad en builders.py
    plan_nr         = {lbl: {} for lbl in ALL_CANAL_LABELS}  # Plan N+R por canal y mes
    plan_lines_data = {}                                      # Sub-líneas N+R (Recurring, Ad-Hoc, etc.)
    plan_valor      = {lbl: {} for lbl in ALL_CANAL_LABELS}  # Plan Valor Predicho por canal y mes
    plan_inv        = {lbl: {} for lbl in ALL_CANAL_LABELS}  # Plan Inversión (USD) por canal y mes

    try:
        df_plan   = pd.read_excel(PLAN_PATH, header=None)
        # Columnas del Excel: 4–15 = ene–dic 2025 (iloc), 18–29 = ene–dic 2026
        excel_cols_2025 = {4+i:  f'2025{i+1:02d}' for i in range(12)}
        excel_cols_2026 = {18+i: f'2026{i+1:02d}' for i in range(12)}
        all_excel_cols  = {**excel_cols_2025, **excel_cols_2026}

        def read_excel_row_into_plan_dict(row_iloc, dest_plan_dict, canal_label):
            """Lee una fila del Excel (por iloc) y la guarda en dest_plan_dict[canal_label]."""
            for col_iloc, month_key in all_excel_cols.items():
                if col_iloc < df_plan.shape[1]:
                    raw_val = df_plan.iloc[row_iloc, col_iloc]
                    dest_plan_dict[canal_label][month_key] = int(round(float(raw_val))) if pd.notna(raw_val) else 0

        # ── Bloque Plan N+R: lecturas directas por canal ──────────────────────
        # Caso estándar: plan_row (int) — una sola fila Excel por canal
        for row_iloc, canal_label in EXCEL_ROW_TO_LABEL_NR.items():
            read_excel_row_into_plan_dict(row_iloc, plan_nr, canal_label)

        # Caso multi-fila: plan_rows (list) — suma de varias filas
        # Ejemplo: POM TOTAL = POM gest (row 5) + POM no gestionado (row 9)
        for canal in HIERARCHY_NR:
            if 'plan_rows' not in canal:
                continue
            for row_iloc in canal['plan_rows']:
                for col_iloc, month_key in all_excel_cols.items():
                    if col_iloc < df_plan.shape[1]:
                        raw_val  = df_plan.iloc[row_iloc, col_iloc]
                        existing = plan_nr[canal['label']].get(month_key, 0)
                        plan_nr[canal['label']][month_key] = (
                            existing + (int(round(float(raw_val))) if pd.notna(raw_val) else 0)
                        )

        # ── Bloque Plan Valor: lecturas directas por canal ────────────────────
        for row_iloc, canal_label in EXCEL_ROW_TO_LABEL_VALOR.items():
            read_excel_row_into_plan_dict(row_iloc, plan_valor, canal_label)

        # ── Bloque Plan Inversión: lecturas directas por canal ────────────────
        # El Excel ya tiene filas de agregados (POM Total, OC+UCR, etc.)
        # No se necesita propagación bottom-up para Inversión
        for row_iloc, canal_label in EXCEL_ROW_TO_LABEL_INV.items():
            read_excel_row_into_plan_dict(row_iloc, plan_inv, canal_label)

        # ── Plan N+R sub-líneas: suma filas del Excel por canal padre ─────────
        # (ej. OC+UCR tiene plan_lines con Plan Recurring + Plan Ad-Hoc + Plan Producto)
        # Estas sub-líneas son consumidas por build_mom_table_html() y build_mom_bar()
        for canal in HIERARCHY_NR:
            if 'plan_lines' not in canal:
                continue
            canal_label = canal['label']
            plan_lines_data[canal_label] = {}
            for sub_line in canal['plan_lines']:
                sub_line_label      = sub_line['label']
                # multiplier: factor de escala para la sub-línea (default 1.0 = sin ajuste)
                # Ejemplo: Plan Producto OC+UCR usa 0.5 porque el otro 50% va a OTHERS
                sub_line_multiplier = sub_line.get('multiplier', 1.0)
                plan_lines_data[canal_label][sub_line_label] = {}
                for sub_row_iloc in sub_line['rows']:
                    for col_iloc, month_key in all_excel_cols.items():
                        if col_iloc < df_plan.shape[1]:
                            raw_val  = df_plan.iloc[sub_row_iloc, col_iloc]
                            existing = plan_lines_data[canal_label][sub_line_label].get(month_key, 0)
                            plan_lines_data[canal_label][sub_line_label][month_key] = (
                                existing + (int(round(float(raw_val) * sub_line_multiplier)) if pd.notna(raw_val) else 0)
                            )
            # Si el nodo padre no tiene plan_row/plan_rows propio, su total N+R = suma de sub-líneas
            if 'plan_row' not in canal and 'plan_rows' not in canal:
                for month_key in all_excel_cols.values():
                    plan_nr[canal_label][month_key] = sum(
                        plan_lines_data[canal_label].get(sl['label'], {}).get(month_key, 0)
                        for sl in canal['plan_lines']
                    )

        # ── Plan Valor propagación bottom-up ──────────────────────────────────
        # Nodos sin plan_row_valor propio (Ucrania, POM TOTAL) suman sus hijos
        # La iteración en reversa garantiza que los hijos ya estén calculados
        for canal in reversed(HIERARCHY_NR):
            if canal.get('is_leaf') or 'plan_row_valor' in canal:
                continue  # Hoja o ya tiene fila directa → no propagar
            canal_label  = canal['label']
            child_labels = [ID_TO_NODE[child_id]['label']
                            for child_id in canal.get('children', [])
                            if child_id in ID_TO_NODE]
            for month_key in all_excel_cols.values():
                plan_valor[canal_label][month_key] = sum(
                    plan_valor[child_label].get(month_key, 0)
                    for child_label in child_labels
                )

        print("  OK: Plan cargado.")
    except Exception as e:
        print(f"  WARNING: No se pudo cargar el Plan. {e}")

    return plan_nr, plan_lines_data, plan_valor, plan_inv


def build_perf_corp_data(config, data):
    """Ensambla perf_corp_data_by_node reutilizando TODOS los dicts de process_all() — CERO queries BQ nuevas.

    Fuente de los mappings: config['hierarchy_cost_corp']['mappings']
      · nr_perf_label    → clave en perf_nr_paid, perf_nr_go, perf_vpu_prod, perf_roa_num
      · cost_inv_label   → clave en monthly_inv_total
      · plan_inv_label   → clave en plan_inv  (de load_plan())
      · plan_valor_label → clave en plan_valor (de load_plan())
      · plan_nr          → plan_nr_corp_by_node[corp_node_id] (de load_plan_corp())

    Retorna:
      perf_corp_data_by_node: { corp_node_id: { yyyymm: {
        actual_nr_total    : int,
        actual_nr_paid     : int,   # N+R con inversión > 0 en COSTOS_CANALES
        actual_nr_go       : int,   # N+R Gest Others (ACTIVATION_OTHER_TEAM)
        actual_vpu_prod    : float, # pre-multiplicado: SUM(VALUE_MKT_PREDICTION_90D_NR_USERS)
        actual_roa_num     : float, # numerador ROA (lógica mixta: COSTOS para UCR/OC, DAILY para POM/MGM)
        actual_inv_total   : float | None,
        plan_inv_for_node  : float | None,  # de plan_inv (load_plan() — no load_plan_corp)
        plan_valor_for_node: float | None,  # de plan_valor
        plan_nr_for_node   : int   | None,  # de plan_nr_corp_by_node (load_plan_corp)
      }}}

    Consumido por: build_perf_corp_table_html() en builders.py
    """
    COST_CORP_MAPPINGS_LIST = config.get('hierarchy_cost_corp', {}).get('mappings', [])
    all_months_available    = data['months']

    # Dicts ya procesados por process_all()
    monthly_inv_total_by_hier_cost_label     = data['monthly_inv_total']        # {hier_cost_label: {yyyymm: float}}
    monthly_inv_canal_by_hier_cost_label     = data.get('monthly_inv_canal',     {})  # Inv. Canal (TC §71)
    monthly_inv_incentivo_by_hier_cost_label = data.get('monthly_inv_incentivo', {})  # Inv. Incentivos (TC §71)
    monthly_inv_mantika_by_hier_cost_label   = data.get('monthly_inv_mantika',   {})  # Inv. Mantika (TC §71)
    perf_nr_paid_by_hier_nr_label         = data['perf_nr_paid']        # {hier_nr_label:   {yyyymm: int}}
    perf_nr_go_by_hier_nr_label           = data['perf_nr_go']          # {hier_nr_label:   {yyyymm: int}}
    perf_vpu_prod_by_hier_nr_label        = data['perf_vpu_prod']       # {hier_nr_label:   {yyyymm: float}}
    perf_roa_num_by_hier_nr_label         = data['perf_roa_num']        # {hier_nr_label:   {yyyymm: float}}
    # Planes cargados por load_plan()
    plan_inv_by_hier_nr_label             = data.get('plan_inv',   {})  # {hier_nr_label:   {yyyymm: int}}
    plan_valor_by_hier_nr_label           = data.get('plan_valor', {})  # {hier_nr_label:   {yyyymm: int}}
    # Plan N+R corp (de load_plan_corp() — indexado por corp_node_id)
    plan_nr_corp_by_node_id               = data.get('plan_nr_corp_by_node', {})
    # N+R real corp (de process_nr_corp() — indexado por corp_node_id)
    monthly_nr_corp_by_node_id            = data['monthly_nr_corp_by_node']

    perf_corp_data_by_node = {}

    for cost_corp_mapping in COST_CORP_MAPPINGS_LIST:
        corp_node_id_for_mapping  = cost_corp_mapping['corp_node_id']
        nr_perf_label             = cost_corp_mapping.get('nr_perf_label')      # hierarchy_nr label
        cost_inv_label            = cost_corp_mapping.get('cost_inv_label')     # hierarchy_cost label
        plan_inv_label            = cost_corp_mapping.get('plan_inv_label')     # hierarchy_nr label
        plan_valor_label          = cost_corp_mapping.get('plan_valor_label')   # hierarchy_nr label

        perf_corp_data_by_node[corp_node_id_for_mapping] = {}

        for month in all_months_available:
            # N+R real corp: desde monthly_nr_corp_by_node (datos corp exactos, AP1+AP2+TOUCHPOINT)
            actual_nr_total_this_month = monthly_nr_corp_by_node_id.get(corp_node_id_for_mapping, {}).get(month, 0)

            # N+R Paid / Gest Others: desde perf_nr_paid/go indexado por hierarchy_nr label
            actual_nr_paid_this_month = (perf_nr_paid_by_hier_nr_label.get(nr_perf_label, {}).get(month, 0)
                                         if nr_perf_label else 0)
            actual_nr_go_this_month   = (perf_nr_go_by_hier_nr_label.get(nr_perf_label, {}).get(month, 0)
                                         if nr_perf_label else 0)

            # VPU pre-multiplicado (= Valor total pred)
            actual_vpu_prod_this_month = (perf_vpu_prod_by_hier_nr_label.get(nr_perf_label, {}).get(month, 0)
                                          if nr_perf_label else 0)

            # ROA numerador (lógica mixta según canal — ver perf_roa_num en process_all)
            actual_roa_num_this_month  = (perf_roa_num_by_hier_nr_label.get(nr_perf_label, {}).get(month, 0)
                                          if nr_perf_label else 0)

            # Inversión total real + desglose Canal/Incentivos/Mantika (TC §71)
            actual_inv_total_this_month     = (monthly_inv_total_by_hier_cost_label.get(cost_inv_label, {}).get(month)
                                               if cost_inv_label else None)
            actual_inv_canal_this_month     = (monthly_inv_canal_by_hier_cost_label.get(cost_inv_label, {}).get(month)
                                               if cost_inv_label else None)
            actual_inv_incentivo_this_month = (monthly_inv_incentivo_by_hier_cost_label.get(cost_inv_label, {}).get(month)
                                               if cost_inv_label else None)
            actual_inv_mantika_this_month   = (monthly_inv_mantika_by_hier_cost_label.get(cost_inv_label, {}).get(month)
                                               if cost_inv_label else None)

            # Plan Inversión (de load_plan() via plan_row_inv en hierarchy_nr)
            plan_inv_value_this_month   = (plan_inv_by_hier_nr_label.get(plan_inv_label, {}).get(month)
                                           if plan_inv_label else None)

            # Plan Valor Predicho (de load_plan() via plan_row_valor en hierarchy_nr)
            plan_valor_value_this_month = (plan_valor_by_hier_nr_label.get(plan_valor_label, {}).get(month)
                                           if plan_valor_label else None)

            # Plan N+R (de load_plan_corp() — indexado por corp_node_id)
            plan_nr_value_this_month    = plan_nr_corp_by_node_id.get(corp_node_id_for_mapping, {}).get(month)

            perf_corp_data_by_node[corp_node_id_for_mapping][month] = {
                'actual_nr_total':     actual_nr_total_this_month,
                'actual_nr_paid':      actual_nr_paid_this_month,
                'actual_nr_go':        actual_nr_go_this_month,
                'actual_vpu_prod':     actual_vpu_prod_this_month,   # pre-mult = Valor total
                'actual_roa_num':      actual_roa_num_this_month,
                'actual_inv_total':     actual_inv_total_this_month,
                'actual_inv_canal':     actual_inv_canal_this_month,
                'actual_inv_incentivo': actual_inv_incentivo_this_month,
                'actual_inv_mantika':   actual_inv_mantika_this_month,
                'plan_inv_for_node':   plan_inv_value_this_month,
                'plan_valor_for_node': plan_valor_value_this_month,
                'plan_nr_for_node':    plan_nr_value_this_month,
            }

    return perf_corp_data_by_node


def load_plan_corp(config):
    """Carga el plan específico para la tabla Corporativa (sección Detalle por Canal).

    Es COMPLETAMENTE INDEPENDIENTE de load_plan() — no lee ni modifica plan_nr.
    No afecta la pestaña NR Mensual ni ningún otro componente del dashboard.

    Lee 'hierarchy_PLAN_Corp' de config, que define qué filas iloc del Excel
    corresponden a cada corp_node_id, con lógica propia (distinta de hierarchy_nr):
      · corp_oc_ucr  = rows [6, 10]    (OC Recurring + OC Adhoc)
      · corp_pom     = rows [5, 9]     (POM gest + POM no gestionado)
      · corp_ucr_prd = row  [17]       (Others + Producto)
      · corp_mgm     = row  [13]
      · corp_lp      = row  [16]
      · corp_noatrib = row  [18]
      · corp_total   = row  [4]

    Retorna:
      plan_nr_corp_by_node: dict { corp_node_id: { yyyymm: plan_int } }
        Consumido por build_nr_corp_table_html() en builders.py para mostrar
        las filas 'Plan' y 'vs Plan' en la tabla corporativa.
    """
    # Leer los mappings del config (hierarchy_PLAN_Corp.mappings)
    plan_corp_mappings_list = config.get('hierarchy_PLAN_Corp', {}).get('mappings', [])
    plan_nr_corp_by_node    = {}

    try:
        df_plan_excel   = pd.read_excel(PLAN_PATH, header=None)
        excel_cols_2025 = {4+i:  f'2025{i+1:02d}' for i in range(12)}
        excel_cols_2026 = {18+i: f'2026{i+1:02d}' for i in range(12)}
        all_excel_cols  = {**excel_cols_2025, **excel_cols_2026}

        for corp_plan_mapping in plan_corp_mappings_list:
            corp_node_id_for_plan = corp_plan_mapping['corp_node_id']
            excel_rows_to_sum     = corp_plan_mapping['excel_rows']   # list of iloc indices

            plan_nr_corp_by_node[corp_node_id_for_plan] = {}

            for col_iloc, month_key in all_excel_cols.items():
                if col_iloc >= df_plan_excel.shape[1]:
                    continue
                # Sumar todas las filas definidas para este nodo corp (plan_type direct_row o sum_rows)
                total_plan_value_this_month = 0
                for row_iloc_in_plan in excel_rows_to_sum:
                    if row_iloc_in_plan < df_plan_excel.shape[0]:
                        raw_excel_val = df_plan_excel.iloc[row_iloc_in_plan, col_iloc]
                        total_plan_value_this_month += float(raw_excel_val) if pd.notna(raw_excel_val) else 0

                plan_nr_corp_by_node[corp_node_id_for_plan][month_key] = int(round(total_plan_value_this_month))

        print("  OK: Plan Corp (hierarchy_PLAN_Corp) cargado.")
    except Exception as e:
        print(f"  WARNING: No se pudo cargar el Plan Corp. {e}")

    return plan_nr_corp_by_node


def summarize_comms_by_month(comms_oc_records_list):
    """Agrega registros de Comms_OC por YYYYMM para el análisis OC+UCR.

    PROPÓSITO: conectar datos de comunicaciones (Comms_OC) con KPIs de performance
    en la pestaña Análisis OC+UCR. Permite mostrar en una sola tabla:
      "Lo que enviaste (Comms) → Lo que obtuviste (KPIs)"

    DEDUPLICACIÓN:
      - TOTAL_*_CUST_EVENT: suma directa por COMMUNICATION_ID (cada comm es única)
      - USER_INC / VALUE_INC: deduplicado por CAMPAIGN_NAME_CLEAN × MES
        (métricas de campaña se repiten para cada COMM_ID de la misma campaña)

    RETORNA:
      dict { 'YYYYMM': {
        'n_comms': int,          # comunicaciones únicas del mes
        'n_campaigns': int,       # campañas únicas (deduplicated)
        'total_test': int,        # usuarios únicos alcanzados (funnel step 1)
        'total_arrived': int,     # usuarios que recibieron la comm
        'total_shown': int,       # usuarios que la vieron
        'total_open': int,        # usuarios que la abrieron
        'open_rate': float,       # open/test × 100 (%)
        'total_user_inc': float,  # usuarios incrementales totales del mes
        'total_value_inc': float, # valor incremental USD totales
        'top3': [                 # top 3 campañas por USER_INC
          {'name': str, 'canal': str, 'user_inc': int, 'lift': float}
        ]
      }}
    """
    import datetime as _dt
    from collections import defaultdict

    # ── Helpers internos ──────────────────────────────────────────────────────
    def _week_of_month(date_str):
        """Clasifica una fecha 'YYYY-MM-DD' en S1/S2/S3/S4."""
        try:
            day = int(date_str[8:10])
            if day <= 7:   return 'S1'
            if day <= 16:  return 'S2'
            if day <= 22:  return 'S3'
            return 'S4'
        except (TypeError, ValueError, IndexError):
            return 'S?'

    def _dow(date_str):
        """Devuelve día de semana abreviado (Lun/Mar/…) de una fecha 'YYYY-MM-DD'."""
        DOW_ES = {0:'Lun',1:'Mar',2:'Mié',3:'Jue',4:'Vie',5:'Sáb',6:'Dom'}
        try:
            d = _dt.date.fromisoformat(date_str)
            return DOW_ES[d.weekday()]
        except (TypeError, ValueError):
            return '?'

    def _init_breakdown_slot():
        return {'n': 0, 'test': 0, 'open': 0, 'user_inc': 0.0, 'lift_sum': 0.0, 'lift_n': 0}

    # ── Estructuras de acumulación ────────────────────────────────────────────
    monthly_comm_ids   = defaultdict(set)    # unique COMMUNICATION_IDs por mes
    monthly_campaigns  = defaultdict(dict)   # {month: {campaign_name: metrics}} — deduplicado
    monthly_events     = defaultdict(lambda: {'create': 0, 'test': 0, 'arrived': 0, 'shown': 0, 'open': 0})
    # Breakdowns multidimensionales (analizar-OC_Comms_skill.md §Modo 11)
    monthly_canal_bd   = defaultdict(lambda: defaultdict(_init_breakdown_slot))  # month → canal
    monthly_bl_bd      = defaultdict(lambda: defaultdict(_init_breakdown_slot))  # month → BL
    monthly_dow_bd     = defaultdict(lambda: defaultdict(_init_breakdown_slot))  # month → DoW
    monthly_week_bd    = defaultdict(lambda: defaultdict(_init_breakdown_slot))  # month → S1/S2/S3/S4
    # Top campañas por (strategy × canal) — alimenta comms_monthly_summary.md §Top por combo
    # Clave: 'STRATEGY|CANAL' (ej. 'UCRANIA|PUSH'). Valor: {campaign_name: full_record_dict}
    # Deduplicado por CAMPAIGN_NAME_CLEAN igual que monthly_campaigns.
    monthly_combo_camps = defaultdict(lambda: defaultdict(dict))  # month → combo_key → {camp: data}

    for record in comms_oc_records_list:
        month   = str(record.get('MONTH_ID', ''))
        comm_id = str(record.get('COMMUNICATION_ID', ''))
        campaign = (
            _cs(record.get('CAMPAIGN_NAME_CLEAN'))
            or _cs(record.get('CAMPAIGN_NAME'))
            or 'Sin nombre'
        )
        if not month or not comm_id:
            continue

        # Dimensiones de segmentación
        canal_dim = (_cs(record.get('CANAL')) or 'SIN_CANAL').upper()
        # BUSINESS_LINE = nuevo nombre (renombrado de CHANNELS_METRICS en queries.py).
        # Fallback a CHANNELS_METRICS para compatibilidad con registros del cache antiguo.
        bl_dim    = (_cs(record.get('BUSINESS_LINE')) or
                     _cs(record.get('CHANNELS_METRICS')) or
                     _cs(record.get('BUSINESS_LINE_SEGMENT_CHANNELS')) or 'SIN_BL')
        date_str  = str(record.get('FIRST_SENT_DATE') or '')
        dow_dim   = _dow(date_str)
        week_dim  = _week_of_month(date_str)

        # Contar comunicaciones únicas (por COMMUNICATION_ID)
        monthly_comm_ids[month].add(comm_id)

        # Sumar eventos del funnel (uno por comunicación, no por campaña)
        test_val = int(record.get('TOTAL_TEST_CUST_EVENT')  or 0)
        open_val = int(record.get('TOTAL_OPEN_CUST_EVENT')  or 0)
        monthly_events[month]['test']    += test_val
        monthly_events[month]['create']  += int(record.get('TOTAL_CREATE_CUST_EVENT')  or 0)
        monthly_events[month]['arrived'] += int(record.get('TOTAL_ARRIVED_CUST_EVENT') or 0)
        monthly_events[month]['shown']   += int(record.get('TOTAL_SHOWN_CUST_EVENT')   or 0)
        monthly_events[month]['open']    += int(record.get('TOTAL_OPEN_CUST_EVENT')    or 0)

        # Métricas de campaña: solo guardar el PRIMER registro de cada campaña
        # (USER_INC está a nivel CAMPAIGN × MES, se repite por cada COMM_ID)
        def _safe_float(v):
            try:
                f = float(v) if v is not None else 0.0
                return f if f == f and abs(f) < 1e15 else 0.0  # NaN/Inf check
            except (TypeError, ValueError):
                return 0.0

        lift_raw   = _safe_float(record.get('M_LIFT'))
        ui_raw     = _safe_float(record.get('USER_INC'))
        strategy_v = (_cs(record.get('STRATEGIES')) or '').split(' | ')[0].strip() or 'SIN_STRATEGY'
        combo_key  = f"{strategy_v}|{canal_dim}"   # ej. 'UCRANIA|PUSH', 'ACQUISITION|EMAIL'

        if campaign not in monthly_campaigns[month]:
            monthly_campaigns[month][campaign] = {
                'user_inc':  ui_raw,
                'value_inc': _safe_float(record.get('VALUE_INC')),
                'lift':      lift_raw,
                'canal':     record.get('CANAL') or '—',
            }
            # Acumular en el combo (strategy × canal) para comms_monthly_summary.md
            # Guardamos los campos clave para el JUEZ: wording, métricas de eficiencia
            if campaign not in monthly_combo_camps[month][combo_key]:
                or_val_raw  = _safe_float(record.get('OPEN_RATE'))
                # Fingerprint completo para análisis de outliers del JUEZ.
                # Incluye TODOS los campos necesarios para que el OPTIMIZADOR pueda decir:
                # "esta comm funcionó porque: App=X, Canal=Y, sent día Z (DoW), semana S2,
                #  NotifType=RECURRING, BL=UCR_GESTION, Título=..."
                monthly_combo_camps[month][combo_key][campaign] = {
                    'name':       campaign,
                    'date':       str(record.get('FIRST_SENT_DATE') or '')[:10],  # YYYY-MM-DD
                    'dow':        _dow(str(record.get('FIRST_SENT_DATE') or '')),   # Lun/Mar/...
                    'week':       _week_of_month(str(record.get('FIRST_SENT_DATE') or '')),  # S1-S4
                    'canal':      record.get('CANAL') or '—',
                    'app':        record.get('APP') or '—',
                    'strategy':   strategy_v,
                    'substrat':   (_cs(record.get('SUBSTRATEGIES')) or '').split(' | ')[0].strip() or '—',
                    'biz_line':   (_cs(record.get('BUSINESS_LINE')) or _cs(record.get('CHANNELS_METRICS')) or '—')[:50],
                    'type_name':  record.get('TYPE_NAME') or '—',
                    'notif_type': record.get('NOTIFICATION_TYPE') or '—',
                    'team':       record.get('TEAM') or '—',
                    'title':      _cs(record.get('NOTIFICATION_TITLE'))[:100],
                    'text':       _cs(record.get('NOTIFICATION_TEXT'))[:150],
                    'user_inc':   ui_raw,
                    'lift_pct':   round(lift_raw * 100, 3),
                    'or_pct':     round(or_val_raw * 100, 1) if or_val_raw and or_val_raw < 1 else round(or_val_raw, 1) if or_val_raw else 0.0,
                    'test':       int(record.get('TOTAL_TEST_CUST_EVENT') or 0),
                    'value_inc':  _safe_float(record.get('VALUE_INC')),
                }

        # ── Breakdowns multidimensionales (una entrada por COMM_ID, no por campaña) ──
        # USER_INC se aproxima dividiendo el valor de campaña entre el n° de comms que la comparten.
        # El conteo de comms por canal/BL/DoW/semana es exacto; los valores de lift son exactos por comm.
        for bd, dim in (
            (monthly_canal_bd[month], canal_dim),
            (monthly_bl_bd[month],    bl_dim),
            (monthly_dow_bd[month],   dow_dim),
            (monthly_week_bd[month],  week_dim),
        ):
            s = bd[dim]
            s['n']        += 1
            s['test']     += test_val
            s['open']     += open_val
            if lift_raw != 0:
                s['lift_sum'] += lift_raw * 100  # convertir a % igual que avg_lift_pct
                s['lift_n']   += 1
            s['user_inc'] += ui_raw

    # Construir resultado final por mes
    result = {}
    for month in monthly_comm_ids:
        camps        = monthly_campaigns[month]
        total_ui     = sum(c['user_inc']  for c in camps.values())
        total_vi     = sum(c['value_inc'] for c in camps.values())
        evts         = monthly_events[month]
        total_test   = evts['test']
        open_rate    = round(evts['open'] / total_test * 100, 1) if total_test > 0 else 0.0

        # Top 3 campañas por USER_INC (ordenado descendente)
        top3_sorted = sorted(
            ((name, m) for name, m in camps.items() if m['user_inc'] > 0),
            key=lambda x: x[1]['user_inc'],
            reverse=True
        )[:3]
        top3 = [
            {
                'name':     (name[:48] + '…') if len(name) > 48 else name,
                'canal':    m['canal'],
                'user_inc': round(m['user_inc']),
                'lift':     round(m['lift'] * 100, 2),  # lift como %
            }
            for name, m in top3_sorted
        ]

        def _safe_round(v, decimals=0):
            """round() seguro contra NaN, Inf y tipos no numéricos."""
            try:
                f = float(v)
                if f != f or abs(f) > 1e15:  # NaN o Inf
                    return 0
                return round(f, decimals) if decimals else int(round(f))
            except (TypeError, ValueError):
                return 0

        n_comms         = len(monthly_comm_ids[month])
        total_create    = evts['create']
        total_arrived   = evts['arrived']
        total_shown     = evts['shown']
        total_open      = evts['open']
        user_inc_safe   = _safe_round(total_ui)
        value_inc_safe  = _safe_round(total_vi, 2)

        # Métricas derivadas del funnel (ver OPTIMIZADOR-OC_skill.md §Dimensión 6)
        # Efficiency Score = NR incremental por comunicación enviada (sweet spot detector)
        efficiency_score = round(user_inc_safe / n_comms, 1) if n_comms > 0 else 0.0
        # Delivery Rate = % de usuarios alcanzados que efectivamente recibieron la comm
        delivery_rate    = round(total_arrived / total_test  * 100, 1) if total_test   > 0 else 0.0
        # Visibility Rate = % de entregados que vieron el mensaje
        visibility_rate  = round(total_shown   / total_arrived * 100, 1) if total_arrived > 0 else 0.0
        # VPU Incremental = valor USD por usuario incremental (calidad del NR adquirido)
        vpu_incremental  = round(value_inc_safe / user_inc_safe, 2) if user_inc_safe > 0 else 0.0
        # avg_lift_pct = LIFT promedio en % (M_LIFT viene como fracción 0.001 = 0.1%, ×100 para %)
        # Mismo factor que en top3: m['lift'] * 100 = lift como porcentaje
        lifts = [c['lift'] for c in camps.values() if c['lift'] != 0]
        avg_lift_pct = round(sum(lifts) / len(lifts) * 100, 3) if lifts else 0.0

        # ── Procesar breakdowns multidimensionales → dicts {dim: {or, lift, user_inc, n}} ──
        def _compile_breakdown(raw_bd):
            """raw_bd: {dim_value: {n, test, open, lift_sum, lift_n, user_inc}}
            Retorna: {dim_value: {n, test, open, lift_sum, lift_n, or_pct, avg_lift_pct, user_inc}}
            Mantiene los valores raw (test, open, lift_sum, lift_n) para poder agregar entre meses
            en builders_analysis.py. Ordenado por user_inc desc.
            """
            compiled = {}
            for dim_val, s in raw_bd.items():
                or_pct   = round(s['open'] / s['test'] * 100, 1) if s['test'] > 0 else 0.0
                avg_lift = round(s['lift_sum'] / s['lift_n'], 2) if s['lift_n'] > 0 else 0.0
                compiled[dim_val] = {
                    'n':             s['n'],
                    # Raw values para re-agregar entre meses
                    'test':          s['test'],
                    'open':          s['open'],
                    'lift_sum':      round(s['lift_sum'], 3),
                    'lift_n':        s['lift_n'],
                    # Métricas derivadas (ya calculadas para acceso rápido)
                    'or_pct':        or_pct,
                    'avg_lift_pct':  avg_lift,    # ya en % (lift_sum fue ×100 en el loop)
                    'user_inc':      round(s['user_inc']),
                }
            return dict(sorted(compiled.items(), key=lambda x: x[1]['user_inc'], reverse=True))

        result[month] = {
            'n_comms':          n_comms,
            'n_campaigns':      len(camps),
            # Funnel absoluto (CREATE → TEST → ARRIVED → SHOWN → OPEN)
            'total_create':     total_create,
            'total_test':       total_test,
            'total_arrived':    total_arrived,
            'total_shown':      total_shown,
            'total_open':       total_open,
            # Métricas de eficiencia del funnel (ver analizar-OC_Comms_skill.md §Modo 9)
            'open_rate':        open_rate,
            'delivery_rate':    delivery_rate,
            'visibility_rate':  visibility_rate,
            'efficiency_score': efficiency_score,
            'avg_lift_pct':     avg_lift_pct,
            'vpu_incremental':  vpu_incremental,
            # Impacto
            'total_user_inc':   user_inc_safe,
            'total_value_inc':  value_inc_safe,
            'top3':             top3,
            # Breakdowns multidimensionales (analizar-OC_Comms_skill.md §Modo 11)
            # Cada dict: {dim_value: {n, test, or_pct, avg_lift_pct, user_inc}}
            'canal_breakdown':  _compile_breakdown(dict(monthly_canal_bd[month])),
            'bl_breakdown':     _compile_breakdown(dict(monthly_bl_bd[month])),
            'dow_breakdown':    _compile_breakdown(dict(monthly_dow_bd[month])),
            'week_breakdown':   _compile_breakdown(dict(monthly_week_bd[month])),
            # Top campañas por Strategy×Canal — para OPTIMIZADOR-OC_skill.md §cruce_funnel
            # Ordenadas por USER_INC desc dentro de cada combo. Incluye wordings.
            'top_by_combo':     {
                combo: sorted(camps.values(), key=lambda c: c['user_inc'], reverse=True)[:10]
                for combo, camps in monthly_combo_camps[month].items()
                if camps
            },
        }

    return result


def generate_comms_monthly_summary_md(comms_monthly_summary_dict, output_path):
    """Genera skills/comms_monthly_summary.md a partir del dict de agregación mensual.

    PROPÓSITO: crear el "archivo puente" que el OPTIMIZADOR-OC_skill.md lee SIEMPRE
    para conectar datos reales de comunicaciones con los KPIs de performance.
    Este archivo se auto-actualiza en cada refresh del dashboard (2x/día).

    FORMAT: Markdown legible por humanos y por LLMs — cada mes tiene:
      - Volumen: N° de comunicaciones y campañas únicas del mes
      - Funnel: TEST → ARRIVED → SHOWN → OPEN y Open Rate real
      - Impacto: USER_INC total y VALUE_INC total del mes
      - Top 3 campañas por USER_INC: nombre, canal, user_inc, lift
    """
    MONTHS_ES = {
        '01': 'Enero', '02': 'Febrero', '03': 'Marzo', '04': 'Abril',
        '05': 'Mayo', '06': 'Junio', '07': 'Julio', '08': 'Agosto',
        '09': 'Septiembre', '10': 'Octubre', '11': 'Noviembre', '12': 'Diciembre',
    }

    def fmt_n(v):
        if v >= 1_000_000: return f'{v/1_000_000:.2f}M'
        if v >= 1_000:     return f'{v/1_000:.1f}K'
        return str(v)

    # Ordenar meses cronológicamente (YYYYMM como string ordena correctamente)
    sorted_months = sorted(comms_monthly_summary_dict.keys())
    if not sorted_months:
        return  # Sin datos, no generar el archivo

    first_month = sorted_months[0]
    last_month  = sorted_months[-1]

    lines = [
        '# Comms_OC Monthly Summary — Puente Comms × KPIs',
        '## Para uso exclusivo de OPTIMIZADOR-OC_skill.md y analizar-OC_Comms_skill.md',
        f'## Actualizado: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M")} | '
        f'Cobertura: {first_month} → {last_month}',
        '',
        '> **INSTRUCCIÓN PARA EL SKILL**: Leer este archivo SIEMPRE junto con',
        '> `analizar-Optimizar_Performance_KPIs_context.md`.',
        '> Este archivo conecta LO QUE SE ENVIÓ (comunicaciones) con LO QUE SE OBTUVO (KPIs).',
        '> Sin él, el análisis es incompleto. Con él, el OPTIMIZADOR puede hacer el cruce real.',
        '',
        '---',
        '',
    ]

    for month_key in sorted_months:
        s = comms_monthly_summary_dict[month_key]
        year = month_key[:4]
        mon  = month_key[4:6]
        label = f"{MONTHS_ES.get(mon, mon)} {year}"

        # Funnel ratios
        total_test = s['total_test']
        arrived_pct = round(s['total_arrived'] / total_test * 100, 1) if total_test > 0 else 0
        shown_pct   = round(s['total_shown']   / total_test * 100, 1) if total_test > 0 else 0

        # Top 3 campañas
        top3_lines = []
        for i, camp in enumerate(s['top3'], 1):
            sign = '+' if camp['lift'] >= 0 else ''
            top3_lines.append(
                f"  {i}. [{camp['name']}] Canal: {camp['canal']} "
                f"→ **+{camp['user_inc']:,} users** | Lift: {sign}{camp['lift']:.2f}%"
            )

        lines += [
            f"## {month_key} — {label}",
            f"- **Comunicaciones**: {s['n_comms']:,} únicas | **Campañas únicas**: {s['n_campaigns']:,}",
            f"- **Funnel**: TEST {fmt_n(s['total_test'])} "
            f"→ ARRIVED {fmt_n(s['total_arrived'])} ({arrived_pct}%) "
            f"→ SHOWN {fmt_n(s['total_shown'])} ({shown_pct}%) "
            f"→ OPEN {fmt_n(s['total_open'])} | **Open Rate: {s['open_rate']:.1f}%**",
            f"- **USER_INC total**: +{s['total_user_inc']:,} | "
            f"**VALUE_INC**: ${s['total_value_inc']:,.0f} USD",
        ]

        if top3_lines:
            lines.append('- **Top 3 campañas por USER_INC**:')
            lines.extend(top3_lines)

        # Métricas de eficiencia del funnel
        lines += [
            f"- **Eficiencia**: Delivery {s.get('delivery_rate', 0):.1f}% | "
            f"Visibility {s.get('visibility_rate', 0):.1f}% | "
            f"Lift avg {s.get('avg_lift_pct', 0):.2f}% | "
            f"Score {s.get('efficiency_score', 0):.1f} NR/comm | "
            f"VPU inc. ${s.get('vpu_incremental', 0):.1f}",
        ]

        # Breakdown por canal (top 5)
        canal_bd = s.get('canal_breakdown', {})
        if canal_bd:
            top_canales = list(canal_bd.items())[:5]
            canal_strs  = [f"{k}: {v['n']} comms, OR {v['or_pct']:.1f}%, Lift {v['avg_lift_pct']:.2f}%, +{v['user_inc']:,} UI"
                           for k, v in top_canales]
            lines.append(f"- **Por Canal**: {' | '.join(canal_strs)}")

        # Breakdown por semana del mes (S1-S4)
        week_bd = s.get('week_breakdown', {})
        if week_bd:
            # Ordenar S1→S4
            worder = {'S1': 0, 'S2': 1, 'S3': 2, 'S4': 3}
            week_sorted = sorted(week_bd.items(), key=lambda x: worder.get(x[0], 9))
            week_strs   = [f"{k}: {v['n']} comms, OR {v['or_pct']:.1f}%, +{v['user_inc']:,} UI"
                           for k, v in week_sorted]
            lines.append(f"- **Por Semana del mes**: {' | '.join(week_strs)}")

        # Breakdown por día de semana (top 5)
        dow_bd = s.get('dow_breakdown', {})
        if dow_bd:
            dorder = {'Lun': 0, 'Mar': 1, 'Mié': 2, 'Jue': 3, 'Vie': 4, 'Sáb': 5, 'Dom': 6}
            dow_sorted = sorted(dow_bd.items(), key=lambda x: dorder.get(x[0], 9))
            dow_strs   = [f"{k}: {v['n']} comms, OR {v['or_pct']:.1f}%" for k, v in dow_sorted]
            lines.append(f"- **Por Día de semana**: {' | '.join(dow_strs)}")

        # Breakdown por BL (top 5)
        bl_bd = s.get('bl_breakdown', {})
        if bl_bd:
            top_bl    = list(bl_bd.items())[:5]
            bl_strs   = [f"{k[:40]}: {v['n']} comms, Lift {v['avg_lift_pct']:.2f}%, +{v['user_inc']:,} UI"
                         for k, v in top_bl]
            lines.append(f"- **Por BL**: {' | '.join(bl_strs)}")

        # ── TOP CAMPAÑAS POR STRATEGY × CANAL (el dato más valioso para el JUEZ) ──
        # Permite al JUEZ responder: "¿Qué comm específica causó el KPI de este mes?"
        top_by_combo = s.get('top_by_combo', {})
        if top_by_combo:
            lines.append('')
            lines.append('### Top campañas por Strategy × Canal')
            lines.append('*(Para cruce KPI → Campaña específica — OPTIMIZADOR-OC_skill.md §cruce_funnel)*')
            lines.append('')

            # Ordenar combos por USER_INC total desc
            combos_sorted = sorted(
                top_by_combo.items(),
                key=lambda x: sum(c['user_inc'] for c in x[1]),
                reverse=True
            )

            # Calcular promedio de USER_INC para detectar outliers
            all_user_incs = [c['user_inc'] for c in list(top_by_combo.values())[0]
                             if c['user_inc'] > 0] if top_by_combo else []
            global_avg_ui = (sum(all_user_incs) / len(all_user_incs)) if all_user_incs else 1
            OUTLIER_THRESHOLD = 5.0  # 5x el promedio = outlier estratégico

            for combo_key, camps_list in combos_sorted[:10]:  # top 10 combos
                total_ui_combo = sum(c['user_inc'] for c in camps_list)
                n_combo = len(camps_list)
                avg_ui_combo = total_ui_combo / n_combo if n_combo > 0 else 0
                lines.append(f"**{combo_key}** ({n_combo} comms, Σ USER_INC: {total_ui_combo:+,.0f}, avg: {avg_ui_combo:+,.0f}):")

                for i, c in enumerate(camps_list[:10], 1):  # top 10 por combo
                    # Clasificar: outlier estratégico, positiva, negativa, neutra
                    is_outlier = c['user_inc'] > global_avg_ui * OUTLIER_THRESHOLD and c['user_inc'] > 5000
                    if is_outlier:
                        flag = '🚀 OUTLIER'
                    elif c['user_inc'] > 100:
                        flag = '✅'
                    elif c['user_inc'] < 0:
                        flag = '🔴 NEGATIVA (CANIBALIZADOR)'
                    elif c['user_inc'] < 10:
                        flag = '⚪ neutra'
                    else:
                        flag = '🟡'

                    # Fingerprint completo para el JUEZ
                    title_str = f'"{c["title"]}"' if c.get('title') else '(sin título)'
                    text_str  = f'"{c["text"][:100]}"' if c.get('text') else ''
                    lines.append(
                        f"  {i}. {flag} **{c['name']}**"
                    )
                    lines.append(
                        f"     USER_INC: {c['user_inc']:+,.0f} | OR: {c['or_pct']:.1f}% "
                        f"| LIFT: {c['lift_pct']:+.3f}% | TEST: {fmt_n(c['test'])}"
                        f" | VALUE_INC: ${c.get('value_inc', 0):,.0f}"
                    )
                    lines.append(
                        f"     Fecha: {c.get('date','?')} ({c.get('dow','?')}, {c.get('week','?')}) "
                        f"| App: {c.get('app','?')} | Canal: {c.get('canal','?')}"
                    )
                    lines.append(
                        f"     Strategy: {c.get('strategy','?')} | SubStrat: {c.get('substrat','?')} "
                        f"| BL: {c.get('biz_line','?')} | TypeName: {c.get('type_name','?')} "
                        f"| NotifType: {c.get('notif_type','?')} | Team: {c.get('team','?')}"
                    )
                    lines.append(f"     Título: {title_str}")
                    if text_str:
                        lines.append(f"     Texto: {text_str}")
                    if is_outlier:
                        lines.append(
                            f"     ⚠️  OUTLIER ESTRATÉGICO: {c['user_inc']:,.0f} USER_INC = "
                            f"{c['user_inc']/max(global_avg_ui,1):.0f}x el promedio global. "
                            f"Analizar con OPTIMIZADOR Modo 5 (cruce)."
                        )
                    lines.append('')

                lines.append('')

        lines += ['---', '']

    lines += [
        f'*Generado automáticamente por `gen_dashboard_v1.py` · '
        f'Datos: Comms_OC cache ({last_month})*',
    ]

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print(f"  OK skills/comms_monthly_summary.md generado ({len(sorted_months)} meses)")


def assemble():
    # ── 1. Config ─────────────────────────────────────────────
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        config = json.load(f)
    HIERARCHY_NR = config['hierarchy_nr']
    HIERARCHY_C  = config['hierarchy_cost']
    LABELS       = [c['label'] for c in HIERARCHY_NR]
    COST_LABELS  = [c['label'] for c in HIERARCHY_C]

    # ── 2. BQ + procesamiento (queries.py + processors.py) ────
    client = bigquery.Client(project=BQ_PROJECT)
    data   = process_all(config, client, N_PRIOR)

    # ── 3. Plan Excel ─────────────────────────────────────────
    print(">>> Paso 3: Cargando Plan desde Excel...")
    plan_nr, plan_lines_data, plan_valor, plan_inv = load_plan(config, data['months'])
    # Inyectar en data para que builders los consuman desde data dict
    data['plan_nr']    = plan_nr
    data['plan_valor'] = plan_valor
    data['plan_inv']   = plan_inv

    # ── 3b. Tabla Corporativa N+R ─────────────────────────────
    # Ejecuta get_nr_corp_sql() (6ta query BQ) y propaga bottom-up por HIERARCHY_NR_CORP
    # Resultado: monthly_nr_corp_by_node { node_id: {yyyymm: nr_int} }
    print(">>> Paso 3b: Consultando BigQuery (Tabla Corporativa N+R — mensual y diario)...")
    HIERARCHY_NR_CORP        = config.get('hierarchy_nr_corp_detail', [])
    monthly_nr_corp_by_node  = process_nr_corp(config, client, data['months'])
    daily_nr_corp_by_node    = process_nr_corp_daily(config, client, data['months'])
    # Plan corp: INDEPENDIENTE de plan_nr — usa hierarchy_PLAN_Corp (no afecta pestaña NR Mensual)
    plan_nr_corp_by_node     = load_plan_corp(config)
    # Inyectar en data{} para builders Python
    data['HIERARCHY_NR_CORP']       = HIERARCHY_NR_CORP
    data['monthly_nr_corp_by_node'] = monthly_nr_corp_by_node
    data['daily_nr_corp_by_node']   = daily_nr_corp_by_node
    data['plan_nr_corp_by_node']    = plan_nr_corp_by_node  # Plan específico de la tabla corp
    # Performance corp: ensambla métricas de performance por corp_node_id reutilizando data{}
    data['perf_corp_data_by_node'] = build_perf_corp_data(config, data)

    # ── 3d. Installs Mensual (§88) ────────────────────────────────────────────
    # Fuentes: Q_INSTALLS (UCR Gest) + QTY_DEVICES/INSTALLS (Paid) + Corp por corp_key
    print(">>> Paso 3d: Consultando BigQuery (Installs Mensual FM + Corp)...")
    installs_data = process_installs_monthly(client, config)
    # Inyectar en data{} para builders Python
    data['monthly_installs']      = installs_data['monthly_installs']
    data['monthly_installs_mom']  = installs_data['monthly_installs_mom']
    data['installs_months']       = installs_data['installs_months']
    data['installs_corp_by_node'] = installs_data['installs_corp_by_node']

    # ── 3c. Comunicaciones OC (Two-Tier: cache + BQ semana actual) ───────────
    # Two-Tier:
    #   Tier 1 → data/comms_oc_cache.json (histórico estable, generado por refresh_comms_oc_cache.py)
    #   Tier 2 → get_comms_oc_fresh_sql() (solo semana actual, <7 días, rápida)
    # Si el cache no existe: solo datos de la semana actual (tabla Comms_OC funcionará pero incompleta)
    # Si la query Tier 2 falla: solo datos del cache (error visible en stdout, no fatal)
    print(">>> Paso 3c: Cargando Comunicaciones OC (cache + mes actual)...")
    all_comms_oc_records_merged_and_sorted = process_comms_oc(
        bq_client_for_fresh_query=client,
        comms_oc_cache_file_path=COMMS_OC_CACHE_PATH,
        comms_oc_current_month_path=COMMS_OC_CURRENT_MONTH_PATH,
    )
    # Limitar el HTML de Comms_OC a los últimos N meses para mantener el HTML < 50 MB
    # (límite práctico de la API de Apps Script). El cache completo se usa para análisis y skill.
    # NOTA: 6 meses = ~53K registros = ~120 MB → timeout en deploy. Reducir a 3 = ~60 MB, 2 = ~40 MB.
    COMMS_OC_DISPLAY_MONTHS = 2
    _all_months_cache = sorted(set(
        str(r.get('MONTH_ID', ''))[:6]
        for r in all_comms_oc_records_merged_and_sorted
        if r.get('MONTH_ID')
    ))
    _display_months = set(_all_months_cache[-COMMS_OC_DISPLAY_MONTHS:])
    comms_oc_for_html = [
        r for r in all_comms_oc_records_merged_and_sorted
        if str(r.get('MONTH_ID', ''))[:6] in _display_months
    ]
    print(f"  Comms_OC HTML: {len(comms_oc_for_html):,} registros "
          f"({len(_display_months)} meses: {sorted(_display_months)}) "
          f"[cache completo: {len(all_comms_oc_records_merged_and_sorted):,}]")
    data['comms_oc_records'] = comms_oc_for_html

    # Agregación mensual de Comms: conecta "lo enviado" ↔ "lo obtenido" (KPIs)
    # Usa el cache COMPLETO para no perder contexto histórico en el análisis
    comms_monthly_summary = summarize_comms_by_month(all_comms_oc_records_merged_and_sorted)
    print(f"  OK Comms summary: {len(comms_monthly_summary)} meses con datos de comunicaciones")

    # Generar el archivo puente para el OPTIMIZADOR skill
    # skills/comms_monthly_summary.md se actualiza en cada refresh → el skill siempre tiene datos frescos
    COMMS_SUMMARY_MD_PATH = os.path.join(PROJECT_ROOT, 'skills', 'comms_monthly_summary.md')
    generate_comms_monthly_summary_md(comms_monthly_summary, COMMS_SUMMARY_MD_PATH)

    # ── 4. HTML + charts (builders.py) ────────────────────────
    print(">>> Paso 4: Ensamblando HTML Final...")
    charts = {
        'mom_bar':           build_mom_bar(data, plan_nr, plan_lines_data),
        'perf_bar':          build_perf_bar(data),
        'nr_corp_bar':       build_nr_corp_bar_chart(data),       # % N+R por grupo — sección NR Mensual corp
        'perf_corp_bar':     build_perf_corp_bar_chart(data),     # Inversión+VPU+CPA — pestaña Performance_vista_Corp
        'installs_bar':      build_installs_bar(data),            # §88: barras installs + CPI
        'installs_corp_bar': build_installs_corp_bar_chart(data), # §88: barras installs Corp
    }

    # ── 5. data_js: payload que el JS del dashboard consume ───
    # hier_comps: mapeo label → lista de leaf labels (para filtros de canal en JS)
    hier_comps = {}
    for c in HIERARCHY_NR:
        if c.get('is_leaf'):        hier_comps[c['label']] = None
        elif c['label'] == 'Total N+R': hier_comps[c['label']] = 'ALL'
        else:                       hier_comps[c['label']] = get_descendants(c['id'], HIERARCHY_NR)

    # canal_to_label: mapeo canal BQ → label jerarquía (para tab Daily)
    canal_to_label = {}
    for c in HIERARCHY_NR:
        if c.get('is_leaf') and 'bq_mapping' in c:
            channels = c['bq_mapping'].get('channel', [])
            if isinstance(channels, str): channels = [channels]
            for ch in channels: canal_to_label[ch] = c['label']

    data_js = {
        # Periodos y etiquetas N+R
        'months':        data['months'],
        'month_labels':  {m: fmt_month(m) for m in data['months']},
        'latest':        data['months'][-1],
        'labels':        LABELS,
        'leaf_labels':   [c['label'] for c in HIERARCHY_NR if c.get('is_leaf')],
        'indents':       [c['indent'] for c in HIERARCHY_NR],
        'classes':       [c['level']  for c in HIERARCHY_NR],
        # Datos N+R (fuente DAILY_HISTORICO)
        'monthly_nr':    data['monthly_nr'],
        'monthly_mom':   data['monthly_mom'],
        'monthly_cost':  data['monthly_cost'],
        'daily_cum':     data['daily_cum'],
        'daily_cost':    data['daily_cost'],
        'avg_cum':       data['avg_cum'],
        'vs_prom_cum':   data['vs_prom_cum'],
        # Datos corporativos diarios — consumidos por renderNRCorpDailySection() + renderMTDCorpSection()
        'daily_nr_corp_by_node':   daily_nr_corp_by_node,   # {node_id: {yyyymm: {dia_str: nr_int}}}
        # Plan N+R corp — consumido por renderMTDCorpSection() y build_nr_corp_table_html()
        'plan_nr_corp_by_node':    plan_nr_corp_by_node,    # {node_id: {yyyymm: plan_int}}
        # Plan Excel (N+R, Valor, Inversión)
        'plan_nr':          plan_nr,
        'plan_valor':       plan_valor,
        'plan_inv':         plan_inv,
        'plan_lines_data':  plan_lines_data,
        'plan_line_map':    {c['label']: [pl['label'] for pl in c['plan_lines'] if not pl.get('no_chart')] for c in HIERARCHY_NR if 'plan_lines' in c},
        'n_prior':          N_PRIOR,
        # Mapeos auxiliares para JS
        'label_colors':    {c['label']: c['color'] for c in HIERARCHY_NR},
        'canal_to_label':  canal_to_label,
        'hier_comps':      hier_comps,
        # Periodos y etiquetas Costos
        'cost_months':      data['cost_months'],
        'cost_month_labels':{m: fmt_month(m) for m in data['cost_months']},
        'cost_labels':      COST_LABELS,
        'cost_leaf_labels': [c['label'] for c in HIERARCHY_C if c.get('is_leaf') and not c.get('no_cost')],
        'cost_indents':     [c['indent']         for c in HIERARCHY_C],
        'cost_classes':     [c['level']          for c in HIERARCHY_C],
        'cost_no_cost':     [c.get('no_cost', False) for c in HIERARCHY_C],
        'cost_label_colors':{c['label']: c['color'] for c in HIERARCHY_C},
        # Datos Costos (fuente COSTOS_CANALES)
        'monthly_inv_canal':     data['monthly_inv_canal'],
        'monthly_inv_incentivo': data['monthly_inv_incentivo'],
        'monthly_inv_total':     data['monthly_inv_total'],
        'monthly_inv_mom':       data['monthly_inv_mom'],
        'monthly_nr_paid':       data['monthly_nr_paid'],
        'monthly_cpa_total':     data['monthly_cpa_total'],
        'monthly_cpa_paid':      data['monthly_cpa_paid'],
        'cost_channels_nr':      data['COST_CHANNELS_NR'],
        # Datos Performance (cruce DAILY_HISTORICO + COSTOS_CANALES)
        'perf_nr_paid':   data['perf_nr_paid'],
        'perf_vpu_prod':  data['perf_vpu_prod'],
        # Installs Mensual (§88)
        'monthly_installs':      data['monthly_installs'],
        'monthly_installs_mom':  data['monthly_installs_mom'],
        'installs_months':       data['installs_months'],
    }

    # ── 6. Inyectar en template y escribir output ──────────────
    if not os.path.exists(TEMPLATE_PATH):
        print(f"ERROR CRÍTICO: No existe {TEMPLATE_PATH}"); return

    with open(TEMPLATE_PATH, 'r', encoding='utf-8') as f:
        template = f.read()
    with open(CSS_PATH, 'r', encoding='utf-8') as f:
        css = f.read()

    final_html = template.replace('{{CSS}}',          css)
    final_html = final_html.replace('{{TIMESTAMP}}',  datetime.datetime.now().strftime('%d/%m/%Y %H:%M'))
    final_html = final_html.replace('{{MOM_TABLE}}',       build_mom_table_html(data, plan_nr, plan_lines_data))
    final_html = final_html.replace('{{PERF_TABLE}}',      build_perf_table_html(data))
    final_html = final_html.replace('{{NR_CORP_TABLE}}',          build_nr_corp_table_html(data))
    # §88: Installs Mensual — tabla FM + tabla Corp
    final_html = final_html.replace('{{INSTALLS_TABLE}}',          build_installs_table_html(data))
    final_html = final_html.replace('{{INSTALLS_CORP_TABLE}}',     build_installs_corp_table_html(data))
    # §89: Install → Activation Rate — análisis LFT + insights estratégicos
    final_html = final_html.replace('{{INSTALL_ACTIVATION_TAB}}', build_install_activation_tab_html(data))
    final_html = final_html.replace('{{PERF_CORP_TABLE}}',     build_perf_corp_table_html(data))
    # Pestaña Análisis OC+UCR — HTML estático, independiente de BQ
    # Actualizar builders_analysis.py cuando llegue nuevo dato mensual de 2026
    final_html = final_html.replace('{{OC_UCR_ANALYSIS_TAB}}', build_oc_ucr_analysis_tab_html(
        comms_monthly_summary      = comms_monthly_summary,
        comms_oc_records           = all_comms_oc_records_merged_and_sorted,
        monthly_nr_corp_by_node    = monthly_nr_corp_by_node,
        monthly_nr                 = data.get('monthly_nr', {}),
        data_months                = data.get('months', []),
    ))
    # Pestaña Reporting — 3 secciones ejecutivas descargables
    print("  Cargando New vs Recovered mensual (BT_MP_USER_ENGAGEMENT_INAPP)...")
    new_rec_monthly = process_new_rec_monthly(client)
    final_html = final_html.replace('{{REPORTING_TAB}}', build_reporting_tab_html(
        data           = data,
        plan_nr        = plan_nr,
        plan_inv       = plan_inv,
        plan_valor     = plan_valor,
        new_rec_monthly= new_rec_monthly,
    ))
    # Pestaña Comms_OC — tabla HTML de comunicaciones OC (cache + BQ semana actual)
    # Para regenerar el cache histórico: python scripts/refresh_comms_oc_cache.py
    final_html = final_html.replace('{{COMMS_OC_TABLE}}',      build_comms_oc_table_html(data))
    final_html = final_html.replace('{{DATA_JSON}}',  json.dumps(data_js, ensure_ascii=False))
    final_html = final_html.replace('{{CHARTS_JSON}}', json.dumps(charts, ensure_ascii=False))

    with open(OUT_HTML, 'w', encoding='utf-8') as f:
        f.write(final_html)

    print(f"✅ ÉXITO: {OUT_HTML} generado ({os.path.getsize(OUT_HTML)/1024:.0f} KB)")


if __name__ == '__main__':
    assemble()
