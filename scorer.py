"""
scorer.py — Sistema de pontuação de leads para Vault Capital

Sweet spot: sócios de PMEs, empreendedores, gerentes, consultores, analistas sênior.
Penaliza: C-Suite de grandes empresas (CEO/CFO de corp) — difíceis de contactar.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from leads_manager import Lead


# ── Pontuação por cargo (0–40 pts) ────────────────────────────────────────────
# Foco: acessíveis e com capital para Bitcoin self-custody

SENIORITY_SCORES: list[tuple[list[str], int]] = [

    # Tier S — Sócios/donos de PME: pessoa física com decisão e capital
    (["sócio", "socio", "co-fundador", "cofundador", "co-founder",
      "cofounder", "dono", "proprietário", "proprietario",
      "sócia", "socia"], 38),

    # Tier A — Empreendedores e profissionais autônomos
    (["empreendedor", "empreendedora", "empresário", "empresaria",
      "autônomo", "autonomo", "freelancer", "consultor", "consultora",
      "advisor", "assessor"], 34),

    # Tier B — Gestão média acessível
    (["gerente", "manager", "head", "coordenador", "coordenadora",
      "líder", "lider", "supervisor", "especialista", "expert",
      "analista sênior", "analista senior", "senior analyst"], 28),

    # Tier C — Fundadores/diretores (podem ser de empresa pequena ou grande)
    (["fundador", "fundadora", "founder", "diretor", "diretora",
      "director"], 22),

    # Tier D — C-Suite: alto cargo mas difícil de contactar em grandes empresas
    # Mantemos score moderado — podem ser CEOs de startup de 3 pessoas
    (["cto", "coo", "cmo", "cpo", "ciso"], 18),

    # Tier E — CEO/CFO/VP: penalizado porque geralmente são grandes empresas
    (["ceo", "chief executive", "presidente", "president",
      "cfo", "chief financial", "vp ", "vice president",
      "vice-president", "vicepresidente"], 10),

    # Tier F — Júnior: pouco capital disponível
    (["analista", "analyst", "assistente", "assistant",
      "trainee", "estagiário", "estagiaria", "estudante",
      "intern", "júnior", "junior"], 8),
]


# ── Sinais de interesse no produto (0–30 pts) ────────────────────────────────
# Qualquer pessoa que demonstre interesse em Bitcoin, finanças alternativas
# ou proteção patrimonial é potencial cliente — não apenas por cargo.

CRYPTO_SIGNALS: list[tuple[list[str], int]] = [
    # Autocustódia / self-custody explícito — máxima intenção
    (["autocustodia", "autocustódia", "self.custody", "self custody",
      "cold wallet", "hardware wallet", "ledger", "trezor", "hodl", "hodler",
      "bitcoin maxi", "bitcoin maximalist"], 30),

    # Bitcoin/cripto no cargo — interesse declarado profissionalmente
    (["bitcoin", "btc", "cripto", "crypto", "blockchain",
      "web3", "defi", "satoshi", "nft"], 25),

    # Proteção patrimonial e investimento alternativo
    # Ex: advogado especialista em planejamento patrimonial, gestor de patrimônio
    (["planejamento patrimonial", "proteção patrimonial", "gestão de patrimônio",
      "family office", "multifamily", "wealth management", "gestão de ativos",
      "asset management", "renda variável", "renda variavel", "alocação",
      "alocacao", "portfólio", "portfolio"], 22),

    # Perfis de tecnologia — tech-savvy, mais propensos à autocustódia
    (["desenvolvedor", "developer", "engenheiro de software", "software engineer",
      "programador", "programmer", "devops", "arquiteto de software",
      "full stack", "backend", "frontend", "data engineer", "machine learning",
      "segurança da informação", "cybersecurity", "infosec", "sre"], 18),

    # Finanças e mercado — conhecem riscos financeiros, abertos a alternativas
    (["investidor", "investor", "fintech", "finanças", "financas",
      "mercado financeiro", "gestor", "assessor de investimentos",
      "planejador financeiro", "cfa", "agente autônomo", "aai"], 15),

    # Empreendedorismo e negócios — entendem valor, tomam decisões próprias
    (["startup", "venture", "angel", "acelerador", "accelerator",
      "inovação", "inovacao", "ecossistema", "scale-up"], 12),
]


# ── Geolocalização (0–20 pts) ──────────────────────────────────────────────────
LOCATION_SCORES: list[tuple[list[str], int]] = [
    # Sudeste prioritário
    (["são paulo", "sao paulo", "sp,", "greater são paulo",
      "região metropolitana de são paulo", "campinas", "santos",
      "ribeirão preto", "sorocaba", "guarulhos", "abc paulista"], 20),
    (["rio de janeiro", "rj,", "niterói", "niteroi",
      "greater rio", "região metropolitana do rio"], 18),
    (["belo horizonte", "bh,", "mg,", "contagem", "betim",
      "greater belo horizonte", "região metropolitana de belo horizonte"], 16),
    (["espírito santo", "espirito santo", "vitória", "vitoria",
      "vila velha", "es,"], 15),
    # Sul
    (["curitiba", "pr,", "londrina", "maringá", "maringa",
      "florianópolis", "florianopolis", "porto alegre", "rs,",
      "joinville", "blumenau"], 14),
    # Centro-Oeste + Nordeste grandes centros
    (["brasília", "brasilia", "df,", "goiânia", "goiania",
      "salvador", "ba,", "recife", "pe,", "fortaleza", "ce,",
      "manaus", "am,", "belém", "belem", "pa,"], 10),
    # Brasil genérico
    (["brasil", "brazil", "br,", "br "], 6),
]


# ── Qualidade do perfil (0–10 pts) ────────────────────────────────────────────
def _profile_quality(lead) -> int:
    pts = 0
    if lead.company and lead.company.strip():
        pts += 4
    if lead.location and lead.location.strip():
        pts += 3
    if lead.name and len(lead.name.strip().split()) >= 2:
        pts += 2
    if lead.job_title and len(lead.job_title.strip()) > 3:
        pts += 1
    return pts


# ── Função principal ──────────────────────────────────────────────────────────
def score_lead(lead) -> int:
    """
    Retorna um score de 0–100 para o lead.

    Hot  → 65–100  (abordar primeiro)
    Warm → 35–64   (fila normal)
    Cold → 0–34    (baixa prioridade)
    """
    score = 0
    jt  = (lead.job_title or "").lower()
    loc = (lead.location  or "").lower()

    # Seniority
    for keywords, pts in SENIORITY_SCORES:
        if any(kw in jt for kw in keywords):
            score += pts
            break
    else:
        score += 5  # cargo desconhecido — neutro

    # Sinais cripto (acumula apenas 1 tier)
    for keywords, pts in CRYPTO_SIGNALS:
        if any(kw in jt for kw in keywords):
            score += pts
            break

    # Localização (acumula apenas 1 tier)
    for keywords, pts in LOCATION_SCORES:
        if any(kw in loc for kw in keywords):
            score += pts
            break

    # Qualidade do perfil
    score += _profile_quality(lead)

    return min(score, 100)


def score_label(score: int) -> str:
    if score >= 65:
        return "Hot"
    elif score >= 35:
        return "Warm"
    else:
        return "Cold"


def score_color(score: int) -> str:
    """Retorna classe CSS para badge de score."""
    if score >= 65:
        return "score-hot"
    elif score >= 35:
        return "score-warm"
    else:
        return "score-cold"
