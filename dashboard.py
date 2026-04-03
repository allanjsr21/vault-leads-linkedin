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
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@700&display=swap" rel="stylesheet">
<style>

    /* ── Reset & base ── */
    html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }

    /* Top gold accent line */
    [data-testid="stAppViewContainer"]::before {
        content: '';
        position: fixed;
        top: 0; left: 0; right: 0;
        height: 2px;
        background: linear-gradient(90deg, transparent 0%, #f0c040 30%, #fb923c 70%, transparent 100%);
        z-index: 9999;
    }

    [data-testid="stAppViewContainer"] {
        background: #07070e;
    }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background: #0b0b14 !important;
        border-right: 1px solid rgba(240,192,64,0.08) !important;
    }
    [data-testid="stSidebar"]::before {
        content: '';
        position: absolute;
        top: 0; left: 0;
        width: 2px; height: 100%;
        background: linear-gradient(180deg, #f0c040 0%, transparent 60%);
    }

    /* ── Fix radio buttons to brand gold ── */
    [data-testid="stRadio"] [role="radio"] {
        border-color: #333355 !important;
    }
    [data-testid="stRadio"] [role="radio"][aria-checked="true"] {
        border-color: #f0c040 !important;
        background: #f0c040 !important;
    }
    [data-testid="stRadio"] label { color: #9090b0 !important; font-size: 0.88rem !important; }
    [data-testid="stRadio"] label:has([aria-checked="true"]) { color: #f0c040 !important; }

    h1, h2, h3, h4 { color: #f0c040 !important; }

    /* ── Buttons ── */
    .stButton > button {
        background: linear-gradient(135deg, #f0c040 0%, #c89a00 100%) !important;
        color: #000 !important;
        font-weight: 600 !important;
        border-radius: 10px !important;
        border: none !important;
        padding: 0.5rem 1.2rem !important;
        letter-spacing: 0.2px !important;
        transition: all 0.15s ease !important;
        box-shadow: 0 1px 8px rgba(240,192,64,0.12) !important;
        font-size: 0.85rem !important;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #ffd84d 0%, #f0c040 100%) !important;
        box-shadow: 0 3px 16px rgba(240,192,64,0.28) !important;
        transform: translateY(-1px) !important;
    }
    .stButton > button:active { transform: translateY(0) !important; }

    /* ── Metric cards ── */
    .metric-card {
        background: #0f0f1c;
        border: 1px solid #1e1e32;
        border-radius: 18px;
        padding: 1.5rem 1rem 1.3rem;
        text-align: center;
        transition: all 0.2s ease;
        position: relative;
        overflow: hidden;
    }
    .metric-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(240,192,64,0.3), transparent);
    }
    .metric-card:hover {
        border-color: rgba(240,192,64,0.25);
        transform: translateY(-2px);
        box-shadow: 0 8px 30px rgba(0,0,0,0.3);
    }
    .metric-card-hot {
        border-color: rgba(251,146,60,0.2) !important;
    }
    .metric-card-hot::before {
        background: linear-gradient(90deg, transparent, rgba(251,146,60,0.4), transparent) !important;
    }
    .metric-card-hot:hover {
        border-color: rgba(251,146,60,0.4) !important;
        box-shadow: 0 8px 30px rgba(251,146,60,0.08) !important;
    }
    .metric-icon {
        font-size: 1.1rem;
        opacity: 0.6;
        margin-bottom: 0.7rem;
        display: block;
    }
    .metric-number {
        font-family: 'Space Grotesk', 'Inter', sans-serif;
        font-size: 2.6rem;
        font-weight: 700;
        letter-spacing: -2px;
        line-height: 1;
        display: block;
    }
    .metric-label {
        font-size: 0.68rem;
        color: #3d3d5c;
        margin-top: 8px;
        text-transform: uppercase;
        letter-spacing: 1.2px;
        font-weight: 600;
        display: block;
    }

    /* ── Log box ── */
    .log-box {
        background: #0b0b14;
        border: 1px solid #1a1a28;
        border-radius: 12px;
        padding: 1rem 1.2rem;
        font-family: 'Fira Code', 'Courier New', monospace;
        font-size: 0.74rem;
        color: #4a5080;
        height: 200px;
        overflow-y: auto;
        line-height: 1.7;
    }
    .log-box pre { margin: 0; white-space: pre-wrap; }

    /* ── Sidebar components ── */
    .sidebar-logo {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 0.2rem 0 0.4rem;
    }
    .sidebar-logo-icon {
        width: 36px; height: 36px;
        background: linear-gradient(135deg, #f0c040, #c89a00);
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1rem;
        color: #000;
        box-shadow: 0 2px 12px rgba(240,192,64,0.25);
    }
    .sidebar-logo-text {
        font-size: 1rem;
        font-weight: 700;
        color: #f0c040;
        letter-spacing: 0.3px;
    }
    .sidebar-logo-sub {
        font-size: 0.67rem;
        color: #33334a;
        margin-top: 1px;
    }

    .section-header {
        display: flex;
        align-items: center;
        gap: 7px;
        color: #f0c040;
        font-size: 0.72rem;
        font-weight: 700;
        margin: 1rem 0 0.5rem;
        text-transform: uppercase;
        letter-spacing: 1.2px;
        opacity: 0.7;
    }
    .section-header i { font-size: 0.7rem; }

    /* ── Status badges ── */
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
    btn_ai_score    = st.button("Score via IA",        icon=":material/psychology:",    use_container_width=True)
    btn_enrich      = st.button("Enriquecer Emails",   icon=":material/alternate_email:", use_container_width=True)
    btn_send        = st.button("Enviar DMs",          icon=":material/send:",          use_container_width=True)

    st.markdown("---")

    btn_sync        = st.button("Sincronizar Sheets",  icon=":material/sync:",          use_container_width=True)
    btn_load_sheets = st.button("Carregar do Sheets",  icon=":material/cloud_download:", use_container_width=True)
    btn_clear       = st.button("Limpar tabela",       icon=":material/delete:",        use_container_width=True)

    st.markdown("""
    <div style="margin-top:1.5rem; padding:0.8rem; background:rgba(240,192,64,0.04);
                border:1px solid rgba(240,192,64,0.08); border-radius:10px;
                font-size:0.7rem; color:#33334a; line-height:1.7;">
        <i class="fa-solid fa-circle-info" style="color:#f0c040; opacity:0.4; margin-right:5px;"></i>
        <b>Score IA</b>: Claude analisa bio e dá nota inteligente<br>
        <b>Enriquecer</b>: busca email via Hunter.io<br>
        <b>Coletar</b>: keywords + posts + eventos
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
            bio          = row.get("bio", ""),
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
<div style="display:flex; align-items:center; gap:14px; margin-bottom:0.15rem;">
    <div style="font-family:'Space Grotesk','Inter',sans-serif; font-size:1.9rem; font-weight:700;
                color:#f0c040; letter-spacing:-1px; line-height:1;">
        Vault Capital
    </div>
    <div style="background:rgba(240,192,64,0.07); border:1px solid rgba(240,192,64,0.15);
                border-radius:20px; padding:4px 13px; font-size:0.72rem;
                color:#c8a830; font-weight:600; letter-spacing:0.3px;">
        <i class="fa-solid {profile_icon}" style="margin-right:5px; opacity:0.8;"></i>{profile_label}
    </div>
</div>
<div style="font-size:0.78rem; color:#2e2e45; margin-bottom:1.4rem; letter-spacing:0.3px; display:flex; align-items:center; gap:6px;">
    <i class="fa-brands fa-linkedin" style="color:#0a66c2;"></i>
    <span>Agente de Leads LinkedIn</span>
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
emails   = len(df[df["email"].astype(str).str.strip() != ""])  if total and "email" in df.columns else 0

col1, col2, col3, col4, col5, col6 = st.columns(6)
metric_data = [
    (col1, "fa-users",        total,    "Total de Leads",     "#f0c040", ""),
    (col2, "fa-fire",         hot,      "Hot Leads",          "#fb923c", "metric-card-hot"),
    (col3, "fa-envelope",     emails,   "Com Email",          "#a78bfa", ""),
    (col4, "fa-hourglass-half",pending, "Aguardando",         "#e2e8f0", ""),
    (col5, "fa-circle-check", approved, "Aprovados",          "#34d399", ""),
    (col6, "fa-paper-plane",  sent,     "DMs Enviadas",       "#60a5fa", ""),
]
for col, icon, value, label, color, extra_class in metric_data:
    with col:
        st.markdown(f"""
        <div class="metric-card {extra_class}">
            <span class="metric-icon"><i class="fa-solid {icon}" style="color:{color};"></i></span>
            <span class="metric-number" style="color:{color};">{value}</span>
            <span class="metric-label">{label}</span>
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

            from scraper import search_by_keywords, search_by_post_engagement, search_by_events
            from leads_manager import add_leads, load_leads

            # Fontes ativas
            sources_info = []
            if _cfg.BRAVE_SEARCH_API_KEY: sources_info.append("Brave Search")
            if getattr(_cfg, "GOOGLE_CSE_API_KEY", "") and getattr(_cfg, "GOOGLE_CSE_ID", ""):
                sources_info.append("Google Custom Search")
            add_log(f"Fontes ativas: {', '.join(sources_info) or 'Nenhuma!'}")

            add_log("Buscando por palavras-chave...")
            keyword_leads = search_by_keywords()
            brave_count  = sum(1 for l in keyword_leads if l.source == "brave")
            google_count = sum(1 for l in keyword_leads if l.source == "google")
            add_log(f"{len(keyword_leads)} perfis via keywords (Brave: {brave_count}, Google: {google_count})")

            add_log("Buscando autores de conteúdo crypto...")
            engagement_leads = search_by_post_engagement()
            add_log(f"{len(engagement_leads)} autores de artigos/posts encontrados")

            add_log("Buscando participantes de eventos crypto...")
            event_leads = search_by_events()
            add_log(f"{len(event_leads)} leads de eventos encontrados")

            all_leads = keyword_leads + engagement_leads + event_leads
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

if btn_ai_score:
    df_current = st.session_state.session_df
    if df_current.empty:
        st.warning("Nenhum lead carregado. Colete ou carregue leads primeiro.")
    else:
        import config as _cfg
        if not getattr(_cfg, "ANTHROPIC_API_KEY", ""):
            st.warning("ANTHROPIC_API_KEY não configurada. Adicione no Streamlit secrets.")
        else:
            with st.spinner("Analisando leads via Claude IA..."):
                try:
                    from scorer import ai_score_lead, score_label
                    from models import Lead as _Lead

                    add_log(f"Iniciando scoring via IA para {len(df_current)} leads...")
                    scored = 0
                    for idx, row in df_current.iterrows():
                        lead = _Lead(
                            linkedin_url=row.get("linkedin_url", ""),
                            name=row.get("name", ""),
                            job_title=row.get("job_title", ""),
                            company=row.get("company", ""),
                            location=row.get("location", ""),
                            bio=row.get("bio", ""),
                            source=row.get("source", ""),
                        )
                        result = ai_score_lead(lead)
                        if result:
                            df_current.at[idx, "score"] = result["score"]
                            df_current.at[idx, "prioridade"] = result["label"]
                            df_current.at[idx, "ai_score"] = result.get("reason", "")
                            scored += 1

                    st.session_state.session_df = df_current
                    add_log(f"IA analisou {scored}/{len(df_current)} leads com sucesso")
                    st.success(f"Score via IA concluído! {scored} leads analisados.")
                except Exception as e:
                    import traceback
                    add_log(f"ERRO IA: {e}")
                    add_log(traceback.format_exc())
                    st.error(str(e))
            st.rerun()

if btn_enrich:
    df_current = st.session_state.session_df
    if df_current.empty:
        st.warning("Nenhum lead carregado. Colete ou carregue leads primeiro.")
    else:
        import config as _cfg
        if not getattr(_cfg, "HUNTER_API_KEY", ""):
            st.warning("HUNTER_API_KEY não configurada. Adicione no Streamlit secrets.")
        else:
            with st.spinner("Buscando emails via Hunter.io..."):
                try:
                    from enricher import enrich_lead
                    from models import Lead as _Lead

                    add_log(f"Enriquecendo {len(df_current)} leads...")
                    found = 0
                    for idx, row in df_current.iterrows():
                        if row.get("email"):
                            continue  # já tem email
                        lead = _Lead(
                            linkedin_url=row.get("linkedin_url", ""),
                            name=row.get("name", ""),
                            company=row.get("company", ""),
                        )
                        result = enrich_lead(lead)
                        if result.get("email"):
                            df_current.at[idx, "email"] = result["email"]
                            found += 1

                    st.session_state.session_df = df_current
                    add_log(f"Emails encontrados: {found}/{len(df_current)}")
                    st.success(f"Enriquecimento concluído! {found} emails encontrados.")
                except Exception as e:
                    import traceback
                    add_log(f"ERRO Enrichment: {e}")
                    add_log(traceback.format_exc())
                    st.error(str(e))
            st.rerun()

# ── Tabela de leads ────────────────────────────────────────────────────────────
st.markdown("""
<div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:0.9rem;">
    <div style="display:flex; align-items:center; gap:8px;">
        <div style="width:3px; height:18px; background:linear-gradient(180deg,#f0c040,#c89a00);
                    border-radius:2px;"></div>
        <span style="font-size:0.95rem; font-weight:700; color:#e8d060; letter-spacing:0.2px;">
            Leads Coletados
        </span>
    </div>
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

    cols = ["prioridade", "name", "job_title", "company", "location", "email", "ai_score", "status", "linkedin_url"]
    cols = [c for c in cols if c in df_display.columns]
    # Remove colunas vazias
    cols = [c for c in cols if not df_display[c].astype(str).str.strip().eq("").all()]

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
            "email":        st.column_config.TextColumn("Email"),
            "ai_score":     st.column_config.TextColumn("IA Análise"),
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
<div style="display:flex; align-items:center; gap:8px; margin: 1.4rem 0 0.7rem;">
    <div style="width:3px; height:18px; background:linear-gradient(180deg,#4a5080,#2a2a40);
                border-radius:2px;"></div>
    <span style="font-size:0.95rem; font-weight:700; color:#5a6080; letter-spacing:0.2px;">
        <i class="fa-solid fa-terminal" style="margin-right:6px; font-size:0.8rem;"></i>Log de Atividade
    </span>
</div>
""", unsafe_allow_html=True)

log_text = "\n".join(st.session_state.logs[-50:]) if st.session_state.logs else "Nenhuma atividade ainda."
st.markdown(f'<div class="log-box"><pre>{log_text}</pre></div>', unsafe_allow_html=True)
