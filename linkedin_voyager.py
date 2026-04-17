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


def _get_headers() -> dict:
    li_at = getattr(config, "LINKEDIN_LI_AT", "")
    jsessionid = getattr(config, "LINKEDIN_JSESSIONID", "")
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
    li_at = getattr(config, "LINKEDIN_LI_AT", "")
    if not li_at:
        return None

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
        if resp.status_code == 401:
            log.warning(
                "[voyager] Cookies expirados. Atualize LINKEDIN_LI_AT e "
                "LINKEDIN_JSESSIONID em Application > Cookies no DevTools (F12)."
            )
            return None
        if resp.status_code == 429:
            log.warning("[voyager] Rate limit atingido. Aguardando 60s...")
            time.sleep(60)
            return None
        if resp.status_code == 404:
            log.warning(
                "[voyager] HTTP 404 — conta muito nova ou sem acesso ao Voyager Search. "
                "Aguarde 24-48h, faça posts/conexões/curtidas na conta e tente novamente."
            )
            return None
        if resp.status_code != 200:
            log.warning(f"[voyager] HTTP {resp.status_code}: {resp.text[:300]}")
            return None

        data = resp.json()
        elements = data.get("elements", [])
        results = []

        for el in elements:
            hit_info = el.get("hitInfo", {})
            profile_data = (
                hit_info.get("com.linkedin.voyager.search.SearchProfile")
                or hit_info.get("com.linkedin.voyager.search.BlendedSearchProfile")
                or {}
            )
            if not profile_data:
                continue

            mini = profile_data.get("miniProfile", {})
            if not mini:
                continue

            first    = mini.get("firstName", "").strip()
            last     = mini.get("lastName", "").strip()
            name     = f"{first} {last}".strip()
            vanity   = mini.get("publicIdentifier", "").strip()
            headline = mini.get("occupation", "").strip()
            location = profile_data.get("locationName", "").strip()

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
        log.error(f"[voyager] Erro: {e}")
        return None


def _get_similar_profiles(vanity: str) -> list:
    """
    Busca perfis similares a um vanity URL via 'People Also Viewed'.
    Retorna lista de dicts ou [] em caso de erro.
    """
    li_at = getattr(config, "LINKEDIN_LI_AT", "")
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
    if not getattr(config, "LINKEDIN_LI_AT", ""):
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
