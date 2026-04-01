"""
Dashboard da Vault Capital — Agente de Leads LinkedIn
Rode com: streamlit run dashboard.py
"""

import sys
import os
import time
import threading
import queue
import pandas as pd
import streamlit as st

# Força UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

st.set_page_config(
    page_title="Vault Capital — Leads LinkedIn",
    page_icon="⚡",
    layout="wide",
)

# ── Estilo ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background-color: #0e0e0e; }
    [data-testid="stSidebar"] { background-color: #161616; }
    h1, h2, h3, h4 { color: #f0c040 !important; }
    .stButton > button {
        background-color: #f0c040;
        color: #000;
        font-weight: bold;
        border-radius: 8px;
        border: none;
        padding: 0.5rem 1.5rem;
    }
    .stButton > button:hover { background-color: #d4a800; color: #000; }
    .metric-card {
        background: #1a1a1a;
        border: 1px solid #333;
        border-radius: 10px;
        padding: 1rem 1.5rem;
        text-align: center;
    }
    .metric-number { font-size: 2rem; font-weight: bold; color: #f0c040; }
    .metric-label { font-size: 0.85rem; color: #888; margin-top: 4px; }
    .log-box {
        background: #111;
        border: 1px solid #333;
        border-radius: 8px;
        padding: 1rem;
        font-family: monospace;
        font-size: 0.78rem;
        color: #aaa;
        height: 220px;
        overflow-y: auto;
    }
    [data-testid="stDataFrame"] { border: 1px solid #333; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://i.imgur.com/placeholder.png", width=60) if False else None
    st.markdown("## ⚡ Vault Capital")
    st.markdown("**Agente de Leads LinkedIn**")
    st.markdown("---")

    st.markdown("### Publico-Alvo")
    profile_choice = st.radio(
        "Selecione o perfil:",
        options=["1", "2"],
        format_func=lambda x: "🔐 Autocustodia" if x == "1" else "💼 Consultoria",
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown("### Acoes")
    btn_collect = st.button("🔍 Coletar Leads", use_container_width=True)
    btn_send    = st.button("📨 Enviar DMs", use_container_width=True)
    btn_sync    = st.button("🔄 Sincronizar Sheets", use_container_width=True)
    btn_refresh = st.button("↻ Atualizar tabela", use_container_width=True)

    st.markdown("---")
    st.caption("Leads aprovados no Google Sheets\nsao enviados automaticamente.")


# ── Helpers ────────────────────────────────────────────────────────────────────
def apply_profile(choice: str):
    import config
    profile = config.AUDIENCE_PROFILES[choice]
    config.SEARCH_KEYWORDS = profile["keywords"]
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
        from sheets_manager import sheets_load_leads  # raises on auth error
        leads = sheets_load_leads()
    else:
        from leads_manager import _csv_load_leads
        leads = _csv_load_leads()

    if not leads:
        return pd.DataFrame(columns=["name", "linkedin_url", "job_title", "company", "location", "status", "source", "sent_at"])
    return pd.DataFrame([asdict(l) for l in leads.values()])


def status_color(status: str) -> str:
    return {
        "pending":  "🟡",
        "approved": "🟢",
        "sent":     "✅",
        "failed":   "🔴",
        "skipped":  "⚪",
    }.get(status, "⚫")


# ── Estado de sessão ───────────────────────────────────────────────────────────
if "logs" not in st.session_state:
    st.session_state.logs = []
if "running" not in st.session_state:
    st.session_state.running = False
if "sheet_url" not in st.session_state:
    st.session_state.sheet_url = ""


def add_log(msg: str):
    ts = time.strftime("%H:%M:%S")
    st.session_state.logs.append(f"[{ts}] {msg}")
    if len(st.session_state.logs) > 200:
        st.session_state.logs = st.session_state.logs[-200:]


# ── Titulo ─────────────────────────────────────────────────────────────────────
profile_info = {"1": "Autocustodia", "2": "Consultoria"}
st.markdown(f"# ⚡ Vault Capital — Leads LinkedIn")
st.markdown(f"**Perfil ativo:** {'🔐 Autocustodia' if profile_choice == '1' else '💼 Consultoria'}")

import config
profile_data = apply_profile(profile_choice)

# ── Metricas ───────────────────────────────────────────────────────────────────
try:
    df = load_dataframe(config.SHEET_NAME)
    if "sheets_error" in st.session_state:
        del st.session_state["sheets_error"]
except Exception as e:
    st.session_state["sheets_error"] = str(e)
    df = pd.DataFrame(columns=["name", "linkedin_url", "job_title", "company", "location", "status", "source", "sent_at"])

total    = len(df)
pending  = len(df[df.status == "pending"])  if total else 0
approved = len(df[df.status == "approved"]) if total else 0
sent     = len(df[df.status == "sent"])     if total else 0

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f'<div class="metric-card"><div class="metric-number">{total}</div><div class="metric-label">Total de Leads</div></div>', unsafe_allow_html=True)
with col2:
    st.markdown(f'<div class="metric-card"><div class="metric-number">{pending}</div><div class="metric-label">Aguardando Revisao</div></div>', unsafe_allow_html=True)
with col3:
    st.markdown(f'<div class="metric-card"><div class="metric-number">{approved}</div><div class="metric-label">Aprovados</div></div>', unsafe_allow_html=True)
with col4:
    st.markdown(f'<div class="metric-card"><div class="metric-number">{sent}</div><div class="metric-label">DMs Enviadas</div></div>', unsafe_allow_html=True)

st.markdown("---")

# ── Acoes ──────────────────────────────────────────────────────────────────────
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
            from sheets_manager import push_leads_to_sheet

            add_log("Buscando por palavras-chave...")
            keyword_leads = search_by_keywords()
            add_log(f"{len(keyword_leads)} perfis encontrados via keywords")

            add_log("Buscando engajamento em posts...")
            engagement_leads = search_by_post_engagement()
            add_log(f"{len(engagement_leads)} perfis via engajamento")

            all_leads = keyword_leads + engagement_leads
            added, dupes = add_leads(all_leads)
            add_log(f"{added} novos leads salvos ({dupes} duplicatas ignoradas)")

            add_log("Publicando no Google Sheets...")
            tab_name = time.strftime("Coleta %Y-%m-%d %H:%M")
            from models import _normalize_url
            new_leads_dict = {_normalize_url(l.linkedin_url): l for l in all_leads}
            sheet_url = push_leads_to_sheet(new_leads_dict, tab_name=tab_name)
            st.session_state.sheet_url = sheet_url
            add_log(f"Planilha atualizada!")
            st.success(f"Coleta concluida! {added} leads novos.")
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
            add_log("Envio concluido!")
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

# ── Tabela de leads ────────────────────────────────────────────────────────────
st.markdown("### Leads Coletados")

load_dataframe.clear()
try:
    df = load_dataframe(config.SHEET_NAME)  # recarrega apos acoes
except Exception as e:
    st.session_state["sheets_error"] = str(e)
    df = pd.DataFrame(columns=["name", "linkedin_url", "job_title", "company", "location", "status", "source", "sent_at"])

if "sheets_error" in st.session_state:
    st.error(f"Erro Google Sheets: {st.session_state['sheets_error']}")

if df.empty:
    st.info("Nenhum lead coletado ainda. Clique em 'Coletar Leads' para comecar.")
else:
    # Formata status com emoji
    df_display = df.copy()
    df_display["status"] = df_display["status"].apply(lambda s: f"{status_color(s)} {s}")

    # Colunas a exibir
    cols = ["name", "job_title", "company", "location", "status", "source", "linkedin_url"]
    cols = [c for c in cols if c in df_display.columns]

    st.dataframe(
        df_display[cols],
        use_container_width=True,
        height=400,
        column_config={
            "name":         st.column_config.TextColumn("Nome"),
            "job_title":    st.column_config.TextColumn("Cargo"),
            "company":      st.column_config.TextColumn("Empresa"),
            "location":     st.column_config.TextColumn("Localizacao"),
            "status":       st.column_config.TextColumn("Status"),
            "source":       st.column_config.TextColumn("Origem"),
            "linkedin_url": st.column_config.LinkColumn("LinkedIn"),
        },
    )

    if st.session_state.sheet_url:
        st.markdown(f"[Abrir planilha no Google Sheets]({st.session_state.sheet_url})")

# ── Log ao vivo ────────────────────────────────────────────────────────────────
st.markdown("### Log de Atividade")
log_text = "\n".join(st.session_state.logs[-50:]) if st.session_state.logs else "Nenhuma atividade ainda."
st.markdown(f'<div class="log-box"><pre>{log_text}</pre></div>', unsafe_allow_html=True)
