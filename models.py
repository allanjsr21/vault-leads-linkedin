"""
Definições de dados compartilhadas entre módulos.
Separado de leads_manager para evitar importações circulares.
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Lead:
    name: str
    linkedin_url: str
    first_name: str = ""
    job_title: str = ""
    company: str = ""
    location: str = ""
    source: str = ""          # "keyword_search" | "post_engagement"
    status: str = "pending"   # "pending" | "approved" | "sent" | "failed" | "skipped"
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
