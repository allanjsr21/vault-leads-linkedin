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
from config import LOCATION_FILTER, MAX_LEADS_PER_RUN
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
    location = ""
    first_sentence = re.split(r"[.\n·]", description)[0].strip()
    if first_sentence and "," in first_sentence and len(first_sentence) < 60:
        location = first_sentence

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

    keywords  = keywords or config.SEARCH_KEYWORDS
    leads: list[Lead] = []
    seen_urls: set[str] = set()

    for keyword in keywords:
        if len(leads) >= max_results:
            break

        query = f"site:linkedin.com/in {keyword} {LOCATION_FILTER}"
        log.info(f"[brave] Buscando: '{keyword}'")

        try:
            resp = requests.get(
                BRAVE_SEARCH_URL,
                headers={
                    "Accept":               "application/json",
                    "Accept-Encoding":      "gzip",
                    "X-Subscription-Token": api_key,
                },
                params={
                    "q":     query,
                    "count": 20,
                },
                timeout=15,
            )

            if resp.status_code == 429:
                log.warning("[brave] Cota mensal atingida. Encerrando busca.")
                break

            if resp.status_code != 200:
                log.warning(f"[brave] HTTP {resp.status_code} para '{keyword}': {resp.text[:200]}")
                continue

            data  = resp.json()
            items = data.get("web", {}).get("results", [])
            log.info(f"[brave] '{keyword}' → {len(items)} resultados")

            for item in items:
                lead = _parse_brave_result(item, source="keyword_search")
                if not lead:
                    continue
                key = _normalize_url(lead.linkedin_url)
                if key in seen_urls:
                    continue
                seen_urls.add(key)
                leads.append(lead)
                if len(leads) >= max_results:
                    break

        except requests.RequestException as e:
            log.error(f"[brave] Erro de conexão para '{keyword}': {e}")

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
