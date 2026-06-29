"""
services/data_loader.py
-------------------------
Responsabilidade única: ler os dados BRUTOS da fonte (SQLite) e
validar sua estrutura. Se o banco SQLite não existir, faz a migração
automática a partir da planilha Excel para garantir retrocompatibilidade.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
import pandas as pd

from core.config import DB_PATH, DATASET_PATH, DATASET_SHEET_NAME, RawColumns
from scripts.migrate_to_sqlite import run_migration

REQUIRED_RAW_COLUMNS = [
    RawColumns.FRETE,
    RawColumns.MP,
    RawColumns.OFICINA,
    RawColumns.DATA_EFETIVOS,
    RawColumns.QTD_EFETIVOS,
    RawColumns.DATA_TRABALHADOS,
    RawColumns.QTD_TRABALHADOS,
    RawColumns.CONTRATACAO,
    RawColumns.DEMISSAO,
    RawColumns.SEMANA,
]


class DataLoadError(Exception):
    """Erro de domínio para falhas na leitura/validação da fonte de dados."""


def load_raw_dataframe(path: Path = DB_PATH, sheet_name: str = DATASET_SHEET_NAME) -> pd.DataFrame:
    """
    Lê os dados brutos da tabela `postos` do SQLite e devolve um DataFrame.
    
    Se o banco SQLite não existir, migra os dados automaticamente a partir do
    Excel original (especificado pelo parâmetro `path`, que por padrão é redirecionado
    para DB_PATH).
    """
    # Se receber o caminho do Excel (legado de chamadas externas), ou se o banco SQLite não existir
    if not DB_PATH.exists():
        # Executa migração automática se o Excel existir
        if DATASET_PATH.exists():
            success = run_migration(DATASET_PATH, DB_PATH)
            if not success:
                raise DataLoadError(
                    f"O banco de dados SQLite não existe e a migração automática a partir do "
                    f"Excel '{DATASET_PATH.name}' falhou."
                )
        else:
            raise DataLoadError(
                f"Nenhuma fonte de dados encontrada. O banco SQLite não existe em {DB_PATH} "
                f"e o arquivo Excel original não foi encontrado em {DATASET_PATH}."
            )

    # Lê os dados do SQLite
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql("SELECT * FROM postos", conn)
    except Exception as exc:
        raise DataLoadError(f"Falha ao ler os dados do banco SQLite: {exc}") from exc
    finally:
        conn.close()

    # Como no SQLite salvamos 'id' autoincrement, removemos ele do DataFrame bruto 
    # para manter o mesmo contrato exato da planilha Excel
    if "id" in df.columns:
        df = df.drop(columns=["id"])

    # Converte as colunas de data (gravadas como texto ISO) de volta para datetime64
    # para garantir retrocompatibilidade com toda a pipeline de análise e filtros
    try:
        df[RawColumns.DATA_EFETIVOS] = pd.to_datetime(df[RawColumns.DATA_EFETIVOS])
        df[RawColumns.DATA_TRABALHADOS] = pd.to_datetime(df[RawColumns.DATA_TRABALHADOS])
    except Exception as exc:
        raise DataLoadError(f"Erro ao converter formatos de data do SQLite: {exc}") from exc

    _validate_schema(df, DB_PATH)
    return df


def _validate_schema(df: pd.DataFrame, path: Path) -> None:
    """Garante que as colunas mínimas esperadas existem no DataFrame carregado."""
    faltantes = [col for col in REQUIRED_RAW_COLUMNS if col not in df.columns]
    if faltantes:
        raise DataLoadError(
            f"Os dados em '{path.name}' estão sem as colunas obrigatórias: {faltantes}. "
            f"Colunas encontradas: {list(df.columns)}"
        )
    if df.empty:
        raise DataLoadError(f"Os dados em '{path.name}' não contêm nenhuma linha.")

