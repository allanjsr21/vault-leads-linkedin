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


QUALIFY_PROMPT = """Voce e um classificador de leads para a Vault Capital (custódia e gestão de Bitcoin).

Analise o perfil abaixo e retorne UM JSON com dois campos:
- "score": número inteiro de 1 a 10
- "reason": frase curta (max 15 palavras) explicando a nota

CRITÉRIOS DE PONTUAÇÃO:
9-10 → Perfil IDEAL: profissional de alta renda (médico, advogado, engenheiro, CEO, empresário)
       que menciona EXPLICITAMENTE bitcoin, hodl, autocustódia, cold wallet ou hardware wallet.
       Ex: "Cirurgião em SP. Bitcoin maximalist. Stack sats diariamente."

7-8  → Bom lead: profissional de alta renda que menciona cripto/blockchain/investimento digital
       de forma clara, mesmo sem citar bitcoin diretamente.
       Ex: "Dentista. Investidor em criptoativos desde 2018."

5-6  → Lead médio: empresário/executivo/profissional sem menção a cripto, mas perfil de patrimônio
       alto (sócio, fundador, diretor) — pode ser abordado com contexto educacional.

3-4  → Baixa qualidade: profissional de área não relacionada, sem sinal de interesse em cripto.

1-2  → REJEITAR: funcionário de exchange, trader profissional, influencer cripto, político,
       perfil de empresa (não pessoa física), pessoa inacessível.

PERFIL:
Nome: {name}
Cargo: {job_title}
Empresa: {company}
Localização: {location}
Bio/Headline: {bio}

Retorne SOMENTE o JSON, sem markdown, sem explicação extra:
{{"score": N, "reason": "..."}}"""


def qualify_lead(name: str, job_title: str = "", company: str = "",
                 location: str = "", bio: str = "") -> Optional[dict]:
    """
    Usa Gemini Flash para qualificar um lead com score 1-10.

    Returns:
        dict com {"score": int, "reason": str}
        None = erro ou sem API key
    """
    global _last_call_time

    cache_key = f"{name}|{job_title}|{company}".lower().strip()
    if cache_key in _cache:
        return _cache[cache_key]

    client = _get_client()
    if client is None:
        return None

    now = time.time()
    elapsed = now - _last_call_time
    if elapsed < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - elapsed)

    prompt = QUALIFY_PROMPT.format(
        name=name,
        job_title=job_title or "(não informado)",
        company=company or "(não informado)",
        location=location or "(não informado)",
        bio=bio or "(não informado)",
    )

    try:
        import json as _json
        from google.genai import types

        _last_call_time = time.time()
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.0,
                max_output_tokens=60,
            ),
        )

        raw = response.text.strip()
        # Extrair JSON mesmo se vier com markdown ```json ... ```
        json_match = __import__("re").search(r'\{.*\}', raw, __import__("re").DOTALL)
        if not json_match:
            raise ValueError(f"JSON não encontrado na resposta: {raw}")

        result = _json.loads(json_match.group(0))
        score = int(result.get("score", 0))
        reason = result.get("reason", "")

        _cache[cache_key] = {"score": score, "reason": reason}
        log.info(f"[gemini] score={score} | {name} ({job_title} @ {company}) — {reason}")
        return _cache[cache_key]

    except Exception as e:
        log.error(f"[gemini] Erro ao qualificar {name}: {e}")
        return None


def qualify_leads_batch(leads: list, min_score: int = 6, callback=None) -> tuple[list, int]:
    """
    Filtra e ordena leads via Gemini (score 1-10).

    Args:
        min_score: score mínimo para aceitar (default 6)

    Returns:
        (leads_aceitos_ordenados_por_score, total_rejeitados)
    """
    import json as _json

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

        if result is None:
            # Sem API key ou erro → aceita com score neutro
            accepted.append(lead)
        elif result["score"] >= min_score:
            lead.ai_score = _json.dumps(result, ensure_ascii=False)
            accepted.append(lead)
        else:
            rejected += 1

        if callback:
            score = result["score"] if result else None
            callback(i + 1, len(leads), lead.name, score)

    # Ordenar aceitos por score decrescente (melhores primeiro)
    def _score(l):
        try:
            return _json.loads(l.ai_score).get("score", 0)
        except Exception:
            return 0

    accepted.sort(key=_score, reverse=True)
    return accepted, rejected
