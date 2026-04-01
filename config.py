"""
Configurações do agente de leads da Vault Capital no LinkedIn.
"""

import os as _os

# ── Secrets ───────────────────────────────────────────────────────────────────
# Lê do Streamlit secrets (cloud) ou direto (local)
def _get_secret(key: str, fallback: str = "") -> str:
    try:
        import streamlit as st
        return st.secrets.get(key, fallback)
    except Exception:
        return fallback

# ── Brave Search API ──────────────────────────────────────────────────────────
BRAVE_SEARCH_API_KEY = _get_secret("BRAVE_SEARCH_API_KEY", "")

# ── Chrome ────────────────────────────────────────────────────────────────────
CHROME_PROFILE_PATH = _os.path.expandvars(
    r"%LOCALAPPDATA%\Google\Chrome\User Data"
)

# ── Perfis de Público ──────────────────────────────────────────────────────────
# Cada perfil tem: keywords, mensagem e nome da planilha

AUDIENCE_PROFILES = {
    "1": {
        "name": "Autocustodia",
        "description": "Evento de autocustodia — pessoas interessadas em guardar o proprio Bitcoin",
        "keywords": [
            "autocustodia Bitcoin",
            "cold wallet Brasil",
            "hardware wallet Bitcoin",
            "soberania financeira cripto",
            "Bitcoin self custody",
            "carteira fria criptomoeda",
            "seed phrase Bitcoin",
        ],
        "sheet_name": "Vault — Leads Autocustodia",
        "leads_csv": "leads_autocustodia.csv",
        "dm_template": """Ola, {first_name}! Tudo bem?

Vi que voce tem interesse em autocustodia e soberania financeira com Bitcoin — e queria te convidar para um evento exclusivo que a Vault Capital esta organizando sobre o tema.

Vamos falar sobre como guardar seus proprios ativos com seguranca, sem depender de exchanges, e ter controle total do seu patrimonio digital.

Se fizer sentido pra voce, adoraria te ver por la! Posso te mandar mais detalhes?

Abracos,
Vault Capital""",
    },

    "2": {
        "name": "Consultoria",
        "description": "Consultoria — empresarios e executivos que querem orientacao profissional em cripto",
        "keywords": [
            "CEO investidor Brasil",
            "fundador patrimonio digital",
            "executivo diversificacao investimento",
            "empresario Bitcoin",
            "CFO criptoativos",
            "gestor patrimonio cripto",
            "investidor qualificado blockchain",
        ],
        "sheet_name": "Vault — Leads Consultoria",
        "leads_csv": "leads_consultoria.csv",
        "dm_template": """Ola, {first_name}! Tudo bem?

Vi seu perfil e queria apresentar a Vault Capital — somos uma gestora especializada em criptoativos, focada em atender empresarios e executivos que querem exposicao ao mercado digital com estrategia e seguranca.

Oferecemos consultoria personalizada para quem quer entrar em cripto de forma profissional, sem perder tempo tentando entender o mercado sozinho.

Se fizer sentido pra voce, adoraria bater um papo rapido. Fico a disposicao!

Abracos,
Vault Capital""",
    },
}

# ── Filtro de localização ──────────────────────────────────────────────────────
LOCATION_FILTER = "Brazil"

# ── Limites de operação ────────────────────────────────────────────────────────
MAX_LEADS_PER_RUN = 50
MAX_DMS_PER_DAY = 20
DELAY_BETWEEN_DMS = (30, 90)

# ── Google Sheets ──────────────────────────────────────────────────────────────
GOOGLE_OAUTH_FILE = "oauth_credentials.json"
GOOGLE_TOKEN_FILE = "google_token.json"
SHEET_OWNER_EMAIL = "allanjunior@vaultcapital.com.br"

# ── Arquivos de saída ──────────────────────────────────────────────────────────
LOG_FILE = "agent.log"

# ── Compat (usado em scraper.py) ───────────────────────────────────────────────
# Preenchidos dinamicamente pelo main.py conforme perfil escolhido
SEARCH_KEYWORDS: list[str] = []
CRYPTO_POST_URLS: list[str] = []
SHEET_NAME = ""
LEADS_CSV = "leads.csv"
DM_TEMPLATE = ""
