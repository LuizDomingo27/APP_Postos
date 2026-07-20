"""
services/data_writer.py
-------------------------
Responsabilidade única: gravar novos registros na tabela `postos` do
Supabase. Isso mantém a lógica de escrita completamente isolada das
visualizações e filtros.
"""

from __future__ import annotations

import pandas as pd

from core.config import Columns, RAW_TO_DB_COLUMNS, RawColumns, SUPABASE_TABLE_POSTOS
from services.supabase_client import fetch_all_rows, get_supabase_client

_BULK_INSERT_BATCH_SIZE = 500


def check_record_exists(oficina: str, mp: str, semana: int, data_efetivos: str) -> bool:
    """
    Verifica se já existe um registro para a combinação de Oficina, MP,
    Semana e Data Efetivos na tabela `postos` do Supabase.

    `data_efetivos` entra na chave porque o número da semana se repete a
    cada ano (ex.: Semana 28 existe tanto em 2025 quanto em 2026) — sem a
    data, um lançamento novo de um ano seria confundido com o de outro ano
    para a mesma Oficina/MP/Semana e seria erroneamente tratado como
    duplicado.
    """
    oficina_clean = str(oficina).strip()
    mp_clean = str(mp).strip().upper()

    client = get_supabase_client()
    try:
        response = (
            client.table(SUPABASE_TABLE_POSTOS)
            .select("id")
            .eq(Columns.OFICINA, oficina_clean)
            .eq(Columns.MP, mp_clean)
            .eq(Columns.SEMANA, int(semana))
            .eq(Columns.DATA_EFETIVOS, str(data_efetivos))
            .limit(1)
            .execute()
        )
        return len(response.data or []) > 0
    except Exception as exc:
        raise RuntimeError(f"Erro ao verificar existência de registro no Supabase: {exc}") from exc


def insert_record(
    frete: str,
    mp: str,
    oficina: str,
    data_efetivos: str,
    qtd_efetivos: int,
    data_trabalhados: str,
    qtd_trabalhados: int,
    contratacoes: int,
    demissoes: int,
    semana: int,
) -> None:
    """
    Insere um único registro de posto de trabalho na tabela `postos` do
    Supabase. Realiza sanitização básica antes da gravação.
    """
    payload = {
        Columns.FRETE: str(frete).strip(),
        Columns.MP: str(mp).strip().upper(),
        Columns.OFICINA: str(oficina).strip(),
        Columns.DATA_EFETIVOS: data_efetivos,
        Columns.QTD_EFETIVOS: int(qtd_efetivos),
        Columns.DATA_TRABALHADOS: data_trabalhados,
        Columns.QTD_TRABALHADOS: int(qtd_trabalhados),
        Columns.CONTRATACOES: int(contratacoes),
        Columns.DEMISSOES: int(demissoes),
        Columns.SEMANA: int(semana),
    }

    client = get_supabase_client()
    try:
        client.table(SUPABASE_TABLE_POSTOS).insert(payload).execute()
    except Exception as exc:
        raise RuntimeError(f"Erro ao inserir registro no Supabase: {exc}") from exc


def insert_bulk_records(df: pd.DataFrame) -> int:
    """
    Insere múltiplos registros na tabela `postos` do Supabase, ignorando
    qualquer linha cuja combinação (Oficinas, MP, Semana, Data Efetivos) já
    exista no banco. Retorna o número de linhas novas inseridas com sucesso.

    A Data Efetivos entra na chave de deduplicação porque o número da
    semana se repete a cada ano — sem a data, um lançamento novo de um ano
    seria confundido com o de outro ano para a mesma Oficina/MP/Semana e
    seria erroneamente ignorado como duplicado (bug corrigido: 92
    registros da Semana 28/2026 nunca foram inseridos por esse motivo,
    pois colidiam com registros da Semana 28/2025 já existentes).

    `df` deve conter as colunas BRUTAS (cabeçalhos originais da planilha
    Excel, ver `core.config.RawColumns`) — mesmo contrato usado pelo upload
    manual na tela de Lançamento de Dados.
    """
    required_cols = list(RAW_TO_DB_COLUMNS.keys())

    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"O arquivo importado está sem as seguintes colunas obrigatórias: {missing}")

    # Cópia e limpeza básica
    df_clean = df[required_cols].copy()
    df_clean[RawColumns.FRETE] = df_clean[RawColumns.FRETE].astype(str).str.strip()
    df_clean[RawColumns.MP] = df_clean[RawColumns.MP].astype(str).str.strip().str.upper()
    df_clean[RawColumns.OFICINA] = df_clean[RawColumns.OFICINA].astype(str).str.strip()

    # Formatação de datas para string ISO
    df_clean[RawColumns.DATA_EFETIVOS] = pd.to_datetime(
        df_clean[RawColumns.DATA_EFETIVOS]
    ).dt.strftime("%Y-%m-%d")
    df_clean[RawColumns.DATA_TRABALHADOS] = pd.to_datetime(
        df_clean[RawColumns.DATA_TRABALHADOS]
    ).dt.strftime("%Y-%m-%d")

    # Tratamento de inteiros e nulos
    int_cols = [
        RawColumns.QTD_EFETIVOS,
        RawColumns.QTD_TRABALHADOS,
        RawColumns.CONTRATACAO,
        RawColumns.DEMISSAO,
        RawColumns.SEMANA,
    ]
    for col in int_cols:
        df_clean[col] = df_clean[col].fillna(0).astype(int)

    client = get_supabase_client()
    try:
        # 1. Carrega as chaves (Oficina, MP, Semana, Data Efetivos) já existentes no Supabase
        existing_rows = fetch_all_rows(
            client,
            SUPABASE_TABLE_POSTOS,
            columns=f"{Columns.OFICINA},{Columns.MP},{Columns.SEMANA},{Columns.DATA_EFETIVOS}",
        )
        existing_keys = {
            (
                str(r[Columns.OFICINA]).strip(),
                str(r[Columns.MP]).strip().upper(),
                int(r[Columns.SEMANA]),
                str(r[Columns.DATA_EFETIVOS])[:10],
            )
            for r in existing_rows
        }

        # 2. Cria chaves temporárias para as novas linhas do lote
        df_clean["_key"] = list(
            zip(
                df_clean[RawColumns.OFICINA],
                df_clean[RawColumns.MP],
                df_clean[RawColumns.SEMANA],
                df_clean[RawColumns.DATA_EFETIVOS],
            )
        )

        # 3. Filtra apenas registros que não existem no banco e remove duplicados do próprio lote
        df_to_insert = df_clean[~df_clean["_key"].isin(existing_keys)].drop(columns=["_key"])
        df_to_insert = df_to_insert.drop_duplicates(
            subset=[RawColumns.OFICINA, RawColumns.MP, RawColumns.SEMANA, RawColumns.DATA_EFETIVOS]
        )

        if len(df_to_insert) == 0:
            return 0

        # 4. Traduz para as colunas do Supabase e grava em blocos (o PostgREST
        #    aceita lotes grandes, mas dividir evita payloads excessivos).
        payload = df_to_insert.rename(columns=RAW_TO_DB_COLUMNS).to_dict(orient="records")
        for i in range(0, len(payload), _BULK_INSERT_BATCH_SIZE):
            client.table(SUPABASE_TABLE_POSTOS).insert(
                payload[i : i + _BULK_INSERT_BATCH_SIZE]
            ).execute()

        return len(df_to_insert)
    except Exception as exc:
        raise RuntimeError(f"Erro ao importar dados em lote para o Supabase: {exc}") from exc
