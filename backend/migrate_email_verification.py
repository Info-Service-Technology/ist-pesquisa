from pathlib import Path
import os
import sqlite3

from sqlalchemy import create_engine, inspect

from verification_models import VerificationBase


DATABASE_PATH = Path(
    os.environ.get(
        "IST_PESQUISA_DATABASE_PATH",
        str(Path(__file__).resolve().parent / "pesquisa.db"),
    )
).expanduser().resolve()

if not DATABASE_PATH.exists():
    raise SystemExit(
        "Banco pesquisa.db não encontrado. Migração cancelada."
    )

connection = sqlite3.connect(DATABASE_PATH)

try:
    integrity = connection.execute(
        "PRAGMA integrity_check"
    ).fetchone()[0]

    if integrity != "ok":
        raise SystemExit(
            f"Falha na integridade do SQLite: {integrity}"
        )

    tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }

    if "submissions" not in tables:
        raise SystemExit(
            "Tabela submissions ausente. Migração cancelada."
        )

finally:
    connection.close()

engine = create_engine(
    f"sqlite:///{DATABASE_PATH}"
)

VerificationBase.metadata.create_all(bind=engine)

inspector = inspect(engine)

assert "email_verifications" in inspector.get_table_names()

print("PASSOU: tabela email_verifications disponível")
print("PASSOU: tabela submissions preservada")
