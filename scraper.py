"""
Módulo de coleta de leads via Google Custom Search API.

Usa site:linkedin.com/in + keywords para encontrar perfis brasileiros.
Gratuito: 100 consultas/dia (10 resultados por consulta).

Setup (uma vez só):
  1. https://programmablesearchengine.google.com → cria engine para linkedin.com/in/*
  2. https://console.cloud.google.com/apis → ativa Custom Search API + cria API Key
  3. Adiciona GOOGLE_CSE_API_KEY e GOOGLE_CSE_ID no Streamlit Cloud secrets
"""

import logging
import re
import time
from typing import Optional
from urllib.parse import quote_plus

import requests

import config
from config import LOCATION_FILTER, MAX_LEADS_PER_RUN
from models import Lead, _normalize_url

log = logging.getLogger(__name__)

GOOGLE_CSE_URL = "https://www.googleapis.com/customsearch/v1"


# ── Parser de resultados Google ───────────────────────────────────────────────

def _parse_google_result(item: dict, source: str) -> Optional[Lead]:
    """
    Converte um item da Google CSE em Lead.

    Formato típico dos resultados do LinkedIn:
      title:   "João Silva - CEO at Empresa X | LinkedIn"
      link:    "https://www.linkedin.com/in/joaosilva"
      snippet: "São Paulo, Brazil. CEO at Empresa X. 500+ connections."
    """
    url = item.get("link", "")
    if "linkedin.com/in/" not in url:
        return None

    title   = item.get("title", "")
    snippet = item.get("snippet", "")

    # ── Nome ──────────────────────────────────────────────────────────────────
    # "João Silva - CEO at Empresa X | LinkedIn"  →  "João Silva"
    name = re.split(r"\s*[-–|]\s*", title)[0].strip()
    if not name:
        return None

    # ── Cargo e empresa ───────────────────────────────────────────────────────
    # Partes intermediárias do title: "CEO at Empresa X"
    title_parts = re.split(r"\s*[-–|]\s*", title)
    job_title = ""
    company   = ""
    for part in title_parts[1:]:
        part = part.strip()
        if part.lower() in ("linkedin", ""):
            continue
        # "CEO at Empresa X" / "CEO na Empresa X" / "CEO em Empresa X"
        at_match = re.split(r"\s+(?:at|na|em|@)\s+", part, maxsplit=1, flags=re.IGNORECASE)
        if len(at_match) == 2:
            job_title = at_match[0].strip()
            company   = at_match[1].strip()
        elif not job_title:
            job_title = part
        break

    # ── Localização ───────────────────────────────────────────────────────────
    # Snippet começa com localização: "São Paulo, Brazil. CEO..."
    location = ""
    first_sentence = re.split(r"[.\n·]", snippet)[0].strip()
    # Considera localização se tiver vírgula e não for muito longo
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
    Busca perfis LinkedIn via Google Custom Search API.
    Retorna até max_results leads únicos.
    """
    api_key = config.GOOGLE_CSE_API_KEY
    cse_id  = config.GOOGLE_CSE_ID

    if not api_key or not cse_id:
        raise ValueError(
            "GOOGLE_CSE_API_KEY e GOOGLE_CSE_ID não configurados.\n"
            "Adicione-os no Streamlit Cloud → Settings → Secrets."
        )

    keywords  = keywords or config.SEARCH_KEYWORDS
    leads: list[Lead] = []
    seen_urls: set[str] = set()

    for keyword in keywords:
        if len(leads) >= max_results:
            break

        query = f"site:linkedin.com/in {keyword} {LOCATION_FILTER}"
        log.info(f"[google_cse] Buscando: '{keyword}'")

        try:
            resp = requests.get(
                GOOGLE_CSE_URL,
                params={
                    "key": api_key,
                    "cx":  cse_id,
                    "q":   query,
                    "num": 10,
                },
                timeout=15,
            )

            if resp.status_code == 429:
                log.warning("[google_cse] Cota diária atingida. Encerrando busca.")
                break

            if resp.status_code != 200:
                log.warning(f"[google_cse] HTTP {resp.status_code} para '{keyword}'")
                continue

            data = resp.json()

            # Verifica cota no corpo da resposta
            error = data.get("error", {})
            if error.get("code") == 429 or "rateLimitExceeded" in str(error):
                log.warning("[google_cse] Cota diária atingida. Encerrando busca.")
                break

            items = data.get("items", [])
            log.info(f"[google_cse] '{keyword}' → {len(items)} resultados")

            for item in items:
                lead = _parse_google_result(item, source="keyword_search")
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
            log.error(f"[google_cse] Erro de conexão para '{keyword}': {e}")

        time.sleep(1)  # rate limiting cortês

    log.info(f"[google_cse] Total: {len(leads)} leads coletados")
    return leads


# ── Engajamento em posts (não disponível sem Apify) ───────────────────────────

def search_by_post_engagement(
    post_urls: Optional[list[str]] = None,
    max_results: int = MAX_LEADS_PER_RUN,
) -> list[Lead]:
    """
    Coleta via engajamento em posts não está disponível com Google CSE.
    Retorna lista vazia.
    """
    log.info("[post_engagement] Método não disponível com Google CSE — ignorado.")
    return []


# ── Execução direta ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    import config as _cfg
    if not _cfg.GOOGLE_CSE_API_KEY:
        print("ERRO: GOOGLE_CSE_API_KEY não configurado em config.py")
        sys.exit(1)

    # Testa com o primeiro perfil
    _cfg.SEARCH_KEYWORDS = _cfg.AUDIENCE_PROFILES["1"]["keywords"]

    from leads_manager import add_leads, print_summary

    print("Coletando leads via Google CSE...")
    leads = search_by_keywords()
    print(f"   → {len(leads)} perfis encontrados")

    added, dupes = add_leads(leads)
    print(f"\n{added} leads novos adicionados ({dupes} duplicatas ignoradas)")
    print_summary()
