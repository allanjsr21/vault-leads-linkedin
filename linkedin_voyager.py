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

# Keywords focadas em entusiastas — sem cidades (filtro de país via GeoURN)
TOPIC_KEYWORDS = [
    "bitcoin hodler",
    "bitcoin entusiasta",
    "autocustódia bitcoin",
    "cold wallet bitcoin",
    "hardware wallet bitcoin",
    "bitcoin investidor",
    "hodl bitcoin",
    "soberania financeira bitcoin",
    "not your keys bitcoin",
    "bitcoin maximalist",
    "stack sats",
    "bitcoiner",
    "bitcoin enthusiast",
    "crypto enthusiast bitcoin",
    "médico bitcoin",
    "advogado bitcoin",
    "engenheiro bitcoin",
    "empresário bitcoin",
    "CEO bitcoin",
    "diretor bitcoin",
    "reserva de valor bitcoin",
    "liberdade financeira bitcoin",
    "DCA bitcoin",
    "acumulando bitcoin",
    "laser eyes bitcoin",
]


def _get_headers() -> dict:
    li_at = getattr(config, "LINKEDIN_LI_AT", "")
    jsessionid = getattr(config, "LINKEDIN_JSESSIONID", "")
    # Remove aspas se presentes no JSESSIONID
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


def _voyager_search(keywords: str, start: int = 0) -> Optional[list]:
    """Faz uma busca no Voyager API. Retorna lista de perfis ou None."""
    li_at = getattr(config, "LINKEDIN_LI_AT", "")
    if not li_at:
        return None

    params = {
        "decorationId": "com.linkedin.voyager.deco.jserp.WebSearchPeopleResultWithDistance-5",
        "q": "jserpFilters",
        "queryContext": "List(primaryHitType->PROFILE,spellCorrectionEnabled->true)",
        "filters": f"List(currentRegion->{BRAZIL_GEO_URN})",
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

        log.info(f"[voyager] '{keywords}' start={start} → {len(results)} perfis")
        return results

    except Exception as e:
        log.error(f"[voyager] Erro: {e}")
        return None


def search_linkedin_direct(max_results: int = 100, callback=None) -> list:
    """
    Busca perfis diretamente no LinkedIn via Voyager API.
    Retorna lista de dicts com nome, cargo, empresa, localização e URL.
    """
    if not getattr(config, "LINKEDIN_LI_AT", ""):
        log.warning("[voyager] LINKEDIN_LI_AT não configurado — pulando busca direta.")
        return []

    from scraper import _location_allowed

    keywords_list = list(TOPIC_KEYWORDS)
    random.shuffle(keywords_list)

    seen_vanity: set = set()
    leads_raw = []

    for kw in keywords_list:
        if len(leads_raw) >= max_results:
            break

        for page in range(3):  # até 75 resultados por keyword
            if len(leads_raw) >= max_results:
                break

            start = page * 25
            results = _voyager_search(kw, start=start)

            if results is None:  # erro de auth ou rate limit
                break
            if not results:
                break

            new_count = 0
            for r in results:
                if r["vanity"] in seen_vanity:
                    continue
                seen_vanity.add(r["vanity"])

                # Filtro de localização (usa a mesma lógica do scraper principal)
                if not _location_allowed(r["location"], r["headline"]):
                    continue

                leads_raw.append(r)
                new_count += 1
                if len(leads_raw) >= max_results:
                    break

            if callback:
                callback(len(leads_raw), max_results, kw)

            if new_count == 0:
                break  # sem novos nessa keyword, próxima

            # Delay humanizado entre requests (3–6 s para não ser detectado)
            time.sleep(random.uniform(3.0, 6.0))

        time.sleep(random.uniform(2.0, 4.0))

    log.info(f"[voyager] Total coletado: {len(leads_raw)} perfis")
    return leads_raw
