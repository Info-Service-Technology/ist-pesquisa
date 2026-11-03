"""Inicialização explícita do esquema PostgreSQL da IST-Pesquisa."""

import getpass
import os
import sys

from sqlalchemy.engine import make_url


def main():
    database_url = os.environ.get("IST_PESQUISA_DATABASE_URL")

    if not database_url:
        raise SystemExit(
            "IST_PESQUISA_DATABASE_URL não configurada."
        )

    url = make_url(database_url)

    if url.drivername != "postgresql+psycopg":
        raise SystemExit(
            "Use exclusivamente postgresql+psycopg."
        )

    if url.query.get("sslmode") != "require":
        raise SystemExit(
            "A URL PostgreSQL deve incluir sslmode=require."
        )

    if os.environ.get("IST_PESQUISA_INIT_SCHEMA") != "CONFIRMAR":
        raise SystemExit(
            "Inicialização bloqueada. "
            "Defina IST_PESQUISA_INIT_SCHEMA=CONFIRMAR."
        )

    # Solicita a senha sem exibi-la no terminal.
    if not url.password:
        password = getpass.getpass(
            "Senha PostgreSQL (não será exibida): "
        )
        url = url.set(password=password)

    # A URL é passada somente ao processo atual.
    os.environ["IST_PESQUISA_DATABASE_URL"] = url.render_as_string(
        hide_password=False
    )

    # Importar main não cria tabelas no PostgreSQL.
    import main
    from verification_models import VerificationBase

    engine = main.engine

    try:
        with engine.begin() as connection:
            main.Base.metadata.create_all(bind=connection)
            VerificationBase.metadata.create_all(bind=connection)

        print("Esquema PostgreSQL inicializado.")
        print("Tabelas: submissions, email_verifications")
    finally:
        engine.dispose()


if __name__ == "__main__":
    sys.exit(main())
