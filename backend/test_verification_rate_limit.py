"""Testes isolados da política de solicitações."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from verification_models import EmailVerification, VerificationBase
from verification_rate_limit import retry_after_seconds


CNPJ = "11222333000181"


def add_request(db, created_at):
    db.add(
        EmailVerification(
            id=str(uuid4()),
            cnpj=CNPJ,
            email="teste@example.com",
            code_salt="a" * 32,
            code_hash="b" * 64,
            payload={},
            attempts=0,
            created_at=created_at,
            expires_at=created_at + timedelta(minutes=10),
        )
    )
    db.commit()


def test_rate_limit():
    with TemporaryDirectory() as directory:
        database = Path(directory) / "teste_rate_limit.db"

        engine = create_engine(f"sqlite:///{database}")

        try:
            VerificationBase.metadata.create_all(engine)

            with Session(engine) as db:
                assert retry_after_seconds(db, CNPJ) == 0
                print("PASSOU: primeira solicitação permitida")

                now = datetime.now(timezone.utc)

                add_request(db, now)

                wait = retry_after_seconds(db, CNPJ)
                assert 1 <= wait <= 60, wait
                print("PASSOU: intervalo de 60 segundos")

                for minutes in (10, 20, 30, 40):
                    add_request(
                        db,
                        now - timedelta(minutes=minutes),
                    )

                wait = retry_after_seconds(db, CNPJ)
                assert 1100 <= wait <= 1200, wait
                print("PASSOU: limite de 5 solicitações por hora")

                db.query(EmailVerification).delete()
                db.commit()

                add_request(
                    db,
                    now - timedelta(hours=2),
                )

                assert retry_after_seconds(db, CNPJ) == 0
                print("PASSOU: liberação após janela expirada")

        finally:
            engine.dispose()


if __name__ == "__main__":
    test_rate_limit()
