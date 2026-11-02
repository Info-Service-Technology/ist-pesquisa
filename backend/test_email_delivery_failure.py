"""Teste de falha na entrega do código de verificação."""

import os
import tempfile
from pathlib import Path

# Isola o banco antes de importar main.py.
_IMPORT_DIRECTORY = tempfile.TemporaryDirectory(
    prefix="ist-pesquisa-failure-import-"
)

os.environ["IST_PESQUISA_DATABASE_PATH"] = str(
    Path(_IMPORT_DIRECTORY.name) / "import.db"
)

import main

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from email_sender import EmailDeliveryError, get_email_sender
from test_email_confirmation import build_payload
from verification_models import EmailVerification, VerificationBase


class FailingEmailSender:
    def __init__(self):
        self.attempts = 0

    def send_verification_code(self, recipient, code):
        self.attempts += 1
        raise EmailDeliveryError("Falha simulada")


def test_delivery_failure():
    original_secret = os.environ.get(
        "EMAIL_VERIFICATION_SECRET"
    )

    os.environ["EMAIL_VERIFICATION_SECRET"] = (
        "segredo-exclusivo-para-teste-de-falha-123456789"
    )

    with tempfile.TemporaryDirectory() as directory:
        database = Path(directory) / "failure.db"

        engine = create_engine(
            f"sqlite:///{database}",
            connect_args={"check_same_thread": False},
        )

        original_session = main.SessionLocal
        sender = FailingEmailSender()

        try:
            main.Base.metadata.create_all(engine)
            VerificationBase.metadata.create_all(engine)

            Session = sessionmaker(bind=engine)
            main.SessionLocal = Session

            main.app.dependency_overrides[get_email_sender] = (
                lambda: sender
            )

            payload = build_payload().model_dump(mode="json")

            with TestClient(main.app) as client:
                response = client.post(
                    "/api/surveys/verification/request",
                    json=payload,
                )

                assert response.status_code == 503, (
                    response.status_code,
                    response.json(),
                )

                print("PASSOU: falha de envio retorna HTTP 503")

                with Session() as db:
                    pending = db.scalar(
                        select(func.count()).select_from(
                            EmailVerification
                        )
                    )

                    submissions = db.scalar(
                        select(func.count()).select_from(
                            main.Submission
                        )
                    )

                assert pending == 1, pending
                assert submissions == 0, submissions
                assert sender.attempts == 1

                print(
                    "PASSOU: solicitação preservada "
                    "após falha de entrega"
                )
                print(
                    "PASSOU: nenhuma pesquisa definitiva registrada"
                )

                second_response = client.post(
                    "/api/surveys/verification/request",
                    json=payload,
                )

                assert second_response.status_code == 429, (
                    second_response.status_code,
                    second_response.json(),
                )

                assert sender.attempts == 1

                print(
                    "PASSOU: nova solicitação imediata "
                    "bloqueada com HTTP 429"
                )

        finally:
            main.app.dependency_overrides.clear()
            main.SessionLocal = original_session
            engine.dispose()

            if original_secret is None:
                os.environ.pop(
                    "EMAIL_VERIFICATION_SECRET",
                    None,
                )
            else:
                os.environ["EMAIL_VERIFICATION_SECRET"] = (
                    original_secret
                )


if __name__ == "__main__":
    test_delivery_failure()
