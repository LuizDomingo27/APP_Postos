"""
core/config.py
----------------
Configurações centrais da aplicação: caminhos, nomes de colunas,
paleta de cores do tema e metadados dos indicadores.

Manter TODAS as constantes "mágicas" aqui evita números/strings
espalhados pelo código e facilita manutenção futura (ex.: troca de
fonte de dados, ajuste de paleta de cores, novo indicador).
"""

from __future__ import annotations

from pathlib import Path
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Caminhos
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
DATASET_PATH = BASE_DIR / "Dataset" / "POSTOS.xlsx"
DATASET_SHEET_NAME = "Planilha1"
DB_PATH = BASE_DIR / "Dataset" / "postos.db"

# ---------------------------------------------------------------------------
# Metadados da aplicação
# ---------------------------------------------------------------------------
APP_TITLE = "Gestão de Postos de Trabalho"
APP_ICON = "🧵"
APP_SUBTITLE = "Acompanhamento de efetivos, produtividade e absenteísmo por oficina"

# ---------------------------------------------------------------------------
# Nomes das colunas BRUTAS, exatamente como vêm da planilha original.
# Centralizar aqui é o que permite que, se a planilha mudar o nome de uma
# coluna, o ajuste seja feito em UM único lugar.
# ---------------------------------------------------------------------------
class RawColumns:
    FRETE = "Frete"
    MP = "MP"
    OFICINA = "Oficinas"
    DATA_EFETIVOS = "Data Efetivos"
    QTD_EFETIVOS = "QTD Efetivos"
    DATA_TRABALHADOS = "Data Trabalhados"
    QTD_TRABALHADOS = "QTD Trabalhados"
    CONTRATACAO = "Contratatação"
    DEMISSAO = "Demissão"
    SEMANA = "Semana"


# ---------------------------------------------------------------------------
# Nomes das colunas já PADRONIZADAS (snake_case), usadas internamente em
# todo o restante da aplicação a partir da camada de limpeza de dados.
# ---------------------------------------------------------------------------
class Columns:
    FRETE = "frete"
    MP = "mp"
    OFICINA = "oficina"
    DATA_EFETIVOS = "data_efetivos"
    QTD_EFETIVOS = "qtd_efetivos"
    DATA_TRABALHADOS = "data_trabalhados"
    QTD_TRABALHADOS = "qtd_trabalhados"
    CONTRATACOES = "contratacoes"
    DEMISSOES = "demissoes"
    SEMANA = "semana"
    ANO_MES = "ano_mes"          # derivado: período mensal (YYYY-MM)
    MES_LABEL = "mes_label"      # derivado: rótulo amigável do mês
    OFICINA_MP = "oficina_mp"    # derivado: "<Oficina> <MP>", ex.: "DI3 CONFECCOES LTDA Malha"
    ANO = "ano"                  # derivado: ano da data de efetivos (YYYY)


# ---------------------------------------------------------------------------
# Indicadores (KPIs)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class IndicatorMeta:
    key: str
    label: str
    column: str | None   # None para indicadores calculados (ex.: absenteísmo)
    icon: str
    is_percentage: bool = False


# O campo `icon` é mantido por compatibilidade da dataclass, mas fica vazio:
# a identidade visual dos cards é feita pelo símbolo tipográfico ✦ (ver
# ui/components/cards.py), sem emojis — alinhado ao design text-only.
INDICATORS: dict[str, IndicatorMeta] = {
    "efetivos": IndicatorMeta("efetivos", "Total de Efetivos", Columns.QTD_EFETIVOS, ""),
    "trabalhados": IndicatorMeta("trabalhados", "Total Trabalhados", Columns.QTD_TRABALHADOS, ""),
    "ausencia": IndicatorMeta("ausencia", "Total de Ausências", None, ""),
    "contratacoes": IndicatorMeta("contratacoes", "Total de Contratações", Columns.CONTRATACOES, ""),
    "demissoes": IndicatorMeta("demissoes", "Total de Demissões", Columns.DEMISSOES, ""),
    "absenteismo": IndicatorMeta("absenteismo", "Taxa de Absenteísmo", None, "", is_percentage=True),
}

# Ordem de exibição dos cards de KPI
KPI_ORDER = ["efetivos", "trabalhados", "ausencia", "contratacoes", "demissoes", "absenteismo"]

# ---------------------------------------------------------------------------
# Paleta de cores — tema claro (light) alinhado ao padrao do SO
# ---------------------------------------------------------------------------
class Theme:
    BG_PRIMARY = "#FFFFFF"          # fundo principal (branco)
    BG_SECONDARY = "#F0FDF9"        # fundo de sidebar / superficies
    CARD_BG = "#FFFFFF"             # fundo dos cards
    CARD_BORDER = "rgba(46,230,192,0.35)"  # borda teal suave

    ACCENT = "#18C99E"              # teal principal
    ACCENT_SOFT = "rgba(46,230,192,0.18)"  # teal muito suave (fundos)
    ACCENT_GLOW = "rgba(46,230,192,0.22)"  # glow radial dos cards

    POSITIVE = "#18C99E"            # positivo — teal
    NEGATIVE = "#D93025"            # negativo — vermelho semantico
    NEUTRAL = "#5E8B83"             # neutro / sem dado

    TEXT_PRIMARY = "#0D2B26"        # texto principal (verde-escuro quase preto)
    TEXT_MUTED = "#5E8B83"          # texto secundario

    FONT_HEADING = "'Sora', sans-serif"
    FONT_BODY = "'Inter', sans-serif"


# ---------------------------------------------------------------------------
# Outras constantes de negócio
# ---------------------------------------------------------------------------
# Mapeamento de normalização de categorias da coluna MP que vêm com
# inconsistências de digitação/acentuação na planilha de origem
# (ex.: "POLÓ" e "POLO" representam a mesma matéria-prima).
MP_NORMALIZATION_MAP = {
    "POLÓ": "POLO",
}

# Linhas cujo valor de "Data Trabalhados" é uma data sentinela/inválida
# vinda da planilha de origem (ex.: 1990-12-31). Não confiável para
# cálculos de tempo — ver services/data_cleaning.py.
INVALID_SENTINEL_DATE_YEAR = 1990
