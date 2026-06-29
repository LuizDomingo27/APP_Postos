"""
scripts/migrate_to_sqlite.py
----------------------------
Script utilitário para migrar os dados do arquivo Excel (POSTOS.xlsx)
para um banco de dados SQLite (postos.db).

Este script cria a tabela `postos` com a tipagem correta e insere os registros
existentes no Excel, formatando as datas para strings ISO (YYYY-MM-DD).
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
import pandas as pd

# Caminhos padrão
BASE_DIR = Path(__file__).resolve().parent.parent
EXCEL_PATH = BASE_DIR / "Dataset" / "POSTOS.xlsx"
DB_PATH = BASE_DIR / "Dataset" / "postos.db"


def run_migration(excel_path: Path = EXCEL_PATH, db_path: Path = DB_PATH) -> bool:
    """Executa a migração dos dados do Excel para o SQLite."""
    print(f"Iniciando migração de {excel_path.name} para {db_path.name}...")

    if not excel_path.exists():
        print(f"Erro: Arquivo Excel não encontrado em: {excel_path}")
        return False

    # 1. Carrega dados do Excel
    try:
        print("Lendo arquivo Excel (isso pode levar alguns segundos)...")
        # Mantendo as colunas brutas exatamente como na planilha original
        df = pd.read_excel(excel_path, sheet_name="Planilha1")
        print(f"Excel carregado com sucesso. Total de linhas: {len(df)}")
    except Exception as exc:
        print(f"Erro ao ler o arquivo Excel: {exc}")
        return False

    # 2. Conecta ao banco de dados SQLite
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 3. Cria a tabela com esquema definido se não existir
        # Usamos colchetes para colunas com espaços ou acentos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS postos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                Frete TEXT,
                MP TEXT,
                Oficinas TEXT,
                [Data Efetivos] TEXT,
                [QTD Efetivos] INTEGER,
                [Data Trabalhados] TEXT,
                [QTD Trabalhados] INTEGER,
                [Contratatação] INTEGER,
                [Demissão] INTEGER,
                Semana INTEGER
            );
        """)
        conn.commit()

        # Limpa tabela se já existirem registros para evitar duplicidades
        cursor.execute("SELECT COUNT(*) FROM postos")
        if cursor.fetchone()[0] > 0:
            print("Banco de dados já contém registros. Limpando tabela para nova carga completa...")
            cursor.execute("DELETE FROM postos")
            conn.commit()

        # 4. Prepara o DataFrame para inserção
        df_mig = df.copy()

        # Converte colunas de data para string formatada YYYY-MM-DD
        if "Data Efetivos" in df_mig.columns:
            df_mig["Data Efetivos"] = pd.to_datetime(df_mig["Data Efetivos"]).dt.strftime("%Y-%m-%d")
        if "Data Trabalhados" in df_mig.columns:
            df_mig["Data Trabalhados"] = pd.to_datetime(df_mig["Data Trabalhados"]).dt.strftime("%Y-%m-%d")

        # Garante tratamento de nulos em colunas numéricas
        num_cols = ["QTD Efetivos", "QTD Trabalhados", "Contratatação", "Demissão", "Semana"]
        for col in num_cols:
            if col in df_mig.columns:
                df_mig[col] = df_mig[col].fillna(0).astype(int)

        # 5. Salva dados na tabela SQLite usando o pandas
        print("Gravando dados no SQLite...")
        # NOTA: O index=False evita gravar a coluna index, e como 'id' é PRIMARY KEY AUTOINCREMENT,
        # o SQLite vai gerar a chave automática para cada linha inserida.
        df_mig.to_sql("postos", conn, if_exists="append", index=False)
        
        print("Migração concluída com sucesso!")
        return True

    except Exception as exc:
        print(f"Erro durante a gravação no SQLite: {exc}")
        conn.rollback()
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    run_migration()
