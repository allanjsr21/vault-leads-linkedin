"""
Módulo de coleta de leads via Brave Search API + Google Custom Search.

Fontes:
  1. Brave Search API (2000 queries/mês — gratuito)
  2. Google Custom Search API (100 queries/dia — gratuito)
  3. LinkedIn articles/posts via Brave (encontra autores de conteúdo crypto)

Todas usam site:linkedin.com/in para garantir perfis individuais.
"""

import logging
import random
import re
import time
from typing import Optional

import requests

import config
from config import LOCATION_FILTER, MAX_LEADS_PER_RUN, MAX_PAGES_PER_KEYWORD, TITLE_EXCLUSIONS
from models import Lead, _normalize_url

log = logging.getLogger(__name__)

BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"
GOOGLE_CSE_URL   = "https://www.googleapis.com/customsearch/v1"


# ── Parser de resultados ────────────────────────────────────────────────────────

# Padrão de localização brasileira (compilado uma vez)
BR_PATTERN = re.compile(
    r"(?:Brazil|Brasil|"
    r"São Paulo|Rio de Janeiro|Belo Horizonte|Brasília|Curitiba|Fortaleza|"
    r"Manaus|Salvador|Recife|Porto Alegre|Belém|Goiânia|Florianópolis|"
    r"Ribeirão Preto|Sorocaba|Santos|Juiz de Fora|Niterói|Vitória|"
    r"Uberlândia|Joinville|Londrina|Maringá|Campinas|"
    r"Região Metropolitana de \w+|Greater\s+\w+|"
    r",\s*(?:SP|RJ|MG|RS|PR|SC|BA|GO|DF|CE|PE|AM|MS|MT|PA|ES|PB|RN|AL|"
    r"SE|PI|MA|AP|RO|AC|RR|TO)\b)",
    re.IGNORECASE,
)


def _parse_result(item: dict, source: str, keyword: str = "") -> Optional[Lead]:
    """
    Converte um resultado de busca (Brave ou Google CSE) em Lead.
    Formato típico:
      title:       "João Silva - CEO at Empresa X | LinkedIn"
      url:         "https://www.linkedin.com/in/joaosilva"
      description: "São Paulo, Brazil. CEO at Empresa X. 500+ connections."
    """
    url = item.get("url", "") or item.get("link", "")
    if "linkedin.com/in/" not in url:
        return None

    title       = item.get("title", "")
    description = item.get("description", "") or item.get("snippet", "")

    # ── Nome ──────────────────────────────────────────────────────────────────
    name = re.split(r"\s*[-–|]\s*", title)[0].strip()
    if not name:
        return None

    # ── Cargo e empresa ───────────────────────────────────────────────────────
    title_parts = re.split(r"\s*[-–|]\s*", title)
    job_title = ""
    company   = ""
    for part in title_parts[1:]:
        part = part.strip()
        if part.lower() in ("linkedin", ""):
            continue
        at_match = re.split(r"\s+(?:at|na|em|@)\s+", part, maxsplit=1, flags=re.IGNORECASE)
        if len(at_match) == 2:
            job_title = at_match[0].strip()
            company   = at_match[1].strip()
        elif not job_title:
            job_title = part
        break

    # ── Localização ───────────────────────────────────────────────────────────
    location = ""
    for text in (description, title):
        if location:
            break
        for seg in re.split(r"[.\n·|]", text):
            seg = seg.strip()
            if not seg or len(seg) > 120:
                continue
            if seg.lower() in ("linkedin", ""):
                continue
            if BR_PATTERN.search(seg):
                location = seg
                break

    # ── Filtro de cargos inalcançáveis ────────────────────────────────────────
    if job_title and TITLE_EXCLUSIONS:
        jt_lower = job_title.lower()
        for excl in TITLE_EXCLUSIONS:
            if excl.lower() in jt_lower:
                log.debug(f"[scraper] Descartado (cargo inalcançável): {name} - {job_title}")
                return None

    # ── Fallback de localização: extrai do keyword ────────────────────────────
    if not location and keyword:
        kw_match = BR_PATTERN.search(keyword)
        if kw_match:
            location = kw_match.group(0).strip()

    return Lead(
        name=name,
        linkedin_url=url,
        job_title=job_title,
        company=company,
        location=location,
        bio=description[:300] if description else "",
        source=source,
        status="pending",
    )


# ── Brave Search ─────────────────────────────────────────────────────────────────

def _brave_search(query: str, offset: int = 0) -> Optional[list[dict]]:
    """Executa uma busca no Brave Search API. Retorna lista de resultados ou None."""
    api_key = config.BRAVE_SEARCH_API_KEY
    if not api_key:
        return None

    try:
        resp = requests.get(
            BRAVE_SEARCH_URL,
            headers={
                "Accept":               "application/json",
                "Accept-Encoding":      "gzip",
                "X-Subscription-Token": api_key,
            },
            params={"q": query, "count": 20, "offset": offset},
            timeout=15,
        )
        if resp.status_code == 429:
            log.warning("[brave] Cota mensal atingida.")
            return None
        if resp.status_code != 200:
            log.warning(f"[brave] HTTP {resp.status_code}: {resp.text[:200]}")
            return None
        return resp.json().get("web", {}).get("results", [])
    except requests.RequestException as e:
        log.error(f"[brave] Erro de conexão: {e}")
        return None


# ── Google Custom Search ─────────────────────────────────────────────────────────

def _google_cse_search(query: str, start: int = 1) -> Optional[list[dict]]:
    """Executa busca no Google Custom Search API. Retorna lista de resultados ou None."""
    api_key = getattr(config, "GOOGLE_CSE_API_KEY", "")
    cse_id  = getattr(config, "GOOGLE_CSE_ID", "")
    if not api_key or not cse_id:
        return None

    try:
        resp = requests.get(
            GOOGLE_CSE_URL,
            params={"key": api_key, "cx": cse_id, "q": query, "num": 10, "start": start},
            timeout=15,
        )
        if resp.status_code != 200:
            log.warning(f"[google] HTTP {resp.status_code}: {resp.text[:200]}")
            return None
        items = resp.json().get("items", [])
        # Normaliza campos para o formato esperado pelo parser
        for item in items:
            item["url"]         = item.get("link", "")
            item["description"] = item.get("snippet", "")
        return items
    except requests.RequestException as e:
        log.error(f"[google] Erro de conexão: {e}")
        return None


# ── Delay humanizado ─────────────────────────────────────────────────────────────

def _human_delay():
    """Delay aleatório entre requests para simular comportamento humano."""
    time.sleep(random.uniform(1.5, 3.5))


# ── Busca por keywords (Brave + Google) ─────────────────────────────────────────

def search_by_keywords(
    keywords: Optional[list[str]] = None,
    max_results: int = MAX_LEADS_PER_RUN,
) -> list[Lead]:
    """
    Busca perfis LinkedIn via Brave Search API + Google Custom Search.
    Combina ambas as fontes para máxima cobertura.
    """
    keywords   = keywords or config.SEARCH_KEYWORDS
    exclusions = getattr(config, "SEARCH_EXCLUSIONS", "")
    leads: list[Lead] = []

    # ── Deduplicação cross-run: carregar leads já existentes ──────────────
    seen_urls: set[str] = set()
    try:
        from leads_manager import load_leads
        existing = load_leads()
        seen_urls = set(existing.keys())
        log.info(f"[scraper] {len(seen_urls)} leads existentes carregados para dedup")
    except Exception:
        pass  # primeira execução, sem leads anteriores

    # ── Randomizar ordem das keywords (evita mesmos resultados) ──────────
    keywords = list(keywords)
    random.shuffle(keywords)

    has_brave  = bool(config.BRAVE_SEARCH_API_KEY)
    has_google = bool(getattr(config, "GOOGLE_CSE_API_KEY", "")) and bool(getattr(config, "GOOGLE_CSE_ID", ""))

    if not has_brave and not has_google:
        raise ValueError(
            "Nenhuma API de busca configurada.\n"
            "Configure BRAVE_SEARCH_API_KEY e/ou GOOGLE_CSE_API_KEY + GOOGLE_CSE_ID."
        )

    sources_label = []
    if has_brave:  sources_label.append("Brave")
    if has_google: sources_label.append("Google")
    log.info(f"[scraper] Fontes ativas: {' + '.join(sources_label)}")
    log.info(f"[scraper] {len(keywords)} keywords configuradas")

    for keyword in keywords:
        if len(leads) >= max_results:
            break

        base_query = f"site:linkedin.com/in {keyword} {LOCATION_FILTER}"
        if exclusions:
            base_query += f" {exclusions}"

        # ── Brave Search (até MAX_PAGES_PER_KEYWORD páginas) ──
        if has_brave:
            for page in range(MAX_PAGES_PER_KEYWORD):
                if len(leads) >= max_results:
                    break
                offset = page * 20
                log.info(f"[brave] '{keyword}' p{page+1} (offset={offset})")

                items = _brave_search(base_query, offset=offset)
                if items is None:
                    break  # erro ou cota

                if not items:
                    break  # sem mais resultados

                new_in_page = 0
                for item in items:
                    lead = _parse_result(item, source="brave", keyword=keyword)
                    if not lead:
                        continue
                    key = _normalize_url(lead.linkedin_url)
                    if key in seen_urls:
                        continue
                    seen_urls.add(key)
                    leads.append(lead)
                    new_in_page += 1
                    if len(leads) >= max_results:
                        break

                if new_in_page == 0:
                    break
                _human_delay()

        # ── Google Custom Search (até 3 páginas de 10) ──
        if has_google:
            google_query = f"site:linkedin.com/in {keyword} {LOCATION_FILTER}"
            for page in range(3):
                if len(leads) >= max_results:
                    break
                start = page * 10 + 1
                log.info(f"[google] '{keyword}' p{page+1} (start={start})")

                items = _google_cse_search(google_query, start=start)
                if items is None:
                    break
                if not items:
                    break

                new_in_page = 0
                for item in items:
                    lead = _parse_result(item, source="google", keyword=keyword)
                    if not lead:
                        continue
                    key = _normalize_url(lead.linkedin_url)
                    if key in seen_urls:
                        continue
                    seen_urls.add(key)
                    leads.append(lead)
                    new_in_page += 1
                    if len(leads) >= max_results:
                        break

                if new_in_page == 0:
                    break
                _human_delay()

    log.info(f"[scraper] Keywords: {len(leads)} leads coletados")
    return leads


# ── Busca por artigos/posts LinkedIn ─────────────────────────────────────────────

def search_by_post_engagement(
    post_urls: Optional[list[str]] = None,
    max_results: int = 30,
) -> list[Lead]:
    """
    Encontra autores de artigos e posts sobre crypto no LinkedIn.
    Usa Brave Search para buscar conteúdo publicado (linkedin.com/pulse e /posts).

    Autores de conteúdo crypto = leads altamente engajados.
    """
    if not config.BRAVE_SEARCH_API_KEY:
        log.info("[posts] Brave API key não disponível — ignorado.")
        return []

    leads: list[Lead] = []
    seen_urls: set[str] = set()

    # Tópicos de conteúdo crypto em PT-BR
    # Foco: quem ESCREVE e COMPARTILHA sobre bitcoin = alto interesse pessoal
    content_queries = [
        # Artigos LinkedIn Pulse sobre autocustódia
        'site:linkedin.com/pulse "bitcoin" "autocustodia" Brasil',
        'site:linkedin.com/pulse "bitcoin" "hardware wallet" Brasil',
        'site:linkedin.com/pulse "bitcoin" "soberania financeira"',
        'site:linkedin.com/pulse "bitcoin" "investimento" Brasil',
        'site:linkedin.com/pulse "bitcoin" "longo prazo" Brasil',
        'site:linkedin.com/pulse "criptomoeda" "investir" Brasil',
        # Posts LinkedIn sobre bitcoin (quem posta = demonstra interesse)
        'site:linkedin.com/posts "bitcoin" "autocustodia"',
        'site:linkedin.com/posts "bitcoin" "hodl"',
        'site:linkedin.com/posts "comprei bitcoin"',
        'site:linkedin.com/posts "meu bitcoin"',
        'site:linkedin.com/posts "entusiasta" "bitcoin"',
        'site:linkedin.com/posts "bitcoin" "cold wallet"',
        'site:linkedin.com/posts "bitcoin" "São Paulo"',
        'site:linkedin.com/posts "bitcoin" "Rio de Janeiro"',
        # Compartilhamentos de conteúdo crypto
        'site:linkedin.com/posts "bitcoin" "soberania"',
        'site:linkedin.com/posts "cripto" "investimento pessoal"',
    ]
    random.shuffle(content_queries)

    for query in content_queries:
        if len(leads) >= max_results:
            break

        log.info(f"[posts] Buscando: {query[:60]}...")
        items = _brave_search(query)
        if not items:
            _human_delay()
            continue

        for item in items:
            url = item.get("url", "")

            # Artigos LinkedIn Pulse: extrair autor via padrão na URL ou título
            # Posts LinkedIn: URL contém o perfil do autor
            author_url = ""

            # linkedin.com/posts/username_activity-... → extrair username
            post_match = re.search(r"linkedin\.com/posts/([a-zA-Z0-9_-]+?)_", url)
            if post_match:
                username = post_match.group(1)
                author_url = f"https://www.linkedin.com/in/{username}"

            # linkedin.com/pulse/titulo-autor-nome → último segmento pode ter autor
            pulse_match = re.search(r"linkedin\.com/pulse/.+-([a-zA-Z0-9_-]+?)(?:\?|$)", url)
            if not author_url and pulse_match:
                username = pulse_match.group(1)
                # Filtrar slugs genéricos
                if len(username) > 3 and not username.startswith("20"):
                    author_url = f"https://www.linkedin.com/in/{username}"

            if not author_url:
                continue

            key = _normalize_url(author_url)
            if key in seen_urls:
                continue
            seen_urls.add(key)

            # Extrair dados do resultado
            title       = item.get("title", "")
            description = item.get("description", "")

            # Tentar extrair nome do autor do título do artigo
            name = ""
            # Padrão: "Título do Artigo | Nome do Autor | LinkedIn"
            parts = re.split(r"\s*[|]\s*", title)
            for p in parts:
                p = p.strip()
                if p.lower() == "linkedin" or len(p) < 3:
                    continue
                # Se parece um nome (2+ palavras, sem termos genéricos)
                words = p.split()
                if 2 <= len(words) <= 5 and not any(w.lower() in ("como", "por", "que", "the", "how", "and") for w in words[:1]):
                    name = p
                    break

            if not name:
                # Tentar extrair do username
                name = post_match.group(1).replace("-", " ").title() if post_match else ""

            if not name:
                continue

            # Localização do conteúdo
            location = ""
            for text in (description, title):
                kw_match = BR_PATTERN.search(text)
                if kw_match:
                    location = kw_match.group(0).strip()
                    break

            lead = Lead(
                name=name,
                linkedin_url=author_url,
                job_title="",  # será preenchido via enrichment
                company="",
                location=location,
                source="linkedin_content",
                status="pending",
            )

            # Filtrar por TITLE_EXCLUSIONS (mesmo sem job_title)
            leads.append(lead)
            if len(leads) >= max_results:
                break

        _human_delay()

    log.info(f"[posts] {len(leads)} autores de conteúdo encontrados")
    return leads


# ── Execução direta ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    import config as _cfg
    if not _cfg.BRAVE_SEARCH_API_KEY:
        print("ERRO: BRAVE_SEARCH_API_KEY não configurado em config.py")
        sys.exit(1)

    _cfg.SEARCH_KEYWORDS = _cfg.AUDIENCE_PROFILES["1"]["keywords"]

    from leads_manager import add_leads, print_summary

    print("Coletando leads via Brave Search...")
    leads = search_by_keywords()
    print(f"   → {len(leads)} perfis encontrados (keywords)")

    print("Buscando autores de conteúdo...")
    content_leads = search_by_post_engagement()
    print(f"   → {len(content_leads)} autores encontrados (posts/artigos)")

    all_leads = leads + content_leads
    added, dupes = add_leads(all_leads)
    print(f"\n{added} leads novos adicionados ({dupes} duplicatas ignoradas)")
    print_summary()
