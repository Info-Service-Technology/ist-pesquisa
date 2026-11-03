"""Serialização de solicitações de verificação por CNPJ."""

from sqlalchemy import text
from sqlalchemy.orm import Session


def lock_verification_request(db: Session, cnpj: str) -> None:
    """Serializa solicitações concorrentes para o mesmo CNPJ."""

    dialect = db.get_bind().dialect.name

    if dialect == "sqlite":
        db.execute(text("BEGIN IMMEDIATE"))
        return

    if dialect == "postgresql":
        db.execute(
            text("""
                SELECT pg_advisory_xact_lock(
                    hashtextextended(:lock_key, 0)
                )
            """),
            {
                "lock_key": f"ist-pesquisa:verification:{cnpj}",
            },
        )
        return

    raise RuntimeError(
        f"Banco de dados não suportado: {dialect}"
    )
