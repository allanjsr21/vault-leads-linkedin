"""
Google Sheets como fonte de verdade para leads da Vault Capital.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 COMO CONFIGURAR (faça uma vez só)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 1. Acesse: https://console.cloud.google.com/
 2. Crie um projeto (ou use um existente)
 3. Ative as APIs: Google Sheets API + Google Drive API
 4. Em "Credenciais" → "Criar credenciais" → "Conta de serviço"
 5. Na conta de serviço → "Chaves" → "Adicionar chave" → JSON
      - Salve como: oauth_credentials.json
 6. Rode o agente — ele cria a planilha automaticamente.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import gspread
from gspread.exceptions import SpreadsheetNotFound, WorksheetNotFound
from gspread_formatting import (
    BooleanCondition,
    BooleanRule,
    CellFormat,
    Color,
    ConditionalFormatRule,
    DataValidationRule,
    GridRange,
    TextFormat,
    get_conditional_format_rules,
    format_cell_range,
    set_data_validation_for_cell_range,
)
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

import config
from config import GOOGLE_OAUTH_FILE, GOOGLE_TOKEN_FILE, SHEET_OWNER_EMAIL
from models import Lead, FIELDNAMES, _normalize_url

log = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Aba principal — fonte de verdade para aprovação
MASTER_TAB = "Todos"

# ── Estrutura das colunas ──────────────────────────────────────────────────────
SHEET_COLUMNS = [
    "status",        # A
    "name",          # B
    "linkedin_url",  # C
    "job_title",     # D
    "company",       # E
    "location",      # F
    "bio",           # G
    "email",         # H
    "ai_score",      # I
    "source",        # J
    "sent_at",       # K
    "error",         # L
    "collected_at",  # M
]

COLUMN_LABELS = {
    "status":       "Status",
    "name":         "Nome",
    "linkedin_url": "LinkedIn",
    "job_title":    "Cargo",
    "company":      "Empresa",
    "location":     "Localização",
    "bio":          "Bio / Interesses",
    "email":        "Email",
    "ai_score":     "IA Score",
    "source":       "Origem",
    "sent_at":      "DM Enviada em",
    "error":        "Erro",
    "collected_at": "Coletado em",
}

COLUMN_WIDTHS = [
    110,  # A — Status
    200,  # B — Nome
    220,  # C — LinkedIn
    220,  # D — Cargo
    180,  # E — Empresa
    150,  # F — Localização
    280,  # G — Bio / Interesses
    200,  # H — Email
    200,  # I — IA Score
    100,  # J — Origem
    160,  # K — DM Enviada em
    200,  # L — Erro
    140,  # M — Coletado em
]

NUM_COLS = len(SHEET_COLUMNS)
LAST_COL_LETTER = chr(ord("A") + NUM_COLS - 1)  # "J"
STATUS_OPTIONS = ["pending", "approved", "skipped"]

# Índices de colunas (0-based) — usados em sheets_update_lead_status
_IDX_STATUS   = SHEET_COLUMNS.index("status")
_IDX_URL      = SHEET_COLUMNS.index("linkedin_url")
_IDX_SENT_AT  = SHEET_COLUMNS.index("sent_at")
_IDX_ERROR    = SHEET_COLUMNS.index("error")


# ── Autenticação ───────────────────────────────────────────────────────────────

def _get_client() -> gspread.Client:
    """
    Autentica via OAuth.
    - Streamlit Cloud: lê credenciais de st.secrets
    - Local: usa arquivos oauth_credentials.json / google_token.json
    """
    creds = None

    # Streamlit Cloud
    try:
        import streamlit as st
        token_json = st.secrets.get("GOOGLE_TOKEN_JSON", "")

        if token_json:
            creds = Credentials.from_authorized_user_info(json.loads(token_json), SCOPES)
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())

        if not creds or not creds.valid:
            raise RuntimeError(
                "Token Google expirado ou ausente no Streamlit secrets.\n"
                "Atualize GOOGLE_TOKEN_JSON no painel do Streamlit Cloud."
            )

        if creds and creds.valid:
            return gspread.authorize(creds)
    except ImportError:
        pass  # streamlit não disponível
    except RuntimeError:
        raise

    # Local
    if os.path.exists(GOOGLE_TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(GOOGLE_TOKEN_FILE, SCOPES)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        Path(GOOGLE_TOKEN_FILE).write_text(creds.to_json(), encoding="utf-8")

    if not creds or not creds.valid:
        if not os.path.exists(GOOGLE_OAUTH_FILE):
            raise FileNotFoundError(
                f"Arquivo OAuth não encontrado: '{GOOGLE_OAUTH_FILE}'"
            )
        flow = InstalledAppFlow.from_client_secrets_file(GOOGLE_OAUTH_FILE, SCOPES)
        creds = flow.run_local_server(port=0)
        Path(GOOGLE_TOKEN_FILE).write_text(creds.to_json(), encoding="utf-8")

    return gspread.authorize(creds)


def _open_or_create_sheet(client: gspread.Client) -> gspread.Spreadsheet:
    """Abre ou cria a planilha. Usa config.SHEET_NAME dinamicamente."""
    sheet_name = config.SHEET_NAME
    try:
        sheet = client.open(sheet_name)
        log.info(f"Planilha aberta: '{sheet_name}'")
        return sheet
    except SpreadsheetNotFound:
        log.info(f"Criando planilha: '{sheet_name}'")
        sheet = client.create(sheet_name)
        sheet.share(SHEET_OWNER_EMAIL, perm_type="user", role="writer", notify=True)
        log.info(f"Planilha compartilhada com {SHEET_OWNER_EMAIL}")
        return sheet


# ── Formatação ─────────────────────────────────────────────────────────────────

def _apply_formatting(worksheet: gspread.Worksheet, num_rows: int) -> None:
    """Cabeçalho azul, dropdown de status, cores condicionais por linha, freeze."""
    header_range = f"A1:{LAST_COL_LETTER}1"
    data_range   = f"A2:{LAST_COL_LETTER}{num_rows + 1}"

    format_cell_range(
        worksheet,
        header_range,
        CellFormat(
            backgroundColor=Color(0.13, 0.29, 0.53),
            textFormat=TextFormat(
                bold=True,
                foregroundColor=Color(1, 1, 1),
                fontSize=10,
            ),
        ),
    )

    if num_rows < 1:
        return

    set_data_validation_for_cell_range(
        worksheet,
        f"A2:A{num_rows + 1}",
        DataValidationRule(
            condition=BooleanCondition("ONE_OF_LIST", STATUS_OPTIONS),
            showCustomUi=True,
            strict=True,
        ),
    )

    row_color_rules = [
        ConditionalFormatRule(
            ranges=[GridRange.from_a1_range(data_range, worksheet)],
            booleanRule=BooleanRule(
                condition=BooleanCondition("CUSTOM_FORMULA", ['=$A2="approved"']),
                format=CellFormat(backgroundColor=Color(0.82, 0.96, 0.82)),
            ),
        ),
        ConditionalFormatRule(
            ranges=[GridRange.from_a1_range(data_range, worksheet)],
            booleanRule=BooleanRule(
                condition=BooleanCondition("CUSTOM_FORMULA", ['=$A2="sent"']),
                format=CellFormat(backgroundColor=Color(0.82, 0.91, 1.0)),
            ),
        ),
        ConditionalFormatRule(
            ranges=[GridRange.from_a1_range(data_range, worksheet)],
            booleanRule=BooleanRule(
                condition=BooleanCondition("CUSTOM_FORMULA", ['=$A2="skipped"']),
                format=CellFormat(backgroundColor=Color(0.90, 0.90, 0.90)),
            ),
        ),
        ConditionalFormatRule(
            ranges=[GridRange.from_a1_range(data_range, worksheet)],
            booleanRule=BooleanRule(
                condition=BooleanCondition("CUSTOM_FORMULA", ['=$A2="failed"']),
                format=CellFormat(backgroundColor=Color(1.0, 0.85, 0.85)),
            ),
        ),
    ]
    rules = get_conditional_format_rules(worksheet)
    rules.clear()
    for rule in row_color_rules:
        rules.append(rule)
    rules.save()

    worksheet.freeze(rows=1)

    col_resize_requests = [
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": worksheet.id,
                    "dimension": "COLUMNS",
                    "startIndex": i,
                    "endIndex": i + 1,
                },
                "properties": {"pixelSize": COLUMN_WIDTHS[i]},
                "fields": "pixelSize",
            }
        }
        for i in range(NUM_COLS)
    ]
    worksheet.spreadsheet.batch_update({"requests": col_resize_requests})


def _write_leads_to_worksheet(
    worksheet: gspread.Worksheet,
    leads_iter,
    use_hyperlink: bool = True,
) -> int:
    """
    Escreve cabeçalho + dados num worksheet.
    use_hyperlink=True  → coluna C fica =HYPERLINK (abas de coleta — visual)
    use_hyperlink=False → URL bruta (aba Todos — necessário para leitura de volta)
    Retorna nº de linhas de dados escritas.
    """
    headers = [COLUMN_LABELS.get(col, col) for col in SHEET_COLUMNS]
    rows = [headers]
    for lead in leads_iter:
        row = []
        for col in SHEET_COLUMNS:
            val = getattr(lead, col, "") or ""
            if col == "linkedin_url" and val and use_hyperlink:
                row.append(f'=HYPERLINK("{val}";"Ver perfil")')
            else:
                row.append(val)
        rows.append(row)
    worksheet.update(rows, "A1", value_input_option="USER_ENTERED")
    return len(rows) - 1


# ── CRUD — Sheets como fonte de verdade ───────────────────────────────────────

def sheets_load_leads() -> dict[str, Lead]:
    """Lê todos os leads da aba 'Todos'. Retorna dict indexado por URL normalizada."""
    client = _get_client()
    spreadsheet = _open_or_create_sheet(client)
    try:
        worksheet = spreadsheet.worksheet(MASTER_TAB)
    except WorksheetNotFound:
        return {}

    all_values = worksheet.get_all_values()
    if len(all_values) < 2:
        return {}

    header_row = all_values[0]
    label_to_field = {v: k for k, v in COLUMN_LABELS.items()}
    col_map = {
        i: label_to_field.get(header_row[i], header_row[i])
        for i in range(len(header_row))
    }

    leads: dict[str, Lead] = {}
    for data_row in all_values[1:]:
        record = {
            col_map[i]: data_row[i]
            for i in range(len(data_row))
            if i in col_map
        }
        url = str(record.get("linkedin_url", "")).strip()
        if not url:
            continue
        key = _normalize_url(url)
        leads[key] = Lead(
            name=record.get("name", ""),
            linkedin_url=url,
            job_title=record.get("job_title", ""),
            company=record.get("company", ""),
            location=record.get("location", ""),
            bio=record.get("bio", ""),
            email=record.get("email", ""),
            ai_score=record.get("ai_score", ""),
            source=record.get("source", ""),
            status=record.get("status", "pending"),
            sent_at=record.get("sent_at", ""),
            error=record.get("error", ""),
            collected_at=record.get("collected_at", ""),
        )
    return leads


def sheets_save_leads(leads: dict[str, Lead]) -> str:
    """Salva todos os leads na aba 'Todos' (cria se não existir). Retorna URL."""
    client = _get_client()
    spreadsheet = _open_or_create_sheet(client)

    try:
        worksheet = spreadsheet.worksheet(MASTER_TAB)
        worksheet.clear()
    except WorksheetNotFound:
        # Renomeia sheet1 para "Todos"
        worksheet = spreadsheet.sheet1
        worksheet.update_title(MASTER_TAB)
        worksheet.clear()

    num_rows = _write_leads_to_worksheet(worksheet, leads.values(), use_hyperlink=False)
    if num_rows > 0:
        _apply_formatting(worksheet, num_rows)

    log.info(f"'{MASTER_TAB}' atualizada com {num_rows} leads.")
    return spreadsheet.url


def sheets_add_leads(new_leads: list[Lead]) -> tuple[int, int]:
    """
    Adiciona leads novos ao Sheets, ignorando duplicatas.
    Retorna (adicionados, duplicatas).
    """
    existing = sheets_load_leads()
    added = 0
    dupes = 0
    for lead in new_leads:
        key = _normalize_url(lead.linkedin_url)
        if key in existing:
            dupes += 1
        else:
            existing[key] = lead
            added += 1
    if added > 0:
        sheets_save_leads(existing)
    return added, dupes


def sheets_update_lead_status(url: str, status: str, error: str = "") -> None:
    """
    Atualiza o status de um lead específico no Sheets.
    Operação cirúrgica: atualiza apenas as células necessárias.
    """
    client = _get_client()
    spreadsheet = _open_or_create_sheet(client)
    try:
        worksheet = spreadsheet.worksheet(MASTER_TAB)
    except WorksheetNotFound:
        log.warning(f"Aba '{MASTER_TAB}' não encontrada para atualizar status.")
        return

    key = _normalize_url(url)
    all_values = worksheet.get_all_values()
    if len(all_values) < 2:
        return

    header_row = all_values[0]
    label_to_field = {v: k for k, v in COLUMN_LABELS.items()}
    col_map = {
        i: label_to_field.get(header_row[i], header_row[i])
        for i in range(len(header_row))
    }

    # Encontra índices de colunas relevantes
    status_col = url_col = sent_at_col = error_col = None
    for i, field_name in col_map.items():
        if field_name == "status":        status_col  = i
        elif field_name == "linkedin_url": url_col    = i
        elif field_name == "sent_at":     sent_at_col = i
        elif field_name == "error":       error_col   = i

    if url_col is None or status_col is None:
        return

    for row_idx, data_row in enumerate(all_values[1:], start=2):  # 1-indexed, linha 1 = header
        row_url = str(data_row[url_col]).strip() if url_col < len(data_row) else ""
        if _normalize_url(row_url) == key:
            cells = [gspread.Cell(row_idx, status_col + 1, status)]
            if error_col is not None:
                cells.append(gspread.Cell(row_idx, error_col + 1, error))
            if status == "sent" and sent_at_col is not None:
                from models import BRT
                cells.append(gspread.Cell(row_idx, sent_at_col + 1, datetime.now(BRT).strftime("%Y-%m-%d %H:%M")))
            worksheet.update_cells(cells)
            log.info(f"Status atualizado no Sheets: {url} → {status}")
            return

    log.warning(f"Lead não encontrado no Sheets para atualizar: {url}")


# ── Interface de coleta (abas por rodada) ──────────────────────────────────────

def push_leads_to_sheet(
    leads: Optional[dict] = None,
    tab_name: Optional[str] = None,
) -> str:
    """
    Cria/atualiza uma aba de coleta na planilha com hyperlinks clicáveis.
    - tab_name fornecido: cria aba "Coleta YYYY-MM-DD HH:MM" com os leads desta rodada.
    - sem tab_name: escreve na aba 'Todos' (compatibilidade com main.py).
    Retorna URL da planilha.
    """
    client = _get_client()
    spreadsheet = _open_or_create_sheet(client)

    if leads is None:
        from leads_manager import load_leads
        leads = load_leads()

    if tab_name:
        try:
            worksheet = spreadsheet.worksheet(tab_name)
            worksheet.clear()
        except WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title=tab_name, rows=500, cols=NUM_COLS)
        num_rows = _write_leads_to_worksheet(worksheet, leads.values(), use_hyperlink=True)
        if num_rows > 0:
            _apply_formatting(worksheet, num_rows)
        log.info(f"Aba '{tab_name}' criada com {num_rows} leads.")
    else:
        return sheets_save_leads(leads)

    url = spreadsheet.url
    log.info(f"Planilha atualizada: {url}")
    return url


# ── Leitura de aprovados ───────────────────────────────────────────────────────

def pull_approved_from_sheet() -> list[Lead]:
    """
    Lê a aba 'Todos' e retorna leads com status 'approved'.
    Nunca sobrescreve leads já enviados ou com falha.
    """
    IMMUTABLE_STATUSES = {"sent", "failed"}

    try:
        sheet_leads = sheets_load_leads()
    except Exception as e:
        log.warning(f"Não foi possível ler o Sheets: {e}")
        return []

    if not sheet_leads:
        return []

    # Tenta ler CSV local para proteger status imutáveis
    local_leads: dict = {}
    try:
        from leads_manager import _csv_load_leads
        local_leads = _csv_load_leads()
    except Exception:
        pass

    approved: list[Lead] = []
    for key, lead in sheet_leads.items():
        status = lead.status.strip().lower()
        local = local_leads.get(key)
        if local and local.status in IMMUTABLE_STATUSES:
            log.debug(f"Status imutável preservado: {lead.linkedin_url} ({local.status})")
            continue
        if status == "approved":
            approved.append(lead)

    log.info(f"{len(approved)} leads aprovados encontrados.")
    return approved
