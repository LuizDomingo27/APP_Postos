"""
app.py
-------
Ponto de entrada da aplicação Streamlit "Gestão de Postos de Trabalho".

Este arquivo é deliberadamente curto: sua única responsabilidade é
ORQUESTRAR a ordem de execução (configuração da página → carga de dados
→ filtros → renderização das seções). Toda a lógica de negócio vive em
`services/`, e toda a apresentação vive em `ui/`.

Como rodar:
    streamlit run app.py
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from core.config import APP_ICON, APP_TITLE, DATASET_PATH
from services.data_cleaning import build_data_quality_report, clean_dataframe
from services.data_loader import DataLoadError, load_raw_dataframe
from ui.cadastro_view import render_cadastro_page
from ui.components.filters import apply_filters, render_sidebar_filters
from ui.layout import (
    render_header,
    render_kpi_section,
    render_monthly_tab,
    render_weekly_tab,
    render_workshops_tab,
)
from ui.styles import build_css


@st.cache_data(show_spinner="Carregando dados de postos de trabalho...")
def _load_clean_data() -> pd.DataFrame:
    df_raw = load_raw_dataframe(DATASET_PATH)
    return clean_dataframe(df_raw)


@st.cache_data(show_spinner=False)
def _load_quality_report() -> dict:
    df_raw = load_raw_dataframe(DATASET_PATH)
    return build_data_quality_report(df_raw)


def _render_data_quality_notes() -> None:
    report = _load_quality_report()
    with st.sidebar.expander("📋 Notas de qualidade dos dados"):
        st.caption(
            f"{report['linhas_totais']} linhas analisadas na planilha de origem."
        )
        st.caption(
            f"Valores nulos tratados como 0: {report['qtd_efetivos_nulos']} em "
            f"QTD Efetivos, {report['qtd_trabalhados_nulos']} em QTD Trabalhados."
        )
        if report["linhas_data_trabalhados_invalida"]:
            st.caption(
                f"'Data Trabalhados' inválida em {report['linhas_data_trabalhados_invalida']} "
                f"linhas (Semana {report['semanas_afetadas_data_invalida']}). "
                "O período mensal usado nos gráficos é sempre derivado de "
                "'Data Efetivos', que é consistente em toda a base."
            )
        st.caption(
            "Categorias de MP normalizadas: " + ", ".join(report["mp_variantes_brutas"])
        )


def main() -> None:
    st.set_page_config(
        page_title=APP_TITLE,
        page_icon=APP_ICON,
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(build_css(), unsafe_allow_html=True)

    try:
        df = _load_clean_data()
    except DataLoadError as exc:
        st.error(f"Não foi possível carregar os dados: {exc}")
        st.stop()
        return

    # Menu de Navegação na Sidebar
    st.sidebar.markdown("### 🗺️ Navegação")
    page = st.sidebar.radio(
        "Selecione a página:",
        ["📊 Dashboard", "➕ Lançamento de Dados"],
        index=0
    )
    st.sidebar.markdown("---")

    # Renderiza a página conforme a seleção
    if page == "📊 Dashboard":
        render_header()

        selection = render_sidebar_filters(df)
        df_filtrado = apply_filters(df, selection)
        _render_data_quality_notes()

        if df_filtrado.empty:
            st.warning("Nenhum registro encontrado para os filtros selecionados.")
            st.stop()
            return

        render_kpi_section(df_filtrado)

        tab_semanal, tab_mensal, tab_oficinas = st.tabs(
            ["📈 Evolução Semanal", "📅 Evolução Mensal", "🏭 Oficinas"]
        )

        with tab_semanal:
            render_weekly_tab(df_filtrado)

        with tab_mensal:
            render_monthly_tab(df_filtrado)

        with tab_oficinas:
            render_workshops_tab(df_filtrado, df)
    
    elif page == "➕ Lançamento de Dados":
        render_cadastro_page(df)


if __name__ == "__main__":
    main()
