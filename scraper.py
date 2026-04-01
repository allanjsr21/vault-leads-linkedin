"""
Módulo de coleta de leads via Brave Search API.

Usa site:linkedin.com/in + keywords para encontrar perfis brasileiros.
Gratuito: 2000 consultas/mês (plano Free, sem cartão de crédito).

Setup (uma vez só):
  1. https://api.search.brave.com → cria conta gratuita → plano Free
  2. Copia a API key
  3. Adiciona BRAVE_SEARCH_API_KEY no Streamlit Cloud secrets
"""

import logging
import re
import time
from typing import Optional

import requests

import config
from config import LOCATION_FILTER, MAX_LEADS_PER_RUN, MAX_PAGES_PER_KEYWORD
from models import Lead, _normalize_url

log = logging.getLogger(__name__)

BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"


# ── Parser de resultados Brave ────────────────────────────────────────────────

def _parse_brave_result(item: dict, source: str) -> Optional[Lead]:
    """
    Converte um item da Brave Web Search em Lead.

    Formato típico dos resultados do LinkedIn:
      title:       "João Silva - CEO at Empresa X | LinkedIn"
      url:         "https://www.linkedin.com/in/joaosilva"
      description: "São Paulo, Brazil. CEO at Empresa X. 500+ connections."
    """
    url = item.get("url", "")
    if "linkedin.com/in/" not in url:
        return None

    title       = item.get("title", "")
    description = item.get("description", "")

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
    # Descricoes do LinkedIn via Brave usam · como separador;
    # localizacao pode aparecer em qualquer segmento, ex: "500+ connections · Sao Paulo, SP · CEO"
    location = ""
    BR_PATTERN = re.compile(
        r"(?:Brazil|Brasil|"
        r"São Paulo|Rio de Janeiro|Belo Horizonte|Brasília|Curitiba|Fortaleza|"
        r"Manaus|Salvador|Recife|Porto Alegre|Belém|Goiânia|Florianópolis|"
        r",\s*(?:SP|RJ|MG|RS|PR|SC|BA|GO|DF|CE|PE|AM|MS|MT|PA|ES|PB|RN|AL|"
        r"SE|PI|MA|AP|RO|AC|RR|TO))",
        re.IGNORECASE,
    )
    for seg in re.split(r"[.\n·|]", description):
        seg = seg.strip()
        if not seg or len(seg) > 80:
            continue
        if BR_PATTERN.search(seg):
            location = seg
            break
    # sem fallback generico — melhor vazio do que texto de bio errado

    return Lead(
        name=name,
        linkedin_url=url,
        job_title=job_title,
        company=company,
        location=location,
        source=source,
        status="pending",
    )


# ── Busca por palavras-chave ───────────────────────────────────────────────────

def search_by_keywords(
    keywords: Optional[list[str]] = None,
    max_results: int = MAX_LEADS_PER_RUN,
) -> list[Lead]:
    """
    Busca perfis LinkedIn via Brave Search API.
    Retorna até max_results leads únicos.
    """
    api_key = config.BRAVE_SEARCH_API_KEY

    if not api_key:
        raise ValueError(
            "BRAVE_SEARCH_API_KEY não configurado.\n"
            "Adicione-o no Streamlit Cloud → Settings → Secrets."
        )

    keywords   = keywords or config.SEARCH_KEYWORDS
    exclusions = getattr(config, "SEARCH_EXCLUSIONS", "")
    leads: list[Lead] = []
    seen_urls: set[str] = set()
    quota_hit = False

    for keyword in keywords:
        if len(leads) >= max_results or quota_hit:
            break

        base_query = f"site:linkedin.com/in {keyword} {LOCATION_FILTER}"
        if exclusions:
            base_query += f" {exclusions}"

        for page in range(MAX_PAGES_PER_KEYWORD):
            if len(leads) >= max_results or quota_hit:
                break

            offset = page * 20
            log.info(f"[brave] '{keyword}' página {page + 1} (offset={offset})")

            try:
                resp = requests.get(
                    BRAVE_SEARCH_URL,
                    headers={
                        "Accept":               "application/json",
                        "Accept-Encoding":      "gzip",
                        "X-Subscription-Token": api_key,
                    },
                    params={
                        "q":      base_query,
                        "count":  20,
                        "offset": offset,
                    },
                    timeout=15,
                )

                if resp.status_code == 429:
                    log.warning("[brave] Cota mensal atingida. Encerrando busca.")
                    quota_hit = True
                    break

                if resp.status_code != 200:
                    log.warning(f"[brave] HTTP {resp.status_code} para '{keyword}' p{page+1}: {resp.text[:200]}")
                    break  # pula para proximo keyword

                data  = resp.json()
                items = data.get("web", {}).get("results", [])
                log.info(f"[brave] '{keyword}' p{page+1} → {len(items)} resultados")

                if not items:
                    break  # sem mais resultados nessa keyword

                new_in_page = 0
                for item in items:
                    lead = _parse_brave_result(item, source="keyword_search")
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
                    break  # pagina sem novidades, pula keyword

            except requests.RequestException as e:
                log.error(f"[brave] Erro de conexão para '{keyword}' p{page+1}: {e}")
                break

            time.sleep(1)  # rate limiting cortês

    log.info(f"[brave] Total: {len(leads)} leads coletados")
    return leads


# ── Engajamento em posts (não disponível sem scraper dedicado) ────────────────

def search_by_post_engagement(
    post_urls: Optional[list[str]] = None,
    max_results: int = MAX_LEADS_PER_RUN,
) -> list[Lead]:
    """
    Coleta via engajamento em posts não está disponível com Brave Search.
    Retorna lista vazia.
    """
    log.info("[post_engagement] Método não disponível com Brave Search — ignorado.")
    return []


# ── Execução direta ────────────────────────────────────────────────────────────

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
    print(f"   → {len(leads)} perfis encontrados")

    added, dupes = add_leads(leads)
    print(f"\n{added} leads novos adicionados ({dupes} duplicatas ignoradas)")
    print_summary()
