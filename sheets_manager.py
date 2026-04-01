"""
Integração com Google Sheets para gestão de leads da Vault Capital.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 COMO CONFIGURAR (faça uma vez só)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 1. Acesse: https://console.cloud.google.com/
 2. Crie um projeto (ou use um existente)
 3. Ative as APIs:
      - Google Sheets API
      - Google Drive API
 4. Em "Credenciais" → "Criar credenciais" → "Conta de serviço"
      - Dê um nome (ex: vault-leads-agent)
      - Role: Editor
 5. Na conta de serviço criada → "Chaves" → "Adicionar chave" → JSON
      - Salve o arquivo como: google_credentials.json
      - Coloque na pasta do agente (linkedin/)
 6. Pronto! O agente cria a planilha automaticamente.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import logging
import os
from pathlib import Path
from typing import Optional

import gspread
from gspread.exceptions import SpreadsheetNotFound
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

from config import GOOGLE_OAUTH_FILE, GOOGLE_TOKEN_FILE, LEADS_CSV, SHEET_NAME, SHEET_OWNER_EMAIL
from leads_manager import Lead, FIELDNAMES, _normalize_url, load_leads, save_leads

log = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# ── Estrutura das colunas ──────────────────────────────────────────────────────
# Ordem e campos exibidos na planilha
SHEET_COLUMNS = [
    "status",        # A
    "name",          # B
    "linkedin_url",  # C  → renderizado como hyperlink clicável
    "job_title",     # D
    "company",       # E
    "location",      # F
    "source",        # G
    "sent_at",       # H
    "error",         # I
    "collected_at",  # J
]

COLUMN_LABELS = {
    "status":       "Status",
    "name":         "Nome",
    "linkedin_url": "LinkedIn",
    "job_title":    "Cargo",
    "company":      "Empresa",
    "location":     "Localização",
    "source":       "Origem",
    "sent_at":      "DM Enviada em",
    "error":        "Erro",
    "collected_at": "Coletado em",
}

# Largura de cada coluna em pixels (mesma ordem de SHEET_COLUMNS)
COLUMN_WIDTHS = [
    110,  # A — Status
    200,  # B — Nome
    110,  # C — LinkedIn (link "Ver perfil")
    220,  # D — Cargo
    180,  # E — Empresa
    150,  # F — Localização
    130,  # G — Origem
    160,  # H — DM Enviada em
    200,  # I — Erro
    160,  # J — Coletado em
]

NUM_COLS = len(SHEET_COLUMNS)  # 10
LAST_COL_LETTER = chr(ord("A") + NUM_COLS - 1)  # "J"

STATUS_OPTIONS = ["pending", "approved", "skipped"]


def _get_client() -> gspread.Client:
    """
    Autentica via OAuth.
    - No Streamlit Cloud: lê credenciais de st.secrets
    - Local: usa arquivos oauth_credentials.json / google_token.json
    """
    import json

    creds = None

    # ── Streamlit Cloud: credenciais via secrets ───────────────────────────────
    try:
        import streamlit as st
        oauth_json  = st.secrets.get("GOOGLE_OAUTH_JSON", "")
        token_json  = st.secrets.get("GOOGLE_TOKEN_JSON", "")

        if token_json:
            creds = Credentials.from_authorized_user_info(json.loads(token_json), SCOPES)
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())

        if not creds or not creds.valid:
            if oauth_json:
                from google_auth_oauthlib.flow import Flow
                flow = Flow.from_client_config(json.loads(oauth_json), SCOPES)
                # No cloud não há browser — precisa do token já gerado
                raise RuntimeError(
                    "Token Google expirado ou ausente no Streamlit secrets.\n"
                    "Atualize GOOGLE_TOKEN_JSON no painel do Streamlit Cloud."
                )

        if creds and creds.valid:
            return gspread.authorize(creds)
    except ImportError:
        pass  # streamlit não disponível, segue fluxo local
    except RuntimeError:
        raise

    # ── Local: usa arquivos ────────────────────────────────────────────────────
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
    try:
        sheet = client.open(SHEET_NAME)
        log.info(f"Planilha existente aberta: '{SHEET_NAME}'")
        return sheet
    except SpreadsheetNotFound:
        log.info(f"Criando nova planilha: '{SHEET_NAME}'")
        sheet = client.create(SHEET_NAME)
        # Compartilha direto com o e-mail do usuário como editor
        sheet.share(SHEET_OWNER_EMAIL, perm_type="user", role="writer", notify=True)
        log.info(f"Planilha compartilhada com {SHEET_OWNER_EMAIL}")
        return sheet


def _apply_formatting(worksheet: gspread.Worksheet, num_rows: int) -> None:
    """
    Aplica toda a formatação visual da planilha:
    - Cabeçalho azul escuro com texto branco
    - Dropdown de status na coluna A
    - Coloração de LINHA INTEIRA baseada no status (coluna A)
    - Largura correta para todas as 10 colunas
    - Cabeçalho fixo (freeze)
    """
    header_range = f"A1:{LAST_COL_LETTER}1"
    data_range   = f"A2:{LAST_COL_LETTER}{num_rows + 1}"

    # ── Cabeçalho: fundo azul escuro, texto branco, negrito ───────────────────
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

    # ── Dropdown na coluna A (Status) ─────────────────────────────────────────
    set_data_validation_for_cell_range(
        worksheet,
        f"A2:A{num_rows + 1}",
        DataValidationRule(
            condition=BooleanCondition("ONE_OF_LIST", STATUS_OPTIONS),
            showCustomUi=True,
            strict=True,
        ),
    )

    # ── Coloração de LINHA INTEIRA via CUSTOM_FORMULA ─────────────────────────
    # =$A2="valor" → aplica cor a toda a linha quando coluna A bate o valor
    row_color_rules = [
        # approved → verde claro
        ConditionalFormatRule(
            ranges=[GridRange.from_a1_range(data_range, worksheet)],
            booleanRule=BooleanRule(
                condition=BooleanCondition("CUSTOM_FORMULA", ['=$A2="approved"']),
                format=CellFormat(backgroundColor=Color(0.82, 0.96, 0.82)),
            ),
        ),
        # sent → azul claro
        ConditionalFormatRule(
            ranges=[GridRange.from_a1_range(data_range, worksheet)],
            booleanRule=BooleanRule(
                condition=BooleanCondition("CUSTOM_FORMULA", ['=$A2="sent"']),
                format=CellFormat(backgroundColor=Color(0.82, 0.91, 1.0)),
            ),
        ),
        # skipped → cinza claro
        ConditionalFormatRule(
            ranges=[GridRange.from_a1_range(data_range, worksheet)],
            booleanRule=BooleanRule(
                condition=BooleanCondition("CUSTOM_FORMULA", ['=$A2="skipped"']),
                format=CellFormat(backgroundColor=Color(0.90, 0.90, 0.90)),
            ),
        ),
        # failed → vermelho claro
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

    # ── Congela cabeçalho ─────────────────────────────────────────────────────
    worksheet.freeze(rows=1)

    # ── Largura de todas as 10 colunas ────────────────────────────────────────
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


def _write_leads_to_worksheet(worksheet: gspread.Worksheet, leads_iter) -> int:
    """Escreve cabeçalho + dados de leads em um worksheet. Retorna nº de linhas de dados."""
    headers = [COLUMN_LABELS.get(col, col) for col in SHEET_COLUMNS]
    rows = [headers]
    for lead in leads_iter:
        row = []
        for col in SHEET_COLUMNS:
            val = getattr(lead, col, "") or ""
            if col == "linkedin_url" and val:
                row.append(f'=HYPERLINK("{val}";"Ver perfil")')
            else:
                row.append(val)
        rows.append(row)
    worksheet.update(rows, "A1", value_input_option="USER_ENTERED")
    return len(rows) - 1


def push_leads_to_sheet(
    leads: Optional[dict] = None,
    tab_name: Optional[str] = None,
) -> str:
    """
    Escreve leads na planilha Google Sheets.
    - Sempre atualiza a sheet1 ("Todos") com TODOS os leads do CSV (para aprovação).
    - Se tab_name for fornecido, cria (ou substitui) uma aba adicional com os leads
      passados em `leads` — usada para registrar os leads de cada coleta.
    - Cria a planilha se não existir e compartilha com SHEET_OWNER_EMAIL.
    - URL do LinkedIn vira hyperlink clicável ("Ver perfil").
    Retorna a URL da planilha.
    """
    client = _get_client()
    spreadsheet = _open_or_create_sheet(client)

    # ── Sempre atualiza sheet1 com TODOS os leads (para aprovação via dropdown) ──
    all_leads = load_leads()
    sheet1 = spreadsheet.sheet1
    # Renomeia sheet1 para "Todos" se ainda tiver nome padrão
    if sheet1.title in ("Sheet1", "Plan1", "Página1", "Folha1"):
        sheet1.update_title("Todos")
    sheet1.clear()
    num_rows = _write_leads_to_worksheet(sheet1, all_leads.values())
    if num_rows > 0:
        _apply_formatting(sheet1, num_rows)
    log.info(f"Sheet1 ('Todos') atualizada com {num_rows} leads.")

    # ── Cria aba da coleta se tab_name fornecido ───────────────────────────────
    if tab_name and leads is not None:
        try:
            ws_tab = spreadsheet.worksheet(tab_name)
            ws_tab.clear()
            log.info(f"Aba existente reutilizada: '{tab_name}'")
        except Exception:
            ws_tab = spreadsheet.add_worksheet(title=tab_name, rows=500, cols=NUM_COLS)
            log.info(f"Nova aba criada: '{tab_name}'")
        tab_rows = _write_leads_to_worksheet(ws_tab, leads.values())
        if tab_rows > 0:
            _apply_formatting(ws_tab, tab_rows)

    url = spreadsheet.url
    log.info(f"Planilha atualizada: {url}")
    return url


def pull_approved_from_sheet() -> list[Lead]:
    """
    Lê a planilha e retorna os leads com status 'approved'.
    Sincroniza o status de volta para o CSV local.
    """
    client = _get_client()
    try:
        spreadsheet = client.open(SHEET_NAME)
    except SpreadsheetNotFound:
        log.warning("Planilha não encontrada. Rode 'python main.py collect' primeiro.")
        return []

    worksheet = spreadsheet.sheet1

    # get_all_values() para não perder URLs que viraram fórmulas
    all_values = worksheet.get_all_values()
    if not all_values:
        return []

    header_row = all_values[0]
    label_to_field = {v: k for k, v in COLUMN_LABELS.items()}

    # Mapeia índice de coluna → campo interno
    col_map = {
        i: label_to_field.get(header_row[i], header_row[i])
        for i in range(len(header_row))
    }

    approved: list[Lead] = []
    local_leads = load_leads()

    for data_row in all_values[1:]:
        record = {col_map[i]: data_row[i] for i in range(len(data_row)) if i in col_map}

        status = str(record.get("status", "")).strip().lower()

        # URL pode ser fórmula =HYPERLINK("url","Ver perfil") ou URL pura
        raw_url = str(record.get("linkedin_url", "")).strip()
        if raw_url.startswith("=HYPERLINK"):
            # extrai a URL da fórmula
            import re
            m = re.search(r'HYPERLINK\("([^"]+)"', raw_url)
            url = m.group(1) if m else ""
        else:
            url = raw_url

        if not url:
            continue

        key = _normalize_url(url)

        # Sincroniza status da planilha → CSV local
        # PROTEÇÃO: nunca sobrescreve leads já enviados ou com falha.
        # Se o CSV diz "sent" e a planilha foi editada para "approved",
        # o CSV prevalece — esse lead não será prospectado de novo.
        IMMUTABLE_STATUSES = {"sent", "failed"}
        if key in local_leads:
            current_status = local_leads[key].status
            if current_status in IMMUTABLE_STATUSES:
                log.debug(f"Ignorando mudança de status para '{status}': {url} já está '{current_status}'")
            elif current_status != status:
                local_leads[key].status = status
                log.info(f"Status sincronizado: {url} → {status}")

        if status == "approved":
            lead = local_leads.get(key)
            # Segurança extra: só aprova quem ainda não foi enviado
            if lead and lead.status not in IMMUTABLE_STATUSES:
                approved.append(lead)

    save_leads(local_leads)
    log.info(f"{len(approved)} leads aprovados encontrados na planilha.")
    return approved
