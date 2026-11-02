from sqlalchemy import select
from sqlalchemy.orm import Session


def cnpj_already_submitted(
    db: Session,
    cnpj: str,
    submission_model,
) -> bool:
    """Consulta se já existe uma pesquisa para o CNPJ."""

    statement = (
        select(submission_model.id)
        .where(submission_model.cnpj == cnpj)
        .limit(1)
    )

    return db.execute(statement).first() is not None
