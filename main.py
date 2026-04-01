"""
Agente de leads da Vault Capital no LinkedIn.

Uso:
  python main.py collect        - Fase 1: coleta leads e publica no Google Sheets
  python main.py send           - Fase 2: le aprovados do Sheets e envia DMs
  python main.py send --dry-run - Simula envio sem enviar de verdade
  python main.py sync           - Sincroniza status do Sheets para o CSV local
  python main.py status         - Mostra resumo dos leads
"""

import logging
import sys
import webbrowser

# Forca UTF-8 no terminal Windows para evitar UnicodeEncodeError
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("agent.log", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)


def select_audience_profile() -> dict:
    """Exibe menu e retorna o perfil de publico escolhido."""
    import config
    profiles = config.AUDIENCE_PROFILES

    print("\n" + "="*55)
    print("  VAULT CAPITAL — SELECIONE O PUBLICO-ALVO")
    print("="*55)
    for key, profile in profiles.items():
        print(f"\n  [{key}] {profile['name']}")
        print(f"      {profile['description']}")
    print()

    while True:
        choice = input("  Digite o numero do perfil (1 ou 2): ").strip()
        if choice in profiles:
            profile = profiles[choice]
            print(f"\n  Perfil selecionado: {profile['name']}")
            print("="*55)
            return profile
        print("  Opcao invalida. Digite 1 ou 2.")


def apply_profile(profile: dict) -> None:
    """Aplica o perfil escolhido nas variaveis do config."""
    import config
    config.SEARCH_KEYWORDS = profile["keywords"]
    config.SHEET_NAME = profile["sheet_name"]
    config.LEADS_CSV = profile["leads_csv"]
    config.DM_TEMPLATE = profile["dm_template"]


def cmd_collect() -> None:
    import config
    from scraper import search_by_keywords, search_by_post_engagement
    from sheets_manager import push_leads_to_sheet

    profile = select_audience_profile()
    apply_profile(profile)

    # Recarrega leads_manager com o CSV correto do perfil
    import leads_manager
    leads_manager.LEADS_CSV = config.LEADS_CSV

    from leads_manager import add_leads, load_leads, print_summary

    print(f"\n  Buscando perfis: {profile['name']}...")
    keyword_leads = search_by_keywords()
    print(f"   -> {len(keyword_leads)} perfis encontrados")

    print("\n  Coletando engajamento em posts...")
    engagement_leads = search_by_post_engagement()
    print(f"   -> {len(engagement_leads)} perfis encontrados")

    all_leads = keyword_leads + engagement_leads
    added, dupes = add_leads(all_leads)
    print(f"\n  {added} leads novos adicionados ({dupes} duplicatas ignoradas)")

    print_summary()

    print("  Publicando no Google Sheets...")
    try:
        sheet_url = push_leads_to_sheet(load_leads())
        print(f"\n  Planilha criada/atualizada: {profile['sheet_name']}")

        print("\n" + "="*55)
        print("  PROXIMO PASSO — SUA REVISAO E OBRIGATORIA")
        print("="*55)
        print(f"\n  Acesse a planilha:")
        print(f"  {sheet_url}")
        print()
        print("  Na coluna 'Status', use o dropdown para marcar:")
        print("    approved -> quer enviar DM para essa pessoa")
        print("    skipped  -> nao quer contatar")
        print()
        print("  Apos revisar, rode: python main.py send")
        print("="*55 + "\n")

        try:
            webbrowser.open(sheet_url)
        except Exception:
            pass

    except Exception as e:
        log.error(f"Erro ao publicar no Sheets: {e}")
        print(f"\n  Leads salvos localmente em: {config.LEADS_CSV}")


def cmd_send(dry_run: bool = False) -> None:
    import config
    from messenger import run_messenger
    from sheets_manager import pull_approved_from_sheet

    profile = select_audience_profile()
    apply_profile(profile)

    import leads_manager
    leads_manager.LEADS_CSV = config.LEADS_CSV

    from leads_manager import print_summary

    print("\n" + "="*55)
    print("  VAULT CAPITAL — ENVIO DE DMs (FASE 2)")
    if dry_run:
        print("  [MODO SIMULACAO]")
    print("="*55 + "\n")

    print("  Lendo aprovados do Google Sheets...")
    try:
        approved = pull_approved_from_sheet()
        print(f"  {len(approved)} leads aprovados encontrados.\n")
    except Exception as e:
        log.warning(f"Nao foi possivel ler do Sheets: {e}")
        print("  (Usando CSV local como fallback)\n")

    run_messenger(dry_run=dry_run)
    print_summary()


def cmd_sync() -> None:
    import config
    from sheets_manager import pull_approved_from_sheet

    profile = select_audience_profile()
    apply_profile(profile)

    import leads_manager
    leads_manager.LEADS_CSV = config.LEADS_CSV

    from leads_manager import print_summary

    print("\n  Sincronizando status do Google Sheets...")
    try:
        approved = pull_approved_from_sheet()
        print(f"  {len(approved)} leads aprovados sincronizados.")
        print_summary()
    except Exception as e:
        print(f"  Erro ao sincronizar: {e}")


def cmd_status() -> None:
    import config

    profile = select_audience_profile()
    apply_profile(profile)

    import leads_manager
    leads_manager.LEADS_CSV = config.LEADS_CSV

    from leads_manager import print_summary
    print_summary()


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "collect":
        cmd_collect()
    elif command == "send":
        dry = "--dry-run" in sys.argv
        cmd_send(dry_run=dry)
    elif command == "sync":
        cmd_sync()
    elif command == "status":
        cmd_status()
    else:
        print(f"Comando invalido: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
