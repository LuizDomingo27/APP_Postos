"""
ui/cadastro_view.py
--------------------
Camada de visualização (UI) separada para a funcionalidade de cadastro
de dados (manual e importação em lote).

Persistência: no Streamlit Community Cloud o disco é efêmero, então todo
lançamento só sobrevive a um reinício se for sincronizado com o GitHub. Por
isso esta página exibe, no topo, um aviso claro do estado da sincronização —
para que o usuário nunca grave achando que os dados ficarão salvos quando, na
verdade, o sync está desativado.
"""

from __future__ import annotations

import datetime
import pandas as pd
import streamlit as st

from core.config import DB_PATH, Columns
from core.errors import error_boundary
from services.data_writer import insert_record, insert_bulk_records, check_record_exists
from services.git_sync import get_sync_status, sync_db_to_github


def _render_sync_banner() -> None:
    """
    Mostra o estado da persistência no topo da página de cadastro.

    Quando a sincronização está desativada, este é o aviso que explica a causa
    da "perda de dados após reiniciar": sem o sync configurado, o Cloud apaga o
    banco a cada reinício. Assim o problema fica visível ANTES de gravar.
    """
    enabled, msg = get_sync_status()
    if enabled:
        st.success(msg, icon=":material/cloud_done:")
    else:
        st.warning(msg, icon=":material/cloud_off:")


def _feedback_sync(commit_message: str) -> None:
    """Sincroniza o banco com o GitHub e mostra o resultado sem quebrar o cadastro."""
    ok, msg = sync_db_to_github(commit_message)
    if ok:
        st.caption(msg)
    else:
        st.warning(f"Registro gravado localmente, mas a sincronização falhou: {msg}")


@st.dialog("Confirmar Lançamento com Valores Zerados")
def confirm_zero_dialog(record_data: dict) -> None:
    st.warning(
        "Os seguintes indicadores foram informados com valor **zero (0)**. "
        "Por favor, confirme se deseja prosseguir:"
    )

    # Lista os campos zerados
    zeros = []
    if record_data["qtd_efetivos"] == 0:
        zeros.append("- **QTD Efetivos (Planejado)**")
    if record_data["qtd_trabalhados"] == 0:
        zeros.append("- **QTD Trabalhados (Realizado)**")
    if record_data["contratacoes"] == 0:
        zeros.append("- **Contratações**")
    if record_data["demissoes"] == 0:
        zeros.append("- **Demissões**")

    for z in zeros:
        st.markdown(z)

    st.markdown("<br>", unsafe_allow_html=True)
    st.write(
        f"**Registro:** Oficina `{record_data['oficina']}` · "
        f"MP `{record_data['mp']}` · Semana `{record_data['semana']}`"
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Sim, salvar mesmo assim", use_container_width=True):
            with error_boundary("salvar o registro"):
                insert_record(
                    db_path=DB_PATH,
                    frete=record_data["frete"],
                    mp=record_data["mp"],
                    oficina=record_data["oficina"],
                    data_efetivos=record_data["data_efetivos"],
                    qtd_efetivos=record_data["qtd_efetivos"],
                    data_trabalhados=record_data["data_trabalhados"],
                    qtd_trabalhados=record_data["qtd_trabalhados"],
                    contratacoes=record_data["contratacoes"],
                    demissoes=record_data["demissoes"],
                    semana=record_data["semana"],
                )
                st.cache_data.clear()
                st.success("Registro salvo com sucesso!")
                _feedback_sync(
                    f"dados: cadastro Oficina {record_data['oficina']} "
                    f"Semana {record_data['semana']}"
                )
                st.rerun()
    with col2:
        if st.button("Não, voltar e ajustar", use_container_width=True):
            st.rerun()


def render_cadastro_page(df_full: pd.DataFrame) -> None:
    """Renderiza a página de inserção de novos registros e importação em lote."""
    st.markdown(
        """
        <div class="app-header">
            <div class="title-row">
                <h1>Lançamento de Dados</h1>
            </div>
            <div class="subtitle">Adicione novos registros manuais ou importe arquivos Excel para o banco de dados</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _render_sync_banner()

    tab_manual, tab_lote = st.tabs(["Formulário Manual", "Importação em Lote"])

    # Extrai opções únicas atuais para facilitar a seleção e evitar typos
    frete_options = sorted(df_full[Columns.FRETE].dropna().unique().tolist())
    mp_options = sorted(df_full[Columns.MP].dropna().unique().tolist())

    # Extrai a oficina sem a matéria-prima (coluna original)
    oficina_options = sorted(df_full[Columns.OFICINA].dropna().unique().tolist())

    with tab_manual:
        _render_manual_form(frete_options, mp_options, oficina_options)

    with tab_lote:
        _render_bulk_import()


def _render_manual_form(
    frete_options: list[str], mp_options: list[str], oficina_options: list[str]
) -> None:
    with st.container(key="cadastro_manual_form"):
        st.markdown("##### Novo Registro")
        st.caption("Preencha as informações abaixo para gravar um novo registro no banco de dados.")

        # ── Seção 1: Identificação ────────────────────────────────────────
        with st.container(border=True):
            st.markdown(
                """
                <div class="form-section-hdr">
                    <span class="fsh-num">01</span>
                    <span class="fsh-title">Identificação</span>
                    <span class="fsh-hint">Oficina · Matéria-prima · Transportador</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Renderiza os inputs diretamente (sem st.form) para habilitar re-execução
            # instantânea na mudança dos selectboxes ("Outro...").
            col1, col2, col3 = st.columns(3)

            with col1:
                oficina_sel = st.selectbox(
                    "Oficina",
                    options=oficina_options + [" Outro... (Novo cadastro)"],
                    index=0,
                    help="Selecione uma oficina existente ou marque 'Outro...' para digitar uma nova."
                )
                nova_oficina = ""
                if oficina_sel == " Outro... (Novo cadastro)":
                    nova_oficina = st.text_input(
                        "Nome da Nova Oficina",
                        placeholder="Ex: OFICINA EXCELENCIA LTDA",
                        help="Digite o nome completo da nova oficina."
                    )

            with col2:
                mp_sel = st.selectbox(
                    "Matéria-prima (MP)",
                    options=mp_options + [" Outro... (Novo cadastro)"],
                    index=0,
                )
                nova_mp = ""
                if mp_sel == " Outro... (Novo cadastro)":
                    nova_mp = st.text_input(
                        "Nome da Nova MP",
                        placeholder="Ex: ALGODAO",
                    )

            with col3:
                frete_sel = st.selectbox(
                    "Frete (Transportador)",
                    options=frete_options + [" Outro... (Novo cadastro)"],
                    index=0,
                )
                novo_frete = ""
                if frete_sel == " Outro... (Novo cadastro)":
                    novo_frete = st.text_input(
                        "Nome do Novo Transportador",
                        placeholder="Ex: RAPIDO BRASIL",
                    )

        # ── Seção 2: Período e Semana ───────────────────────────────────────
        with st.container(border=True):
            st.markdown(
                """
                <div class="form-section-hdr">
                    <span class="fsh-num">02</span>
                    <span class="fsh-title">Período e Semana</span>
                    <span class="fsh-hint">Datas de referência · Semana calculada automaticamente</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            col_dt1, col_dt2, col_sem = st.columns([1.2, 1.2, 0.8])

            with col_dt1:
                data_efetivos = st.date_input(
                    "Data Efetivos (Planejado)",
                    value=datetime.date.today(),
                    help="Data de referência para a quantidade planejada de efetivos."
                )

            with col_dt2:
                mesma_data = st.checkbox("Mesma data para 'Trabalhados'", value=True)
                if mesma_data:
                    data_trabalhados = data_efetivos
                else:
                    data_trabalhados = st.date_input(
                        "Data Trabalhados (Realizado)",
                        value=data_efetivos,
                        help="Data de referência para a quantidade real de trabalhadores presentes."
                    )

            with col_sem:
                semana_calculada = data_efetivos.isocalendar()[1]
                semana = st.number_input(
                    "Semana",
                    min_value=1,
                    max_value=53,
                    value=semana_calculada,
                    step=1,
                    help="Calculado automaticamente com base na 'Data Efetivos', mas você pode ajustar se necessário."
                )

        # ── Seção 3: Quantidades ─────────────────────────────────────────────
        with st.container(border=True):
            st.markdown(
                """
                <div class="form-section-hdr">
                    <span class="fsh-num">03</span>
                    <span class="fsh-title">Quantidades</span>
                    <span class="fsh-hint">Efetivos planejados · Presença realizada · Movimentação</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            col_n1, col_n2, col_n3, col_n4 = st.columns(4)

            with col_n1:
                qtd_efetivos = st.number_input("QTD Efetivos", min_value=0, value=0, step=1, help="Planejado")
            with col_n2:
                qtd_trabalhados = st.number_input("QTD Trabalhados", min_value=0, value=0, step=1, help="Realizado")
            with col_n3:
                contratacoes = st.number_input("Contratações", min_value=0, value=0, step=1)
            with col_n4:
                demissoes = st.number_input("Demissões", min_value=0, value=0, step=1)

        st.markdown("<br>", unsafe_allow_html=True)
        btn_gravar = st.button("Gravar Registro", use_container_width=True, type="primary")

    if btn_gravar:
        # Resolve os valores selecionados (existentes ou novos)
        final_oficina = nova_oficina if oficina_sel == " Outro... (Novo cadastro)" else oficina_sel
        final_mp = nova_mp if mp_sel == " Outro... (Novo cadastro)" else mp_sel
        final_frete = novo_frete if frete_sel == " Outro... (Novo cadastro)" else frete_sel

        # Validações básicas de preenchimento
        erros = []
        if not final_oficina or final_oficina.strip() == "":
            erros.append("O campo 'Oficina' é obrigatório.")
        if not final_mp or final_mp.strip() == "":
            erros.append("O campo 'Matéria-prima (MP)' é obrigatório.")
        if not final_frete or final_frete.strip() == "":
            erros.append("O campo 'Frete' é obrigatório.")

        if erros:
            for erro in erros:
                st.error(erro)
        else:
            with error_boundary("validar e gravar o registro"):
                # 1. Validação de Duplicidade (Oficina + MP + Semana)
                if check_record_exists(DB_PATH, final_oficina, final_mp, semana):
                    st.error(
                        f"**Erro de Duplicidade:** Já existe um lançamento para a Oficina "
                        f"**'{final_oficina}'** e Matéria-prima **'{final_mp}'** na **Semana {semana}**."
                    )
                else:
                    # Prepara os dados para inserção ou diálogo
                    record_data = {
                        "frete": final_frete,
                        "mp": final_mp,
                        "oficina": final_oficina,
                        "data_efetivos": data_efetivos.strftime("%Y-%m-%d"),
                        "qtd_efetivos": int(qtd_efetivos),
                        "data_trabalhados": data_trabalhados.strftime("%Y-%m-%d"),
                        "qtd_trabalhados": int(qtd_trabalhados),
                        "contratacoes": int(contratacoes),
                        "demissoes": int(demissoes),
                        "semana": int(semana),
                    }

                    # 2. Validação de Valores Zerados
                    has_zeros = (
                        qtd_efetivos == 0 or
                        qtd_trabalhados == 0 or
                        contratacoes == 0 or
                        demissoes == 0
                    )

                    if has_zeros:
                        # Chama a janela de confirmação nativa
                        confirm_zero_dialog(record_data)
                    else:
                        # Gravação direta sem zeros
                        insert_record(
                            db_path=DB_PATH,
                            frete=record_data["frete"],
                            mp=record_data["mp"],
                            oficina=record_data["oficina"],
                            data_efetivos=record_data["data_efetivos"],
                            qtd_efetivos=record_data["qtd_efetivos"],
                            data_trabalhados=record_data["data_trabalhados"],
                            qtd_trabalhados=record_data["qtd_trabalhados"],
                            contratacoes=record_data["contratacoes"],
                            demissoes=record_data["demissoes"],
                            semana=record_data["semana"],
                        )
                        st.cache_data.clear()
                        st.success(
                            f"Sucesso! Registro gravado para a Oficina '{final_oficina}' "
                            f"(Semana {semana}). Os dados já foram computados no Dashboard!"
                        )
                        _feedback_sync(
                            f"dados: cadastro Oficina {final_oficina} Semana {semana}"
                        )
                        st.rerun()  # Força o reset dos campos limpando os inputs


def _render_bulk_import() -> None:
    st.markdown("##### Importação em Lote via Excel")
    st.caption(
        "Faça upload de uma planilha Excel com novos lançamentos. "
        "Registros duplicados (mesma Oficina + MP + Semana) são ignorados automaticamente."
    )

    _REQUIRED_COLS = [
        "Frete", "MP", "Oficinas", "Data Efetivos", "QTD Efetivos",
        "Data Trabalhados", "QTD Trabalhados", "Contratatação", "Demissão", "Semana",
    ]
    chips_html = "".join(f'<span class="col-chip">{col}</span>' for col in _REQUIRED_COLS)

    st.markdown(
        f"""
        <div class="import-info-box">
            <div class="iib-title">Colunas obrigatórias</div>
            <div class="iib-desc">
                A planilha deve conter exatamente os cabeçalhos abaixo
                (respeite maiúsculas, acentuação e espaços):
            </div>
            <div class="col-chips">{chips_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    uploaded_file = st.file_uploader(
        "Selecione o arquivo Excel (.xlsx)",
        type=["xlsx"],
        help="Carregue uma planilha no formato de colunas listado acima."
    )

    if uploaded_file is None:
        return

    with error_boundary("processar o arquivo importado"):
        df_uploaded = pd.read_excel(uploaded_file)

        st.markdown(
            f"""
            <div class="form-section-hdr" style="margin-top:1rem;">
                <span class="fsh-title">Pré-visualização</span>
                <span class="fsh-hint">{len(df_uploaded)} linhas encontradas · exibindo as 10 primeiras</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.dataframe(df_uploaded.head(10), use_container_width=True)

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Confirmar Importação em Lote", use_container_width=True, type="primary"):
            with st.spinner("Gravando dados no banco..."):
                linhas_inseridas = insert_bulk_records(DB_PATH, df_uploaded)
                st.cache_data.clear()

            if linhas_inseridas > 0:
                st.success(
                    f"Importação concluída! **{linhas_inseridas}** novos registros "
                    f"foram inseridos com sucesso (duplicados ignorados)."
                )
                _feedback_sync(
                    f"dados: importação em lote ({linhas_inseridas} linhas)"
                )
            else:
                st.info(
                    "Nenhum novo registro foi inserido. "
                    "Todos os registros já constavam no banco de dados."
                )
