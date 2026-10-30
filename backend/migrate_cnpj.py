import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parent / "pesquisa.db"


def migrate():
    with sqlite3.connect(DB) as conn:
        conn.execute("BEGIN IMMEDIATE")

        columns = {
            row[1]
            for row in conn.execute(
                "PRAGMA table_info(submissions)"
            )
        }

        if "cnpj" not in columns:
            conn.execute(
                "ALTER TABLE submissions ADD COLUMN cnpj TEXT"
            )
            print("Coluna cnpj adicionada.")
        else:
            print("Coluna cnpj já existe.")

        conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS
                ux_submissions_cnpj
            ON submissions(cnpj)
            WHERE cnpj IS NOT NULL
        """)

        conn.commit()
        print("Índice único de CNPJ confirmado.")


if __name__ == "__main__":
    migrate()
