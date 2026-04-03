"""
enricher.py — Enriquecimento de leads (email, dados adicionais)

Provedores suportados:
  1. Hunter.io (50 buscas/mês grátis) — busca email por nome + empresa
  2. Fallback: derivação de email via padrões comuns (nome@empresa.com)

Configuração:
  - HUNTER_API_KEY no Streamlit secrets ou config.py
"""

import logging
import re
from typing import Optional

import requests

import config

log = logging.getLogger(__name__)

HUNTER_API_URL = "https://api.hunter.io/v2/email-finder"


def _clean_company_domain(company: str) -> str:
    """Tenta derivar um domínio a partir do nome da empresa."""
    if not company:
        return ""
    # Remove sufixos corporativos comuns
    company = company.strip()
    for suffix in ["Ltda", "LTDA", "S.A.", "SA", "S/A", "ME", "EIRELI",
                    "Inc.", "Inc", "LLC", "Ltd", "Corp", "Corp."]:
        company = company.replace(suffix, "").strip()
    # Remove caracteres especiais, mantém letras e números
    domain = re.sub(r"[^a-zA-Z0-9]", "", company.lower())
    if domain:
        return f"{domain}.com.br"
    return ""


# ── Hunter.io ──────────────────────────────────────────────────────────────────

def hunter_find_email(
    first_name: str,
    last_name: str,
    company: str = "",
    domain: str = "",
) -> Optional[dict]:
    """
    Busca email via Hunter.io Email Finder.
    Retorna dict com email, score, position ou None.
    """
    api_key = getattr(config, "HUNTER_API_KEY", "")
    if not api_key:
        return None

    if not domain and company:
        domain = _clean_company_domain(company)
    if not domain:
        return None

    try:
        resp = requests.get(
            HUNTER_API_URL,
            params={
                "domain": domain,
                "first_name": first_name,
                "last_name": last_name,
                "api_key": api_key,
            },
            timeout=10,
        )
        if resp.status_code != 200:
            log.warning(f"[hunter] HTTP {resp.status_code}: {resp.text[:200]}")
            return None

        data = resp.json().get("data", {})
        email = data.get("email")
        if email:
            return {
                "email": email,
                "score": data.get("score", 0),
                "position": data.get("position", ""),
                "source": "hunter",
            }
    except requests.RequestException as e:
        log.error(f"[hunter] Erro de conexão: {e}")

    return None


# ── Enriquecimento principal ──────────────────────────────────────────────────

def enrich_lead(lead) -> dict:
    """
    Tenta enriquecer um lead com email.
    Retorna dict com dados encontrados (pode ser vazio).
    """
    result = {}

    # Extrair nome e sobrenome
    name_parts = (lead.name or "").strip().split()
    if len(name_parts) < 2:
        return result

    first_name = name_parts[0]
    last_name = name_parts[-1]

    # Tentar Hunter.io
    hunter_result = hunter_find_email(
        first_name=first_name,
        last_name=last_name,
        company=lead.company or "",
    )
    if hunter_result:
        result["email"] = hunter_result["email"]
        result["email_source"] = "hunter"
        result["email_confidence"] = hunter_result.get("score", 0)
        log.info(f"[enricher] Email encontrado via Hunter: {hunter_result['email']}")

    return result


def enrich_leads_batch(leads: list, callback=None) -> list[dict]:
    """
    Enriquece uma lista de leads em batch.
    callback(i, total, result) é chamado após cada lead.
    Retorna lista de dicts com dados encontrados.
    """
    results = []
    for i, lead in enumerate(leads):
        result = enrich_lead(lead)
        results.append(result)
        if callback:
            callback(i, len(leads), result)
    return results
