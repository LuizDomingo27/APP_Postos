"""
app.py
-------
Ponto de entrada da aplicação Streamlit "Gestão de Postos de Trabalho".

Este arquivo é deliberadamente curto: sua única responsabilidade é
ORQUESTRAR a ordem de execução (configuração da página → navbar → carga de
dados → filtros → renderização das seções). Toda a lógica de negócio vive em
`services/`, e toda a apresentação vive em `ui/`.

Navegação e filtros ficam no TOPO da página (navbar + barra de filtros). A
sidebar foi desativada — ver `ui/styles.py`.

Como rodar:
    streamlit run app.py
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core.config import APP_ICON, APP_SUBTITLE, APP_TITLE, DATASET_PATH
from core.errors import error_boundary, guard
from services.data_cleaning import clean_dataframe
from services.data_loader import load_raw_dataframe
from ui.cadastro_view import render_cadastro_page
from ui.components.filters import apply_filters, render_top_filters
from ui.layout import (
    render_kpi_section,
    render_monthly_tab,
    render_weekly_tab,
    render_workshops_tab,
)
from ui.styles import build_css

_PAGE_DASHBOARD = "dashboard"
_PAGE_LANCAMENTO = "lancamento"


@st.cache_data(show_spinner="Carregando dados de postos de trabalho...")
def _load_clean_data() -> pd.DataFrame:
    df_raw = load_raw_dataframe(DATASET_PATH)
    return clean_dataframe(df_raw)


def render_navbar() -> str:
    """
    Renderiza a navbar do topo (marca + navegação entre páginas) e devolve a
    página ativa. A navegação usa `st.session_state` para preservar a seleção
    entre re-execuções; o item ativo aparece como botão primário (destacado).
    """
    if "page" not in st.session_state:
        st.session_state.page = _PAGE_DASHBOARD

    col_brand, col_dash, col_lanc = st.columns([6, 2, 2], vertical_alignment="center")

    with col_brand:
        st.markdown(
            f"""
            <div class="app-navbar">
                <span class="brand-title">{APP_TITLE}</span>
                <span class="brand-sub">{APP_SUBTITLE}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_dash:
        if st.button(
            "Dashboard",
            use_container_width=True,
            type="primary" if st.session_state.page == _PAGE_DASHBOARD else "secondary",
            key="nav_dashboard",
        ):
            st.session_state.page = _PAGE_DASHBOARD
            st.rerun()

    with col_lanc:
        if st.button(
            "Lançamento de Dados",
            use_container_width=True,
            type="primary" if st.session_state.page == _PAGE_LANCAMENTO else "secondary",
            key="nav_lancamento",
        ):
            st.session_state.page = _PAGE_LANCAMENTO
            st.rerun()

    st.markdown('<div class="navbar-divider"></div>', unsafe_allow_html=True)
    return st.session_state.page


@guard("montar o dashboard")
def _render_dashboard(df: pd.DataFrame) -> None:
    selection = render_top_filters(df)
    df_filtrado = apply_filters(df, selection)

    if df_filtrado.empty:
        st.warning("Nenhum registro encontrado para os filtros selecionados.")
        return

    render_kpi_section(df_filtrado)

    tab_semanal, tab_mensal, tab_oficinas = st.tabs(
        ["Evolução Semanal", "Evolução Mensal", "Oficinas"]
    )

    with tab_semanal:
        render_weekly_tab(df_filtrado)

    with tab_mensal:
        render_monthly_tab(df_filtrado)

    with tab_oficinas:
        render_workshops_tab(df_filtrado, df)


def main() -> None:
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon=APP_ICON,
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    st.markdown(build_css(), unsafe_allow_html=True)

    page = render_navbar()

    # A carga de dados é fatal: sem dados não há o que exibir em nenhuma página.
    with error_boundary("carregar os dados de postos de trabalho", fatal=True):
        df = _load_clean_data()

    if page == _PAGE_LANCAMENTO:
        render_cadastro_page(df)
    else:
        _render_dashboard(df)


if __name__ == "__main__":
    # Rede de segurança final: qualquer falha não capturada nas camadas
    # internas ainda vira uma mensagem amigável em vez de um traceback cru.
    with error_boundary("iniciar a aplicação", fatal=True):
        main()
