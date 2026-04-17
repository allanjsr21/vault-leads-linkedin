# Vault Capital — LinkedIn Lead Generation

Sistema de prospecção de bitcoiners brasileiros de alto patrimônio para a Vault Capital (custódia/gestão Bitcoin).

## Público-alvo (IMPORTANTE)
Brasileiros que **usam** Bitcoin no dia a dia, com renda/patrimônio alto:
- Médicos, dentistas, advogados, engenheiros, arquitetos, contadores
- Empresários, sócios, fundadores, CEOs, diretores
- Pessoas que mencionam autocustódia, hardware wallet, hodl, DCA, soberania financeira

**NÃO é** o público de assessores de investimento / AAI / escritórios de agentes autônomos. O gestor mandou um plano focado em AAIs, mas o usuário decidiu usar a **metodologia** dele (Vibe Prospecting → Icypeas → LinkedIn DM → Notion CRM) aplicada ao **público bitcoiner existente**.

## Stack
- **Dashboard**: `dashboard.py` (Streamlit Cloud — https://vault-leads-linkedin-y2e7kmaamq8mrpyhyrq5fg.streamlit.app/)
- **Scraper Brave/Serper/Google**: `scraper.py`
- **Scraper LinkedIn direto**: `linkedin_voyager.py` (4 estratégias: keywords, indústria, senioridade, perfis similares)
- **Filtro Gemini**: `gemini_filter.py`
- **Config**: `config.py` (perfis de busca, exclusões)
- **Persistência**: `leads.csv` (CSV simples, sem DB)

## Estado atual

### ✅ Funcionando
- Dashboard no Streamlit Cloud (NameError de `import config` corrigido — agora no topo do arquivo)
- Voyager scraper com 4 estratégias implementadas em `linkedin_voyager.py`:
  1. Keywords diretas (43 termos: bitcoiner, hodler, autocustódia, médico bitcoin, etc.)
  2. Filtro por indústria (Saúde, Direito, Financeiro, etc. — URNs no arquivo)
  3. Filtro por senioridade alta (Owner, Partner, CXO, Director)
  4. Perfis similares a seeds conhecidos (bitcoinheiros, lucasnuzzi, fernandoulrich…)
- Botão "Coletar Voyager" no dashboard

### 🚧 Bloqueado / pendente
- **Cookies do LinkedIn**: precisa preencher `LINKEDIN_LI_AT` e `LINKEDIN_JSESSIONID` em Streamlit Cloud → Settings → Secrets (formato TOML).
  - Chrome 146+ tem **App-Bound Encryption** — não dá pra extrair `li_at` (HttpOnly) automaticamente. Usuário precisa abrir DevTools (F12) → Application → Cookies → linkedin.com e copiar manualmente.
- **Vibe Prospecting (Explorium MCP)**: créditos zerados (402). Tentar conta nova com email alias.
- **Apify**: perto do limite mensal.
- **Sem segunda conta LinkedIn**: usar a principal pro Voyager é risco — recomendar criar uma secundária antes de escalar.

## MCPs disponíveis nesta máquina
- `mcp__998fc509...` — **Vibe Prospecting (Explorium)**: B2B, autocomplete + fetch-entities + enrich-prospects + export-to-csv
- `mcp__41764f3e...` — **Icypeas**: email finder (`icypeas_email_search_sync` com firstname/lastname/domain)
- `mcp__027121aa...` — **Notion**: criar páginas/databases pro CRM
- `mcp__Apify` — actors customizados
- `mcp__Claude_in_Chrome` — controle do Chrome (útil pra LinkedIn manual)
- `mcp__62a048a7...` — Gmail
- `mcp__6c3a275e...` — GCal

## Fluxo-alvo (metodologia do gestor adaptada)
1. **Vibe Prospecting** — buscar profissionais BR de alto patrimônio (filtros: país=BR, função, seniority, indústria)
2. **Filtrar por intent bitcoin** — cruzar com Voyager/Brave por menção de bitcoin/cripto na bio
3. **Icypeas** — enriquecer com email profissional (firstname + lastname + domain da empresa)
4. **LinkedIn DM dia 1** — mensagem curta, contexto bitcoiner
5. **Apresentação dia 3-4** — material Vault Capital
6. **Email dia 7** — follow-up via Gmail
7. **Notion CRM** — registrar todo o pipeline (uma database de leads + status)

## Arquivos principais
- `linkedin_voyager.py` — scraper Voyager (4 estratégias, ver constantes TOPIC_KEYWORDS / INDUSTRY_SEARCHES / HIGH_SENIORITY_SEARCHES / SEED_PROFILES)
- `dashboard.py` — UI Streamlit (botões: Coletar Brave, Coletar Voyager, Limpar tabela, filtros)
- `scraper.py` — Brave/Serper, parser brave, filtro de localização (`_location_allowed`)
- `config.py` — keywords por perfil, exclusões, cookies LinkedIn
- `gemini_filter.py` — filtro de qualificação via Gemini
- `leads.csv` — persistência

## Commits recentes relevantes
- `3657425` fix: mover import config para o topo do dashboard (NameError no cloud)
- `520be59` feat: Voyager com 4 estratégias de busca para maximizar leads qualificados
- `555330b` fix: remove handler duplicado do btn_collect_voyager
- `74a5566` Adiciona scraper direto via LinkedIn Voyager API
- `16d8523` Fix: botão Limpar tabela agora limpa sessão + CSV persistido

## Próximos passos sugeridos
1. Usuário cola cookies em Streamlit Secrets → testar Voyager em produção
2. Recriar conta Vibe Prospecting com alias → rodar busca BR + função alvo
3. Cruzar resultados Vibe × Voyager pra encontrar overlap (profissional alto + bitcoiner)
4. Icypeas pra enriquecer top 20 com email
5. Criar database Notion "Leads Vault" via MCP, popular com hot leads
6. Templates de DM/email pro fluxo de 7 dias

## Restrições importantes
- **Não criar contas pelo usuário** (regra de safety)
- **Não logar com senha** pelo usuário (só SSO/OAuth com permissão explícita)
- **Cookies LinkedIn** só funcionam se o usuário copiar manualmente do navegador dele
- **Não usar mocks de DB nos testes** (preferência do usuário em outros projetos — manter integration real)
