# Changes

## 1. Migração do banco de dados: SQLite+git_sync → Supabase

**Problema:** o app (Streamlit) usava SQLite (`Dataset/postos.db`) com um
sync automático para o GitHub via `services/git_sync.py` — um workaround
necessário porque o disco do Streamlit Community Cloud é efêmero. Isso trazia
fragilidade: token PAT exposto nos secrets, risco de conflito de push,
complexidade desnecessária.

**Solução:** arquitetura substituída por Supabase (Postgres gerenciado). A
tabela `postos` (schema `public`) passou a ser a fonte de dados primária,
acessada via `services/supabase_client.py` (autenticação por service_role
key, lida de `.streamlit/secrets.toml`, seção `[supabase]`). O
`services/git_sync.py` foi removido — não é mais necessário, pois o Postgres
já é persistente.

**Arquivos-chave da nova arquitetura:**
- [services/supabase_client.py](services/supabase_client.py) — client
  singleton (`st.cache_resource`) + paginação de leituras (`fetch_all_rows`,
  blocos de 1000 linhas, limite do PostgREST).
- [services/data_loader.py](services/data_loader.py) /
  [services/data_writer.py](services/data_writer.py) — leitura/escrita na
  tabela `postos`, traduzindo entre o contrato histórico da planilha Excel
  (`core.config.RawColumns`) e as colunas snake_case do banco
  (`core.config.Columns`) via `RAW_TO_DB_COLUMNS` / `DB_TO_RAW_COLUMNS`.
- `db_migrations/migrations/20260720120000_create_postos_table.sql` — DDL da
  tabela (idempotente, `CREATE TABLE IF NOT EXISTS`, sem DROP).
- `scripts/migrate_excel_to_supabase.py` — popula a tabela a partir do Excel
  original, reaproveitando `insert_bulk_records`.

**Decisões confirmadas pelo usuário:** usar service_role key (não
anon+RLS), nomenclatura snake_case no banco, remover `git_sync.py`; dados
históricos foram importados depois via planilha Excel (92 linhas), não
migrados automaticamente do `postos.db` local.

**Armadilha descoberta:** a pasta de migrations SQL não pode se chamar
`supabase/` na raiz do projeto — colide com o pacote pip `supabase`
(namespace package shadowing) e quebra `from supabase import create_client`.
Por isso o diretório é `db_migrations/migrations/`, e não
`supabase/migrations/` (convenção padrão da Supabase CLI, mas inviável
aqui).

**Como aplicar/configurar:** preencher `.streamlit/secrets.toml`
(`[supabase]` → `url`, `service_role_key`) a partir de
`.streamlit/secrets.toml.example`, e garantir que a migration em
`db_migrations/migrations/` já rodou no Supabase Dashboard → SQL Editor
antes do primeiro `streamlit run`.

## 2. Cor do rótulo "Média" ilegível nos gráficos

**Problema:** o rótulo com o valor da média (markLine) usava a cor do tema
(`Theme.ACCENT_SOFT` / `Theme.NEUTRAL`) sobre um fundo quase branco
(`rgba(240,253,249,...)`), ficando praticamente invisível.

**Correção:** cor do texto trocada para `#1a1a1a` (preto forte) em ambos os
gráficos.

- [ui/components/charts.py](ui/components/charts.py) — `build_evolution_chart`
  (label da média no gráfico de evolução)
- [ui/components/charts.py](ui/components/charts.py) — `build_absenteismo_ranking_chart`
  (label da média no gráfico de ranking de absenteísmo)

## 3. Cor dos pontos (verde/vermelho) invertida para indicadores negativos

**Problema:** os pontos do gráfico de evolução eram coloridos por
`trend_color`, que sempre pinta de verde quando o valor sobe e de vermelho
quando cai. Isso é correto para indicadores "positivos" (ex.: efetivos,
trabalhados, contratações), mas confunde a leitura em indicadores onde
**subir é ruim**: absenteísmo, ausência e demissões — nesses casos, queda é
que representa melhora.

**Correção:** adicionada inversão de cor, aplicada somente ao gráfico de
evolução e somente para esses três indicadores.

- [core/utils.py](core/utils.py) — `trend_color(delta, invert=False)` passou
  a aceitar o parâmetro `invert`; quando `True`, alta = vermelho e queda =
  verde. Retrocompatível (default `False` preserva o comportamento antigo).
- [ui/components/charts.py](ui/components/charts.py) — `build_evolution_chart`
  passou a aceitar `invert_trend: bool = False`, repassado ao cálculo da cor
  de cada ponto da série principal.
- [ui/layout.py](ui/layout.py) — novo conjunto
  `_INDICADORES_INVERTIDOS = {"absenteismo", "ausencia", "demissoes"}`;
  `render_weekly_tab` e `render_monthly_tab` passam
  `invert_trend=(indicator_key in _INDICADORES_INVERTIDOS)` ao montar o
  gráfico de evolução.
- [ui/components/charts.py](ui/components/charts.py) — a cor da variação
  exibida no **tooltip** (`varColor`, no JS `formatter_js`) tinha a mesma
  lógica fixa e ficou esquecida na primeira correção; agora recebe o
  placeholder `__INVERT_TREND__` (substituído por `true`/`false` conforme
  `invert_trend`) e também inverte verde/vermelho junto com os pontos do
  gráfico.

Indicadores não afetados (mantêm alta = verde): `efetivos`, `trabalhados`,
`contratacoes`.
