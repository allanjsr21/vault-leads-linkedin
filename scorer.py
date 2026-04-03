"""
scorer.py — Sistema de pontuação de leads para Vault Capital

Filosofia: pontuar por INTERESSE em bitcoin, não por cargo.
O público-alvo é pessoa física que investe ou quer investir em bitcoin,
independente da profissão. Um médico entusiasta vale mais que um CEO de exchange.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from leads_manager import Lead


# ── Sinais de interesse na bio/snippet (0–40 pts) ────────────────────────────
# Esses termos aparecem no snippet do LinkedIn (headline + about section)
# Quem menciona esses termos no perfil DEMONSTRA interesse pessoal.

INTEREST_SIGNALS: list[tuple[list[str], int]] = [
    # Tier S — Autocustódia explícita (máxima intenção para o produto)
    (["autocustodia", "autocustódia", "self.custody", "self custody",
      "cold wallet", "hardware wallet", "ledger", "trezor",
      "not your keys", "nao sua chave", "não sua chave",
      "soberania financeira", "guardo meu bitcoin", "meu bitcoin"], 40),

    # Tier A — Autodeclaração de interesse em bitcoin
    (["entusiasta bitcoin", "entusiasta de bitcoin", "entusiasta cripto",
      "entusiasta de cripto", "apaixonado por bitcoin", "apaixonado por cripto",
      "bitcoiner", "bitcoin maximalist", "bitcoin maxi", "btc maxi",
      "bitcoin enthusiast", "crypto enthusiast", "hodler", "hodl",
      "stacking sats", "stack sats", "dca bitcoin"], 35),

    # Tier B — Investidor pessoal em cripto
    (["investidor bitcoin", "investidor de bitcoin", "investidor cripto",
      "investidor de cripto", "invisto em bitcoin", "compro bitcoin",
      "acumulando bitcoin", "bitcoin longo prazo", "investimento em cripto",
      "minha carteira cripto", "minha carteira bitcoin",
      "patrimônio digital", "patrimonio digital", "alocação em cripto",
      "diversificação cripto"], 28),

    # Tier C — Interesse geral em blockchain/cripto/fintech
    (["bitcoin", "btc", "blockchain", "crypto", "cripto", "criptomoeda",
      "criptoativo", "web3", "defi", "nft", "ethereum", "eth",
      "satoshi", "halving"], 18),

    # Tier D — Interesse em finanças/investimentos (pode incluir cripto)
    (["investidor", "investor", "fintech", "mercado financeiro",
      "renda variável", "renda variavel", "day trade", "swing trade",
      "bolsa de valores", "ações", "acoes", "investimento alternativo",
      "family office", "wealth management", "gestão de patrimônio",
      "gestao de patrimonio"], 10),
]


# ── Acessibilidade do lead (0–25 pts) ────────────────────────────────────────
# Não queremos C-Suite de grandes empresas (difíceis de contactar).
# Queremos profissionais acessíveis de qualquer área.

ACCESSIBILITY_SCORES: list[tuple[list[str], int]] = [
    # Tier S — Autônomos, donos de PME, consultores (muito acessíveis)
    (["autônomo", "autonomo", "freelancer", "consultor", "consultora",
      "dono", "proprietário", "proprietario",
      "sócio", "socio", "co-fundador", "cofundador",
      "empreendedor", "empreendedora", "empresário", "empresaria",
      "profissional liberal", "advisor", "assessor"], 25),

    # Tier A — Profissionais qualificados (acessíveis + com renda)
    (["médico", "medico", "advogado", "engenheiro", "engenheira",
      "dentista", "arquiteto", "contador", "contadora",
      "professor", "professora", "psicólogo", "psicologa",
      "veterinário", "veterinaria", "farmacêutico", "farmaceutica",
      "fisioterapeuta", "nutricionista", "cirurgião", "cirurgiao"], 22),

    # Tier B — Gestão média (acessíveis em empresas)
    (["gerente", "manager", "head", "coordenador", "coordenadora",
      "líder", "lider", "supervisor", "especialista", "expert",
      "analista sênior", "analista senior", "senior analyst",
      "tech lead", "product manager", "product owner"], 18),

    # Tier C — Desenvolvedores/tech (tech-savvy, entendem cripto)
    (["desenvolvedor", "developer", "engenheiro de software",
      "software engineer", "programador", "full stack", "backend",
      "frontend", "devops", "data scientist", "data engineer",
      "machine learning", "cybersecurity", "infosec"], 15),

    # Tier D — Diretores (podem ser acessíveis em empresas menores)
    (["diretor", "diretora", "director", "fundador", "fundadora",
      "founder"], 12),

    # Tier E — C-Suite (difíceis de contactar, penalizar)
    (["ceo", "chief executive", "presidente", "president",
      "cfo", "chief financial", "cto", "chief technology",
      "coo", "vp ", "vice president", "vice-president"], 5),
]


# ── Geolocalização (0–20 pts) ────────────────────────────────────────────────
LOCATION_SCORES: list[tuple[list[str], int]] = [
    (["são paulo", "sao paulo", "sp,", "campinas", "santos",
      "ribeirão preto", "sorocaba", "guarulhos"], 20),
    (["rio de janeiro", "rj,", "niterói", "niteroi"], 18),
    (["belo horizonte", "bh,", "mg,", "contagem"], 16),
    (["espírito santo", "espirito santo", "vitória", "vitoria", "es,"], 15),
    (["curitiba", "pr,", "londrina", "maringá", "maringa",
      "florianópolis", "florianopolis", "porto alegre", "rs,",
      "joinville", "blumenau"], 14),
    (["brasília", "brasilia", "df,", "goiânia", "goiania",
      "salvador", "ba,", "recife", "pe,", "fortaleza", "ce,"], 10),
    (["brasil", "brazil"], 6),
]


# ── Qualidade do perfil (0–15 pts) ───────────────────────────────────────────
def _profile_quality(lead) -> int:
    pts = 0
    if lead.company and lead.company.strip():
        pts += 3
    if lead.location and lead.location.strip():
        pts += 3
    if lead.name and len(lead.name.strip().split()) >= 2:
        pts += 2
    if lead.job_title and len(lead.job_title.strip()) > 3:
        pts += 2
    if lead.bio and len(lead.bio.strip()) > 30:
        pts += 3  # bio rica = perfil detalhado
    if lead.source == "linkedin_content":
        pts += 2  # autor de conteúdo = engajamento alto
    return pts


# ── Penalizações ─────────────────────────────────────────────────────────────
# Perfis de empresas/exchanges/políticos que passaram pelo filtro

PENALTY_SIGNALS: list[str] = [
    "exchange", "binance", "mercado bitcoin", "foxbit", "novadax",
    "coinbase", "bitso", "okx", "bybit", "kraken", "bitget",
    "board member", "chairman", "deputado", "senador",
    "ministro", "governador", "prefeito", "embaixador",
    "recrutador", "recruiter", "headhunter", "rh ",
    "human resources", "recursos humanos",
]


# ── Função principal ─────────────────────────────────────────────────────────
def score_lead(lead) -> int:
    """
    Retorna um score de 0–100 para o lead.

    Hot  → 65–100  (abordar primeiro — alto interesse + acessível)
    Warm → 35–64   (fila normal)
    Cold → 0–34    (baixa prioridade)
    """
    score = 0

    # Combinar todos os textos do lead para análise
    bio_text = (lead.bio or "").lower()
    jt_text  = (lead.job_title or "").lower()
    all_text = f"{bio_text} {jt_text}".strip()

    # ── Sinais de interesse (0–40 pts) — MAIS IMPORTANTE ────────────────
    for keywords, pts in INTEREST_SIGNALS:
        if any(kw in all_text for kw in keywords):
            score += pts
            break
    else:
        score += 2  # nenhum sinal de interesse explícito

    # ── Acessibilidade do cargo (0–25 pts) ──────────────────────────────
    for keywords, pts in ACCESSIBILITY_SCORES:
        if any(kw in jt_text for kw in keywords):
            score += pts
            break
    else:
        score += 8  # cargo desconhecido — neutro

    # ── Localização (0–20 pts) ──────────────────────────────────────────
    loc = (lead.location or "").lower()
    for keywords, pts in LOCATION_SCORES:
        if any(kw in loc for kw in keywords):
            score += pts
            break

    # ── Qualidade do perfil (0–15 pts) ──────────────────────────────────
    score += _profile_quality(lead)

    # ── Penalizações ────────────────────────────────────────────────────
    for penalty in PENALTY_SIGNALS:
        if penalty in all_text:
            score -= 20
            break

    return max(0, min(score, 100))


def score_label(score: int) -> str:
    if score >= 65:
        return "Hot"
    elif score >= 35:
        return "Warm"
    else:
        return "Cold"
