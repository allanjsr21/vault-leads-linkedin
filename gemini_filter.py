"""
Filtro inteligente de leads via Google Gemini Flash.

Analisa o snippet/bio do lead e decide se é um perfil com interesse
REAL em Bitcoin/cripto (aceita) ou se é profissional de exchange/
cripto sem fit (rejeita).

Gemini Flash é gratuito: 15 req/min, 1500 req/dia.
"""

import logging
import time
from typing import Optional

log = logging.getLogger(__name__)

# Cache para evitar chamadas duplicadas
_cache: dict[str, bool] = {}

# Rate limiting simples
_last_call_time = 0.0
_MIN_INTERVAL = 4.2  # ~14 req/min (margem de segurança para 15/min)


def _get_client():
    """Cria cliente Gemini sob demanda."""
    try:
        import config
        api_key = getattr(config, "GEMINI_API_KEY", "")
        if not api_key:
            return None
        from google import genai
        return genai.Client(api_key=api_key)
    except ImportError:
        log.warning("[gemini] google-genai não instalado")
        return None
    except Exception as e:
        log.error(f"[gemini] Erro ao criar cliente: {e}")
        return None


QUALIFY_PROMPT = """Voce e um filtro de leads para a Vault Capital, empresa que organiza eventos de autocustodia de Bitcoin e oferece consultoria em criptoativos.

Analise este perfil do LinkedIn e responda APENAS "SIM" ou "NAO".

Responda SIM se:
- Pessoa COMUM (medico, advogado, empresario, engenheiro, dentista, etc.) que menciona Bitcoin, cripto, blockchain ou investimentos digitais no perfil
- Investidor pessoal de Bitcoin/cripto (nao profissional de exchange)
- Entusiasta de Bitcoin, hodler, interessado em autocustodia
- Empresario/executivo que pode ter interesse em diversificar patrimonio em cripto
- Qualquer profissional que demonstre interesse pessoal em Bitcoin

Responda NAO se:
- Funcionario de exchange (Binance, Coinbase, Mercado Bitcoin, Foxbit, etc.)
- Analista de cripto, trader profissional, gestor de fundo cripto
- Influencer/youtuber de cripto (ja sabe tudo, nao e nosso publico)
- Perfil sem NENHUMA conexao com Bitcoin/cripto/investimentos
- Politico, celebridade, pessoa inacessivel
- Perfil de empresa (nao pessoa fisica)

PERFIL:
Nome: {name}
Cargo: {job_title}
Empresa: {company}
Localizacao: {location}
Bio/Headline: {bio}

Responda apenas SIM ou NAO:"""


def qualify_lead(name: str, job_title: str = "", company: str = "",
                 location: str = "", bio: str = "") -> Optional[bool]:
    """
    Usa Gemini Flash para qualificar um lead.

    Returns:
        True = lead qualificado (aceitar)
        False = lead nao qualificado (rejeitar)
        None = erro ou sem API key (aceitar por padrao)
    """
    global _last_call_time

    # Cache key
    cache_key = f"{name}|{job_title}|{company}".lower().strip()
    if cache_key in _cache:
        return _cache[cache_key]

    client = _get_client()
    if client is None:
        return None  # Sem API = aceita por padrao

    # Rate limiting
    now = time.time()
    elapsed = now - _last_call_time
    if elapsed < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - elapsed)

    prompt = QUALIFY_PROMPT.format(
        name=name,
        job_title=job_title or "(nao informado)",
        company=company or "(nao informado)",
        location=location or "(nao informado)",
        bio=bio or "(nao informado)",
    )

    try:
        from google.genai import types

        _last_call_time = time.time()
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.0,
                max_output_tokens=5,
            ),
        )

        answer = response.text.strip().upper()
        result = "SIM" in answer

        _cache[cache_key] = result
        label = "ACEITO" if result else "REJEITADO"
        log.info(f"[gemini] {label}: {name} ({job_title} @ {company})")
        return result

    except Exception as e:
        log.error(f"[gemini] Erro ao qualificar {name}: {e}")
        return None  # Erro = aceita por padrao


def qualify_leads_batch(leads: list, callback=None) -> tuple[list, int]:
    """
    Filtra uma lista de leads via Gemini.

    Returns:
        (leads_aceitos, total_rejeitados)
    """
    accepted = []
    rejected = 0

    for i, lead in enumerate(leads):
        result = qualify_lead(
            name=lead.name,
            job_title=lead.job_title,
            company=lead.company,
            location=lead.location,
            bio=lead.bio,
        )

        if result is False:
            rejected += 1
        else:
            accepted.append(lead)

        if callback:
            callback(i + 1, len(leads), lead.name, result)

    return accepted, rejected
