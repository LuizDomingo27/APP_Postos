"""
services/data_writer.py
-------------------------
Responsabilidade única: gravar novos registros no banco de dados SQLite.
Isso mantém a lógica de escrita completamente isolada das visualizações e filtros.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
import pandas as pd


def check_record_exists(db_path: Path, oficina: str, mp: str, semana: int) -> bool:
    """
    Verifica se já existe um registro para a combinação de Oficina, MP e Semana no SQLite.
    """
    oficina_clean = str(oficina).strip()
    mp_clean = str(mp).strip().upper()
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT 1 FROM postos WHERE Oficinas = ? AND MP = ? AND Semana = ? LIMIT 1",
            (oficina_clean, mp_clean, int(semana)),
        )
        return cursor.fetchone() is not None
    except Exception as exc:
        raise RuntimeError(f"Erro ao verificar existência de registro no SQLite: {exc}") from exc
    finally:
        conn.close()


def insert_record(
    db_path: Path,
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
    Insere um único registro de posto de trabalho na tabela `postos` do SQLite.
    Realiza sanitização básica antes da gravação.
    """
    # Limpeza básica (mesma padronização da leitura, garantindo consistência)
    frete_clean = str(frete).strip()
    mp_clean = str(mp).strip().upper()
    oficina_clean = str(oficina).strip()

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO postos (
                Frete, MP, Oficinas, [Data Efetivos], [QTD Efetivos],
                [Data Trabalhados], [QTD Trabalhados], [Contratatação], [Demissão], Semana
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                frete_clean,
                mp_clean,
                oficina_clean,
                data_efetivos,
                int(qtd_efetivos),
                data_trabalhados,
                int(qtd_trabalhados),
                int(contratacoes),
                int(demissoes),
                int(semana),
            ),
        )
        conn.commit()
    except Exception as exc:
        conn.rollback()
        raise RuntimeError(f"Erro ao inserir registro no SQLite: {exc}") from exc
    finally:
        conn.close()


def insert_bulk_records(db_path: Path, df: pd.DataFrame) -> int:
    """
    Insere múltiplos registros no banco de dados em lote, ignorando qualquer linha
    cuja combinação (Oficinas, MP, Semana) já exista no banco de dados.
    Retorna o número de linhas novas inseridas com sucesso.
    """
    # Mapeamento para garantir que as colunas brutas do Excel fiquem corretas no banco
    required_cols = [
        "Frete",
        "MP",
        "Oficinas",
        "Data Efetivos",
        "QTD Efetivos",
        "Data Trabalhados",
        "QTD Trabalhados",
        "Contratatação",
        "Demissão",
        "Semana",
    ]

    # Validação estrutural do lote
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"O arquivo importado está sem as seguintes colunas obrigatórias: {missing}")

    # Cópia e limpeza básica
    df_clean = df[required_cols].copy()
    df_clean["Frete"] = df_clean["Frete"].astype(str).str.strip()
    df_clean["MP"] = df_clean["MP"].astype(str).str.strip().str.upper()
    df_clean["Oficinas"] = df_clean["Oficinas"].astype(str).str.strip()
    
    # Formatação de datas para string ISO
    df_clean["Data Efetivos"] = pd.to_datetime(df_clean["Data Efetivos"]).dt.strftime("%Y-%m-%d")
    df_clean["Data Trabalhados"] = pd.to_datetime(df_clean["Data Trabalhados"]).dt.strftime("%Y-%m-%d")

    # Tratamento de inteiros e nulos
    int_cols = ["QTD Efetivos", "QTD Trabalhados", "Contratatação", "Demissão", "Semana"]
    for col in int_cols:
        df_clean[col] = df_clean[col].fillna(0).astype(int)

    conn = sqlite3.connect(db_path)
    try:
        # 1. Carrega chaves existentes (Oficinas, MP, Semana) do banco de dados
        existing_df = pd.read_sql("SELECT Oficinas, MP, Semana FROM postos", conn)
        existing_keys = set(
            zip(
                existing_df["Oficinas"].astype(str).str.strip(),
                existing_df["MP"].astype(str).str.strip().str.upper(),
                existing_df["Semana"].astype(int),
            )
        )

        # 2. Cria chaves temporárias para as novas linhas do lote
        df_clean["_key"] = list(
            zip(
                df_clean["Oficinas"].astype(str).str.strip(),
                df_clean["MP"].astype(str).str.strip().str.upper(),
                df_clean["Semana"].astype(int),
            )
        )

        # 3. Filtra apenas registros que não existem no banco de dados e remove duplicados do próprio lote
        df_to_insert = df_clean[~df_clean["_key"].isin(existing_keys)].drop(columns=["_key"])
        df_to_insert = df_to_insert.drop_duplicates(subset=["Oficinas", "MP", "Semana"])

        # 4. Grava os novos registros, se houver
        if len(df_to_insert) > 0:
            df_to_insert.to_sql("postos", conn, if_exists="append", index=False)
            return len(df_to_insert)
        
        return 0
    except Exception as exc:
        raise RuntimeError(f"Erro ao importar dados em lote para o SQLite: {exc}") from exc
    finally:
        conn.close()
