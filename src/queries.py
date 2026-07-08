"""
queries.py — Generadores de SQL para MLM ADQ Dashboard V1
══════════════════════════════════════════════════════════
CONEXIONES:
  · Entrada : config/channels_config.json
               └─ hierarchy_nr   → bq_mapping    (usado por get_nr_sql, get_perf_vpu_sql)
               └─ hierarchy_cost → cost_mapping   (usado por get_costos_sql, get_perf_paid_sql)
  · Llamado desde : processors.py → process_all()
  · Tablas BQ:
      PANEL_MONTHLY_DAILY_HISTORICO   → get_nr_sql, get_perf_vpu_sql
      PANEL_MONTHLY_COSTOS_CANALES    → get_costos_sql, get_perf_paid_sql

CONVENCIÓN DE NOMBRES:
  HIERARCHY_NR  = config['hierarchy_nr']   (canales N+R, fuente DAILY_HISTORICO)
  HIERARCHY_C   = config['hierarchy_cost'] (canales Costos, fuente COSTOS_CANALES)

Todas las funciones son puras: reciben la jerarquía y devuelven un string SQL.
"""


def get_nr_sql(HIERARCHY_NR):
    """SQL N+R diario acumulado desde PANEL_MONTHLY_DAILY_HISTORICO.
    El CASE WHEN se genera automáticamente desde hierarchy_nr → bq_mapping.
    Resultado: una fila por (CANAL, FECHA_MES, DIA) con NR acumulado (CUM_NR).
    """
    cases = []
    for c in HIERARCHY_NR:
        if c.get('is_leaf') and 'bq_mapping' in c and not c['bq_mapping'].get('is_org'):
            m       = c['bq_mapping']
            s_list  = f"('{m['strategy']}')" if isinstance(m['strategy'], str) else str(tuple(m['strategy']))
            ch_list = f"('{m['channel'].upper()}')" if isinstance(m['channel'], str) else str(tuple([x.upper() for x in m['channel']]))
            cases.append(f"WHEN STRATEGY IN {s_list} AND UPPER(CHANNEL_APERTURA_3) IN {ch_list} THEN '{c['label']}'")
    case_stmt = "\n      ".join(cases)
    return f"""
    WITH base AS (
      SELECT
        CASE {case_stmt} ELSE 'ORG' END AS CANAL,
        FORMAT_DATE('%Y%m', FECHA_DIARIA) AS FECHA_MES,
        CAST(EXTRACT(DAY FROM FECHA_DIARIA) AS INT64) AS DIA,
        NR_USERS AS NR, COALESCE(INVERSION_TOTAL_USD, 0) AS COST
      FROM `meli-bi-data.SBOX_MKTCORPMP.PANEL_MONTHLY_DAILY_HISTORICO`
      WHERE SIT_SITE_ID = 'MLM' AND FECHA_DIARIA >= DATE '2025-01-01'
    ),
    agg AS (SELECT CANAL, FECHA_MES, DIA, SUM(NR) AS NR, SUM(COST) AS COST FROM base GROUP BY 1,2,3)
    SELECT *, SUM(NR) OVER (PARTITION BY CANAL, FECHA_MES ORDER BY DIA) AS CUM_NR FROM agg
    """


def get_nr_tc_sql(HIERARCHY_NR):
    """SQL N+R diario certificado desde la Torre de Control (TC).

    Reemplaza: get_nr_sql()
    Fuentes TC:
      · oc_tc   → meli-bi-data.SBOX_EG_MKT.BT_OC_NR_REPORTE_TORRE_DAILY
      · paid_tc → meli-bi-data.SBOX_MARKETING.BT_MP_INDIVIDUALS_PERFORMANCE
    Output (schema idéntico a get_nr_sql — processors.py sin cambios):
      CANAL (str), FECHA_MES (YYYYMM), DIA (int), NR (float), COST (float), CUM_NR (float)

    Clasificación de canales: leída desde tc_mapping en cada nodo hoja de HIERARCHY_NR.
    Mismo patrón que get_nr_sql() leía bq_mapping — la lógica de generación dinámica
    se preserva para que channels_config.json siga siendo el SSoT del mapeo.

    Gotchas de producción documentados (ver §71 History.md):
      · BT_MP_INDIVIDUALS_PERFORMANCE contiene filas OC (CHANNEL_GROUP='OC') → EXCLUIR.
        Los datos OC ya están en BT_OC_NR_REPORTE_TORRE_DAILY con metodología lift.
      · ORG = NOT NETWORK APPE + SOURCE_CD='TOOL_COST' (§76). ~589K NR/mes Apr-26.
        Misma fuente TC que el resto de canales. Sin cache adicional.
      · PANDORA ya está en oc_tc (CANAL='PANDORA' en BT_OC_NR_REPORTE_TORRE_DAILY).
        No debe entrar por paid_tc — la whitelist de strategy_group_tc no lo incluye.
      · Ventana SSOT: SOURCE_CD='INSTALLS'→7D, TOOL_COST→std. Determinada por fila.
      · NR negativos son normales: correcciones retroactivas de atribución.
      · Ordenamiento CASE WHEN: strategy_group_tc va ANTES que network_group_name_tc.
        Garantiza que 'ACTIVATION MGM' (MGM ACT) gane sobre el filtro de red (MGM ADQ).
    """
    # ── Separar hojas por fuente TC ──────────────────────────────────────────
    leaves_oc_tc      = []   # source_tc = "torre_daily"
    leaves_paid_sg    = []   # source_tc = "individuals_performance" + solo strategy_group_tc
    leaves_paid_ng    = []   # source_tc = "individuals_performance" + network_group_name_tc
    leaves_org_legacy = []   # source_tc = "baseline_skipped" → ORG via NOT NETWORK APPE CTE
    leaves_catchall   = []   # source_tc = "individuals_catchall" § 78 → catch-all no-whitelisted

    for c in HIERARCHY_NR:
        if not (c.get('is_leaf') and 'tc_mapping' in c):
            continue
        tm  = c['tc_mapping']
        src = tm.get('source_tc', '')
        if src == 'torre_daily':
            leaves_oc_tc.append(c)
        elif src == 'individuals_performance':
            # Condiciones STRATEGY_GROUP-only van primero (más específicas):
            # evitan que ACTIVATION MGM caiga en el WHEN de NETWORK_GROUP_NAME.
            if tm.get('strategy_group_tc') and not tm.get('network_group_name_tc'):
                leaves_paid_sg.append(c)
            else:
                leaves_paid_ng.append(c)
        elif src == 'baseline_skipped':
            leaves_org_legacy.append(c)
        elif src == 'individuals_catchall':
            leaves_catchall.append(c)

    # Orden correcto: strategy_group_tc primero en el CASE WHEN de paid_tc.
    leaves_paid_tc = leaves_paid_sg + leaves_paid_ng

    # ── Generar CASE WHEN de org_legacy_tc (ORG temporal) ───────────────────
    # Una fila por hoja 'baseline_skipped'. En la práctica solo existe 'ORG'.
    # Fuente: PANEL_MONTHLY_DAILY_HISTORICO, CHANNEL_APERTURA_1='ORGANICO'.
    org_cases_tc = []
    for c in leaves_org_legacy:
        org_cases_tc.append(f"WHEN CHANNEL_APERTURA_1 = 'ORGANICO' THEN '{c['label']}'")
    org_case_stmt_tc = '\n        '.join(org_cases_tc)

    # ── Generar CASE WHEN de oc_tc ───────────────────────────────────────────
    # Cada hoja torre_daily genera un WHEN: CLASIFICACION IN (...) THEN 'label'.
    # CLASIFICACION en BT_OC_NR_REPORTE_TORRE_DAILY ≡ CHANNEL_APERTURA_2 en la tabla vieja.
    #
    # §79 excepción: OTHER RECURRING + JOURNEY → OC ACT (journeys son OC Recurring, no UCR PRD).
    # Debe ir ANTES del WHEN genérico de OTHER RECURRING → UCR PRD para tener precedencia.
    _oc_act_label    = next((c['label'] for c in HIERARCHY_NR if c.get('id') == 'oc_act'), 'OC ACT')
    oc_cases_tc = [
        f"WHEN CLASIFICACION = 'OTHER RECURRING' AND UPPER(CANAL) = 'JOURNEY' THEN '{_oc_act_label}'"
    ]
    for c in leaves_oc_tc:
        tm       = c['tc_mapping']
        clsf_sql = ', '.join(f"'{v}'" for v in tm['clasificacion_tc'])
        oc_cases_tc.append(f"WHEN CLASIFICACION IN ({clsf_sql}) THEN '{c['label']}'")
    oc_case_stmt_tc = '\n        '.join(oc_cases_tc)

    # ── Generar CASE WHEN de paid_tc ────────────────────────────────────────
    # Cada hoja individuals_performance genera un WHEN combinando:
    #   strategy_group_tc (OR) network_group_name_tc,
    #   + filtro AND SOURCE_CD IN (...) si existe source_cd_filter_tc.
    paid_cases_tc = []
    for c in leaves_paid_tc:
        tm    = c['tc_mapping']
        label = c['label']

        # Construir condición de identificación del canal
        id_parts = []
        sg_list  = tm.get('strategy_group_tc', [])
        ng_list  = tm.get('network_group_name_tc', [])
        if sg_list:
            sg_sql = ', '.join(f"'{v}'" for v in sg_list)
            id_parts.append(f'STRATEGY_GROUP IN ({sg_sql})')
        if ng_list:
            # UPPER() para normalizar variaciones de casing en los datos BQ
            ng_sql = ', '.join(f"'{v.upper()}'" for v in ng_list)
            id_parts.append(f'UPPER(NETWORK_GROUP_NAME) IN ({ng_sql})')

        if not id_parts:
            continue  # hoja sin condición TC → omitir (error de configuración)

        # Filtro opcional SOURCE_CD: separa ADQ (INSTALLS) de ACT (TOOL_COST)
        sc_list  = tm.get('source_cd_filter_tc', [])
        sc_cond  = ''
        if sc_list:
            sc_sql  = ', '.join(f"'{v}'" for v in sc_list)
            sc_cond = f' AND SOURCE_CD IN ({sc_sql})'

        # Paréntesis si hay OR (claridad); sin paréntesis si es condición única
        canal_cond = f"({' OR '.join(id_parts)})" if len(id_parts) > 1 else id_parts[0]
        paid_cases_tc.append(f"WHEN {canal_cond}{sc_cond} THEN '{label}'")

    paid_case_stmt_tc = '\n        '.join(paid_cases_tc)

    # ── Whitelist WHERE de paid_tc ───────────────────────────────────────────
    # Contiene solo STRATEGY_GROUP y NETWORK_GROUP_NAME del dashboard MLM.
    # NOT NETWORK APPE incluido: clasifica como 'ORG' con SOURCE_CD='TOOL_COST' (§76).
    # 'ORGANIC' excluido: installs orgánicos sin atribución, fuera del scope ADQ.
    all_sg_tc = set()
    all_ng_tc = set()
    for c in leaves_paid_tc:
        tm = c['tc_mapping']
        all_sg_tc.update(tm.get('strategy_group_tc', []))
        all_ng_tc.update(tm.get('network_group_name_tc', []))

    where_parts_tc = []
    if all_sg_tc:
        sg_w = ', '.join(f"'{v}'" for v in sorted(all_sg_tc))
        where_parts_tc.append(f'STRATEGY_GROUP IN ({sg_w})')
    if all_ng_tc:
        ng_w = ', '.join(f"'{v.upper()}'" for v in sorted(all_ng_tc))
        where_parts_tc.append(f'UPPER(NETWORK_GROUP_NAME) IN ({ng_w})')
    paid_where_tc = '\n        OR '.join(f'({p})' for p in where_parts_tc)

    # Exclusión catch-all: inverso del whitelist paid_tc
    catchall_excl_sg_tc = ', '.join(f"'{v}'"         for v in sorted(all_sg_tc)) if all_sg_tc else "'__NEVER__'"
    catchall_excl_ng_tc = ', '.join(f"'{v.upper()}'" for v in sorted(all_ng_tc)) if all_ng_tc else "'__NEVER__'"

    # Label UCR PRD para CTE de RE placements FM (§79)
    _ucr_prd_label = next((c['label'] for c in HIERARCHY_NR if c.get('id') == 'ucr_prd'), 'UCR PRD')

    # ── Fix B §78: pom_flag_tc — POM Others vía POM_FLAG ───────────────────────
    # Captura POM_FLAG='POM Others'/etc. no clasificados en paid_tc whitelist.
    # POM_FLAG check dispara antes de redes orgánicas (igual que query de referencia).
    # Se suma a 'POM Others' junto con WEB POM + CTW POM del paid_tc.
    _pom_others_node  = next((c for c in HIERARCHY_NR if c.get('id') == 'pom_others'), None)
    _pom_others_label = _pom_others_node['label'] if _pom_others_node else 'POM Others'
    if _pom_others_node:
        pom_flag_cte_tc = f"""
    -- ── pom_flag_tc: POM Others via POM_FLAG (§78 Fix B) ─────────────────────
    -- DV360/Google/Tiktok/Facebook con POM_FLAG='POM Others'.
    -- STRATEGY_GROUP='OTHER POM' no está en whitelist paid_tc → sin doble conteo.
    pom_flag_tc AS (
      SELECT
        I.TIM_DAY                                                          AS fecha_tc,
        '{_pom_others_label}'                                              AS CANAL,
        SUM(CASE
          WHEN I.SOURCE_CD = 'INSTALLS'
            THEN COALESCE(I.NEW_USERS_7D_INAPP,      0) + COALESCE(I.RECOVERED_USERS_7D_INAPP,      0)
          ELSE  COALESCE(I.NEW_USERS_INAPP,           0) + COALESCE(I.RECOVERED_USERS_INAPP,          0)
        END)                                                               AS NR,
        SUM(COALESCE(I.COST_USD, 0.0))                                    AS COST
      FROM `meli-bi-data.SBOX_MARKETING.BT_MP_INDIVIDUALS_PERFORMANCE` I
      WHERE I.SIT_SITE_ID  = 'MLM'
        AND I.TIM_DAY       >= DATE '2025-01-01'
        AND I.TIM_DAY        <= DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
        AND I.CHANNEL_GROUP != 'OC'
        AND UPPER(I.POM_FLAG) IN ('POM ACTIVATION', 'POM ACQUISITION', 'POM OTHERS')
      GROUP BY I.TIM_DAY
    ),"""
        pom_flag_union_tc = "UNION ALL\n      SELECT fecha_tc, CANAL, NR, COST FROM pom_flag_tc"
    else:
        pom_flag_cte_tc   = ""
        pom_flag_union_tc = ""

    # ── Fix A §78/§79: ORG = INAPP_TOTAL − OC − PAID − UCR_PRD_RE (residual exacto) ─
    # §79: ucr_prd_inapp_tc (RE placements) ahora aparece en UCR PRD del FM union_tc.
    # Para que FM ORG = Corp NO ATRIBUIDO, esas filas también deben restarse del residual.
    if leaves_org_legacy:
        _org_label = leaves_org_legacy[0]['label']
        # ucr_prd_inapp_tc siempre está definido (CTE anterior en el WITH).
        # Lo restamos del residual ORG para que FM Total = INAPP Total correctamente.
        _ucr_day_cte      = "ucr_day_tc AS (SELECT fecha_tc, SUM(NR) AS NR FROM ucr_prd_inapp_tc GROUP BY 1),"
        _ucr_day_join     = "LEFT JOIN ucr_day_tc ucr ON t.fecha_tc = ucr.fecha_tc"
        _ucr_day_subtract = "- COALESCE(ucr.NR, 0)"
        # POM_FLAG: NO se resta (se absorbe en ORG, consistente con §79).
        _pf_day_cte       = ""
        _pf_day_join      = ""
        _pf_day_subtract  = ""
        org_legacy_cte_tc = f"""
    -- ── inapp_total_tc: Total N+R diario desde BT_MP_USER_ENGAGEMENT_INAPP (§78) ─
    inapp_total_tc AS (
      SELECT
        EVENT_DATE                                                          AS fecha_tc,
        (COUNT(DISTINCT CASE WHEN DAYS_SINCE_FIRST_EVENT = 0  THEN CUS_CUST_ID END)
       + COUNT(DISTINCT CASE WHEN DAYS_SINCE_PRIOR_EVENT > 89 THEN CUS_CUST_ID END)) AS NR_TOTAL
      FROM `meli-bi-data.SBOX_MARKETING.BT_MP_USER_ENGAGEMENT_INAPP`
      WHERE SIT_SITE_ID = 'MLM'
        AND EVENT_DATE  >= DATE '2025-01-01'
        AND EVENT_DATE   <= DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
        AND (DAYS_SINCE_FIRST_EVENT = 0 OR DAYS_SINCE_PRIOR_EVENT > 89)
      GROUP BY EVENT_DATE
    ),
    -- Totales por día para el residual ORG (§78/§79)
    oc_day_tc   AS (SELECT fecha_tc, SUM(NR) AS NR FROM oc_tc   WHERE CANAL IS NOT NULL GROUP BY 1),
    paid_day_tc AS (SELECT fecha_tc, SUM(NR) AS NR FROM paid_tc  WHERE CANAL IS NOT NULL GROUP BY 1),
    {_ucr_day_cte}
    -- ORG = INAPP_TOTAL − OC − PAID − UCR_PRD_RE (residual §78/§79)
    -- GREATEST(..., 0): evita negativos en días con correcciones retroactivas.
    org_legacy_tc AS (
      SELECT
        t.fecha_tc,
        '{_org_label}'      AS CANAL,
        GREATEST(
          t.NR_TOTAL
          - COALESCE(oc.NR, 0)
          - COALESCE(p.NR,  0)
          {_ucr_day_subtract},
          0
        )                   AS NR,
        0.0                 AS COST
      FROM inapp_total_tc t
      LEFT JOIN oc_day_tc   oc  ON t.fecha_tc = oc.fecha_tc
      LEFT JOIN paid_day_tc p   ON t.fecha_tc = p.fecha_tc
      {_ucr_day_join}
    ),"""
        org_legacy_union_tc = "UNION ALL\n      SELECT fecha_tc, CANAL, NR, COST FROM org_legacy_tc"
    else:
        org_legacy_cte_tc   = ""
        org_legacy_union_tc = ""

    # ── CTE catch-all §78 ───────────────────────────────────────────────────
    # Captura filas BT_MP_INDIVIDUALS_PERFORMANCE que NO están en whitelist paid_tc,
    # NO son OC y NO son NOT NETWORK APPE (ORG). ~14K NR/mes abr-26.
    if leaves_catchall:
        _catchall_label = leaves_catchall[0]['label']   # 'Others'
        catchall_cte_tc = f"""
    -- ── others_catchall_tc: canal catch-all §78 ─────────────────────────────
    -- Filas BT_MP_INDIVIDUALS_PERFORMANCE no clasificadas en ningún canal whitelisted.
    -- Exclusión explícita: NOT en paid_tc whitelist + NOT OC + NOT NOT_NETWORK_APPE.
    others_catchall_tc AS (
      SELECT
        I.TIM_DAY                                                          AS fecha_tc,
        '{_catchall_label}'                                                AS CANAL,
        SUM(CASE
          WHEN I.SOURCE_CD = 'INSTALLS'
            THEN COALESCE(I.NEW_USERS_7D_INAPP,      0) + COALESCE(I.RECOVERED_USERS_7D_INAPP,      0)
          ELSE  COALESCE(I.NEW_USERS_INAPP,           0) + COALESCE(I.RECOVERED_USERS_INAPP,          0)
        END)                                                               AS NR,
        SUM(COALESCE(I.COST_USD, 0.0))                                    AS COST
      FROM `meli-bi-data.SBOX_MARKETING.BT_MP_INDIVIDUALS_PERFORMANCE` I
      WHERE I.SIT_SITE_ID              = 'MLM'
        AND I.TIM_DAY                   >= DATE '2025-01-01'
        AND I.TIM_DAY                    <= DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
        AND UPPER(I.CHANNEL_GROUP)      != 'OC'
        AND NOT (I.STRATEGY_GROUP IN ('PANDORA', 'OC'))
        AND UPPER(I.NETWORK_GROUP_NAME) != 'NOT NETWORK APPE'
        AND I.STRATEGY_GROUP     NOT IN ({catchall_excl_sg_tc})
        AND UPPER(I.NETWORK_GROUP_NAME) NOT IN ({catchall_excl_ng_tc})
      GROUP BY I.TIM_DAY
    ),"""
        catchall_union_tc = "UNION ALL\n      SELECT fecha_tc, CANAL, NR, COST FROM others_catchall_tc"
    else:
        catchall_cte_tc   = ""
        catchall_union_tc = ""

    return f"""
    -- ═══════════════════════════════════════════════════════════════════════
    -- get_nr_tc_sql() — N+R diario Torre de Control (TC) | §71 §76 §78
    -- Reemplaza: get_nr_sql()
    -- Output: CANAL, FECHA_MES, DIA, NR, COST, CUM_NR  ← schema idéntico
    -- Fuentes:
    --   oc_tc         → BT_OC_NR_REPORTE_TORRE_DAILY
    --   paid_tc       → BT_MP_INDIVIDUALS_PERFORMANCE (whitelist)
    --   pom_flag_tc   → BT_MP_INDIVIDUALS_PERFORMANCE (POM_FLAG='POM Others', §78 Fix B)
    --   org_legacy_tc → INAPP_TOTAL − OC − PAID − POM_FLAG (residual exacto §78 Fix A)
    -- ═══════════════════════════════════════════════════════════════════════
    WITH

    -- ── oc_tc: canales OC desde Torre de Control ─────────────────────────
    -- NR_INC_USERS = usuarios incrementales (Test - Control). Metodología lift.
    -- Usar esta tabla y NO BT_MP_INDIVIDUALS_PERFORMANCE para OC:
    -- la segunda daría atribución simple (≠ incrementalidad).
    -- Costo OC = 3 componentes certificados: CONSUMIDO + COSTO_ENVIO + COSTO_MANTIKA.
    oc_tc AS (
      SELECT
        DAY_ID                              AS fecha_tc,
        CASE
          {oc_case_stmt_tc}
        END                                 AS CANAL,
        COALESCE(NR_INC_USERS, 0)           AS NR,
        COALESCE(CONSUMIDO_USD,      0)
          + COALESCE(COSTO_ENVIO_USD,  0)
          + COALESCE(COSTO_MANTIKA_USD, 0)  AS COST
      FROM `meli-bi-data.SBOX_EG_MKT.BT_OC_NR_REPORTE_TORRE_DAILY`
      WHERE SITE   = 'MLM'
        AND DAY_ID >= DATE '2025-01-01'
        AND DAY_ID <= DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
    ),

    -- ── paid_tc: canales Paid desde Individuals Performance ──────────────
    -- Ventana de atribución según estándar SSOT (por fila, no por canal):
    --   INSTALLS  → 7D (NEW_USERS_7D_INAPP + RECOVERED_USERS_7D_INAPP)
    --   TOOL_COST → std (NEW_USERS_INAPP    + RECOVERED_USERS_INAPP)
    -- CHANNEL_GROUP != 'OC': excluye filas de canales propios (ya están en oc_tc).
    -- Whitelist explícita: solo STRATEGY_GROUP / NETWORK_GROUP_NAME del dashboard.
    -- CASE WHEN ordenado: strategy_group_tc primero (más específico).
    paid_tc AS (
      SELECT
        I.TIM_DAY                           AS fecha_tc,
        CASE
          {paid_case_stmt_tc}
        END                                 AS CANAL,
        SUM(
          CASE
            WHEN SOURCE_CD = 'INSTALLS'
              THEN COALESCE(NEW_USERS_7D_INAPP,      0)
                 + COALESCE(RECOVERED_USERS_7D_INAPP, 0)
            ELSE  COALESCE(NEW_USERS_INAPP,           0)
                 + COALESCE(RECOVERED_USERS_INAPP,    0)
          END
        )                                   AS NR,
        -- Costo paid = media + incentivos LC convertidos a USD
        SUM(
          COALESCE(I.COST_USD, 0)
          + COALESCE(I.COST_LC_INCENTIVOS * D.USD_RATIO, 0)
        )                                   AS COST
      FROM `meli-bi-data.SBOX_MARKETING.BT_MP_INDIVIDUALS_PERFORMANCE` I
      LEFT JOIN `meli-bi-data.WHOWNER.LK_API_CURRENCY_CONVERSION` D
        ON  I.SIT_SITE_ID = D.SIT_SITE_ID
        AND I.TIM_DAY     = D.TIM_DAY
      WHERE I.SIT_SITE_ID  = 'MLM'
        AND I.TIM_DAY       >= DATE '2025-01-01'
        AND I.TIM_DAY        <= DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
        AND I.CHANNEL_GROUP != 'OC'
        AND (
          {paid_where_tc}
        )
      GROUP BY I.TIM_DAY, CANAL
    ),

    -- ── ucr_prd_inapp_tc: UCR PRD via RE placements FM (§79) ─────────────────
    -- Misma fuente que ucr_prd_indiv_tc de Corp. CHANNEL_GROUP != 'OC' → sin doble conteo.
    ucr_prd_inapp_tc AS (
      SELECT
        I.TIM_DAY                                                          AS fecha_tc,
        '{_ucr_prd_label}'                                                 AS CANAL,
        SUM(CASE
          WHEN I.SOURCE_CD = 'INSTALLS'
            THEN COALESCE(I.NEW_USERS_7D_INAPP, 0) + COALESCE(I.RECOVERED_USERS_7D_INAPP, 0)
          ELSE  COALESCE(I.NEW_USERS_INAPP,     0) + COALESCE(I.RECOVERED_USERS_INAPP,     0)
        END)                                                               AS NR,
        0.0                                                                AS COST
      FROM `meli-bi-data.SBOX_MARKETING.BT_MP_INDIVIDUALS_PERFORMANCE` I
      WHERE I.SIT_SITE_ID  = 'MLM'
        AND I.TIM_DAY       >= DATE '2025-01-01'
        AND I.TIM_DAY        <= DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
        AND I.CHANNEL_GROUP != 'OC'
        AND (
          (UPPER(I.NETWORK_GROUP_NAME) = 'REAL ESTATE'
            AND REGEXP_CONTAINS(UPPER(I.CAMPAIGN_NAME),
              r'DRAWER|FALLBACK|HOME_ML|HUB_CREDITS|REFUNDS_ML|CREDITS_PERSONAL_LOANS|BANNER-LOYALTY-ML|HUB-LOYALTY_ML|ADMIN_CREDITS|MUSD|MELIMAIS|MELIMAS|MELIDOLAR|MERCADO_COIN|INSUR'))
          OR (UPPER(I.NETWORK_GROUP_NAME) = 'OTHERS'
            AND REGEXP_CONTAINS(UPPER(I.CAMPAIGN_NAME), r'ACQUISITION_TC|CX_SOLICITUD_'))
          OR UPPER(I.NETWORK_GROUP_NAME) = 'LOYALTY'
        )
      GROUP BY I.TIM_DAY
    ),

    {pom_flag_cte_tc}
    {org_legacy_cte_tc}
    {catchall_cte_tc}
    -- ── union_tc: une todas las fuentes, descarta filas sin canal mapeado ───
    -- NOTA §78: pom_flag_tc NO se incluye aquí intencionalmente.
    -- Las filas POM_FLAG van al residual ORG (se restan en org_legacy_tc via pf_day_tc).
    -- En Corp aparecen como corp_pom_others. En FM se absorben en ORG (= "no atribuido").
    -- Esto mantiene consistencia: FM pom_others = WEB POM + CTW POM solamente.
    union_tc AS (
      SELECT fecha_tc, CANAL, NR, COST FROM oc_tc              WHERE CANAL IS NOT NULL
      UNION ALL
      SELECT fecha_tc, CANAL, NR, COST FROM paid_tc             WHERE CANAL IS NOT NULL
      UNION ALL
      SELECT fecha_tc, CANAL, NR, COST FROM ucr_prd_inapp_tc
      {org_legacy_union_tc}
      {catchall_union_tc}
    ),

    -- ── agg_tc: agrega por canal/mes/día ─────────────────────────────────
    -- Suma necesaria porque oc_tc puede tener múltiples CLASIFICACION para el mismo
    -- canal del dashboard (e.g. ACTIVATION + ADHOC → ambos mapean a 'OC ACT').
    agg_tc AS (
      SELECT
        FORMAT_DATE('%Y%m', fecha_tc)             AS FECHA_MES,
        CAST(EXTRACT(DAY FROM fecha_tc) AS INT64) AS DIA,
        CANAL,
        SUM(NR)                                   AS NR,
        SUM(COST)                                 AS COST
      FROM union_tc
      GROUP BY FECHA_MES, DIA, CANAL
    )

    -- ── Output: schema idéntico a get_nr_sql() ───────────────────────────
    -- processors.py consume exactamente: CANAL, FECHA_MES, DIA, NR, COST, CUM_NR.
    -- CUM_NR = acumulado diario dentro del mes (particionado por CANAL).
    SELECT
      CANAL,
      FECHA_MES,
      DIA,
      NR,
      COST,
      SUM(NR) OVER (
        PARTITION BY CANAL, FECHA_MES
        ORDER BY DIA
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
      ) AS CUM_NR
    FROM agg_tc
    ORDER BY CANAL, FECHA_MES, DIA
    """


def _tc_channel_parts(HIERARCHY_NR):
    """Helper interno: clasifica nodos hoja por source_tc y genera partes SQL reutilizables.

    Reutilizado por get_vpu_tc_sql(), get_costos_tc_sql(), get_perf_paid_tc_sql().
    NO usado por get_nr_tc_sql() (tiene su propia implementación inline con CTE condicional).

    Retorna dict con claves:
      leaves_oc_tc      → lista de hojas torre_daily
      leaves_paid_tc    → lista de hojas individuals_performance (sg primero, luego ng)
      leaves_org_legacy → lista de hojas baseline_skipped
      oc_case_stmt      → string CASE WHEN para oc CTE
      paid_case_stmt    → string CASE WHEN para paid CTE
      paid_where        → string WHERE whitelist para paid CTE
      org_case_stmt     → string CASE WHEN para org CTE
    """
    leaves_oc_tc      = []
    leaves_paid_sg    = []   # strategy_group_tc sin network → más específico, va primero
    leaves_paid_ng    = []   # network_group_name_tc → va después
    leaves_org_legacy = []
    leaves_catchall   = []   # individuals_catchall §78: catch-all de filas no-whitelisted

    for c in HIERARCHY_NR:
        if not (c.get('is_leaf') and 'tc_mapping' in c):
            continue
        tm  = c['tc_mapping']
        src = tm.get('source_tc', '')
        if src == 'torre_daily':
            leaves_oc_tc.append(c)
        elif src == 'individuals_performance':
            # strategy_group_tc sin network_group_name_tc → condición más específica → va primero
            # Garantiza que ACTIVATION MGM (MGM ACT) gana sobre NETWORK_GROUP_NAME (MGM ADQ)
            if tm.get('strategy_group_tc') and not tm.get('network_group_name_tc'):
                leaves_paid_sg.append(c)
            else:
                leaves_paid_ng.append(c)
        elif src == 'baseline_skipped':
            leaves_org_legacy.append(c)
        elif src == 'individuals_catchall':
            leaves_catchall.append(c)

    leaves_paid_tc = leaves_paid_sg + leaves_paid_ng

    # OC: WHEN CLASIFICACION IN (...) THEN 'label'
    oc_cases = []
    for c in leaves_oc_tc:
        clsf_sql = ', '.join(f"'{v}'" for v in c['tc_mapping']['clasificacion_tc'])
        oc_cases.append(f"WHEN CLASIFICACION IN ({clsf_sql}) THEN '{c['label']}'")

    # Paid: WHEN (strategy OR network) [AND source_cd] THEN 'label'
    paid_cases = []
    for c in leaves_paid_tc:
        tm    = c['tc_mapping']
        label = c['label']
        id_parts = []
        sg_list  = tm.get('strategy_group_tc', [])
        ng_list  = tm.get('network_group_name_tc', [])
        if sg_list:
            sg_sql = ', '.join(f"'{v}'" for v in sg_list)
            id_parts.append(f'STRATEGY_GROUP IN ({sg_sql})')
        if ng_list:
            ng_sql = ', '.join(f"'{v.upper()}'" for v in ng_list)
            id_parts.append(f'UPPER(NETWORK_GROUP_NAME) IN ({ng_sql})')
        if not id_parts:
            continue
        sc_list  = tm.get('source_cd_filter_tc', [])
        sc_cond  = f" AND SOURCE_CD IN ({', '.join(repr(v) for v in sc_list)})" if sc_list else ''
        canal_cond = f"({' OR '.join(id_parts)})" if len(id_parts) > 1 else id_parts[0]
        paid_cases.append(f"WHEN {canal_cond}{sc_cond} THEN '{label}'")

    # Whitelist WHERE para paid CTE (NOT NETWORK APPE incluido como ORG §76)
    all_sg, all_ng = set(), set()
    for c in leaves_paid_tc:
        tm = c['tc_mapping']
        all_sg.update(tm.get('strategy_group_tc', []))
        all_ng.update(tm.get('network_group_name_tc', []))
    where_parts = []
    if all_sg:
        where_parts.append(f"STRATEGY_GROUP IN ({', '.join(repr(v) for v in sorted(all_sg))})")
    if all_ng:
        where_parts.append(f"UPPER(NETWORK_GROUP_NAME) IN ({', '.join(repr(v.upper()) for v in sorted(all_ng))})")
    paid_where = '\n        OR '.join(f'({p})' for p in where_parts)

    # ORG: WHEN CHANNEL_APERTURA_1='ORGANICO' THEN 'label'
    org_cases = [
        f"WHEN CHANNEL_APERTURA_1 = 'ORGANICO' THEN '{c['label']}'"
        for c in leaves_org_legacy
    ]

    # Catch-all: exclusión de todos los canales ya clasificados
    # Condición inversa a paid_where: NOT en whitelist + NOT OC + NOT NOT_NETWORK_APPE
    catchall_excl_sg = ', '.join(repr(v)         for v in sorted(all_sg)) if all_sg else "'__NEVER__'"
    catchall_excl_ng = ', '.join(repr(v.upper()) for v in sorted(all_ng)) if all_ng else "'__NEVER__'"

    # Label del nodo pom_others para usar en CTEs pom_flag_* de vpu/costos/paid
    _pom_others_node = next((c for c in HIERARCHY_NR if c.get('id') == 'pom_others'), None)
    pom_others_label = _pom_others_node['label'] if _pom_others_node else None

    return {
        'leaves_oc_tc':      leaves_oc_tc,
        'leaves_paid_tc':    leaves_paid_tc,
        'leaves_org_legacy': leaves_org_legacy,
        'leaves_catchall':   leaves_catchall,
        'oc_case_stmt':      '\n        '.join(oc_cases),
        'paid_case_stmt':    '\n        '.join(paid_cases),
        'paid_where':        paid_where,
        'org_case_stmt':     '\n        '.join(org_cases),
        'catchall_label':    leaves_catchall[0]['label'] if leaves_catchall else None,
        'catchall_excl_sg':  catchall_excl_sg,
        'catchall_excl_ng':  catchall_excl_ng,
        'pom_others_label':  pom_others_label,   # §78: para CTEs pom_flag_* en vpu/costos/paid
    }


def get_vpu_tc_sql(HIERARCHY_NR):
    """SQL Valor Pred 90D por canal/mes desde la Torre de Control (TC).

    Reemplaza: get_perf_vpu_sql(HIERARCHY_NR)
    Output (schema idéntico — processors.py sin cambios):
      MONTH_ID (YYYYMM str), PERF_CANAL, NR_TOTAL, NR_VPU_PROD

    NR_VPU_PROD = suma del valor predicho 90D para los NR users (pre-multiplicado).
    VPU promedio = NR_VPU_PROD / NR_TOTAL — calculado en processors.py.

    Fuentes TC (mismas que get_nr_tc_sql()):
      oc_vpu_tc   → NR_INC_VALUE de BT_OC_NR_REPORTE_TORRE_DAILY
      paid_vpu_tc → VALUE_MKT_USD_7D (INSTALLS) / VALUE_MKT_USD (TOOL_COST) de BT_MP_INDIVIDUALS_PERFORMANCE
      org_vpu_tc  → §75: ORG VPU desde paid_vpu_tc (BT_MP_INDIVIDUALS_PERFORMANCE, NOT NETWORK APPE)
    """
    p = _tc_channel_parts(HIERARCHY_NR)

    # pom_flag_vpu_tc: VPU de POM Others vía POM_FLAG (§78)
    if p.get('pom_others_label'):
        _pf_vpu_label = p['pom_others_label']
        pom_flag_vpu_cte = f"""
    -- pom_flag_vpu_tc: VPU POM Others via POM_FLAG §78
    pom_flag_vpu_tc AS (
      SELECT
        FORMAT_DATE('%Y%m', I.TIM_DAY)  AS MONTH_ID,
        '{_pf_vpu_label}'               AS PERF_CANAL,
        SUM(CASE WHEN SOURCE_CD = 'INSTALLS'
                 THEN COALESCE(NEW_USERS_7D_INAPP,0)        + COALESCE(RECOVERED_USERS_7D_INAPP,0)
                 ELSE COALESCE(NEW_USERS_INAPP,0)           + COALESCE(RECOVERED_USERS_INAPP,0)
            END)                        AS NR,
        SUM(CASE WHEN SOURCE_CD = 'INSTALLS'
                 THEN COALESCE(VALUE_MKT_USD_NEW_USERS_7D,0)        + COALESCE(VALUE_MKT_USD_RECOVERED_USERS_7D,0)
                 ELSE COALESCE(VALUE_MKT_USD_NEW_USERS,0)           + COALESCE(VALUE_MKT_USD_RECOVERED_USERS,0)
            END)                        AS VPU_PROD
      FROM `meli-bi-data.SBOX_MARKETING.BT_MP_INDIVIDUALS_PERFORMANCE` I
      WHERE I.SIT_SITE_ID  = 'MLM'
        AND I.TIM_DAY       >= DATE '2025-01-01'
        AND I.TIM_DAY        <= DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
        AND I.CHANNEL_GROUP != 'OC'
        AND UPPER(I.POM_FLAG) IN ('POM ACTIVATION', 'POM ACQUISITION', 'POM OTHERS')
      GROUP BY MONTH_ID
    ),"""
        pom_flag_vpu_union = "UNION ALL\n      SELECT MONTH_ID, PERF_CANAL, NR, VPU_PROD FROM pom_flag_vpu_tc WHERE PERF_CANAL IS NOT NULL"
    else:
        pom_flag_vpu_cte   = ""
        pom_flag_vpu_union = ""

    if p.get('leaves_catchall'):
        _catchall_vpu_label = p['catchall_label']
        catchall_vpu_cte = f"""
    -- others_catchall_vpu_tc: VPU del canal catch-all §78
    others_catchall_vpu_tc AS (
      SELECT
        FORMAT_DATE('%Y%m', I.TIM_DAY)  AS MONTH_ID,
        '{_catchall_vpu_label}'          AS PERF_CANAL,
        SUM(CASE WHEN SOURCE_CD = 'INSTALLS'
                 THEN COALESCE(NEW_USERS_7D_INAPP,0) + COALESCE(RECOVERED_USERS_7D_INAPP,0)
                 ELSE COALESCE(NEW_USERS_INAPP,0)    + COALESCE(RECOVERED_USERS_INAPP,0)
            END)                         AS NR,
        SUM(CASE WHEN SOURCE_CD = 'INSTALLS'
                 THEN COALESCE(VALUE_MKT_USD_NEW_USERS_7D,0) + COALESCE(VALUE_MKT_USD_RECOVERED_USERS_7D,0)
                 ELSE COALESCE(VALUE_MKT_USD_NEW_USERS,0)    + COALESCE(VALUE_MKT_USD_RECOVERED_USERS,0)
            END)                         AS VPU_PROD
      FROM `meli-bi-data.SBOX_MARKETING.BT_MP_INDIVIDUALS_PERFORMANCE` I
      WHERE I.SIT_SITE_ID              = 'MLM'
        AND I.TIM_DAY                   >= DATE '2025-01-01'
        AND I.TIM_DAY                    <= DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
        AND UPPER(I.CHANNEL_GROUP)      != 'OC'
        AND NOT (I.STRATEGY_GROUP IN ('PANDORA', 'OC'))
        AND UPPER(I.NETWORK_GROUP_NAME) != 'NOT NETWORK APPE'
        AND I.STRATEGY_GROUP     NOT IN ({p['catchall_excl_sg']})
        AND UPPER(I.NETWORK_GROUP_NAME) NOT IN ({p['catchall_excl_ng']})
      GROUP BY I.TIM_DAY
    ),"""
        catchall_vpu_union = "UNION ALL\n      SELECT MONTH_ID, PERF_CANAL, NR, VPU_PROD FROM others_catchall_vpu_tc"
    else:
        catchall_vpu_cte   = ""
        catchall_vpu_union = ""

    if p['leaves_org_legacy']:
        _org_vpu_label = p['leaves_org_legacy'][0]['label']
        org_vpu_cte = f"""
    -- org_vpu_tc: ORG VPU desde NOT NETWORK APPE (§76)
    org_vpu_tc AS (
      SELECT
        FORMAT_DATE('%Y%m', I.TIM_DAY)                AS MONTH_ID,
        '{_org_vpu_label}'                             AS PERF_CANAL,
        SUM(
          COALESCE(I.NEW_USERS_INAPP,      0)
          + COALESCE(I.RECOVERED_USERS_INAPP, 0)
        )                                              AS NR,
        SUM(
          COALESCE(I.VALUE_MKT_USD_NEW_USERS,      0)
          + COALESCE(I.VALUE_MKT_USD_RECOVERED_USERS, 0)
        )                                              AS VPU_PROD
      FROM `meli-bi-data.SBOX_MARKETING.BT_MP_INDIVIDUALS_PERFORMANCE` I
      WHERE I.SIT_SITE_ID              = 'MLM'
        AND I.TIM_DAY                   >= DATE '2025-01-01'
        AND I.TIM_DAY                    <= DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
        AND UPPER(I.NETWORK_GROUP_NAME) = 'NOT NETWORK APPE'
        AND I.SOURCE_CD                 = 'TOOL_COST'
      GROUP BY I.TIM_DAY
    ),"""
        org_vpu_union = "UNION ALL\n      SELECT MONTH_ID, PERF_CANAL, NR, VPU_PROD FROM org_vpu_tc"
    else:
        org_vpu_cte   = ""
        org_vpu_union = ""

    return f"""
    -- ═══════════════════════════════════════════════════════════════════════
    -- get_vpu_tc_sql() — Valor Pred 90D por canal/mes TC | §71 §78
    -- Reemplaza: get_perf_vpu_sql()
    -- Output: MONTH_ID, PERF_CANAL, NR_TOTAL, NR_VPU_PROD  ← schema idéntico
    -- ═══════════════════════════════════════════════════════════════════════
    WITH

    -- ── oc_vpu_tc: Valor Pred OC desde Torre de Control ─────────────────
    -- NR_INC_VALUE = valor predicho 90D para los usuarios incrementales (lift).
    oc_vpu_tc AS (
      SELECT
        FORMAT_DATE('%Y%m', DAY_ID)    AS MONTH_ID,
        CASE
          {p['oc_case_stmt']}
        END                            AS PERF_CANAL,
        COALESCE(NR_INC_USERS, 0)     AS NR,
        COALESCE(NR_INC_VALUE, 0)     AS VPU_PROD
      FROM `meli-bi-data.SBOX_EG_MKT.BT_OC_NR_REPORTE_TORRE_DAILY`
      WHERE SITE   = 'MLM'
        AND DAY_ID >= DATE '2025-01-01'
        AND DAY_ID <= DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
    ),

    -- ── paid_vpu_tc: Valor Pred Paid desde Individuals Performance ───────
    -- VALUE_MKT_USD_* = valor predicho 90D para los NR users.
    -- Misma ventana que NR: INSTALLS→7D, TOOL_COST→estándar.
    paid_vpu_tc AS (
      SELECT
        FORMAT_DATE('%Y%m', I.TIM_DAY) AS MONTH_ID,
        CASE
          {p['paid_case_stmt']}
        END                            AS PERF_CANAL,
        SUM(
          CASE
            WHEN SOURCE_CD = 'INSTALLS'
              THEN COALESCE(NEW_USERS_7D_INAPP,      0) + COALESCE(RECOVERED_USERS_7D_INAPP,      0)
            ELSE  COALESCE(NEW_USERS_INAPP,           0) + COALESCE(RECOVERED_USERS_INAPP,          0)
          END
        )                              AS NR,
        SUM(
          CASE
            WHEN SOURCE_CD = 'INSTALLS'
              THEN COALESCE(VALUE_MKT_USD_NEW_USERS_7D, 0) + COALESCE(VALUE_MKT_USD_RECOVERED_USERS_7D, 0)
            ELSE  COALESCE(VALUE_MKT_USD_NEW_USERS,     0) + COALESCE(VALUE_MKT_USD_RECOVERED_USERS,     0)
          END
        )                              AS VPU_PROD
      FROM `meli-bi-data.SBOX_MARKETING.BT_MP_INDIVIDUALS_PERFORMANCE` I
      WHERE I.SIT_SITE_ID  = 'MLM'
        AND I.TIM_DAY       >= DATE '2025-01-01'
        AND I.TIM_DAY        <= DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
        AND I.CHANNEL_GROUP != 'OC'
        AND (
          {p['paid_where']}
        )
      GROUP BY I.TIM_DAY, PERF_CANAL
    ),

    {org_vpu_cte}
    {catchall_vpu_cte}
    -- NOTA §78: pom_flag_vpu_tc excluido del UNION (consistente con get_nr_tc_sql).
    -- VPU de pom_others FM = solo WEB POM + CTW POM.
    union_vpu_tc AS (
      SELECT MONTH_ID, PERF_CANAL, NR, VPU_PROD FROM oc_vpu_tc  WHERE PERF_CANAL IS NOT NULL
      UNION ALL
      SELECT MONTH_ID, PERF_CANAL, NR, VPU_PROD FROM paid_vpu_tc WHERE PERF_CANAL IS NOT NULL
      {org_vpu_union}
      {catchall_vpu_union}
    )

    SELECT
      MONTH_ID,
      PERF_CANAL,
      SUM(NR)        AS NR_TOTAL,
      SUM(VPU_PROD)  AS NR_VPU_PROD
    FROM union_vpu_tc
    GROUP BY MONTH_ID, PERF_CANAL
    """


def get_costos_tc_sql(HIERARCHY_NR):
    """SQL inversión mensual por canal desde la Torre de Control (TC).

    Reemplaza: get_costos_sql(HIERARCHY_C) — ahora recibe HIERARCHY_NR (tiene tc_mapping).
    Los labels de CANAL son los mismos en ambas jerarquías → processors.py sin cambios.
    Output (schema idéntico):
      MONTH_ID (YYYYMM str), CANAL, INV_CANAL, INV_INCENTIVO, INV_TOTAL

    OC:   INV_CANAL=CONSUMIDO_USD  INV_INCENTIVO=COSTO_ENVIO_USD+COSTO_MANTIKA_USD
    Paid: INV_CANAL=COST_USD       INV_INCENTIVO=COST_LC_INCENTIVOS*USD_RATIO
    ORG:  todo 0 (sin inversión gestionada)
    """
    p = _tc_channel_parts(HIERARCHY_NR)

    # pom_flag_cost_tc: Inversión POM Others vía POM_FLAG (§78)
    pom_flag_cost_cte   = ""
    pom_flag_cost_union = ""
    if p.get('pom_others_label'):
        _pf_cost_label = p['pom_others_label']
        pom_flag_cost_cte = f""",

    -- pom_flag_cost_tc: Inversión POM Others via POM_FLAG §78
    pom_flag_cost_tc AS (
      SELECT
        FORMAT_DATE('%Y%m', I.TIM_DAY)   AS MONTH_ID,
        '{_pf_cost_label}'               AS CANAL,
        SUM(COALESCE(I.COST_USD, 0))     AS INV_CANAL,
        0                                AS INV_INCENTIVO,
        SUM(COALESCE(I.COST_USD, 0))     AS INV_TOTAL,
        0                                AS INV_MANTIKA
      FROM `meli-bi-data.SBOX_MARKETING.BT_MP_INDIVIDUALS_PERFORMANCE` I
      WHERE I.SIT_SITE_ID  = 'MLM'
        AND I.TIM_DAY       >= DATE '2025-01-01'
        AND I.TIM_DAY        <= DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
        AND I.CHANNEL_GROUP != 'OC'
        AND UPPER(I.POM_FLAG) IN ('POM ACTIVATION', 'POM ACQUISITION', 'POM OTHERS')
      GROUP BY MONTH_ID
    )"""
        pom_flag_cost_union = "UNION ALL\n      SELECT MONTH_ID, CANAL, INV_CANAL, INV_INCENTIVO, INV_TOTAL, INV_MANTIKA FROM pom_flag_cost_tc WHERE CANAL IS NOT NULL"

    # El CTE catch-all se inyecta CON coma al inicio para conectarse a paid_cost_tc
    # que siempre termina con ')' sin coma. La coma la pone el catch-all al iniciar.
    catchall_cost_cte   = ""
    catchall_cost_union = ""
    if p.get('leaves_catchall'):
        _catchall_cost_label = p['catchall_label']
        catchall_cost_cte = f""",

    -- others_catchall_cost_tc: Inversión del canal catch-all §78
    others_catchall_cost_tc AS (
      SELECT
        FORMAT_DATE('%Y%m', I.TIM_DAY)           AS MONTH_ID,
        '{_catchall_cost_label}'                  AS CANAL,
        SUM(COALESCE(I.COST_USD, 0))              AS INV_CANAL,
        0                                         AS INV_INCENTIVO,
        SUM(COALESCE(I.COST_USD, 0))              AS INV_TOTAL,
        0                                         AS INV_MANTIKA
      FROM `meli-bi-data.SBOX_MARKETING.BT_MP_INDIVIDUALS_PERFORMANCE` I
      WHERE I.SIT_SITE_ID              = 'MLM'
        AND I.TIM_DAY                   >= DATE '2025-01-01'
        AND I.TIM_DAY                    <= DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
        AND UPPER(I.CHANNEL_GROUP)      != 'OC'
        AND NOT (I.STRATEGY_GROUP IN ('PANDORA', 'OC'))
        AND UPPER(I.NETWORK_GROUP_NAME) != 'NOT NETWORK APPE'
        AND I.STRATEGY_GROUP     NOT IN ({p['catchall_excl_sg']})
        AND UPPER(I.NETWORK_GROUP_NAME) NOT IN ({p['catchall_excl_ng']})
      GROUP BY I.TIM_DAY
    )"""
        catchall_cost_union = "UNION ALL\n      SELECT MONTH_ID, CANAL, INV_CANAL, INV_INCENTIVO, INV_TOTAL, INV_MANTIKA FROM others_catchall_cost_tc WHERE CANAL IS NOT NULL"

    return f"""
    -- ═══════════════════════════════════════════════════════════════════════
    -- get_costos_tc_sql() — Inversión mensual por canal TC | §71 §78
    -- Reemplaza: get_costos_sql(HIERARCHY_C)
    -- Output: MONTH_ID, CANAL, INV_CANAL, INV_INCENTIVO, INV_TOTAL  ← idéntico
    -- ═══════════════════════════════════════════════════════════════════════
    WITH

    -- ── oc_cost_tc: inversión OC certificada (3 componentes) ─────────────
    -- Mapeo verificado vs Corp centralizado (§71):
    --   INV_CANAL     = COSTO_ENVIO_USD   (costo de envío push/email/wpp ≈ 0)
    --   INV_INCENTIVO = CONSUMIDO_USD     (cashback / incentivo entregado al usuario — el grueso)
    --   INV_TOTAL     = suma de los 3     (igual que antes — CPA no cambia)
    oc_cost_tc AS (
      SELECT
        FORMAT_DATE('%Y%m', DAY_ID)            AS MONTH_ID,
        CASE
          {p['oc_case_stmt']}
        END                                    AS CANAL,
        SUM(COALESCE(COSTO_ENVIO_USD,    0))   AS INV_CANAL,
        SUM(COALESCE(CONSUMIDO_USD,      0))   AS INV_INCENTIVO,
        SUM(COALESCE(CONSUMIDO_USD,      0)
          + COALESCE(COSTO_ENVIO_USD,    0)
          + COALESCE(COSTO_MANTIKA_USD,  0))   AS INV_TOTAL,
        SUM(COALESCE(COSTO_MANTIKA_USD,  0))   AS INV_MANTIKA
      FROM `meli-bi-data.SBOX_EG_MKT.BT_OC_NR_REPORTE_TORRE_DAILY`
      WHERE SITE   = 'MLM'
        AND DAY_ID >= DATE '2025-01-01'
        AND DAY_ID <= DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
      GROUP BY MONTH_ID, CANAL
    ),

    -- ── paid_cost_tc: inversión Paid — solo COST_USD (media cost) ────────
    -- COST_LC_INCENTIVOS excluido: Corp centralizado muestra POM INV_INCENTIVO = $0.
    -- Los incentivos de POM (cashback por install) no se contabilizan como inversión
    -- en el SSOT — son costos de producto, no de canal de marketing.
    -- INV_MANTIKA = 0 para paid channels (Mantika es plataforma exclusiva de OC).
    paid_cost_tc AS (
      SELECT
        FORMAT_DATE('%Y%m', I.TIM_DAY)                             AS MONTH_ID,
        CASE
          {p['paid_case_stmt']}
        END                                                        AS CANAL,
        SUM(COALESCE(I.COST_USD, 0))                               AS INV_CANAL,
        0                                                          AS INV_INCENTIVO,
        SUM(COALESCE(I.COST_USD, 0))                               AS INV_TOTAL,
        0                                                          AS INV_MANTIKA
      FROM `meli-bi-data.SBOX_MARKETING.BT_MP_INDIVIDUALS_PERFORMANCE` I
      LEFT JOIN `meli-bi-data.WHOWNER.LK_API_CURRENCY_CONVERSION` D
        ON  I.SIT_SITE_ID = D.SIT_SITE_ID
        AND I.TIM_DAY     = D.TIM_DAY
      WHERE I.SIT_SITE_ID  = 'MLM'
        AND I.TIM_DAY       >= DATE '2025-01-01'
        AND I.TIM_DAY        <= DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
        AND I.CHANNEL_GROUP != 'OC'
        AND (
          {p['paid_where']}
        )
      GROUP BY I.TIM_DAY, CANAL
    )

    {catchall_cost_cte}
    -- NOTA §78: pom_flag_cost_tc excluido del UNION.
    -- Costos de pom_others FM = solo WEB POM + CTW POM (consistente con N+R).

    SELECT
      MONTH_ID,
      CANAL,
      SUM(INV_CANAL)      AS INV_CANAL,
      SUM(INV_INCENTIVO)  AS INV_INCENTIVO,
      SUM(INV_TOTAL)      AS INV_TOTAL,
      SUM(INV_MANTIKA)    AS INV_MANTIKA
    FROM (
      SELECT MONTH_ID, CANAL, INV_CANAL, INV_INCENTIVO, INV_TOTAL, INV_MANTIKA FROM oc_cost_tc   WHERE CANAL IS NOT NULL
      UNION ALL
      SELECT MONTH_ID, CANAL, INV_CANAL, INV_INCENTIVO, INV_TOTAL, INV_MANTIKA FROM paid_cost_tc  WHERE CANAL IS NOT NULL
      {catchall_cost_union}
    )
    WHERE CANAL IS NOT NULL
    GROUP BY MONTH_ID, CANAL
    """


def get_perf_paid_tc_sql(HIERARCHY_NR):
    """SQL N+R Paid/Free split por canal/mes desde la Torre de Control (TC).

    Reemplaza: get_perf_paid_sql(HIERARCHY_C) — ahora recibe HIERARCHY_NR.
    Output (schema idéntico — processors.py sin cambios):
      MONTH_ID, PERF_CANAL, NR_TOTAL, NR_PAID, NR_GEST_OTHERS

    OC: FLAG_PAID='PAID' → NR_PAID; FLAG_PAID='FREE' → solo NR_TOTAL.
    Paid: COST_USD > 0 → NR_PAID (mismo criterio que COSTOS_CANALES vieja).
    NR_GEST_OTHERS = 0 (métrica legacy MGM sin equivalente directo en TC).
    """
    p = _tc_channel_parts(HIERARCHY_NR)

    return f"""
    -- ═══════════════════════════════════════════════════════════════════════
    -- get_perf_paid_tc_sql() — N+R Paid/Free split por canal/mes TC | §71
    -- Reemplaza: get_perf_paid_sql(HIERARCHY_C)
    -- Output: MONTH_ID, PERF_CANAL, NR_TOTAL, NR_PAID, NR_GEST_OTHERS  ← idéntico
    -- ═══════════════════════════════════════════════════════════════════════
    WITH

    -- ── oc_paid_tc: NR Paid OC via FLAG_PAID ─────────────────────────────
    oc_paid_tc AS (
      SELECT
        FORMAT_DATE('%Y%m', DAY_ID)                                AS MONTH_ID,
        CASE
          {p['oc_case_stmt']}
        END                                                        AS PERF_CANAL,
        SUM(COALESCE(NR_INC_USERS, 0))                            AS NR,
        SUM(CASE WHEN FLAG_PAID = 'PAID'
              THEN COALESCE(NR_INC_USERS, 0) ELSE 0
            END)                                                   AS NR_PAID_SUM
      FROM `meli-bi-data.SBOX_EG_MKT.BT_OC_NR_REPORTE_TORRE_DAILY`
      WHERE SITE   = 'MLM'
        AND DAY_ID >= DATE '2025-01-01'
        AND DAY_ID <= DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
      GROUP BY MONTH_ID, PERF_CANAL
    ),

    -- ── paid_paid_tc: NR Paid donde COST_USD > 0 ─────────────────────────
    -- Mismo criterio que COSTOS_CANALES: si hay inversión → paid.
    paid_paid_tc AS (
      SELECT
        FORMAT_DATE('%Y%m', I.TIM_DAY)                            AS MONTH_ID,
        CASE
          {p['paid_case_stmt']}
        END                                                        AS PERF_CANAL,
        SUM(
          CASE
            WHEN SOURCE_CD = 'INSTALLS'
              THEN COALESCE(NEW_USERS_7D_INAPP,      0) + COALESCE(RECOVERED_USERS_7D_INAPP,      0)
            ELSE  COALESCE(NEW_USERS_INAPP,           0) + COALESCE(RECOVERED_USERS_INAPP,          0)
          END
        )                                                          AS NR,
        SUM(
          CASE WHEN COALESCE(I.COST_USD, 0) > 0
            THEN CASE
              WHEN SOURCE_CD = 'INSTALLS'
                THEN COALESCE(NEW_USERS_7D_INAPP,  0) + COALESCE(RECOVERED_USERS_7D_INAPP,  0)
              ELSE  COALESCE(NEW_USERS_INAPP,       0) + COALESCE(RECOVERED_USERS_INAPP,      0)
            END
            ELSE 0
          END
        )                                                          AS NR_PAID_SUM
      FROM `meli-bi-data.SBOX_MARKETING.BT_MP_INDIVIDUALS_PERFORMANCE` I
      WHERE I.SIT_SITE_ID  = 'MLM'
        AND I.TIM_DAY       >= DATE '2025-01-01'
        AND I.TIM_DAY        <= DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
        AND I.CHANNEL_GROUP != 'OC'
        AND (
          {p['paid_where']}
        )
      GROUP BY I.TIM_DAY, PERF_CANAL
    ){"," if p.get('pom_others_label') else ""}

    {"-- pom_flag_paid_tc: NR Paid POM Others via POM_FLAG §78" if p.get('pom_others_label') else ""}
    {f"""pom_flag_paid_tc AS (
      SELECT
        FORMAT_DATE('%Y%m', I.TIM_DAY)                            AS MONTH_ID,
        '{p["pom_others_label"]}'                                  AS PERF_CANAL,
        SUM(CASE WHEN SOURCE_CD = 'INSTALLS'
                 THEN COALESCE(NEW_USERS_7D_INAPP,0)+COALESCE(RECOVERED_USERS_7D_INAPP,0)
                 ELSE COALESCE(NEW_USERS_INAPP,0)+COALESCE(RECOVERED_USERS_INAPP,0) END) AS NR,
        SUM(CASE WHEN COALESCE(I.COST_USD,0) > 0
                 THEN CASE WHEN SOURCE_CD='INSTALLS'
                           THEN COALESCE(NEW_USERS_7D_INAPP,0)+COALESCE(RECOVERED_USERS_7D_INAPP,0)
                           ELSE COALESCE(NEW_USERS_INAPP,0)+COALESCE(RECOVERED_USERS_INAPP,0)
                      END ELSE 0 END)                              AS NR_PAID_SUM
      FROM `meli-bi-data.SBOX_MARKETING.BT_MP_INDIVIDUALS_PERFORMANCE` I
      WHERE I.SIT_SITE_ID  = 'MLM'
        AND I.TIM_DAY       >= DATE '2025-01-01'
        AND I.TIM_DAY        <= DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
        AND I.CHANNEL_GROUP != 'OC'
        AND UPPER(I.POM_FLAG) IN ('POM ACTIVATION','POM ACQUISITION','POM OTHERS')
      GROUP BY I.TIM_DAY, PERF_CANAL
    )""" if p.get('pom_others_label') else ""}

    SELECT
      MONTH_ID,
      PERF_CANAL,
      SUM(NR)          AS NR_TOTAL,
      SUM(NR_PAID_SUM) AS NR_PAID,
      0                AS NR_GEST_OTHERS
    FROM (
      SELECT MONTH_ID, PERF_CANAL, NR, NR_PAID_SUM FROM oc_paid_tc   WHERE PERF_CANAL IS NOT NULL
      UNION ALL
      SELECT MONTH_ID, PERF_CANAL, NR, NR_PAID_SUM FROM paid_paid_tc  WHERE PERF_CANAL IS NOT NULL
      {"UNION ALL SELECT MONTH_ID, PERF_CANAL, NR, NR_PAID_SUM FROM pom_flag_paid_tc WHERE PERF_CANAL IS NOT NULL" if p.get('pom_others_label') else ""}
    )
    WHERE PERF_CANAL IS NOT NULL
    GROUP BY MONTH_ID, PERF_CANAL
    """


def get_roa_tc_sql():
    """SQL numerador ROA para UCR Gest y OC ACT desde la Torre de Control (TC).

    Reemplaza: get_perf_roa_costos_sql()
    Output (schema idéntico — processors.py sin cambios):
      MONTH_ID (YYYYMM str), PERF_CANAL, ROA_VALUE_PRED

    Solo OC canales: CLASIFICACION='UCRANIA' → UCR Gest, ('ACTIVATION','ADHOC') → OC ACT.
    Filtro FLAG_PAID='PAID' + cost > 0: excluye comms FREE (sin inversión real).
    POM y MGM ROA se calculan desde perf_vpu_prod en processors.py (sin cambio).
    """
    return """
    -- ═══════════════════════════════════════════════════════════════════════
    -- get_roa_tc_sql() — Numerador ROA OC por canal/mes TC | §71 History.md
    -- Reemplaza: get_perf_roa_costos_sql()
    -- Output: MONTH_ID, PERF_CANAL, ROA_VALUE_PRED  ← schema idéntico
    -- ═══════════════════════════════════════════════════════════════════════
    SELECT
      FORMAT_DATE('%Y%m', DAY_ID)            AS MONTH_ID,
      CASE
        WHEN CLASIFICACION = 'UCRANIA'                THEN 'UCR Gest'
        WHEN CLASIFICACION IN ('ACTIVATION', 'ADHOC') THEN 'OC ACT'
      END                                            AS PERF_CANAL,
      SUM(COALESCE(NR_INC_VALUE, 0))                 AS ROA_VALUE_PRED
    FROM `meli-bi-data.SBOX_EG_MKT.BT_OC_NR_REPORTE_TORRE_DAILY`
    WHERE SITE      = 'MLM'
      AND DAY_ID    >= DATE '2025-01-01'
      AND DAY_ID    <= DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
      AND FLAG_PAID  = 'PAID'
      AND CLASIFICACION IN ('UCRANIA', 'ACTIVATION', 'ADHOC')
      -- Solo filas con inversión real (igual que get_perf_roa_costos_sql con INV > 0)
      AND (COALESCE(CONSUMIDO_USD, 0) + COALESCE(COSTO_ENVIO_USD, 0) + COALESCE(COSTO_MANTIKA_USD, 0)) > 0
    GROUP BY MONTH_ID, PERF_CANAL
    HAVING PERF_CANAL IS NOT NULL
    """


def get_costos_sql(HIERARCHY_C):
    """DEPRECATED §72 — NO USADO. Reemplazado por get_costos_tc_sql().
    SQL inversión mensual por canal desde PANEL_MONTHLY_COSTOS_CANALES.
    El CASE WHEN se genera automáticamente desde hierarchy_cost → cost_mapping.
    Resultado: una fila por (MONTH_ID, CANAL) con INV_CANAL, INV_INCENTIVO, INV_TOTAL.
    """
    cases = []
    for c in HIERARCHY_C:
        if c.get('is_leaf') and 'cost_mapping' in c:
            m      = c['cost_mapping']
            ch     = m['channel']
            strats = m['strategy']
            st     = f"('{strats[0]}')" if len(strats) == 1 else str(tuple(strats))
            cases.append(f"WHEN CHANNEL = '{ch}' AND STRATEGY IN {st} THEN '{c['label']}'")
    case_stmt = "\n        ".join(cases)
    return f"""
    WITH base AS (
      SELECT
        MONTH_ID,
        CASE {case_stmt}
        END AS CANAL,
        INVERSION_CANAL_USD,
        INVERSION_INCENTIVO_USD,
        INVERSION_TOTAL_USD
      FROM `meli-bi-data.SBOX_MKTCORPMP.PANEL_MONTHLY_COSTOS_CANALES`
      WHERE SIT_SITE_ID = 'MLM'
        AND MONTH_ID >= '202501'
    )
    SELECT
      MONTH_ID,
      CANAL,
      SUM(INVERSION_CANAL_USD)     AS INV_CANAL,
      SUM(INVERSION_INCENTIVO_USD) AS INV_INCENTIVO,
      SUM(INVERSION_TOTAL_USD)     AS INV_TOTAL
    FROM base
    WHERE CANAL IS NOT NULL
    GROUP BY MONTH_ID, CANAL
    """


def get_perf_paid_sql(HIERARCHY_C):
    """DEPRECATED §72 — NO USADO. Reemplazado por get_perf_paid_tc_sql().
    SQL N+R Paid y Gest Others por canal desde PANEL_MONTHLY_COSTOS_CANALES.
    Mapeos derivados de hierarchy_cost → cost_mapping (misma lógica que get_costos_sql).
    gest_others_strategies en cost_mapping marca qué estrategias son N+R Gest Others.
    Resultado: una fila por (MONTH_ID, PERF_CANAL) con NR_TOTAL, NR_PAID, NR_GEST_OTHERS.
    """
    cases_canal = []
    cases_go    = []
    for c in HIERARCHY_C:
        if not (c.get('is_leaf') and 'cost_mapping' in c):
            continue
        cm     = c['cost_mapping']
        ch     = cm['channel']
        strats = cm['strategy']
        st     = f"('{strats[0]}')" if len(strats) == 1 else str(tuple(strats))
        cases_canal.append(f"WHEN CHANNEL = '{ch}' AND STRATEGY IN {st} THEN '{c['label']}'")
        go_strats = cm.get('gest_others_strategies', [])
        if go_strats:
            go_st = f"('{go_strats[0]}')" if len(go_strats) == 1 else str(tuple(go_strats))
            cases_go.append(f"WHEN CHANNEL = '{ch}' AND STRATEGY IN {go_st} THEN COALESCE(NR, 0)")

    case_canal = "\n          ".join(cases_canal)
    go_expr    = f"CASE {chr(10).join(cases_go)} ELSE 0 END" if cases_go else "0"
    return f"""
    WITH base AS (
      SELECT
        MONTH_ID,
        CASE {case_canal}
        END AS PERF_CANAL,
        {go_expr} AS NR_GEST_OTHERS,
        CASE WHEN COALESCE(INVERSION_TOTAL_USD, 0) > 0 THEN COALESCE(NR, 0) ELSE 0 END AS NR_PAID,
        COALESCE(NR, 0) AS NR
      FROM `meli-bi-data.SBOX_MKTCORPMP.PANEL_MONTHLY_COSTOS_CANALES`
      WHERE SIT_SITE_ID = 'MLM' AND MONTH_ID >= '202501'
    )
    SELECT
      MONTH_ID,
      PERF_CANAL,
      SUM(NR)             AS NR_TOTAL,
      SUM(NR_PAID)        AS NR_PAID,
      SUM(NR_GEST_OTHERS) AS NR_GEST_OTHERS
    FROM base
    WHERE PERF_CANAL IS NOT NULL
    GROUP BY MONTH_ID, PERF_CANAL
    """


def get_nr_corp_tc_sql(HIERARCHY_NR=None):
    """SQL tabla corporativa N+R mensual desde la Torre de Control (TC).

    Reemplaza: get_nr_corp_sql()
    Output (schema idéntico — process_nr_corp() sin cambios):
      fecha_mes_corp (YYYYMM str), corp_key (str), nr_total_corp (float)

    HIERARCHY_NR: opcional. Si se pasa, extrae dinámicamente las redes L&P adicionales
      definidas en channels_config.json (lp_adq/lp_act tc_mapping.network_group_name_tc).
      Redes estándar (LANDINGS/TELCEL/AFFILIATES/PARTNERSHIPS/BRANDFORMANCE/GTM) mapean
      a sus corp_key específicos. Redes extra mapean a 'OTH|LP|OTHERS'.
      → Así agregar una red a channels_config.json actualiza automáticamente FM + Corp.

    Fuentes TC:
      oc_corp_tc   → BT_OC_NR_REPORTE_TORRE_DAILY  (CLASIFICACION + CANAL → corp_key)
      paid_corp_tc → BT_MP_INDIVIDUALS_PERFORMANCE   (STRATEGY_GROUP / NETWORK → corp_key)
      org_corp_tc  → BT_MP_INDIVIDUALS_PERFORMANCE   (NOT NETWORK APPE + OTHER + TOOL_COST → NOATRIB, §75)
    """
    # Redes L&P con corp_key específico (mapeadas directamente, no a OTHERS)
    _LP_KNOWN = {'LANDINGS', 'TELCEL', 'AFFILIATES', 'PARTNERSHIPS', 'BRANDFORMANCE', 'GTM'}

    # Extraer redes extra de channels_config.json si se pasa HIERARCHY_NR
    _lp_extra = []
    if HIERARCHY_NR:
        for c in HIERARCHY_NR:
            if 'lp' in c.get('id', '').lower() and c.get('tc_mapping'):
                for net in c['tc_mapping'].get('network_group_name_tc', []):
                    if net.upper() not in _LP_KNOWN:
                        _lp_extra.append(net.upper())
    _lp_extra = sorted(set(_lp_extra))

    # CASE WHEN dinámico para redes extra → todas a 'OTH|LP|OTHERS'
    if _lp_extra:
        nets_sql  = ', '.join(f"'{n}'" for n in _lp_extra)
        lp_extra_case      = (f"-- L&P extra (leídas de channels_config.json §88):\n"
                              f"          WHEN UPPER(NETWORK_GROUP_NAME) IN ({nets_sql})"
                              f"              THEN 'OTH|LP|OTHERS'")
        lp_extra_whitelist = f",\n            {nets_sql}"
    else:
        lp_extra_case      = "-- (sin redes L&P extra en channels_config.json)"
        lp_extra_whitelist = ""

    return f"""
    -- ═══════════════════════════════════════════════════════════════════════
    -- get_nr_corp_tc_sql() — Tabla Corporativa N+R mensual TC | §71
    -- Reemplaza: get_nr_corp_sql()
    -- Output: fecha_mes_corp, corp_key, nr_total_corp  ← schema idéntico
    -- ═══════════════════════════════════════════════════════════════════════
    WITH

    -- ── oc_corp_tc: OC desde Torre de Control ────────────────────────────
    -- CLASIFICACION + CANAL → corp_key.
    -- §78 Fix UCR PRD: OTHER RECURRING → OTH|UCR_PRD|TOTAL (antes iba a OC_REC — incorrecto).
    -- WHATSAPP en Torre = WPP en corp_key (cambio de nombre, §71).
    oc_corp_tc AS (
      SELECT
        FORMAT_DATE('%Y%m', DAY_ID)   AS fecha_mes_corp,
        CASE
          -- UCRANIA E&G (5 medios + catch-all OTROS)
          WHEN CLASIFICACION = 'UCRANIA' AND UPPER(CANAL) IN ('EMAIL','SMS')  THEN 'OC|UCR_EG|EMAIL'
          WHEN CLASIFICACION = 'UCRANIA' AND UPPER(CANAL) = 'PANDORA'         THEN 'OC|UCR_EG|PANDORA'
          WHEN CLASIFICACION = 'UCRANIA' AND UPPER(CANAL) = 'PUSH'            THEN 'OC|UCR_EG|PUSH'
          WHEN CLASIFICACION = 'UCRANIA' AND UPPER(CANAL) LIKE 'REAL ESTATE%' THEN 'OC|UCR_EG|REAL_ESTATES'
          WHEN CLASIFICACION = 'UCRANIA' AND UPPER(CANAL) = 'WHATSAPP'        THEN 'OC|UCR_EG|WPP'
          WHEN CLASIFICACION = 'UCRANIA'                                      THEN 'OC|UCR_EG|OTROS'
          -- OTHER RECURRING JOURNEY → OC_REC|JOURNEY (journeys son OC Recurring, no UCR PRD §79)
          WHEN CLASIFICACION = 'OTHER RECURRING' AND UPPER(CANAL) = 'JOURNEY' THEN 'OC|OC_REC|JOURNEY'
          -- OTHER RECURRING resto → UCR PRD (§78: PUSH/WPP/EMAIL del equipo de producto)
          WHEN CLASIFICACION = 'OTHER RECURRING'                              THEN 'OTH|UCR_PRD|TOTAL'
          -- ACTIVATION → OC_REC (5 medios + catch-all OTROS)
          WHEN CLASIFICACION = 'ACTIVATION' AND UPPER(CANAL) = 'EMAIL'        THEN 'OC|OC_REC|EMAIL'
          WHEN CLASIFICACION = 'ACTIVATION' AND UPPER(CANAL) = 'JOURNEY'      THEN 'OC|OC_REC|JOURNEY'
          WHEN CLASIFICACION = 'ACTIVATION' AND UPPER(CANAL) = 'PANDORA'      THEN 'OC|OC_REC|PANDORA'
          WHEN CLASIFICACION = 'ACTIVATION' AND UPPER(CANAL) = 'PUSH'         THEN 'OC|OC_REC|PUSH'
          WHEN CLASIFICACION = 'ACTIVATION' AND UPPER(CANAL) = 'WHATSAPP'     THEN 'OC|OC_REC|WPP'
          WHEN CLASIFICACION = 'ACTIVATION'                                   THEN 'OC|OC_REC|OTROS'
          -- ADHOC → OC_ADHOC bucket total (sin desglose de medios)
          WHEN CLASIFICACION = 'ADHOC'                                        THEN 'OC|OC_ADHOC|TOTAL'
        END                           AS corp_key,
        COALESCE(NR_INC_USERS, 0)    AS nr_corp
      FROM `meli-bi-data.SBOX_EG_MKT.BT_OC_NR_REPORTE_TORRE_DAILY`
      WHERE SITE   = 'MLM'
        AND DAY_ID >= DATE '2025-01-01'
        AND DAY_ID <= DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
    ),

    -- ── paid_corp_tc: POM / MGM / L&P desde Individuals Performance ──────
    -- §78 Fixes:
    --   POM Others: UPPER(POM_FLAG) IN ('POM ACTIVATION','POM ACQUISITION','POM OTHERS')
    --     dispara ANTES de las redes orgánicas (igual que query de referencia del equipo).
    --   L&P: UPPER() consistente en todos los WHEN para capturar cualquier casing.
    --   Rows con STRATEGY_GROUP='' y NETWORK_GROUP_NAME=PARTNERSHIPS/LANDINGS/BRANDFORMANCE
    --     pasan por la nueva condición UPPER() sin depender de STRATEGY_GROUP.
    paid_corp_tc AS (
      SELECT
        FORMAT_DATE('%Y%m', TIM_DAY)  AS fecha_mes_corp,
        CASE
          -- POM sub-canales directos (strategy_group named)
          WHEN STRATEGY_GROUP = 'ACQUISITION POM'    THEN 'POM|ACQ_POM|TOTAL'
          WHEN STRATEGY_GROUP = 'WEB POM'            THEN 'POM|WEB_POM|TOTAL'
          WHEN STRATEGY_GROUP = 'CTW POM'            THEN 'POM|CTW_POM|TOTAL'
          WHEN STRATEGY_GROUP = 'ACTIVATION POM'     THEN 'POM|ACT_POM|TOTAL'
          -- MGM (installs + activación)
          WHEN UPPER(NETWORK_GROUP_NAME) IN ('MGM','MGM ECOSISTEMICO')
               OR STRATEGY_GROUP = 'ACTIVATION MGM'  THEN 'OTH|MGM|TOTAL'
          -- L&P por sub-canal de red (UPPER en todos para capturar cualquier casing)
          WHEN UPPER(NETWORK_GROUP_NAME) IN ('LANDINGS','TELCEL')    THEN 'OTH|LP|LANDINGS'
          WHEN UPPER(NETWORK_GROUP_NAME) = 'AFFILIATES'              THEN 'OTH|LP|AFFILIATES'
          WHEN UPPER(NETWORK_GROUP_NAME) = 'PARTNERSHIPS'            THEN 'OTH|LP|PARTNERSHIPS'
          WHEN UPPER(NETWORK_GROUP_NAME) = 'BRANDFORMANCE'           THEN 'OTH|LP|BRANDFORMANCE'
          WHEN STRATEGY_GROUP = 'GTM'                                THEN 'OTH|LP|GTM'
          {lp_extra_case}
          -- POM Others: POM_FLAG dispara ANTES de redes orgánicas (igual que query referencia)
          -- Captura DV360/Google/Tiktok/Facebook con POM_FLAG='POM Others'
          WHEN UPPER(POM_FLAG) IN ('POM ACTIVATION','POM ACQUISITION','POM OTHERS')
                                                     THEN 'OTH|POM_OTHERS|TOTAL'
        END                           AS corp_key,
        CASE
          WHEN SOURCE_CD = 'INSTALLS'
            THEN COALESCE(NEW_USERS_7D_INAPP,      0) + COALESCE(RECOVERED_USERS_7D_INAPP,      0)
          ELSE  COALESCE(NEW_USERS_INAPP,           0) + COALESCE(RECOVERED_USERS_INAPP,          0)
        END                           AS nr_corp
      FROM `meli-bi-data.SBOX_MARKETING.BT_MP_INDIVIDUALS_PERFORMANCE`
      WHERE SIT_SITE_ID  = 'MLM'
        AND TIM_DAY       >= DATE '2025-01-01'
        AND TIM_DAY        <= DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
        AND CHANNEL_GROUP != 'OC'
        AND (
          STRATEGY_GROUP IN ('ACQUISITION POM','WEB POM','CTW POM','ACTIVATION POM',
                             'ACTIVATION MGM','GTM')
          OR UPPER(NETWORK_GROUP_NAME) IN ('MGM','MGM ECOSISTEMICO',
            'LANDINGS','TELCEL','AFFILIATES','PARTNERSHIPS','BRANDFORMANCE'
            {lp_extra_whitelist})
          OR UPPER(POM_FLAG) IN ('POM ACTIVATION','POM ACQUISITION','POM OTHERS')
        )
    ),

    -- ── others_catchall_corp_tc: catch-all §78 ───────────────────────────
    -- Filas BT_MP_INDIVIDUALS_PERFORMANCE no clasificadas en whitelist paid_corp_tc.
    others_catchall_corp_tc AS (
      SELECT
        FORMAT_DATE('%Y%m', TIM_DAY)   AS fecha_mes_corp,
        'OTH|OTHERS_CATCHALL|TOTAL'    AS corp_key,
        SUM(CASE
          WHEN SOURCE_CD = 'INSTALLS'
            THEN COALESCE(NEW_USERS_7D_INAPP,0) + COALESCE(RECOVERED_USERS_7D_INAPP,0)
          ELSE  COALESCE(NEW_USERS_INAPP,0)     + COALESCE(RECOVERED_USERS_INAPP,0)
        END)                           AS nr_corp
      FROM `meli-bi-data.SBOX_MARKETING.BT_MP_INDIVIDUALS_PERFORMANCE`
      WHERE SIT_SITE_ID              = 'MLM'
        AND TIM_DAY                   >= DATE '2025-01-01'
        AND TIM_DAY                    <= DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
        AND UPPER(CHANNEL_GROUP)      != 'OC'
        AND NOT (STRATEGY_GROUP IN ('PANDORA', 'OC'))
        AND UPPER(NETWORK_GROUP_NAME) != 'NOT NETWORK APPE'
        AND NOT (STRATEGY_GROUP IN ('ACQUISITION POM','WEB POM','CTW POM','ACTIVATION POM',
                                    'ACTIVATION MGM','GTM'))
        AND UPPER(NETWORK_GROUP_NAME) NOT IN ('MGM','MGM ECOSISTEMICO',
          'LANDINGS','TELCEL','AFFILIATES','PARTNERSHIPS','BRANDFORMANCE')
      GROUP BY TIM_DAY
    ),

    -- ── ucr_prd_indiv_tc: UCR PRD via RE placements (BT_MP_INDIVIDUALS_PERFORMANCE §79) ──
    -- Patrón referencia: REAL ESTATE + campaign name = product placements del equipo PRD.
    -- CHANNEL_GROUP != 'OC' → evita doble conteo con Torre Daily (OC managed RE).
    -- Estos rows ya están en others_catchall_corp_tc → ya se restan de NO ATRIBUIDO.
    -- Al añadirlos aquí, MIGRAN de "invisible" a UCR PRD visible, sin cambiar el total.
    ucr_prd_indiv_tc AS (
      SELECT
        FORMAT_DATE('%Y%m', TIM_DAY)                               AS fecha_mes_corp,
        'OTH|UCR_PRD|TOTAL'                                        AS corp_key,
        SUM(CASE
          WHEN SOURCE_CD = 'INSTALLS'
            THEN COALESCE(NEW_USERS_7D_INAPP, 0) + COALESCE(RECOVERED_USERS_7D_INAPP, 0)
          ELSE  COALESCE(NEW_USERS_INAPP,     0) + COALESCE(RECOVERED_USERS_INAPP,     0)
        END)                                                       AS nr_corp
      FROM `meli-bi-data.SBOX_MARKETING.BT_MP_INDIVIDUALS_PERFORMANCE`
      WHERE SIT_SITE_ID = 'MLM'
        AND TIM_DAY      >= DATE '2025-01-01'
        AND TIM_DAY       <= DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
        AND CHANNEL_GROUP != 'OC'   -- excluye RE ya en Torre Daily (OC managed)
        AND (
          (UPPER(NETWORK_GROUP_NAME) = 'REAL ESTATE'
            AND REGEXP_CONTAINS(UPPER(CAMPAIGN_NAME),
              r'DRAWER|FALLBACK|HOME_ML|HUB_CREDITS|REFUNDS_ML|CREDITS_PERSONAL_LOANS|BANNER-LOYALTY-ML|HUB-LOYALTY_ML|ADMIN_CREDITS|MUSD|MELIMAIS|MELIMAS|MELIDOLAR|MERCADO_COIN|INSUR'))
          OR (UPPER(NETWORK_GROUP_NAME) = 'OTHERS'
            AND REGEXP_CONTAINS(UPPER(CAMPAIGN_NAME), r'ACQUISITION_TC|CX_SOLICITUD_'))
          OR UPPER(NETWORK_GROUP_NAME) = 'LOYALTY'
        )
      GROUP BY TIM_DAY
    ),

    -- ── Totales para calcular residual NO ATRIBUIDO (§82 fix) ──────────────
    -- §82: sustituimos catch_total_corp por ucr_total_corp como sustracción explícita.
    -- Esto elimina el "lost NR" (~1,200/mes) que before se restaba del residual
    -- vía others_catchall pero nunca aparecía en ningún nodo de la jerarquía.
    oc_total_corp   AS (SELECT fecha_mes_corp, SUM(nr_corp) AS nr FROM oc_corp_tc   WHERE corp_key IS NOT NULL GROUP BY 1),
    paid_total_corp AS (SELECT fecha_mes_corp, SUM(nr_corp) AS nr FROM paid_corp_tc  WHERE corp_key IS NOT NULL GROUP BY 1),
    ucr_total_corp  AS (SELECT fecha_mes_corp, SUM(nr_corp) AS nr FROM ucr_prd_indiv_tc GROUP BY 1),

    -- ── inapp_total_corp: Total N+R desde BT_MP_USER_ENGAGEMENT_INAPP (§78) ─
    -- ~20 GB para MLM desde 2025-01-01. Fuente del residual NO ATRIBUIDO.
    inapp_total_corp AS (
      SELECT
        FORMAT_DATE('%Y%m', EVENT_DATE) AS fecha_mes_corp,
        (COUNT(DISTINCT CASE WHEN DAYS_SINCE_FIRST_EVENT = 0  THEN CUS_CUST_ID END) +
         COUNT(DISTINCT CASE WHEN DAYS_SINCE_PRIOR_EVENT > 89 THEN CUS_CUST_ID END)) AS nr_total
      FROM `meli-bi-data.SBOX_MARKETING.BT_MP_USER_ENGAGEMENT_INAPP`
      WHERE SIT_SITE_ID = 'MLM'
        AND EVENT_DATE  >= DATE '2025-01-01'
        AND EVENT_DATE   <= DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
        AND (DAYS_SINCE_FIRST_EVENT = 0 OR DAYS_SINCE_PRIOR_EVENT > 89)
      GROUP BY fecha_mes_corp
    ),

    -- ── org_corp_tc: NO ATRIBUIDO = INAPP − OC − PAID − UCR_PRD ─────────────
    -- §82: fórmula alineada con FM org_legacy_tc: INAPP − OC − PAID − UCR_PRD.
    -- Garantiza Corp Total = FM Total = INAPP (sin "lost NR" de others_catchall).
    -- Nota: PAID incluye POM_FLAG (~1K/mes) → Corp NO ATRIBUIDO difiere de FM ORG
    -- en exactamente el importe de POM_Others (diseño: Corp lo muestra por separado).
    org_corp_tc AS (
      SELECT
        t.fecha_mes_corp,
        'NOATRIB|ORGANICO|TOTAL'        AS corp_key,
        GREATEST(
          t.nr_total
          - COALESCE(oc.nr,   0)
          - COALESCE(p.nr,    0)
          - COALESCE(u.nr,    0),
          0
        )                               AS nr_corp
      FROM inapp_total_corp t
      LEFT JOIN oc_total_corp    oc  ON t.fecha_mes_corp = oc.fecha_mes_corp
      LEFT JOIN paid_total_corp  p   ON t.fecha_mes_corp = p.fecha_mes_corp
      LEFT JOIN ucr_total_corp   u   ON t.fecha_mes_corp = u.fecha_mes_corp
    )

    SELECT
      fecha_mes_corp,
      corp_key,
      SUM(nr_corp) AS nr_total_corp
    FROM (
      SELECT fecha_mes_corp, corp_key, nr_corp FROM oc_corp_tc            WHERE corp_key IS NOT NULL
      UNION ALL
      SELECT fecha_mes_corp, corp_key, nr_corp FROM paid_corp_tc           WHERE corp_key IS NOT NULL
      UNION ALL
      SELECT fecha_mes_corp, corp_key, nr_corp FROM ucr_prd_indiv_tc
      -- §82: others_catchall_corp_tc eliminado del UNION ALL.
      -- Antes sus filas se restaban del residual Y se descartaban por bq_key desconocido
      -- → "lost NR" de ~1,200/mes. Ahora el residual usa ucr_total_corp directamente.
      UNION ALL
      SELECT fecha_mes_corp, corp_key, nr_corp FROM org_corp_tc
    )
    GROUP BY fecha_mes_corp, corp_key
    ORDER BY fecha_mes_corp, corp_key
    """


def get_nr_corp_daily_tc_sql(HIERARCHY_NR=None):
    """SQL tabla corporativa N+R DIARIA desde la Torre de Control (TC).

    Reemplaza: get_nr_corp_daily_sql()
    Output (schema idéntico — process_nr_corp_daily() sin cambios):
      fecha_mes_corp, dia_del_mes (int), corp_key, nr_dia_corp

    HIERARCHY_NR: mismo patrón dinámico que get_nr_corp_tc_sql() — lee redes
      L&P extras de channels_config.json y las añade al CASE WHEN Corp.
    """
    _LP_KNOWN = {'LANDINGS', 'TELCEL', 'AFFILIATES', 'PARTNERSHIPS', 'BRANDFORMANCE', 'GTM'}
    _lp_extra = []
    if HIERARCHY_NR:
        for c in HIERARCHY_NR:
            if 'lp' in c.get('id', '').lower() and c.get('tc_mapping'):
                for net in c['tc_mapping'].get('network_group_name_tc', []):
                    if net.upper() not in _LP_KNOWN:
                        _lp_extra.append(net.upper())
    _lp_extra = sorted(set(_lp_extra))

    if _lp_extra:
        nets_sql  = ', '.join(f"'{n}'" for n in _lp_extra)
        lp_extra_case      = (f"-- L&P extra (channels_config.json §88):\n"
                              f"          WHEN UPPER(NETWORK_GROUP_NAME) IN ({nets_sql})"
                              f"              THEN 'OTH|LP|OTHERS'")
        lp_extra_whitelist = f",\n            {nets_sql}"
    else:
        lp_extra_case      = ""
        lp_extra_whitelist = ""

    return f"""
    -- ═══════════════════════════════════════════════════════════════════════
    -- get_nr_corp_daily_tc_sql() — Tabla Corporativa N+R diaria TC | §71
    -- Reemplaza: get_nr_corp_daily_sql()
    -- Output: fecha_mes_corp, dia_del_mes, corp_key, nr_dia_corp  ← idéntico
    -- ═══════════════════════════════════════════════════════════════════════
    WITH

    -- §78: OTHER RECURRING → OTH|UCR_PRD|TOTAL (fix UCR PRD)
    oc_corp_daily_tc AS (
      SELECT
        FORMAT_DATE('%Y%m', DAY_ID)             AS fecha_mes_corp,
        CAST(EXTRACT(DAY FROM DAY_ID) AS INT64) AS dia_del_mes,
        CASE
          WHEN CLASIFICACION = 'UCRANIA' AND UPPER(CANAL) IN ('EMAIL','SMS')  THEN 'OC|UCR_EG|EMAIL'
          WHEN CLASIFICACION = 'UCRANIA' AND UPPER(CANAL) = 'PANDORA'         THEN 'OC|UCR_EG|PANDORA'
          WHEN CLASIFICACION = 'UCRANIA' AND UPPER(CANAL) = 'PUSH'            THEN 'OC|UCR_EG|PUSH'
          WHEN CLASIFICACION = 'UCRANIA' AND UPPER(CANAL) LIKE 'REAL ESTATE%' THEN 'OC|UCR_EG|REAL_ESTATES'
          WHEN CLASIFICACION = 'UCRANIA' AND UPPER(CANAL) = 'WHATSAPP'        THEN 'OC|UCR_EG|WPP'
          WHEN CLASIFICACION = 'UCRANIA'                                      THEN 'OC|UCR_EG|OTROS'
          -- OTHER RECURRING JOURNEY → OC_REC|JOURNEY (journeys son OC Recurring, no UCR PRD §79)
          WHEN CLASIFICACION = 'OTHER RECURRING' AND UPPER(CANAL) = 'JOURNEY' THEN 'OC|OC_REC|JOURNEY'
          -- OTHER RECURRING resto → UCR PRD (§78: PUSH/WPP/EMAIL del equipo de producto)
          WHEN CLASIFICACION = 'OTHER RECURRING'                              THEN 'OTH|UCR_PRD|TOTAL'
          WHEN CLASIFICACION = 'ACTIVATION' AND UPPER(CANAL) = 'EMAIL'        THEN 'OC|OC_REC|EMAIL'
          WHEN CLASIFICACION = 'ACTIVATION' AND UPPER(CANAL) = 'JOURNEY'      THEN 'OC|OC_REC|JOURNEY'
          WHEN CLASIFICACION = 'ACTIVATION' AND UPPER(CANAL) = 'PANDORA'      THEN 'OC|OC_REC|PANDORA'
          WHEN CLASIFICACION = 'ACTIVATION' AND UPPER(CANAL) = 'PUSH'         THEN 'OC|OC_REC|PUSH'
          WHEN CLASIFICACION = 'ACTIVATION' AND UPPER(CANAL) = 'WHATSAPP'     THEN 'OC|OC_REC|WPP'
          WHEN CLASIFICACION = 'ACTIVATION'                                   THEN 'OC|OC_REC|OTROS'
          WHEN CLASIFICACION = 'ADHOC'                                        THEN 'OC|OC_ADHOC|TOTAL'
        END                                     AS corp_key,
        COALESCE(NR_INC_USERS, 0)              AS nr_corp
      FROM `meli-bi-data.SBOX_EG_MKT.BT_OC_NR_REPORTE_TORRE_DAILY`
      WHERE SITE   = 'MLM'
        AND DAY_ID >= DATE '2025-01-01'
        AND DAY_ID <= DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
    ),

    -- §78: UPPER() consistente en L&P + POM_FLAG para POM Others
    paid_corp_daily_tc AS (
      SELECT
        FORMAT_DATE('%Y%m', TIM_DAY)             AS fecha_mes_corp,
        CAST(EXTRACT(DAY FROM TIM_DAY) AS INT64) AS dia_del_mes,
        CASE
          WHEN STRATEGY_GROUP = 'ACQUISITION POM'    THEN 'POM|ACQ_POM|TOTAL'
          WHEN STRATEGY_GROUP = 'WEB POM'            THEN 'POM|WEB_POM|TOTAL'
          WHEN STRATEGY_GROUP = 'CTW POM'            THEN 'POM|CTW_POM|TOTAL'
          WHEN STRATEGY_GROUP = 'ACTIVATION POM'     THEN 'POM|ACT_POM|TOTAL'
          WHEN UPPER(NETWORK_GROUP_NAME) IN ('MGM','MGM ECOSISTEMICO')
               OR STRATEGY_GROUP = 'ACTIVATION MGM'  THEN 'OTH|MGM|TOTAL'
          WHEN UPPER(NETWORK_GROUP_NAME) IN ('LANDINGS','TELCEL')    THEN 'OTH|LP|LANDINGS'
          WHEN UPPER(NETWORK_GROUP_NAME) = 'AFFILIATES'              THEN 'OTH|LP|AFFILIATES'
          WHEN UPPER(NETWORK_GROUP_NAME) = 'PARTNERSHIPS'            THEN 'OTH|LP|PARTNERSHIPS'
          WHEN UPPER(NETWORK_GROUP_NAME) = 'BRANDFORMANCE'           THEN 'OTH|LP|BRANDFORMANCE'
          WHEN STRATEGY_GROUP = 'GTM'                                THEN 'OTH|LP|GTM'
          {lp_extra_case}
          WHEN UPPER(POM_FLAG) IN ('POM ACTIVATION','POM ACQUISITION','POM OTHERS')
                                                     THEN 'OTH|POM_OTHERS|TOTAL'
        END                                      AS corp_key,
        CASE
          WHEN SOURCE_CD = 'INSTALLS'
            THEN COALESCE(NEW_USERS_7D_INAPP,  0) + COALESCE(RECOVERED_USERS_7D_INAPP,  0)
          ELSE  COALESCE(NEW_USERS_INAPP,       0) + COALESCE(RECOVERED_USERS_INAPP,      0)
        END                                      AS nr_corp
      FROM `meli-bi-data.SBOX_MARKETING.BT_MP_INDIVIDUALS_PERFORMANCE`
      WHERE SIT_SITE_ID  = 'MLM'
        AND TIM_DAY       >= DATE '2025-01-01'
        AND TIM_DAY        <= DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
        AND CHANNEL_GROUP != 'OC'
        AND (
          STRATEGY_GROUP IN ('ACQUISITION POM','WEB POM','CTW POM','ACTIVATION POM',
                             'ACTIVATION MGM','GTM')
          OR UPPER(NETWORK_GROUP_NAME) IN ('MGM','MGM ECOSISTEMICO',
            'LANDINGS','TELCEL','AFFILIATES','PARTNERSHIPS','BRANDFORMANCE'
            {lp_extra_whitelist})
          OR UPPER(POM_FLAG) IN ('POM ACTIVATION','POM ACQUISITION','POM OTHERS')
        )
    ),

    -- others_catchall_corp_daily_tc: catch-all §78 (diario)
    others_catchall_corp_daily_tc AS (
      SELECT
        FORMAT_DATE('%Y%m', TIM_DAY)             AS fecha_mes_corp,
        CAST(EXTRACT(DAY FROM TIM_DAY) AS INT64) AS dia_del_mes,
        'OTH|OTHERS_CATCHALL|TOTAL'              AS corp_key,
        SUM(CASE
          WHEN SOURCE_CD = 'INSTALLS'
            THEN COALESCE(NEW_USERS_7D_INAPP,0) + COALESCE(RECOVERED_USERS_7D_INAPP,0)
          ELSE  COALESCE(NEW_USERS_INAPP,0)     + COALESCE(RECOVERED_USERS_INAPP,0)
        END)                                     AS nr_corp
      FROM `meli-bi-data.SBOX_MARKETING.BT_MP_INDIVIDUALS_PERFORMANCE`
      WHERE SIT_SITE_ID              = 'MLM'
        AND TIM_DAY                   >= DATE '2025-01-01'
        AND TIM_DAY                    <= DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
        AND UPPER(CHANNEL_GROUP)      != 'OC'
        AND NOT (STRATEGY_GROUP IN ('PANDORA', 'OC'))
        AND UPPER(NETWORK_GROUP_NAME) != 'NOT NETWORK APPE'
        AND NOT (STRATEGY_GROUP IN ('ACQUISITION POM','WEB POM','CTW POM','ACTIVATION POM',
                                    'ACTIVATION MGM','GTM'))
        AND UPPER(NETWORK_GROUP_NAME) NOT IN ('MGM','MGM ECOSISTEMICO',
          'LANDINGS','TELCEL','AFFILIATES','PARTNERSHIPS','BRANDFORMANCE')
      GROUP BY TIM_DAY
    ),

    -- ── ucr_prd_indiv_daily_tc: UCR PRD via RE placements diario (§79) ──
    ucr_prd_indiv_daily_tc AS (
      SELECT
        FORMAT_DATE('%Y%m', TIM_DAY)             AS fecha_mes_corp,
        CAST(EXTRACT(DAY FROM TIM_DAY) AS INT64) AS dia_del_mes,
        'OTH|UCR_PRD|TOTAL'                      AS corp_key,
        SUM(CASE
          WHEN SOURCE_CD = 'INSTALLS'
            THEN COALESCE(NEW_USERS_7D_INAPP, 0) + COALESCE(RECOVERED_USERS_7D_INAPP, 0)
          ELSE  COALESCE(NEW_USERS_INAPP,     0) + COALESCE(RECOVERED_USERS_INAPP,     0)
        END)                                     AS nr_corp
      FROM `meli-bi-data.SBOX_MARKETING.BT_MP_INDIVIDUALS_PERFORMANCE`
      WHERE SIT_SITE_ID = 'MLM'
        AND TIM_DAY      >= DATE '2025-01-01'
        AND TIM_DAY       <= DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
        AND CHANNEL_GROUP != 'OC'
        AND (
          (UPPER(NETWORK_GROUP_NAME) = 'REAL ESTATE'
            AND REGEXP_CONTAINS(UPPER(CAMPAIGN_NAME),
              r'DRAWER|FALLBACK|HOME_ML|HUB_CREDITS|REFUNDS_ML|CREDITS_PERSONAL_LOANS|BANNER-LOYALTY-ML|HUB-LOYALTY_ML|ADMIN_CREDITS|MUSD|MELIMAIS|MELIMAS|MELIDOLAR|MERCADO_COIN|INSUR'))
          OR (UPPER(NETWORK_GROUP_NAME) = 'OTHERS'
            AND REGEXP_CONTAINS(UPPER(CAMPAIGN_NAME), r'ACQUISITION_TC|CX_SOLICITUD_'))
          OR UPPER(NETWORK_GROUP_NAME) = 'LOYALTY'
        )
      GROUP BY TIM_DAY
    ),

    -- Totales diarios para residual NO ATRIBUIDO (§82 fix — igual que versión mensual)
    oc_total_daily   AS (SELECT fecha_mes_corp, dia_del_mes, SUM(nr_corp) AS nr FROM oc_corp_daily_tc   WHERE corp_key IS NOT NULL GROUP BY 1,2),
    paid_total_daily AS (SELECT fecha_mes_corp, dia_del_mes, SUM(nr_corp) AS nr FROM paid_corp_daily_tc  WHERE corp_key IS NOT NULL GROUP BY 1,2),
    ucr_total_daily  AS (SELECT fecha_mes_corp, dia_del_mes, SUM(nr_corp) AS nr FROM ucr_prd_indiv_daily_tc GROUP BY 1,2),

    -- inapp_total_daily: Total N+R diario desde BT_MP_USER_ENGAGEMENT_INAPP (§78)
    inapp_total_daily AS (
      SELECT
        FORMAT_DATE('%Y%m', EVENT_DATE)          AS fecha_mes_corp,
        CAST(EXTRACT(DAY FROM EVENT_DATE) AS INT64) AS dia_del_mes,
        (COUNT(DISTINCT CASE WHEN DAYS_SINCE_FIRST_EVENT = 0  THEN CUS_CUST_ID END) +
         COUNT(DISTINCT CASE WHEN DAYS_SINCE_PRIOR_EVENT > 89 THEN CUS_CUST_ID END)) AS nr_total
      FROM `meli-bi-data.SBOX_MARKETING.BT_MP_USER_ENGAGEMENT_INAPP`
      WHERE SIT_SITE_ID = 'MLM'
        AND EVENT_DATE  >= DATE '2025-01-01'
        AND EVENT_DATE   <= DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
        AND (DAYS_SINCE_FIRST_EVENT = 0 OR DAYS_SINCE_PRIOR_EVENT > 89)
      GROUP BY fecha_mes_corp, dia_del_mes
    ),

    -- org_corp_daily_tc: NO ATRIBUIDO = INAPP − OC − PAID − UCR_PRD (§82 fix)
    org_corp_daily_tc AS (
      SELECT
        t.fecha_mes_corp,
        t.dia_del_mes,
        'NOATRIB|ORGANICO|TOTAL'  AS corp_key,
        GREATEST(
          t.nr_total
          - COALESCE(oc.nr,   0)
          - COALESCE(p.nr,    0)
          - COALESCE(u.nr,    0),
          0
        )                         AS nr_corp
      FROM inapp_total_daily t
      LEFT JOIN oc_total_daily    oc  ON t.fecha_mes_corp = oc.fecha_mes_corp   AND t.dia_del_mes = oc.dia_del_mes
      LEFT JOIN paid_total_daily  p   ON t.fecha_mes_corp = p.fecha_mes_corp    AND t.dia_del_mes = p.dia_del_mes
      LEFT JOIN ucr_total_daily   u   ON t.fecha_mes_corp = u.fecha_mes_corp    AND t.dia_del_mes = u.dia_del_mes
    )

    SELECT
      fecha_mes_corp,
      dia_del_mes,
      corp_key,
      SUM(nr_corp) AS nr_dia_corp
    FROM (
      SELECT fecha_mes_corp, dia_del_mes, corp_key, nr_corp FROM oc_corp_daily_tc            WHERE corp_key IS NOT NULL
      UNION ALL
      SELECT fecha_mes_corp, dia_del_mes, corp_key, nr_corp FROM paid_corp_daily_tc           WHERE corp_key IS NOT NULL
      UNION ALL
      SELECT fecha_mes_corp, dia_del_mes, corp_key, nr_corp FROM ucr_prd_indiv_daily_tc
      -- §82: others_catchall_corp_daily_tc eliminado del UNION ALL (mismo fix que versión mensual)
      UNION ALL
      SELECT fecha_mes_corp, dia_del_mes, corp_key, nr_corp FROM org_corp_daily_tc
    )
    GROUP BY fecha_mes_corp, dia_del_mes, corp_key
    ORDER BY fecha_mes_corp, dia_del_mes, corp_key
    """


def get_nr_corp_daily_sql():
    """DEPRECATED §71 — NO USADO. Reemplazado por get_nr_corp_daily_tc_sql().
    SQL para la sección corporativa de la pestaña NR Diario.
    Misma lógica de CASE WHEN que get_nr_corp_sql() pero con granularidad DIARIA.
    Añade columna DIA (número de día dentro del mes) para construir daily_nr_corp_by_node.

    Diferencias respecto a get_nr_corp_sql():
      · get_nr_corp_sql()        → agrupa por (CORP_KEY, FECHA_MES)      → usado en NR Mensual corp
      · get_nr_corp_daily_sql()  → agrupa por (CORP_KEY, FECHA_MES, DIA) → usado en NR Diario corp

    Retorna: (fecha_mes_corp, dia_del_mes, corp_key, nr_dia_corp)
    Consumido por: process_nr_corp_daily() en processors.py
    Almacenado en: daily_nr_corp_by_node { node_id: { yyyymm: { dia_str: nr_int } } }
    """
    return """
    WITH base_corp_diario AS (
      SELECT
        FORMAT_DATE('%Y%m', FECHA_DIARIA)             AS fecha_mes_corp,
        CAST(EXTRACT(DAY FROM FECHA_DIARIA) AS INT64) AS dia_del_mes,
        CHANNEL_APERTURA_1                            AS ap1_corp,
        CHANNEL_APERTURA_2                            AS ap2_corp,
        CHANNEL_APERTURA_3                            AS ap3_corp,
        TOUCHPOINT                                    AS touchpoint_corp,
        GREATEST(COALESCE(NR_USERS, 0), 0)                         AS nr_corp
      FROM `meli-bi-data.SBOX_MKTCORPMP.PANEL_MONTHLY_DAILY_HISTORICO`
      WHERE SIT_SITE_ID = 'MLM'
        AND FECHA_DIARIA >= DATE '2025-01-01'
        AND FECHA_DIARIA <= DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
    ),
    keyed_corp_diario AS (
      SELECT
        fecha_mes_corp,
        dia_del_mes,
        CASE
          -- ── OC: UCRANIA E&G → desglose por TOUCHPOINT (5 medios) ─────────────────
          WHEN ap1_corp = 'OC' AND ap2_corp = 'UCRANIA E&G'
               AND touchpoint_corp IN ('EMAIL', 'SMS')     THEN 'OC|UCR_EG|EMAIL'
          WHEN ap1_corp = 'OC' AND ap2_corp = 'UCRANIA E&G'
               AND touchpoint_corp = 'PANDORA'             THEN 'OC|UCR_EG|PANDORA'
          WHEN ap1_corp = 'OC' AND ap2_corp = 'UCRANIA E&G'
               AND touchpoint_corp = 'PUSH'                THEN 'OC|UCR_EG|PUSH'
          WHEN ap1_corp = 'OC' AND ap2_corp = 'UCRANIA E&G'
               AND touchpoint_corp LIKE 'RE - %'           THEN 'OC|UCR_EG|REAL_ESTATES'
          WHEN ap1_corp = 'OC' AND ap2_corp = 'UCRANIA E&G'
               AND touchpoint_corp = 'WPP'                 THEN 'OC|UCR_EG|WPP'
          WHEN ap1_corp = 'OC' AND ap2_corp = 'UCRANIA E&G'
                                                           THEN 'OC|UCR_EG|OTROS'
          -- ── OC: OWN CHANNELS RECURRING → desglose por TOUCHPOINT (5 medios) ──────
          WHEN ap1_corp = 'OC' AND ap2_corp = 'OWN CHANNELS RECURRING'
               AND touchpoint_corp = 'EMAIL'               THEN 'OC|OC_REC|EMAIL'
          WHEN ap1_corp = 'OC' AND ap2_corp = 'OWN CHANNELS RECURRING'
               AND touchpoint_corp = 'JOURNEY'             THEN 'OC|OC_REC|JOURNEY'
          WHEN ap1_corp = 'OC' AND ap2_corp = 'OWN CHANNELS RECURRING'
               AND touchpoint_corp = 'PANDORA'             THEN 'OC|OC_REC|PANDORA'
          WHEN ap1_corp = 'OC' AND ap2_corp = 'OWN CHANNELS RECURRING'
               AND touchpoint_corp = 'PUSH'                THEN 'OC|OC_REC|PUSH'
          WHEN ap1_corp = 'OC' AND ap2_corp = 'OWN CHANNELS RECURRING'
               AND touchpoint_corp = 'WPP'                 THEN 'OC|OC_REC|WPP'
          WHEN ap1_corp = 'OC' AND ap2_corp = 'OWN CHANNELS RECURRING'
                                                           THEN 'OC|OC_REC|OTROS'
          -- ── OC: OWN CHANNELS ADHOC → bucket total ───────────────────────────────
          WHEN ap1_corp = 'OC' AND ap2_corp = 'OWN CHANNELS ADHOC'  THEN 'OC|OC_ADHOC|TOTAL'
          -- ── POM sub-canales (AP1=POM) ────────────────────────────────────────────
          WHEN ap1_corp = 'POM' AND ap2_corp = 'ACQUISITION POM'     THEN 'POM|ACQ_POM|TOTAL'
          WHEN ap1_corp = 'POM' AND ap2_corp = 'ACTIVATION POM'      THEN 'POM|ACT_POM|TOTAL'
          WHEN ap1_corp = 'POM' AND ap2_corp = 'WEB POM'             THEN 'POM|WEB_POM|TOTAL'
          WHEN ap1_corp = 'POM' AND ap2_corp = 'CTW POM'             THEN 'POM|CTW_POM|TOTAL'
          -- ── OTHERS: MGM ─────────────────────────────────────────────────────────
          WHEN ap1_corp = 'OTHERS' AND ap2_corp = 'MGM'              THEN 'OTH|MGM|TOTAL'
          -- ── OTHERS: L&P → desagregado por AP3 (mismos 6 sub-canales que get_nr_corp_sql)
          WHEN ap1_corp = 'OTHERS' AND ap2_corp = 'LP'
               AND ap3_corp = 'AFFILIATES'                           THEN 'OTH|LP|AFFILIATES'
          WHEN ap1_corp = 'OTHERS' AND ap2_corp = 'LP'
               AND ap3_corp = 'BRANDFORMANCE'                        THEN 'OTH|LP|BRANDFORMANCE'
          WHEN ap1_corp = 'OTHERS' AND ap2_corp = 'LP'
               AND ap3_corp = 'LANDINGS'                             THEN 'OTH|LP|LANDINGS'
          WHEN ap1_corp = 'OTHERS' AND ap2_corp = 'LP'
               AND ap3_corp = 'PARTNERSHIPS'                         THEN 'OTH|LP|PARTNERSHIPS'
          WHEN ap1_corp = 'OTHERS' AND ap2_corp = 'LP'
               AND ap3_corp = 'GTM'                                  THEN 'OTH|LP|GTM'
          WHEN ap1_corp = 'OTHERS' AND ap2_corp = 'LP'               THEN 'OTH|LP|OTHERS'
          -- ── OTHERS: resto de sub-canales ─────────────────────────────────────────
          WHEN ap1_corp = 'OTHERS' AND ap2_corp = 'UCRANIA PRD'      THEN 'OTH|UCR_PRD|TOTAL'
          WHEN ap1_corp = 'OTHERS' AND ap2_corp = 'SEO'              THEN 'OTH|SEO|TOTAL'
          WHEN ap1_corp = 'OTHERS' AND ap2_corp = 'POM SELLERS'      THEN 'OTH|POM_SELLERS|TOTAL'
          WHEN ap1_corp = 'OTHERS' AND ap2_corp = 'POM OTHERS'       THEN 'OTH|POM_OTHERS|TOTAL'
          -- ── ELSE: AP1=ORGANICO → NO ATRIBUIDO ───────────────────────────────────
          ELSE 'NOATRIB|ORGANICO|TOTAL'
        END AS corp_key,
        nr_corp
      FROM base_corp_diario
    )
    SELECT
      fecha_mes_corp,
      dia_del_mes,
      corp_key,
      SUM(nr_corp) AS nr_dia_corp
    FROM keyed_corp_diario
    GROUP BY fecha_mes_corp, dia_del_mes, corp_key
    ORDER BY fecha_mes_corp, dia_del_mes, corp_key
    """


def get_perf_roa_costos_sql():
    """ROA numerator para UCR Gest y OC ACT desde PANEL_MONTHLY_COSTOS_CANALES.
    Filtra INVERSION_TOTAL_USD > 0 para aislar solo el valor de usuarios paid.
    VALUE_PRED en COSTOS_CANALES tiene datos reales para OWN CHANNELS MKT (0 para POM/MGM).
    """
    return """
    WITH base AS (
      SELECT
        MONTH_ID,
        CASE
          WHEN CHANNEL = 'OWN CHANNELS MKT' AND STRATEGY = 'UCRANIA'    THEN 'UCR Gest'
          WHEN CHANNEL = 'OWN CHANNELS MKT' AND STRATEGY = 'ACTIVATION' THEN 'OC ACT'
        END AS PERF_CANAL,
        COALESCE(VALUE_PRED, 0) AS VALUE_PRED
      FROM `meli-bi-data.SBOX_MKTCORPMP.PANEL_MONTHLY_COSTOS_CANALES`
      WHERE SIT_SITE_ID = 'MLM'
        AND MONTH_ID >= '202501'
        AND COALESCE(INVERSION_TOTAL_USD, 0) > 0
    )
    SELECT MONTH_ID, PERF_CANAL, SUM(VALUE_PRED) AS ROA_VALUE_PRED
    FROM base
    WHERE PERF_CANAL IS NOT NULL
    GROUP BY MONTH_ID, PERF_CANAL
    """


def get_nr_corp_sql():
    """DEPRECATED §71 — NO USADO. Reemplazado por get_nr_corp_tc_sql() (Torre de Control).
    SQL para la tabla corporativa de N+R (hierarchy_nr_corp_detail).
    Usa los tres niveles de canal del nuevo schema (abr-2026) de PANEL_MONTHLY_DAILY_HISTORICO:
      CHANNEL_APERTURA_1 (AP1) → grupo macro (OC, POM, OTHERS, ORGANICO)
      CHANNEL_APERTURA_2 (AP2) → sub-canal de negocio (UCRANIA E&G, ACQUISITION POM, MGM…)
      TOUCHPOINT          → medio de comunicación (EMAIL, PUSH, PANDORA, RE-*, WPP…)

    Retorna una fila por (CORP_KEY, FECHA_MES) con NR total.
    CORP_KEY es la clave plana que se mapea a hierarchy_nr_corp_detail[].bq_key en Python.

    Reglas de mapeo (ver también History.md §25 y channels_config.json hierarchy_nr_corp_detail):
      OC UCR E&G     → desglose por TOUCHPOINT (5 medios + catch-all OTROS)
      OC RECURRING   → desglose por TOUCHPOINT (5 medios + catch-all OTROS)
      OC ADHOC       → un único bucket TOTAL (sin desglose de medios)
      POM sub-canales→ AP2 directo, sin desglose de medios
      OTHERS         → AP2 directo, sin desglose de medios
      ELSE           → NOATRIB|ORGANICO|TOTAL (captura AP1=ORGANICO y cualquier no mapeado)
    """
    return """
    WITH base_corp AS (
      SELECT
        FORMAT_DATE('%Y%m', FECHA_DIARIA) AS FECHA_MES_CORP,
        CHANNEL_APERTURA_1                AS ap1_corp,
        CHANNEL_APERTURA_2                AS ap2_corp,
        CHANNEL_APERTURA_3                AS ap3_corp,   -- usado para desagregar L&P por sub-canal
        TOUCHPOINT                        AS touchpoint_corp,
        GREATEST(COALESCE(NR_USERS, 0), 0)             AS nr_corp
      FROM `meli-bi-data.SBOX_MKTCORPMP.PANEL_MONTHLY_DAILY_HISTORICO`
      WHERE SIT_SITE_ID = 'MLM'
        AND FECHA_DIARIA >= DATE '2025-01-01'
        AND FECHA_DIARIA <= DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
    ),
    keyed_corp AS (
      SELECT
        FECHA_MES_CORP,
        CASE
          -- ── OC: UCRANIA E&G → desglose por TOUCHPOINT (5 medios) ──────────────────
          WHEN ap1_corp = 'OC' AND ap2_corp = 'UCRANIA E&G'
               AND touchpoint_corp IN ('EMAIL', 'SMS')      THEN 'OC|UCR_EG|EMAIL'
          WHEN ap1_corp = 'OC' AND ap2_corp = 'UCRANIA E&G'
               AND touchpoint_corp = 'PANDORA'              THEN 'OC|UCR_EG|PANDORA'
          WHEN ap1_corp = 'OC' AND ap2_corp = 'UCRANIA E&G'
               AND touchpoint_corp = 'PUSH'                 THEN 'OC|UCR_EG|PUSH'
          WHEN ap1_corp = 'OC' AND ap2_corp = 'UCRANIA E&G'
               AND touchpoint_corp LIKE 'RE - %'            THEN 'OC|UCR_EG|REAL_ESTATES'
          WHEN ap1_corp = 'OC' AND ap2_corp = 'UCRANIA E&G'
               AND touchpoint_corp = 'WPP'                  THEN 'OC|UCR_EG|WPP'
          WHEN ap1_corp = 'OC' AND ap2_corp = 'UCRANIA E&G'
                                                            THEN 'OC|UCR_EG|OTROS'
          -- ── OC: OWN CHANNELS RECURRING → desglose por TOUCHPOINT (5 medios) ───────
          WHEN ap1_corp = 'OC' AND ap2_corp = 'OWN CHANNELS RECURRING'
               AND touchpoint_corp = 'EMAIL'                THEN 'OC|OC_REC|EMAIL'
          WHEN ap1_corp = 'OC' AND ap2_corp = 'OWN CHANNELS RECURRING'
               AND touchpoint_corp = 'JOURNEY'              THEN 'OC|OC_REC|JOURNEY'
          WHEN ap1_corp = 'OC' AND ap2_corp = 'OWN CHANNELS RECURRING'
               AND touchpoint_corp = 'PANDORA'              THEN 'OC|OC_REC|PANDORA'
          WHEN ap1_corp = 'OC' AND ap2_corp = 'OWN CHANNELS RECURRING'
               AND touchpoint_corp = 'PUSH'                 THEN 'OC|OC_REC|PUSH'
          WHEN ap1_corp = 'OC' AND ap2_corp = 'OWN CHANNELS RECURRING'
               AND touchpoint_corp = 'WPP'                  THEN 'OC|OC_REC|WPP'
          WHEN ap1_corp = 'OC' AND ap2_corp = 'OWN CHANNELS RECURRING'
                                                            THEN 'OC|OC_REC|OTROS'
          -- ── OC: OWN CHANNELS ADHOC → bucket total sin desglose ───────────────────
          WHEN ap1_corp = 'OC' AND ap2_corp = 'OWN CHANNELS ADHOC'   THEN 'OC|OC_ADHOC|TOTAL'
          -- ── POM sub-canales (AP1=POM) → AP2 directo ─────────────────────────────
          WHEN ap1_corp = 'POM' AND ap2_corp = 'ACQUISITION POM'      THEN 'POM|ACQ_POM|TOTAL'
          WHEN ap1_corp = 'POM' AND ap2_corp = 'ACTIVATION POM'       THEN 'POM|ACT_POM|TOTAL'
          WHEN ap1_corp = 'POM' AND ap2_corp = 'WEB POM'              THEN 'POM|WEB_POM|TOTAL'
          WHEN ap1_corp = 'POM' AND ap2_corp = 'CTW POM'              THEN 'POM|CTW_POM|TOTAL'
          -- ── OTHERS sub-canales (AP1=OTHERS) ─────────────────────────────────────
          WHEN ap1_corp = 'OTHERS' AND ap2_corp = 'MGM'               THEN 'OTH|MGM|TOTAL'
          -- ── L&P → desagregado por CHANNEL_APERTURA_3 (6 sub-canales) ────────────
          WHEN ap1_corp = 'OTHERS' AND ap2_corp = 'LP'
               AND ap3_corp = 'AFFILIATES'                            THEN 'OTH|LP|AFFILIATES'
          WHEN ap1_corp = 'OTHERS' AND ap2_corp = 'LP'
               AND ap3_corp = 'BRANDFORMANCE'                         THEN 'OTH|LP|BRANDFORMANCE'
          WHEN ap1_corp = 'OTHERS' AND ap2_corp = 'LP'
               AND ap3_corp = 'LANDINGS'                              THEN 'OTH|LP|LANDINGS'
          WHEN ap1_corp = 'OTHERS' AND ap2_corp = 'LP'
               AND ap3_corp = 'PARTNERSHIPS'                          THEN 'OTH|LP|PARTNERSHIPS'
          WHEN ap1_corp = 'OTHERS' AND ap2_corp = 'LP'
               AND ap3_corp = 'GTM'                                   THEN 'OTH|LP|GTM'
          WHEN ap1_corp = 'OTHERS' AND ap2_corp = 'LP'                THEN 'OTH|LP|OTHERS'
          WHEN ap1_corp = 'OTHERS' AND ap2_corp = 'UCRANIA PRD'       THEN 'OTH|UCR_PRD|TOTAL'
          WHEN ap1_corp = 'OTHERS' AND ap2_corp = 'SEO'               THEN 'OTH|SEO|TOTAL'
          WHEN ap1_corp = 'OTHERS' AND ap2_corp = 'POM SELLERS'       THEN 'OTH|POM_SELLERS|TOTAL'
          WHEN ap1_corp = 'OTHERS' AND ap2_corp = 'POM OTHERS'        THEN 'OTH|POM_OTHERS|TOTAL'
          -- ── ELSE: AP1=ORGANICO + cualquier combinación no mapeada → NO ATRIBUIDO ─
          ELSE 'NOATRIB|ORGANICO|TOTAL'
        END AS corp_key,
        nr_corp
      FROM base_corp
    )
    SELECT
      FECHA_MES_CORP AS fecha_mes_corp,
      corp_key,
      SUM(nr_corp) AS nr_total_corp
    FROM keyed_corp
    GROUP BY fecha_mes_corp, corp_key
    ORDER BY fecha_mes_corp, corp_key
    """


def get_new_rec_monthly_sql():
    """Monthly New vs Recovered N+R desde BT_MP_INDIVIDUALS_PERFORMANCE.
    Misma tabla que el resto del dashboard. SOURCE_CD='TOOL_COST' = ventana estándar.
    CHANNEL_GROUP != 'OC' evita duplicar OC (ya contado en Torre Daily).
    Retorna: MONTH_ID, new_nr, rec_nr por mes.
    """
    return """
    SELECT
      FORMAT_DATE('%Y%m', TIM_DAY)   AS MONTH_ID,
      SUM(NEW_USERS_INAPP)           AS new_nr,
      SUM(RECOVERED_USERS_INAPP)     AS rec_nr
    FROM `meli-bi-data.SBOX_MARKETING.BT_MP_INDIVIDUALS_PERFORMANCE`
    WHERE SIT_SITE_ID = 'MLM'
      AND TIM_DAY >= DATE '2025-01-01'
      AND TIM_DAY <  DATE_TRUNC(CURRENT_DATE(), DAY)
      AND SOURCE_CD = 'TOOL_COST'
      AND UPPER(CHANNEL_GROUP) != 'OC'
    GROUP BY 1
    ORDER BY 1
    """


def get_installs_monthly_sql(HIERARCHY_NR):
    """SQL installs mensuales por canal — SSOT: BASE_INSTALLS_LIFECYCLE (§88).

    Fuente certificada: meli-bi-data.SBOX_MKTCORPMP.BASE_INSTALLS_LIFECYCLE
    Verificado contra Corp screenshot: diferencia < 1% en todos los canales.

    Total installs = qty_custs_potential_new + qty_custs_potential_recovered
                   + qty_custs_repeated   (todos los usuarios que instalaron)

    Mapping channel → label del dashboard (FM):
      POM                → 'POM ADQ'    (toda la familia POM sin split ADQ/ACT)
      Own Channels MKT   → 'UCR Gest'  (UCR E&G campaigns)
      Own Channels PRD   → 'UCR PRD'   (product OC)
      Own Channels OTHERS→ 'OC ACT'    (OC misceláneos / ad-hoc)
      MGM                → 'MGM ADQ'
      Partnerships       → 'L&P ADQ'   (Landings & Partnerships)
      BRANDFORMANCE      → 'L&P ADQ'   (Brandformance ⊂ L&P)
      OTHERS             → 'L&P ADQ'   (OTHERS ⊂ L&P)
      ORGANICO           → 'ORG'

    HIERARCHY_NR: recibido por consistencia de firma; no se usa en el SQL —
    la tabla ya tiene la clasificación de canales correcta.
    Retorna: MONTH_ID (YYYYMM str), INST_CANAL (label), INSTALLS (float)
    """
    return """
    -- ═══════════════════════════════════════════════════════════════════════════
    -- get_installs_monthly_sql() — SSOT BASE_INSTALLS_LIFECYCLE §88
    -- Verificado vs Corp screenshot: diferencia < 1% en todos los canales.
    -- Total = new + recovered + repeated (todos los usuarios que instalaron)
    -- ═══════════════════════════════════════════════════════════════════════════
    SELECT
      fecha_mes                                                            AS MONTH_ID,
      CASE channel
        WHEN 'POM'                 THEN 'POM ADQ'
        WHEN 'Own Channels MKT'    THEN 'UCR Gest'
        WHEN 'Own Channels PRD'    THEN 'UCR PRD'
        WHEN 'Own Channels OTHERS' THEN 'OC ACT'
        WHEN 'MGM'                 THEN 'MGM ADQ'
        WHEN 'Partnerships'        THEN 'L&P ADQ'
        WHEN 'BRANDFORMANCE'       THEN 'L&P ADQ'
        WHEN 'OTHERS'              THEN 'L&P ADQ'
        WHEN 'ORGANICO'            THEN 'ORG'
      END                                                                  AS INST_CANAL,
      SUM(qty_custs_potential_new
        + qty_custs_potential_recovered
        + qty_custs_repeated)                                              AS INSTALLS
    FROM `meli-bi-data.SBOX_MKTCORPMP.BASE_INSTALLS_LIFECYCLE`
    WHERE sit_site_id = 'MLM'
      AND fecha_mes  >= '202501'
    GROUP BY 1, 2
    HAVING INST_CANAL IS NOT NULL
    ORDER BY 1, 2
    """


def get_installs_corp_monthly_sql():
    """SQL installs Corp por corp_key — SSOT: BASE_INSTALLS_LIFECYCLE (§88).

    Misma fuente que get_installs_monthly_sql() mapeada a corp_key del hierarchy.

    Canales sin breakdown de medio (corp_ucr_eg, corp_pom) usan el node_id
    directamente como corp_key — el processor detecta si el corp_key es un
    node_id válido y evita sobreescribirlo en la propagación bottom-up.

    Retorna: fecha_mes_corp (YYYYMM str), corp_key (str), installs_corp (float)
    """
    return """
    -- ═══════════════════════════════════════════════════════════════════════════
    -- get_installs_corp_monthly_sql() — Installs Corp SSOT BASE_INSTALLS §88
    -- Para UCR y POM se usa node_id directamente (sin breakdown de medio).
    -- ═══════════════════════════════════════════════════════════════════════════
    SELECT
      fecha_mes                                                            AS fecha_mes_corp,
      CASE channel
        -- UCR: Own Channels MKT → node_id corp_ucr_eg (padre de todos los medios)
        -- BASE_INSTALLS_LIFECYCLE no tiene breakdown por medio, se agrega al padre.
        WHEN 'Own Channels MKT'    THEN 'corp_ucr_eg'
        WHEN 'Own Channels PRD'    THEN 'OTH|UCR_PRD|TOTAL'
        WHEN 'Own Channels OTHERS' THEN 'OC|OC_ADHOC|TOTAL'
        -- POM: sin breakdown ADQ/ACT → node_id corp_pom (padre)
        WHEN 'POM'                 THEN 'corp_pom'
        WHEN 'MGM'                 THEN 'OTH|MGM|TOTAL'
        WHEN 'Partnerships'        THEN 'OTH|LP|PARTNERSHIPS'
        WHEN 'BRANDFORMANCE'       THEN 'OTH|LP|BRANDFORMANCE'
        WHEN 'OTHERS'              THEN 'OTH|LP|OTHERS'
        WHEN 'ORGANICO'            THEN 'NOATRIB|ORGANICO|TOTAL'
      END                                                                  AS corp_key,
      SUM(qty_custs_potential_new
        + qty_custs_potential_recovered
        + qty_custs_repeated)                                              AS installs_corp
    FROM `meli-bi-data.SBOX_MKTCORPMP.BASE_INSTALLS_LIFECYCLE`
    WHERE sit_site_id = 'MLM'
      AND fecha_mes  >= '202501'
    GROUP BY 1, 2
    HAVING corp_key IS NOT NULL
    ORDER BY 1, 2
    """


def get_comms_oc_fresh_sql():
    """SQL comunicaciones OC para el mes actual (Tier 2 fresh).

    §75 History.md — Migración completa desde arquitectura 4 ramas
    (BT_OC_CUST_EVENT + DASHBOARD_CAMPAIGNS_INDIVIDUOS_METRICAS + BT_OC_DASHBOARD_ALL_CAMPAIGNS
    + BT_OC_EMAIL_MP_MONTHLY + BT_OC_MP_FLOWS_DAILY + DIM_REE_METRICS_PRINTS) a
    arquitectura 2 ramas unificadas desde tablas Torre de Control certificadas.

    Ramas:
      · RAMA A: SBOX_EG_MKT.BT_OC_DASHBOARD_ALL_CAMPAIGNS_NR
          OC ACT (ACTIVATION/ACQUISITION) + UCR ADHOC + JOURNEYS + RE (OC) + PANDORA + WPP
          USER_INC: NR_INC_USERS (ACTIVATION) o NEW_7D_ADJUST+REC_7D_ADJUST (UCRANIA/ACQ)
          Extras: TOTAL_ABSOLUTO_NR, RATIO_CANIBALIZACION, CLASIF_CAMPAIGNS, costos

      · RAMA B: SBOX_EG_MKT.BT_OC_DASHBOARD_ALL_CAMPAIGNS_NR_ACQUISITION
          UCR Gest recurring + RE (UCR Gest)
          USER_INC: Q_NR_7D (Adjust 7D incremental)
          VALUE_INC: VALUE_PREDICTED (real atribuido)
          Sin TOTAL_ABSOLUTO_NR (solo incremental disponible)

    Schema de salida (33 cols):
      SENT_DATE, MONTH_ID, COMMUNICATION_ID, CAMPAIGN_NAME, CAMPAIGN_NAME_CLEAN,
      CANAL, CHANNEL, TEAM, STRATEGY, SUBSTRATEGY, EXPERIMENT,
      NOTIFICATION_TYPE, BUSINESS_LINE_SEGMENT, BUSINESS_LINE, STATUS,
      SENTS, TOTAL_TEST, TOTAL_CONTROL, TOTAL_ARRIVED, TOTAL_OPEN, TOTAL_CLICK,
      OPEN_RATE, USER_INC, VALUE_INC, TOTAL_ABSOLUTO_NR, RATIO_CANIBALIZACION,
      CLASIF_CAMPAIGNS, FLAG_PAID, FLAG_INCENTIVO,
      CONSUMIDO_USD, COSTO_ENVIO_USD, COSTO_MANTIKA_USD, FUENTE_TABLA

    Eliminados vs legacy: M_CVR_TEST, M_LIFT, TPN_INC, TPV_INC,
      NOTIFICATION_TITLE, NOTIFICATION_TEXT, APP (reemplazado por CHANNEL),
      TYPE_NAME (reemplazado por CLASIF_CAMPAIGNS), TOTAL_CREATE, TOTAL_SHOWN,
      TOTAL_BLACKLIST/BLOCKED/BOUNCE/SPAMREPORT, TOTAL_PRINTS_RE/UNIQUE_PRINTS_RE/
      TOTAL_TAPS_RE/UNIQUE_TAPS_RE (RE ahora usa VOLUMEN_SENT/OPEN directamente)

    Dedup: QUALIFY ROW_NUMBER() OVER (PARTITION BY COMMUNICATION_ID, SENT_DATE, CANAL) = 1
    Filtro fecha: MONTH_ID >= DATE_TRUNC(CURRENT_DATE(), MONTH)
    """
    # Exclusiones de calidad — compartidas por ambas ramas
    _EXCL = """
      AND COMUNICATION_NAME NOT LIKE '%SELLER%'
      AND COMUNICATION_NAME NOT LIKE '%%-XT1-%%'
      AND COMUNICATION_NAME NOT LIKE '%%SEV-T3-%%'
      AND COMUNICATION_NAME NOT LIKE '%%-ENG%%'
      AND COMUNICATION_NAME NOT LIKE '%%-ENG'
      AND COMUNICATION_NAME NOT LIKE '%%T1%%'
      AND COMUNICATION_NAME NOT LIKE '%%XSELL%%'
      AND COMUNICATION_NAME NOT LIKE '%%SVS_CUPON%%'
      AND COMUNICATION_NAME NOT LIKE '%%SVS%%'
    """

    return """
    -- ════════════════════════════════════════════════════════════════════
    -- get_comms_oc_fresh_sql() — Comms OC mes actual (Tier 2) | §75
    -- 2 ramas: ALL_CAMPAIGNS_NR (Rama A) + NR_ACQUISITION (Rama B)
    -- Granularidad: (COMMUNICATION_ID, SENT_DATE, CANAL)
    -- ════════════════════════════════════════════════════════════════════

    -- ── RAMAS A y B como CTEs — el colapso final unifica duplicados cross-tabla ──
    WITH rama_a AS (
    -- ── RAMA A: BT_OC_DASHBOARD_ALL_CAMPAIGNS_NR ────────────────────────
    -- OC ACT (ACTIVATION/ACQUISITION) + UCR ADHOC + JOURNEYS + RE (OC) + PANDORA + WPP
    -- USER_INC: dual — UCRANIA/ACQUISITION usa NEW_7D_ADJUST+REC_7D_ADJUST (Adjust 7D);
    --           ACTIVATION usa NR_INC_USERS (calibrado por Blacklist).
    SELECT
      CAST(SENT_DATE AS STRING)                                         AS SENT_DATE,
      FORMAT_DATE('%Y%m', MONTH_ID)                                     AS MONTH_ID,
      CAST(COMMUNICATION_ID AS STRING)                                  AS COMMUNICATION_ID,
      COMUNICATION_NAME                                                  AS CAMPAIGN_NAME,
      NULLIF(
        CASE WHEN ENDS_WITH(TRIM(COMUNICATION_NAME), '_DEFAULT')
             THEN SUBSTR(TRIM(COMUNICATION_NAME), 1, LENGTH(TRIM(COMUNICATION_NAME)) - 8)
             ELSE TRIM(COMUNICATION_NAME) END, '')                      AS CAMPAIGN_NAME_CLEAN,
      CANAL,
      CHANNEL,
      TEAM,
      STRATEGY,
      SUBSTRATEGY,
      EXPERIMENT,
      NOTIFICATION_TYPE,
      BUSINESS_LINE_SEGMENT_CHANNELS                                     AS BUSINESS_LINE_SEGMENT,
      BUSINESS_LINE,
      STATUS,
      COALESCE(VOLUMEN_SENT,           0.0) AS SENTS,
      COALESCE(VOLUMEN_ENTRY_TEST,     0)   AS TOTAL_TEST,
      COALESCE(VOLUMEN_CONTROL,        0)   AS TOTAL_CONTROL,
      COALESCE(VOLUMEN_SHOWN,          0)   AS TOTAL_ARRIVED,
      COALESCE(VOLUMEN_OPEN,           0)   AS TOTAL_OPEN,
      COALESCE(VOLUMEN_CLICK,          0)   AS TOTAL_CLICK,
      -- Columnas específicas JOURNEY: entradas al journey por grupo test y control
      COALESCE(VOLUMEN_ENTRY_TEST,     0)   AS ENTRY_TEST_JNY,
      COALESCE(VOLUMEN_ENTRY_CONTROL,  0)   AS ENTRY_CONTROL_JNY,
      -- OR: usa ARRIVED si disponible; si ARRIVED=0 usa SENTS como fallback (RE-Drawer no tiene ARRIVED)
      SAFE_DIVIDE(COALESCE(VOLUMEN_OPEN, 0),
        NULLIF(COALESCE(NULLIF(COALESCE(VOLUMEN_SHOWN,0),0), COALESCE(VOLUMEN_SENT,0)), 0)
      )                                                                  AS OPEN_RATE,
      -- USER_INC: lift puro (NR_INC_USERS) — alineado con Torre de Control.
      COALESCE(NR_INC_USERS, 0)                                          AS USER_INC,
      -- USER_INC_CON_ADJUST: fórmula oficial del equipo.
      -- CLASIF='UCRANIA' → Adjust 7D (calibrado por Blacklist). Resto → lift.
      CASE
        WHEN CLASIF_CAMPAIGNS = 'UCRANIA'
        THEN COALESCE(NEW_7D_ADJUST, 0) + COALESCE(REC_7D_ADJUST, 0)
        ELSE COALESCE(NR_INC_USERS, 0)
      END                                                                AS USER_INC_CON_ADJUST,
      COALESCE(NR_INC_VALUE, 0.0)                                       AS VALUE_INC,
      -- TOTAL_ABSOLUTO_NR (= NR_TOTAL_Test): conversiones brutas del grupo Test
      COALESCE(NEW_COUNT_USERS_TEST_CONV, 0)
        + COALESCE(REC_COUNT_USERS_TEST_CONV, 0)                        AS TOTAL_ABSOLUTO_NR,
      -- NR_TOTAL_CONTROL: conversiones brutas del grupo Control (benchmark orgánico)
      COALESCE(NEW_COUNT_USERS_CONTROL_CONV, 0)
        + COALESCE(REC_COUNT_USERS_CONTROL_CONV, 0)                     AS NR_TOTAL_CONTROL,
      -- RATIO_CANIBALIZACION: (ABSOLUTO - INCREMENTAL) / ABSOLUTO
      -- Cuantifica qué fracción del éxito bruto es conversión orgánica, no incremental.
      CASE
        WHEN (COALESCE(NEW_COUNT_USERS_TEST_CONV, 0)
              + COALESCE(REC_COUNT_USERS_TEST_CONV, 0)) = 0
          THEN CAST(NULL AS FLOAT64)
        ELSE ROUND(SAFE_DIVIDE(
          (COALESCE(NEW_COUNT_USERS_TEST_CONV, 0) + COALESCE(REC_COUNT_USERS_TEST_CONV, 0))
          - CASE
              WHEN CLASIF_CAMPAIGNS = 'UCRANIA'
              THEN COALESCE(NEW_7D_ADJUST, 0) + COALESCE(REC_7D_ADJUST, 0)
              ELSE COALESCE(NR_INC_USERS, 0)
            END,
          (COALESCE(NEW_COUNT_USERS_TEST_CONV, 0) + COALESCE(REC_COUNT_USERS_TEST_CONV, 0))
        ), 4)
      END                                                                AS RATIO_CANIBALIZACION,
      CLASIF_CAMPAIGNS,
      FLAG_PAID,
      CAST(FLAG_INCENTIVO AS INT64)                                     AS FLAG_INCENTIVO,
      COALESCE(CONSUMIDO_USD,     0.0)                                  AS CONSUMIDO_USD,
      COALESCE(COSTO_ENVIO_USD,   0.0)                                  AS COSTO_ENVIO_USD,
      COALESCE(COSTO_MANTIKA_USD, 0.0)                                  AS COSTO_MANTIKA_USD,
      'ALL_CAMPAIGNS_NR'                                                 AS FUENTE_TABLA
    FROM `SBOX_EG_MKT.BT_OC_DASHBOARD_ALL_CAMPAIGNS_NR`
    WHERE SITE = 'MLM'
      AND MONTH_ID >= DATE_TRUNC(CURRENT_DATE(), MONTH)
      AND (
        -- Canales regulares: filtro por strategy
        STRATEGY IN ('UCRANIA', 'ACTIVATION', 'ACQUISITION', 'RE-ACTIVATION', 'ENGAGEMENT')
        -- Journey: capturar todas sin restricción de strategy (incluye OTHERS/RETENTION/etc.)
        OR UPPER(CANAL) = 'JOURNEY'
      )
      AND (
        -- Journey bypass: sin filtro de team
        UPPER(CANAL) = 'JOURNEY'
        OR TEAM NOT IN ('SELLERS', 'ADHOC - SELLERS')
        OR ABS(COALESCE(NULLIF(COALESCE(NEW_7D_ADJUST,0)+COALESCE(REC_7D_ADJUST,0), 0), COALESCE(NR_INC_USERS,0))) > 250
      )
      AND (
        -- Journey bypass: sin filtros de nombre
        UPPER(CANAL) = 'JOURNEY'
        OR (
          COMUNICATION_NAME NOT LIKE '%SELLER%'
          AND COMUNICATION_NAME NOT LIKE '%-XT1-%'
          AND COMUNICATION_NAME NOT LIKE '%SEV-T3-%'
          AND COMUNICATION_NAME NOT LIKE '%-ENG%'
          AND COMUNICATION_NAME NOT LIKE '%-ENG'
          AND COMUNICATION_NAME NOT LIKE '%T1%'
          AND COMUNICATION_NAME NOT LIKE '%XSELL%'
          AND COMUNICATION_NAME NOT LIKE '%SVS_CUPON%'
          AND COMUNICATION_NAME NOT LIKE '%SVS%'
        )
      )
    QUALIFY ROW_NUMBER() OVER (
      PARTITION BY COMMUNICATION_ID, SENT_DATE, CANAL
      ORDER BY SENT_DATE DESC
    ) = 1
    ),  -- fin rama_a

    rama_b AS (
    -- ── RAMA B: BT_OC_DASHBOARD_ALL_CAMPAIGNS_NR_ACQUISITION ────────────
    -- UCR Gest recurring + RE para UCR Gest
    -- USER_INC: Q_NR_7D (N+R incremental Adjust 7D — único disponible en _ACQUISITION)
    -- VALUE_INC: VALUE_PREDICTED (valor N+R real atribuido por Adjust 7D en USD)
    -- TOTAL_ABSOLUTO_NR: NULL (tabla solo tiene métricas incrementales)
    -- COSTO_MANTIKA_USD: NULL (no aplica a campañas UCR Gest recurring)
    SELECT
      CAST(SENT_DATE AS STRING)                                         AS SENT_DATE,
      FORMAT_DATE('%Y%m', MONTH_ID)                                     AS MONTH_ID,
      CAST(COMMUNICATION_ID AS STRING)                                  AS COMMUNICATION_ID,
      COMUNICATION_NAME                                                  AS CAMPAIGN_NAME,
      NULLIF(
        CASE WHEN ENDS_WITH(TRIM(COMUNICATION_NAME), '_DEFAULT')
             THEN SUBSTR(TRIM(COMUNICATION_NAME), 1, LENGTH(TRIM(COMUNICATION_NAME)) - 8)
             ELSE TRIM(COMUNICATION_NAME) END, '')                      AS CAMPAIGN_NAME_CLEAN,
      CANAL,
      CAST(NULL AS STRING)                                              AS CHANNEL,
      TEAM,
      STRATEGY,
      SUBSTRATEGY,
      CAST(NULL AS STRING)                                              AS EXPERIMENT,
      CAST(NULL AS STRING)                                              AS NOTIFICATION_TYPE,
      CAST(NULL AS STRING)                                              AS BUSINESS_LINE_SEGMENT,
      BUSINESS_LINE,
      CAST(NULL AS STRING)                                              AS STATUS,
      COALESCE(VOLUMEN_SENT,          0.0) AS SENTS,
      COALESCE(VOLUMEN_ENTRY_TEST,    0)   AS TOTAL_TEST,
      COALESCE(VOLUMEN_CONTROL,       0)   AS TOTAL_CONTROL,
      COALESCE(VOLUMEN_SHOWN,         0)   AS TOTAL_ARRIVED,
      COALESCE(VOLUMEN_OPEN,          0)   AS TOTAL_OPEN,
      CAST(0 AS INT64)                     AS TOTAL_CLICK,
      COALESCE(VOLUMEN_ENTRY_TEST,    0)   AS ENTRY_TEST_JNY,
      COALESCE(VOLUMEN_ENTRY_CONTROL, 0)   AS ENTRY_CONTROL_JNY,
      -- OR: usa ARRIVED si disponible; si ARRIVED=0 usa SENTS como fallback (RE-Drawer no tiene ARRIVED)
      SAFE_DIVIDE(COALESCE(VOLUMEN_OPEN, 0),
        NULLIF(COALESCE(NULLIF(COALESCE(VOLUMEN_SHOWN,0),0), COALESCE(VOLUMEN_SENT,0)), 0)
      )                                                                  AS OPEN_RATE,
      COALESCE(Q_NR_7D, 0.0)                                           AS USER_INC,
      COALESCE(Q_NR_7D, 0.0)                                           AS USER_INC_CON_ADJUST,
      COALESCE(VALUE_PREDICTED, 0.0)                                    AS VALUE_INC,
      CAST(NULL AS FLOAT64)                                             AS TOTAL_ABSOLUTO_NR,
      CAST(NULL AS FLOAT64)                                             AS NR_TOTAL_CONTROL,
      CAST(NULL AS FLOAT64)                                             AS RATIO_CANIBALIZACION,
      CLASIFICATION                                                      AS CLASIF_CAMPAIGNS,
      FLAG_PAID,
      CAST(FLAG_INCENTIVO AS INT64)                                     AS FLAG_INCENTIVO,
      COALESCE(CONSUMIDO_USD,   0.0)                                    AS CONSUMIDO_USD,
      COALESCE(COSTO_ENVIO_USD, 0.0)                                    AS COSTO_ENVIO_USD,
      CAST(NULL AS FLOAT64)                                             AS COSTO_MANTIKA_USD,
      'NR_ACQUISITION'                                                   AS FUENTE_TABLA
    FROM `SBOX_EG_MKT.BT_OC_DASHBOARD_ALL_CAMPAIGNS_NR_ACQUISITION`
    WHERE SITE = 'MLM'
      AND MONTH_ID >= DATE_TRUNC(CURRENT_DATE(), MONTH)
      AND (
        TEAM NOT IN ('SELLERS', 'ADHOC - SELLERS')
        OR ABS(COALESCE(Q_NR_7D, 0)) > 250
      )
      AND COMUNICATION_NAME NOT LIKE '%SELLER%'
      AND COMUNICATION_NAME NOT LIKE '%-XT1-%'
      AND COMUNICATION_NAME NOT LIKE '%SEV-T3-%'
      AND COMUNICATION_NAME NOT LIKE '%-ENG%'
      AND COMUNICATION_NAME NOT LIKE '%-ENG'
      AND COMUNICATION_NAME NOT LIKE '%T1%'
      AND COMUNICATION_NAME NOT LIKE '%XSELL%'
      AND COMUNICATION_NAME NOT LIKE '%SVS_CUPON%'
      AND COMUNICATION_NAME NOT LIKE '%SVS%'
      AND COMUNICATION_NAME NOT LIKE '%CHURN%'
    QUALIFY ROW_NUMBER() OVER (
      PARTITION BY COMMUNICATION_ID, SENT_DATE, CANAL
      ORDER BY SENT_DATE DESC
    ) = 1
    ),  -- fin rama_b

    combined AS (
      SELECT * FROM rama_a
      UNION ALL
      SELECT * FROM rama_b
    )

    -- ── COLAPSO CROSS-TABLA ──────────────────────────────────────────────────
    -- Objetivo: (COMMUNICATION_ID, SENT_DATE, CANAL) es la clave de unicidad.
    -- Si la misma comunicación aparece en AMBAS tablas en el mismo día y canal,
    -- se colapsa en UNA sola fila con FUENTE_TABLA = 'AMBAS'.
    -- Prioridad de métricas: Rama A (ALL_CAMPAIGNS_NR) sobre Rama B (NR_ACQUISITION).
    -- Los campos NULL en Rama B (CHANNEL, NOTIFICATION_TYPE, TOTAL_ABSOLUTO_NR,
    -- RATIO_CANIBALIZACION, COSTO_MANTIKA_USD, TOTAL_CLICK, STATUS,
    -- BUSINESS_LINE_SEGMENT) se toman directamente de Rama A via MAX().
    SELECT
      SENT_DATE,
      MONTH_ID,
      COMMUNICATION_ID,
      ANY_VALUE(CAMPAIGN_NAME)                                                     AS CAMPAIGN_NAME,
      ANY_VALUE(CAMPAIGN_NAME_CLEAN)                                               AS CAMPAIGN_NAME_CLEAN,
      CANAL,
      -- Campos NULL en Rama B → MAX toma automáticamente el valor de Rama A
      MAX(CHANNEL)                                                                 AS CHANNEL,
      -- Campos presentes en ambas: prioridad Rama A
      COALESCE(MAX(IF(FUENTE_TABLA='ALL_CAMPAIGNS_NR', TEAM,      NULL)), MAX(TEAM))      AS TEAM,
      COALESCE(MAX(IF(FUENTE_TABLA='ALL_CAMPAIGNS_NR', STRATEGY,  NULL)), MAX(STRATEGY))  AS STRATEGY,
      COALESCE(MAX(IF(FUENTE_TABLA='ALL_CAMPAIGNS_NR', SUBSTRATEGY,NULL)), MAX(SUBSTRATEGY)) AS SUBSTRATEGY,
      COALESCE(MAX(IF(FUENTE_TABLA='ALL_CAMPAIGNS_NR', EXPERIMENT, NULL)), MAX(EXPERIMENT)) AS EXPERIMENT,
      MAX(NOTIFICATION_TYPE)                                                       AS NOTIFICATION_TYPE,
      MAX(BUSINESS_LINE_SEGMENT)                                                   AS BUSINESS_LINE_SEGMENT,
      COALESCE(MAX(IF(FUENTE_TABLA='ALL_CAMPAIGNS_NR', BUSINESS_LINE,NULL)), MAX(BUSINESS_LINE)) AS BUSINESS_LINE,
      MAX(STATUS)                                                                  AS STATUS,
      -- Funnel: priorizar Rama A (metodología más completa)
      COALESCE(MAX(IF(FUENTE_TABLA='ALL_CAMPAIGNS_NR', SENTS,        NULL)), MAX(SENTS))        AS SENTS,
      COALESCE(MAX(IF(FUENTE_TABLA='ALL_CAMPAIGNS_NR', TOTAL_TEST,   NULL)), MAX(TOTAL_TEST))   AS TOTAL_TEST,
      COALESCE(MAX(IF(FUENTE_TABLA='ALL_CAMPAIGNS_NR', TOTAL_CONTROL,NULL)), MAX(TOTAL_CONTROL)) AS TOTAL_CONTROL,
      COALESCE(MAX(IF(FUENTE_TABLA='ALL_CAMPAIGNS_NR', TOTAL_ARRIVED,NULL)), MAX(TOTAL_ARRIVED)) AS TOTAL_ARRIVED,
      COALESCE(MAX(IF(FUENTE_TABLA='ALL_CAMPAIGNS_NR', TOTAL_OPEN,   NULL)), MAX(TOTAL_OPEN))   AS TOTAL_OPEN,
      MAX(TOTAL_CLICK)                                                             AS TOTAL_CLICK,
      COALESCE(MAX(IF(FUENTE_TABLA='ALL_CAMPAIGNS_NR', OPEN_RATE,    NULL)), MAX(OPEN_RATE))    AS OPEN_RATE,
      -- Impacto incremental: priorizar Rama A (NR_INC_USERS/7D_ADJUST vs Q_NR_7D)
      COALESCE(MAX(IF(FUENTE_TABLA='ALL_CAMPAIGNS_NR', USER_INC,             NULL)), MAX(USER_INC))             AS USER_INC,
      COALESCE(MAX(IF(FUENTE_TABLA='ALL_CAMPAIGNS_NR', USER_INC_CON_ADJUST,  NULL)), MAX(USER_INC_CON_ADJUST))  AS USER_INC_CON_ADJUST,
      COALESCE(MAX(IF(FUENTE_TABLA='ALL_CAMPAIGNS_NR', VALUE_INC,            NULL)), MAX(VALUE_INC))            AS VALUE_INC,
      -- Métricas solo en Rama A (NULL en Rama B → MAX funciona directamente)
      MAX(TOTAL_ABSOLUTO_NR)                                                       AS TOTAL_ABSOLUTO_NR,
      MAX(NR_TOTAL_CONTROL)                                                        AS NR_TOTAL_CONTROL,
      MAX(RATIO_CANIBALIZACION)                                                    AS RATIO_CANIBALIZACION,
      -- JOURNEY-specific: entradas al journey por grupo test y control
      MAX(ENTRY_TEST_JNY)                                                          AS ENTRY_TEST_JNY,
      MAX(ENTRY_CONTROL_JNY)                                                       AS ENTRY_CONTROL_JNY,
      -- Clasificación y flags
      COALESCE(MAX(IF(FUENTE_TABLA='ALL_CAMPAIGNS_NR', CLASIF_CAMPAIGNS,NULL)), MAX(CLASIF_CAMPAIGNS)) AS CLASIF_CAMPAIGNS,
      COALESCE(MAX(IF(FUENTE_TABLA='ALL_CAMPAIGNS_NR', FLAG_PAID,     NULL)), MAX(FLAG_PAID))     AS FLAG_PAID,
      COALESCE(MAX(IF(FUENTE_TABLA='ALL_CAMPAIGNS_NR', FLAG_INCENTIVO,NULL)), MAX(FLAG_INCENTIVO)) AS FLAG_INCENTIVO,
      -- Costos
      MAX(CONSUMIDO_USD)                                                           AS CONSUMIDO_USD,
      MAX(COSTO_ENVIO_USD)                                                         AS COSTO_ENVIO_USD,
      MAX(COSTO_MANTIKA_USD)                                                       AS COSTO_MANTIKA_USD,
      -- FUENTE_TABLA: 'AMBAS' si la comm está en las 2 tablas el mismo día y canal
      CASE
        WHEN COUNT(DISTINCT FUENTE_TABLA) > 1 THEN 'AMBAS'
        ELSE ANY_VALUE(FUENTE_TABLA)
      END                                                                          AS FUENTE_TABLA
    FROM combined
    GROUP BY COMMUNICATION_ID, SENT_DATE, MONTH_ID, CANAL
    ORDER BY SENT_DATE DESC, COMMUNICATION_ID, CANAL
    """


def get_perf_vpu_sql(HIERARCHY_NR):
    """DEPRECATED §72 — NO USADO. Reemplazado por get_vpu_tc_sql().
    SQL Valor Predictivo 90D por canal/mes desde PANEL_MONTHLY_DAILY_HISTORICO.
    VALUE_MKT_PREDICTION_90D_NR_USERS ya viene pre-multiplicado (NR × VPU por fila).
    → VPU_avg = SUM(col) / SUM(NR_USERS). No requiere multiplicación manual.
    Mapeos desde hierarchy_nr → bq_mapping (igual que get_nr_sql).
    Resultado: una fila por (MONTH_ID, PERF_CANAL) con NR_TOTAL, NR_VPU_PROD.
    """
    cases = []
    for c in HIERARCHY_NR:
        if c.get('is_leaf') and 'bq_mapping' in c and not c['bq_mapping'].get('is_org'):
            bm      = c['bq_mapping']
            s_list  = f"('{bm['strategy']}')" if isinstance(bm['strategy'], str) else str(tuple(bm['strategy']))
            ch_list = f"('{bm['channel'].upper()}')" if isinstance(bm['channel'], str) else str(tuple([x.upper() for x in bm['channel']]))
            cases.append(f"WHEN STRATEGY IN {s_list} AND UPPER(CHANNEL_APERTURA_3) IN {ch_list} THEN '{c['label']}'")
    case_stmt = "\n      ".join(cases)
    return f"""
    WITH base AS (
      SELECT
        CASE {case_stmt} ELSE 'ORG' END AS PERF_CANAL,
        FORMAT_DATE('%Y%m', FECHA_DIARIA) AS MONTH_ID,
        COALESCE(NR_USERS, 0) AS NR,
        COALESCE(VALUE_MKT_PREDICTION_90D_NR_USERS, 0) AS VPU_PROD
      FROM `meli-bi-data.SBOX_MKTCORPMP.PANEL_MONTHLY_DAILY_HISTORICO`
      WHERE SIT_SITE_ID = 'MLM' AND FECHA_DIARIA >= DATE '2025-01-01'
    )
    SELECT
      MONTH_ID,
      PERF_CANAL,
      SUM(NR)       AS NR_TOTAL,
      SUM(VPU_PROD) AS NR_VPU_PROD
    FROM base
    GROUP BY MONTH_ID, PERF_CANAL
    """
