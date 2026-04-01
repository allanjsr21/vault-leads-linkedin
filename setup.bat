@echo off
echo Instalando dependencias do agente LinkedIn Vault...
pip install -r requirements.txt
playwright install chromium
echo.
echo Instalacao concluida!
echo.
echo Proximos passos:
echo  1. Configure config.py com APIFY_API_TOKEN, LINKEDIN_EMAIL, LINKEDIN_PASSWORD
echo  2. Siga as instrucoes em sheets_manager.py para criar google_credentials.json
echo  3. Rode: python main.py collect
pause
