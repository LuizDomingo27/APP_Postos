# Gestão de Postos de Trabalho 🧵

Dashboard em **Python + Streamlit** para acompanhamento de efetivos,
produtividade, contratações/demissões e absenteísmo nas oficinas
parceiras, a partir da planilha de controle (`Dataset/POSTOS.xlsx`).

---

## 1. Como executar

```bash
# 1. Criar e ativar um ambiente virtual (recomendado)
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Rodar a aplicação
streamlit run app.py
```

A planilha de origem já está em `Dataset/POSTOS.xlsx`. Para usar uma
planilha atualizada, basta substituir esse arquivo mantendo o mesmo
nome de aba (`Planilha1`) e as mesmas colunas.

---

## 2. Arquitetura

O projeto segue uma **arquitetura em camadas**, separando regra de
negócio de apresentação — o mesmo padrão usado nos demais projetos
internos:

```
APP_PostosTrabalho/
├── app.py                       # Ponto de entrada — apenas orquestra
├── .streamlit/
│   └── config.toml              # Tema dark fixo (todas as plataformas)
├── core/
│   ├── config.py                # Constantes: colunas, cores, indicadores
│   └── utils.py                 # Helpers genéricos (formatação, % , cor)
├── services/                     # Regra de negócio (sem Streamlit aqui)
│   ├── data_loader.py            # Leitura + validação da planilha bruta
│   ├── data_cleaning.py          # Normalização e regras de qualidade
│   ├── indicators_service.py     # Cálculo dos KPIs (cards)
│   └── analytics_service.py      # Séries semanais/mensais + variação %
├── ui/                           # Apresentação (Streamlit)
│   ├── styles.py                 # CSS do tema (dark + verde-ciano neon)
│   ├── layout.py                 # Orquestra header, cards e abas
│   └── components/
│       ├── cards.py               # Cards de KPI (HTML/CSS)
│       ├── filters.py             # Filtros da sidebar (select_all_popover)
│       └── charts.py              # Gráficos de linha (Plotly)
├── Dataset/
│   └── POSTOS.xlsx
├── requirements.txt
└── README.md
```

**Regra de dependência:** `ui` pode chamar `services` e `core`;
`services` pode chamar `core`; `core` não depende de nada do projeto.
Isso garante que a lógica de negócio (`services/`) possa ser testada ou
reaproveitada (ex.: em um script de relatório, ou outra interface) sem
precisar do Streamlit.

---

## 3. Indicadores (KPIs)

| Indicador | Fórmula |
|---|---|
| Total de Efetivos | `soma(QTD Efetivos)` no recorte filtrado |
| Total Trabalhados | `soma(QTD Trabalhados)` no recorte filtrado |
| Total de Contratações | `soma(Contratação)` no recorte filtrado |
| Total de Demissões | `soma(Demissão)` no recorte filtrado |
| Taxa de Absenteísmo | `(Total Efetivos − Total Trabalhados) / Total Efetivos × 100` |

Cada card também mostra a **variação percentual da última semana em
relação à anterior**, dentro do recorte de filtros aplicado.

Os gráficos de evolução (abas "Evolução Semanal" e "Evolução Mensal")
aplicam a mesma lógica de agregação, mas ponto a ponto ao longo do
tempo, e exibem:
- a série do indicador (linha + marcadores, coloridos por tendência);
- uma linha pontilhada com a **média** do período filtrado;
- a **variação percentual** entre cada ponto e o anterior (no hover de
  cada marcador, e em destaque no último ponto da série).

> **Importante sobre o mês de referência:** o período mensal usado nos
> gráficos é sempre derivado da coluna `Data Efetivos` (consistente em
> toda a base), e não de `Data Trabalhados` — ver seção 5.

---

## 4. Tema visual

- **Tema fixo em dark mode com verde-ciano neon suave** (`#3FE0C5`),
  independente do tema do sistema operacional do usuário — configurado
  em `.streamlit/config.toml` (`[theme] base = "dark"`).
- CSS customizado em `ui/styles.py`, usando **CSS Custom Properties**
  espelhando a paleta de `core/config.py::Theme` (mudar a cor em um
  lugar exige replicar no outro — ver comentário no topo do arquivo).
- Tipografia: **Sora** (títulos/destaques) + **Inter** (corpo de
  texto), carregadas via Google Fonts.
- Layout responsivo: os cards de KPI usam CSS Grid com
  `repeat(auto-fit, minmax(...))`, reorganizando automaticamente o
  número de colunas conforme a largura da tela (desktop → mobile),
  sem depender de `st.columns` fixo.

---

## 5. Notas de qualidade de dados

A planilha de origem apresenta algumas inconsistências tratadas na
camada `services/data_cleaning.py`. Ficam documentadas aqui para
facilitar manutenção futura (e para não serem "re-descobertas" do
zero):

1. **Categorias de MP duplicadas por acentuação** — `"POLÓ"` e
   `"POLO"` representam a mesma matéria-prima e são normalizadas para
   `"POLO"` (`core/config.py::MP_NORMALIZATION_MAP`).
2. **Categorias de Frete com espaços extras** — ex.: `"MANSOUR "` vs
   `"MANSOUR"`. Resolvido com `.strip()` em todas as colunas de texto.
3. **Valores nulos em `QTD Efetivos` (77 linhas) e `QTD Trabalhados`
   (120 linhas)** — tratados como `0` (ausência de lançamento naquela
   semana/oficina), para não quebrar somas e médias.
4. **Data sentinela inválida em `Data Trabalhados`** — todas as 116
   linhas da Semana 31 trazem `31/12/1990` nessa coluna (claramente um
   valor padrão/erro de preenchimento na planilha de origem). Por isso,
   **`Data Trabalhados` nunca é usada para derivar período/mês** — o
   mês de referência vem sempre de `Data Efetivos`, que é consistente
   (uma única data por número de semana, sem essa anomalia).
5. **Semana 50 com volume de linhas fora do padrão** — outras semanas
   têm ~116 linhas; a Semana 50 (12/12/2025) tem 226. **Não é
   duplicidade**: algumas oficinas produzem mais de uma matéria-prima
   (ex.: "DI3 CONFECCOES LTDA" tem uma linha para JEANS e outra para
   MALHA), então aparecem mais de uma vez naquela semana. Isso já era
   somado corretamente nos KPIs, mas agora também fica visível na
   interface — ver coluna `oficina_mp` abaixo.
6. **Identificação Oficina + MP** — para deixar claro quando uma mesma
   oficina tem mais de um lançamento por semana (regra 5), foi criada a
   coluna derivada `oficina_mp`, no formato `"<Oficina> <MP>"` (ex.:
   `"DI3 CONFECCOES LTDA Malha"`, `"DI3 CONFECCOES LTDA Jeans"`). Esse
   rótulo é usado no filtro de Oficinas da sidebar e no ranking da aba
   "🏭 Oficinas".

Um resumo desses pontos também aparece em runtime no expander
**"📋 Notas de qualidade dos dados"**, na sidebar da aplicação.

---

## 6. Decisões e observações sobre o escopo

- **Filtros na sidebar**: Matéria-prima (MP), Oficinas (rotuladas como
  `Oficina + MP`, ver seção 5.6) e intervalo de Semanas — usando um
  padrão de popover com "Selecionar todos / Limpar seleção"
  (`ui/components/filters.py::select_all_popover`), em vez do
  `st.multiselect` padrão, para ficar compacto mesmo com 142 combinações
  de oficina/MP cadastradas.
- **Coluna `Frete`** existe na planilha de origem mas não fazia parte
  das colunas de análise solicitadas — foi mantida na limpeza dos
  dados (normalizada) para uso futuro, mas não é usada em filtros nem
  KPIs no momento.
- **Aba extra "🏭 Oficinas"**: adicionada como valor agregado ao
  escopo original — uma tabela ordenável com os mesmos indicadores por
  oficina, ranqueada por absenteísmo, para ajudar a identificar pontos
  de atenção entre as 100+ oficinas. Pode ser removida facilmente
  (bastando excluir a chamada em `app.py`) se não for desejada.

---

## 7. Possíveis melhorias futuras

- **Testes automatizados**: os módulos em `services/` não dependem do
  Streamlit, então são fáceis de testar com `pytest` isoladamente
  (ex.: `compute_kpis`, `weekly_evolution`, `clean_dataframe`).
- **Exportação**: botão de download (Excel/CSV) do recorte filtrado ou
  do ranking de oficinas, reaproveitando o padrão de exportação já
  usado no `sistema_ajustes_app`.
- **Múltiplas fontes de dados**: se a planilha crescer ou vier a ser
  substituída por um banco de dados, apenas `services/data_loader.py`
  precisa mudar — o restante da aplicação não é afetado.
- **Drill-down por oficina**: clicar em uma oficina no ranking e ver a
  evolução semanal isolada daquela oficina (reaproveitando
  `ui/components/charts.py`).
- **Cache incremental**: hoje o `@st.cache_data` recarrega tudo quando
  o arquivo muda; para planilhas muito grandes, vale considerar leitura
  incremental ou uma base intermediária (parquet/SQLite).
