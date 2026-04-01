"""
Gerenciamento de leads: armazenamento em CSV, deduplicação e status de envio.
"""

import csv
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional

from config import LEADS_CSV


@dataclass
class Lead:
    name: str
    linkedin_url: str
    first_name: str = ""
    job_title: str = ""
    company: str = ""
    location: str = ""
    source: str = ""          # "keyword_search" | "post_engagement"
    status: str = "pending"   # "pending" | "sent" | "failed" | "skipped"
    sent_at: str = ""
    error: str = ""
    collected_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def __post_init__(self):
        if not self.first_name and self.name:
            self.first_name = self.name.strip().split()[0]


FIELDNAMES = [
    "name", "first_name", "linkedin_url", "job_title", "company",
    "location", "source", "status", "sent_at", "error", "collected_at",
]


def _normalize_url(url: str) -> str:
    """Remove parâmetros de query e trailing slash para deduplicação."""
    url = url.split("?")[0].rstrip("/").lower()
    return url


def load_leads() -> dict[str, Lead]:
    """Carrega leads do CSV. Retorna dict indexado por URL normalizada."""
    leads: dict[str, Lead] = {}
    if not os.path.exists(LEADS_CSV):
        return leads
    with open(LEADS_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = _normalize_url(row["linkedin_url"])
            leads[key] = Lead(**{k: row.get(k, "") for k in FIELDNAMES})
    return leads


def save_leads(leads: dict[str, Lead]) -> None:
    """Salva todos os leads no CSV."""
    with open(LEADS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for lead in leads.values():
            writer.writerow(asdict(lead))


def add_leads(new_leads: list[Lead]) -> tuple[int, int]:
    """
    Adiciona novos leads ao CSV, ignorando duplicatas.
    Um lead é duplicata se o LinkedIn URL já existir — independente do status.
    Isso garante que leads já prospectados (sent/failed/skipped) nunca sejam
    re-adicionados como pending em coletas futuras.
    Retorna (adicionados, duplicatas).
    """
    existing = load_leads()
    added = 0
    dupes = 0
    for lead in new_leads:
        key = _normalize_url(lead.linkedin_url)
        if key in existing:
            dupes += 1
        else:
            existing[key] = lead
            added += 1
    save_leads(existing)
    return added, dupes


def get_leads_by_status(status: str, limit: Optional[int] = None) -> list[Lead]:
    """Retorna leads com o status especificado."""
    leads = load_leads()
    result = [l for l in leads.values() if l.status == status]
    if limit:
        result = result[:limit]
    return result


def get_pending_leads(limit: Optional[int] = None) -> list[Lead]:
    """Retorna leads com status 'pending' (aguardando revisão)."""
    return get_leads_by_status("pending", limit)


def get_approved_leads(limit: Optional[int] = None) -> list[Lead]:
    """Retorna leads com status 'approved' (aprovados para envio de DM)."""
    return get_leads_by_status("approved", limit)


def update_lead_status(
    linkedin_url: str,
    status: str,
    error: str = "",
) -> None:
    """Atualiza o status de um lead no CSV."""
    leads = load_leads()
    key = _normalize_url(linkedin_url)
    if key in leads:
        leads[key].status = status
        leads[key].error = error
        if status == "sent":
            leads[key].sent_at = datetime.now().isoformat()
    save_leads(leads)


def count_sent_today() -> int:
    """Conta quantas DMs foram enviadas hoje."""
    today = datetime.now().date().isoformat()
    leads = load_leads()
    return sum(
        1 for l in leads.values()
        if l.status == "sent" and l.sent_at.startswith(today)
    )


def print_summary() -> None:
    """Imprime resumo do estado dos leads."""
    leads = load_leads()
    total = len(leads)
    by_status: dict[str, int] = {}
    for lead in leads.values():
        by_status[lead.status] = by_status.get(lead.status, 0) + 1

    STATUS_LABELS = {
        "pending":  "Aguardando revisão",
        "approved": "Aprovados p/ envio",
        "sent":     "DM enviada",
        "failed":   "Falhou",
        "skipped":  "Ignorado",
    }

    print(f"\n{'='*45}")
    print(f"  RESUMO DE LEADS — {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    print(f"{'='*45}")
    print(f"  Total:              {total}")
    for status in ["pending", "approved", "sent", "failed", "skipped"]:
        count = by_status.get(status, 0)
        if count > 0:
            label = STATUS_LABELS.get(status, status)
            print(f"  {label:<22} {count}")
    print(f"  DMs enviadas hoje:  {count_sent_today()}")
    print(f"{'='*45}\n")
