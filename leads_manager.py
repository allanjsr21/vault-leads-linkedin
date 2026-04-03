"""
Gerenciamento de leads.

Usa Google Sheets como fonte de verdade quando disponível,
CSV local como fallback (uso offline / sem credenciais).
"""

import csv
import logging
import os
from dataclasses import asdict
from datetime import datetime
from models import BRT
from typing import Optional

import config
from models import Lead, FIELDNAMES, _normalize_url

log = logging.getLogger(__name__)

# Pode ser sobrescrito externamente: leads_manager.LEADS_CSV = "outro.csv"
LEADS_CSV = config.LEADS_CSV


# ── Detecção de ambiente ───────────────────────────────────────────────────────

def _use_sheets() -> bool:
    """
    True se credenciais Google estiverem disponíveis E um perfil estiver selecionado.
    Garante que Sheets só é usado quando SHEET_NAME está configurado.
    """
    if not config.SHEET_NAME:
        return False
    # Streamlit Cloud: credenciais via secrets
    try:
        import streamlit as st
        if st.secrets.get("GOOGLE_TOKEN_JSON"):
            return True
    except Exception:
        pass
    # Local: token salvo em arquivo
    return os.path.exists("google_token.json")


# ── API pública ────────────────────────────────────────────────────────────────

def load_leads() -> dict[str, Lead]:
    """Carrega leads da fonte disponível (Sheets ou CSV)."""
    if _use_sheets():
        try:
            from sheets_manager import sheets_load_leads
            return sheets_load_leads()
        except Exception as e:
            log.warning(f"Falha ao ler Sheets, usando CSV: {e}")
    return _csv_load_leads()


def save_leads(leads: dict[str, Lead]) -> None:
    """Salva leads na fonte disponível (Sheets ou CSV)."""
    if _use_sheets():
        try:
            from sheets_manager import sheets_save_leads
            sheets_save_leads(leads)
            return
        except Exception as e:
            log.warning(f"Falha ao salvar no Sheets, usando CSV: {e}")
    _csv_save_leads(leads)


def add_leads(new_leads: list[Lead]) -> tuple[int, int]:
    """Adiciona leads novos, ignorando duplicatas. Retorna (adicionados, duplicatas)."""
    if _use_sheets():
        try:
            from sheets_manager import sheets_add_leads
            return sheets_add_leads(new_leads)
        except Exception as e:
            log.warning(f"Falha ao adicionar no Sheets, usando CSV: {e}")
    return _csv_add_leads(new_leads)


def update_lead_status(linkedin_url: str, status: str, error: str = "") -> None:
    """Atualiza o status de um lead."""
    if _use_sheets():
        try:
            from sheets_manager import sheets_update_lead_status
            sheets_update_lead_status(linkedin_url, status, error)
            return
        except Exception as e:
            log.warning(f"Falha ao atualizar Sheets, usando CSV: {e}")
    _csv_update_lead_status(linkedin_url, status, error)


# ── Queries ────────────────────────────────────────────────────────────────────

def get_leads_by_status(status: str, limit: Optional[int] = None) -> list[Lead]:
    leads = load_leads()
    result = [l for l in leads.values() if l.status == status]
    if limit:
        result = result[:limit]
    return result


def get_pending_leads(limit: Optional[int] = None) -> list[Lead]:
    return get_leads_by_status("pending", limit)


def get_approved_leads(limit: Optional[int] = None) -> list[Lead]:
    return get_leads_by_status("approved", limit)


def count_sent_today() -> int:
    today = datetime.now(BRT).date().isoformat()
    leads = load_leads()
    return sum(
        1 for l in leads.values()
        if l.status == "sent" and l.sent_at.startswith(today)
    )


def print_summary() -> None:
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
    print(f"  RESUMO DE LEADS — {datetime.now(BRT).strftime('%d/%m/%Y %H:%M')}")
    print(f"{'='*45}")
    print(f"  Total:              {total}")
    for status in ["pending", "approved", "sent", "failed", "skipped"]:
        count = by_status.get(status, 0)
        if count > 0:
            label = STATUS_LABELS.get(status, status)
            print(f"  {label:<22} {count}")
    print(f"  DMs enviadas hoje:  {count_sent_today()}")
    print(f"{'='*45}\n")


# ── CSV fallback ───────────────────────────────────────────────────────────────

def _csv_load_leads() -> dict[str, Lead]:
    leads: dict[str, Lead] = {}
    if not os.path.exists(LEADS_CSV):
        return leads
    with open(LEADS_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = _normalize_url(row["linkedin_url"])
            leads[key] = Lead(**{k: row.get(k, "") for k in FIELDNAMES})
    return leads


def _csv_save_leads(leads: dict[str, Lead]) -> None:
    with open(LEADS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for lead in leads.values():
            writer.writerow(asdict(lead))


def _csv_add_leads(new_leads: list[Lead]) -> tuple[int, int]:
    existing = _csv_load_leads()
    added = 0
    dupes = 0
    for lead in new_leads:
        key = _normalize_url(lead.linkedin_url)
        if key in existing:
            dupes += 1
        else:
            existing[key] = lead
            added += 1
    _csv_save_leads(existing)
    return added, dupes


def _csv_update_lead_status(linkedin_url: str, status: str, error: str = "") -> None:
    leads = _csv_load_leads()
    key = _normalize_url(linkedin_url)
    if key in leads:
        leads[key].status = status
        leads[key].error = error
        if status == "sent":
            leads[key].sent_at = datetime.now(BRT).isoformat()
    _csv_save_leads(leads)
