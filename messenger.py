"""
Módulo de envio de DMs no LinkedIn via Playwright.

Usa o SEU Chrome com o SEU perfil — já logado no LinkedIn.
Não precisa de senha nem de sessão separada.

IMPORTANTE: feche o Chrome completamente antes de rodar o agente.
            (Chrome não permite dois processos no mesmo perfil ao mesmo tempo)

Fluxo:
  1. Abre o Chrome usando seu perfil real (já logado no LinkedIn)
  2. Para cada lead aprovado: acessa o perfil → clica em "Mensagem" → envia DM
  3. Rate limiting: máximo MAX_DMS_PER_DAY por dia, delay aleatório entre envios
"""

import logging
import os
import random
import subprocess
import time

from playwright.sync_api import sync_playwright, Page, BrowserContext

from config import (
    CHROME_PROFILE_PATH,
    DELAY_BETWEEN_DMS,
    DM_TEMPLATE,
    MAX_DMS_PER_DAY,
)
from leads_manager import (
    Lead,
    count_sent_today,
    get_approved_leads,
    update_lead_status,
)

log = logging.getLogger(__name__)

LINKEDIN_BASE = "https://www.linkedin.com"


# ── Verificações ───────────────────────────────────────────────────────────────

def _chrome_is_running() -> bool:
    """Detecta se o Chrome está aberto (Windows)."""
    try:
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq chrome.exe"],
            capture_output=True, text=True
        )
        return "chrome.exe" in result.stdout
    except Exception:
        return False


def _is_logged_in(page: Page) -> bool:
    return "feed" in page.url or page.query_selector("nav.global-nav") is not None


# ── Envio de DM ────────────────────────────────────────────────────────────────

def _send_dm(page: Page, lead: Lead) -> bool:
    """
    Acessa o perfil do lead e envia uma DM personalizada.
    Retorna True se enviou com sucesso.
    """
    try:
        log.info(f"Acessando perfil: {lead.linkedin_url}")
        page.goto(lead.linkedin_url, wait_until="domcontentloaded", timeout=30_000)
        page.wait_for_timeout(random.randint(2000, 4000))

        # Botão "Mensagem" / "Message" na seção de ações do perfil
        msg_button = page.query_selector(
            ".pvs-profile-actions button:has-text('Mensagem'), "
            ".pvs-profile-actions button:has-text('Message'), "
            "button:has-text('Mensagem'), "
            "button:has-text('Message')"
        )

        if not msg_button:
            log.warning(f"  Botão de mensagem não encontrado: {lead.linkedin_url}")
            return False

        msg_button.click()
        page.wait_for_timeout(random.randint(1500, 3000))

        # Caixa de texto da mensagem
        text_box = page.query_selector(
            ".msg-form__contenteditable, [contenteditable='true']"
        )
        if not text_box:
            log.warning(f"  Caixa de texto não encontrada: {lead.linkedin_url}")
            return False

        message = DM_TEMPLATE.format(first_name=lead.first_name or lead.name)
        text_box.click()
        page.wait_for_timeout(500)

        # Digita simulando comportamento humano
        for char in message:
            text_box.type(char, delay=random.randint(10, 40))

        page.wait_for_timeout(random.randint(1000, 2000))

        # Botão de enviar
        send_button = page.query_selector(
            "button.msg-form__send-button, "
            "button[type='submit']:has-text('Enviar'), "
            "button[type='submit']:has-text('Send')"
        )
        if not send_button:
            log.warning(f"  Botão de enviar não encontrado: {lead.linkedin_url}")
            return False

        send_button.click()
        page.wait_for_timeout(random.randint(2000, 4000))

        log.info(f"  DM enviada para {lead.name}")
        return True

    except Exception as e:
        log.error(f"  Erro ao enviar para {lead.name}: {e}")
        return False


# ── Orquestrador principal ─────────────────────────────────────────────────────

def run_messenger(dry_run: bool = False) -> None:
    """
    Envia DMs para todos os leads com status 'approved'.
    dry_run=True: simula sem enviar de verdade.
    """
    sent_today = count_sent_today()
    remaining_quota = MAX_DMS_PER_DAY - sent_today

    if remaining_quota <= 0:
        print(f"  Limite diário atingido ({MAX_DMS_PER_DAY} DMs/dia). Tente amanhã.")
        return

    leads = get_approved_leads()
    if not leads:
        print("  Nenhum lead com status 'approved' encontrado.")
        print("  Abra a planilha e mude 'pending' → 'approved' nos leads desejados.")
        return

    # Proteção extra: remove quem já foi enviado
    leads = [l for l in leads if l.status != "sent"]
    if not leads:
        print("  Todos os leads aprovados já foram prospectados anteriormente.")
        return

    leads_to_send = leads[:remaining_quota]
    print(f"\n  Enviando DMs para {len(leads_to_send)} leads (quota restante hoje: {remaining_quota})")

    if dry_run:
        print("  [DRY RUN] Nenhuma mensagem será enviada.\n")
        for lead in leads_to_send:
            msg = DM_TEMPLATE.format(first_name=lead.first_name or lead.name)
            print(f"  → {lead.name} ({lead.linkedin_url})")
            print(f"     {msg[:100]}...\n")
        return

    # Avisa se Chrome estiver aberto
    if _chrome_is_running():
        print("\n  AVISO: O Chrome parece estar aberto.")
        print("  Feche o Chrome completamente e pressione ENTER para continuar...")
        input()
        if _chrome_is_running():
            print("  Chrome ainda está aberto. Encerrando.")
            return

    if not os.path.exists(CHROME_PROFILE_PATH):
        print(f"  Perfil do Chrome não encontrado em: {CHROME_PROFILE_PATH}")
        print("  Verifique o caminho em CHROME_PROFILE_PATH no config.py")
        return

    with sync_playwright() as p:
        # Abre o Chrome com o perfil real do usuário
        # channel="chrome" usa o Chrome instalado, não o Chromium do Playwright
        context: BrowserContext = p.chromium.launch_persistent_context(
            user_data_dir=CHROME_PROFILE_PATH,
            channel="chrome",
            headless=False,
            args=["--start-maximized"],
        )

        page: Page = context.pages[0] if context.pages else context.new_page()

        try:
            page.goto(f"{LINKEDIN_BASE}/feed", wait_until="domcontentloaded", timeout=30_000)

            if not _is_logged_in(page):
                print("\n  Não está logado no LinkedIn.")
                print("  Faça login manualmente no browser que abriu e pressione ENTER...")
                input()
                if not _is_logged_in(page):
                    print("  Login não detectado. Encerrando.")
                    return

            print("  Logado no LinkedIn com sucesso.\n")

            sent = 0
            for i, lead in enumerate(leads_to_send):
                print(f"  [{i+1}/{len(leads_to_send)}] {lead.name} — {lead.linkedin_url}")

                success = _send_dm(page, lead)

                if success:
                    update_lead_status(lead.linkedin_url, "sent")
                    sent += 1
                else:
                    update_lead_status(lead.linkedin_url, "failed", "Botão não encontrado ou erro")

                if i < len(leads_to_send) - 1:
                    delay = random.randint(*DELAY_BETWEEN_DMS)
                    print(f"     Aguardando {delay}s antes da próxima DM...")
                    time.sleep(delay)

        finally:
            context.close()

    print(f"\n  Concluído: {sent}/{len(leads_to_send)} DMs enviadas.")
    print(f"  DMs enviadas hoje: {count_sent_today()}/{MAX_DMS_PER_DAY}")


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    dry = "--dry-run" in sys.argv
    run_messenger(dry_run=dry)
