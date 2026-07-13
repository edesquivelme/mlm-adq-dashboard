"""
builders.py — Generadores HTML y chart JSON para MLM ADQ Dashboard V1
══════════════════════════════════════════════════════════════════════
CONEXIONES:
  · Entrada  : dict 'data' devuelto por processors.process_all()
               └─ data['HIERARCHY_NR'] → canales N+R (hierarchy_nr del JSON)
               └─ data['HIERARCHY_C']  → canales Costos (hierarchy_cost del JSON)
               └─ data['monthly_nr'], data['monthly_inv_total'], etc.
  · plan_nr, plan_lines_data → cargados en gen_dashboard_v1.py desde Excel
  · Salida   : strings HTML (inyectados en template via {{MOM_TABLE}}, {{PERF_TABLE}})
               dicts JSON de Plotly (inyectados via {{CHARTS_JSON}})

CONVENCIÓN DE NOMBRES:
  HIERARCHY_NR  = data['HIERARCHY_NR']  (canales N+R)
  HIERARCHY_C   = data['HIERARCHY_C']   (canales Costos)
"""

import json
import plotly.graph_objects as go
from processors import fmt_month


def _cs(v):
    """Coerce to str NaN-safe. float NaN es truthy en Python, 'v or default' no funciona."""
    if v is None or (isinstance(v, float) and v != v):
        return ''
    return str(v).strip()


# ── Formateadores compartidos por todas las tablas ────────────

def fmt_val(v):
    if v >= 1_000_000: return f'{v/1_000_000:.2f}M'
    if v >= 1_000:     return f'{v/1_000:.1f}K'
    return f'{v:,.0f}'

def fmt_usd(v):
    if v is None: return '<span style="color:#aaa">—</span>'
    if abs(v) >= 1_000_000: return f'${v/1_000_000:.2f}M'
    if abs(v) >= 1_000:     return f'${v/1_000:.1f}K'
    return f'${v:,.0f}'

def fmt_cpa(v):
    if v is None: return '<span style="color:#aaa">—</span>'
    return f'${v:.2f}'


# ── Tabla NR Mensual (pestaña NR Mensual) ─────────────────────

def build_mom_table_html(data, plan_nr, plan_lines_data):
    """Genera la tabla HTML estática de NR Mensual (pestaña NR Mensual).
    Itera HIERARCHY_NR para construir filas Canal + sub-filas MoM/Plan/vs Plan.
    plan_nr y plan_lines_data vienen del Excel (cargados en gen_dashboard_v1.py).
    """
    HIERARCHY_NR = data['HIERARCHY_NR']
    months       = data['months']
    monthly_nr   = data['monthly_nr']
    monthly_mom  = data['monthly_mom']

    CLS = {
        'grand': ('background:#1a2744;color:#fff;font-weight:700', 'background:#111d38;color:#9db4d0'),
        'sub1':  ('background:#2d5986;color:#fff;font-weight:600', 'background:#1e4570;color:#c0d8f0'),
        'sub2':  ('background:#4a7ab5;color:#fff;font-weight:500', 'background:#3a6898;color:#d0e4f8'),
        'leaf':  ('background:#fff;color:#333', 'background:#fafafa;color:#666')
    }

    def fmt_pct(v, dark):
        if v is None: return '<span style="color:#aaa">—</span>'
        pos_col = '#81c995' if dark else '#0d7a3e'
        neg_col = '#f28b82' if dark else '#c5221f'
        if v >= 0: return f'<span style="color:{pos_col};font-weight:600">▲ {v*100:.1f}%</span>'
        return f'<span style="color:{neg_col};font-weight:600">▼ {abs(v)*100:.1f}%</span>'

    h = '<div class="table-scroll"><table class="mom-tbl"><thead><tr><th class="lbl-col">Canal</th>'
    for m in months: h += f'<th data-month="{m}">{fmt_month(m)}</th>'
    h += '</tr></thead><tbody>'

    for c in HIERARCHY_NR:
        label  = c['label']
        indent = c['indent']
        row_s, met_s = CLS[c['level']]
        dark = c['level'] != 'leaf'
        pad  = f'padding-left:{indent*14+10}px'

        h += f'<tr data-canal="{label}"><td class="lbl-col" style="{pad};{row_s}">{label}</td>'
        for m in months: h += f'<td style="{row_s}" data-month="{m}">{fmt_val(monthly_nr[label].get(m,0))}</td>'
        h += '</tr>'

        h += f'<tr data-canal="{label}"><td class="lbl-col" style="padding-left:{(indent+1)*14+10}px;{met_s};font-style:italic;font-size:10px">MoM</td>'
        for m in months: h += f'<td style="{met_s};font-size:10px" data-month="{m}">{fmt_pct(monthly_mom[label].get(m), dark)}</td>'
        h += '</tr>'

        label_plan = plan_nr.get(label, {})
        has_plan   = any(v for v in label_plan.values())
        plan_row_s = 'background:#2a3347;color:#9db4d0;font-size:10px' if dark else 'background:#f0f0f0;color:#555;font-size:10px'

        if has_plan:
            h += f'<tr data-canal="{label}"><td class="lbl-col" style="padding-left:{(indent+1)*14+10}px;{plan_row_s};font-style:italic">Plan</td>'
            for m in months:
                pv   = label_plan.get(m)
                cell = fmt_val(pv) if pv and pv > 0 else '<span style="color:#aaa">—</span>'
                h += f'<td style="{plan_row_s}" data-month="{m}">{cell}</td>'
            h += '</tr>'

            h += f'<tr data-canal="{label}"><td class="lbl-col" style="padding-left:{(indent+1)*14+10}px;{plan_row_s};font-style:italic">vs Plan</td>'
            for m in months:
                pv   = label_plan.get(m)
                av   = monthly_nr[label].get(m, 0)
                cell = fmt_pct((av - pv) / pv, dark) if pv and pv > 0 else '<span style="color:#aaa">—</span>'
                h += f'<td style="{plan_row_s};font-size:10px" data-month="{m}">{cell}</td>'
            h += '</tr>'

        # Sub-filas de plan_lines (visibles solo al filtrar ese canal en JS)
        if label in plan_lines_data:
            c_node   = next(x for x in HIERARCHY_NR if x['label'] == label)
            pl_pad   = f'padding-left:{(indent+2)*14+10}px'
            pl_row_s = 'background:#162840;color:#7fa8cc;font-size:10px;font-style:italic'
            for pl in c_node.get('plan_lines', []):
                pl_lbl     = pl['label']
                pl_color   = pl.get('color', '#888')
                pl_monthly = plan_lines_data[label].get(pl_lbl, {})
                h += f'<tr data-planline="{label}" style="display:none">'
                h += f'<td class="lbl-col" style="{pl_pad};{pl_row_s}"><span style="color:{pl_color};font-weight:700">&#9632;</span> {pl_lbl}</td>'
                for m in months:
                    pv   = pl_monthly.get(m)
                    cell = fmt_val(pv) if pv and pv > 0 else '<span style="color:#aaa">—</span>'
                    h += f'<td style="{pl_row_s}" data-month="{m}">{cell}</td>'
                h += '</tr>'

    h += '</tbody></table></div>'
    return h


# ── Gráfica Corporativa N+R — % Participación por Grupo (pestaña NR Mensual) ─

def build_nr_corp_bar_chart(data):
    """Barras apiladas de N+R nominal por grupo de canal + línea Plan Total N+R.

    Eje Y izquierdo (y1): N+R absoluto en K — permite ver diferencias de volumen entre meses.
    Eje Y derecho  (y2): Plan Total N+R (de hierarchy_PLAN_Corp, corp_total) — línea roja punteada.
    Labels internos:     % de participación de cada grupo (calculado internamente, no afecta escala).

    Grupos (de abajo arriba):
      1. NO ATRIBUIDO — gris claro  (#C8CDD8)
      2. OC+UCRANIA   — amarillo    (#F5D000)
      3. POM          — cian        (#1FB8D4)
      4. OTHERS       — gris oscuro (#7A7D82)

    Datos N+R real:  data['monthly_nr_corp_by_node']  — construido por process_nr_corp()
    Datos Plan:      data['plan_nr_corp_by_node']      — construido por load_plan_corp()
    """
    months                    = data['months']
    monthly_nr_corp_by_node   = data['monthly_nr_corp_by_node']
    # Plan Total N+R para el eje Y derecho — clave 'corp_total' de hierarchy_PLAN_Corp
    plan_nr_corp_by_node       = data.get('plan_nr_corp_by_node', {})
    plan_total_nr_by_month     = plan_nr_corp_by_node.get('corp_total', {})

    x_labels = [fmt_month(m) for m in months]

    # ── NR mensual por grupo (valores absolutos — eje y1) ────────────────────
    nr_by_group_noatrib = [monthly_nr_corp_by_node.get('corp_noatrib', {}).get(m, 0) for m in months]
    nr_by_group_oc_ucr  = [monthly_nr_corp_by_node.get('corp_oc_ucr',  {}).get(m, 0) for m in months]
    nr_by_group_pom     = [monthly_nr_corp_by_node.get('corp_pom',     {}).get(m, 0) for m in months]
    nr_by_group_others  = [monthly_nr_corp_by_node.get('corp_others',  {}).get(m, 0) for m in months]
    nr_total_by_month   = [monthly_nr_corp_by_node.get('corp_total',   {}).get(m, 0) for m in months]

    # Escala K para barras (eje y1)
    def to_k(nr_list):
        return [round(v / 1_000, 1) for v in nr_list]

    # % participación — solo para labels internos (no cambia la escala del eje)
    def pct_of_total(nr_list_for_group, total_nr_list):
        return [round(n / t * 100, 1) if t > 0 else 0.0
                for n, t in zip(nr_list_for_group, total_nr_list)]

    pct_noatrib = pct_of_total(nr_by_group_noatrib, nr_total_by_month)
    pct_oc_ucr  = pct_of_total(nr_by_group_oc_ucr,  nr_total_by_month)
    pct_pom     = pct_of_total(nr_by_group_pom,     nr_total_by_month)
    pct_others  = pct_of_total(nr_by_group_others,  nr_total_by_month)

    def inside_label_with_pct(pct_val, min_pct=5):
        """Label interior: % de participación — solo si el segmento es suficientemente visible."""
        return f'{pct_val:.0f}%' if pct_val >= min_pct else ''

    fig = go.Figure()

    # ── Barras apiladas en K (eje y1) — de abajo a arriba ────────────────────
    fig.add_trace(go.Bar(
        name='NO ATRIBUIDO', x=x_labels, y=to_k(nr_by_group_noatrib),
        marker_color='#C8CDD8',
        text=[inside_label_with_pct(v) for v in pct_noatrib],
        textposition='inside', textfont=dict(size=10, color='#555555'),
        customdata=[[int(n), p] for n, p in zip(nr_by_group_noatrib, pct_noatrib)],
        hovertemplate='NO ATRIBUIDO: %{customdata[0]:,} (%{customdata[1]:.1f}%)<extra></extra>'
    ))
    fig.add_trace(go.Bar(
        name='OC+UCRANIA', x=x_labels, y=to_k(nr_by_group_oc_ucr),
        marker_color='#F5D000',
        text=[inside_label_with_pct(v) for v in pct_oc_ucr],
        textposition='inside', textfont=dict(size=10, color='#333333'),
        customdata=[[int(n), p] for n, p in zip(nr_by_group_oc_ucr, pct_oc_ucr)],
        hovertemplate='OC+UCRANIA: %{customdata[0]:,} (%{customdata[1]:.1f}%)<extra></extra>'
    ))
    fig.add_trace(go.Bar(
        name='POM', x=x_labels, y=to_k(nr_by_group_pom),
        marker_color='#1FB8D4',
        text=[inside_label_with_pct(v) for v in pct_pom],
        textposition='inside', textfont=dict(size=10, color='#ffffff'),
        customdata=[[int(n), p] for n, p in zip(nr_by_group_pom, pct_pom)],
        hovertemplate='POM: %{customdata[0]:,} (%{customdata[1]:.1f}%)<extra></extra>'
    ))
    fig.add_trace(go.Bar(
        name='OTHERS', x=x_labels, y=to_k(nr_by_group_others),
        marker_color='#7A7D82',
        text=[inside_label_with_pct(v, min_pct=4) for v in pct_others],
        textposition='inside', textfont=dict(size=9, color='#ffffff'),
        customdata=[[int(n), p] for n, p in zip(nr_by_group_others, pct_others)],
        hovertemplate='OTHERS: %{customdata[0]:,} (%{customdata[1]:.1f}%)<extra></extra>'
    ))

    # ── Línea Plan Total N+R (eje y2 derecho) ────────────────────────────────
    # Fuente: plan_nr_corp_by_node['corp_total'] — cargado por load_plan_corp()
    # Usa la misma escala K que el eje y1 para facilitar comparación visual
    plan_total_k_by_month = [
        round(plan_total_nr_by_month.get(m, 0) / 1_000, 1) if plan_total_nr_by_month.get(m) else None
        for m in months
    ]
    if any(v is not None for v in plan_total_k_by_month):
        fig.add_trace(go.Scatter(
            name='Plan Total N+R', x=x_labels, y=plan_total_k_by_month,
            yaxis='y2', mode='lines+markers',
            line=dict(color='#C00000', width=2, dash='dot'),
            marker=dict(size=6, symbol='circle', color='#C00000'),
            customdata=[int(plan_total_nr_by_month.get(m, 0)) for m in months],
            hovertemplate='Plan Total: %{customdata:,}<extra></extra>'
        ))

    # ── Máximo del eje y1 para que las barras no toquen el techo ─────────────
    max_total_k = max((v / 1_000 for v in nr_total_by_month if v), default=1)
    y1_range_max = round(max_total_k * 1.15, 0)  # +15% de margen visual

    has_plan_line = any(v is not None for v in plan_total_k_by_month)

    # ── Anotaciones: total N+R encima de cada barra (eje y1) ─────────────────
    total_nr_top_annotations = []
    for i, month in enumerate(months):
        total_val = nr_total_by_month[i]
        if total_val > 0:
            label = f'{total_val/1_000_000:.2f}M' if total_val >= 1_000_000 else f'{total_val/1_000:.0f}K'
            total_nr_top_annotations.append(dict(
                x=x_labels[i], y=total_val / 1_000,
                text=f'<b>{label}</b>',
                showarrow=False, yanchor='bottom', yshift=4, xanchor='center',
                font=dict(size=9, color='#333333')
            ))

    fig.update_layout(
        barmode='stack',
        height=330,
        plot_bgcolor='white', paper_bgcolor='white',
        title_text='N+R por Canal — Volumen y % Participación',
        title_font=dict(size=13, color='#0d1f3c'),
        hovermode='x unified',
        legend=dict(orientation='h', y=-0.22, font_size=10, traceorder='reversed',
                    xanchor='left', x=0),
        margin=dict(l=55, r=65, t=50, b=85),
        # Eje Y izquierdo: N+R nominal en K
        yaxis=dict(
            title=dict(text='N+R (miles)', font=dict(size=10)),
            ticksuffix='K', range=[0, y1_range_max],
            showgrid=True, gridcolor='#eeeeee', tickfont_size=10,
            zeroline=False
        ),
        # Eje Y derecho: Plan Total N+R en K — color negro (la línea de plan sigue siendo roja)
        yaxis2=dict(
            title=dict(text='Plan N+R (miles)', font=dict(size=10, color='#333333')),
            ticksuffix='K', overlaying='y', side='right',
            showgrid=False, tickfont=dict(size=10, color='#333333'),
            range=[0, y1_range_max]
        ) if has_plan_line else {},
        xaxis=dict(tickfont_size=10, showgrid=False),   # sin líneas verticales
        # uniformtext: todos los labels internos al mismo tamaño — oculta los que no caben
        uniformtext=dict(minsize=9, mode='hide'),
        annotations=total_nr_top_annotations
    )
    return json.loads(fig.to_json())


# ── Tabla Corporativa N+R (pestaña NR Mensual — sección inferior) ────────────

def build_nr_corp_table_html(data):
    """Tabla interactiva de N+R usando hierarchy_nr_corp_detail (4 niveles con colapso).

    ESTRUCTURA VISUAL (▶ = colapsado por defecto, ▼ = expandido):
      ▶ 1. OC + UCR          ← grupo sub1, siempre visible
          ▶ 1.1 UCRANIA E&G  ← sub2, visible al expandir OC+UCR
              ⸻ EMAIL        ← medio, visible al expandir UCRANIA E&G
              ⸻ PANDORA
              ⸻ PUSH
              ⸻ REAL ESTATES
              ⸻ WPP
          ▶ 1.2 OWN CHANNELS RECURRING
              ⸻ EMAIL / JOURNEY / PANDORA / PUSH / WPP
          ⸻ 1.3 OWN CHANNELS ADHOC
      ▶ 2. POM
          ⸻ ACQUISITION POM / ACTIVATION POM / WEB POM / CTW POM
      ▶ 3. OTHERS
          ⸻ MGM / L&P / UCR PRD / SEO / POM SELLERS / POM OTHERS
      ⸻ 4. NO ATRIBUIDO
      ── Total N+R  ← al final, referencia global

    Interactividad: toggleCorpNode() / collapseCorpNode() definidos en template_dashboard.html.

    Filas por nodo: N+R (absoluto) | MoM (▲/▼%) | Share N+R (%).
    Fuente: data['monthly_nr_corp_by_node'] (process_nr_corp → processors.py).
    """
    HIERARCHY_NR_CORP        = data['HIERARCHY_NR_CORP']
    months                   = data['months']
    monthly_nr_corp_by_node  = data['monthly_nr_corp_by_node']
    # plan_nr_corp_by_node: dict { corp_node_id: { yyyymm: plan_int } }
    # construido por load_plan_corp() en gen_dashboard_v1.py, usando hierarchy_PLAN_Corp.
    # INDEPENDIENTE de plan_nr (que alimenta la pestaña NR Mensual).
    # OC+UCR = rows 6+10; POM = rows 5+9; UCR PRD = row 17; ver hierarchy_PLAN_Corp en config.
    plan_nr_corp_by_node_from_data = data.get('plan_nr_corp_by_node', {})

    corp_total_node_id = 'corp_total'
    total_nr_by_month  = monthly_nr_corp_by_node.get(corp_total_node_id, {})

    # Lookup rápido id → nodo. Se incluyen TODOS — _doc es solo documentación embebida.
    node_by_id = {c['id']: c for c in HIERARCHY_NR_CORP if 'id' in c}

    # ── Paleta de estilos — clean/light (fondo blanco, texto oscuro, sin fondos saturados) ─
    # Inspiración: tabla de referencia con fondo blanco, bullet de canal y separadores sutiles
    LEVEL_BG   = {'grand': '#f0f4fa', 'sub1': '#ffffff', 'sub2': '#ffffff', 'medio': '#ffffff'}
    LEVEL_TXT  = {'grand': '#0d1f3c', 'sub1': '#0d1f3c', 'sub2': '#1a3562', 'medio': '#333333'}
    LEVEL_WT   = {'grand': '700',     'sub1': '700',     'sub2': '500',     'medio': '400'}
    # Sub-filas MoM / Share: fondo levemente grisado, texto gris
    LEVEL_SUBROW_BG  = {'grand': '#e8edf5', 'sub1': '#f5f6f8', 'sub2': '#f5f6f8', 'medio': '#f5f6f8'}
    LEVEL_SUBROW_TXT = {'grand': '#4a6080',  'sub1': '#6b7a99',  'sub2': '#6b7a99',  'medio': '#888888'}

    def is_dark(level):
        return False  # Todos los fondos son claros → texto verde/rojo estándar en MoM

    def fmt_pct_corp_mom(actual_nr, prev_nr, dark_bg):
        """MoM con flecha de color — verde si sube, rojo si baja."""
        if prev_nr is None or prev_nr == 0:
            return '<span style="color:#aaa">—</span>'
        pct  = (actual_nr - prev_nr) / abs(prev_nr)
        pos_col = '#81c995' if dark_bg else '#0d7a3e'
        neg_col = '#f28b82' if dark_bg else '#c5221f'
        arrow = '▲' if pct >= 0 else '▼'
        color = pos_col if pct >= 0 else neg_col
        return f'<span style="color:{color};font-weight:600">{arrow} {abs(pct)*100:.1f}%</span>'

    def fmt_pct_corp_share(node_nr, total_nr):
        """Share N+R neutral — sin flecha."""
        if not total_nr:
            return '<span style="color:#aaa">—</span>'
        return f'{node_nr / total_nr * 100:.1f}%'

    def render_corp_node_rows(node_id, parent_id, hidden_by_default):
        """Genera filas HTML del nodo (header + N+R + Plan + vs Plan + MoM + Share) recursivamente.

        Estructura de 6 filas por nodo:
          1. HEADER      — nombre canal + toggle ▶, SIN valores numéricos.
                           Única fila con data-corp-node (usada por collapseCorpNode()).
          2. N+R         — valores reales de N+R del mes.
          3. Plan        — plan del Excel (solo nodos con corp_plan_nr_key en config).
                           Mapeo Excel→nodo: ver hierarchy_PLAN en channels_config.json.
          4. vs Plan     — % desviación (actual - plan) / plan (solo si hay Plan).
          5. MoM         — % cambio mes a mes de N+R real.
          6. Share N+R   — % del total mensual.

        Filas 2-6: data-corp-parent=parent_id (se ocultan cuando el padre colapsa).
                   NO tienen data-corp-node (evita tratarlas como raíz en collapse recursivo).
        Hijos:     data-corp-parent=node_id (ocultos por defecto, toggle los muestra).
        """
        node   = node_by_id.get(node_id)
        if not node:
            return ''

        # Nodos con 0 N+R en todos los meses y sin hijos activos → no renderizar
        # SEO y POM SELLERS siempre dan 0 en TC (canales deprecated/sin data)
        _SKIP_ZERO_NODES = {'corp_seo', 'corp_pom_sellers'}
        if node_id in _SKIP_ZERO_NODES:
            return ''

        level    = node.get('level', 'medio')
        label    = node['label']
        indent   = node.get('indent', 0)
        color    = node.get('color', '#888888')
        children = [cid for cid in node.get('children', []) if cid in node_by_id]

        # Plan corp: indexado directamente por corp_node_id desde plan_nr_corp_by_node_from_data.
        # Calculado por load_plan_corp() en gen_dashboard_v1.py usando hierarchy_PLAN_Corp.
        # Lógica distinta a plan_nr (NR Mensual): OC+UCR=rows 6+10, POM=rows 5+9, UCR_PRD=row 17.
        plan_nr_by_month_for_node_in_corp  = plan_nr_corp_by_node_from_data.get(node_id, {})
        this_node_has_plan_in_corp_table   = bool(any(v for v in plan_nr_by_month_for_node_in_corp.values()))

        nr_by_month_for_node = monthly_nr_corp_by_node.get(node_id, {})

        # ── Estilos por nivel (paleta limpia: fondos blancos, texto oscuro) ──
        bg      = LEVEL_BG.get(level, '#ffffff')
        txt     = LEVEL_TXT.get(level, '#333333')
        sub_bg  = LEVEL_SUBROW_BG.get(level, '#f5f6f8')
        sub_txt = LEVEL_SUBROW_TXT.get(level, '#888888')
        wt      = LEVEL_WT.get(level, '400')
        dark_bg = is_dark(level)

        pad_px     = indent * 18 + 10
        sub_pad_px = (indent + 1) * 18 + 10

        left_border_width_css = '3px' if level in ('grand', 'sub1') else '2px'
        border_top_css        = 'border-top:1px solid #e0e4ed;' if level in ('sub1', 'grand') else ''

        # Estilo header (con fondo y peso del nivel)
        header_cell_s = (f'{border_top_css}background:{bg};color:{txt};font-weight:{wt};'
                         f'border-left:{left_border_width_css} solid {color}')
        # Estilo sub-métricas normales (N+R, MoM, Share)
        subrow_cell_s = (f'background:{sub_bg};color:{sub_txt};font-size:10px;'
                         f'border-left:{left_border_width_css} solid {color}')
        # Estilo filas Plan y vs Plan: fondo crema #fdf9ec (idéntico a tabla NR Mensual)
        plan_cell_s   = (f'font-size:10px;color:#5a4a10;background:#fdf9ec;font-style:italic;'
                         f'border-left:{left_border_width_css} solid {color}')
        vsplan_cell_s = (f'font-size:10px;background:#fdf9ec;'
                         f'border-left:{left_border_width_css} solid {color}')

        hidden_s    = ' style="display:none"' if hidden_by_default else ''
        parent_attr = f' data-corp-parent="{parent_id}"' if parent_id else ''

        # Botón toggle ▶ para nodos con hijos; bullet ● para hojas
        if children:
            toggle_btn_html = (f'<button onclick="toggleCorpNode(\'{node_id}\')" '
                               f'data-corp-toggle="{node_id}" '
                               f'style="background:none;border:none;cursor:pointer;'
                               f'color:{color};font-size:10px;margin-right:4px;padding:0;'
                               f'vertical-align:middle;line-height:1;font-weight:700">▶</button>')
        else:
            toggle_btn_html = (f'<span style="display:inline-block;width:18px;color:{color};'
                               f'font-size:9px;vertical-align:middle">●</span>')

        rows = ''

        # ── Fila 1: HEADER — nombre del canal, celdas vacías, con toggle ─────
        # Única fila con data-corp-node → collapseCorpNode() la usa como ancla de recursión
        rows += f'<tr{parent_attr}{hidden_s} data-corp-node="{node_id}" data-corp-level="{level}">'
        rows += f'<td class="lbl-col" style="padding-left:{pad_px}px;{header_cell_s}">{toggle_btn_html}{label}</td>'
        for month in months:
            rows += f'<td style="background:{bg}" data-month="{month}"></td>'
        rows += '</tr>'

        # ── Fila 2: N+R — valores reales ─────────────────────────────────────
        rows += f'<tr{parent_attr}{hidden_s}>'
        rows += f'<td class="lbl-col" style="padding-left:{sub_pad_px}px;{subrow_cell_s}">N+R</td>'
        for month in months:
            nr_actual_this_month = nr_by_month_for_node.get(month, 0)
            rows += f'<td style="{subrow_cell_s}" data-month="{month}">{fmt_val(nr_actual_this_month) if nr_actual_this_month else "—"}</td>'
        rows += '</tr>'

        # ── Fila 3: Plan — valores de hierarchy_PLAN_Corp (solo nodos con mapeo definido) ──
        # plan_nr_by_month_for_node_in_corp viene de load_plan_corp() via data['plan_nr_corp_by_node'].
        # OC+UCR = rows 6+10 (no row 17); POM = rows 5+9; UCR PRD = row 17.
        # INDEPENDIENTE del plan_nr usado en NR Mensual.
        if this_node_has_plan_in_corp_table:
            rows += f'<tr{parent_attr}{hidden_s}>'
            rows += f'<td class="lbl-col" style="padding-left:{sub_pad_px}px;{plan_cell_s}">Plan</td>'
            for month in months:
                plan_val_this_month  = plan_nr_by_month_for_node_in_corp.get(month)
                plan_formatted_value = (fmt_val(plan_val_this_month)
                                        if plan_val_this_month and plan_val_this_month > 0
                                        else '<span style="color:#aaa">—</span>')
                rows += f'<td style="{plan_cell_s}" data-month="{month}">{plan_formatted_value}</td>'
            rows += '</tr>'

            # ── Fila 4: vs Plan — % desviación (actual_nr - plan_nr) / plan_nr ──
            rows += f'<tr{parent_attr}{hidden_s}>'
            rows += f'<td class="lbl-col" style="padding-left:{sub_pad_px}px;{vsplan_cell_s};font-style:italic">vs Plan</td>'
            for month in months:
                actual_nr_for_vs_plan = nr_by_month_for_node.get(month, 0)
                plan_val_for_vs_plan  = plan_nr_by_month_for_node_in_corp.get(month)
                if plan_val_for_vs_plan and plan_val_for_vs_plan > 0:
                    vsplan_cell_content = fmt_pct_corp_mom(actual_nr_for_vs_plan,
                                                           plan_val_for_vs_plan, dark_bg)
                else:
                    vsplan_cell_content = '<span style="color:#aaa">—</span>'
                rows += f'<td style="{vsplan_cell_s}" data-month="{month}">{vsplan_cell_content}</td>'
            rows += '</tr>'

        # ── Fila 5: MoM — % cambio mes a mes ─────────────────────────────────
        rows += f'<tr{parent_attr}{hidden_s}>'
        rows += f'<td class="lbl-col" style="padding-left:{sub_pad_px}px;{subrow_cell_s};font-style:italic">MoM</td>'
        for i, month in enumerate(months):
            actual_nr_this_month = nr_by_month_for_node.get(month, 0)
            prev_nr_this_node    = nr_by_month_for_node.get(months[i - 1]) if i > 0 else None
            rows += f'<td style="{subrow_cell_s}" data-month="{month}">{fmt_pct_corp_mom(actual_nr_this_month, prev_nr_this_node, dark_bg)}</td>'
        rows += '</tr>'

        # ── Fila 6: Share N+R — % del total mensual ───────────────────────────
        rows += f'<tr{parent_attr}{hidden_s}>'
        rows += f'<td class="lbl-col" style="padding-left:{sub_pad_px}px;{subrow_cell_s};font-style:italic">Share N+R</td>'
        for month in months:
            nr_val_for_share    = nr_by_month_for_node.get(month, 0)
            total_nr_this_month = total_nr_by_month.get(month, 0)
            rows += f'<td style="{subrow_cell_s}" data-month="{month}">{fmt_pct_corp_share(nr_val_for_share, total_nr_this_month)}</td>'
        rows += '</tr>'

        # ── Hijos (recursivo — ocultos por defecto hasta toggle del usuario) ──
        for child_id in children:
            rows += render_corp_node_rows(child_id, parent_id=node_id, hidden_by_default=True)

        return rows

    # ── Construir HTML ────────────────────────────────────────────────────────
    h  = '<div class="table-scroll"><table class="mom-tbl nr-corp-tbl">'
    h += '<thead><tr><th class="lbl-col">Canal / Métrica</th>'
    for month in months:
        h += f'<th data-month="{month}">{fmt_month(month)}</th>'
    h += '</tr></thead><tbody>'

    # Grupos (hijos directos de corp_total) se muestran primero — siempre visibles
    root_node      = node_by_id.get(corp_total_node_id, {})
    group_node_ids = [cid for cid in root_node.get('children', []) if cid in node_by_id]
    for group_id in group_node_ids:
        # parent_id=None → siempre visible (sin data-corp-parent → no se ocultan por toggle externo)
        h += render_corp_node_rows(group_id, parent_id=None, hidden_by_default=False)

    # Total N+R al fondo — separador visual + fila de referencia global
    h += ('<tr><td class="lbl-col" colspan="1" '
          'style="border-top:2px solid #2d5986;padding:0;height:4px;background:#f0f4fa"></td>'
          f'<td colspan="{len(months)}" '
          'style="border-top:2px solid #2d5986;padding:0;height:4px;background:#f0f4fa"></td></tr>')
    h += render_corp_node_rows(corp_total_node_id, parent_id=None, hidden_by_default=False)

    h += '</tbody></table></div>'
    return h


# ── Gráfica Performance Corp (pestaña Performance_vista_Corp) ────────────────

def build_perf_corp_bar_chart(data):
    """Gráfica de Inversión + VPU + CPA Blend + Plan Inv. para la pestaña Performance_vista_Corp.

    MISMOS colores, estilos y grupos que build_nr_corp_bar_chart() en la sección NR Mensual corp:
      · Stack de abajo a arriba: NO ATRIBUIDO (#C8CDD8) → OC+UCRANIA (#F5D000) → POM (#1FB8D4) → OTHERS (#7A7D82)
      · Fondo blanco, uniformtext, sin gridlines verticales

    Diferencia respecto a la gráfica de NR: eje Y izquierdo = Inversión (M USD) en lugar de N+R.
    Las barras muestran la inversión de cada grupo (OTHERS = Total − OC+UCR − POM).
    NO ATRIBUIDO no tiene inversión → siempre 0 pero mantiene la leyenda para consistencia visual.

    Eje Y izquierdo (y1, M USD): barras apiladas + anotación total + línea Plan Inv. (roja punteada)
    Eje Y derecho  (y2, USD/usuario): CPA Blend (amarillo) + VPU Pred 90D (azul oscuro)
    """
    cost_months             = data['cost_months']
    monthly_inv_total       = data['monthly_inv_total']   # {hier_cost_label: {yyyymm: float}}
    monthly_nr              = data['monthly_nr']          # {hier_nr_label:   {yyyymm: int}}
    perf_vpu_prod           = data['perf_vpu_prod']       # {hier_nr_label:   {yyyymm: float}}
    plan_inv                = data.get('plan_inv', {})    # {hier_nr_label:   {yyyymm: int}}
    monthly_nr_corp_by_node = data['monthly_nr_corp_by_node']

    x_labels = [fmt_month(m) for m in cost_months]

    # ── Inversión por grupo (escala M USD) ────────────────────────────────────
    # Total real = referencia para calcular OTHERS y anotaciones
    inv_total_real_by_month = [(monthly_inv_total.get('Total Inversión', {}).get(m) or 0) for m in cost_months]
    inv_oc_ucr_by_month     = [(monthly_inv_total.get('OC + UCR',  {}).get(m) or 0) for m in cost_months]
    inv_pom_by_month        = [(monthly_inv_total.get('POM TOTAL', {}).get(m) or 0) for m in cost_months]
    # OTHERS = Total − OC+UCR − POM (incluye MGM y otros con inversión)
    inv_others_by_month     = [max(0, t - oc - po) for t, oc, po in zip(inv_total_real_by_month, inv_oc_ucr_by_month, inv_pom_by_month)]
    # NO ATRIBUIDO: sin inversión real (0 siempre) — se incluye por consistencia con la leyenda
    inv_noatrib_by_month    = [0.0] * len(cost_months)

    def to_m(inv_list):
        return [round(v / 1_000_000, 3) for v in inv_list]

    def fmt_inv_hover(m_usd_value):
        if m_usd_value >= 1:    return f'${m_usd_value:.2f}M'
        if m_usd_value >= 0.001: return f'${m_usd_value*1000:.0f}K'
        return '—'

    fig = go.Figure()

    # ── Barras apiladas (y1) — mismo orden que build_nr_corp_bar_chart ─────────
    # Abajo → arriba: NO ATRIBUIDO → OC+UCRANIA → POM → OTHERS
    fig.add_trace(go.Bar(
        name='NO ATRIBUIDO', x=x_labels, y=to_m(inv_noatrib_by_month),
        marker_color='#C8CDD8',
        hovertemplate='NO ATRIBUIDO: sin inversión<extra></extra>'
    ))
    fig.add_trace(go.Bar(
        name='OC+UCRANIA', x=x_labels, y=to_m(inv_oc_ucr_by_month),
        marker_color='#F5D000',
        customdata=[fmt_inv_hover(v/1_000_000) for v in inv_oc_ucr_by_month],
        hovertemplate='OC+UCRANIA: %{customdata}<extra></extra>'
    ))
    fig.add_trace(go.Bar(
        name='POM', x=x_labels, y=to_m(inv_pom_by_month),
        marker_color='#1FB8D4',
        customdata=[fmt_inv_hover(v/1_000_000) for v in inv_pom_by_month],
        hovertemplate='POM: %{customdata}<extra></extra>'
    ))
    fig.add_trace(go.Bar(
        name='OTHERS', x=x_labels, y=to_m(inv_others_by_month),
        marker_color='#7A7D82',
        customdata=[fmt_inv_hover(v/1_000_000) for v in inv_others_by_month],
        hovertemplate='OTHERS: %{customdata}<extra></extra>'
    ))

    # ── Línea Plan Inv. Total (y1, roja punteada) ─────────────────────────────
    plan_inv_total_nr_by_month = plan_inv.get('Total N+R', {})
    plan_inv_y1_mm = [
        round(plan_inv_total_nr_by_month.get(m, 0) / 1_000_000, 3)
        if plan_inv_total_nr_by_month.get(m) else None
        for m in cost_months
    ]
    if any(v is not None for v in plan_inv_y1_mm):
        fig.add_trace(go.Scatter(
            name='Plan Inv.', x=x_labels, y=plan_inv_y1_mm,
            mode='lines+markers',
            line=dict(color='#C00000', width=2, dash='dot'),
            marker=dict(size=6, symbol='circle', color='#C00000'),
            customdata=[fmt_inv_hover(v) if v else '—' for v in plan_inv_y1_mm],
            hovertemplate='Plan Inv.: %{customdata}<extra></extra>'
        ))

    # ── CPA Blend (y2, amarillo) — total_inv / total_nr_corp ─────────────────
    cpa_blend_y2 = []
    for m in cost_months:
        inv = monthly_inv_total.get('Total Inversión', {}).get(m) or 0
        nr  = (monthly_nr_corp_by_node.get('corp_total', {}).get(m)
               or monthly_nr.get('Total N+R', {}).get(m) or 0)
        cpa_blend_y2.append(round(inv / nr, 2) if inv and nr > 0 else None)

    if any(v is not None for v in cpa_blend_y2):
        fig.add_trace(go.Scatter(
            name='CPA Blend', x=x_labels, y=cpa_blend_y2,
            yaxis='y2', mode='lines+markers',
            line=dict(color='#E9C46A', width=2.5, dash='dot'),
            marker=dict(size=7, symbol='circle', color='#E9C46A'),
            customdata=[f'${v:.2f}' if v else '—' for v in cpa_blend_y2],
            hovertemplate='CPA Blend: %{customdata}<extra></extra>'
        ))

    # ── VPU Pred 90D (y2, azul oscuro) ───────────────────────────────────────
    vpu_y2 = []
    for m in cost_months:
        vpu_p = perf_vpu_prod.get('Total N+R', {}).get(m, 0) or 0
        nr    = monthly_nr.get('Total N+R', {}).get(m, 0) or 0
        vpu_y2.append(round(vpu_p / nr, 2) if nr > 0 and vpu_p > 0 else None)

    if any(v is not None for v in vpu_y2):
        fig.add_trace(go.Scatter(
            name='VPU Pred 90D', x=x_labels, y=vpu_y2,
            yaxis='y2', mode='lines+markers',
            line=dict(color='#264653', width=2.5, dash='dash'),
            marker=dict(size=7, symbol='diamond', color='#264653'),
            customdata=[f'${v:.2f}' if v else '—' for v in vpu_y2],
            hovertemplate='VPU: %{customdata}<extra></extra>'
        ))

    # ── Anotaciones: total inversión encima de cada barra ────────────────────
    inv_annotations = []
    for i, m in enumerate(cost_months):
        total_v = inv_total_real_by_month[i]
        if total_v > 0:
            lbl = f'${total_v/1_000_000:.1f}M' if total_v >= 1_000_000 else f'${total_v/1_000:.0f}K'
            bar_top_mm = sum(to_m([inv_oc_ucr_by_month[i], inv_pom_by_month[i], inv_others_by_month[i]]))
            inv_annotations.append(dict(
                x=x_labels[i], y=bar_top_mm,
                text=f'<b>{lbl}</b>', showarrow=False,
                yanchor='bottom', yshift=4, xanchor='center',
                font=dict(size=9, color='#333333')
            ))

    has_y2 = any(v is not None for v in cpa_blend_y2) or any(v is not None for v in vpu_y2)
    max_inv_mm = max((v/1_000_000 for v in inv_total_real_by_month if v), default=1)

    fig.update_layout(
        barmode='stack',
        height=330,
        plot_bgcolor='white', paper_bgcolor='white',
        title_text='Inversión & Performance por Grupo de Canal (USD)',
        title_font=dict(size=13, color='#0d1f3c'),
        hovermode='x unified',
        # Misma leyenda que la gráfica NR corp (traceorder='reversed')
        legend=dict(orientation='h', y=-0.22, font_size=10,
                    traceorder='reversed', xanchor='left', x=0),
        margin=dict(l=55, r=70, t=50, b=85),
        uniformtext=dict(minsize=9, mode='hide'),
        yaxis=dict(
            title=dict(text='Inversión (M USD)', font=dict(size=10)),
            tickprefix='$', ticksuffix='M', tickformat=',.1f',
            range=[0, round(max_inv_mm * 1.18, 1)],
            showgrid=True, gridcolor='#eeeeee', tickfont_size=10, zeroline=False
        ),
        yaxis2=dict(
            title=dict(text='VPU / CPA (USD)', font=dict(size=10, color='#333333')),
            side='right', overlaying='y',
            showgrid=False, tickfont=dict(size=10, color='#333333'),
            tickprefix='$', tickformat=',.1f'
        ) if has_y2 else {},
        xaxis=dict(tickfont_size=10, showgrid=False),
        annotations=inv_annotations
    )
    return json.loads(fig.to_json())


# ── Tabla Performance Corp (pestaña Performance_vista_Corp) ──────────────────

def build_perf_corp_table_html(data):
    """Tabla de métricas de performance usando hierarchy_nr_corp_detail (4 niveles colapsables).

    Combina tres fuentes de datos ya procesadas:
      · perf_corp_data_by_node   → N+R, Inversión, VPU, ROA (de build_perf_corp_data)
      · plan_nr_corp_by_node     → Plan N+R corp (de load_plan_corp)
      · monthly_nr_corp_by_node  → N+R real corp (de process_nr_corp)

    Filas por nodo (la fila header siempre se muestra; el resto solo si hay datos):
      1.  HEADER         — nombre canal + toggle ▶ (data-corp-perf-node)
      2.  N+R            — N+R total real
      3.  ↳ N+R Paid     — solo si nr_perf_label definido
      4.  ↳ N+R Free     — solo si nr_perf_label definido
      5.  ↳ N+R Gest.    — solo si hay Gest Others > 0
      6.  Share N+R      — % del total mensual
      7.  Inv. Total     — resaltada; "—" si sin inversión
      8.  ↳ Plan Inv.    — solo si plan_inv_label definido
      9.  ↳ vs Plan Inv. — solo si Plan Inv.
      10. CPA Blend.     — resaltada; "—" si sin inversión
      11. ↳ Plan CPA     — solo si plan_inv+plan_nr disponibles
      12. ↳ vs Plan CPA  — solo si Plan CPA
      13. ↳ CPA Paid     — solo si nr_perf_label definido
      14. VPU Pred 90D   — resaltada; "—" si sin VPU
      15. ↳ Plan VPU     — derivado: plan_valor / plan_nr
      16. ↳ vs Plan VPU  — solo si Plan VPU
      17. ↳ Valor Pred   — solo si nr_perf_label definido
      18. ↳ Plan Valor   — solo si plan_valor_label definido
      19. ↳ vs Plan Valor— solo si Plan Valor
      20. ROAs           — solo si roa disponible

    Colapso: data-corp-perf-node/parent/toggle (separados de data-corp-* mensual).
    JS: toggleCorpPerfNode() / collapseCorpPerfNode() en template_dashboard.html.
    """
    HIERARCHY_NR_CORP          = data['HIERARCHY_NR_CORP']           # hierarchy_nr_corp_detail
    months                     = data['months']
    perf_corp_data_by_node     = data.get('perf_corp_data_by_node',   {})
    monthly_nr_corp_by_node    = data['monthly_nr_corp_by_node']
    plan_nr_corp_by_node       = data.get('plan_nr_corp_by_node',     {})

    # Lookup id → nodo (ignorar entradas sin id como _doc)
    node_by_id_for_perf_corp   = {c['id']: c for c in HIERARCHY_NR_CORP if 'id' in c}

    # Total N+R corp por mes — denominador para Share N+R
    total_nr_corp_by_month     = monthly_nr_corp_by_node.get('corp_total', {})

    # ── Estilos por nivel (idénticos a tabla NR corp) ─────────────────────────
    PERF_CORP_LEVEL_BG      = {'grand': '#f0f4fa', 'sub1': '#ffffff', 'sub2': '#ffffff', 'medio': '#ffffff'}
    PERF_CORP_LEVEL_TXT     = {'grand': '#0d1f3c', 'sub1': '#0d1f3c', 'sub2': '#1a3562', 'medio': '#333333'}
    PERF_CORP_LEVEL_WT      = {'grand': '700',     'sub1': '700',     'sub2': '500',     'medio': '400'}
    PERF_CORP_SUBROW_BG     = {'grand': '#e8edf5', 'sub1': '#f5f6f8', 'sub2': '#f5f6f8', 'medio': '#f5f6f8'}
    PERF_CORP_SUBROW_TXT    = {'grand': '#4a6080',  'sub1': '#6b7a99',  'sub2': '#6b7a99',  'medio': '#888888'}
    # Sub-filas resaltadas (Inv. Total, CPA Blend., VPU Pred)
    HL_BG  = '#f0f4fa'
    HL_TXT = '#1a3562'
    HL_WT  = '600'
    # Sub-filas de Plan (fondo crema)
    PLAN_BG  = '#fdf9ec'
    PLAN_TXT = '#5a4a10'

    # ── Helpers de formato ────────────────────────────────────────────────────

    def fmt_usd_perf_corp(value):
        """Inversión en USD — None → '—'."""
        if value is None: return '<span style="color:#aaa">—</span>'
        if abs(value) >= 1_000_000: return f'${value/1_000_000:.2f}M'
        if abs(value) >= 1_000:     return f'${value/1_000:.1f}K'
        return f'${value:,.0f}'

    def fmt_cpa_perf_corp(value):
        """CPA en USD — None → '—'."""
        if value is None: return '<span style="color:#aaa">—</span>'
        return f'${value:.2f}'

    def fmt_vpu_perf_corp(value):
        """VPU en USD por usuario — 0 o None → '—'."""
        if not value: return '<span style="color:#aaa">—</span>'
        return f'${value:,.2f}'

    def fmt_roas_perf_corp(value):
        """ROAs — None o 0 → '—'."""
        if not value: return '<span style="color:#aaa">—</span>'
        return f'{value:.1f}x'

    def fmt_mom_perf_corp(current_val, prev_val):
        """MoM % = (actual - prev) / |prev|. Verde si sube, rojo si baja. '—' si no hay prev."""
        if prev_val is None or prev_val == 0:
            return '<span style="color:#aaa">—</span>'
        pct   = (current_val - prev_val) / abs(prev_val)
        color = '#0d7a3e' if pct >= 0 else '#c5221f'
        arrow = '▲' if pct >= 0 else '▼'
        return f'<span style="color:{color};font-weight:600">{arrow} {abs(pct)*100:.1f}%</span>'

    def fmt_pct_perf_corp(actual, reference, is_dark_bg):
        """% desviación (actual - ref) / ref — con flecha de color."""
        if reference is None or reference == 0:
            return '<span style="color:#aaa">—</span>'
        pct    = (actual - reference) / abs(reference)
        pos_c  = '#0d7a3e' if not is_dark_bg else '#81c995'
        neg_c  = '#c5221f' if not is_dark_bg else '#f28b82'
        arrow  = '▲' if pct >= 0 else '▼'
        color  = pos_c if pct >= 0 else neg_c
        return f'<span style="color:{color};font-weight:600">{arrow} {abs(pct)*100:.1f}%</span>'

    def cell_dash():
        return '<span style="color:#aaa">—</span>'

    # ── Función recursiva de renderizado por nodo ─────────────────────────────

    def render_perf_corp_node(node_id, parent_id_for_attr, hidden_by_default):
        """Genera todas las filas de performance para un nodo + llama recursivamente a sus hijos.

        Usa perf_corp_data_by_node[node_id] para métricas de rendimiento.
        Si el nodo no tiene entrada en perf_corp_data_by_node → todas las métricas "—".
        Solo muestra Plan/vs Plan cuando los datos de plan están disponibles para ese nodo.
        """
        node = node_by_id_for_perf_corp.get(node_id)
        if not node:
            return ''

        level    = node.get('level', 'medio')
        label    = node['label']
        indent   = node.get('indent', 0)
        color    = node.get('color', '#888888')
        children = [cid for cid in node.get('children', []) if cid in node_by_id_for_perf_corp]

        # Datos de performance para este nodo (puede ser {} si no hay mapping)
        node_perf_months = perf_corp_data_by_node.get(node_id, {})
        node_has_perf    = bool(node_perf_months)

        # Estilos
        bg      = PERF_CORP_LEVEL_BG.get(level, '#ffffff')
        txt     = PERF_CORP_LEVEL_TXT.get(level, '#333333')
        wt      = PERF_CORP_LEVEL_WT.get(level, '400')
        sub_bg  = PERF_CORP_SUBROW_BG.get(level, '#f5f6f8')
        sub_txt = PERF_CORP_SUBROW_TXT.get(level, '#888888')

        pad_px     = indent * 14 + 10
        sub_pad_px = (indent + 1) * 14 + 10
        bw         = '3px' if level in ('grand', 'sub1') else '2px'
        bt         = 'border-top:1px solid #e0e4ed;' if level in ('sub1', 'grand') else ''

        hdr_s  = f'{bt}background:{bg};color:{txt};font-weight:{wt};border-left:{bw} solid {color}'
        sm_s   = f'background:{sub_bg};color:{sub_txt};font-size:10.5px;border-left:{bw} solid {color}'
        hl_s   = f'background:{HL_BG};color:{HL_TXT};font-weight:{HL_WT};font-size:10.5px;border-left:{bw} solid {color}'
        pl_s   = f'background:{PLAN_BG};color:{PLAN_TXT};font-size:10px;font-style:italic;border-left:{bw} solid {color}'
        vs_s   = f'background:{PLAN_BG};font-size:10px;border-left:{bw} solid {color}'

        hidden_attr = ' style="display:none"' if hidden_by_default else ''
        parent_attr = f' data-corp-perf-parent="{parent_id_for_attr}"' if parent_id_for_attr else ''

        # Toggle ▶ para nodos con hijos; bullet ● para hojas
        if children:
            toggle_html = (f'<button onclick="toggleCorpPerfNode(\'{node_id}\')" '
                           f'data-corp-perf-toggle="{node_id}" '
                           f'style="background:none;border:none;cursor:pointer;color:{color};'
                           f'font-size:10px;margin-right:4px;padding:0;font-weight:700">▶</button>')
        else:
            toggle_html = f'<span style="display:inline-block;width:18px;color:{color};font-size:9px">●</span>'

        rows = ''

        # ── Fila 1: HEADER ────────────────────────────────────────────────────
        rows += f'<tr{parent_attr}{hidden_attr} data-corp-perf-node="{node_id}">'
        rows += f'<td class="lbl-col" style="padding-left:{pad_px}px;{hdr_s}">{toggle_html}{label}</td>'
        for m in months:
            rows += f'<td style="background:{bg}" data-month="{m}"></td>'
        rows += '</tr>'

        # ── Calcular métricas por mes ─────────────────────────────────────────
        # Preparar listas por mes para evitar repetición
        def get_month_data(m):
            return node_perf_months.get(m, {}) if node_has_perf else {}

        # ── Fila 2: N+R ───────────────────────────────────────────────────────
        rows += f'<tr{parent_attr}{hidden_attr}>'
        rows += f'<td class="lbl-col" style="padding-left:{sub_pad_px}px;{sm_s}">N+R</td>'
        for m in months:
            md = get_month_data(m)
            nr = md.get('actual_nr_total', 0) or monthly_nr_corp_by_node.get(node_id, {}).get(m, 0)
            rows += f'<td style="{sm_s}" data-month="{m}">{fmt_val(nr) if nr else "—"}</td>'
        rows += '</tr>'

        # ── Fila N+R vs MoM ──────────────────────────────────────────────────────
        rows += f'<tr{parent_attr}{hidden_attr}>'
        rows += f'<td class="lbl-col" style="padding-left:{sub_pad_px}px;{sm_s};font-style:italic">↳ vs MoM</td>'
        for i, m in enumerate(months):
            cur_nr  = monthly_nr_corp_by_node.get(node_id, {}).get(m, 0) or 0
            prev_nr = monthly_nr_corp_by_node.get(node_id, {}).get(months[i-1], 0) if i > 0 else None
            rows += f'<td style="{sm_s}" data-month="{m}">{fmt_mom_perf_corp(cur_nr, prev_nr)}</td>'
        rows += '</tr>'

        # ── Filas 3-4: ↳ Plan N+R + ↳ vs Plan N+R ───────────────────────────────
        # plan_nr_for_node viene de plan_nr_corp_by_node[node_id] (load_plan_corp, hierarchy_PLAN_Corp)
        any_has_plan_nr = any(get_month_data(m).get('plan_nr_for_node') for m in months)
        if any_has_plan_nr:
            rows += f'<tr{parent_attr}{hidden_attr}>'
            rows += f'<td class="lbl-col" style="padding-left:{sub_pad_px}px;{pl_s}">↳ Plan N+R</td>'
            for m in months:
                plan_nr_val = get_month_data(m).get('plan_nr_for_node')
                rows += f'<td style="{pl_s}" data-month="{m}">{fmt_val(plan_nr_val) if plan_nr_val and plan_nr_val > 0 else cell_dash()}</td>'
            rows += '</tr>'
            rows += f'<tr{parent_attr}{hidden_attr}>'
            rows += f'<td class="lbl-col" style="padding-left:{sub_pad_px}px;{vs_s};font-style:italic">↳ vs Plan N+R</td>'
            for m in months:
                md          = get_month_data(m)
                actual_nr_m = md.get('actual_nr_total', 0) or monthly_nr_corp_by_node.get(node_id, {}).get(m, 0)
                plan_nr_m   = md.get('plan_nr_for_node')
                rows += f'<td style="{vs_s}" data-month="{m}">{fmt_pct_perf_corp(actual_nr_m, plan_nr_m, False)}</td>'
            rows += '</tr>'

        # Verificar si hay datos de performance (nr_paid, etc.) para mostrar sub-filas
        any_has_nr_paid = any((get_month_data(m).get('actual_nr_paid') or 0) > 0 for m in months)

        # ── Fila 3: ↳ N+R Paid ────────────────────────────────────────────────
        if node_has_perf and any_has_nr_paid:
            rows += f'<tr{parent_attr}{hidden_attr}>'
            rows += f'<td class="lbl-col" style="padding-left:{sub_pad_px}px;{sm_s}">↳ N+R Paid</td>'
            for m in months:
                md = get_month_data(m)
                v  = md.get('actual_nr_paid', 0)
                rows += f'<td style="{sm_s}" data-month="{m}">{fmt_val(v) if v else "—"}</td>'
            rows += '</tr>'

            # ── Fila 4: ↳ N+R Free ────────────────────────────────────────────
            rows += f'<tr{parent_attr}{hidden_attr}>'
            rows += f'<td class="lbl-col" style="padding-left:{sub_pad_px}px;{sm_s}">↳ N+R Free</td>'
            for m in months:
                md    = get_month_data(m)
                nr_t  = md.get('actual_nr_total', 0) or monthly_nr_corp_by_node.get(node_id, {}).get(m, 0)
                paid  = md.get('actual_nr_paid', 0) or 0
                go    = md.get('actual_nr_go',   0) or 0
                free  = max(0, nr_t - paid - go)
                rows += f'<td style="{sm_s}" data-month="{m}">{fmt_val(free) if free else "—"}</td>'
            rows += '</tr>'

            # ── Fila 5: ↳ N+R Gest. Others (condicional) ─────────────────────
            any_has_go = any((get_month_data(m).get('actual_nr_go') or 0) > 0 for m in months)
            if any_has_go:
                rows += f'<tr{parent_attr}{hidden_attr}>'
                rows += f'<td class="lbl-col" style="padding-left:{sub_pad_px}px;{sm_s}">↳ N+R Gest. Others</td>'
                for m in months:
                    v = get_month_data(m).get('actual_nr_go', 0)
                    rows += f'<td style="{sm_s}" data-month="{m}">{fmt_val(v) if v else "—"}</td>'
                rows += '</tr>'

        # ── Fila 6: Share N+R ─────────────────────────────────────────────────
        rows += f'<tr{parent_attr}{hidden_attr}>'
        rows += f'<td class="lbl-col" style="padding-left:{sub_pad_px}px;{sm_s}">Share N+R</td>'
        for m in months:
            nr_node  = monthly_nr_corp_by_node.get(node_id, {}).get(m, 0) or 0
            nr_total = total_nr_corp_by_month.get(m, 0) or 0
            share    = f'{nr_node/nr_total*100:.1f}%' if nr_total > 0 else '—'
            rows += f'<td style="{sm_s}" data-month="{m}">{share}</td>'
        rows += '</tr>'

        # ── Fila 7: Inv. Total (resaltada) ────────────────────────────────────
        any_has_inv = any(get_month_data(m).get('actual_inv_total') is not None for m in months)
        rows += f'<tr{parent_attr}{hidden_attr}>'
        rows += f'<td class="lbl-col" style="padding-left:{sub_pad_px}px;{hl_s}">Inv. Total (USD)</td>'
        for m in months:
            inv = get_month_data(m).get('actual_inv_total') if any_has_inv else None
            rows += f'<td style="{hl_s}" data-month="{m}">{fmt_usd_perf_corp(inv)}</td>'
        rows += '</tr>'

        # ── Desglose Inversión: Canal / Incentivos / Mantika (TC §71) ────────────
        # Mismo breakdown que Corp centralizado (NR-INAPP-INVERSION-ALL).
        # Solo se muestra si hay datos de inversión (any_has_inv).
        if any_has_inv:
            for inv_key, inv_lbl in [('actual_inv_canal',     '↳ Inv. Canal'),
                                      ('actual_inv_incentivo', '↳ Inv. Incentivos'),
                                      ('actual_inv_mantika',   '↳ Inv. Mantika')]:
                # Solo mostrar la fila si hay al menos un valor > 0
                vals_for_row = [get_month_data(m).get(inv_key) for m in months]
                if any((v or 0) > 0 for v in vals_for_row):
                    rows += f'<tr{parent_attr}{hidden_attr}>'
                    rows += f'<td class="lbl-col" style="padding-left:{sub_pad_px}px;{sm_s}">{inv_lbl}</td>'
                    for m in months:
                        v = get_month_data(m).get(inv_key)
                        rows += f'<td style="{sm_s}" data-month="{m}">{fmt_usd_perf_corp(v)}</td>'
                    rows += '</tr>'

        # ── Inv. Total vs MoM ────────────────────────────────────────────────────
        rows += f'<tr{parent_attr}{hidden_attr}>'
        rows += f'<td class="lbl-col" style="padding-left:{sub_pad_px}px;{hl_s};font-style:italic">↳ vs MoM</td>'
        for i, m in enumerate(months):
            cur_inv  = get_month_data(m).get('actual_inv_total')
            prev_inv = get_month_data(months[i-1]).get('actual_inv_total') if i > 0 else None
            rows += f'<td style="{hl_s}" data-month="{m}">{fmt_mom_perf_corp(cur_inv or 0, prev_inv)}</td>'
        rows += '</tr>'

        # ── Filas 8-9: Plan Inv. + vs Plan Inv. ──────────────────────────────
        any_has_plan_inv = any(get_month_data(m).get('plan_inv_for_node') for m in months)
        if any_has_plan_inv:
            rows += f'<tr{parent_attr}{hidden_attr}>'
            rows += f'<td class="lbl-col" style="padding-left:{sub_pad_px}px;{pl_s}">↳ Plan Inv.</td>'
            for m in months:
                pv = get_month_data(m).get('plan_inv_for_node')
                rows += f'<td style="{pl_s}" data-month="{m}">{fmt_usd_perf_corp(pv)}</td>'
            rows += '</tr>'
            rows += f'<tr{parent_attr}{hidden_attr}>'
            rows += f'<td class="lbl-col" style="padding-left:{sub_pad_px}px;{vs_s};font-style:italic">↳ vs Plan Inv.</td>'
            for m in months:
                act_inv  = get_month_data(m).get('actual_inv_total')
                plan_inv = get_month_data(m).get('plan_inv_for_node')
                rows += f'<td style="{vs_s}" data-month="{m}">{fmt_pct_perf_corp(act_inv or 0, plan_inv, False)}</td>'
            rows += '</tr>'

        # ── Fila 10: CPA Blend. (resaltada) ──────────────────────────────────
        rows += f'<tr{parent_attr}{hidden_attr}>'
        rows += f'<td class="lbl-col" style="padding-left:{sub_pad_px}px;{hl_s}">CPA Blend.</td>'
        for m in months:
            md  = get_month_data(m)
            inv = md.get('actual_inv_total') or 0
            nr  = md.get('actual_nr_total',  0) or monthly_nr_corp_by_node.get(node_id, {}).get(m, 0)
            cpa = round(inv / nr, 2) if inv and nr > 0 else None
            rows += f'<td style="{hl_s}" data-month="{m}">{fmt_cpa_perf_corp(cpa)}</td>'
        rows += '</tr>'

        # ── CPA Blend vs MoM ─────────────────────────────────────────────────────
        rows += f'<tr{parent_attr}{hidden_attr}>'
        rows += f'<td class="lbl-col" style="padding-left:{sub_pad_px}px;{hl_s};font-style:italic">↳ vs MoM</td>'
        for i, m in enumerate(months):
            def _cpa(month_key):
                md_  = get_month_data(month_key)
                inv_ = md_.get('actual_inv_total') or 0
                nr_  = md_.get('actual_nr_total', 0) or monthly_nr_corp_by_node.get(node_id, {}).get(month_key, 0)
                return round(inv_ / nr_, 2) if inv_ and nr_ > 0 else None
            cur_cpa  = _cpa(m)
            prev_cpa = _cpa(months[i-1]) if i > 0 else None
            rows += f'<td style="{hl_s}" data-month="{m}">{fmt_mom_perf_corp(cur_cpa or 0, prev_cpa)}</td>'
        rows += '</tr>'

        # ── Filas 11-13: Plan CPA + vs Plan CPA + CPA Paid ───────────────────
        any_has_plan_cpa = any(
            get_month_data(m).get('plan_inv_for_node') and get_month_data(m).get('plan_nr_for_node')
            for m in months)
        if any_has_plan_cpa:
            rows += f'<tr{parent_attr}{hidden_attr}>'
            rows += f'<td class="lbl-col" style="padding-left:{sub_pad_px}px;{pl_s}">↳ Plan CPA</td>'
            for m in months:
                md       = get_month_data(m)
                pi       = md.get('plan_inv_for_node') or 0
                pn       = md.get('plan_nr_for_node')  or 0
                plan_cpa = round(pi / pn, 2) if pi and pn > 0 else None
                rows += f'<td style="{pl_s}" data-month="{m}">{fmt_cpa_perf_corp(plan_cpa)}</td>'
            rows += '</tr>'
            rows += f'<tr{parent_attr}{hidden_attr}>'
            rows += f'<td class="lbl-col" style="padding-left:{sub_pad_px}px;{vs_s};font-style:italic">↳ vs Plan CPA</td>'
            for m in months:
                md       = get_month_data(m)
                inv      = md.get('actual_inv_total') or 0
                nr       = md.get('actual_nr_total', 0) or monthly_nr_corp_by_node.get(node_id, {}).get(m, 0)
                pi       = md.get('plan_inv_for_node') or 0
                pn       = md.get('plan_nr_for_node')  or 0
                act_cpa  = round(inv / nr,  2) if inv and nr  > 0 else None
                plan_cpa = round(pi  / pn,  2) if pi  and pn  > 0 else None
                rows += f'<td style="{vs_s}" data-month="{m}">{fmt_pct_perf_corp(act_cpa or 0, plan_cpa, False)}</td>'
            rows += '</tr>'

        if node_has_perf and any_has_nr_paid:
            rows += f'<tr{parent_attr}{hidden_attr}>'
            rows += f'<td class="lbl-col" style="padding-left:{sub_pad_px}px;{sm_s}">↳ CPA Paid</td>'
            for m in months:
                md   = get_month_data(m)
                inv  = md.get('actual_inv_total') or 0
                paid = md.get('actual_nr_paid', 0) or 0
                cpa  = round(inv / paid, 2) if inv and paid > 0 else None
                rows += f'<td style="{sm_s}" data-month="{m}">{fmt_cpa_perf_corp(cpa)}</td>'
            rows += '</tr>'

        # ── Fila 14: VPU Pred 90D (resaltada) ────────────────────────────────
        any_has_vpu = any((get_month_data(m).get('actual_vpu_prod') or 0) > 0 for m in months)
        rows += f'<tr{parent_attr}{hidden_attr}>'
        rows += f'<td class="lbl-col" style="padding-left:{sub_pad_px}px;{hl_s}">VPU Pred 90D</td>'
        for m in months:
            md      = get_month_data(m)
            vpu_p   = md.get('actual_vpu_prod', 0) or 0
            nr_tot  = md.get('actual_nr_total', 0) or monthly_nr_corp_by_node.get(node_id, {}).get(m, 0)
            vpu_per_user = round(vpu_p / nr_tot, 2) if nr_tot > 0 and vpu_p > 0 else None
            rows += f'<td style="{hl_s}" data-month="{m}">{fmt_vpu_perf_corp(vpu_per_user)}</td>'
        rows += '</tr>'

        # ── Filas 15-19: Plan VPU, vs Plan VPU, Valor Pred, Plan Valor, vs Plan Valor ─
        any_has_plan_valor = any(get_month_data(m).get('plan_valor_for_node') for m in months)
        if any_has_plan_valor:
            rows += f'<tr{parent_attr}{hidden_attr}>'
            rows += f'<td class="lbl-col" style="padding-left:{sub_pad_px}px;{pl_s}">↳ Plan VPU</td>'
            for m in months:
                md     = get_month_data(m)
                pv_val = md.get('plan_valor_for_node') or 0
                pv_nr  = md.get('plan_nr_for_node')    or 0
                plan_vpu = round(pv_val / pv_nr, 2) if pv_val and pv_nr > 0 else None
                rows += f'<td style="{pl_s}" data-month="{m}">{"$"+f"{plan_vpu:,.2f}" if plan_vpu else "—"}</td>'
            rows += '</tr>'
            rows += f'<tr{parent_attr}{hidden_attr}>'
            rows += f'<td class="lbl-col" style="padding-left:{sub_pad_px}px;{vs_s};font-style:italic">↳ vs Plan VPU</td>'
            for m in months:
                md       = get_month_data(m)
                vpu_p    = md.get('actual_vpu_prod', 0) or 0
                nr_tot   = md.get('actual_nr_total', 0) or monthly_nr_corp_by_node.get(node_id, {}).get(m, 0)
                pv_val   = md.get('plan_valor_for_node') or 0
                pv_nr    = md.get('plan_nr_for_node')    or 0
                act_vpu  = round(vpu_p  / nr_tot, 2) if nr_tot > 0 and vpu_p > 0 else None
                plan_vpu = round(pv_val / pv_nr,  2) if pv_val  and pv_nr  > 0 else None
                rows += f'<td style="{vs_s}" data-month="{m}">{fmt_pct_perf_corp(act_vpu or 0, plan_vpu, False)}</td>'
            rows += '</tr>'

        if any_has_vpu:
            rows += f'<tr{parent_attr}{hidden_attr}>'
            rows += f'<td class="lbl-col" style="padding-left:{sub_pad_px}px;{sm_s}">↳ Valor Pred 90D</td>'
            for m in months:
                v = get_month_data(m).get('actual_vpu_prod', 0) or None
                rows += f'<td style="{sm_s}" data-month="{m}">{fmt_usd_perf_corp(v)}</td>'
            rows += '</tr>'
            # ── Valor Pred 90D vs MoM ─────────────────────────────────────────
            rows += f'<tr{parent_attr}{hidden_attr}>'
            rows += f'<td class="lbl-col" style="padding-left:{sub_pad_px}px;{sm_s};font-style:italic">↳ vs MoM</td>'
            for i, m in enumerate(months):
                cur_v  = get_month_data(m).get('actual_vpu_prod', 0) or 0
                prev_v = get_month_data(months[i-1]).get('actual_vpu_prod', 0) if i > 0 else None
                rows += f'<td style="{sm_s}" data-month="{m}">{fmt_mom_perf_corp(cur_v, prev_v)}</td>'
            rows += '</tr>'

        if any_has_plan_valor:
            rows += f'<tr{parent_attr}{hidden_attr}>'
            rows += f'<td class="lbl-col" style="padding-left:{sub_pad_px}px;{pl_s}">↳ Plan Valor</td>'
            for m in months:
                pv = get_month_data(m).get('plan_valor_for_node')
                rows += f'<td style="{pl_s}" data-month="{m}">{fmt_usd_perf_corp(pv)}</td>'
            rows += '</tr>'
            rows += f'<tr{parent_attr}{hidden_attr}>'
            rows += f'<td class="lbl-col" style="padding-left:{sub_pad_px}px;{vs_s};font-style:italic">↳ vs Plan Valor</td>'
            for m in months:
                md     = get_month_data(m)
                actual = md.get('actual_vpu_prod', 0) or 0
                plan   = md.get('plan_valor_for_node') or 0
                rows += f'<td style="{vs_s}" data-month="{m}">{fmt_pct_perf_corp(actual, plan, False)}</td>'
            rows += '</tr>'

        # ── Fila 20: ROAs ──────────────────────────────────────────────────────
        any_has_roa = any((get_month_data(m).get('actual_roa_num') or 0) > 0 for m in months)
        if any_has_roa:
            roa_lbl_s = f'{sm_s};font-weight:600;color:#2d5986'
            roa_val_s = f'{sm_s};font-weight:600;color:#2d5986'
            rows += f'<tr{parent_attr}{hidden_attr}>'
            rows += f'<td class="lbl-col" style="padding-left:{sub_pad_px}px;{roa_lbl_s}">ROAs</td>'
            for m in months:
                md   = get_month_data(m)
                roa  = md.get('actual_roa_num', 0) or 0
                inv  = md.get('actual_inv_total') or 0
                roas = round(roa / inv, 2) if inv > 0 and roa > 0 else None
                rows += f'<td style="{roa_val_s}" data-month="{m}">{fmt_roas_perf_corp(roas)}</td>'
            rows += '</tr>'

        # ── ROAs vs MoM ───────────────────────────────────────────────────────────
        if any_has_roa:
            rows += f'<tr{parent_attr}{hidden_attr}>'
            rows += f'<td class="lbl-col" style="padding-left:{sub_pad_px}px;{roa_val_s};font-style:italic">↳ vs MoM</td>'
            for i, m in enumerate(months):
                def _roas(month_key):
                    md_  = get_month_data(month_key)
                    roa_ = md_.get('actual_roa_num', 0) or 0
                    inv_ = md_.get('actual_inv_total') or 0
                    return round(roa_ / inv_, 2) if inv_ > 0 and roa_ > 0 else None
                cur_roas  = _roas(m)
                prev_roas = _roas(months[i-1]) if i > 0 else None
                rows += f'<td style="{roa_val_s}" data-month="{m}">{fmt_mom_perf_corp(cur_roas or 0, prev_roas)}</td>'
            rows += '</tr>'

        # ── Hijos recursivos (ocultos por defecto) ────────────────────────────
        for child_id in children:
            rows += render_perf_corp_node(child_id, parent_id_for_attr=node_id, hidden_by_default=True)

        return rows

    # ── Construir tabla HTML ──────────────────────────────────────────────────
    h  = '<div class="table-scroll"><table class="mom-tbl perf-corp-tbl">'
    h += '<thead><tr><th class="lbl-col">Canal / Métrica</th>'
    for m in months:
        h += f'<th data-month="{m}">{fmt_month(m)}</th>'
    h += '</tr></thead><tbody>'

    # Grupos primero (children of corp_total, sin corp_total mismo)
    root_node_for_perf_corp = node_by_id_for_perf_corp.get('corp_total', {})
    group_ids_in_order      = [cid for cid in root_node_for_perf_corp.get('children', [])
                                if cid in node_by_id_for_perf_corp]
    for group_node_id in group_ids_in_order:
        h += render_perf_corp_node(group_node_id, parent_id_for_attr=None, hidden_by_default=False)

    # Separador + Total al fondo
    h += (f'<tr><td colspan="{len(months)+1}" '
          'style="border-top:2px solid #2d5986;padding:0;height:4px;background:#f0f4fa"></td></tr>')
    h += render_perf_corp_node('corp_total', parent_id_for_attr=None, hidden_by_default=False)

    h += '</tbody></table></div>'
    return h


# ── Gráfica NR Mensual (pestaña NR Mensual) ───────────────────

def build_mom_bar(data, plan_nr, plan_lines_data):
    """Barras apiladas N+R por canal leaf + línea CPA + líneas de plan (pestaña NR Mensual).
    Itera HIERARCHY_NR. plan_nr/plan_lines_data vienen del Excel.
    """
    HIERARCHY_NR  = data['HIERARCHY_NR']
    months        = data['months']
    monthly_nr    = data['monthly_nr']
    monthly_cost  = data['monthly_cost']

    leaf_nodes = sorted([c for c in HIERARCHY_NR if c.get('is_leaf')],
                        key=lambda c: sum(monthly_nr[c['label']].get(m, 0) for m in months), reverse=True)
    x_labels = [fmt_month(m) for m in months]

    fig = go.Figure()

    for c in leaf_nodes:
        y_vals = [monthly_nr[c['label']].get(m, 0) / 1000 for m in months]
        cust   = [fmt_val(monthly_nr[c['label']].get(m, 0)) for m in months]
        fig.add_trace(go.Bar(
            name=c['label'], x=x_labels, y=y_vals, customdata=cust,
            hovertemplate='%{fullData.name}: %{customdata}<extra></extra>',
            marker_color=c['color']
        ))

    cpa_y = []
    for m in months:
        nr   = monthly_nr['Total N+R'].get(m, 0)
        cost = monthly_cost['Total N+R'].get(m, 0)
        cpa_y.append(round(cost / nr, 4) if nr > 0 else None)

    has_cpr = any(v is not None and v > 0 for v in cpa_y)
    if has_cpr:
        fig.add_trace(go.Scatter(
            name='CPA (USD)', x=x_labels, y=cpa_y,
            customdata=[f'${v:.2f}' if v is not None else '—' for v in cpa_y],
            hovertemplate='CPA: %{customdata}<extra></extra>',
            yaxis='y2', mode='lines+markers',
            line=dict(color='#E9C46A', width=2.5, dash='dash'),
            marker=dict(size=6, symbol='diamond', color='#E9C46A')
        ))

    plan_total = plan_nr.get('Total N+R', {})
    plan_y = [plan_total.get(m, None) for m in months]
    plan_y = [v / 1000 if v else None for v in plan_y]
    if any(v is not None for v in plan_y):
        fig.add_trace(go.Scatter(
            name='Plan Oficial', x=x_labels, y=plan_y,
            customdata=[fmt_val(v * 1000) if v else '—' for v in plan_y],
            hovertemplate='Plan: %{customdata}<extra></extra>',
            mode='lines+markers',
            line=dict(color='#C00000', width=2, dash='dot'),
            marker=dict(size=7, symbol='circle', color='#C00000')
        ))

    # Sub-líneas de plan (ocultas; JS las muestra al filtrar el canal padre)
    for c in HIERARCHY_NR:
        if 'plan_lines' not in c:
            continue
        for pl in c['plan_lines']:
            if pl.get('no_chart'):
                continue
            pl_lbl     = pl['label']
            pl_monthly = plan_lines_data.get(c['label'], {}).get(pl_lbl, {})
            pl_y       = [pl_monthly.get(m, 0) / 1000 if pl_monthly.get(m, 0) > 0 else None for m in months]
            if not any(v is not None for v in pl_y):
                continue
            fig.add_trace(go.Scatter(
                name=pl_lbl, x=x_labels, y=pl_y,
                customdata=[fmt_val(int(v * 1000)) if v else '—' for v in pl_y],
                hovertemplate=f'{pl_lbl}: %{{customdata}}<extra></extra>',
                mode='lines+markers',
                line=dict(color=pl['color'], width=1.5, dash='dashdot'),
                marker=dict(size=5, symbol='square', color=pl['color']),
                visible=False
            ))

    fig.update_layout(
        plot_bgcolor='white', paper_bgcolor='white',
        barmode='stack', height=380, hovermode='x unified',
        title_text='N+R por Canal — Acumulado Mensual',
        legend=dict(orientation='h', y=-0.18, font_size=10),
        margin=dict(l=60, r=70, t=50, b=90),
        yaxis=dict(tickformat=',.0f', ticksuffix='K', showgrid=False),
        yaxis2=dict(title='CPA (USD)', side='right', overlaying='y', showgrid=False, tickformat='$,.2f') if has_cpr else {},
        xaxis=dict(tickfont_size=10)
    )
    return json.loads(fig.to_json())


# ── Tabla Performance (pestaña Performance) ───────────────────

def build_perf_table_html(data):
    """Tabla con métricas de performance por canal/mes.
    Itera HIERARCHY_NR (filas de canales) cruzando datos de N+R y Costos.
    Punto de cruce N+R ↔ Costos: get_inv() mapea 'Total N+R' → 'Total Inversión'.
    Incluye sub-filas Plan / vs Plan para Inv. Total, CPA Blend., VPU Pred 90D y Valor Pred 90D.
    """
    HIERARCHY_NR        = data['HIERARCHY_NR']
    months              = data['months']
    monthly_nr          = data['monthly_nr']
    monthly_inv_total   = data['monthly_inv_total']     # INV total por canal/mes
    monthly_inv_canal   = data.get('monthly_inv_canal',     {})  # Inv. Canal (media / envío)
    monthly_inv_incentivo = data.get('monthly_inv_incentivo', {})  # Inv. Incentivos (CONSUMIDO)
    monthly_inv_mantika = data.get('monthly_inv_mantika',   {})  # Inv. Mantika (plataforma OC)
    perf_nr_paid        = data['perf_nr_paid']
    perf_nr_go          = data['perf_nr_go']
    perf_vpu_prod       = data['perf_vpu_prod']
    perf_roa_num        = data['perf_roa_num']
    plan_nr             = data.get('plan_nr',    {})
    plan_valor          = data.get('plan_valor', {})
    plan_inv            = data.get('plan_inv',   {})

    def fmt_pct_plan(actual, plan):
        """Formatea variación vs plan como porcentaje con flecha de color."""
        if plan is None or plan == 0: return '<span style="color:#aaa">—</span>'
        pct = (actual - plan) / abs(plan)
        col = '#0d7a3e' if pct >= 0 else '#c5221f'
        arrow = '▲' if pct >= 0 else '▼'
        return f'<span style="color:{col};font-weight:600">{arrow} {abs(pct)*100:.1f}%</span>'

    # ── Paleta clean: nivel jerárquico = acento izquierdo + fondo suave ──
    # (row_bg, row_txt, row_weight, border_accent, sep_top)
    LVL = {
        'grand': ('#eef1f8', '#0d1f3c', '700', '#1a2744', True),
        'sub1':  ('#f3f6fb', '#1e3a6e', '600', '#2d5986', True),
        'sub2':  ('#f8fafd', '#2a4d80', '500', '#4a7ab5', False),
        'leaf':  ('#ffffff', '#333333', '500', '#b8cce0', False),
    }
    # Sub-métricas normales
    SM_LBL = 'font-size:10.5px;color:#888;font-style:normal'
    SM_VAL = 'font-size:10.5px;color:#556'
    # Sub-métricas resaltadas (Inv. Total, CPA Blend., VPU Pred 90D)
    HL_LBL = 'font-size:10.5px;color:#1a3562;font-weight:600;font-style:normal;background:#f0f4fa'
    HL_VAL = 'font-size:10.5px;color:#1a3562;font-weight:600;background:#f0f4fa'
    # Sub-métricas de Plan (fondo crema claro, itálica)
    PL_BG  = '#fdf9ec'
    PL_LBL_BASE = f'font-size:10px;color:#6b5a1e;font-style:italic;background:{PL_BG}'
    PL_VAL_BASE = f'font-size:10px;color:#5a4a10;background:{PL_BG}'
    VS_VAL_BASE = f'font-size:10px;background:{PL_BG}'

    def get_inv(label):
        key = 'Total Inversión' if label == 'Total N+R' else label
        return monthly_inv_total.get(key, {})

    h  = '<div class="table-scroll"><table class="mom-tbl perf-tbl"><thead><tr>'
    h += '<th class="lbl-col">Canal / Métrica</th>'
    for m in months:
        h += f'<th data-month="{m}">{fmt_month(m)}</th>'
    h += '</tr></thead><tbody>'

    for c in HIERARCHY_NR:
        label  = c['label']
        indent = c['indent']
        bg, txt, wt, _lvl_border, sep = LVL[c['level']]
        border = c['color']  # color del canal definido en channels_config.json
        pad     = f'padding-left:{indent*16+12}px'
        sub_pad = f'padding-left:{(indent+1)*16+12}px'
        inv_map = get_inv(label)

        hdr_lbl_s = f'background:{bg};color:{txt};font-weight:{wt};border-left:3px solid {border};font-size:11px'
        nr_lbl_s  = f'background:{bg};color:{txt};font-weight:{wt};border-left:3px solid {border}'
        nr_val_s  = f'background:{bg};color:{txt};font-weight:{wt}'
        sep_cls   = ' class="perf-sep"' if sep else ''

        # ── Row A: Cabecera de canal (solo nombre, sin valores) ──
        h += f'<tr{sep_cls} data-canal="{label}"><td class="lbl-col" style="{pad};{hdr_lbl_s}">{label}</td>'
        for m in months:
            h += f'<td style="background:{bg}" data-month="{m}"></td>'
        h += '</tr>'

        # ── Row B: N+R Total (primer dato del canal) ─────────────
        h += f'<tr data-canal="{label}"><td class="lbl-col" style="{sub_pad};{nr_lbl_s}">N+R Total</td>'
        for m in months:
            v = monthly_nr[label].get(m, 0)
            h += f'<td style="{nr_val_s}" data-month="{m}">{fmt_val(v) if v else "—"}</td>'
        h += '</tr>'

        # ── N+R Paid ─────────────────────────────────────────────
        h += f'<tr data-canal="{label}"><td class="lbl-col" style="{sub_pad};{SM_LBL};background:{bg};border-left:3px solid {border}">↳ N+R Paid</td>'
        for m in months:
            v = perf_nr_paid[label].get(m, 0)
            h += f'<td style="{SM_VAL};background:{bg}" data-month="{m}">{fmt_val(v) if v else "—"}</td>'
        h += '</tr>'

        # ── N+R Free ──────────────────────────────────────────────
        h += f'<tr data-canal="{label}"><td class="lbl-col" style="{sub_pad};{SM_LBL};background:{bg};border-left:3px solid {border}">↳ N+R Free</td>'
        for m in months:
            nr   = monthly_nr[label].get(m, 0) or 0
            paid = perf_nr_paid[label].get(m, 0) or 0
            go   = perf_nr_go[label].get(m, 0)   or 0
            v    = max(0, nr - paid - go)
            h += f'<td style="{SM_VAL};background:{bg}" data-month="{m}">{fmt_val(v) if v else "—"}</td>'
        h += '</tr>'

        # ── N+R Gest. Others (condicional, estilo normal) ─────────
        if any(perf_nr_go[label].get(m, 0) for m in months):
            h += f'<tr data-canal="{label}"><td class="lbl-col" style="{sub_pad};{SM_LBL};background:{bg};border-left:3px solid {border}">↳ N+R Gest. Others</td>'
            for m in months:
                v = perf_nr_go[label].get(m, 0)
                h += f'<td style="{SM_VAL};background:{bg}" data-month="{m}">{fmt_val(v) if v else "—"}</td>'
            h += '</tr>'

        # ── Inversión Total real (resaltada) — TC §71 ─────────────────────────────────────
        h += f'<tr data-canal="{label}"><td class="lbl-col" style="{sub_pad};{HL_LBL};border-left:3px solid {border}">Inv. Total (USD)</td>'
        for m in months:
            h += f'<td style="{HL_VAL}" data-month="{m}">{fmt_usd(inv_map.get(m))}</td>'
        h += '</tr>'

        # ── Desglose Inversión: Canal / Incentivos / Mantika ───────────────────────────
        # Mismo breakdown que Corp centralizado (NR-INAPP-INVERSION-ALL).
        # Canal     = costo de envío / media (COSTO_ENVIO_USD para OC, COST_USD para Paid)
        # Incentivos = presupuesto de cashback/incentivo (CONSUMIDO_USD para OC)
        # Mantika   = fee de plataforma Mantika (solo OC, ≈0 para Paid)
        canal_map     = (monthly_inv_canal.get('Total Inversión' if label == 'Total N+R' else label) or {})
        incentivo_map = (monthly_inv_incentivo.get('Total Inversión' if label == 'Total N+R' else label) or {})
        mantika_map   = (monthly_inv_mantika.get('Total Inversión' if label == 'Total N+R' else label) or {})
        has_breakdown = any(
            (canal_map.get(m) or 0) + (incentivo_map.get(m) or 0) + (mantika_map.get(m) or 0) > 0
            for m in months
        )
        if has_breakdown:
            h += f'<tr data-canal="{label}"><td class="lbl-col" style="{sub_pad};{SM_LBL};border-left:2px solid {border}">↳ Inv. Canal</td>'
            for m in months:
                h += f'<td style="{SM_VAL}" data-month="{m}">{fmt_usd(canal_map.get(m)) if canal_map.get(m) else "—"}</td>'
            h += '</tr>'
            h += f'<tr data-canal="{label}"><td class="lbl-col" style="{sub_pad};{SM_LBL};border-left:2px solid {border}">↳ Inv. Incentivos</td>'
            for m in months:
                h += f'<td style="{SM_VAL}" data-month="{m}">{fmt_usd(incentivo_map.get(m)) if incentivo_map.get(m) else "—"}</td>'
            h += '</tr>'
            h += f'<tr data-canal="{label}"><td class="lbl-col" style="{sub_pad};{SM_LBL};border-left:2px solid {border}">↳ Inv. Mantika</td>'
            for m in months:
                v = mantika_map.get(m)
                h += f'<td style="{SM_VAL}" data-month="{m}">{fmt_usd(v) if v else "—"}</td>'
            h += '</tr>'

        # ── Plan Inv. + vs Plan Inv. — fuente: Excel plan_inv → data['plan_inv'] ──────────
        # Solo se muestran para canales con fila de inversión en el Excel
        # (Total N+R, OC+UCR, OC ACT, POM TOTAL, MGM TOTAL — ver plan_row_inv en channels_config.json)
        plan_inv_by_month = plan_inv.get(label, {})  # {} si el canal no tiene plan de inversión
        plan_row_style    = f'{PL_LBL_BASE};border-left:3px solid {border}'
        if any(plan_inv_by_month.get(m) for m in months):
            h += f'<tr data-canal="{label}"><td class="lbl-col" style="{sub_pad};{plan_row_style}">↳ Plan Inv.</td>'
            for m in months:
                plan_inv_val = plan_inv_by_month.get(m)
                h += f'<td style="{PL_VAL_BASE}" data-month="{m}">{fmt_usd(plan_inv_val) if plan_inv_val else "—"}</td>'
            h += '</tr>'
            h += f'<tr data-canal="{label}"><td class="lbl-col" style="{sub_pad};{plan_row_style}">↳ vs Plan Inv.</td>'
            for m in months:
                plan_inv_val   = plan_inv_by_month.get(m)
                actual_inv_val = inv_map.get(m) or 0
                h += f'<td style="{VS_VAL_BASE}" data-month="{m}">{fmt_pct_plan(actual_inv_val, plan_inv_val)}</td>'
            h += '</tr>'

        # ── CPA Blend real (resaltada) — derivado: actual_inv / actual_nr_total ──────────
        h += f'<tr data-canal="{label}"><td class="lbl-col" style="{sub_pad};{HL_LBL};border-left:3px solid {border}">CPA Blend.</td>'
        for m in months:
            actual_inv = inv_map.get(m) or 0
            actual_nr  = monthly_nr[label].get(m, 0) or 0
            actual_cpa_blend = round(actual_inv / actual_nr, 2) if actual_inv and actual_nr > 0 else None
            h += f'<td style="{HL_VAL}" data-month="{m}">{fmt_cpa(actual_cpa_blend)}</td>'
        h += '</tr>'

        # ── Plan CPA + vs Plan CPA — derivado: plan_inv / plan_nr ────────────────────────
        # Solo canales con ambos plan_inv y plan_nr en el Excel pueden calcular Plan CPA
        plan_nr_by_month = plan_nr.get(label, {})  # {} si el canal no tiene plan N+R
        if any(plan_inv_by_month.get(m) and plan_nr_by_month.get(m) for m in months):
            h += f'<tr data-canal="{label}"><td class="lbl-col" style="{sub_pad};{plan_row_style}">↳ Plan CPA</td>'
            for m in months:
                plan_inv_val = plan_inv_by_month.get(m) or 0
                plan_nr_val  = plan_nr_by_month.get(m)  or 0
                plan_cpa_blend = round(plan_inv_val / plan_nr_val, 2) if plan_inv_val and plan_nr_val > 0 else None
                h += f'<td style="{PL_VAL_BASE}" data-month="{m}">{fmt_cpa(plan_cpa_blend)}</td>'
            h += '</tr>'
            h += f'<tr data-canal="{label}"><td class="lbl-col" style="{sub_pad};{plan_row_style}">↳ vs Plan CPA</td>'
            for m in months:
                plan_inv_val = plan_inv_by_month.get(m) or 0
                plan_nr_val  = plan_nr_by_month.get(m)  or 0
                plan_cpa_blend = round(plan_inv_val / plan_nr_val, 2) if plan_inv_val and plan_nr_val > 0 else None
                actual_inv = inv_map.get(m) or 0
                actual_nr  = monthly_nr[label].get(m, 0) or 0
                actual_cpa_blend = round(actual_inv / actual_nr, 2) if actual_inv and actual_nr > 0 else None
                h += f'<td style="{VS_VAL_BASE}" data-month="{m}">{fmt_pct_plan(actual_cpa_blend, plan_cpa_blend) if actual_cpa_blend is not None else "—"}</td>'
            h += '</tr>'

        # ── CPA Paid real (normal) — derivado: actual_inv / actual_nr_paid ──────────────
        h += f'<tr data-canal="{label}"><td class="lbl-col" style="{sub_pad};{SM_LBL};background:#fff;border-left:3px solid {border}">↳ CPA Paid</td>'
        for m in months:
            actual_inv     = inv_map.get(m) or 0
            actual_nr_paid = perf_nr_paid[label].get(m, 0) or 0
            actual_cpa_paid = round(actual_inv / actual_nr_paid, 2) if actual_inv and actual_nr_paid > 0 else None
            h += f'<td style="{SM_VAL}" data-month="{m}">{fmt_cpa(actual_cpa_paid)}</td>'
        h += '</tr>'

        # ── VPU Pred 90D real (resaltada) — derivado: perf_vpu_prod / actual_nr_total ────
        # perf_vpu_prod viene de DAILY_HISTORICO: SUM(VALUE_MKT_PREDICTION_90D_NR_USERS)
        # VPU = ese total pre-multiplicado dividido por N+R Total (ver metrics_logic.md §4)
        h += f'<tr data-canal="{label}"><td class="lbl-col" style="{sub_pad};{HL_LBL};border-left:3px solid {border}">VPU Pred 90D</td>'
        for m in months:
            actual_nr_total      = monthly_nr[label].get(m, 0) or 0
            actual_valor_total   = perf_vpu_prod[label].get(m, 0) or 0  # pre-multiplicado por NR
            actual_vpu_per_user  = round(actual_valor_total / actual_nr_total, 2) if actual_nr_total > 0 else 0
            h += f'<td style="{HL_VAL}" data-month="{m}">{"$"+f"{actual_vpu_per_user:,.2f}" if actual_vpu_per_user > 0 else "—"}</td>'
        h += '</tr>'

        # ── VPU Paid (sub-fila) — VPU sobre usuarios PAGADOS únicamente ────────────────────
        # VPU Paid = perf_roa_num[canal][mes] / perf_nr_paid[canal][mes]
        # Equivalente a la métrica "VPU Paid" del Corp tool.
        # Verificado: OC Apr-26 = $22.31 == Corp $22.30 (diff=0.00) ✅
        # perf_roa_num fuente: NR_INC_VALUE(FLAG_PAID='PAID') para OC; perf_vpu_prod para POM/MGM.
        if any(perf_nr_paid[label].get(m, 0) > 0 for m in months):
            h += f'<tr data-canal="{label}"><td class="lbl-col" style="{sub_pad};{SM_LBL};background:#fff;border-left:3px solid {border}">↳ VPU Paid</td>'
            for m in months:
                nr_paid_m   = perf_nr_paid[label].get(m, 0) or 0
                roa_val_m   = perf_roa_num[label].get(m, 0) or 0
                vpu_paid_v  = round(roa_val_m / nr_paid_m, 2) if nr_paid_m > 0 and roa_val_m > 0 else None
                h += f'<td style="{SM_VAL}" data-month="{m}">{"$"+f"{vpu_paid_v:,.2f}" if vpu_paid_v else "—"}</td>'
            h += '</tr>'

        # ── Plan VPU + vs Plan VPU — derivado: plan_valor / plan_nr ──────────────────────
        # Plan VPU NO se lee directamente del Excel; se deriva dividiendo plan_valor / plan_nr
        # Esto evita problemas de aditividad: el VPU no es sumable entre canales
        plan_valor_by_month = plan_valor.get(label, {})  # {} si el canal no tiene plan de valor
        if any(plan_valor_by_month.get(m) and plan_nr_by_month.get(m) for m in months):
            h += f'<tr data-canal="{label}"><td class="lbl-col" style="{sub_pad};{plan_row_style}">↳ Plan VPU</td>'
            for m in months:
                plan_valor_val = plan_valor_by_month.get(m) or 0
                plan_nr_val    = plan_nr_by_month.get(m)    or 0
                plan_vpu_per_user = round(plan_valor_val / plan_nr_val, 2) if plan_valor_val and plan_nr_val > 0 else None
                h += f'<td style="{PL_VAL_BASE}" data-month="{m}">{"$"+f"{plan_vpu_per_user:,.2f}" if plan_vpu_per_user else "—"}</td>'
            h += '</tr>'
            h += f'<tr data-canal="{label}"><td class="lbl-col" style="{sub_pad};{plan_row_style}">↳ vs Plan VPU</td>'
            for m in months:
                plan_valor_val = plan_valor_by_month.get(m) or 0
                plan_nr_val    = plan_nr_by_month.get(m)    or 0
                plan_vpu_per_user  = round(plan_valor_val / plan_nr_val, 2) if plan_valor_val and plan_nr_val > 0 else None
                actual_nr_total    = monthly_nr[label].get(m, 0) or 0
                actual_valor_total = perf_vpu_prod[label].get(m, 0) or 0
                actual_vpu_per_user = round(actual_valor_total / actual_nr_total, 2) if actual_nr_total > 0 and actual_valor_total > 0 else None
                h += f'<td style="{VS_VAL_BASE}" data-month="{m}">{fmt_pct_plan(actual_vpu_per_user, plan_vpu_per_user) if actual_vpu_per_user is not None else "—"}</td>'
            h += '</tr>'

        # ── Valor Pred 90D real (normal) — fuente directa: perf_vpu_prod ─────────────────
        # perf_vpu_prod = SUM(VALUE_MKT_PREDICTION_90D_NR_USERS) — ya es valor total, no por usuario
        h += f'<tr data-canal="{label}"><td class="lbl-col" style="{sub_pad};{SM_LBL};background:#fff;border-left:3px solid {border}">↳ Valor Pred 90D</td>'
        for m in months:
            actual_valor_total = perf_vpu_prod[label].get(m, 0) or None
            h += f'<td style="{SM_VAL}" data-month="{m}">{fmt_usd(actual_valor_total)}</td>'
        h += '</tr>'

        # ── Plan Valor + vs Plan Valor — fuente: Excel plan_valor → data['plan_valor'] ───
        # plan_valor es aditivo (a diferencia de VPU): se puede leer directamente del Excel
        # Para Ucrania y POM TOTAL se propaga bottom-up en load_plan() (ver gen_dashboard_v1.py)
        if any(plan_valor_by_month.get(m) for m in months):
            h += f'<tr data-canal="{label}"><td class="lbl-col" style="{sub_pad};{plan_row_style}">↳ Plan Valor</td>'
            for m in months:
                plan_valor_val = plan_valor_by_month.get(m)
                h += f'<td style="{PL_VAL_BASE}" data-month="{m}">{fmt_usd(plan_valor_val) if plan_valor_val else "—"}</td>'
            h += '</tr>'
            h += f'<tr data-canal="{label}"><td class="lbl-col" style="{sub_pad};{plan_row_style}">↳ vs Plan Valor</td>'
            for m in months:
                plan_valor_val     = plan_valor_by_month.get(m) or 0
                actual_valor_total = perf_vpu_prod[label].get(m, 0) or 0
                h += f'<td style="{VS_VAL_BASE}" data-month="{m}">{fmt_pct_plan(actual_valor_total, plan_valor_val) if actual_valor_total else "—"}</td>'
            h += '</tr>'

        # ── ROAs ──────────────────────────────────────────────────
        roa_lbl = f'{SM_LBL};font-weight:600;color:#2d5986;background:#fff;border-left:3px solid {border}'
        roa_val = f'{SM_VAL};font-weight:600;color:#2d5986'
        h += f'<tr data-canal="{label}"><td class="lbl-col" style="{sub_pad};{roa_lbl}">ROAs</td>'
        for m in months:
            inv = inv_map.get(m) or 0
            vp  = perf_roa_num[label].get(m, 0) or 0
            v   = round(vp / inv, 2) if inv > 0 and vp > 0 else None
            h += f'<td style="{roa_val}" data-month="{m}">{""+f"{v:.1f}"+"x" if v else "—"}</td>'
        h += '</tr>'

    h += '</tbody></table></div>'
    return h


# ── Gráfica Performance (pestaña Performance) ─────────────────

def build_perf_bar(data):
    """Barras apiladas Inversión por canal leaf (HIERARCHY_C) + líneas CPA Blend, ROAs y Plan.
    Cruce N+R ↔ Costos: CPA usa monthly_nr['Total N+R'] + monthly_inv_total['Total Inversión'].
    ROAs usa perf_vpu_prod (VPU pre-multiplicado de DAILY_HISTORICO) + perf_nr_paid.
    Plan: plan_inv['Total N+R'] → línea Plan Inv. (y1); plan_inv/plan_nr → línea Plan CPA (y2).
    Los datos de plan vienen de data['plan_inv'] y data['plan_nr'], cargados en gen_dashboard_v1.py.
    """
    HIERARCHY_C       = data['HIERARCHY_C']
    cost_months       = data['cost_months']
    monthly_inv_total = data['monthly_inv_total']
    monthly_nr        = data['monthly_nr']
    perf_vpu_prod     = data['perf_vpu_prod']
    perf_nr_paid      = data['perf_nr_paid']
    # Plan — indexados por label de HIERARCHY_NR; 'Total N+R' corresponde al total del gráfico
    plan_inv = data.get('plan_inv', {})
    plan_nr  = data.get('plan_nr',  {})

    leaf_nodes = sorted(
        [c for c in HIERARCHY_C if c.get('is_leaf') and not c.get('no_cost')],
        key=lambda c: sum(monthly_inv_total[c['label']].get(m, 0) or 0 for m in cost_months),
        reverse=True
    )
    x_labels = [fmt_month(m) for m in cost_months]

    fig = go.Figure()

    # Barras apiladas: un trace por canal leaf con inversión real
    for c in leaf_nodes:
        y_vals = [(monthly_inv_total[c['label']].get(m) or 0) / 1_000_000 for m in cost_months]
        cust   = [fmt_usd(monthly_inv_total[c['label']].get(m)) for m in cost_months]
        fig.add_trace(go.Bar(
            name=c['label'], x=x_labels, y=y_vals, customdata=cust,
            hovertemplate='%{fullData.name}: %{customdata}<extra></extra>',
            marker_color=c['color']
        ))

    # CPA Blended = Inversión Total / N+R Total (cruce HIERARCHY_C ↔ HIERARCHY_NR)
    cpa_blend_y = []
    for m in cost_months:
        inv = monthly_inv_total.get('Total Inversión', {}).get(m) or 0
        nr  = monthly_nr.get('Total N+R', {}).get(m) or 0
        cpa_blend_y.append(round(inv / nr, 2) if inv and nr > 0 else None)

    # ROAs = perf_roa_num / Inversión  (numerador varía por canal: COSTOS para UCR/OC, HISTORICO para POM/MGM)
    perf_roa_num = data['perf_roa_num']
    roas_y = []
    for m in cost_months:
        inv = monthly_inv_total.get('Total Inversión', {}).get(m) or 0
        vp  = perf_roa_num.get('Total N+R', {}).get(m) or 0
        roas_y.append(round(vp / inv, 2) if inv > 0 and vp > 0 else None)

    # ── Plan Inv. (y1) — línea sobre las barras de inversión real ────────────────────────
    # plan_inv['Total N+R'] contiene el plan de inversión total por mes (leído del Excel)
    plan_inv_total_by_month = plan_inv.get('Total N+R', {})
    plan_inv_y_mm = [plan_inv_total_by_month.get(m) for m in cost_months]
    plan_inv_y_mm = [v / 1_000_000 if v else None for v in plan_inv_y_mm]  # escala M USD

    has_y2 = any(v is not None for v in cpa_blend_y) or any(v is not None for v in roas_y)

    if any(v is not None for v in cpa_blend_y):
        fig.add_trace(go.Scatter(
            name='CPA Blend.', x=x_labels, y=cpa_blend_y,
            yaxis='y2', mode='lines+markers',
            line=dict(color='#E9C46A', width=2.5, dash='dot'),
            marker=dict(size=7, symbol='circle', color='#E9C46A'),
            customdata=[f'${v:.2f}' if v is not None else '—' for v in cpa_blend_y],
            hovertemplate='CPA Blend.: %{customdata}<extra></extra>'
        ))

    if any(v is not None for v in roas_y):
        fig.add_trace(go.Scatter(
            name='ROAs', x=x_labels, y=roas_y,
            yaxis='y2', mode='lines+markers',
            line=dict(color='#555555', width=2.5, dash='dash'),
            marker=dict(size=7, symbol='diamond', color='#555555'),
            customdata=[f'{v:.2f}x' if v is not None else '—' for v in roas_y],
            hovertemplate='ROAs: %{customdata}<extra></extra>'
        ))

    # ── Trace: Plan Inv. (y1) ─────────────────────────────────────────────────────────────
    if any(v is not None for v in plan_inv_y_mm):
        fig.add_trace(go.Scatter(
            name='Plan Inv.', x=x_labels, y=plan_inv_y_mm,
            customdata=[fmt_usd(v * 1_000_000) if v else '—' for v in plan_inv_y_mm],
            hovertemplate='Plan Inv.: %{customdata}<extra></extra>',
            mode='lines+markers',
            line=dict(color='#C00000', width=2, dash='dot'),
            marker=dict(size=7, symbol='circle', color='#C00000')
        ))

    # Anotaciones: total inversión por mes (actualizadas dinámicamente en JS por canal)
    def fmt_ann_inv(v):
        if v >= 1_000_000: return f'${v/1_000_000:.1f}M'
        if v >= 1_000:     return f'${v/1_000:.0f}K'
        return f'${v:.0f}'

    annotations = [dict(
        x=fmt_month(m),
        y=(monthly_inv_total.get('Total Inversión', {}).get(m) or 0) / 1_000_000,
        text=fmt_ann_inv(monthly_inv_total.get('Total Inversión', {}).get(m) or 0),
        showarrow=False, yanchor='bottom', yshift=5,
        font=dict(size=9, color='#333')
    ) for m in cost_months]

    fig.update_layout(
        plot_bgcolor='white', paper_bgcolor='white',
        barmode='stack', height=380, hovermode='x unified',
        title_text='Inversión & Performance por Canal (USD)',
        legend=dict(orientation='h', y=-0.18, font_size=10),
        margin=dict(l=60, r=70, t=50, b=90),
        yaxis=dict(tickprefix='$', tickformat=',.1f', ticksuffix='M', showgrid=False),
        yaxis2=dict(title='CPA (USD) / ROAs', side='right', overlaying='y', showgrid=False) if has_y2 else {},
        xaxis=dict(tickfont_size=10),
        annotations=annotations
    )
    return json.loads(fig.to_json())


# ══════════════════════════════════════════════════════════════════════════════
# build_comms_oc_table_html — Pestaña Comms_OC
# ══════════════════════════════════════════════════════════════════════════════

def build_comms_oc_table_html(data):
    """Genera la tabla HTML de la pestaña Comms_OC.

    §75 History.md — Migración a BT_OC_DASHBOARD_ALL_CAMPAIGNS_NR + NR_ACQUISITION.
    Granularidad: 1 fila por (COMMUNICATION_ID, SENT_DATE, CANAL, FUENTE_TABLA).

    27 columnas visibles:
     1  Mes, 2 Fecha Envío, 3 Fuente, 4 Canal, 5 Channel,
     6  Strategy, 7 Substrategy, 8 Clasif, 9 Notif.Type, 10 Team,
     11 Biz Line, 12 Seg.Canal, 13 Campaña,
     14 Sents, 15 CONTROL, 16 ARRIVED, 17 OPEN, 18 CLICK, 19 Open%,
     20 User Inc, 21 Value Inc, 22 NR_TOTAL_Test, 23 NR_TOTAL_Control, 24 %Canibalizac.,
     24 Flag Paid, 25 Consumido USD, 26 Envio USD, 27 Mantika USD

    Eliminados vs legacy: M_CVR_TEST, M_LIFT, TPN_INC, TPV_INC,
      NOTIFICATION_TITLE, NOTIFICATION_TEXT, APP→CHANNEL, TYPE_NAME→CLASIF_CAMPAIGNS,
      CREATE, SHOWN, BLACKLIST/BLOCKED/BOUNCE/SPAM, PRINTS_RE/TAPS_RE columns.
    """

    all_comms_oc_records = data.get('comms_oc_records', [])

    if not all_comms_oc_records:
        return (
            '<div style="padding:24px;color:#888;font-size:13px">'
            'Sin datos de comunicaciones OC. '
            'Ejecuta: <code>python scripts/refresh_comms_oc_cache.py --full</code>'
            '</div>'
        )

    def safe_float_or_none(raw_value):
        if raw_value is None:
            return None
        try:
            f = float(raw_value)
            return None if f != f else f
        except (TypeError, ValueError):
            return None

    def safe_int_or_dash(raw_value):
        f = safe_float_or_none(raw_value)
        if f is None:
            return '<span style="color:#bbb">—</span>'
        return f'{int(round(f)):,}'

    def fmt_pct_or_dash(float_0_to_1):
        if float_0_to_1 is None:
            return '<span style="color:#bbb">—</span>'
        return f'{float_0_to_1 * 100:.1f}%'

    def fmt_ratio_color(float_ratio):
        """RATIO_CANIBALIZACION: % con color (>50%=rojo, 20-50%=naranja, <20%=verde)."""
        if float_ratio is None:
            return '<span style="color:#bbb">—</span>'
        pct = float_ratio * 100
        col = '#c5221f' if pct > 50 else ('#e37400' if pct > 20 else '#0d7a3e')
        return f'<span style="color:{col}">{pct:.1f}%</span>'

    def fmt_user_inc_color(float_val):
        """USER_INC con color verde/rojo."""
        if float_val is None:
            return '<span style="color:#bbb">—</span>'
        v    = int(round(float_val))
        col  = '#0d7a3e' if v >= 0 else '#c5221f'
        sign = '+' if v >= 0 else ''
        return f'<span style="color:{col};font-weight:600">{sign}{v:,}</span>'

    def fmt_usd_or_dash(float_val):
        f = safe_float_or_none(float_val)
        if f is None or f == 0:
            return '<span style="color:#bbb">—</span>'
        return f'${f:,.0f}'

    def trunc(text, max_chars, tooltip=True, max_tooltip=200):
        if not text or str(text) in ('None', 'nan', ''):
            return '<span style="color:#bbb">—</span>'
        s = str(text)
        if len(s) <= max_chars:
            return s
        short = s[:max_chars] + '…'
        if tooltip:
            tt = s[:max_tooltip] + ('…' if len(s) > max_tooltip else '')
            return f'<span title="{tt.replace(chr(34), "&quot;")}">{short}</span>'
        return short

    def escape_attr(raw_value):
        if not raw_value or str(raw_value) in ('None', 'nan', '—', ''):
            return ''
        return (str(raw_value)
                .replace('&', '&amp;')
                .replace('"', '&quot;')
                .replace('<', '&lt;')
                .replace('>', '&gt;'))

    sorted_records = sorted(
        all_comms_oc_records,
        key=lambda r: (str(r.get('MONTH_ID', '')), str(r.get('SENT_DATE', ''))),
        reverse=True
    )

    TH     = 'class="coc-th"'
    TD     = 'class="coc-td"'
    TD_NUM = 'class="coc-td coc-num"'

    # ── Clasificación Corp/FM sub-canal (§83 — tabla oficial del equipo) ─────────
    def _classify_corp_subcanal(strategy: str, notif_type: str, team: str,
                                 substrategy: str = '', clasif_campaigns: str = '',
                                 campaign_name: str = '') -> str:
        """Sub-canal vista Corp — tabla oficial + regla UCR por nombre de campaña."""
        s   = (_cs(strategy)         or '').upper()
        nt  = (_cs(notif_type)       or '').upper()
        t   = (_cs(team)             or '').upper()
        ss  = (_cs(substrategy)      or '').upper()
        cl  = (_cs(clasif_campaigns) or '').upper()
        ucr = 'UCR' in (_cs(campaign_name) or '').upper()
        # P0: SELLERS team con |USER_INC| > 250 — incluida pero marcada aparte
        if 'SELLERS' in t:
            return 'OTHERS_SELLERS'
        # P1: UCR PRD (strategy + team)
        if s in ('UCRANIA', 'ACQUISITION') and any(x in t for x in ('CREDITS', 'OTHERS')):
            return 'UCR PRD'
        # P2: nombre de campaña contiene UCR — ADHOC → ADHOC, otros → E&G
        if ucr and 'ADHOC' in t:
            return 'OWN CHANNELS ADHOC'
        if ucr and any(x in t for x in ('OTHERS', 'INDIVIDUALS', 'CREDITS')):
            return 'UCRANIA E&G'
        # P2b: ACQUISITION + SUBSTRATEGY UCRANIA/NEW/STOCK + ADHOC → OWN CHANNELS ADHOC
        # (CLASIF=SIN FILTROS en la tabla — la regla aplica independiente de CLASIF)
        if s == 'ACQUISITION' and 'ADHOC' in t and any(x in ss for x in ('UCRANIA', 'NEW', 'STOCK')):
            return 'OWN CHANNELS ADHOC'
        # P3: ADHOC team — CLASIF distingue ADHOC vs RECURRING
        if 'ADHOC' in t:
            return 'OWN CHANNELS ADHOC' if cl == 'UCRANIA' else 'OWN CHANNELS RECURRING'
        # P4: UCRANIA → UCRANIA E&G
        if s == 'UCRANIA':
            return 'UCRANIA E&G'
        # P5: OTHERS + SUBSTRATEGY=OTHERS → RECURRING
        if s == 'OTHERS' and ss == 'OTHERS':
            return 'OWN CHANNELS RECURRING'
        # P6: ACTIVATION / RE-ACTIVATION → RECURRING
        if s in ('ACTIVATION', 'RE-ACTIVATION'):
            return 'OWN CHANNELS RECURRING'
        return 'NA'

    def _classify_medio_final(canal: str, channel: str, strategy: str,
                               substrategy: str, campaign_name: str,
                               flag_paid: str = '', experiment: str = '') -> str:
        """MEDIO_CLASIF_FINAL según tabla oficial:
        PUSH + PUSH APP MP + STRATEGY≠UCRANIA + SUBSTRAT≠UCRANIA
          + CAMPAIGN LIKE 'flows_communication%' + FLAG_PAID=FREE + EXPERIMENT contains EYG → JOURNEY
        Para todas las demás: mismo valor que CANAL.
        """
        c   = (_cs(canal)         or '').upper()
        ch  = (_cs(channel)       or '').upper()
        s   = (_cs(strategy)      or '').upper()
        ss  = (_cs(substrategy)   or '').upper()
        cn  = (_cs(campaign_name) or '').lower()
        fp  = (_cs(flag_paid)     or '').upper()
        exp = (_cs(experiment)    or '').upper()
        # Regla JOURNEY: PUSH APP MP + no UCRANIA + flows_communication + FREE + EYG experiment
        if (c == 'PUSH' and 'PUSH APP MP' in ch
                and s != 'UCRANIA' and ss != 'UCRANIA'
                and cn.startswith('flows_communication')
                and fp == 'FREE'
                and 'EYG' in exp):
            return 'JOURNEY'
        # Para todas las demás → mismo que Canal
        return canal or '—'

    def _classify_fm_subcanal(strategy: str, team: str, campaign_name: str = '') -> str:
        """Sub-canal vista FM — tabla oficial + regla UCR por nombre de campaña."""
        s   = (_cs(strategy)      or '').upper()
        t   = (_cs(team)          or '').upper()
        ucr = 'UCR' in (_cs(campaign_name) or '').upper()
        # P0: SELLERS team con |USER_INC| > 250 — incluida pero marcada aparte
        if 'SELLERS' in t:
            return 'OTHERS_SELLERS'
        # Nombre UCR — ADHOC/INDIVIDUALS → UCR GEST, OTHERS/CREDITS → UCR PRD
        if ucr and any(x in t for x in ('ADHOC', 'INDIVIDUALS')):
            return 'UCR GEST'
        if ucr and any(x in t for x in ('OTHERS', 'CREDITS')):
            return 'UCR PRD'
        # Reglas por strategy/team
        if s in ('UCRANIA', 'ACQUISITION') and any(x in t for x in ('CREDITS', 'OTHERS')):
            return 'UCR PRD'
        if s in ('UCRANIA', 'ACQUISITION') and any(x in t for x in ('ADHOC', 'INDIVIDUALS')):
            return 'UCR GEST'
        if s in ('ACTIVATION', 'OTHERS', 'RE-ACTIVATION'):
            return 'OC ACT'
        return 'NA'

    # ── Clasificación ENFOQUE desde nombre de campaña (§79) ──────────────────
    # Busca el código de estrategia como segmento entre guiones en el CAMPAIGN_NAME.
    # Orden de precedencia: primero los más específicos (3P, GTM, SS, TT, BP, IN).
    _ENFOQUE_RULES = [
        ('GTM',              'GTM'),
        ('SS',               'Seasonal'),
        ('3P',               'Promos c/Terceros'),
        ('TT',               'Testeos'),
        ('BP',               'Boost Productos'),
        ('IN',               'Informativas'),
    ]
    def _classify_enfoque(campaign_name: str) -> str:
        """Clasifica la campaña por ENFOQUE buscando -CODE- o -CODE al final."""
        name = (_cs(campaign_name) or '').upper()
        if not name:
            return '—'
        for code, label in _ENFOQUE_RULES:
            if f'-{code}-' in name or name.endswith(f'-{code}'):
                return label
        return '—'

    headers = [
        'Mes', 'Fecha Envío', 'Fuente',
        'Canal', 'Channel', 'Strategy', 'Substrategy',
        'Clasif', 'Notif. Type', 'Team', 'Biz Line', 'Seg. Canal',
        'Campaña', 'Enfoque', 'Experiment',
        'Corp Sub-canal', 'Corp Sub-canal Aux', 'FM Sub-canal', 'FM Sub-canal Aux', 'Medio Final',
        'Sents', 'CONTROL', 'ARRIVED', 'OPEN', 'CLICK',
        'Open%', 'User Inc', 'User Inc Adj', 'Value Inc',
        'NR_TOTAL_Test', 'NR_TOTAL_Control', '% Canibalizac.',
        'Entry Test (JNY)', 'Entry Ctrl (JNY)',
        'Flag Paid', 'Consumido USD', 'Envío USD', 'Mantika USD',
    ]

    # ── Pre-pasada §79: campañas que tienen AL MENOS UNA fila con funnel > 0 ──
    # Solo se usan para el filtro de ADHOC-INDIVIDUALS.
    # Si una campaña tiene TODAS las filas con funnel=0, no se filtra ninguna.
    def _funnel_nonzero(r):
        def _i(k): return int(safe_float_or_none(r.get(k)) or 0)
        return (_i('TOTAL_TEST') > 0 or _i('TOTAL_CONTROL') > 0
                or _i('TOTAL_ARRIVED') > 0 or _i('TOTAL_OPEN') > 0
                or _i('TOTAL_CLICK') > 0)

    _campaigns_with_real_data = {
        (r.get('CAMPAIGN_NAME_CLEAN') or r.get('CAMPAIGN_NAME') or '')
        for r in all_comms_oc_records
        if _funnel_nonzero(r)
    }

    html_output = (
        '<style id="css-comms-oc-tbl">'
        '.coc-th{background:#f0f3f8;color:#7a8499;font-size:9.5px;text-transform:uppercase;'
        'letter-spacing:.4px;font-weight:500;border-right:1px solid #e4e8f0;'
        'border-bottom:2px solid #d0d8e8;white-space:nowrap;padding:5px 6px;'
        'position:sticky;top:0;z-index:1}'
        '.coc-td{padding:4px 6px;font-size:10.5px;color:#333;'
        'border-bottom:1px solid #f2f4f8;white-space:nowrap;vertical-align:middle}'
        '.coc-td.coc-num{color:#444;text-align:right}'
        '</style>'
        '<div id="comms-oc-filters" style="margin-bottom:8px"></div>'
        '<div id="comms-oc-kpi-row" style="margin-bottom:4px"></div>'
        '<div style="overflow-x:auto;max-height:75vh;overflow-y:auto">'
        '<table style="border-collapse:collapse;width:max-content;min-width:100%;font-size:10.5px">'
        '<thead><tr>'
        + ''.join(f'<th {TH}>{h}</th>' for h in headers)
        + '</tr></thead><tbody>'
    )

    for record in sorted_records:
        month_id_yyyymm = str(record.get('MONTH_ID', ''))
        month_label     = fmt_month(month_id_yyyymm) if len(month_id_yyyymm) == 6 else month_id_yyyymm
        sent_date       = str(record.get('SENT_DATE', ''))[:10]

        fuente_val     = _cs(record.get('FUENTE_TABLA'))     or '—'
        canal_val      = _cs(record.get('CANAL'))           or '—'
        channel_val    = _cs(record.get('CHANNEL'))         or '—'
        strategy_val   = _cs(record.get('STRATEGY'))        or '—'
        substrat_val   = _cs(record.get('SUBSTRATEGY'))     or '—'
        clasif_val     = _cs(record.get('CLASIF_CAMPAIGNS')) or '—'
        notif_type_val = _cs(record.get('NOTIFICATION_TYPE')) or '—'
        team_val       = _cs(record.get('TEAM'))            or '—'
        biz_line_val   = _cs(record.get('BUSINESS_LINE'))   or '—'
        biz_seg_val    = _cs(record.get('BUSINESS_LINE_SEGMENT')) or '—'
        campaign_val   = _cs(record.get('CAMPAIGN_NAME_CLEAN')) or _cs(record.get('CAMPAIGN_NAME')) or '—'
        enfoque_val       = _classify_enfoque(campaign_val)
        experiment_val    = _cs(record.get('EXPERIMENT'))   or '—'
        corp_subcanal_aux_val = _classify_corp_subcanal(strategy_val, notif_type_val, team_val,
                                                       substrat_val, clasif_val, campaign_val)
        corp_subcanal_val     = 'OWN CHANNELS RECURRING' if corp_subcanal_aux_val == 'OTHERS_SELLERS' else corp_subcanal_aux_val
        fm_subcanal_aux_val   = _classify_fm_subcanal(strategy_val, team_val, campaign_val)
        fm_subcanal_val       = 'OC ACT' if fm_subcanal_aux_val == 'OTHERS_SELLERS' else fm_subcanal_aux_val
        medio_final_val   = _classify_medio_final(canal_val, channel_val, strategy_val,
                                                   substrat_val, campaign_val,
                                                   _cs(record.get('FLAG_PAID')),
                                                   _cs(record.get('EXPERIMENT')))

        ev_test    = record.get('TOTAL_TEST')
        ev_control = record.get('TOTAL_CONTROL')
        ev_arrived = record.get('TOTAL_ARRIVED')
        ev_open    = record.get('TOTAL_OPEN')
        ev_click   = record.get('TOTAL_CLICK')

        # Filtro de filas vacías §79: se aplica a una comm solo si:
        #   1. Esa fila tiene todo el funnel en 0
        #   2. El team es ADHOC-INDIVIDUALS (o similar)
        #   3. La misma campaña tiene al menos OTRA fila con datos reales
        # Condición 3 evita eliminar comms que genuinamente tienen 0 (ej: EMAIL sin open tracking)
        def _to_int(v): return int(safe_float_or_none(v) or 0)
        _all_funnel_zero = (_to_int(ev_test) == 0 and _to_int(ev_control) == 0
                            and _to_int(ev_arrived) == 0 and _to_int(ev_open) == 0
                            and _to_int(ev_click) == 0)
        _is_adhoc_ind = 'INDIVIDUAL' in (_cs(team_val) or '').upper()
        if _all_funnel_zero and _is_adhoc_ind and campaign_val in _campaigns_with_real_data:
            continue

        open_rate_val = safe_float_or_none(record.get('OPEN_RATE'))
        # Fallback §83: si ARRIVED=0 pero hay SENTS y OPEN, calcular OR = OPEN/SENTS
        # Aplica a campañas RE (Drawer, etc.) que no tienen ARRIVED en la fuente
        if (not open_rate_val or open_rate_val == 0.0):
            _op = float(record.get('TOTAL_OPEN') or 0)
            _sn = float(record.get('SENTS') or 0)
            _ar = float(record.get('TOTAL_ARRIVED') or 0)
            if _op > 0 and _sn > 0 and _ar == 0:
                open_rate_val = _op / _sn
        user_inc_val     = safe_float_or_none(record.get('USER_INC'))
        user_inc_adj_val = safe_float_or_none(record.get('USER_INC_CON_ADJUST'))
        value_inc_val    = safe_float_or_none(record.get('VALUE_INC'))
        absoluto_val    = safe_float_or_none(record.get('TOTAL_ABSOLUTO_NR'))
        control_nr_val  = safe_float_or_none(record.get('NR_TOTAL_CONTROL'))
        ratio_val       = safe_float_or_none(record.get('RATIO_CANIBALIZACION'))
        entry_test_val  = safe_float_or_none(record.get('ENTRY_TEST_JNY'))
        entry_ctrl_val  = safe_float_or_none(record.get('ENTRY_CONTROL_JNY'))
        _is_journey     = 'JOURNEY' in (_cs(canal_val) or '').upper()
        flag_paid_val = record.get('FLAG_PAID') or '—'
        consumido_val = safe_float_or_none(record.get('CONSUMIDO_USD'))
        envio_val     = safe_float_or_none(record.get('COSTO_ENVIO_USD'))
        mantika_val   = safe_float_or_none(record.get('COSTO_MANTIKA_USD'))

        da_user_inc     = user_inc_val     if user_inc_val     is not None else ''
        da_user_inc_adj = user_inc_adj_val if user_inc_adj_val is not None else ''
        da_value_inc    = value_inc_val    if value_inc_val    is not None else ''
        da_absoluto   = absoluto_val   if absoluto_val   is not None else ''
        da_control_nr = control_nr_val if control_nr_val is not None else ''
        da_ratio      = ratio_val      if ratio_val      is not None else ''
        da_open_rate = open_rate_val if open_rate_val is not None else ''
        da_test      = int(safe_float_or_none(ev_test)    or 0)
        da_arrived   = int(safe_float_or_none(ev_arrived) or 0)
        da_open      = int(safe_float_or_none(ev_open)    or 0)
        da_sents     = int(safe_float_or_none(record.get('SENTS')) or 0)

        html_output += (
            f'<tr data-month="{month_id_yyyymm}"'
            f' data-fecha="{sent_date}"'
            f' data-open-rate="{da_open_rate}"'
            f' data-user-inc="{da_user_inc}" data-user-inc-adj="{da_user_inc_adj}" data-value-inc="{da_value_inc}"'
            f' data-absoluto="{da_absoluto}" data-control-nr="{da_control_nr}" data-ratio="{da_ratio}"'
            f' data-test="{da_test}" data-arrived="{da_arrived}" data-open="{da_open}" data-sents="{da_sents}"'
            f' data-canal="{escape_attr(canal_val)}" data-strategy="{escape_attr(strategy_val)}"'
            f' data-substrat="{escape_attr(substrat_val)}" data-clasif="{escape_attr(clasif_val)}"'
            f' data-notiftype="{escape_attr(notif_type_val)}"'
            f' data-fuente="{escape_attr(fuente_val)}" data-team="{escape_attr(team_val)}"'
            f' data-campaign="{escape_attr(campaign_val)}"'
            f' data-enfoque="{escape_attr(enfoque_val)}"'
            f' data-experiment="{escape_attr(experiment_val)}"'
            f' data-corpsubcanal="{escape_attr(corp_subcanal_val)}"'
            f' data-corpsubcanalaux="{escape_attr(corp_subcanal_aux_val)}"'
            f' data-fmsubcanal="{escape_attr(fm_subcanal_val)}"'
            f' data-fmsubcanalaux="{escape_attr(fm_subcanal_aux_val)}"'
            f' data-mediofinal="{escape_attr(medio_final_val)}"'
            f' data-bl="{escape_attr(biz_line_val)}" data-bizseg="{escape_attr(biz_seg_val)}">'
            f'<td {TD}>{month_label}</td>'
            f'<td {TD}>{sent_date}</td>'
            f'<td {TD}>{trunc(fuente_val, 18)}</td>'
            f'<td {TD}>{trunc(canal_val, 20)}</td>'
            f'<td {TD}>{trunc(channel_val, 20)}</td>'
            f'<td {TD}>{trunc(strategy_val, 20)}</td>'
            f'<td {TD}>{trunc(substrat_val, 20)}</td>'
            f'<td {TD}>{trunc(clasif_val, 20)}</td>'
            f'<td {TD}>{trunc(notif_type_val, 15)}</td>'
            f'<td {TD}>{trunc(team_val, 20)}</td>'
            f'<td {TD}>{trunc(biz_line_val, 25)}</td>'
            f'<td {TD}>{trunc(biz_seg_val, 25)}</td>'
            f'<td {TD}>{trunc(campaign_val, 40, tooltip=True)}</td>'
            f'<td {TD}>{enfoque_val}</td>'
            f'<td {TD}>{trunc(experiment_val, 15)}</td>'
            f'<td {TD}>{corp_subcanal_val}</td>'
            f'<td {TD} style="color:#888;font-size:10px">{corp_subcanal_aux_val}</td>'
            f'<td {TD}>{fm_subcanal_val}</td>'
            f'<td {TD} style="color:#888;font-size:10px">{fm_subcanal_aux_val}</td>'
            f'<td {TD}>{medio_final_val}</td>'
            f'<td {TD_NUM}>{safe_int_or_dash(ev_test)}</td>'
            f'<td {TD_NUM}>{safe_int_or_dash(ev_control)}</td>'
            f'<td {TD_NUM}>{safe_int_or_dash(ev_arrived)}</td>'
            f'<td {TD_NUM}>{safe_int_or_dash(ev_open)}</td>'
            f'<td {TD_NUM}>{safe_int_or_dash(ev_click)}</td>'
            f'<td {TD_NUM}>{fmt_pct_or_dash(open_rate_val)}</td>'
            f'<td {TD_NUM}>{fmt_user_inc_color(user_inc_val)}</td>'
            f'<td {TD_NUM}>{fmt_user_inc_color(user_inc_adj_val)}</td>'
            f'<td {TD_NUM}>{fmt_usd_or_dash(value_inc_val)}</td>'
            f'<td {TD_NUM}>{safe_int_or_dash(absoluto_val)}</td>'
            f'<td {TD_NUM}>{safe_int_or_dash(control_nr_val)}</td>'
            f'<td {TD_NUM}>{fmt_ratio_color(ratio_val)}</td>'
            f'<td {TD_NUM}>{safe_int_or_dash(entry_test_val) if _is_journey else "—"}</td>'
            f'<td {TD_NUM}>{safe_int_or_dash(entry_ctrl_val) if _is_journey else "—"}</td>'
            f'<td {TD}>{trunc(flag_paid_val, 10)}</td>'
            f'<td {TD_NUM}>{fmt_usd_or_dash(consumido_val)}</td>'
            f'<td {TD_NUM}>{fmt_usd_or_dash(envio_val)}</td>'
            f'<td {TD_NUM}>{fmt_usd_or_dash(mantika_val)}</td>'
            '</tr>'
        )

    html_output += '</tbody></table></div>'
    return html_output


# ══════════════════════════════════════════════════════════════════════════════
# PESTAÑA INSTALL → ACTIVATION RATE (§89) — análisis LFT + insights estratégicos
# Sin nuevas BQ queries — usa monthly_nr + monthly_installs + monthly_inv_total
# ══════════════════════════════════════════════════════════════════════════════

def build_install_activation_tab_html(data):
    """Tab Install → Activation Rate (§89).

    LFT (Lift Factor) = N+R / Installs por canal/mes.
    Relación fundamental: CPA = CPI / LFT.

    100% calculado en Python desde datos ya en memory:
      monthly_nr          → de NR Mensual (TC §71)
      monthly_installs    → de Installs Mensual (BASE_INSTALLS_LIFECYCLE §88)
      monthly_inv_total   → de Performance (TC §72)

    Nota metodológica: UCR Gest N+R es lift-based (incremental Test-Control),
    lo que puede subestimar su LFT real vs la métrica de atribución del Corp.
    POM, MGM, L&P usan N+R de atribución → LFT más representativo.
    """
    import json as _json
    import datetime as _dt

    monthly_nr       = data.get('monthly_nr', {})
    monthly_installs = data.get('monthly_installs', {})
    inv_total        = data.get('monthly_inv_total', {})
    nr_months        = data.get('months', [])
    inst_months      = data.get('installs_months', [])

    # Meses con ambas fuentes disponibles (últimos 12 para el análisis completo)
    months_all = sorted(set(nr_months) & set(inst_months))
    months12   = months_all[-12:]   # hasta 12 meses para charts
    cur_m      = _dt.date.today().strftime('%Y%m')
    closed     = [m for m in months12 if m < cur_m]
    last_m     = closed[-1] if closed else (months12[-1] if months12 else None)

    # ── Canales analizados ────────────────────────────────────────────────────
    # has_inv=True → canal con datos de inversión (para CPI/CPA matrix)
    # note: OC ACT N+R es lift-based; UCR Gest también
    CHANNELS = [
        {'label': 'UCR Gest', 'color': '#5899D1', 'has_inv': True,
         'note': 'N+R lift-based (puede subestimar LFT real)'},
        {'label': 'POM ADQ',  'color': '#2F9E8F', 'has_inv': True,  'note': ''},
        {'label': 'OC ACT',   'color': '#E1484C', 'has_inv': True,
         'note': 'N+R lift-based'},
        {'label': 'MGM ADQ',  'color': '#F5A664', 'has_inv': True,  'note': ''},
        {'label': 'L&P ADQ',  'color': '#7A41ED', 'has_inv': False, 'note': 'Sin datos inv.'},
        {'label': 'ORG',      'color': '#A4ACB9', 'has_inv': False, 'note': 'Orgánico'},
    ]

    def sdiv(a, b):
        """División segura — None si denominador es 0."""
        return round(a / b, 4) if b and b > 0 else None

    # ── Computar LFT, CPI, CPA por canal/mes ─────────────────────────────────
    lft = {}   # {label: {m: float 0-1}}
    cpi = {}   # {label: {m: float USD/install}}
    cpa = {}   # {label: {m: float USD/NR}}

    for ch in CHANNELS:
        lbl = ch['label']
        lft[lbl], cpi[lbl], cpa[lbl] = {}, {}, {}
        for m in months12:
            nr   = monthly_nr.get(lbl, {}).get(m, 0) or 0
            inst = monthly_installs.get(lbl, {}).get(m, 0) or 0
            inv  = (inv_total.get(lbl, {}).get(m) or 0) if ch['has_inv'] else 0
            lft[lbl][m] = sdiv(nr, inst)
            if ch['has_inv'] and inv > 0:
                cpi[lbl][m] = sdiv(inv, inst)
                cpa[lbl][m] = sdiv(inv, nr)

    # ── Helpers de formateo ───────────────────────────────────────────────────
    def fmt_pct(v):
        return f'{v*100:.1f}%' if v is not None else '—'
    def fmt_usd(v):
        return f'${v:,.2f}' if v is not None else '—'
    def fmt_trend(v_now, v_prev):
        if v_now is None or v_prev is None: return ('—', '#888')
        delta = v_now - v_prev
        if abs(delta) < 0.005: return ('≈ estable', '#888')
        col = '#0d7a3e' if delta > 0 else '#c5221f'
        arrow = '▲' if delta > 0 else '▼'
        return (f'{arrow} {abs(delta)*100:.1f}pp', col)

    # ── Chart 1: LFT Histórico por canal (líneas) ─────────────────────────────
    mlbls = [fmt_month(m) for m in months12]
    c1_traces = []
    for ch in CHANNELS:
        lbl = ch['label']
        y   = [lft[lbl].get(m) for m in months12]
        txt = [fmt_pct(v) for v in y]
        c1_traces.append({
            'type': 'scatter', 'name': lbl,
            'x': mlbls, 'y': [v*100 if v is not None else None for v in y],
            'mode': 'lines+markers',
            'line': {'color': ch['color'], 'width': 2.5},
            'marker': {'size': 6, 'color': ch['color']},
            'text': txt, 'textposition': 'top center',
            'hovertemplate': '%{fullData.name}: %{text}<extra></extra>',
            'connectgaps': True,
        })
    c1_layout = {
        'plot_bgcolor': 'white', 'paper_bgcolor': 'white',
        'height': 360, 'hovermode': 'x unified',
        'title': {'text': 'LFT: Install → Activation Rate por canal (%)', 'font': {'size': 13}},
        'legend': {'orientation': 'h', 'y': -0.22, 'font': {'size': 10}},
        'margin': {'l': 55, 'r': 30, 't': 45, 'b': 90},
        'yaxis': {'tickformat': '.0f', 'ticksuffix': '%', 'gridcolor': '#f0f0f0',
                  'range': [0, 105]},
        'xaxis': {'tickfont': {'size': 10}},
    }

    # ── Chart 2: LFT mes actual — barras horizontales ─────────────────────────
    if last_m:
        ch_sorted = sorted(CHANNELS, key=lambda c: lft[c['label']].get(last_m) or 0)
        c2_traces = [{
            'type': 'bar', 'orientation': 'h',
            'name': 'LFT',
            'x': [(lft[c['label']].get(last_m) or 0) * 100 for c in ch_sorted],
            'y': [c['label'] for c in ch_sorted],
            'marker': {'color': [c['color'] for c in ch_sorted]},
            'text': [fmt_pct(lft[c['label']].get(last_m)) for c in ch_sorted],
            'textposition': 'outside',
            'hovertemplate': '%{y}: %{text}<extra></extra>',
        }]
        # Línea de promedio (solo canales con datos)
        vals = [lft[c['label']].get(last_m) for c in CHANNELS
                if lft[c['label']].get(last_m) is not None]
        avg_lft = sum(vals) / len(vals) if vals else None
        c2_shapes = [{'type': 'line', 'xref': 'x', 'yref': 'paper',
                      'x0': avg_lft*100, 'x1': avg_lft*100, 'y0': 0, 'y1': 1,
                      'line': {'color': '#1a2744', 'width': 1.5, 'dash': 'dot'}}] if avg_lft else []
        c2_layout = {
            'plot_bgcolor': 'white', 'paper_bgcolor': 'white',
            'height': 280, 'hovermode': 'y unified',
            'title': {'text': f'LFT — {fmt_month(last_m)} (ordenado menor → mayor)',
                      'font': {'size': 12}},
            'margin': {'l': 90, 'r': 80, 't': 40, 'b': 40},
            'xaxis': {'tickformat': '.0f', 'ticksuffix': '%', 'range': [0, 105]},
            'yaxis': {'tickfont': {'size': 11}},
            'showlegend': False, 'shapes': c2_shapes,
        }
    else:
        c2_traces, c2_layout = [], {}

    # ── Chart 3: Matriz de Eficiencia — CPI vs LFT (scatter) ─────────────────
    # Solo canales con inversión. Tamaño = N+R volumen.
    c3_traces = []
    if last_m:
        for ch in [c for c in CHANNELS if c['has_inv']]:
            lbl = ch['label']
            lft_v = lft[lbl].get(last_m)
            cpi_v = cpi[lbl].get(last_m)
            cpa_v = cpa[lbl].get(last_m)
            nr_v  = monthly_nr.get(lbl, {}).get(last_m, 0) or 0
            if lft_v and cpi_v and nr_v > 0:
                c3_traces.append({
                    'type': 'scatter', 'mode': 'markers+text',
                    'name': lbl,
                    'x': [cpi_v], 'y': [lft_v * 100],
                    'marker': {
                        'color': ch['color'],
                        'size': [max(12, min(50, nr_v / 3000))],
                        'sizemode': 'area', 'opacity': 0.85,
                        'line': {'color': 'white', 'width': 1.5},
                    },
                    'text': [lbl], 'textposition': 'top center',
                    'textfont': {'size': 10, 'color': '#333'},
                    'customdata': [[nr_v, cpa_v or 0]],
                    'hovertemplate': (
                        f'<b>{lbl}</b><br>'
                        'CPI: $%{x:.2f}<br>'
                        'LFT: %{y:.1f}%<br>'
                        'N+R: %{customdata[0]:,.0f}<br>'
                        'CPA: $%{customdata[1]:.2f}<extra></extra>'
                    ),
                })
    c3_layout = {
        'plot_bgcolor': 'white', 'paper_bgcolor': 'white',
        'height': 320, 'showlegend': False,
        'title': {'text': 'Matriz de Eficiencia: CPI vs LFT (tamaño = N+R volumen)',
                  'font': {'size': 12}},
        'margin': {'l': 55, 'r': 30, 't': 45, 'b': 55},
        'xaxis': {'title': 'CPI (USD/install)', 'tickformat': '$,.2f',
                  'gridcolor': '#f0f0f0'},
        'yaxis': {'title': 'LFT (%)', 'tickformat': '.0f', 'ticksuffix': '%',
                  'gridcolor': '#f0f0f0'},
        'annotations': [{'x': 0.02, 'y': 0.98, 'xref': 'paper', 'yref': 'paper',
                          'text': '← CPI bajo + LFT alto = IDEAL',
                          'showarrow': False, 'font': {'size': 9, 'color': '#0d7a3e'},
                          'xanchor': 'left', 'yanchor': 'top'}],
    }

    # ── Tabla LFT histórica ───────────────────────────────────────────────────
    def lft_cell_bg(v):
        if v is None: return '#f8f8f8'
        if v >= 0.60: return '#d6f5e3'   # verde
        if v >= 0.40: return '#fff9db'   # amarillo
        return '#ffe0e0'                 # rojo

    tbl_html = (
        '<table style="width:100%;border-collapse:collapse;font-size:11px">'
        '<thead><tr style="background:#1a2744;color:#f5d000">'
        '<th style="padding:5px 8px;text-align:left">Canal</th>'
    )
    for m in months12:
        tbl_html += f'<th style="padding:5px 8px;text-align:center;min-width:64px">{fmt_month(m)}</th>'
    tbl_html += '</tr></thead><tbody>'

    for ch in CHANNELS:
        lbl = ch['label']
        tbl_html += (
            f'<tr><td style="padding:4px 8px;font-weight:600;'
            f'border-left:3px solid {ch["color"]};white-space:nowrap">'
            f'{lbl}'
        )
        if ch['note']:
            tbl_html += f' <span style="font-weight:400;color:#888;font-size:9px">({ch["note"]})</span>'
        tbl_html += '</td>'
        for m in months12:
            v   = lft[lbl].get(m)
            bg  = lft_cell_bg(v)
            tbl_html += (
                f'<td style="padding:4px 8px;text-align:center;background:{bg}'
                f';font-weight:{"700" if v and v >= 0.60 else "400"}">'
                f'{fmt_pct(v)}</td>'
            )
        tbl_html += '</tr>'
        # Sub-fila CPA (solo canales con inversión)
        if ch['has_inv']:
            tbl_html += (
                '<tr><td style="padding:2px 8px 4px 20px;color:#888;'
                'font-style:italic;font-size:9.5px">↳ CPA</td>'
            )
            for m in months12:
                v = cpa[lbl].get(m)
                tbl_html += (
                    f'<td style="padding:2px 8px 4px;text-align:center;'
                    f'color:#556;font-size:9.5px">{fmt_usd(v)}</td>'
                )
            tbl_html += '</tr>'
    tbl_html += '</tbody></table>'

    # ── Motor de insights estratégicos ───────────────────────────────────────
    insights = []

    # ① Canal con mejor LFT actual
    best_lft = max(
        [(ch['label'], lft[ch['label']].get(last_m)) for ch in CHANNELS
         if lft[ch['label']].get(last_m) is not None],
        key=lambda x: x[1], default=None
    )
    if best_lft:
        insights.append({
            'tipo': 'oportunidad',
            'icon': '🏆',
            'titulo': f'Mayor conversor: <b>{best_lft[0]}</b> — LFT {fmt_pct(best_lft[1])}',
            'detalle': (
                f'{best_lft[0]} convierte {fmt_pct(best_lft[1])} de sus installs en usuarios N+R. '
                f'Escalar su presupuesto tiene el mayor retorno por install. '
                f'CPA actual: {fmt_usd(cpa[best_lft[0]].get(last_m))}.'
            ),
        })

    # ② Canal con peor LFT (con inversión)
    worst_lft = min(
        [(ch['label'], lft[ch['label']].get(last_m)) for ch in CHANNELS
         if ch['has_inv'] and lft[ch['label']].get(last_m) is not None],
        key=lambda x: x[1], default=None
    )
    if worst_lft and worst_lft[1] is not None:
        insights.append({
            'tipo': 'alerta',
            'icon': '⚠️',
            'titulo': f'Menor conversor (con inversión): <b>{worst_lft[0]}</b> — LFT {fmt_pct(worst_lft[1])}',
            'detalle': (
                f'{worst_lft[0]} solo convierte {fmt_pct(worst_lft[1])} de installs en N+R. '
                f'Con un CPA de {fmt_usd(cpa[worst_lft[0]].get(last_m))}, '
                f'mejorar la experiencia post-install o el targeting de audiencias '
                f'reduciría el CPA proporcionalmente.'
            ),
        })

    # ③ Tendencias MoM (comparar último vs penúltimo mes cerrado)
    if len(closed) >= 2:
        m_now, m_prev = closed[-1], closed[-2]
        for ch in CHANNELS:
            lbl = ch['label']
            v_now  = lft[lbl].get(m_now)
            v_prev = lft[lbl].get(m_prev)
            if v_now is None or v_prev is None: continue
            delta = v_now - v_prev
            if delta <= -0.03:  # caída > 3pp → alerta
                cpa_impacto = None
                if ch['has_inv'] and cpa[lbl].get(m_now):
                    cpa_impacto = cpa[lbl][m_now] - (cpa[lbl][m_now] * v_prev / v_now)
                insights.append({
                    'tipo': 'alerta',
                    'icon': '📉',
                    'titulo': f'LFT cayendo: <b>{lbl}</b> — {fmt_pct(v_prev)} → {fmt_pct(v_now)} ({delta*100:+.1f}pp MoM)',
                    'detalle': (
                        f'La tasa de conversión de {lbl} cayó {abs(delta)*100:.1f}pp '
                        f'de {fmt_month(m_prev)} a {fmt_month(m_now)}. '
                        + (f'Impacto en CPA: +{fmt_usd(cpa_impacto)} adicional por N+R. ' if cpa_impacto else '')
                        + 'Revisar calidad de audiencias y optimización post-install.'
                    ),
                })
            elif delta >= 0.03:  # mejora > 3pp → oportunidad
                insights.append({
                    'tipo': 'oportunidad',
                    'icon': '📈',
                    'titulo': f'LFT mejorando: <b>{lbl}</b> — {fmt_pct(v_prev)} → {fmt_pct(v_now)} (+{delta*100:.1f}pp MoM)',
                    'detalle': (
                        f'{lbl} mejoró su conversión {delta*100:.1f}pp en un mes. '
                        'Es el momento de escalar — más presupuesto al mismo CPA mejorado.'
                    ),
                })

    # ④ Relación CPI → CPA via LFT (regla fundamental)
    if last_m:
        for ch in [c for c in CHANNELS if c['has_inv']]:
            lbl = ch['label']
            lft_v = lft[lbl].get(last_m)
            cpi_v = cpi[lbl].get(last_m)
            cpa_v = cpa[lbl].get(last_m)
            if lft_v and cpi_v and cpa_v:
                cpa_calc = cpi_v / lft_v
                diff_pct = abs(cpa_v - cpa_calc) / cpa_calc if cpa_calc else 0
                if diff_pct < 0.05:  # CPA ≈ CPI/LFT → consistencia confirmada
                    insights.append({
                        'tipo': 'insight',
                        'icon': '🔗',
                        'titulo': f'Relación CPI→CPA verificada: <b>{lbl}</b>',
                        'detalle': (
                            f'CPI={fmt_usd(cpi_v)} / LFT={fmt_pct(lft_v)} = CPA={fmt_usd(cpa_calc)} '
                            f'(real: {fmt_usd(cpa_v)}). '
                            f'Para bajar CPA a ${cpa_v*0.8:.2f} (-20%), necesitas LFT ≥ {fmt_pct(lft_v*1.25)} '
                            f'o CPI ≤ ${cpi_v*0.8:.2f}.'
                        ),
                    })
                    break  # Un ejemplo basta

    # ⑤ ORG como benchmark
    if last_m and lft['ORG'].get(last_m):
        lft_org = lft['ORG'][last_m]
        insights.append({
            'tipo': 'insight',
            'icon': '📊',
            'titulo': f'Benchmark Orgánico: LFT {fmt_pct(lft_org)}',
            'detalle': (
                f'El canal orgánico convierte {fmt_pct(lft_org)} de installs sin inversión directa. '
                'Canales pagados por debajo de este benchmark no están generando valor incremental '
                'suficiente vs la línea base orgánica.'
            ),
        })

    # ── Renderizar insights HTML ──────────────────────────────────────────────
    colors = {'oportunidad': '#d6f5e3', 'alerta': '#ffe0e0', 'insight': '#e8f0fe'}
    border = {'oportunidad': '#0d7a3e', 'alerta': '#c5221f', 'insight': '#1a73e8'}
    insights_html = ''
    for ins in insights[:8]:  # máximo 8 insights
        bg = colors.get(ins['tipo'], '#f8f8f8')
        bd = border.get(ins['tipo'], '#ccc')
        insights_html += (
            f'<div style="background:{bg};border-left:4px solid {bd};'
            f'border-radius:0 6px 6px 0;padding:10px 14px;margin-bottom:10px">'
            f'<div style="font-size:12px;font-weight:700;color:#1a2744;margin-bottom:4px">'
            f'{ins["icon"]} {ins["titulo"]}</div>'
            f'<div style="font-size:11px;color:#444;line-height:1.6">{ins["detalle"]}</div>'
            f'</div>'
        )
    if not insights_html:
        insights_html = '<div style="color:#aaa;font-size:11px">Datos insuficientes para generar insights.</div>'

    # ── Leyenda de colores LFT ─────────────────────────────────────────────────
    legend_html = (
        '<div style="display:flex;gap:16px;font-size:10px;color:#555;margin-bottom:12px;flex-wrap:wrap">'
        '<span><span style="display:inline-block;width:12px;height:12px;background:#d6f5e3;border:1px solid #ccc;margin-right:4px"></span>≥ 60% Excelente</span>'
        '<span><span style="display:inline-block;width:12px;height:12px;background:#fff9db;border:1px solid #ccc;margin-right:4px"></span>40–60% Aceptable</span>'
        '<span><span style="display:inline-block;width:12px;height:12px;background:#ffe0e0;border:1px solid #ccc;margin-right:4px"></span>&lt; 40% Atención</span>'
        '</div>'
    )

    # ── Serializar charts ─────────────────────────────────────────────────────
    c1j = _json.dumps({'data': c1_traces, 'layout': c1_layout}, ensure_ascii=False)
    c2j = _json.dumps({'data': c2_traces, 'layout': c2_layout}, ensure_ascii=False)
    c3j = _json.dumps({'data': c3_traces, 'layout': c3_layout}, ensure_ascii=False)

    # ── CSS ───────────────────────────────────────────────────────────────────
    css = '''<style>
.iar-wrap{padding:16px;font-family:Arial,sans-serif;background:#f5f7fa}
.iar-sec{background:#fff;border:1px solid #e4e8f0;border-radius:8px;
          padding:16px;margin-bottom:18px}
.iar-ttl{font-size:13px;font-weight:700;color:#1a2744;
          border-bottom:2px solid #F5D000;padding-bottom:6px;margin-bottom:14px}
.iar-g2{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.iar-note{font-size:10px;color:#888;font-style:italic;margin-top:6px}
</style>'''

    # ── Construir HTML final ──────────────────────────────────────────────────
    period_label = f'{fmt_month(months12[0])} – {fmt_month(months12[-1])}' if months12 else ''
    html = f'<div class="iar-wrap">\n{css}\n'

    html += ('<script>\n'
             f'var _iarC1={c1j};\n'
             f'var _iarC2={c2j};\n'
             f'var _iarC3={c3j};\n'
             'function initInstallActivationCharts(){'
             'var cfg={responsive:true};'
             'if(document.getElementById("iar-c1"))Plotly.newPlot("iar-c1",_iarC1.data,_iarC1.layout,cfg);'
             'if(document.getElementById("iar-c2"))Plotly.newPlot("iar-c2",_iarC2.data,_iarC2.layout,cfg);'
             'if(document.getElementById("iar-c3"))Plotly.newPlot("iar-c3",_iarC3.data,_iarC3.layout,cfg);'
             '}\n</script>\n')

    # Sección 1: LFT Trend
    html += ('<div class="iar-sec"><div class="iar-ttl">'
             f'📈 LFT Histórico por Canal — {period_label}</div>'
             '<div id="iar-c1" style="height:360px"></div>'
             '<div class="iar-note">LFT = N+R / Installs. '
             'UCR Gest y OC ACT usan N+R lift-based (puede subestimar su LFT real).</div>'
             '</div>\n')

    # Sección 2: Snapshot + Matriz
    html += '<div class="iar-g2">\n'
    html += ('<div class="iar-sec"><div class="iar-ttl">'
             f'📊 LFT {fmt_month(last_m) if last_m else ""} por Canal</div>'
             '<div id="iar-c2" style="height:280px"></div></div>\n')
    html += ('<div class="iar-sec"><div class="iar-ttl">'
             '🎯 Matriz Eficiencia: CPI vs LFT</div>'
             '<div id="iar-c3" style="height:280px"></div>'
             '<div class="iar-note">Cuadrante ideal: CPI bajo + LFT alto (esquina superior izquierda). '
             'Solo canales con datos de inversión.</div></div>\n')
    html += '</div>\n'

    # Sección 3: Tabla histórica
    html += ('<div class="iar-sec"><div class="iar-ttl">📋 Tabla LFT histórica</div>'
             + legend_html + tbl_html + '</div>\n')

    # Sección 4: Insights
    html += ('<div class="iar-sec"><div class="iar-ttl">'
             '💡 Insights y Recomendaciones Estratégicas</div>'
             + insights_html + '</div>\n')

    html += '</div>'
    return html


# ══════════════════════════════════════════════════════════════════════════════
# PESTAÑA INSTALLS MENSUAL (§88) — misma estructura que NR Mensual pero installs
# Fuentes: Q_INSTALLS (UCR) + QTY_DEVICES/INSTALLS (Paid)
# ══════════════════════════════════════════════════════════════════════════════

def build_installs_table_html(data):
    """Tabla HTML estática de Installs Mensuales (pestaña Installs Mensual §88).

    Filas por canal: Installs | MoM | CPI (solo canales con inversión)
    """
    HIERARCHY_NR         = data['HIERARCHY_NR']
    months               = data.get('installs_months', data['months'])
    monthly_installs     = data['monthly_installs']
    monthly_installs_mom = data['monthly_installs_mom']
    monthly_inv_total    = data.get('monthly_inv_total', {})

    CLS = {
        'grand': ('background:#1a2744;color:#fff;font-weight:700', 'background:#111d38;color:#9db4d0'),
        'sub1':  ('background:#2d5986;color:#fff;font-weight:600', 'background:#1e4570;color:#c0d8f0'),
        'sub2':  ('background:#4a7ab5;color:#fff;font-weight:500', 'background:#3a6898;color:#d0e4f8'),
        'leaf':  ('background:#fff;color:#333', 'background:#fafafa;color:#666')
    }

    def fmt_pct_inst(v, dark):
        if v is None: return '<span style="color:#aaa">—</span>'
        pos_col = '#81c995' if dark else '#0d7a3e'
        neg_col = '#f28b82' if dark else '#c5221f'
        if v >= 0: return f'<span style="color:{pos_col};font-weight:600">▲ {v*100:.1f}%</span>'
        return f'<span style="color:{neg_col};font-weight:600">▼ {abs(v)*100:.1f}%</span>'

    # 'Total Inversión' es el root de hierarchy_cost; canales hoja tienen su propio label
    def get_inv(label):
        key = 'Total Inversión' if label == 'Total N+R' else label
        return monthly_inv_total.get(key, {})

    h = ('<div class="table-scroll"><table class="mom-tbl" id="tbl-installs-mensual">'
         '<thead><tr><th class="lbl-col">Canal</th>')
    for m in months:
        h += f'<th data-month="{m}">{fmt_month(m)}</th>'
    h += '</tr></thead><tbody>'

    for c in HIERARCHY_NR:
        label  = c['label']
        indent = c['indent']
        row_s, met_s = CLS[c['level']]
        dark = c['level'] != 'leaf'
        pad  = f'padding-left:{indent*14+10}px'
        sub_pad = f'padding-left:{(indent+1)*14+10}px'

        # Fila de installs absolutas
        h += f'<tr data-canal="{label}"><td class="lbl-col" style="{pad};{row_s}">{label}</td>'
        for m in months:
            val = monthly_installs.get(label, {}).get(m, 0)
            h += f'<td style="{row_s}" data-month="{m}">{fmt_val(val)}</td>'
        h += '</tr>'

        # Sub-fila MoM
        h += (f'<tr data-canal="{label}"><td class="lbl-col" '
              f'style="{sub_pad};{met_s};font-style:italic;font-size:10px">MoM</td>')
        for m in months:
            mom = monthly_installs_mom.get(label, {}).get(m)
            h += f'<td style="{met_s};font-size:10px" data-month="{m}">{fmt_pct_inst(mom, dark)}</td>'
        h += '</tr>'

        # Sub-fila CPI (solo si el canal tiene datos de inversión)
        inv_map = get_inv(label)
        if any(inv_map.get(m) for m in months):
            cpi_s = 'font-size:9.5px;color:#556;font-style:italic;background:#f5f6f8'
            h += (f'<tr data-canal="{label}"><td class="lbl-col" '
                  f'style="{sub_pad};{cpi_s}">↳ CPI (USD)</td>')
            for m in months:
                inv  = inv_map.get(m) or 0
                inst = monthly_installs.get(label, {}).get(m, 0)
                cpi  = round(inv / inst, 2) if inst > 0 and inv > 0 else None
                cell = f'${cpi:.2f}' if cpi else '—'
                h += f'<td style="{cpi_s};text-align:right" data-month="{m}">{cell}</td>'
            h += '</tr>'

    h += '</tbody></table></div>'
    return h


def build_installs_bar(data):
    """Barras apiladas Installs por canal leaf + línea CPI (§88).

    Misma estructura que build_mom_bar(), pero:
      · Usa monthly_installs (en lugar de monthly_nr)
      · CPI = Inversión Total / Installs Totales (en lugar de CPA)
      · Sin líneas de Plan (no hay plan de installs)
      · Título: 'Installs por Canal — Acumulado Mensual'
    """
    HIERARCHY_NR      = data['HIERARCHY_NR']
    months            = data.get('installs_months', data['months'])
    monthly_installs  = data['monthly_installs']
    monthly_inv_total = data.get('monthly_inv_total', {})

    leaf_nodes = sorted(
        [c for c in HIERARCHY_NR if c.get('is_leaf')],
        key=lambda c: sum(monthly_installs.get(c['label'], {}).get(m, 0) for m in months),
        reverse=True
    )
    x_labels = [fmt_month(m) for m in months]

    fig = go.Figure()

    # Total por mes para calcular % en hover
    total_by_m = {m: monthly_installs.get('Total N+R', {}).get(m, 0) or 1 for m in months}

    # Barras apiladas por canal leaf — mismos colores que NR Mensual
    for c in leaf_nodes:
        abs_vals = [monthly_installs.get(c['label'], {}).get(m, 0) for m in months]
        y_vals   = [v / 1000 for v in abs_vals]
        # customdata: [[valor_abs, pct_del_total], ...]
        cust = [[fmt_val(abs_vals[i]),
                 round(abs_vals[i] / total_by_m[m] * 100, 1)]
                for i, m in enumerate(months)]
        fig.add_trace(go.Bar(
            name=c['label'], x=x_labels, y=y_vals, customdata=cust,
            hovertemplate='%{fullData.name}: %{customdata[0]} (%{customdata[1]:.1f}%)<extra></extra>',
            marker_color=c['color']
        ))

    # Línea CPI (Cost Per Install) = Inversión Total / Installs Totales
    # Reutiliza monthly_inv_total['Total Inversión'] ya calculado en process_all()
    cpi_y = []
    for m in months:
        inv   = (monthly_inv_total.get('Total Inversión', {}).get(m) or 0)
        inst  = monthly_installs.get('Total N+R', {}).get(m, 0)
        cpi_y.append(round(inv / inst, 4) if inst > 0 and inv > 0 else None)

    has_cpi = any(v is not None and v > 0 for v in cpi_y)
    if has_cpi:
        fig.add_trace(go.Scatter(
            name='CPI (USD)', x=x_labels, y=cpi_y,
            customdata=[f'${v:.2f}' if v is not None else '—' for v in cpi_y],
            hovertemplate='CPI: %{customdata}<extra></extra>',
            yaxis='y2', mode='lines+markers',
            line=dict(color='#E9C46A', width=2.5, dash='dash'),
            marker=dict(size=6, symbol='diamond', color='#E9C46A')
        ))

    fig.update_layout(
        plot_bgcolor='white', paper_bgcolor='white',
        barmode='stack', height=380, hovermode='x unified',
        title_text='Installs por Canal — Acumulado Mensual',
        legend=dict(orientation='h', y=-0.18, font_size=10),
        margin=dict(l=60, r=70, t=50, b=90),
        yaxis=dict(tickformat=',.0f', ticksuffix='K', showgrid=False),
        yaxis2=(dict(title='CPI (USD)', side='right', overlaying='y',
                     showgrid=False, tickformat='$,.2f') if has_cpi else {}),
        xaxis=dict(tickfont_size=10)
    )
    return json.loads(fig.to_json())


def build_installs_corp_bar_chart(data):
    """Barras apiladas de installs por grupo Corp — sección inferior de Installs Mensual (§88).

    Misma estructura que build_nr_corp_bar_chart(), adaptada para installs.
    4 grupos: NO ATRIBUIDO (0, excluido), OC+UCR, POM, OTHERS.
    """
    import json as _json

    HIERARCHY_NR_CORP       = data.get('HIERARCHY_NR_CORP', [])
    installs_corp_by_node   = data.get('installs_corp_by_node', {})
    months                  = data.get('installs_months', data['months'])

    # Mismos grupos y colores que el chart NR Corp
    GROUPS = [
        ('corp_noatrib', 'No Atribuído',  '#C8CDD8', ['corp_noatrib']),
        ('corp_others',  'OTHERS',        '#7A7D82', ['corp_mgm','corp_lp_brandformance','corp_lp_landings','corp_lp_partnerships','corp_lp_others','corp_lp_affiliates','corp_ucr_prd','corp_pom_others']),
        # BASE_INSTALLS_LIFECYCLE no tiene breakdown por medio/sub-tipo →
        # se usan los nodos padre directamente (corp_pom, corp_ucr_eg).
        # corp_oc_adhoc = Own Channels OTHERS (mapeado vía bq_key OC|OC_ADHOC|TOTAL).
        ('corp_pom',     'POM',           '#1FB8D4', ['corp_pom']),
        ('corp_oc_ucr',  'OC+UCR',        '#F5D000', ['corp_ucr_eg', 'corp_oc_adhoc']),
    ]

    x_labels = [fmt_month(m) for m in months]
    fig = go.Figure()

    # Pre-calcular totales por mes para % en hover y labels dentro de barras
    totals = [
        sum(sum(installs_corp_by_node.get(cid, {}).get(m, 0) for cid in child_ids)
            for _, _, _, child_ids in GROUPS)
        for m in months
    ]

    for _gid, gname, gcolor, child_ids in GROUPS:
        y_vals     = []
        cust       = []
        text_inner = []   # % dentro de la barra (igual que NR Corp)
        for j, m in enumerate(months):
            v     = sum(installs_corp_by_node.get(cid, {}).get(m, 0) for cid in child_ids)
            total = totals[j]
            pct   = round(v / total * 100, 0) if total > 0 else 0
            y_vals.append(v / 1000)
            cust.append([fmt_val(v), pct])
            # Label visible solo si el segmento es ≥ 4% del total
            text_inner.append(f'{int(pct)}%' if pct >= 4 else '')
        fig.add_trace(go.Bar(
            name=gname, x=x_labels, y=y_vals, customdata=cust,
            text=text_inner, textposition='inside',
            textfont={'size': 10, 'color': 'white', 'family': 'Arial'},
            hovertemplate='%{fullData.name}: %{customdata[0]} (%{customdata[1]:.0f}%)<extra></extra>',
            marker_color=gcolor
        ))

    anns = [
        {'x': x_labels[i], 'y': totals[i] / 1000,
         'text': f'<b>{fmt_val(totals[i])}</b>',
         'xref': 'x', 'yref': 'y', 'showarrow': False,
         'font': {'size': 9, 'color': '#1a2744'}, 'yanchor': 'bottom', 'yshift': 4}
        for i in range(len(months)) if totals[i]
    ]

    fig.update_layout(
        barmode='stack', plot_bgcolor='white', paper_bgcolor='white',
        height=310, hovermode='x unified',
        legend=dict(orientation='h', y=-0.22, font_size=10),
        margin=dict(l=50, r=30, t=30, b=80),
        yaxis=dict(tickformat=',.0f', ticksuffix='K', showgrid=False),
        xaxis=dict(tickfont_size=10),
        annotations=anns
    )
    return _json.loads(fig.to_json())


def build_installs_corp_table_html(data):
    """Tabla colapsable de installs por estructura corporativa — Installs Mensual (§88).

    Misma lógica que build_nr_corp_table_html(), adaptada para installs:
      · Usa installs_corp_by_node en lugar de monthly_nr_corp_by_node
      · Filas por nodo: Installs | MoM | Share Installs
      · Sin Plan/vs Plan (no hay plan de installs en Excel)
    """
    HIERARCHY_NR_CORP     = data.get('HIERARCHY_NR_CORP', [])
    installs_corp_by_node = data.get('installs_corp_by_node', {})
    months                = data.get('installs_months', data['months'])

    if not HIERARCHY_NR_CORP:
        return '<div style="color:#aaa;font-size:11px">Sin jerarquía corp disponible.</div>'

    node_by_id = {c['id']: c for c in HIERARCHY_NR_CORP if 'id' in c}

    # Total corp por mes para calcular Share
    total_corp_inst = {
        m: sum(installs_corp_by_node.get(c['id'], {}).get(m, 0)
               for c in HIERARCHY_NR_CORP if c.get('level') == 'sub1')
        for m in months
    }

    # Estilos por nivel — idénticos a NR Corp para consistencia
    LVLBG = {
        'grand': '#1a2744', 'sub1': '#2d5986', 'sub2': '#4a7ab5', 'medio': '#ffffff'
    }
    LVLTXT = {
        'grand': '#ffffff',  'sub1': '#ffffff',  'sub2': '#ffffff', 'medio': '#333333'
    }

    def fmt_pct_c(v):
        if v is None: return '<span style="color:#aaa">—</span>'
        col = '#81c995' if v >= 0 else '#f28b82'
        arrow = '▲' if v >= 0 else '▼'
        return f'<span style="color:{col};font-weight:600">{arrow} {abs(v)*100:.1f}%</span>'

    def render_corp_inst_node(node_id, parent_id, is_hidden):
        c = node_by_id.get(node_id)
        if not c:
            return ''
        level     = c.get('level', 'medio')
        bg        = LVLBG.get(level, '#ffffff')
        txt       = LVLTXT.get(level, '#333')
        indent_px = c.get('indent', 0) * 16 + 8
        is_leaf   = c.get('is_leaf', True)
        children  = [x['id'] for x in HIERARCHY_NR_CORP
                     if 'id' in x and x.get('parent') == node_id]
        display   = 'none' if is_hidden else ''

        # Botón toggle / bullet
        if children:
            btn = (f'<button class="corp-toggle" data-corp-inst-toggle="{node_id}" '
                   f'onclick="toggleCorpInstallsNode(\'{node_id}\')" '
                   f'style="background:none;border:none;cursor:pointer;color:{txt};'
                   f'font-size:12px;padding:0 4px">▶</button>')
        else:
            btn = '<span style="padding:0 4px;font-size:10px">●</span>'

        lbl  = c.get('label', node_id)
        fwt  = '700' if level in ('grand', 'sub1') else '500'
        name_cell = (f'<td class="lbl-col" '
                     f'style="padding-left:{indent_px}px;background:{bg};color:{txt};'
                     f'font-weight:{fwt};font-size:11px" '
                     f'data-corp-inst-node="{node_id}">{btn}{lbl}</td>')

        # Valores de installs por mes
        vals_html = ''
        inst_by_m = installs_corp_by_node.get(node_id, {})
        for m in months:
            v = inst_by_m.get(m, 0)
            vals_html += (f'<td style="background:{bg};color:{txt};text-align:right;'
                          f'font-size:10.5px" data-month="{m}">'
                          f'{fmt_val(v) if v else "—"}</td>')

        h = (f'<tr style="display:{display}" '
             f'data-corp-inst-parent="{parent_id or ""}">'
             f'{name_cell}{vals_html}</tr>')

        # Sub-fila MoM
        mom_vals = ''
        inst_months_sorted = sorted(inst_by_m.keys())
        for idx, m in enumerate(months):
            if idx > 0 and m in inst_by_m:
                prev_m = inst_months_sorted[inst_months_sorted.index(m) - 1] if m in inst_months_sorted and inst_months_sorted.index(m) > 0 else None
                prev_v = inst_by_m.get(prev_m, 0) if prev_m else 0
                curr_v = inst_by_m.get(m, 0)
                mom    = round((curr_v - prev_v) / prev_v, 4) if prev_v else None
                mom_vals += (f'<td style="background:#f5f6f8;color:#556;text-align:right;'
                             f'font-size:9.5px" data-month="{m}">{fmt_pct_c(mom)}</td>')
            else:
                mom_vals += (f'<td style="background:#f5f6f8;color:#aaa;text-align:right;'
                             f'font-size:9.5px" data-month="{m}">—</td>')
        h += (f'<tr style="display:{display}" data-corp-inst-parent="{parent_id or ""}">'
              f'<td class="lbl-col" style="padding-left:{indent_px+12}px;background:#f5f6f8;'
              f'color:#888;font-style:italic;font-size:9.5px">MoM</td>{mom_vals}</tr>')

        # Sub-fila Share Installs
        share_vals = ''
        for m in months:
            v     = inst_by_m.get(m, 0)
            total = total_corp_inst.get(m, 0)
            share = round(v / total * 100, 1) if total else None
            share_vals += (f'<td style="background:#f5f6f8;color:#556;text-align:right;'
                           f'font-size:9.5px" data-month="{m}">'
                           f'{"%.1f%%" % share if share is not None else "—"}</td>')
        h += (f'<tr style="display:{display}" data-corp-inst-parent="{parent_id or ""}">'
              f'<td class="lbl-col" style="padding-left:{indent_px+12}px;background:#f5f6f8;'
              f'color:#888;font-style:italic;font-size:9.5px">Share</td>{share_vals}</tr>')

        # Hijos (sub1 visibles, sub2/medios ocultos)
        for child_id in children:
            child_c   = node_by_id.get(child_id, {})
            child_lvl = child_c.get('level', 'medio')
            hidden    = is_hidden or child_lvl not in ('sub1',)
            h += render_corp_inst_node(child_id, node_id, hidden)

        return h

    # Encabezado de la tabla
    hdr_cols = ''.join(
        f'<th style="min-width:72px;text-align:right;font-size:11px" data-month="{m}">{fmt_month(m)}</th>'
        for m in months
    )
    h = (f'<div class="table-scroll"><table class="mom-tbl" style="font-size:11px">'
         f'<thead><tr>'
         f'<th class="lbl-col" style="font-size:11px">Canal / Estructura Corp</th>'
         f'{hdr_cols}</tr></thead><tbody>')

    # Renderizar desde nodos raíz (sub1 level) — mismo orden que NR Corp
    root_order = ['corp_oc_ucr', 'corp_pom', 'corp_mgm', 'corp_lp', 'corp_noatrib']
    rendered   = set()
    for root_id in root_order:
        if root_id in node_by_id:
            h += render_corp_inst_node(root_id, None, False)
            rendered.add(root_id)

    # Nodos sub1 no cubiertos por root_order
    for c in HIERARCHY_NR_CORP:
        if 'id' in c and c.get('level') == 'sub1' and c['id'] not in rendered:
            h += render_corp_inst_node(c['id'], None, False)

    # Separador + Total corp al fondo
    h += f'<tr><td colspan="{len(months)+1}" style="border-top:2px solid #2d5986;padding:0;height:4px;background:#f0f4fa"></td></tr>'
    if 'corp_total' in node_by_id:
        h += render_corp_inst_node('corp_total', None, False)

    h += '</tbody></table></div>'
    return h


# ══════════════════════════════════════════════════════════════════════════════
# PESTAÑA REPORTING — 3 secciones ejecutivas con charts descargables
# Sección 1: N+R in App + Valor Predictivo (vista Corp, 6 meses)
# Sección 2: New vs Recovered + N+R por Canal
# Sección 3: Evolución N+R por estrategia OC+UCR
# Metodología de clasificación: config/reporting_methodology.md
# ══════════════════════════════════════════════════════════════════════════════

def _rep_highlights(months6, month_lbls, s3_ucr, s3_actr, s3_adh, s3_jny,
                    s3_total, s1_oc, s1_total, cpa_paid_g, inv_oc_fn):
    """Auto-genera sección de Highlights estilo VP — comparando último mes vs anterior."""
    if len(months6) < 2:
        return '<p style="color:#aaa;font-size:11px">Sin suficientes meses para highlights.</p>'

    cur, prev = months6[-1], months6[-2]
    lbl_cur, lbl_prev = month_lbls[-1], month_lbls[-2]

    def dp(a, b): return round((a - b) / b * 100, 1) if b else None
    def si(v): return int(v or 0)
    def _s(v): return '+' if v > 0 else ''
    def sc(v): return (_s(v) + f'{v:.0f}%') if v is not None else '—'
    def snr(v): return (_s(v) + f'{int(abs(v)/1000)}K') if v else '0K'

    oc_c,oc_p   = si(s1_oc[-1]),   si(s1_oc[-2])
    tot_c,tot_p = si(s3_total[-1]), si(s3_total[-2])
    ucr_c,ucr_p = si(s3_ucr[-1]),  si(s3_ucr[-2])
    act_c,act_p = si(s3_actr[-1]), si(s3_actr[-2])
    adh_c,adh_p = si(s3_adh[-1]),  si(s3_adh[-2])
    jny_c,jny_p = si(s3_jny[-1]),  si(s3_jny[-2])

    d_tot = dp(tot_c, tot_p)
    d_ucr = dp(ucr_c, ucr_p)
    d_act = dp(act_c, act_p)
    d_adh = dp(adh_c, adh_p)
    d_jny = dp(jny_c, jny_p)

    cpa_c  = cpa_paid_g.get(cur)
    d_cpa  = dp(cpa_c, cpa_paid_g.get(prev))

    # Share pp changes
    sh_ucr_c = round(ucr_c/tot_c*100,1) if tot_c else 0
    sh_ucr_p = round(ucr_p/tot_p*100,1) if tot_p else 0
    sh_act_c = round(act_c/tot_c*100,1) if tot_c else 0
    sh_act_p = round(act_p/tot_p*100,1) if tot_p else 0
    sh_adh_c = round(adh_c/tot_c*100,1) if tot_c else 0
    sh_adh_p = round(adh_p/tot_p*100,1) if tot_p else 0
    sh_jny_c = round(jny_c/tot_c*100,1) if tot_c else 0
    sh_jny_p = round(jny_p/tot_p*100,1) if tot_p else 0

    def col(v, pos_good=True):
        if v is None: return '#555'
        return '#0d7a3e' if (v > 0) == pos_good else '#c5221f'

    def li(txt): return f'<li style="margin:2px 0">{txt}</li>'
    def h4(txt, color='#1a2744'):
        return f'<p style="color:{color};font-weight:700;font-size:11px;margin:8px 0 3px;text-decoration:underline">{txt}</p>'

    # Header: total OC MoM
    sign_tot = '+' if (d_tot or 0) > 0 else ''
    nr_delta = tot_c - tot_p
    html  = (f'<div style="font-size:13px;font-weight:700;color:#1a2744;margin-bottom:6px">'
             f'Highlights:</div>')
    html += (f'<p style="font-size:11px;font-weight:700;margin:2px 0">'
             f'<span style="color:{col(d_tot)}">{sign_tot}{d_tot:.0f}% N+R MoM</span>'
             f' ({snr(nr_delta)} N+R):</p>')

    # One-liner per strategy
    html += '<p style="font-size:11px;margin:4px 0">'
    parts = []
    if d_ucr is not None:
        pp_ucr = round(sh_ucr_c - sh_ucr_p, 1)
        parts.append(f'<b>Ucrania</b> <span style="color:{col(d_ucr)}">{_s(d_ucr)}{d_ucr:.0f}% MoM</span>'
                     f' ({snr(ucr_c-ucr_p)} N+R, {_s(pp_ucr)}{pp_ucr:.0f}pp)')
    if d_act is not None:
        pp_act = round(sh_act_c - sh_act_p, 1)
        parts.append(f'<b>Activaci&oacute;n</b> <span style="color:{col(d_act)}">{_s(d_act)}{d_act:.0f}% MoM</span>'
                     f' ({snr(act_c-act_p)} N+R, {_s(pp_act)}{pp_act:.0f}pp)')
    if d_adh is not None and abs(adh_c) > 100:
        parts.append(f'<b>AdHoc</b> <span style="color:{col(d_adh)}">{_s(d_adh)}{d_adh:.0f}% MoM</span>'
                     f' ({snr(adh_c-adh_p)} N+R)')
    if d_jny is not None and abs(jny_c) > 100:
        pp_jny = round(sh_jny_c - sh_jny_p, 1)
        parts.append(f'<b>Resto Rec</b> <span style="color:{col(d_jny)}">{_s(d_jny)}{d_jny:.0f}% MoM</span>'
                     f' ({snr(jny_c-jny_p)} N+R, {_s(pp_jny)}{pp_jny:.0f}pp)')
    html += ', '.join(parts)
    html += '</p>'

    html += '<hr style="border:none;border-top:1px solid #e4e8f0;margin:6px 0">'
    html += h4('Detalle por track:', '#1a2744')

    # Ucrania detail
    html += h4('- Ucrania:', '#F5A000')
    html += '<ul style="margin:2px 0 4px 0;padding-left:14px;font-size:11px">'
    if d_ucr is not None:
        pp = round(sh_ucr_c - sh_ucr_p, 1)
        html += li(f'N+R {snr(ucr_c-ucr_p)} '
                   f'(<span style="color:{col(d_ucr)}">{_s(d_ucr)}{d_ucr:.0f}% MoM</span>, '
                   f'{_s(pp)}{pp:.0f}pp share)')
    if cpa_c and d_cpa is not None:
        html += li(f'CPA Paid: <b>${cpa_c:.0f}</b> '
                   f'(<span style="color:{col(d_cpa, False)}">{_s(d_cpa)}{d_cpa:.0f}% MoM</span>)')
    html += '</ul>'

    html += h4('- Activaci&oacute;n:', '#5899D1')
    html += '<ul style="margin:2px 0 4px 0;padding-left:14px;font-size:11px">'
    if d_act is not None:
        pp = round(sh_act_c - sh_act_p, 1)
        html += li(f'N+R {snr(act_c-act_p)} '
                   f'(<span style="color:{col(d_act)}">{_s(d_act)}{d_act:.0f}% MoM</span>, '
                   f'{_s(pp)}{pp:.0f}pp share)')
    html += '</ul>'

    if adh_c > 100:
        html += h4('- AdHoc:', '#1a2744')
        html += '<ul style="margin:2px 0 4px 0;padding-left:14px;font-size:11px">'
        if d_adh is not None:
            html += li(f'N+R {snr(adh_c-adh_p)} '
                       f'(<span style="color:{col(d_adh)}">{_s(d_adh)}{d_adh:.0f}% MoM</span>)')
        html += '</ul>'

    if abs(jny_c) > 100 or abs(jny_p) > 100:
        html += h4('- Resto Rec (Journey):', '#2F9E8F')
        html += '<ul style="margin:2px 0 4px 0;padding-left:14px;font-size:11px">'
        if d_jny is not None:
            pp = round(sh_jny_c - sh_jny_p, 1)
            html += li(f'N+R {snr(jny_c-jny_p)} '
                       f'(<span style="color:{col(d_jny)}">{_s(d_jny)}{d_jny:.0f}% MoM</span>, '
                       f'{_s(pp)}{pp:.0f}pp share)')
        html += '</ul>'

    return html


def build_reporting_tab_html(data, plan_nr, plan_inv, plan_valor, new_rec_monthly=None):
    """Genera HTML de la pestaña Reporting con 3 secciones ejecutivas descargables.

    Clasificación de canales Corp → config/reporting_methodology.md
    """
    import json as _json

    # ── Node ID groups (ver config/reporting_methodology.md) ─────────
    UCRANIA_IDS = ['corp_ucr_eg_email', 'corp_ucr_eg_pandora', 'corp_ucr_eg_push',
                   'corp_ucr_eg_real_estates', 'corp_ucr_eg_wpp']
    ACT_REC_IDS = ['corp_oc_rec_email', 'corp_oc_rec_pandora',
                   'corp_oc_rec_push', 'corp_oc_rec_wpp']
    JOURNEY_ID  = 'corp_oc_rec_journey'
    ADHOC_IDS   = ['corp_oc_adhoc']
    POM_IDS     = ['corp_acq_pom', 'corp_act_pom', 'corp_web_pom', 'corp_ctw_pom']
    MGM_IDS     = ['corp_mgm']
    LP_IDS      = ['corp_lp_brandformance', 'corp_lp_landings', 'corp_lp_partnerships',
                   'corp_lp_others', 'corp_lp_gtm', 'corp_lp_affiliates']
    OTHERS_IDS  = MGM_IDS + LP_IDS + ['corp_ucr_prd', 'corp_seo', 'corp_pom_sellers', 'corp_pom_others']
    NOATRIB_IDS = ['corp_noatrib']
    OC_UCR_IDS  = UCRANIA_IDS + ACT_REC_IDS + [JOURNEY_ID] + ADHOC_IDS

    # ── Helpers ───────────────────────────────────────────────────────
    nr_corp = data.get('monthly_nr_corp_by_node', {})

    def nv(nid, m):  return nr_corp.get(nid, {}).get(m, 0) or 0
    def sn(ids, m):  return sum(nv(nid, m) for nid in ids)
    def pct(a, b):   return round(a / b * 100, 1) if b else 0.0
    def fmk(v):
        v = int(v or 0)
        if abs(v) >= 1_000_000: return f'{v/1_000_000:.2f}M'
        if abs(v) >= 1_000:     return f'{v/1_000:.0f}K'
        return f'{v:,}'

    # ── Time window: last 6 CLOSED months (excluye mes en curso) ────────
    import datetime as _dt
    _cur_m  = _dt.date.today().strftime('%Y%m')
    months6 = sorted(m for m in data.get('months', []) if m < _cur_m)[-6:]
    month_lbl = [fmt_month(m) for m in months6]
    n_months  = len(months6)

    # ── Marcador cambio de modelo Valor Pred 90D — Abr 2026 (§86/§87) ────
    # En Abr-2026 MktSci Corp desplegó un nuevo modelo "Fact Based" que bajó
    # el VPU de ~$55-70 a ~$22-26/usuario en todas las tablas BQ.
    # Solo se muestra cuando hay mezcla (al menos 1 mes viejo + 1 mes nuevo).
    _MODEL_BREAK_YYYYMM = '202604'
    _break_idx = next(
        (i for i, m in enumerate(months6) if m >= _MODEL_BREAK_YYYYMM), None
    )
    _show_break = _break_idx is not None and _break_idx > 0

    def _apply_model_break(layout):
        """Añade línea vertical discontinua + callout entre modelo viejo y nuevo."""
        if not _show_break:
            return layout
        x_pos = _break_idx - 0.5          # entre última barra vieja y primera nueva
        shapes = list(layout.get('shapes', []))
        shapes.append({
            'type': 'line', 'xref': 'x', 'yref': 'paper',
            'x0': x_pos, 'x1': x_pos, 'y0': 0, 'y1': 1,
            'line': {'color': '#795548', 'width': 1.5, 'dash': 'dot'},
        })
        layout['shapes'] = shapes
        anns = list(layout.get('annotations', []))
        anns.append({
            'x': x_pos, 'y': 1.05,
            'xref': 'x', 'yref': 'paper',
            'text': '⚠ Nuevo modelo<br>de valor',
            'showarrow': False,
            'font': {'size': 8, 'color': '#795548', 'family': 'Arial'},
            'xanchor': 'center', 'yanchor': 'bottom',
            'bgcolor': 'rgba(255,243,224,0.9)',
            'bordercolor': '#795548', 'borderwidth': 1, 'borderpad': 3,
        })
        layout['annotations'] = anns
        return layout

    # ── Auxiliary data ────────────────────────────────────────────────
    inv_total  = data.get('monthly_inv_total', {})
    cpa_total  = data.get('monthly_cpa_total', {})
    cpa_paid   = data.get('monthly_cpa_paid',  {})
    vpu_prod   = data.get('perf_vpu_prod',     {})
    nr_fm      = data.get('monthly_nr',        {})

    def inv_oc(m):
        return (inv_total.get('UCR Gest', {}).get(m) or 0) + \
               (inv_total.get('OC ACT',   {}).get(m) or 0)

    # ── Section 1: Corp N+R + Valor Predictivo ────────────────────────
    s1_oc   = [sn(OC_UCR_IDS, m)  for m in months6]
    s1_pom  = [sn(POM_IDS, m)     for m in months6]
    s1_oth  = [sn(OTHERS_IDS, m)  for m in months6]
    s1_noat = [sn(NOATRIB_IDS, m) for m in months6]
    s1_tot  = [a+b+c+d for a,b,c,d in zip(s1_oc, s1_pom, s1_oth, s1_noat)]

    # Plan MKT Gestionado = OC+UCR + POM + Others (excluye ORG/No Atribuido)
    # Usa labels de agregado desde plan_nr (calculados por load_plan via plan_lines/plan_rows)
    plan_mkt = [(
        (plan_nr.get('OC + UCR',   {}).get(m) or 0) +
        (plan_nr.get('POM TOTAL',  {}).get(m) or 0) +
        (plan_nr.get('MGM TOTAL',  {}).get(m) or 0) +
        (plan_nr.get('L&P TOTAL',  {}).get(m) or 0)
    ) for m in months6]

    # NR MKT Gestionado = OC+UCR + POM + Others (sin ORG/No Atribuido)
    # Usado para Share MKT y vs Plan '26
    s1_mkt = [a + b + c for a, b, c in zip(s1_oc, s1_pom, s1_oth)]

    # plan_oc: misma razón que plan_oc7 — usar clave agregada 'OC + UCR'
    plan_oc = [(plan_nr.get('OC + UCR', {}).get(m) or 0) for m in months6]

    # Inversión TOTAL (todos los canales, en USD)
    # Usa el nodo raíz 'Total Inversión' de hierarchy_cost — ya incluye toda la propagación bottom-up
    def total_inv(m):
        return (inv_total.get('Total Inversión', {}).get(m) or 0)

    # Valor Predictivo: perf_vpu_prod contiene VALOR TOTAL por canal FM en USD
    def vp_lbl(labels, m):
        return sum((vpu_prod.get(l, {}).get(m) or 0) for l in labels)

    OC_VP_LABELS  = ['UCR Gest', 'OC ACT', 'UCR PRD']
    POM_VP_LABELS = ['POM ADQ', 'POM ACT', 'POM Others']
    OTH_VP_LABELS = ['MGM ADQ', 'MGM ACT', 'L&P ADQ', 'L&P ACT']

    s2v_oc  = [vp_lbl(OC_VP_LABELS,  m) for m in months6]
    s2v_pom = [vp_lbl(POM_VP_LABELS, m) for m in months6]
    s2v_oth = [vp_lbl(OTH_VP_LABELS, m) for m in months6]
    s2v_tot = [sum((vpu_prod.get(l, {}).get(m) or 0) for l in vpu_prod) for m in months6]
    s2v_nat = [max(0, t - a - b - c) for t, a, b, c in zip(s2v_tot, s2v_oc, s2v_pom, s2v_oth)]
    # MKT valor gestionado = OC+UCR + POM + Others (excluye No Atribuido)
    s2v_mkt = [a + b + c for a, b, c in zip(s2v_oc, s2v_pom, s2v_oth)]

    # Plan Valor TOTAL SITE (no solo OC+UCR) — línea punteada en gráfico Valor Predictivo
    plan_val = [(plan_valor.get('Total N+R', {}).get(m) or 0) for m in months6]

    # ── Section 2: New vs Rec + Canal ────────────────────────────────
    has_nr = bool(new_rec_monthly and any(new_rec_monthly.get(m, {}).get('new') for m in months6))
    s_new = [new_rec_monthly.get(m, {}).get('new', 0) if new_rec_monthly else 0 for m in months6]
    s_rec = [new_rec_monthly.get(m, {}).get('rec', 0) if new_rec_monthly else 0 for m in months6]
    s_nrt = [a+b for a, b in zip(s_new, s_rec)]

    # Línea Plan MoM Absoluto para chart 3 (Plan Total N+R por mes)
    plan_tot_line = [(plan_nr.get('Total N+R', {}).get(m) or 0) for m in months6]

    # Vs Plan total site (para tabla debajo del chart 3)
    # Compara total NR actual (corp) vs plan total N+R
    vstot_plan_row = [round((t / p - 1)*100, 1) if p else None
                      for t, p in zip(s1_tot, plan_tot_line)]

    s_can_oc  = [sn(OC_UCR_IDS, m) for m in months6]
    s_can_pom = [sn(POM_IDS, m)    for m in months6]
    s_can_mgm = [sn(MGM_IDS, m)    for m in months6]
    s_can_lp  = [sn(LP_IDS, m)     for m in months6]
    s_can_org = [sn(NOATRIB_IDS, m) for m in months6]

    # ── Plan '26 insights panel (VP de insight — derecha de Sección 2) ──
    # Toma el último mes cerrado como referencia
    last_m   = months6[-1] if months6 else None
    last_lbl = month_lbl[-1] if month_lbl else ''
    plan26_html = ''
    if last_m:
        act_tot  = s1_tot[-1]
        pln_tot  = (plan_nr.get('Total N+R', {}).get(last_m) or 0)
        act_oc   = s1_oc[-1]
        pln_oc   = (plan_nr.get('OC + UCR',  {}).get(last_m) or 0)
        act_pom  = s1_pom[-1]
        pln_pom  = (plan_nr.get('POM TOTAL', {}).get(last_m) or 0)
        act_mkt  = s1_mkt[-1]
        pln_mktv = plan_mkt[-1]

        def _signed_pct(v):
            if v is None: return '—'
            return (f'<span style="color:#00A650">+{v:.1f}%</span>' if v > 0
                    else f'<span style="color:#D32F2F">{v:.1f}%</span>')
        def _signed_pp(v):
            if v is None: return '—'
            return (f'<span style="color:#00A650">+{v:.1f}pp</span>' if v > 0
                    else f'<span style="color:#D32F2F">{v:.1f}pp</span>')

        vs_tot   = round((act_tot / pln_tot - 1)*100, 1) if pln_tot else None
        vs_oc    = round((act_oc  / pln_oc  - 1)*100, 1) if pln_oc  else None
        vs_pom   = round((act_pom / pln_pom - 1)*100, 1) if pln_pom else None

        shr_act  = pct(act_mkt, act_tot)
        shr_pln  = pct(pln_mktv, pln_tot) if pln_tot else 0
        shr_diff = round(shr_act - shr_pln, 1)
        oc_shr   = pct(act_oc,  act_tot)
        pom_shr  = pct(act_pom, act_tot)
        oth_shr  = pct(s1_oth[-1], act_tot)

        # YTD
        ytd_act  = sum(s1_tot)
        ytd_pln  = sum((plan_nr.get('Total N+R', {}).get(m) or 0) for m in months6)
        ytd_vs   = round((ytd_act / ytd_pln - 1)*100, 1) if ytd_pln else None

        plan26_html = (
            f'<div style="background:#1a2744;color:#f5d000;padding:6px 10px;'
            f'border-radius:6px 6px 0 0;font-size:11px;font-weight:700">'
            f'Plan \'26 (% vs Plan) — {last_lbl}</div>'
            f'<div style="background:#f8fafd;border:1px solid #e4e8f0;border-top:none;'
            f'border-radius:0 0 6px 6px;padding:10px;font-size:11px;line-height:1.8">'
            f'<b>Plan {last_lbl}:</b> {fmk(pln_tot)} ({_signed_pct(vs_tot)})<br>'
            f'&nbsp;&nbsp;OC {fmk(pln_oc)} ({_signed_pct(vs_oc)}) | '
            f'POM {fmk(pln_pom)} ({_signed_pct(vs_pom)})<br>'
            f'<b>Share MKT:</b> {shr_act:.0f}% ({_signed_pp(shr_diff)})<br>'
            f'&nbsp;&nbsp;OC {oc_shr:.0f}% | POM {pom_shr:.0f}% | Otros {oth_shr:.0f}%<br>'
            f'<b>YTD</b> — Plan {fmk(ytd_pln)} | Hoy {fmk(ytd_act)} ({_signed_pct(ytd_vs)} Vs Plan)'
            f'</div>'
        )

    # ── Section 3: OC estrategia — 7 meses (más contexto histórico) ──
    months7   = sorted(m for m in data.get('months', []) if m < _cur_m)[-7:]
    month_lbl7 = [fmt_month(m) for m in months7]
    s3_ucr  = [sn(UCRANIA_IDS, m) for m in months7]
    s3_act  = [sn(ACT_REC_IDS, m) for m in months7]
    s3_adh  = [sn(ADHOC_IDS, m)   for m in months7]
    s3_jny  = [nv(JOURNEY_ID, m)  for m in months7]
    s3_tot  = [a+b+c+d for a,b,c,d in zip(s3_ucr, s3_act, s3_adh, s3_jny)]
    # plan_oc7: usa la clave agregada 'OC + UCR' que load_plan() calcula
    # sumando plan_lines rows [6, 10, 17] (OC Recurring + OC Adhoc + Others+Producto).
    # Las hojas 'UCR Gest' y 'OC ACT' no tienen plan_row individual en channels_config.json
    # por lo que plan_nr.get('UCR Gest') daría siempre 0.
    plan_oc7 = [(plan_nr.get('OC + UCR', {}).get(m) or 0) for m in months7]
    inv_act7 = [(inv_total.get('OC ACT',   {}).get(m) or 0) for m in months7]
    inv_ucr7 = [(inv_total.get('UCR Gest', {}).get(m) or 0) for m in months7]

    # ── Color palette ─────────────────────────────────────────────────
    C_OC   = '#F5D000'
    C_POM  = '#1FB8D4'
    C_OTH  = '#7A7D82'
    C_NAT  = '#C8CDD8'
    C_PLAN = '#C00000'
    C_CPA  = '#FF6B35'
    C_UCR  = '#F5D000'
    C_ACT  = '#5899D1'
    C_ADH  = '#1a2744'
    C_JNY  = '#2F9E8F'
    C_NEW  = '#1a2744'
    C_REC  = '#5899D1'
    C_MGM  = '#9C6B3C'
    C_LP   = '#8A4D99'

    # ── Build Plotly trace dicts ──────────────────────────────────────
    def bar_pct_trace(name, vals, totals, color, min_pct=4):
        # Solo mostrar % si el segmento ocupa ≥ min_pct% del total
        texts = [f'{pct(v, t):.0f}%' if (t and pct(v, t) >= min_pct) else ''
                 for v, t in zip(vals, totals)]
        return {'type': 'bar', 'name': name, 'x': month_lbl, 'y': vals,
                'marker': {'color': color, 'line': {'width': 0}},
                'text': texts, 'textposition': 'inside',
                'textfont': {'size': 11, 'color': 'white', 'family': 'Arial'},
                'hovertemplate': '%{y:,.0f} (%{text})<extra>' + name + '</extra>'}

    def bar_abs_trace(name, vals, color):
        return {'type': 'bar', 'name': name, 'x': month_lbl, 'y': vals,
                'marker': {'color': color, 'line': {'width': 0}},
                'hovertemplate': '%{y:,.0f}<extra>' + name + '</extra>'}

    def line_trace(name, vals, color, dash='dot', yaxis='y2', show_vals=False, fmt='$,.0f'):
        v_texts = []
        if show_vals:
            for v in vals:
                if v is None:
                    v_texts.append('')
                elif fmt == '$,.0f':
                    v_texts.append(f'${int(v):,}')
                else:
                    v_texts.append(f'{v:.1f}')
        return {'type': 'scatter', 'name': name, 'x': month_lbl, 'y': vals,
                'mode': 'lines+markers+text' if show_vals else 'lines+markers',
                'text': v_texts if show_vals else None,
                'textposition': 'top center',
                'textfont': {'size': 9, 'color': color},
                'line': {'color': color, 'dash': dash, 'width': 2},
                'marker': {'size': 6, 'color': color}, 'yaxis': yaxis,
                'hovertemplate': '%{y:,.1f}<extra>' + name + '</extra>'}

    def tot_annotations(totals, y_vals=None, fmt_fn=None, x_labels=None):
        """Etiqueta el total encima de cada barra apilada."""
        xlbls = x_labels if x_labels is not None else month_lbl
        yv    = y_vals if y_vals is not None else totals
        anns  = []
        for i, (t, y) in enumerate(zip(totals, yv)):
            if i >= len(xlbls): break
            if t:
                label = fmt_fn(t) if fmt_fn else (
                    f'{t/1_000_000:.2f}M' if t >= 1_000_000 else f'{t/1_000:.0f}K')
                anns.append({'x': xlbls[i], 'y': y, 'text': f'<b>{label}</b>',
                             'xref': 'x', 'yref': 'y', 'showarrow': False,
                             'font': {'size': 11, 'color': '#1a2744', 'family': 'Arial'},
                             'yanchor': 'bottom', 'xanchor': 'center', 'yshift': 4})
        return anns

    def growth_annotations(totals, x_labels=None, use_arrows=False):
        """Anotaciones MoM entre barras. use_arrows=True → callout estilo PPT con flecha."""
        xlbls = x_labels if x_labels is not None else month_lbl
        anns  = []
        for i in range(1, len(totals)):
            if i >= len(xlbls): break
            if totals[i-1] and totals[i]:
                g   = (totals[i] - totals[i-1]) / totals[i-1] * 100
                col = '#0d7a3e' if g > 0 else '#c5221f'
                if use_arrows:
                    # Callout con flecha apuntando al tope de la barra más alta
                    anns.append({
                        'x': xlbls[i], 'y': max(totals[i], totals[i-1]),
                        'text': ('+' if g > 0 else '') + f'{g:.0f}%',
                        'xref': 'x', 'yref': 'y',
                        'showarrow': True, 'arrowhead': 2, 'arrowsize': 0.9,
                        'arrowwidth': 1.5, 'arrowcolor': col,
                        'ax': 0, 'ay': -52,
                        'bgcolor': 'white', 'bordercolor': col,
                        'borderwidth': 1.5, 'borderpad': 4,
                        'font': {'size': 9, 'color': col, 'family': 'Arial', 'weight': 'bold'},
                        'xanchor': 'center', 'yanchor': 'bottom',
                    })
                else:
                    anns.append({'x': xlbls[i], 'y': max(totals[i], totals[i-1]) * 1.06,
                                 'text': ('+' if g > 0 else '') + f'{g:.0f}%',
                                 'xref': 'x', 'yref': 'y', 'showarrow': False,
                                 'font': {'size': 9, 'color': col, 'family': 'Arial'},
                                 'yanchor': 'bottom', 'xanchor': 'center'})
        return anns

    base_layout = {
        'barmode': 'stack', 'plot_bgcolor': 'white', 'paper_bgcolor': 'white',
        'font': {'family': 'Arial,sans-serif', 'size': 11, 'color': '#333'},
        'legend': {'orientation': 'h', 'y': -0.22, 'x': 0, 'font': {'size': 10},
                   'bgcolor': 'rgba(0,0,0,0)'},
        'margin': {'l': 50, 'r': 60, 't': 35, 'b': 90},
        'yaxis': {'gridcolor': '#f0f0f0', 'title': ''},
        'yaxis2': {'overlaying': 'y', 'side': 'right', 'gridcolor': 'transparent',
                   'tickformat': '$,.0f', 'title': 'CPA'},
        'hovermode': 'x unified',
    }

    # Pre-compute KPI rows — todos a nivel TOTAL SITE (igual que PPT)
    # Share MKT = MKT Gestionado (OC+UCR+POM+Others) / Total site NR
    share_mkt_row  = [pct(m, t) for m, t in zip(s1_mkt, s1_tot)]
    # vs Plan '26 = Total N+R Corp / Plan Total N+R − 1  (igual que PPT: total vs total)
    vsplan_row     = [round((t / p - 1) * 100, 1) if p else None
                      for t, p in zip(s1_tot, plan_tot_line)]
    # Inv total site: nodo raíz 'Total Inversión' ya calculado en processors (en USD)
    inv_total_row  = [total_inv(m) / 1_000_000 for m in months6]
    # VPU Total = Valor Total Site / NR Total Site (USD por usuario)
    vpu_row        = [round(s2v_tot[i] / s1_tot[i]) if s1_tot[i] else 0 for i in range(n_months)]
    # ROAS = VPU Total / CPA Paid (igual que en PPT: 54/13≈4, 60/12=5)
    roas_row       = [round(vpu_row[i] / (cpa_paid.get(months6[i]) or 1))
                      if (vpu_row[i] and cpa_paid.get(months6[i])) else 0
                      for i in range(n_months)]
    # Share Valor MKT = Valor MKT Gestionado (OC+UCR+POM+Others) / Valor Total Site
    share_v_row    = [pct(m, t) for m, t in zip(s2v_mkt, s2v_tot)]
    # vs Plan Valor = Valor Total actual / Plan Valor Total Site − 1
    vsplan_val_row = [round((v / p - 1) * 100, 1) if p else None
                      for v, p in zip(s2v_tot, plan_val)]

    # CPA Paid values para mostrar en línea
    cpa_paid_vals = [cpa_paid.get(m) for m in months6]
    cpa_total_vals = [cpa_total.get(m) for m in months6]

    # Chart 1 — N+R Corp segments
    c1_traces = [
        bar_pct_trace('No Atribuído', s1_noat, s1_tot, C_NAT),
        bar_pct_trace('Others',       s1_oth,  s1_tot, C_OTH),
        bar_pct_trace('POM',          s1_pom,  s1_tot, C_POM),
        bar_pct_trace('OC + UCR',     s1_oc,   s1_tot, C_OC),
        line_trace('Plan MKT Gestionado', plan_mkt, C_PLAN, 'dash', 'y'),
        line_trace('CPA Paid', cpa_paid_vals, C_CPA, 'solid', 'y2', show_vals=True),
    ]
    c1_layout = dict(**base_layout)
    c1_layout['yaxis2'] = {'overlaying': 'y', 'side': 'right', 'gridcolor': 'transparent',
                           'tickformat': '$,.0f', 'title': '', 'rangemode': 'tozero'}
    c1_layout['margin'] = {'l': 50, 'r': 60, 't': 75, 'b': 90}
    c1_layout['annotations'] = (
        tot_annotations(s1_tot, fmt_fn=lambda v: f'{v/1_000_000:.2f}') +
        growth_annotations(s1_tot, use_arrows=True)
    )

    # Chart 2 — Valor Predictivo
    c2_traces = [
        bar_pct_trace('No Atribuído', s2v_nat, s2v_tot, C_NAT),
        bar_pct_trace('Others',       s2v_oth, s2v_tot, C_OTH),
        bar_pct_trace('POM',          s2v_pom, s2v_tot, C_POM),
        bar_pct_trace('OC + UCR',     s2v_oc,  s2v_tot, C_OC),
        line_trace('Plan Valor', plan_val, C_PLAN, 'dash', 'y'),
        line_trace('ROAS', roas_row, '#9B59B6', 'solid', 'y2', show_vals=True, fmt='x'),
    ]
    c2_layout = dict(**base_layout)
    c2_layout['yaxis2'] = {'overlaying': 'y', 'side': 'right', 'gridcolor': 'transparent',
                           'title': '', 'rangemode': 'tozero'}
    c2_layout['margin'] = {'l': 50, 'r': 60, 't': 75, 'b': 90}
    c2_layout['annotations'] = (
        tot_annotations(s2v_tot, fmt_fn=lambda v: f'{v/1_000_000:.1f}' if v >= 1e6 else f'{v/1_000:.0f}K')
        + growth_annotations(s2v_tot, use_arrows=True)
    )
    _apply_model_break(c2_layout)

    # Chart 3 — New vs Recovered + línea Plan MoM Absoluto
    # Colores: Recovered=azul oscuro, New=azul claro (igual que PPT)
    if has_nr:
        c3_traces = [
            bar_pct_trace('Recovered', s_rec, s_nrt, C_NEW),   # C_NEW = '#1a2744' oscuro
            bar_pct_trace('New',       s_new, s_nrt, C_REC),   # C_REC = '#5899D1' claro
            line_trace('Plan MoM (Absoluto)', plan_tot_line, C_PLAN, 'dot', 'y'),
        ]
    else:
        c3_traces = [
            {'type': 'scatter', 'x': month_lbl, 'y': [0]*n_months,
             'mode': 'lines', 'name': 'Pendiente — ejecutar query New/Rec',
             'line': {'color': '#aaa'}},
            line_trace('Plan MoM (Absoluto)', plan_tot_line, C_PLAN, 'dot', 'y'),
        ]
    c3_layout = dict(**base_layout)
    c3_layout['annotations'] = (
        tot_annotations(s1_tot) +         # total absoluto encima de cada barra
        growth_annotations(s1_tot)        # %MoM y %YoY
    )
    c3_layout['yaxis2'] = {'overlaying': 'y', 'side': 'right', 'gridcolor': 'transparent',
                            'showticklabels': False}

    # Tabla debajo del chart 3 — Vs Plan (inline HTML, sin depender de HDR/krow que se definen después)
    _hdr_nr = ('<tr style="background:#1a2744;color:#f5d000">'
               '<th style="padding:4px 8px;text-align:left;font-size:11px">KPI</th>'
               + ''.join(f'<th style="padding:4px 8px;text-align:right;font-size:11px">{l}</th>'
                         for l in month_lbl) + '</tr>')
    _cells_nr = ''.join(
        f'<td style="padding:3px 8px;text-align:right;font-size:11px">'
        f'{"—" if v is None else (f"+{v:.1f}%" if v > 0 else f"{v:.1f}%")}</td>'
        for v in vstot_plan_row)
    t_nr = ('<table style="width:100%;border-collapse:collapse;margin-top:8px">'
            + _hdr_nr
            + f'<tr><td style="padding:3px 8px;font-size:11px">Vs Plan (%)</td>{_cells_nr}</tr>'
            + '</table>')

    # Chart 4 — N+R por Canal (con valores K dentro de las barras)
    def bar_abs_k(name, vals, color):
        """Barra absoluta con valor en K dentro del segmento (mínimo 40K para mostrar)."""
        texts = [f'{int(v/1000)}K' if v >= 40_000 else '' for v in vals]
        return {'type': 'bar', 'name': name, 'x': month_lbl, 'y': vals,
                'marker': {'color': color, 'line': {'width': 0}},
                'text': texts, 'textposition': 'inside',
                'textfont': {'size': 10, 'color': 'white', 'family': 'Arial,sans-serif'},
                'hovertemplate': '%{y:,.0f}<extra>' + name + '</extra>'}

    c4_traces = [
        bar_abs_k('No Atribuído / Org',    s_can_org, C_NAT),
        bar_abs_k('L&P',                   s_can_lp,  C_LP),
        bar_abs_k('MGM',                   s_can_mgm, C_MGM),
        bar_abs_k('POM',                   s_can_pom, C_POM),
        bar_abs_k('Own Channels (OC+UCR)', s_can_oc,  C_OC),
    ]
    c4_layout = dict(**base_layout)
    c4_layout['annotations'] = (
        tot_annotations(s1_tot) +
        growth_annotations(s1_tot)
    )
    c4_layout.pop('yaxis2', None)

    # Chart 5 — OC estrategia: valores ABSOLUTOS dentro de barras, 7 meses
    def bar_abs_s3(name, vals, color, min_show=3000):
        """Barra con valor absoluto en K dentro del segmento."""
        texts = [f'{int(v/1000)}' if v >= min_show else '' for v in vals]
        return {'type': 'bar', 'name': name, 'x': month_lbl7, 'y': vals,
                'marker': {'color': color, 'line': {'width': 0}},
                'text': texts, 'textposition': 'inside',
                'textfont': {'size': 11, 'color': 'white', 'family': 'Arial,sans-serif'},
                'hovertemplate': '%{y:,.0f}<extra>' + name + '</extra>'}

    def line_trace7(name, vals, color, dash='dot', yaxis='y2', show_vals=False):
        txts = [f'${int(v)}' if v else '' for v in vals] if show_vals else None
        return {'type': 'scatter', 'name': name, 'x': month_lbl7, 'y': vals,
                'mode': 'lines+markers+text' if show_vals else 'lines+markers',
                'text': txts, 'textposition': 'top center',
                'textfont': {'size': 9, 'color': color},
                'line': {'color': color, 'dash': dash, 'width': 2},
                'marker': {'size': 6}, 'yaxis': yaxis,
                'hovertemplate': '%{y:,.1f}<extra>' + name + '</extra>'}

    c5_traces = [
        bar_abs_s3('Ucrania',         s3_ucr, C_UCR),
        bar_abs_s3('Activation Rec',  s3_act, C_ACT),
        bar_abs_s3('Ad Hoc',          s3_adh, C_ADH),
        bar_abs_s3('Resto Rec (JNY)', s3_jny, C_JNY),
        line_trace7('Plan N+R OC', plan_oc7, C_PLAN, 'dash', 'y'),
        line_trace7('CPA Paid', [cpa_paid.get(m) for m in months7], C_CPA, show_vals=True),
    ]
    c5_layout = {
        'barmode': 'stack', 'plot_bgcolor': 'white', 'paper_bgcolor': 'white',
        'font': {'family': 'Arial,sans-serif', 'size': 11, 'color': '#333'},
        'legend': {'orientation': 'h', 'y': -0.22, 'x': 0, 'font': {'size': 10}},
        'margin': {'l': 50, 'r': 60, 't': 35, 'b': 90},
        'yaxis': {'gridcolor': '#f0f0f0', 'title': 'N+R (Miles)'},
        'yaxis2': {'overlaying': 'y', 'side': 'right', 'gridcolor': 'transparent',
                   'tickformat': '$,.0f', 'title': '', 'rangemode': 'tozero'},
        'hovermode': 'x unified',
        'annotations': tot_annotations(s3_tot, fmt_fn=lambda v: f'{int(v/1000)}K',
                                        x_labels=month_lbl7) +
                       growth_annotations(s3_tot, x_labels=month_lbl7),
    }

    # ── Serialize chart JSONs ─────────────────────────────────────────
    def cj(traces, layout):
        return _json.dumps({'data': traces, 'layout': layout}, ensure_ascii=False)

    c1j, c2j, c3j, c4j, c5j = cj(c1_traces,c1_layout), cj(c2_traces,c2_layout), \
        cj(c3_traces,c3_layout), cj(c4_traces,c4_layout), cj(c5_traces,c5_layout)

    cfg_json = _json.dumps({
        'displaylogo': False,
        'modeBarButtonsToRemove': ['lasso2d', 'select2d'],
        'toImageButtonOptions': {'format': 'png', 'height': 520, 'width': 980, 'scale': 2}
    }, ensure_ascii=False)

    # ── KPI tables ────────────────────────────────────────────────────
    HDR = ('<tr style="background:#1a2744;color:#f5d000">'
           '<th style="padding:4px 8px;text-align:left;font-size:11px">KPI</th>'
           + ''.join(f'<th style="padding:4px 8px;text-align:right;font-size:11px">{l}</th>'
                     for l in month_lbl) + '</tr>')

    def krow(label, vals, fmt):
        cells = ''.join(
            f'<td style="padding:3px 8px;text-align:right;font-size:11px">'
            f'{fmt(v) if v is not None else "—"}</td>'
            for v in vals
        )
        return f'<tr><td style="padding:3px 8px;font-size:11px;white-space:nowrap">{label}</td>{cells}</tr>'

    def pcts(v): return f'{v:.1f}%'
    def ups(v):  return f'+{v:.1f}%' if v > 0 else f'{v:.1f}%'
    def uf(v):   return f'${v:.1f}M'
    def us(v):   return f'${v:.0f}'

    # t1 — N+R in App (igual que PPT: Share de MKT / vs Plan / Inv / CPA Paid)
    t1 = ('<table style="width:100%;border-collapse:collapse;margin-top:8px">'
          + HDR
          + krow('Share de MKT (%)', share_mkt_row, pcts)
          + krow("vs Plan '26 (%)", vsplan_row, ups)
          + krow('Inv. Total (M USD)', inv_total_row, uf)
          + krow('CPA Paid (USD)', [cpa_paid.get(m) for m in months6], us)
          + '</table>')

    # t2 — Valor Predictivo in App (igual que PPT: Share MKT / vs Plan / ROAS / VPU Total)
    t2 = ('<table style="width:100%;border-collapse:collapse;margin-top:8px">'
          + HDR
          + krow('Share MKT (%)', share_v_row, pcts)
          + krow('vs Plan Valor (%)', vsplan_val_row, ups)
          + krow('ROAS', roas_row, lambda v: f'{v:.0f}x')
          + krow('VPU Total (USD)', vpu_row, lambda v: f'${int(v):,}')
          + '</table>')

    # KPI table Section 3 usa months7 (7 meses)
    _s3_tot_m6 = [sn(OC_UCR_IDS, m) for m in months6]  # para share vs total site (months6)
    share_oc3 = [pct(o, t) for o, t in zip(s3_tot, [sn(list(OC_UCR_IDS)+list(POM_IDS)+list(OTHERS_IDS)+list(NOATRIB_IDS), m) for m in months7])]
    HDR7 = ('<tr style="background:#1a2744;color:#f5d000"><th style="padding:4px 8px;text-align:left;font-size:11px">KPI</th>'
            + ''.join(f'<th style="padding:4px 8px;text-align:right;font-size:11px">{l}</th>' for l in month_lbl7) + '</tr>')
    def krow7(label, vals, fmt):
        cells = ''.join(
            f'<td style="padding:3px 8px;text-align:right;font-size:11px">'
            f'{fmt(v) if v is not None else "—"}</td>'
            for v in vals)
        return f'<tr><td style="padding:3px 8px;font-size:11px;white-space:nowrap">{label}</td>{cells}</tr>'
    def inv_k(v):
        return f'${int((v or 0)/1000)}K' if v else '—'
    t3 = ('<table style="width:100%;border-collapse:collapse;margin-top:8px">'
          + HDR7
          + krow7('Share N+R OC+UCR (%)', share_oc3, pcts)
          + krow7('N+R OC+UCR', s3_tot, lambda v: fmk(v))
          + krow7('CPA (USD)', [cpa_total.get(m) for m in months7], us)
          + krow7('CPA Paid (USD)', [cpa_paid.get(m) for m in months7], us)
          + krow7('ROAS Paid', [round(
              ((vpu_prod.get('UCR Gest',{}).get(m,0) or 0) + (vpu_prod.get('OC ACT',{}).get(m,0) or 0))
              / max(inv_oc(m), 1), 1) for m in months7], lambda v: f'{v:.1f}x')
          + krow7('Inv. Act (USD)', inv_act7, inv_k)
          + krow7('Inv. Ucr (USD)', inv_ucr7, inv_k)
          + '</table>')

    # ── Highlights ────────────────────────────────────────────────────
    # Highlights usa los 7 meses de Section 3; pasa s3_tot (months7-based)
    highlights_html = _rep_highlights(
        months7, month_lbl7, s3_ucr, s3_act, s3_adh, s3_jny,
        s3_tot, s1_oc, s1_tot, cpa_paid, inv_oc
    )

    # ── CSS ───────────────────────────────────────────────────────────
    css = '''<style>
.rep-wrap{padding:20px;font-family:Arial,sans-serif;background:#f5f7fa}
.rep-sec{margin-bottom:24px;background:#fff;border:1px solid #e4e8f0;
         border-radius:8px;padding:20px}
.rep-sec-ttl{font-size:13px;font-weight:700;color:#1a2744;
             border-bottom:2px solid #F5D000;padding-bottom:6px;margin-bottom:16px}
.rep-g2{display:grid;grid-template-columns:1fr 1fr;gap:18px}
.rep-g31{display:grid;grid-template-columns:2.2fr 1fr;gap:18px}
.rep-box{background:#f8fafd;border:1px solid #e4e8f0;border-radius:6px;padding:12px}
.rep-bttl{font-size:12px;font-weight:700;color:#1a2744;margin-bottom:6px;
          display:flex;justify-content:space-between;align-items:center}
.rep-dl{font-size:10px;padding:3px 10px;border:1px solid #1a2744;border-radius:4px;
        background:#fff;color:#1a2744;cursor:pointer}
.rep-dl:hover{background:#1a2744;color:#f5d000}
.rep-hl{font-size:11px;line-height:1.65;color:#333}
.rep-hl h4{font-size:11px;font-weight:700;margin:8px 0 2px}
.rep-hl ul{margin:2px 0 6px 0;padding-left:14px}
.rep-hl li{margin:1px 0}
</style>'''

    # ── HTML Assembly (string concatenation to avoid f-string/JSON issues) ──
    nr_pending = ('' if has_nr else
                  ' <em style="font-weight:400;font-size:10px;color:#aaa">'
                  '(pendiente new_rec query)</em>')

    html  = '<div class="rep-wrap">\n' + css + '\n'

    html += '<script>\nvar _repCfg=' + cfg_json + ';\n'
    html += ('function repDL(id,fn){'
             'var c=Object.assign({filename:fn},_repCfg.toImageButtonOptions);'
             'Plotly.downloadImage(document.getElementById(id),c);}\n')
    html += ('function repDLTable(tblId,fn){'
             'var tbl=document.getElementById(tblId);'
             'if(!tbl){alert("Tabla no encontrada");return;}'
             'var rows=Array.from(tbl.querySelectorAll("tr"));'
             'var csv=rows.map(function(r){'
             'return Array.from(r.querySelectorAll("th,td")).map(function(c){'
             'return "\\""+c.textContent.trim().replace(/\\"/g,"\\"\\"")+"\\""'
             '}).join(",");}).join("\\n");'
             'var blob=new Blob(["\\uFEFF"+csv],{type:"text/csv;charset=utf-8;"});'
             'var a=document.createElement("a");'
             'a.href=URL.createObjectURL(blob);'
             'a.download=fn+".csv";'
             'document.body.appendChild(a);a.click();document.body.removeChild(a);}\n'
             '</script>\n')

    # Section 1
    html += ('<div class="rep-sec"><div class="rep-sec-ttl">'
             '&#128202; N+R in App &amp; Valor Predictivo &mdash; Vista Corporativa</div>\n'
             '<div class="rep-g2">\n')
    html += ('<div class="rep-box"><div class="rep-bttl"><span>N+R in App</span>'
             '<button class="rep-dl" onclick="repDL(\'rep-c1\',\'MLM_NR_Corp\')">&#8595; PNG</button>'
             '</div><div id="rep-c1" style="height:300px"></div>' + t1 + '</div>\n')
    html += ('<div class="rep-box"><div class="rep-bttl"><span>Valor Predictivo in App</span>'
             '<button class="rep-dl" onclick="repDL(\'rep-c2\',\'MLM_Valor_Corp\')">&#8595; PNG</button>'
             '</div><div id="rep-c2" style="height:300px"></div>' + t2 + '</div>\n')
    html += '</div></div>\n'

    # Section 2 — 3 columnas: New/Rec | Por Canal | Plan '26 + Highlights
    # CSS adicional para 3 columnas
    html += ('<style>.rep-g3{display:grid;grid-template-columns:1fr 1fr 0.65fr;gap:14px}'
             '.rep-plan26{font-size:11px;line-height:1.8;color:#1a2744}</style>\n')
    html += ('<div class="rep-sec"><div class="rep-sec-ttl">'
             '&#128200; N+R &mdash; New &amp; Recovered | Por Canal</div>\n'
             '<div class="rep-g3">\n')
    html += ('<div class="rep-box"><div class="rep-bttl"><span>N+R (New + Recovered)' + nr_pending + '</span>'
             '<button class="rep-dl" onclick="repDL(\'rep-c3\',\'MLM_NewRec\')">&#8595; PNG</button>'
             '</div><div id="rep-c3" style="height:300px"></div>' + t_nr + '</div>\n')
    html += ('<div class="rep-box"><div class="rep-bttl"><span>N+R por Canal (Miles)</span>'
             '<button class="rep-dl" onclick="repDL(\'rep-c4\',\'MLM_NR_Canal\')">&#8595; PNG</button>'
             '</div><div id="rep-c4" style="height:300px"></div></div>\n')
    # Panel derecho: Plan '26 + Highlights del mes
    html += ('<div style="display:flex;flex-direction:column;gap:10px">\n'
             + (plan26_html if plan26_html else
                '<div style="font-size:11px;color:#aaa">Sin datos de plan</div>')
             + '\n<div class="rep-hl" style="flex:1">' + highlights_html + '</div>\n</div>\n')
    html += '</div></div>\n'

    # Section 3
    html += ('<div class="rep-sec"><div class="rep-sec-ttl">'
             '&#127919; Evoluci&oacute;n N+R por Estrategia OC+UCR</div>\n'
             '<div class="rep-g31">\n')
    html += ('<div class="rep-box"><div class="rep-bttl"><span>N+R por Estrategia OC</span>'
             '<button class="rep-dl" onclick="repDL(\'rep-c5\',\'MLM_OC_Estrategia\')">&#8595; PNG</button>'
             '</div><div id="rep-c5" style="height:300px"></div>' + t3 + '</div>\n')
    html += '<div class="rep-hl">' + highlights_html + '</div>\n'
    html += '</div></div>\n'

    # Inline Plotly init script
    html += '<script>\n(function(){\n'
    html += '  var cfg=' + cfg_json + ';\n'
    html += '  var charts=[["rep-c1",' + c1j + '],["rep-c2",' + c2j + '],\n'
    html += '    ["rep-c3",' + c3j + '],["rep-c4",' + c4j + '],["rep-c5",' + c5j + ']];\n'
    html += ('  function init(){charts.forEach(function(c){'
             'var el=document.getElementById(c[0]);'
             'if(el)Plotly.newPlot(el,c[1].data,c[1].layout,cfg);})}\n')
    html += ('  if(document.readyState==="loading"){'
             'document.addEventListener("DOMContentLoaded",init);}else{init();}\n')
    html += '})();\n</script>\n</div>'

    return html

