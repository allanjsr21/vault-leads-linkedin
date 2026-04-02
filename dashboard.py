"""
Dashboard da Vault Capital — Agente de Leads LinkedIn
Rode com: streamlit run dashboard.py
"""

import sys
import os
import time
import pandas as pd
import streamlit as st

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

st.set_page_config(
    page_title="Vault Capital — Leads LinkedIn",
    page_icon="⚡",
    layout="wide",
)

# ── Estilo ─────────────────────────────────────────────────────────────────────
st.markdown("""
<link rel="stylesheet"
      href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css"
      crossorigin="anonymous" />
<style>
    [data-testid="stAppViewContainer"] {
        background: #08080f;
    }
    [data-testid="stSidebar"] {
        background: #0c0c16;
        border-right: 1px solid #1c1c2e;
    }
    h1, h2, h3, h4 { color: #f0c040 !important; }

    .stButton > button {
        background: linear-gradient(135deg, #f0c040 0%, #c89a00 100%);
        color: #000;
        font-weight: 600;
        border-radius: 10px;
        border: none;
        padding: 0.55rem 1.5rem;
        letter-spacing: 0.3px;
        transition: all 0.18s ease;
        box-shadow: 0 2px 10px rgba(240, 192, 64, 0.15);
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #ffd84d 0%, #f0c040 100%);
        box-shadow: 0 4px 18px rgba(240, 192, 64, 0.3);
        transform: translateY(-1px);
        color: #000;
    }
    .stButton > button:active { transform: translateY(0); }

    .metric-card {
        background: linear-gradient(160deg, #111120 0%, #14141f 100%);
        border: 1px solid #22223a;
        border-radius: 16px;
        padding: 1.4rem 1.5rem 1.2rem;
        text-align: center;
        transition: border-color 0.2s, box-shadow 0.2s;
    }
    .metric-card:hover {
        border-color: #f0c040;
        box-shadow: 0 0 20px rgba(240, 192, 64, 0.07);
    }
    .metric-icon {
        font-size: 1.3rem;
        color: #f0c040;
        opacity: 0.75;
        margin-bottom: 0.5rem;
    }
    .metric-number {
        font-size: 2.4rem;
        font-weight: 700;
        color: #f0c040;
        letter-spacing: -1.5px;
        line-height: 1;
    }
    .metric-label {
        font-size: 0.72rem;
        color: #555577;
        margin-top: 6px;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 500;
    }

    .log-box {
        background: #0c0c16;
        border: 1px solid #1c1c2e;
        border-radius: 12px;
        padding: 1rem 1.2rem;
        font-family: 'Courier New', monospace;
        font-size: 0.75rem;
        color: #5a6080;
        height: 220px;
        overflow-y: auto;
        line-height: 1.6;
    }

    .sidebar-logo {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 0.2rem 0 0.5rem;
    }
    .sidebar-logo-icon {
        width: 34px;
        height: 34px;
        background: linear-gradient(135deg, #f0c040, #c89a00);
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1rem;
        color: #000;
    }
    .sidebar-logo-text {
        font-size: 1.05rem;
        font-weight: 700;
        color: #f0c040;
        letter-spacing: 0.5px;
    }
    .sidebar-logo-sub {
        font-size: 0.7rem;
        color: #44445a;
        margin-top: 1px;
        letter-spacing: 0.3px;
    }

    .section-header {
        display: flex;
        align-items: center;
        gap: 8px;
        color: #f0c040;
        font-size: 1rem;
        font-weight: 600;
        margin: 0.8rem 0 0.5rem;
    }
    .section-header i { font-size: 0.85rem; opacity: 0.8; }

    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        padding: 2px 8px;
        border-radius: 20px;
        font-size: 0.72rem;
        font-weight: 500;
    }
    .badge-pending  { background: #2a2200; color: #f0c040; }
    .badge-approved { background: #002a12; color: #34d399; }
    .badge-sent     { background: #001a2a; color: #60a5fa; }
    .badge-failed   { background: #2a0000; color: #f87171; }
    .badge-skipped  { background: #1a1a1a; color: #6b7280; }

    /* Score badges */
    .score-pill {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        padding: 2px 9px;
        border-radius: 20px;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.3px;
    }
    .score-hot  { background: #2a0e00; color: #fb923c; border: 1px solid #7c2d12; }
    .score-warm { background: #1a1a00; color: #facc15; border: 1px solid #713f12; }
    .score-cold { background: #0d1117; color: #6b7280; border: 1px solid #1f2937; }

    /* Score legend */
    .score-legend {
        display: flex;
        gap: 12px;
        align-items: center;
        font-size: 0.72rem;
        color: #44445a;
        margin-bottom: 0.6rem;
    }

    [data-testid="stDataFrame"] {
        border: 1px solid #22223a !important;
        border-radius: 12px !important;
    }
    hr { border-color: #1c1c2e !important; }

    .stTextInput > div > div > input {
        background: #111120 !important;
        border: 1px solid #22223a !important;
        border-radius: 8px !important;
        color: #c8c8e0 !important;
    }
    [data-baseweb="select"] > div {
        background: #111120 !important;
        border: 1px solid #22223a !important;
        border-radius: 8px !important;
        color: #c8c8e0 !important;
    }
    .stRadio > div { gap: 6px; }
</style>
""", unsafe_allow_html=True)


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="sidebar-logo">
        <div class="sidebar-logo-icon"><i class="fa-solid fa-bolt"></i></div>
        <div>
            <div class="sidebar-logo-text">Vault Capital</div>
            <div class="sidebar-logo-sub">Agente de Leads LinkedIn</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    st.markdown("""
    <div class="section-header">
        <i class="fa-solid fa-crosshairs"></i> Público-Alvo
    </div>
    """, unsafe_allow_html=True)

    profile_choice = st.radio(
        "perfil",
        options=["1", "2"],
        format_func=lambda x: "Autocustódia" if x == "1" else "Consultoria",
        label_visibility="collapsed",
    )

    st.markdown("---")

    st.markdown("""
    <div class="section-header">
        <i class="fa-solid fa-sliders"></i> Ações
    </div>
    """, unsafe_allow_html=True)

    btn_collect     = st.button("Coletar Leads",      icon=":material/search:",        use_container_width=True)
    btn_send        = st.button("Enviar DMs",          icon=":material/send:",          use_container_width=True)
    btn_sync        = st.button("Sincronizar Sheets",  icon=":material/sync:",          use_container_width=True)
    btn_load_sheets = st.button("Carregar do Sheets",  icon=":material/cloud_download:", use_container_width=True)
    btn_clear       = st.button("Limpar tabela",       icon=":material/delete:",        use_container_width=True)

    st.markdown("---")
    st.markdown("""
    <div style="font-size:0.72rem; color:#44445a; line-height:1.6;">
        <i class="fa-solid fa-circle-info" style="color:#f0c040; opacity:0.5;"></i>
        Leads aprovados no Google Sheets<br>são enviados automaticamente.
    </div>
    """, unsafe_allow_html=True)


# ── Helpers ────────────────────────────────────────────────────────────────────
def apply_profile(choice: str):
    import config
    profile = config.AUDIENCE_PROFILES[choice]
    config.SEARCH_KEYWORDS = profile["keywords"]
    config.LOCATION_FILTER = profile.get("location_filter", "Brazil")
    config.SHEET_NAME      = profile["sheet_name"]
    config.LEADS_CSV       = profile["leads_csv"]
    config.DM_TEMPLATE     = profile["dm_template"]
    import leads_manager
    leads_manager.LEADS_CSV = config.LEADS_CSV
    return profile


@st.cache_data(ttl=30)
def load_dataframe(sheet_name: str) -> pd.DataFrame:
    from dataclasses import asdict
    from leads_manager import _use_sheets

    if _use_sheets():
        from sheets_manager import sheets_load_leads
        leads = sheets_load_leads()
    else:
        from leads_manager import _csv_load_leads
        leads = _csv_load_leads()

    if not leads:
        return pd.DataFrame(columns=["name", "linkedin_url", "job_title", "company", "location", "status", "source", "sent_at"])
    return pd.DataFrame([asdict(l) for l in leads.values()])


def status_badge(status: str) -> str:
    icons = {
        "pending":  ('<i class="fa-regular fa-clock"></i>',        "badge-pending"),
        "approved": ('<i class="fa-solid fa-circle-check"></i>',    "badge-approved"),
        "sent":     ('<i class="fa-solid fa-paper-plane"></i>',     "badge-sent"),
        "failed":   ('<i class="fa-solid fa-triangle-exclamation"></i>', "badge-failed"),
        "skipped":  ('<i class="fa-solid fa-minus"></i>',           "badge-skipped"),
    }
    icon_html, cls = icons.get(status, ('<i class="fa-solid fa-circle"></i>', "badge-skipped"))
    return f'<span class="status-badge {cls}">{icon_html} {status}</span>'


def status_color(status: str) -> str:
    return {
        "pending":  "🟡",
        "approved": "🟢",
        "sent":     "✅",
        "failed":   "🔴",
        "skipped":  "⚪",
    }.get(status, "⚫")


def compute_scores(df: pd.DataFrame) -> pd.DataFrame:
    """Adiciona colunas 'score' e 'prioridade' ao dataframe."""
    from scorer import score_lead, score_label
    from leads_manager import Lead

    scores  = []
    labels  = []
    for _, row in df.iterrows():
        lead = Lead(
            linkedin_url = row.get("linkedin_url", ""),
            name         = row.get("name", ""),
            job_title    = row.get("job_title", ""),
            company      = row.get("company", ""),
            location     = row.get("location", ""),
            status       = row.get("status", "pending"),
            source       = row.get("source", ""),
        )
        s = score_lead(lead)
        scores.append(s)
        labels.append(score_label(s))

    df = df.copy()
    df["score"]      = scores
    df["prioridade"] = labels
    return df


# ── Estado de sessão ───────────────────────────────────────────────────────────
_EMPTY_DF = pd.DataFrame(columns=["name", "linkedin_url", "job_title", "company", "location", "status", "source", "sent_at"])

if "logs"       not in st.session_state: st.session_state.logs       = []
if "running"    not in st.session_state: st.session_state.running    = False
if "sheet_url"  not in st.session_state: st.session_state.sheet_url  = ""
if "session_df" not in st.session_state: st.session_state.session_df = _EMPTY_DF.copy()


def add_log(msg: str):
    ts = time.strftime("%H:%M:%S")
    st.session_state.logs.append(f"[{ts}] {msg}")
    if len(st.session_state.logs) > 200:
        st.session_state.logs = st.session_state.logs[-200:]


# ── Config de perfil ───────────────────────────────────────────────────────────
import config
profile_data = apply_profile(profile_choice)

# ── Cabeçalho ──────────────────────────────────────────────────────────────────
profile_label = "Autocustódia" if profile_choice == "1" else "Consultoria"
profile_icon  = "fa-shield-halved" if profile_choice == "1" else "fa-briefcase"

st.markdown(f"""
<div style="display:flex; align-items:center; gap:12px; margin-bottom:0.2rem;">
    <div style="font-size:1.8rem; font-weight:700; color:#f0c040; letter-spacing:-0.5px;">
        Vault Capital
    </div>
    <div style="background:#1c1c2e; border:1px solid #2a2a4a; border-radius:20px;
                padding:3px 12px; font-size:0.75rem; color:#9090b0; font-weight:500;">
        <i class="fa-solid {profile_icon}" style="color:#f0c040; margin-right:5px;"></i>{profile_label}
    </div>
</div>
<div style="font-size:0.82rem; color:#44445a; margin-bottom:1rem; letter-spacing:0.3px;">
    <i class="fa-brands fa-linkedin" style="color:#0a66c2; margin-right:5px;"></i>Agente de Leads LinkedIn
</div>
""", unsafe_allow_html=True)

# ── Métricas ───────────────────────────────────────────────────────────────────
df = st.session_state.session_df

# Calcula scores se há leads
if not df.empty:
    df_scored = compute_scores(df)
    st.session_state.session_df = df_scored
    df = df_scored

total    = len(df)
pending  = len(df[df["status"] == "pending"])       if total else 0
approved = len(df[df["status"] == "approved"])      if total else 0
sent     = len(df[df["status"] == "sent"])          if total else 0
hot      = len(df[df["prioridade"] == "Hot"])       if total and "prioridade" in df.columns else 0

col1, col2, col3, col4, col5 = st.columns(5)
metric_data = [
    (col1, "fa-users",       total,    "Total de Leads",      "#f0c040"),
    (col2, "fa-fire",        hot,      "Hot Leads",           "#fb923c"),
    (col3, "fa-clock",       pending,  "Aguardando Revisão",  "#f0c040"),
    (col4, "fa-circle-check",approved, "Aprovados",           "#34d399"),
    (col5, "fa-paper-plane", sent,     "DMs Enviadas",        "#60a5fa"),
]
for col, icon, value, label, color in metric_data:
    with col:
        st.markdown(f"""
        <div class="metric-card">
            <div class="metric-icon"><i class="fa-solid {icon}" style="color:{color};"></i></div>
            <div class="metric-number" style="color:{color};">{value}</div>
            <div class="metric-label">{label}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<div style='margin:1.2rem 0;'></div>", unsafe_allow_html=True)

# ── Ações ──────────────────────────────────────────────────────────────────────
if btn_collect:
    st.session_state.running = True
    add_log(f"Iniciando coleta — perfil: {profile_data['name']}")

    with st.spinner("Coletando leads via Brave Search..."):
        try:
            import config as _cfg
            add_log(f"Keywords: {len(_cfg.SEARCH_KEYWORDS)} configuradas")
            add_log(f"Sheet: {_cfg.SHEET_NAME}")
            add_log(f"Brave API Key: {'OK' if _cfg.BRAVE_SEARCH_API_KEY else 'VAZIO'}")

            from scraper import search_by_keywords, search_by_post_engagement
            from leads_manager import add_leads, load_leads
            add_log("Buscando por palavras-chave...")
            keyword_leads = search_by_keywords()
            add_log(f"{len(keyword_leads)} perfis encontrados via keywords")

            add_log("Buscando engajamento em posts...")
            engagement_leads = search_by_post_engagement()
            add_log(f"{len(engagement_leads)} perfis via engajamento")

            all_leads = keyword_leads + engagement_leads
            added, dupes = add_leads(all_leads)
            add_log(f"{added} novos leads salvos ({dupes} duplicatas ignoradas)")

            from dataclasses import asdict
            if all_leads:
                st.session_state.session_df = pd.DataFrame([asdict(l) for l in all_leads])
            else:
                st.session_state.session_df = _EMPTY_DF.copy()

            add_log("Planilha atualizada!")
            st.success(f"Coleta concluída! {added} leads novos.")
        except Exception as e:
            import traceback
            add_log(f"ERRO: {e}")
            add_log(traceback.format_exc())
            st.error(str(e))

    st.session_state.running = False
    st.rerun()

if btn_send:
    st.session_state.running = True
    add_log(f"Iniciando envio de DMs — perfil: {profile_data['name']}")

    with st.spinner("Enviando DMs via Chrome..."):
        try:
            from sheets_manager import pull_approved_from_sheet
            from messenger import run_messenger

            add_log("Lendo aprovados do Google Sheets...")
            approved_leads = pull_approved_from_sheet()
            add_log(f"{len(approved_leads)} leads aprovados encontrados")

            run_messenger(dry_run=False)
            add_log("Envio concluído!")
            st.success("DMs enviadas com sucesso!")
        except Exception as e:
            add_log(f"ERRO: {e}")
            st.error(str(e))

    st.session_state.running = False
    st.rerun()

if btn_sync:
    with st.spinner("Sincronizando..."):
        try:
            from sheets_manager import pull_approved_from_sheet
            approved_leads = pull_approved_from_sheet()
            add_log(f"Sincronizado: {len(approved_leads)} aprovados")
            st.success(f"{len(approved_leads)} leads aprovados sincronizados do Sheets.")
        except Exception as e:
            add_log(f"ERRO: {e}")
            st.error(str(e))
    st.rerun()

if btn_load_sheets:
    with st.spinner("Carregando leads do Google Sheets..."):
        try:
            load_dataframe.clear()
            df_sheets = load_dataframe(config.SHEET_NAME)
            st.session_state.session_df = df_sheets
            add_log(f"Carregado {len(df_sheets)} leads do Sheets.")
            st.success(f"{len(df_sheets)} leads carregados do Google Sheets.")
        except Exception as e:
            add_log(f"ERRO ao carregar Sheets: {e}")
            st.error(str(e))
    st.rerun()

if btn_clear:
    st.session_state.session_df = _EMPTY_DF.copy()
    add_log("Tabela limpa.")
    st.rerun()

# ── Tabela de leads ────────────────────────────────────────────────────────────
st.markdown("""
<div class="section-header" style="font-size:1.1rem; margin-bottom:0.8rem;">
    <i class="fa-solid fa-table-list"></i> Leads Coletados
</div>
""", unsafe_allow_html=True)

df_table = st.session_state.session_df

# ── Filtros ────────────────────────────────────────────────────────────────────
col_search, col_status, col_loc, col_prio = st.columns([3, 1, 1, 1])

with col_search:
    search_text = st.text_input(
        "Buscar",
        placeholder="  Buscar por nome, cargo, empresa...",
        label_visibility="collapsed",
    )
with col_status:
    status_opts = ["Todos"] + sorted(df_table["status"].dropna().unique().tolist()) if not df_table.empty else ["Todos"]
    status_filter = st.selectbox("Status", status_opts, label_visibility="collapsed")

with col_loc:
    if not df_table.empty and "location" in df_table.columns:
        locs = df_table["location"].dropna().loc[lambda s: s.str.strip() != ""].unique().tolist()
    else:
        locs = []
    loc_opts = ["Todas"] + sorted(locs)
    loc_filter = st.selectbox("Localização", loc_opts, label_visibility="collapsed")

with col_prio:
    prio_opts = ["Todas", "Hot", "Warm", "Cold"]
    prio_filter = st.selectbox("Prioridade", prio_opts, label_visibility="collapsed")

# Aplica filtros
if not df_table.empty:
    if search_text:
        mask = df_table.apply(lambda row: search_text.lower() in " ".join(str(v) for v in row.values).lower(), axis=1)
        df_table = df_table[mask]
    if status_filter != "Todos":
        df_table = df_table[df_table["status"] == status_filter]
    if loc_filter != "Todas":
        df_table = df_table[df_table["location"] == loc_filter]
    if prio_filter != "Todas" and "prioridade" in df_table.columns:
        df_table = df_table[df_table["prioridade"] == prio_filter]

if df_table.empty:
    st.markdown("""
    <div style="text-align:center; padding:3rem 0; color:#44445a;">
        <i class="fa-solid fa-inbox" style="font-size:2.5rem; display:block; margin-bottom:0.8rem;"></i>
        Nenhum lead nesta sessão.<br>
        <span style="font-size:0.85rem;">Clique em <b>Coletar Leads</b> ou <b>Carregar do Sheets</b>.</span>
    </div>
    """, unsafe_allow_html=True)
else:
    df_display = df_table.copy()

    # Ordena por score decrescente
    if "score" in df_display.columns:
        df_display = df_display.sort_values("score", ascending=False)

    df_display["status"] = df_display["status"].apply(lambda s: f"{status_color(s)} {s}")

    # Emoji de prioridade na coluna
    prio_emoji = {"Hot": "🔥", "Warm": "🟡", "Cold": "❄️"}
    if "prioridade" in df_display.columns:
        df_display["prioridade"] = df_display.apply(
            lambda r: f"{prio_emoji.get(r['prioridade'], '')} {r['prioridade']}  {r.get('score', '')}pts",
            axis=1,
        )

    # Legenda de prioridade
    st.markdown("""
    <div class="score-legend">
        <span><span class="score-pill score-hot">🔥 Hot</span> &nbsp;65–100 pts — abordar primeiro</span>
        <span><span class="score-pill score-warm">🟡 Warm</span> &nbsp;35–64 pts — fila normal</span>
        <span><span class="score-pill score-cold">❄️ Cold</span> &nbsp;0–34 pts — baixa prioridade</span>
    </div>
    """, unsafe_allow_html=True)

    cols = ["prioridade", "name", "job_title", "company", "location", "status", "linkedin_url"]
    cols = [c for c in cols if c in df_display.columns]

    st.dataframe(
        df_display[cols],
        use_container_width=True,
        height=420,
        column_config={
            "prioridade":   st.column_config.TextColumn("Prioridade"),
            "name":         st.column_config.TextColumn("Nome"),
            "job_title":    st.column_config.TextColumn("Cargo"),
            "company":      st.column_config.TextColumn("Empresa"),
            "location":     st.column_config.TextColumn("Localização"),
            "status":       st.column_config.TextColumn("Status"),
            "linkedin_url": st.column_config.LinkColumn("LinkedIn"),
        },
    )
    st.markdown(f"""
    <div style="font-size:0.75rem; color:#44445a; margin-top:6px; display:flex; align-items:center; gap:6px;">
        <i class="fa-solid fa-circle-info"></i>
        {len(df_table)} leads exibidos &nbsp;·&nbsp; Leads salvos permanentemente no Google Sheets
    </div>
    """, unsafe_allow_html=True)

# ── Log de atividade ───────────────────────────────────────────────────────────
st.markdown("""
<div class="section-header" style="font-size:1.1rem; margin: 1.2rem 0 0.8rem;">
    <i class="fa-solid fa-terminal"></i> Log de Atividade
</div>
""", unsafe_allow_html=True)

log_text = "\n".join(st.session_state.logs[-50:]) if st.session_state.logs else "Nenhuma atividade ainda."
st.markdown(f'<div class="log-box"><pre>{log_text}</pre></div>', unsafe_allow_html=True)
