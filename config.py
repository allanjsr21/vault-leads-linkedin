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
            # Linguagem de quem USA bitcoin no dia a dia (nao quem vende)
            "hodler bitcoin brasil",
            "minha carteira ledger bitcoin",
            "guardando bitcoin cold wallet",
            "nao deixo bitcoin em exchange",
            "bitcoin hardware wallet pessoal",
            "trezor bitcoin brasil",
            "bitcoin soberania financeira pessoal",
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
            # Empresarios/executivos independentes — nao funcionarios de exchange
            "empresario investindo bitcoin",
            "socio fundador alocacao cripto",
            "CEO diversificacao patrimonio bitcoin",
            "empreendedor reserva bitcoin",
            "diretor executivo cripto brasil",
            "CFO patrimonio digital empresa",
            "investidor anjo bitcoin brasil",
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
    ' -"Bitso" -"Crypto.com" -"OKX" -"Bybit" -"Kraken"'
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
MAX_PAGES_PER_KEYWORD = 3  # paginas Brave por keyword (20 resultados cada)
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
