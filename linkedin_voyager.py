"""
Scraper direto do LinkedIn via Voyager API interna.
Usa cookies da sessão do usuário para buscar perfis reais.
Taxa: ~100 buscas/dia antes de throttling. Máx 25 resultados/busca.
"""
import logging
import time
import random
import requests
from typing import Optional

import config

log = logging.getLogger(__name__)

# Armazena debug da última resposta (acessível pelo dashboard)
_last_response_debug: dict = {}

VOYAGER_SEARCH_URL = "https://www.linkedin.com/voyager/api/search/hits"
BRAZIL_GEO_URN = "105490917"  # URN do Brasil no LinkedIn

# ── Keywords por intenção ─────────────────────────────────────────────────────
# Buscas por menção direta a Bitcoin na bio/headline
TOPIC_KEYWORDS = [
    # Identidade / autodeclaração
    "bitcoiner",
    "bitcoin maximalist",
    "bitcoin enthusiast",
    "bitcoin entusiasta",
    "hodler bitcoin",
    "hodl bitcoin",
    "stack sats",
    "laser eyes bitcoin",
    # Autocustódia
    "autocustódia bitcoin",
    "cold wallet bitcoin",
    "hardware wallet bitcoin",
    "not your keys bitcoin",
    "ledger bitcoin",
    "trezor bitcoin",
    "self custody bitcoin",
    # Investimento pessoal
    "bitcoin investidor",
    "DCA bitcoin",
    "acumulando bitcoin",
    "reserva de valor bitcoin",
    "liberdade financeira bitcoin",
    "soberania financeira bitcoin",
    "independência financeira bitcoin",
    "bitcoin aposentadoria",
    "bitcoin patrimônio",
    # Profissão + bitcoin (alto patrimônio)
    "médico bitcoin",
    "advogado bitcoin",
    "engenheiro bitcoin",
    "empresário bitcoin",
    "dentista bitcoin",
    "arquiteto bitcoin",
    "contador bitcoin",
    "consultor bitcoin",
    "CEO bitcoin",
    "diretor bitcoin",
    "sócio bitcoin",
    "fundador bitcoin",
    "investidor bitcoin",
    # Inglês
    "bitcoin hodler",
    "bitcoin advocate",
    "bitcoin believer",
    "crypto enthusiast bitcoin",
    "bitcoin investor",
]

# ── Buscas por indústria de alto patrimônio + bitcoin ────────────────────────
# (industryV2 URN, keyword)
# URNs: 14=Saúde, 9=Direito, 43=Serviços Financeiros, 45=Gestão de Investimentos,
#       1=Contabilidade, 44=Imobiliário, 96=TI/Software, 6=Banking, 100=Venture Capital
INDUSTRY_SEARCHES = [
    ("14",  "bitcoin"),          # Saúde → médicos, dentistas
    ("9",   "bitcoin"),          # Direito → advogados
    ("43",  "bitcoin"),          # Serviços Financeiros
    ("45",  "bitcoin"),          # Gestão de Investimentos
    ("1",   "bitcoin"),          # Contabilidade
    ("44",  "bitcoin"),          # Imobiliário
    ("96",  "bitcoiner"),        # TI/Software
    ("6",   "bitcoin"),          # Banking
    ("100", "bitcoin"),          # Venture Capital
    ("14",  "autocustódia"),     # Saúde → autocustódia
    ("43",  "hodler"),           # Financeiro → hodler
    ("9",   "cripto"),           # Direito → cripto
]

# ── Seniority filters para profissionais de alto nível ───────────────────────
# URNs: 10=Owner, 9=Partner, 8=CXO, 6=Director, 5=VP
HIGH_SENIORITY_SEARCHES = [
    ("10", "bitcoin"),   # Owners
    ("9",  "bitcoin"),   # Partners
    ("8",  "bitcoin"),   # C-level
    ("6",  "bitcoin"),   # Directors
]


def _read_secret(key: str) -> str:
    """Lê direto do Streamlit secrets (bypassa cache do módulo config)."""
    try:
        import streamlit as st
        return st.secrets.get(key, "") or ""
    except Exception:
        return getattr(config, key, "") or ""


def _get_headers() -> dict:
    li_at = _read_secret("LINKEDIN_LI_AT")
    jsessionid = _read_secret("LINKEDIN_JSESSIONID")
    csrf = jsessionid.strip('"').strip("'")
    return {
        "Cookie": f'li_at={li_at}; JSESSIONID="{csrf}"',
        "Csrf-Token": csrf,
        "X-Li-Lang": "pt_BR",
        "X-Restli-Protocol-Version": "2.0.0",
        "Accept": "application/vnd.linkedin.normalized+json+2.1",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "X-Li-Track": '{"clientVersion":"1.13.4","mpVersion":"1.13.4","osName":"web","timezoneOffset":-3}',
        "Referer": "https://www.linkedin.com/search/results/people/",
    }


def _voyager_search(
    keywords: str,
    start: int = 0,
    industry_urn: str = "",
    seniority_urn: str = "",
) -> Optional[list]:
    """
    Faz uma busca no Voyager API com filtros opcionais de indústria e senioridade.
    Retorna lista de perfis ou None em caso de erro/auth.
    """
    # Registrar credenciais usadas no debug (antes de qualquer request)
    _dbg_li_at = _read_secret("LINKEDIN_LI_AT")
    _last_response_debug["li_at_len"] = len(_dbg_li_at)
    _last_response_debug["status"]    = "PENDING"
    _last_response_debug["keys"]      = []
    _last_response_debug["raw"]       = ""

    # Monta filtros dinamicamente
    filters = [f"currentRegion->{BRAZIL_GEO_URN}"]
    if industry_urn:
        filters.append(f"industryV2->{industry_urn}")
    if seniority_urn:
        filters.append(f"seniorityLevel->{seniority_urn}")
    filters_str = "List(" + ",".join(filters) + ")"

    params = {
        "decorationId": "com.linkedin.voyager.deco.jserp.WebSearchPeopleResultWithDistance-5",
        "q": "jserpFilters",
        "queryContext": "List(primaryHitType->PROFILE,spellCorrectionEnabled->true)",
        "filters": filters_str,
        "keywords": keywords,
        "start": start,
        "count": 25,
        "origin": "FACETED_SEARCH",
    }

    try:
        resp = requests.get(
            VOYAGER_SEARCH_URL,
            headers=_get_headers(),
            params=params,
            timeout=20,
        )

        # Capturar status e corpo ANTES de qualquer parse
        _last_response_debug["status"]   = resp.status_code
        _last_response_debug["raw"]      = resp.text[:800]
        _last_response_debug["content_type"] = resp.headers.get("Content-Type", "")
        log.info(f"[voyager] HTTP {resp.status_code} ct={resp.headers.get('Content-Type','')} raw={resp.text[:300]}")

        if resp.status_code == 401:
            log.warning("[voyager] Cookies expirados.")
            return None
        if resp.status_code == 429:
            log.warning("[voyager] Rate limit atingido. Aguardando 60s...")
            time.sleep(60)
            return None
        if resp.status_code == 404:
            log.warning("[voyager] HTTP 404 — conta nova ou sem acesso ao Voyager Search.")
            return None
        if resp.status_code != 200:
            log.warning(f"[voyager] HTTP {resp.status_code}: {resp.text[:300]}")
            return None

        data = resp.json()

        # Debug: guardar estrutura da resposta
        top_keys = list(data.keys()) if isinstance(data, dict) else []
        _last_response_debug["keys"] = top_keys
        log.info(f"[voyager] JSON keys={top_keys}")

        results = []

        # ── Formato 1: {"elements": [...]} — resposta direta ─────────────────
        elements = data.get("elements", [])

        # ── Formato 2: {"data": {"elements": [...]}} — wrapper aninhado ──────
        if not elements and isinstance(data.get("data"), dict):
            elements = data["data"].get("elements", [])

        log.info(f"[voyager] elements encontrados: {len(elements)}")

        # ── Formato 3: {"included": [...]} — JSON normalizado (mais comum) ───
        # Neste formato, "elements" tem apenas referências e os perfis reais
        # ficam em "included" com $type contendo "miniProfile"
        included = data.get("included", [])
        if not elements and included:
            log.info(f"[voyager] Tentando formato 'included' ({len(included)} itens)")
            for item in included:
                item_type = str(item.get("$type", "") or item.get("entityUrn", ""))
                # Aceitar qualquer item que tenha publicIdentifier (miniProfile)
                vanity = item.get("publicIdentifier", "").strip()
                if not vanity:
                    continue
                first    = item.get("firstName", "").strip()
                last     = item.get("lastName", "").strip()
                name     = f"{first} {last}".strip()
                headline = item.get("occupation", "").strip()
                location = item.get("geoLocationName", "") or item.get("locationName", "")
                location = location.strip() if location else ""
                if name and vanity:
                    results.append({
                        "name":     name,
                        "vanity":   vanity,
                        "headline": headline,
                        "location": location,
                        "url":      f"https://www.linkedin.com/in/{vanity}",
                    })
            log.info(f"[voyager] formato included → {len(results)} perfis")
            return results

        if elements:
            first_el_keys = list(elements[0].keys()) if elements else []
            log.info(f"[voyager] primeiro elemento keys={first_el_keys}")

        for el in elements:
            hit_info = el.get("hitInfo", {})
            # Tentar múltiplos formatos de resposta do Voyager
            profile_data = (
                hit_info.get("com.linkedin.voyager.search.SearchProfile")
                or hit_info.get("com.linkedin.voyager.search.BlendedSearchProfile")
                or hit_info.get("com.linkedin.voyager.search.WebSearchHit")
                or {}
            )
            # Formato alternativo: perfil direto no elemento (sem hitInfo)
            if not profile_data and el.get("publicIdentifier"):
                profile_data = el

            if not profile_data:
                # Último recurso: procurar publicIdentifier em qualquer lugar do elemento
                pub_id = el.get("publicIdentifier", "")
                if pub_id:
                    profile_data = el
                else:
                    continue

            # Suporte ao formato legado (miniProfile aninhado)
            mini = profile_data.get("miniProfile") or profile_data
            if not mini:
                continue

            first    = mini.get("firstName", "").strip()
            last     = mini.get("lastName", "").strip()
            name     = f"{first} {last}".strip()
            vanity   = mini.get("publicIdentifier", "").strip()
            headline = mini.get("occupation", "").strip()
            location = (
                profile_data.get("locationName", "")
                or profile_data.get("geoLocationName", "")
                or mini.get("geoLocationName", "")
            ).strip()

            if not name or not vanity:
                continue

            results.append({
                "name":     name,
                "vanity":   vanity,
                "headline": headline,
                "location": location,
                "url":      f"https://www.linkedin.com/in/{vanity}",
            })

        log.info(
            f"[voyager] kw='{keywords}' ind={industry_urn or '-'} "
            f"sen={seniority_urn or '-'} start={start} → {len(results)} perfis"
        )
        return results

    except Exception as e:
        _last_response_debug["status"] = f"EXCEPTION:{type(e).__name__}"
        _last_response_debug["raw"]    = str(e)[:400]
        log.error(f"[voyager] Erro: {type(e).__name__}: {e}")
        return None


def _get_similar_profiles(vanity: str) -> list:
    """
    Busca perfis similares a um vanity URL via 'People Also Viewed'.
    Retorna lista de dicts ou [] em caso de erro.
    """
    li_at = _read_secret("LINKEDIN_LI_AT")
    if not li_at:
        return []

    url = f"https://www.linkedin.com/voyager/api/identity/profiles/{vanity}/browseMaps"
    params = {
        "decorationId": "com.linkedin.voyager.deco.identity.profile.ProfileBrowseMap-5",
        "q": "browseMaps",
        "type": "BROWSEMAP",
    }

    try:
        resp = requests.get(url, headers=_get_headers(), params=params, timeout=15)
        if resp.status_code != 200:
            return []

        data = resp.json()
        results = []
        for el in data.get("elements", []):
            mini = el.get("miniProfile", {})
            if not mini:
                continue
            first  = mini.get("firstName", "").strip()
            last   = mini.get("lastName", "").strip()
            name   = f"{first} {last}".strip()
            vanity = mini.get("publicIdentifier", "").strip()
            headline = mini.get("occupation", "").strip()
            if name and vanity:
                results.append({
                    "name":     name,
                    "vanity":   vanity,
                    "headline": headline,
                    "location": "",
                    "url":      f"https://www.linkedin.com/in/{vanity}",
                })
        log.info(f"[voyager] similar de '{vanity}' → {len(results)} perfis")
        return results
    except Exception as e:
        log.error(f"[voyager] similar error: {e}")
        return []


# Perfis semente — bitcoiners conhecidos no Brasil para seed de "similar profiles"
SEED_PROFILES = [
    "bitcoinheiros",
    "lucasnuzzi",
    "fernandoulrich",
    "bitcoindidático",
    "gustavocaetano",
]


def search_linkedin_direct(max_results: int = 100, callback=None) -> list:
    """
    Busca perfis diretamente no LinkedIn via Voyager API.
    3 estratégias em sequência:
      1. Keywords diretas (bio menciona bitcoin)
      2. Filtro por indústria de alto patrimônio + bitcoin
      3. Filtro por senioridade alta + bitcoin
      4. Seed: perfis similares a bitcoiners conhecidos
    """
    if not _read_secret("LINKEDIN_LI_AT"):
        log.warning("[voyager] LINKEDIN_LI_AT não configurado — pulando busca direta.")
        return []

    from scraper import _location_allowed

    seen_vanity: set = set()
    leads_raw = []

    def _process_results(results, source_label=""):
        """Filtra e adiciona resultados ao leads_raw."""
        new = 0
        for r in results:
            if len(leads_raw) >= max_results:
                break
            if r["vanity"] in seen_vanity:
                continue
            seen_vanity.add(r["vanity"])
            if r["location"] and not _location_allowed(r["location"], r["headline"]):
                continue
            leads_raw.append(r)
            new += 1
        return new

    def _run_search(keywords, industry="", seniority="", pages=2):
        """Executa busca paginada e retorna novos leads adicionados."""
        if len(leads_raw) >= max_results:
            return 0
        total_new = 0
        for page in range(pages):
            if len(leads_raw) >= max_results:
                break
            results = _voyager_search(keywords, start=page * 25,
                                       industry_urn=industry, seniority_urn=seniority)
            if results is None:   # auth error — para tudo
                return -1
            if not results:
                break
            added = _process_results(results)
            total_new += added
            if callback:
                callback(len(leads_raw), max_results, keywords)
            if not added:
                break
            time.sleep(random.uniform(2.5, 5.0))
        return total_new

    # ── Estratégia 1: Keywords diretas ───────────────────────────────────────
    log.info("[voyager] Estratégia 1: keywords diretas")
    kw_list = list(TOPIC_KEYWORDS)
    random.shuffle(kw_list)

    # Fazer uma busca de diagnóstico e logar a resposta bruta via callback
    _diag = _voyager_search(kw_list[0], start=0)
    if callback:
        dbg = _last_response_debug
        callback(0, max_results,
                 f"[DEBUG Voyager] li_at_len={dbg.get('li_at_len')} "
                 f"status={dbg.get('status')} ct={dbg.get('content_type','')} "
                 f"keys={dbg.get('keys')} raw={str(dbg.get('raw',''))[:300]}")
    if _diag is None:
        log.error("[voyager] Diagnóstico: auth error")
        return leads_raw

    for kw in kw_list:
        if len(leads_raw) >= max_results:
            break
        r = _run_search(kw, pages=2)
        if r == -1:  # cookies inválidos
            log.error("[voyager] Abortando — cookies inválidos")
            return leads_raw
        time.sleep(random.uniform(1.5, 3.0))

    # ── Estratégia 2: Filtro por indústria de alto patrimônio ────────────────
    if len(leads_raw) < max_results:
        log.info("[voyager] Estratégia 2: filtro por indústria")
        ind_list = list(INDUSTRY_SEARCHES)
        random.shuffle(ind_list)
        for ind_urn, kw in ind_list:
            if len(leads_raw) >= max_results:
                break
            r = _run_search(kw, industry=ind_urn, pages=2)
            if r == -1:
                return leads_raw
            time.sleep(random.uniform(1.5, 3.0))

    # ── Estratégia 3: Filtro por senioridade alta ─────────────────────────────
    if len(leads_raw) < max_results:
        log.info("[voyager] Estratégia 3: filtro por senioridade")
        for sen_urn, kw in HIGH_SENIORITY_SEARCHES:
            if len(leads_raw) >= max_results:
                break
            r = _run_search(kw, seniority=sen_urn, pages=2)
            if r == -1:
                return leads_raw
            time.sleep(random.uniform(1.5, 3.0))

    # ── Estratégia 4: Perfis similares a bitcoiners conhecidos ───────────────
    if len(leads_raw) < max_results:
        log.info("[voyager] Estratégia 4: perfis similares (seed)")
        for seed in SEED_PROFILES:
            if len(leads_raw) >= max_results:
                break
            similar = _get_similar_profiles(seed)
            _process_results(similar, source_label=f"similar:{seed}")
            if callback:
                callback(len(leads_raw), max_results, f"similar:{seed}")
            time.sleep(random.uniform(2.0, 4.0))

    log.info(f"[voyager] Total coletado: {len(leads_raw)} perfis")
    return leads_raw
