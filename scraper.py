"""
Módulo de coleta de leads via Apify.

Dois métodos de descoberta:
  1. keyword_search  — busca perfis por palavras-chave (cripto, bitcoin, etc.)
  2. post_engagement — extrai quem curtiu/comentou em posts de cripto BR
"""

import logging
import os
from typing import Optional

from apify_client import ApifyClient

import config
from config import (
    APIFY_API_TOKEN,
    LOCATION_FILTER,
    MAX_LEADS_PER_RUN,
)
from models import Lead

log = logging.getLogger(__name__)


def _get_client() -> ApifyClient:
    token = APIFY_API_TOKEN or os.environ.get("APIFY_API_TOKEN", "")
    if not token:
        raise ValueError(
            "APIFY_API_TOKEN não configurado. Preencha em config.py ou defina "
            "a variável de ambiente APIFY_API_TOKEN."
        )
    return ApifyClient(token)


# ── Método 1: busca por palavras-chave ────────────────────────────────────────

def search_by_keywords(
    keywords: Optional[list[str]] = None,
    max_results: int = MAX_LEADS_PER_RUN,
) -> list[Lead]:
    """
    Usa harvestapi/linkedin-profile-search para buscar perfis que mencionam
    termos de cripto/investimento. Filtra por Brasil.
    """
    client = _get_client()
    keywords = keywords or config.SEARCH_KEYWORDS
    leads: list[Lead] = []

    for keyword in keywords:
        remaining = max_results - len(leads)
        if remaining <= 0:
            break

        log.info(f"[keyword_search] Buscando: '{keyword}'")
        try:
            run_input = {
                "searchQuery": keyword,
                "locations": [LOCATION_FILTER],
                "maxItems": min(remaining, 25),
                "profileScraperMode": "Short",
            }
            run = client.actor("harvestapi/linkedin-profile-search").call(
                run_input=run_input
            )
            dataset_id = run.get("defaultDatasetId")
            if not dataset_id:
                log.warning(f"[keyword_search] Nenhum dataset retornado para '{keyword}'")
                continue

            items = list(
                client.dataset(dataset_id).iterate_items()
            )
            log.info(f"[keyword_search] '{keyword}' → {len(items)} perfis")

            for item in items:
                lead = _parse_profile_item(item, source="keyword_search")
                if lead:
                    leads.append(lead)

        except Exception as e:
            log.error(f"[keyword_search] Erro em '{keyword}': {e}")

    return leads[:max_results]


def _parse_profile_item(item: dict, source: str) -> Optional[Lead]:
    """Converte item do Apify em Lead."""
    url = (
        item.get("linkedinUrl")
        or item.get("profileUrl")
        or item.get("url")
        or ""
    )
    name = (
        item.get("name")
        or item.get("fullName")
        or f"{item.get('firstName', '')} {item.get('lastName', '')}".strip()
    )
    if not url or not name:
        return None

    # location pode vir como dict {"linkedinText": "São Paulo, Brazil"}
    raw_location = (
        item.get("location")
        or item.get("geoRegion")
        or ""
    )
    if isinstance(raw_location, dict):
        location = raw_location.get("linkedinText") or raw_location.get("text") or ""
    else:
        location = str(raw_location)

    # job_title e company vêm dentro de currentPositions[0]
    positions = item.get("currentPositions") or []
    current = positions[0] if positions else {}
    job_title = (
        current.get("title")
        or item.get("headline")
        or item.get("title")
        or ""
    )
    company = (
        current.get("companyName")
        or item.get("companyName")
        or item.get("company")
        or ""
    )

    return Lead(
        name=name,
        linkedin_url=url,
        job_title=job_title,
        company=company,
        location=location,
        source=source,
        status="pending",
    )


# ── Método 2: engajamento em posts ────────────────────────────────────────────

def search_by_post_engagement(
    post_urls: Optional[list[str]] = None,
    max_results: int = MAX_LEADS_PER_RUN,
) -> list[Lead]:
    """
    Usa data-slayer/linkedin-post-analytics-scraper para obter quem
    reagiu/comentou em posts virais de cripto BR.
    """
    client = _get_client()
    post_urls = post_urls or config.CRYPTO_POST_URLS
    leads: list[Lead] = []

    if not post_urls:
        log.warning(
            "[post_engagement] Nenhuma URL de post configurada em CRYPTO_POST_URLS. "
            "Adicione URLs de posts populares de cripto em config.py."
        )
        return []

    for post_url in post_urls:
        remaining = max_results - len(leads)
        if remaining <= 0:
            break

        log.info(f"[post_engagement] Analisando post: {post_url}")
        try:
            run_input = {
                "postUrls": [post_url],
                "includeReactions": True,
                "includeComments": True,
            }
            run = client.actor("data-slayer/linkedin-post-analytics-scraper").call(
                run_input=run_input
            )
            dataset_id = run.get("defaultDatasetId")
            if not dataset_id:
                continue

            items = list(client.dataset(dataset_id).iterate_items())
            log.info(f"[post_engagement] {len(items)} itens de engajamento")

            for item in items:
                # reações e comentários vêm em sub-listas
                for reactor in item.get("reactions", []):
                    lead = _parse_engagement_item(reactor)
                    if lead:
                        leads.append(lead)
                for commenter in item.get("comments", []):
                    lead = _parse_engagement_item(commenter)
                    if lead:
                        leads.append(lead)

        except Exception as e:
            log.error(f"[post_engagement] Erro em '{post_url}': {e}")

    return leads[:max_results]


def _parse_engagement_item(item: dict) -> Optional[Lead]:
    """Converte item de engajamento em Lead."""
    url = item.get("profileUrl") or item.get("linkedinUrl") or ""
    name = (
        item.get("name")
        or f"{item.get('firstName', '')} {item.get('lastName', '')}".strip()
    )
    if not url or not name:
        return None

    return Lead(
        name=name,
        linkedin_url=url,
        job_title=item.get("headline") or item.get("title") or "",
        company=item.get("companyName") or "",
        location=item.get("location") or "",
        source="post_engagement",
        status="pending",
    )


# ── Execução direta ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    from leads_manager import add_leads, print_summary

    print("🔍 Coletando leads via keyword search...")
    keyword_leads = search_by_keywords()
    print(f"   → {len(keyword_leads)} perfis encontrados")

    print("🔍 Coletando leads via engajamento em posts...")
    engagement_leads = search_by_post_engagement()
    print(f"   → {len(engagement_leads)} perfis encontrados")

    all_leads = keyword_leads + engagement_leads
    added, dupes = add_leads(all_leads)
    print(f"\n✅ {added} leads novos adicionados ({dupes} duplicatas ignoradas)")
    print_summary()
    print(f"\n📊 Planilha salva em: leads.csv")
    print("👉 Revise a planilha e altere 'status' de 'pending' para 'approved'")
    print("   nos leads que deseja contatar. Depois rode: python messenger.py")
