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
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=Space+Grotesk:wght@500;600;700&family=JetBrains+Mono:wght@400&display=swap" rel="stylesheet">
<style>
    /* ── Animations ── */
    @keyframes shimmer {
        0% { background-position: -200% 0; }
        100% { background-position: 200% 0; }
    }
    @keyframes pulse-glow {
        0%, 100% { opacity: 0.4; }
        50% { opacity: 0.8; }
    }
    @keyframes fade-in-up {
        from { opacity: 0; transform: translateY(12px); }
        to { opacity: 1; transform: translateY(0); }
    }
    @keyframes border-breathe {
        0%, 100% { border-color: rgba(212,175,55,0.04); }
        50% { border-color: rgba(212,175,55,0.10); }
    }
    @keyframes glow-pulse {
        0%, 100% { box-shadow: 0 0 20px rgba(212,175,55,0.0); }
        50% { box-shadow: 0 0 40px rgba(212,175,55,0.04); }
    }

    /* ── Global resets ── */
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif !important;
        -webkit-font-smoothing: antialiased;
        -moz-osx-font-smoothing: grayscale;
        text-rendering: optimizeLegibility;
    }
    ::selection {
        background: rgba(212,175,55,0.3);
        color: #fff;
    }

    /* ── Background — deep mesh gradient ── */
    [data-testid="stAppViewContainer"] {
        background: #0a0a0f;
        background-image:
            radial-gradient(ellipse at 15% 10%, rgba(212,175,55,0.04) 0%, transparent 50%),
            radial-gradient(ellipse at 85% 30%, rgba(99,102,241,0.04) 0%, transparent 50%),
            radial-gradient(ellipse at 50% 80%, rgba(14,165,233,0.03) 0%, transparent 50%),
            radial-gradient(ellipse at 70% 60%, rgba(212,175,55,0.02) 0%, transparent 40%);
    }

    /* Noise/grain overlay — premium texture */
    [data-testid="stAppViewContainer"]::after {
        content: '';
        position: fixed;
        top: 0; left: 0;
        width: 100%; height: 100%;
        background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E");
        opacity: 0.03;
        pointer-events: none;
        z-index: 1;
        mix-blend-mode: overlay;
    }

    /* Top accent line — shimmer */
    [data-testid="stAppViewContainer"]::before {
        content: '';
        position: fixed;
        top: 0; left: 0; right: 0;
        height: 2px;
        background: linear-gradient(90deg, transparent, #d4af37, #f59e0b, #d4af37, transparent);
        background-size: 200% 100%;
        animation: shimmer 4s ease-in-out infinite;
        z-index: 9999;
    }

    /* ── Sidebar — glass panel ── */
    [data-testid="stSidebar"] {
        background: rgba(8,9,18,0.90) !important;
        backdrop-filter: blur(24px) saturate(120%) !important;
        -webkit-backdrop-filter: blur(24px) saturate(120%) !important;
        border-right: 1px solid rgba(255,255,255,0.04) !important;
    }
    [data-testid="stSidebar"]::before {
        content: '';
        position: absolute;
        top: 0; right: 0;
        width: 1px; height: 100%;
        background: linear-gradient(180deg, rgba(212,175,55,0.4) 0%, rgba(212,175,55,0.08) 30%, transparent 60%);
    }

    /* ── Radio buttons ── */
    [data-testid="stRadio"] [role="radio"] {
        border-color: rgba(255,255,255,0.06) !important;
        transition: all 0.2s ease !important;
    }
    [data-testid="stRadio"] [role="radio"][aria-checked="true"] {
        border-color: #d4af37 !important;
        background: linear-gradient(135deg, #d4af37, #b8960c) !important;
        box-shadow: 0 0 16px rgba(212,175,55,0.3) !important;
    }
    [data-testid="stRadio"] label {
        color: rgba(255,255,255,0.30) !important;
        font-size: 0.85rem !important;
        font-weight: 500 !important;
        transition: color 0.2s ease !important;
    }
    [data-testid="stRadio"] label:has([aria-checked="true"]) {
        color: #d4af37 !important;
    }

    h1, h2, h3, h4 { color: #d4af37 !important; }

    /* ── Buttons — gold glass ── */
    .stButton > button {
        background: linear-gradient(135deg, rgba(212,175,55,0.9) 0%, rgba(184,150,12,0.85) 100%) !important;
        color: #0a0a0f !important;
        font-weight: 600 !important;
        border-radius: 10px !important;
        border: 1px solid rgba(212,175,55,0.2) !important;
        padding: 0.55rem 1.3rem !important;
        letter-spacing: 0.3px !important;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: 0 2px 12px rgba(212,175,55,0.12), inset 0 1px 0 rgba(255,255,255,0.1) !important;
        font-size: 0.82rem !important;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, rgba(245,200,60,0.95) 0%, rgba(212,175,55,0.95) 100%) !important;
        box-shadow: 0 4px 24px rgba(212,175,55,0.3), inset 0 1px 0 rgba(255,255,255,0.15) !important;
        transform: translateY(-1px) !important;
    }
    .stButton > button:active {
        transform: scale(0.97) !important;
        transition: transform 0.1s ease !important;
        box-shadow: 0 1px 6px rgba(212,175,55,0.15) !important;
    }

    /* ── Metric cards — glass with inner light ── */
    .metric-card {
        background: rgba(255,255,255,0.02);
        backdrop-filter: blur(16px) saturate(120%);
        -webkit-backdrop-filter: blur(16px) saturate(120%);
        border: 1px solid rgba(255,255,255,0.04);
        border-radius: 16px;
        padding: 1.8rem 1rem 1.5rem;
        text-align: center;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        position: relative;
        overflow: hidden;
        animation: fade-in-up 0.5s ease-out both, border-breathe 4s ease-in-out infinite;
        box-shadow:
            0 0 0 1px rgba(255,255,255,0.02),
            inset 0 1px 0 rgba(255,255,255,0.03),
            0 4px 24px rgba(0,0,0,0.4);
    }
    .metric-card:nth-child(1) { animation-delay: 0.05s; }
    .metric-card:nth-child(2) { animation-delay: 0.10s; }
    .metric-card:nth-child(3) { animation-delay: 0.15s; }
    .metric-card:nth-child(4) { animation-delay: 0.20s; }
    .metric-card:nth-child(5) { animation-delay: 0.25s; }
    .metric-card:nth-child(6) { animation-delay: 0.30s; }

    .metric-card::before {
        content: '';
        position: absolute;
        top: 0; left: 15%; right: 15%;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(212,175,55,0.2), transparent);
    }
    .metric-card::after {
        content: '';
        position: absolute;
        top: -50%; left: -50%;
        width: 200%; height: 200%;
        background: radial-gradient(circle at center, rgba(212,175,55,0.015) 0%, transparent 70%);
        opacity: 0;
        transition: opacity 0.4s ease;
    }
    .metric-card:hover {
        border-color: rgba(212,175,55,0.12);
        transform: translateY(-2px);
        box-shadow:
            0 8px 32px rgba(0,0,0,0.5),
            0 0 0 1px rgba(212,175,55,0.06),
            0 0 48px rgba(212,175,55,0.03);
    }
    .metric-card:hover::after { opacity: 1; }

    .metric-card-hot { border-color: rgba(251,146,60,0.10) !important; }
    .metric-card-hot::before {
        background: linear-gradient(90deg, transparent, rgba(251,146,60,0.3), transparent) !important;
    }
    .metric-card-hot:hover {
        border-color: rgba(251,146,60,0.20) !important;
        box-shadow: 0 8px 32px rgba(0,0,0,0.5), 0 0 40px rgba(251,146,60,0.05) !important;
    }

    .metric-icon {
        font-size: 0.9rem;
        opacity: 0.4;
        margin-bottom: 0.9rem;
        display: block;
    }
    .metric-number {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 2.8rem;
        font-weight: 700;
        letter-spacing: -0.03em;
        line-height: 1;
        display: block;
        text-shadow: 0 0 60px currentColor, 0 0 120px rgba(212,175,55,0.08);
    }
    .metric-label {
        font-family: 'Inter', sans-serif;
        font-size: 0.6rem;
        color: rgba(255,255,255,0.20);
        margin-top: 12px;
        text-transform: uppercase;
        letter-spacing: 0.15em;
        font-weight: 600;
        display: block;
    }

    /* ── Log box — terminal ── */
    .log-box {
        background: rgba(8,9,18,0.8);
        backdrop-filter: blur(12px) saturate(110%);
        border: 1px solid rgba(255,255,255,0.04);
        border-radius: 12px;
        padding: 1.2rem 1.4rem;
        font-family: 'JetBrains Mono', 'Fira Code', monospace;
        font-size: 0.72rem;
        color: rgba(120,130,180,0.6);
        height: 180px;
        overflow-y: auto;
        line-height: 1.8;
        position: relative;
    }
    .log-box::before {
        content: '>';
        position: absolute;
        top: 1.2rem; left: 1.4rem;
        color: rgba(212,175,55,0.25);
        font-size: 0.7rem;
        animation: pulse-glow 2s ease-in-out infinite;
    }
    .log-box pre { margin: 0; white-space: pre-wrap; padding-left: 0; }
    .log-box::-webkit-scrollbar { width: 4px; }
    .log-box::-webkit-scrollbar-track { background: transparent; }
    .log-box::-webkit-scrollbar-thumb {
        background: rgba(255,255,255,0.06);
        border-radius: 4px;
    }
    .log-box::-webkit-scrollbar-thumb:hover {
        background: rgba(255,255,255,0.12);
    }

    /* ── Sidebar components ── */
    .sidebar-logo {
        display: flex;
        align-items: center;
        gap: 14px;
        padding: 0.4rem 0 0.8rem;
    }
    .sidebar-logo-icon {
        width: 42px; height: 42px;
        background: linear-gradient(135deg, #d4af37, #9a7b1e);
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.1rem;
        color: #0a0a0f;
        box-shadow: 0 4px 20px rgba(212,175,55,0.25), inset 0 1px 0 rgba(255,255,255,0.15);
    }
    .sidebar-logo-text {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 1.15rem;
        font-weight: 700;
        color: #d4af37;
        letter-spacing: -0.03em;
    }
    .sidebar-logo-sub {
        font-size: 0.6rem;
        color: rgba(255,255,255,0.15);
        margin-top: 3px;
        letter-spacing: 0.1em;
        text-transform: uppercase;
    }

    .section-header {
        display: flex;
        align-items: center;
        gap: 8px;
        color: rgba(255,255,255,0.25);
        font-size: 0.6rem;
        font-weight: 700;
        margin: 1.2rem 0 0.6rem;
        text-transform: uppercase;
        letter-spacing: 0.15em;
    }
    .section-header i { font-size: 0.55rem; color: rgba(212,175,55,0.4); }

    /* ── Status badges ── */
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        padding: 3px 10px;
        border-radius: 100px;
        font-size: 0.68rem;
        font-weight: 500;
        backdrop-filter: blur(8px);
    }
    .badge-pending  { background: rgba(212,175,55,0.06); color: #d4af37; border: 1px solid rgba(212,175,55,0.10); }
    .badge-approved { background: rgba(52,211,153,0.06); color: #34d399; border: 1px solid rgba(52,211,153,0.10); }
    .badge-sent     { background: rgba(96,165,250,0.06); color: #60a5fa; border: 1px solid rgba(96,165,250,0.10); }
    .badge-failed   { background: rgba(248,113,113,0.06); color: #f87171; border: 1px solid rgba(248,113,113,0.10); }
    .badge-skipped  { background: rgba(107,114,128,0.06); color: #6b7280; border: 1px solid rgba(107,114,128,0.08); }

    /* ── Score badges ── */
    .score-pill {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        padding: 3px 10px;
        border-radius: 100px;
        font-size: 0.68rem;
        font-weight: 600;
        letter-spacing: 0.05em;
        backdrop-filter: blur(8px);
    }
    .score-hot {
        background: rgba(251,146,60,0.08);
        color: #fb923c;
        border: 1px solid rgba(251,146,60,0.15);
        text-shadow: 0 0 12px rgba(251,146,60,0.3);
    }
    .score-warm {
        background: rgba(250,204,21,0.06);
        color: #facc15;
        border: 1px solid rgba(250,204,21,0.12);
    }
    .score-cold {
        background: rgba(107,114,128,0.05);
        color: rgba(107,114,128,0.6);
        border: 1px solid rgba(107,114,128,0.08);
    }

    .score-legend {
        display: flex;
        gap: 16px;
        align-items: center;
        font-size: 0.68rem;
        color: rgba(255,255,255,0.18);
        margin-bottom: 0.8rem;
    }

    /* ── Table — Linear/Vercel style ── */
    [data-testid="stDataFrame"] {
        border: 1px solid rgba(255,255,255,0.04) !important;
        border-radius: 12px !important;
        overflow: hidden !important;
    }

    hr {
        border: none !important;
        height: 1px !important;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.04), transparent) !important;
    }

    /* ── Inputs — glass ── */
    .stTextInput > div > div > input {
        background: rgba(255,255,255,0.02) !important;
        backdrop-filter: blur(12px) !important;
        border: 1px solid rgba(255,255,255,0.06) !important;
        border-radius: 10px !important;
        color: rgba(255,255,255,0.85) !important;
        transition: all 0.2s ease !important;
    }
    .stTextInput > div > div > input:focus {
        border-color: rgba(212,175,55,0.25) !important;
        box-shadow: 0 0 0 3px rgba(212,175,55,0.06), 0 0 20px rgba(212,175,55,0.04) !important;
        outline: none !important;
    }
    .stTextInput > div > div > input::placeholder {
        color: rgba(255,255,255,0.15) !important;
    }
    [data-baseweb="select"] > div {
        background: rgba(255,255,255,0.02) !important;
        backdrop-filter: blur(12px) !important;
        border: 1px solid rgba(255,255,255,0.06) !important;
        border-radius: 10px !important;
        color: rgba(255,255,255,0.85) !important;
    }
    .stRadio > div { gap: 6px; }

    /* ── Custom scrollbar ── */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb {
        background: rgba(255,255,255,0.06);
        border-radius: 3px;
    }
    ::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.12); }

    /* ── Section titles ── */
    .section-title {
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .section-title-bar {
        width: 3px; height: 18px;
        border-radius: 2px;
    }
    .section-title-text {
        font-family: 'Space Grotesk', sans-serif;
        font-size: 0.9rem;
        font-weight: 600;
        letter-spacing: -0.02em;
    }

    /* ── Info panel in sidebar ── */
    .info-panel {
        margin-top: 1.5rem;
        padding: 0.9rem 1rem;
        background: rgba(255,255,255,0.02);
        border: 1px solid rgba(255,255,255,0.04);
        border-radius: 10px;
        font-size: 0.68rem;
        color: rgba(255,255,255,0.25);
        line-height: 1.8;
    }
    .info-panel b { color: rgba(255,255,255,0.40); }
    .info-panel i { color: rgba(212,175,55,0.3); margin-right: 4px; }

    /* ── Divider gradient ── */
    .divider {
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.06), transparent);
        margin: 1.5rem 0;
    }

    /* ── Empty state ── */
    .empty-state {
        text-align: center;
        padding: 4rem 2rem;
        color: rgba(255,255,255,0.15);
    }
    .empty-state i {
        font-size: 2.5rem;
        display: block;
        margin-bottom: 1rem;
        opacity: 0.3;
    }
    .empty-state b { color: rgba(212,175,55,0.5); }

    /* ── Lead count footer ── */
    .lead-count {
        font-size: 0.72rem;
        color: rgba(255,255,255,0.15);
        margin-top: 8px;
        display: flex;
        align-items: center;
        gap: 6px;
    }
</style>
""", unsafe_allow_html=True)


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="sidebar-logo">
        <div class="sidebar-logo-icon"><i class="fa-solid fa-bolt"></i></div>
        <div>
            <div class="sidebar-logo-text">Vault Capital</div>
            <div class="sidebar-logo-sub">Lead Generation</div>
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
    <div class="info-panel">
        <i class="fa-solid fa-circle-info"></i>
        <b>Score IA</b>: Claude analisa bio e dá nota<br>
        <i class="fa-solid fa-circle-info"></i>
        <b>Enriquecer</b>: busca email via Hunter.io<br>
        <i class="fa-solid fa-circle-info"></i>
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
<div style="display:flex; align-items:center; gap:16px; margin-bottom:0.2rem;">
    <div style="font-family:'Space Grotesk',sans-serif; font-size:1.8rem; font-weight:700;
                color:rgba(255,255,255,0.90); letter-spacing:-0.03em; line-height:1;">
        Vault Capital
    </div>
    <div style="background:rgba(212,175,55,0.06); border:1px solid rgba(212,175,55,0.10);
                border-radius:100px; padding:4px 14px; font-size:0.68rem;
                color:#d4af37; font-weight:600; letter-spacing:0.05em;">
        <i class="fa-solid {profile_icon}" style="margin-right:5px; opacity:0.7;"></i>{profile_label}
    </div>
</div>
<div style="font-size:0.72rem; color:rgba(255,255,255,0.20); margin-bottom:1.8rem;
            letter-spacing:0.05em; display:flex; align-items:center; gap:8px;">
    <i class="fa-brands fa-linkedin" style="color:rgba(99,102,241,0.5); font-size:0.8rem;"></i>
    <span>Lead Generation Agent</span>
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
<div class="section-title" style="margin-bottom:1rem;">
    <div class="section-title-bar" style="background:linear-gradient(180deg,#d4af37,rgba(212,175,55,0.2));"></div>
    <span class="section-title-text" style="color:rgba(255,255,255,0.70);">Leads Coletados</span>
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
    <div class="empty-state">
        <i class="fa-solid fa-inbox"></i>
        Nenhum lead nesta sessão.<br>
        <span style="font-size:0.8rem;">Clique em <b>Coletar Leads</b> ou <b>Carregar do Sheets</b>.</span>
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
    <div class="lead-count">
        <i class="fa-solid fa-circle" style="font-size:4px; color:rgba(212,175,55,0.3);"></i>
        {len(df_table)} leads exibidos &nbsp;·&nbsp; Google Sheets sync
    </div>
    """, unsafe_allow_html=True)

# ── Log de atividade ───────────────────────────────────────────────────────────
st.markdown("""
<div class="divider"></div>
<div class="section-title" style="margin-bottom:0.7rem;">
    <div class="section-title-bar" style="background:linear-gradient(180deg,rgba(99,102,241,0.5),rgba(99,102,241,0.1));"></div>
    <span class="section-title-text" style="color:rgba(255,255,255,0.35);">
        <i class="fa-solid fa-terminal" style="margin-right:8px; font-size:0.75rem; opacity:0.5;"></i>Log
    </span>
</div>
""", unsafe_allow_html=True)

log_text = "\n".join(st.session_state.logs[-50:]) if st.session_state.logs else "Nenhuma atividade ainda."
st.markdown(f'<div class="log-box"><pre>{log_text}</pre></div>', unsafe_allow_html=True)
