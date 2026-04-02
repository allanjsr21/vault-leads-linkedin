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
            # São Paulo
            "bitcoin autocustodia \"São Paulo\"",
            "bitcoin hardware wallet \"São Paulo\"",
            "hodler bitcoin \"São Paulo\"",
            "ledger trezor bitcoin \"São Paulo\"",
            "bitcoin cold storage \"São Paulo\"",
            # Rio de Janeiro
            "bitcoin autocustodia \"Rio de Janeiro\"",
            "bitcoin hardware wallet \"Rio de Janeiro\"",
            "hodler bitcoin \"Rio de Janeiro\"",
            # Belo Horizonte / Minas
            "bitcoin autocustodia \"Belo Horizonte\"",
            "bitcoin self custody \"Minas Gerais\"",
            # Curitiba / Sul
            "bitcoin hardware wallet Curitiba",
            "hodler bitcoin Curitiba",
            # Campinas / interior SP
            "bitcoin autocustodia Campinas",
            "bitcoin cold wallet \"interior de São Paulo\"",
            # Brasil genérico
            "bitcoin soberania financeira pessoal Brasil",
            "guardando bitcoin cold wallet Brasil",
            "trezor ledger bitcoin brasileiro",
        ],
        "location_filter": "(\"São Paulo\" OR \"Rio de Janeiro\" OR \"Belo Horizonte\" OR \"Espírito Santo\" OR \"Campinas\" OR \"Curitiba\") Brazil",
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
            # São Paulo
            "empresario investindo bitcoin \"São Paulo\"",
            "empreendedor reserva bitcoin \"São Paulo\"",
            "socio fundador bitcoin \"São Paulo\"",
            "CEO alocacao cripto \"São Paulo\"",
            "investidor anjo bitcoin \"São Paulo\"",
            # Rio de Janeiro
            "empresario bitcoin \"Rio de Janeiro\"",
            "empreendedor cripto \"Rio de Janeiro\"",
            # Belo Horizonte
            "empresario bitcoin \"Belo Horizonte\"",
            # Curitiba
            "empreendedor bitcoin Curitiba",
            # Brasil genérico
            "CFO patrimonio digital Brasil",
            "diretor executivo cripto Brasil",
            "empresario bitcoin Brasil",
            "fundador startup cripto Brasil",
        ],
        "location_filter": "Brazil",
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

# ── Exclusões de busca (evita funcionarios de exchanges conhecidas) ────────────
SEARCH_EXCLUSIONS = (
    '-"Mercado Bitcoin" -"Binance" -"Coinbase" -"Foxbit" -"NovaDAX"'
    ' -"Bitso" -"Crypto.com" -"OKX" -"Bybit" -"Kraken" -"Bitget"'
    ' -"Chairman" -"Board Member" -"Deputado" -"Senador"'
)

# ── Cargos inalcançáveis (leads com esses termos no cargo são descartados) ────
TITLE_EXCLUSIONS = [
    "Board Member", "Chairman", "Chairwoman",
    "Presidente do Conselho", "Conselheiro",
    "Deputado", "Senador", "Ministro", "Minister",
    "Governador", "Prefeito", "Secretário de Estado",
    "Ambassador", "Embaixador",
]

# ── Limites de operação ────────────────────────────────────────────────────────
MAX_LEADS_PER_RUN = 100
MAX_PAGES_PER_KEYWORD = 5  # paginas Brave por keyword (20 resultados cada)
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
