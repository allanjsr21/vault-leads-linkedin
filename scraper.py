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
import unicodedata
from typing import Optional

import requests

import config
from config import MAX_LEADS_PER_RUN, MAX_PAGES_PER_KEYWORD, TITLE_EXCLUSIONS
from models import Lead, _normalize_url

log = logging.getLogger(__name__)

BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"
GOOGLE_CSE_URL   = "https://www.googleapis.com/customsearch/v1"
BING_SEARCH_URL  = "https://api.bing.microsoft.com/v7.0/search"
SERPER_SEARCH_URL = "https://google.serper.dev/search"

def _strip_accents(s: str) -> str:
    """Remove acentos para comparação case-insensitive sem acento."""
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )

# ── Filtro de regiões permitidas (Sudeste + Centro-Oeste + Sul) ──────────────
# Armazenadas SEM acento para comparação robusta com texto que pode vir sem acento
_ALLOWED_REGIONS = [
    # País (qualquer localização no Brasil é válida inicialmente)
    "brazil", "brasil",
    # Sudeste
    "sao paulo", "rio de janeiro", "belo horizonte", "minas gerais",
    "espirito santo", "vitoria", "campinas", "santos", "ribeirao preto",
    "sorocaba", "guarulhos", "niteroi", "juiz de fora", "uberlandia",
    # Sul
    "curitiba", "porto alegre", "florianopolis", "joinville", "londrina",
    "maringa", "blumenau", "caxias do sul", "parana", "santa catarina",
    "rio grande do sul",
    # Centro-Oeste
    "brasilia", "goiania", "campo grande", "cuiaba", "goias",
    "mato grosso", "mato grosso do sul", "distrito federal",
    # NOTA: siglas de estado removidas — causam falsos positivos
    # (ex: "Praia" contém "pr", "Score" contém "sc").
]

# Estados do Nordeste/Norte — se aparecerem, rejeita
_BLOCKED_REGIONS = [
    "salvador", "recife", "fortaleza", "belém", "manaus", "natal",
    "joão pessoa", "maceió", "teresina", "são luís", "aracaju",
    "porto velho", "macapá", "boa vista", "rio branco", "palmas",
    "bahia", "pernambuco", "ceara", "amazonas",
    "maranhao", "piaui", "paraiba", "alagoas", "sergipe",
    "rio grande do norte", "tocantins", "rondônia", "roraima",
    "amapá", "acre",
]

def _location_allowed(location: str, full_text: str = "") -> bool:
    """Retorna True se a localização do lead está nas regiões permitidas."""
    if not location:
        # Sem localização detectada → checar se há sinal FORTE de Brasil no texto
        # (cidade específica, não "Brazil/Brasil" genérico que vem da query de busca)
        if full_text:
            ft_lower = _strip_accents(full_text.lower())

            # PRIMEIRO: rejeitar se houver sinal de país estrangeiro no texto
            # (ex: "Montreal, Canada", "New York", "London", etc.)
            foreign_signals = [
                "canada", "montreal", "toronto", "vancouver", "ottawa",
                "united states", "united kingdom", "australia", "new zealand",
                "new york", "london", "paris", "madrid", "berlin", "amsterdam",
                "lisbon", "porto, portugal", "mexico", "argentina", "colombia",
                "chile", "peru", "spain", "france", "germany", "italy",
                "netherlands", "switzerland", "austria", "sweden", "norway",
                "denmark", "finland", "poland", "czech", "romania",
                "india", "china", "japan", "singapore", "hong kong",
                "dubai", "uae", "south africa", "nigeria", "kenya",
                ", ca", ", us", ", uk", ", au", ", nz",
            ]
            for foreign in foreign_signals:
                if foreign in ft_lower:
                    return False  # Sinal estrangeiro encontrado → rejeita

            # Sinais fortes de localização pessoal brasileira
            # REMOVIDAS cidades soltas (ex: "São Paulo") pois aparecem em nomes
            # de conferências (ex: "Scaling Bitcoin Conference São Paulo").
            # Exige formato LinkedIn de localização: "Cidade, SP" ou estado por extenso.
            unambiguous_signals = [
                # Formato LinkedIn: "Cidade, UF" — muito específico, raramente em eventos
                ", sp", ", rj", ", mg", ", pr", ", sc", ", rs", ", df",
                ", es", ", ms", ", mt", ", go", ", ro", ", am", ", pa",
                # Estados por extenso — aparecem raramente em nomes de conferências
                "minas gerais", "santa catarina", "rio grande do sul",
                "espírito santo", "distrito federal", "mato grosso",
                # Formatos "cidade, estado" explícitos — inequívocos
                "sao paulo, sp", "rio de janeiro, rj", "belo horizonte, mg",
                "porto alegre, rs", "florianopolis, sc", "curitiba, pr",
                "brasilia, df", "goiania, go", "campo grande, ms",
                "ribeirao preto, sp", "campinas, sp", "santos, sp",
            ]
            for signal in unambiguous_signals:
                if signal in ft_lower:
                    return True
            # Nenhum sinal forte de Brasil → rejeita
            log.debug(f"[scraper] Sem localização e sem sinal forte de Brasil (rejeitado)")
            return False
        # Sem localização e sem texto → rejeita (melhor perder do que aceitar lixo)
        return False
    # Normaliza: minúsculo + sem acentos (LinkedIn às vezes retorna sem acento)
    loc_norm = _strip_accents(location.lower())
    # Se menciona região bloqueada → rejeita
    for blocked in _BLOCKED_REGIONS:
        if _strip_accents(blocked) in loc_norm:
            return False
    # Se tem localização e menciona região permitida → aceita
    for allowed in _ALLOWED_REGIONS:
        if allowed in loc_norm:  # _ALLOWED_REGIONS já sem acentos
            return True
    # Localização presente mas NÃO reconhecida → REJEITA (outro país, outra região)
    log.debug(f"[scraper] Localização não reconhecida (rejeitado): {location}")
    return False


# ── Filtro de idioma (português vs inglês) ────────────────────────────────────

# Palavras muito comuns em português que raramente aparecem em inglês
_PT_WORDS = {
    " de ", " da ", " do ", " das ", " dos ", " na ", " no ", " nas ", " nos ",
    " em ", " para ", " com ", " que ", " uma ", " um ", " pelo ", " pela ",
    " entre ", " sobre ", " mais ", " sua ", " seu ", " aos ", " são ",
    " está ", " como ", " mas ", " tem ", " por ", " foi ",
    " especialista ", " experiência ", " gestão ", " negócios ",
    " empresa ", " desenvolvimento ", " financeiro ", " investimento ",
}

# Palavras comuns em inglês que raramente aparecem em português
_EN_WORDS = {
    " the ", " and ", " with ", " for ", " that ", " this ", " from ",
    " have ", " been ", " will ", " are ", " was ", " were ", " has ",
    " can ", " our ", " their ", " about ", " which ", " into ",
    " also ", " than ", " been ", " would ", " should ", " could ",
    " experience ", " management ", " development ", " business ",
    " passionate ", " building ", " helping ", " looking ", " working ",
    " skilled ", " driven ", " focused ", " leading ", " based ",
}


def _text_is_portuguese(text: str) -> bool:
    """Retorna True se o texto parece ser português (não inglês)."""
    if not text or len(text) < 30:
        return True  # texto muito curto → não dá pra saber, aceita
    t = f" {text.lower()} "
    pt_count = sum(1 for w in _PT_WORDS if w in t)
    en_count = sum(1 for w in _EN_WORDS if w in t)
    # Se tem mais palavras em inglês do que português → provavelmente inglês
    if en_count >= 3 and en_count > pt_count:
        return False
    return True


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
    # Rejeitar "nomes" que são claramente títulos de artigo/post (não pessoas)
    name_words = name.split()
    if len(name_words) > 6:  # nomes reais raramente têm mais de 6 palavras
        return None
    # Se tem caracteres estranhos para nomes (!, ?, :, números no início)
    if re.search(r"[!?:]|^\d", name):
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
    # Extrair APENAS da description (não do título, que tem nome/cargo)
    location = ""
    for seg in re.split(r"[.\n·|]", description):
        seg = seg.strip()
        if not seg or len(seg) > 60:
            continue
        if seg.lower() in ("linkedin", ""):
            continue
        # Checar se parece localização (padrão: "Cidade, Estado" ou "Cidade, Country")
        # e contém referência brasileira
        if BR_PATTERN.search(seg) and ("," in seg or len(seg.split()) <= 4):
            location = seg
            break

    # ── Filtro de cargos inalcançáveis ────────────────────────────────────────
    if job_title and TITLE_EXCLUSIONS:
        jt_lower = job_title.lower()
        for excl in TITLE_EXCLUSIONS:
            if excl.lower() in jt_lower:
                log.debug(f"[scraper] Descartado (cargo inalcançável): {name} - {job_title}")
                return None

    # NOTA: NÃO usar keyword como fallback de localização.
    # A keyword contém cidades brasileiras, mas isso não significa
    # que o lead é dessa cidade. Isso gerava falsos positivos.

    # ── Filtro de região (Sudeste + Centro-Oeste + Sul apenas) ───────────────
    # Usar APENAS description para sinais de Brasil (title tem nome/cargo = falsos positivos)
    if not _location_allowed(location, description):
        log.debug(f"[scraper] Descartado (região fora do escopo): {name} - {location}")
        return None

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
            params={
                "key": api_key, "cx": cse_id, "q": query,
                "num": 10, "start": start,
                "filter": "0",  # desativa dedup do Google → mais resultados únicos
            },
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


# ── Bing Web Search API ──────────────────────────────────────────────────────────

def _bing_search(query: str, offset: int = 0) -> Optional[list[dict]]:
    """Executa busca no Bing Web Search API. Retorna lista de resultados ou None.
    Free tier: 1.000 queries/mês — https://aka.ms/bingapifreetier
    """
    api_key = getattr(config, "BING_SEARCH_API_KEY", "")
    if not api_key:
        return None

    try:
        resp = requests.get(
            BING_SEARCH_URL,
            headers={"Ocp-Apim-Subscription-Key": api_key},
            params={"q": query, "count": 50, "offset": offset, "mkt": "pt-BR"},
            timeout=15,
        )
        if resp.status_code == 401:
            log.warning("[bing] API key inválida.")
            return None
        if resp.status_code == 429:
            log.warning("[bing] Cota atingida.")
            return None
        if resp.status_code != 200:
            log.warning(f"[bing] HTTP {resp.status_code}: {resp.text[:200]}")
            return None

        web_pages = resp.json().get("webPages", {}).get("value", [])
        # Normaliza para o mesmo formato do Brave/Google
        results = []
        for item in web_pages:
            results.append({
                "url":         item.get("url", ""),
                "title":       item.get("name", ""),
                "description": item.get("snippet", ""),
            })
        return results
    except requests.RequestException as e:
        log.error(f"[bing] Erro de conexão: {e}")
        return None


# ── Serper.dev — Google Search API ───────────────────────────────────────────────

def _serper_search(query: str, page: int = 1) -> Optional[list[dict]]:
    """Executa busca via Serper.dev (Google Search API). 2.500 queries grátis.
    Docs: https://serper.dev/
    """
    api_key = getattr(config, "SERPER_API_KEY", "")
    if not api_key:
        return None

    try:
        resp = requests.post(
            SERPER_SEARCH_URL,
            headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
            json={"q": query, "num": 10, "page": page, "gl": "br", "hl": "pt"},
            timeout=15,
        )
        if resp.status_code == 401:
            log.warning("[serper] API key inválida.")
            return None
        if resp.status_code == 429:
            log.warning("[serper] Cota atingida.")
            return None
        if resp.status_code != 200:
            log.warning(f"[serper] HTTP {resp.status_code}: {resp.text[:200]}")
            return None

        organic = resp.json().get("organic", [])
        results = []
        for item in organic:
            results.append({
                "url":         item.get("link", ""),
                "title":       item.get("title", ""),
                "description": item.get("snippet", ""),
            })
        return results
    except requests.RequestException as e:
        log.error(f"[serper] Erro de conexão: {e}")
        return None


# ── Delay humanizado ─────────────────────────────────────────────────────────────

def _human_delay():
    """Delay aleatório entre requests para simular comportamento humano."""
    time.sleep(random.uniform(0.3, 0.8))


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

    # ── Cap de keywords por run (evita rodar centenas de queries) ─────────
    max_kw = getattr(config, "MAX_KEYWORDS_PER_RUN", 40)
    if len(keywords) > max_kw:
        keywords = keywords[:max_kw]
        log.info(f"[scraper] Keywords limitadas a {max_kw} por MAX_KEYWORDS_PER_RUN")

    has_brave  = bool(config.BRAVE_SEARCH_API_KEY)
    has_google = bool(getattr(config, "GOOGLE_CSE_API_KEY", "")) and bool(getattr(config, "GOOGLE_CSE_ID", ""))
    has_bing   = bool(getattr(config, "BING_SEARCH_API_KEY", ""))
    has_serper = bool(getattr(config, "SERPER_API_KEY", ""))

    if not has_brave and not has_google and not has_bing and not has_serper:
        raise ValueError(
            "Nenhuma API de busca configurada.\n"
            "Configure BRAVE_SEARCH_API_KEY e/ou GOOGLE_CSE_API_KEY + GOOGLE_CSE_ID "
            "e/ou BING_SEARCH_API_KEY e/ou SERPER_API_KEY."
        )

    sources_label = []
    if has_brave:  sources_label.append("Brave")
    if has_google: sources_label.append("Google CSE")
    if has_serper: sources_label.append("Serper")
    if has_bing:   sources_label.append("Bing")
    log.info(f"[scraper] Fontes ativas: {' + '.join(sources_label)}")
    log.info(f"[scraper] {len(keywords)} keywords configuradas")

    for keyword in keywords:
        if len(leads) >= max_results:
            break

        base_query = f"site:linkedin.com/in {keyword} {config.LOCATION_FILTER}"
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

        # ── Google Custom Search (até MAX_PAGES_PER_KEYWORD páginas) ──
        if has_google:
            google_query = f"site:linkedin.com/in {keyword} {config.LOCATION_FILTER}"
            for page in range(MAX_PAGES_PER_KEYWORD):
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

        # ── Serper.dev — Google Search (até MAX_PAGES_PER_KEYWORD páginas) ──
        if has_serper:
            serper_query = f"site:linkedin.com/in {keyword} {config.LOCATION_FILTER}"
            if exclusions:
                serper_query += f" {exclusions}"
            for page in range(1, MAX_PAGES_PER_KEYWORD + 1):
                if len(leads) >= max_results:
                    break
                log.info(f"[serper] '{keyword}' p{page}")

                items = _serper_search(serper_query, page=page)
                if items is None:
                    break
                if not items:
                    break

                new_in_page = 0
                for item in items:
                    lead = _parse_result(item, source="serper", keyword=keyword)
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

        # ── Bing Web Search (até MAX_PAGES_PER_KEYWORD páginas) ──
        if has_bing:
            bing_query = f"site:linkedin.com/in {keyword} {config.LOCATION_FILTER}"
            if exclusions:
                bing_query += f" {exclusions}"
            for page in range(MAX_PAGES_PER_KEYWORD):
                if len(leads) >= max_results:
                    break
                offset = page * 50
                log.info(f"[bing] '{keyword}' p{page+1} (offset={offset})")

                items = _bing_search(bing_query, offset=offset)
                if items is None:
                    break
                if not items:
                    break

                new_in_page = 0
                for item in items:
                    lead = _parse_result(item, source="bing", keyword=keyword)
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
    max_results: int = 50,
) -> list[Lead]:
    """
    Encontra autores de artigos e posts sobre crypto no LinkedIn.
    Usa Brave Search + Serper para buscar conteúdo publicado (linkedin.com/pulse e /posts).

    Autores de conteúdo crypto = leads altamente engajados.
    """
    has_brave  = bool(config.BRAVE_SEARCH_API_KEY)
    has_serper = bool(getattr(config, "SERPER_API_KEY", ""))
    if not has_brave and not has_serper:
        log.info("[posts] Nenhuma API de busca disponível — ignorado.")
        return []

    leads: list[Lead] = []
    seen_urls: set[str] = set()

    # Tópicos de conteúdo crypto em PT-BR
    # Foco: quem ESCREVE e COMPARTILHA sobre bitcoin = alto interesse pessoal
    content_queries = [
        # ── Artigos LinkedIn Pulse (alta intenção — escreveu sobre o tema) ──
        'site:linkedin.com/pulse "bitcoin" "autocustodia" Brasil',
        'site:linkedin.com/pulse "bitcoin" "hardware wallet" Brasil',
        'site:linkedin.com/pulse "bitcoin" "soberania financeira"',
        'site:linkedin.com/pulse "bitcoin" "investimento" Brasil',
        'site:linkedin.com/pulse "bitcoin" "longo prazo" Brasil',
        'site:linkedin.com/pulse "criptomoeda" "investir" Brasil',
        'site:linkedin.com/pulse "bitcoin" "hodl" Brasil',
        'site:linkedin.com/pulse "bitcoin" "cold wallet"',
        'site:linkedin.com/pulse "bitcoin" "ledger" Brasil',
        'site:linkedin.com/pulse "bitcoin" "trezor" Brasil',
        'site:linkedin.com/pulse "bitcoin" "not your keys"',
        'site:linkedin.com/pulse "stack sats" Brasil',
        'site:linkedin.com/pulse "DCA bitcoin" Brasil',
        'site:linkedin.com/pulse "bitcoin" "reserva de valor" Brasil',
        'site:linkedin.com/pulse "bitcoin" "aposentadoria" Brasil',
        # ── Profissão + bitcoin (artigos de médicos/advogados/engenheiros) ──
        'site:linkedin.com/pulse "médico" "bitcoin"',
        'site:linkedin.com/pulse "advogado" "bitcoin"',
        'site:linkedin.com/pulse "engenheiro" "bitcoin"',
        'site:linkedin.com/pulse "dentista" "bitcoin"',
        'site:linkedin.com/pulse "empresário" "bitcoin"',
        'site:linkedin.com/pulse "CEO" "bitcoin" Brasil',
        'site:linkedin.com/pulse "diretor" "bitcoin" Brasil',
        # ── Posts LinkedIn (engajamento recente) ──
        'site:linkedin.com/posts "bitcoin" "autocustodia"',
        'site:linkedin.com/posts "bitcoin" "hodl"',
        'site:linkedin.com/posts "comprei bitcoin"',
        'site:linkedin.com/posts "meu bitcoin"',
        'site:linkedin.com/posts "entusiasta" "bitcoin"',
        'site:linkedin.com/posts "bitcoin" "cold wallet"',
        'site:linkedin.com/posts "bitcoin" "São Paulo"',
        'site:linkedin.com/posts "bitcoin" "Rio de Janeiro"',
        'site:linkedin.com/posts "bitcoin" "soberania"',
        'site:linkedin.com/posts "cripto" "investimento pessoal"',
        'site:linkedin.com/posts "stack sats"',
        'site:linkedin.com/posts "laser eyes" bitcoin',
        'site:linkedin.com/posts "bitcoin maximalist" Brasil',
        'site:linkedin.com/posts "hodler" "bitcoin" Brasil',
        'site:linkedin.com/posts "bitcoin" "Curitiba"',
        'site:linkedin.com/posts "bitcoin" "Belo Horizonte"',
        'site:linkedin.com/posts "bitcoin" "Florianópolis"',
        'site:linkedin.com/posts "bitcoin" "Porto Alegre"',
        'site:linkedin.com/posts "bitcoin" "Brasília"',
        # ── Perfis que mencionam bitcoin na headline (sinal direto) ──
        'site:linkedin.com/in "₿" "São Paulo" médico OR advogado OR engenheiro OR empresário',
        'site:linkedin.com/in "bitcoin" "hodler" Brasil',
        'site:linkedin.com/in "bitcoin maximalist" Brasil',
        'site:linkedin.com/in "autocustódia" bitcoin Brasil',
        'site:linkedin.com/in "stack sats" Brasil',
        'site:linkedin.com/in "not your keys" Brasil',
        'site:linkedin.com/in "cold wallet" bitcoin Brasil',
    ]
    random.shuffle(content_queries)
    content_queries = content_queries[:20]  # cap para acelerar run

    for query in content_queries:
        if len(leads) >= max_results:
            break

        log.info(f"[posts] Buscando: {query[:60]}...")

        # Tentar Brave primeiro, depois Serper como fallback
        items = _brave_search(query) if has_brave else None
        if not items and has_serper:
            items = _serper_search(query)
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

            # Filtrar por localização (usar description apenas, não título)
            if not _location_allowed(location, description):
                log.debug(f"[posts] Descartado (região): {name} - {location}")
                continue

            leads.append(lead)
            if len(leads) >= max_results:
                break

        _human_delay()

    log.info(f"[posts] {len(leads)} autores de conteúdo encontrados")
    return leads


# ── Busca por participantes de eventos crypto ────────────────────────────────────

def search_by_events(max_results: int = 30) -> list[Lead]:
    """
    Encontra participantes/organizadores de eventos crypto no LinkedIn.
    Eventos = leads ultra qualificados (demonstraram interesse ativo ao ponto de
    participar de um evento presencial ou online sobre bitcoin/cripto).

    Estratégia: busca no Brave por eventos LinkedIn de crypto no Brasil,
    depois extrai perfis dos organizadores/participantes mencionados.
    """
    if not config.BRAVE_SEARCH_API_KEY:
        log.info("[events] Brave API key não disponível — ignorado.")
        return []

    leads: list[Lead] = []
    seen_urls: set[str] = set()

    # Buscar eventos crypto no LinkedIn e perfis associados
    event_queries = [
        # Eventos LinkedIn
        'site:linkedin.com/events "bitcoin" "São Paulo"',
        'site:linkedin.com/events "bitcoin" "Rio de Janeiro"',
        'site:linkedin.com/events "bitcoin" Brasil',
        'site:linkedin.com/events "cripto" Brasil',
        'site:linkedin.com/events "blockchain" Brasil',
        'site:linkedin.com/events "web3" Brasil',
        # Organizadores de eventos crypto (perfis que mencionam eventos)
        'site:linkedin.com/in "organizador" "bitcoin" "evento" Brasil',
        'site:linkedin.com/in "palestrante" "bitcoin" Brasil',
        'site:linkedin.com/in "speaker" "bitcoin" Brazil',
        'site:linkedin.com/in "meetup bitcoin" Brasil',
        'site:linkedin.com/in "comunidade bitcoin" Brasil',
        'site:linkedin.com/in "embaixador bitcoin" Brasil',
        # Grupos/comunidades LinkedIn
        'site:linkedin.com/in "bitcoin conference" Brasil',
        'site:linkedin.com/in "bitconf" OR "blockchain rio" OR "bitsampa"',
        'site:linkedin.com/in "lider comunidade" "bitcoin" Brasil',
        # Meetup mentions in LinkedIn profiles
        'site:linkedin.com/in "meetup" "bitcoin" "São Paulo"',
        'site:linkedin.com/in "meetup" "bitcoin" "Rio de Janeiro"',
        'site:linkedin.com/in "meetup" "cripto" Brasil',
    ]
    random.shuffle(event_queries)
    event_queries = event_queries[:10]  # cap para acelerar run

    for query in event_queries:
        if len(leads) >= max_results:
            break

        log.info(f"[events] Buscando: {query[:60]}...")
        items = _brave_search(query)
        if not items:
            _human_delay()
            continue

        for item in items:
            url = item.get("url", "")

            # Extrair perfil de eventos LinkedIn
            if "/events/" in url:
                # Eventos não são perfis — buscar organizador na description
                desc = item.get("description", "")
                title = item.get("title", "")
                # Procurar menção de organizador com link linkedin.com/in
                profile_match = re.search(r"linkedin\.com/in/([a-zA-Z0-9_-]+)", desc)
                if profile_match:
                    url = f"https://www.linkedin.com/in/{profile_match.group(1)}"
                else:
                    continue

            # Perfil direto
            if "linkedin.com/in/" not in url:
                continue

            lead = _parse_result(item, source="linkedin_event", keyword="evento bitcoin")
            if not lead:
                continue

            # Sobrescrever URL se veio de evento
            if "linkedin.com/in/" in url:
                lead.linkedin_url = url

            key = _normalize_url(lead.linkedin_url)
            if key in seen_urls:
                continue
            seen_urls.add(key)
            leads.append(lead)

            if len(leads) >= max_results:
                break

        _human_delay()

    log.info(f"[events] {len(leads)} participantes/organizadores encontrados")
    return leads


# ── LinkedIn Direto (Voyager API) ────────────────────────────────────────────────

def search_linkedin_voyager(max_results: int = 100, callback=None) -> list[Lead]:
    """
    Busca perfis diretamente no LinkedIn via Voyager API interna.
    Requer LINKEDIN_LI_AT e LINKEDIN_JSESSIONID configurados.
    Retorna lista de Lead prontos para salvar.
    """
    from linkedin_voyager import search_linkedin_direct
    from models import _normalize_url

    raw = search_linkedin_direct(max_results=max_results, callback=callback)

    leads: list[Lead] = []
    seen_urls: set[str] = set()

    for r in raw:
        url = r.get("url", "")
        if not url:
            continue
        key = _normalize_url(url)
        if key in seen_urls:
            continue
        seen_urls.add(key)

        name     = r.get("name", "").strip()
        headline = r.get("headline", "").strip()
        location = r.get("location", "").strip()

        # Separar cargo e empresa do headline (formato "Cargo na Empresa")
        job_title = headline
        company   = ""
        for sep in (" na ", " at ", " em ", " @ ", " - "):
            if sep in headline:
                parts     = headline.split(sep, 1)
                job_title = parts[0].strip()
                company   = parts[1].strip()
                break

        leads.append(Lead(
            name         = name,
            linkedin_url = url,
            job_title    = job_title,
            company      = company,
            location     = location,
            bio          = headline,
            source       = "voyager",
            status       = "pending",
        ))

    log.info(f"[scraper] Voyager: {len(leads)} leads convertidos para Lead")
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
