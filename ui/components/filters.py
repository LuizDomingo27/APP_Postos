"""
ui/components/filters.py
---------------------------
Filtros laterais da aplicação. Segue o mesmo padrão já adotado em outros
projetos: um helper `select_all_popover` que substitui o `st.multiselect`
padrão por um popover compacto com opção de "selecionar todos", guardando
o estado em `st.session_state` para manter a seleção entre re-execuções.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import streamlit as st

from core.config import Columns


from core.utils import all_or_selected


@dataclass(frozen=True)
class FilterSelection:
    ano: int
    mp: list[str]
    oficinas: list[str]  # rótulos combinados "<Oficina> <MP>" (ver Columns.OFICINA_MP)
    semanas: list[int]


def render_sidebar_filters(df: pd.DataFrame) -> FilterSelection:
    """Renderiza os filtros da sidebar e devolve a seleção atual do usuário."""
    st.sidebar.markdown("### 🔎 Filtros")

    # Inicializa estados dos filtros no session_state, se necessário
    if "filtro_mp_widget" not in st.session_state:
        st.session_state.filtro_mp_widget = []
    if "filtro_oficinas_widget" not in st.session_state:
        st.session_state.filtro_oficinas_widget = []
    if "filtro_semanas_widget" not in st.session_state:
        st.session_state.filtro_semanas_widget = []

    # 1. Filtro de Ano (selectbox simples - prioriza o ano mais recente)
    ano_options = sorted(df[Columns.ANO].unique().tolist(), reverse=True)
    
    if "previous_ano" not in st.session_state:
        st.session_state.previous_ano = ano_options[0]

    ano_selected = st.sidebar.selectbox(
        "Ano de Análise",
        options=ano_options,
        index=0,
        help="Selecione o ano para filtrar todas as análises do dashboard."
    )

    # Se o ano de análise mudou, resetamos todos os filtros em cascata
    if ano_selected != st.session_state.previous_ano:
        st.session_state.filtro_mp_widget = []
        st.session_state.filtro_oficinas_widget = []
        st.session_state.filtro_semanas_widget = []
        st.session_state.previous_ano = ano_selected

    # Filtra o DataFrame temporariamente pelo ano selecionado para cascatear as opções
    df_ano = df[df[Columns.ANO] == ano_selected]

    # 2. Matéria-prima (MP) - Cascata Nível 1
    mp_options = sorted(df_ano[Columns.MP].unique().tolist())
    st.session_state.filtro_mp_widget = [x for x in st.session_state.filtro_mp_widget if x in mp_options]

    mp_sel = st.sidebar.multiselect(
        "Matéria-prima (MP)",
        options=mp_options,
        placeholder="Todos",
        key="filtro_mp_widget"
    )
    mp_selected = all_or_selected(mp_sel, mp_options)

    # 3. Oficinas (Oficina · MP) - Cascata Nível 2 (filtrado pelo ano e MPs selecionadas)
    df_mp = df_ano[df_ano[Columns.MP].isin(mp_selected)]
    oficina_options = sorted(df_mp[Columns.OFICINA_MP].unique().tolist())
    st.session_state.filtro_oficinas_widget = [x for x in st.session_state.filtro_oficinas_widget if x in oficina_options]

    oficinas_sel = st.sidebar.multiselect(
        "Oficinas (Oficina · MP)",
        options=oficina_options,
        placeholder="Todos",
        key="filtro_oficinas_widget"
    )
    oficinas_selected = all_or_selected(oficinas_sel, oficina_options)

    # 4. Semanas - Cascata Nível 3 (filtrado pelo ano, MPs e Oficinas selecionadas)
    df_oficina = df_mp[df_mp[Columns.OFICINA_MP].isin(oficinas_selected)]
    semanas_options = sorted(df_oficina[Columns.SEMANA].unique().tolist())
    semanas_str_options = [f"Semana {w}" for w in semanas_options]
    st.session_state.filtro_semanas_widget = [x for x in st.session_state.filtro_semanas_widget if x in semanas_str_options]

    semanas_sel = st.sidebar.multiselect(
        "Semanas",
        options=semanas_str_options,
        placeholder="Todos",
        key="filtro_semanas_widget"
    )
    semanas_selected_str = all_or_selected(semanas_sel, semanas_str_options)

    semanas_selected = []
    for s_str in semanas_selected_str:
        try:
            num = int(s_str.replace("Semana ", ""))
            semanas_selected.append(num)
        except ValueError:
            pass

    return FilterSelection(
        ano=ano_selected,
        mp=mp_selected,
        oficinas=oficinas_selected,
        semanas=semanas_selected,
    )


def apply_filters(df: pd.DataFrame, selection: FilterSelection) -> pd.DataFrame:
    """Aplica a seleção de filtros (incluindo o ano) ao DataFrame limpo."""
    filtrado = df[
        (df[Columns.ANO] == selection.ano)
        & df[Columns.MP].isin(selection.mp)
        & df[Columns.OFICINA_MP].isin(selection.oficinas)
        & df[Columns.SEMANA].isin(selection.semanas)
    ]
    return filtrado

