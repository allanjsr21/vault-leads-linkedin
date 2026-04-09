# HANDOFF — Estado exato da sessão (2026-04-09)

> Leia primeiro o `CLAUDE.md` pra contexto geral. Este arquivo é o **estado momentâneo** de onde paramos.

## O que acabamos de fazer
1. Reescrevi `linkedin_voyager.py` com 4 estratégias (keywords, indústria, senioridade, perfis similares).
2. Corrigi NameError em `dashboard.py` (movi `import config` pro topo). Commit `3657425`, já em produção no Streamlit Cloud.
3. Tentei extrair cookies do LinkedIn automaticamente — **falhou**, Chrome 146 tem App-Bound Encryption. Cookies HttpOnly (`li_at`) não são acessíveis nem via `document.cookie` nem via `browser_cookie3` nem via leitura direta do SQLite (perfis ativos ficam locked).
4. Testei Vibe Prospecting (Explorium MCP) — funcionou e trouxe 17 perfis, **mas eram assessores de investimento (AAIs)**, público errado. Conta esgotou créditos (402 Payment Required) na segunda chamada.
5. Testei Icypeas em paralelo nesses 17 — voltou 3 emails profissionais válidos, 2 erros de "Cannot read properties of undefined (reading 'length')" (provavelmente sem email encontrado).
6. Usuário esclareceu o público correto: **bitcoiners brasileiros de alto patrimônio**, não AAIs. Quer aplicar a metodologia do gestor (Vibe → Icypeas → LinkedIn → Notion) ao público existente do sistema.
7. Criei `CLAUDE.md` com o contexto do projeto.

## Bloqueios ativos AGORA
| Bloqueio | Ação necessária | Quem resolve |
|---|---|---|
| Cookies LinkedIn não estão em Streamlit Secrets | Usuário abrir DevTools (F12) → Application → Cookies → linkedin.com → copiar `li_at` e `JSESSIONID` → colar em https://share.streamlit.io → vault-leads-linkedin → Settings → Secrets (formato TOML abaixo) | **Usuário** |
| Vibe Prospecting com créditos zerados | Criar conta nova com email alias | **Usuário** (Claude não cria contas) |
| Apify perto do limite mensal | Criar conta nova com email alias | **Usuário** |
| Sem segunda conta LinkedIn pro Voyager | Criar antes de escalar pra evitar risco da conta principal | **Usuário** |

### Formato dos Streamlit Secrets
```toml
LINKEDIN_LI_AT = "AQEDA..."
LINKEDIN_JSESSIONID = "ajax:1234567890"
```

## Próxima ação concreta (quando voltar)
**Pergunta pro usuário**: "Você já colou os cookies do LinkedIn no Streamlit Secrets? E criou conta nova do Vibe Prospecting?"

- **Se sim pros cookies**: testar Voyager em produção pelo botão "Coletar Voyager" no dashboard. Confirmar que as 4 estratégias rodam.
- **Se sim pro Vibe novo**: rodar busca correta com filtros para o público bitcoiner:
  - País: Brasil
  - Funções: Médicos, Dentistas, Advogados, Engenheiros, Empresários, CEOs, Diretores
  - Indústrias de alto patrimônio (Saúde, Direito, Financeiro, TI, Imobiliário)
  - Cruzar resultados com Voyager por menção de bitcoin/cripto na bio
- **Se ambos não**: continuar dependendo só do scraper Brave/Serper atual e refinar keywords no `config.py`.

## Tarefas pendentes (do plano do gestor adaptado)
- [ ] Cookies LinkedIn → Streamlit Secrets
- [ ] Vibe Prospecting conta nova → busca BR + funções de alto patrimônio
- [ ] Cruzar Vibe × Voyager → overlap (profissional alto + bitcoiner)
- [ ] Icypeas enriquecer top 20 com email profissional
- [ ] Criar database Notion "Leads Vault" via `mcp__027121aa...notion-create-database`
- [ ] Popular Notion com hot leads
- [ ] Templates de DM LinkedIn (dia 1) e email (dia 7) para bitcoiners
- [ ] Sequência de follow-up (DM dia 1 → apresentação dia 3-4 → email dia 7)

## Decisões já tomadas (não revisitar)
- **Público é bitcoiner brasileiro de alto patrimônio**, não AAI. Confirmado pelo usuário.
- **Metodologia do gestor sim, público dele não.**
- **Voyager scraper com 4 estratégias** é a abordagem certa pro LinkedIn direto.
- **Streamlit Cloud** é o deploy (não local).
- **CSV (`leads.csv`)** é a persistência, sem DB.
- **Não criar contas pelo usuário** (regra de safety, mesmo se ele pedir).
- **Não usar senha do usuário** pra logar (só SSO/OAuth com permissão explícita).

## Transcrição completa da sessão anterior
Se precisar de detalhes específicos de antes da compactação:
`C:\Users\allan\.claude\projects\C--Users-allan-linkedin\8cdfe9c8-5882-4364-b0b1-f0524b47f8dd.jsonl`

## Como retomar de outra conta Claude
1. Abrir Claude Code na pasta `C:\Users\allan\linkedin`
2. `CLAUDE.md` carrega automaticamente
3. Mandar pro Claude novo: **"Leia o HANDOFF.md e me diga qual o próximo passo"**
4. Garantir que os MCPs estão instalados (`claude mcp list` deve mostrar Vibe Prospecting, Icypeas, Notion, Apify, etc.)
