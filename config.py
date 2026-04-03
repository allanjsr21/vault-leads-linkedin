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

# ── Anthropic API (Claude) — para scoring inteligente de leads ───────────────
ANTHROPIC_API_KEY = _get_secret("ANTHROPIC_API_KEY", "")

# ── Hunter.io — para enriquecimento de email ─────────────────────────────────
HUNTER_API_KEY = _get_secret("HUNTER_API_KEY", "")

# ── Gmail SMTP — para envio de email follow-up ───────────────────────────────
# GMAIL_USER = conta Google com App Password (ex: allan.junior777@gmail.com)
# GMAIL_REPLY_TO = email profissional que aparece como remetente
GMAIL_USER         = _get_secret("GMAIL_USER", "")
GMAIL_APP_PASSWORD = _get_secret("GMAIL_APP_PASSWORD", "")
GMAIL_REPLY_TO     = _get_secret("GMAIL_REPLY_TO", "allanjunior@vaultcapital.com.br")
GMAIL_SENDER_NAME  = _get_secret("GMAIL_SENDER_NAME", "Allan Junior | Vault Capital")

# ── Google Custom Search API (100 queries/dia grátis) ─────────────────────────
# Setup: https://programmablesearchengine.google.com → criar engine → search entire web
# API key: https://console.cloud.google.com → Custom Search API → Create Credentials
GOOGLE_CSE_API_KEY = _get_secret("GOOGLE_CSE_API_KEY", "")
GOOGLE_CSE_ID      = _get_secret("GOOGLE_CSE_ID", "")

# ── Chrome ────────────────────────────────────────────────────────────────────
CHROME_PROFILE_PATH = _os.path.expandvars(
    r"%LOCALAPPDATA%\Google\Chrome\User Data"
)

# ── Geração programática de keywords ─────────────────────────────────────────
# Combina tópicos × cidades para cobertura máxima

CITIES_PRIORITY = [
    '"São Paulo"', '"Rio de Janeiro"', '"Belo Horizonte"',
    'Curitiba', 'Campinas', '"Espírito Santo"',
    '"Porto Alegre"', '"Florianópolis"', '"Brasília"',
]

def _generate_keywords(topics: list[str], cities: list[str], generic_kws: list[str] = []) -> list[str]:
    """Gera keywords combinando tópicos × cidades + genéricas."""
    kws = []
    for topic in topics:
        for city in cities:
            kws.append(f'{topic} {city}')
    kws.extend(generic_kws)
    return kws


# ── Perfis de Público ──────────────────────────────────────────────────────────
# Cada perfil tem: keywords, mensagem e nome da planilha

# ── Autocustódia: pessoas que TÊM INTERESSE em bitcoin (não profissionais cripto) ──
# Foco em sinais de interesse: entusiasta, investidor pessoal, hodler

_AUTOCUSTODIA_TOPICS = [
    # Autodeclarações de interesse (o que escrevem no perfil)
    '"entusiasta bitcoin"',
    '"entusiasta de bitcoin"',
    '"entusiasta cripto"',
    '"apaixonado por bitcoin"',
    '"bitcoin enthusiast"',
    '"investidor bitcoin"',
    '"bitcoiner"',
    # Sinais de atividade / ownership
    '"hodler" bitcoin',
    '"investidor de criptomoedas"',
    '"acumulando bitcoin"',
    '"DCA bitcoin"',
    # Sinais de autocustódia
    '"cold wallet"',
    '"hardware wallet" pessoal',
    '"soberania financeira"',
    # Profissão + interesse (qualquer profissional que mencione bitcoin)
    '"médico" "bitcoin"',
    '"advogado" "bitcoin"',
    '"engenheiro" "bitcoin"',
    '"empresário" "bitcoin"',
    '"dentista" "bitcoin"',
    '"arquiteto" "bitcoin"',
    '"professor" "bitcoin"',
    '"contador" "bitcoin"',
]

_AUTOCUSTODIA_GENERIC = [
    '"entusiasta bitcoin" Brasil',
    '"investidor bitcoin" Brasil',
    '"apaixonado por bitcoin" Brasil',
    '"bitcoin hodler" Brasil',
    '"meu bitcoin" Brasil',
    '"soberania financeira" bitcoin Brasil',
    '"bitcoiner" brasileiro',
    '"entusiasta de criptomoedas" Brasil',
    '"not your keys" Brasil',
    '"interessado em bitcoin" Brasil',
]

# ── Consultoria: pessoas com patrimônio que querem orientação sobre cripto ──
# Foco em profissionais de alta renda que demonstram interesse em cripto

_CONSULTORIA_TOPICS = [
    '"investidor" "bitcoin"',
    '"patrimônio" "bitcoin"',
    '"diversificação" "bitcoin"',
    '"alocação" "cripto"',
    '"investidor" "criptomoeda"',
    '"entusiasta" "blockchain"',
    '"empresário" "cripto"',
    '"empreendedor" "bitcoin"',
    '"gestão de patrimônio" "cripto"',
    '"family office" "bitcoin"',
    '"investimento alternativo" "bitcoin"',
]

_CONSULTORIA_GENERIC = [
    '"investidor bitcoin" Brasil',
    '"patrimônio digital" Brasil',
    '"diversificação cripto" Brasil',
    '"alocação em bitcoin" Brasil',
    '"consultoria cripto" Brasil',
    '"assessoria bitcoin" Brasil',
    '"gestão patrimônio" "criptoativos" Brasil',
]

AUDIENCE_PROFILES = {
    "1": {
        "name": "Autocustodia",
        "description": "Evento de autocustodia — pessoas interessadas em guardar o proprio Bitcoin",
        "keywords": _generate_keywords(_AUTOCUSTODIA_TOPICS, CITIES_PRIORITY, _AUTOCUSTODIA_GENERIC),
        "location_filter": "(\"São Paulo\" OR \"Rio de Janeiro\" OR \"Belo Horizonte\" OR \"Espírito Santo\" OR \"Campinas\" OR \"Curitiba\") Brazil",
        "sheet_name": "Vault — Leads Autocustodia",
        "leads_csv": "leads_autocustodia.csv",
        "dm_template": """Ola, {first_name}! Tudo bem?

Vi que voce tem interesse em autocustodia e soberania financeira com Bitcoin — e queria te convidar para um evento exclusivo que a Vault Capital esta organizando sobre o tema.

Vamos falar sobre como guardar seus proprios ativos com seguranca, sem depender de exchanges, e ter controle total do seu patrimonio digital.

Se fizer sentido pra voce, adoraria te ver por la! Posso te mandar mais detalhes?

Abracos,
Vault Capital""",
        "email_subject": "Convite: Evento de Autocustodia Bitcoin — Vault Capital",
        "email_template": """Ola, {first_name}!

Meu nome e Allan, da Vault Capital. Tentei te contactar pelo LinkedIn, mas queria garantir que voce recebesse nosso convite.

Estamos organizando um evento exclusivo sobre autocustodia de Bitcoin — como guardar seus ativos com seguranca total, sem depender de exchanges.

Se voce ja investe ou tem interesse em Bitcoin, esse evento e pra voce.

Posso te mandar mais detalhes sobre data e local?

Abracos,
Allan Junior
Vault Capital
""",
        "connection_note": """Ola, {first_name}! Vi que voce tem interesse em Bitcoin. Estou conectando profissionais que investem em cripto de forma independente. Vamos trocar ideias?""",
    },

    "2": {
        "name": "Consultoria",
        "description": "Consultoria — empresarios e executivos que querem orientacao profissional em cripto",
        "keywords": _generate_keywords(_CONSULTORIA_TOPICS, CITIES_PRIORITY, _CONSULTORIA_GENERIC),
        "location_filter": "Brazil",
        "sheet_name": "Vault — Leads Consultoria",
        "leads_csv": "leads_consultoria.csv",
        "dm_template": """Ola, {first_name}! Tudo bem?

Vi seu perfil e queria apresentar a Vault Capital — somos uma gestora especializada em criptoativos, focada em atender empresarios e executivos que querem exposicao ao mercado digital com estrategia e seguranca.

Oferecemos consultoria personalizada para quem quer entrar em cripto de forma profissional, sem perder tempo tentando entender o mercado sozinho.

Se fizer sentido pra voce, adoraria bater um papo rapido. Fico a disposicao!

Abracos,
Vault Capital""",
        "email_subject": "Consultoria em Criptoativos — Vault Capital",
        "email_template": """Ola, {first_name}!

Meu nome e Allan, da Vault Capital. Tentei te contactar pelo LinkedIn e gostaria de me apresentar rapidamente.

Somos uma gestora especializada em criptoativos, focada em atender empresarios e executivos que querem exposicao ao mercado digital com estrategia e seguranca.

Se voce tem interesse em diversificar parte do patrimonio em cripto de forma profissional, adoraria bater um papo rapido de 15 minutos.

Fico a disposicao!

Abracos,
Allan Junior
Vault Capital
""",
        "connection_note": """Ola, {first_name}! Sou da Vault Capital, gestora especializada em criptoativos. Vi seu perfil e gostaria de conectar para trocar ideias sobre o mercado.""",
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
MAX_PAGES_PER_KEYWORD = 3  # paginas por keyword (para economizar cota)
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
