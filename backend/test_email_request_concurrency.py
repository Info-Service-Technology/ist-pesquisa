"""Concorrência na solicitação de códigos de verificação."""

import os
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier, Lock

# Deve ser configurado antes de importar main.
_IMPORT_DIRECTORY = tempfile.TemporaryDirectory(
    prefix="ist-pesquisa-import-"
)

os.environ["IST_PESQUISA_DATABASE_PATH"] = str(
    Path(_IMPORT_DIRECTORY.name) / "import.db"
)

import main

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from email_sender import get_email_sender
from test_email_confirmation import build_payload
from verification_models import EmailVerification, VerificationBase


class FakeEmailSender:
    def __init__(self):
        self.messages = []
        self.lock = Lock()

    def send_verification_code(self, recipient, code):
        with self.lock:
            self.messages.append((recipient, code))


def test_concurrent_requests():
    original_secret = os.environ.get(
        "EMAIL_VERIFICATION_SECRET"
    )

    os.environ["EMAIL_VERIFICATION_SECRET"] = (
        "segredo-exclusivo-para-teste-concorrente-123456789"
    )

    with tempfile.TemporaryDirectory() as directory:
        database = Path(directory) / "requests.db"

        engine = create_engine(
            f"sqlite:///{database}",
            connect_args={
                "check_same_thread": False,
                "timeout": 10,
            },
        )

        original_session = main.SessionLocal
        sender = FakeEmailSender()

        try:
            main.Base.metadata.create_all(engine)
            VerificationBase.metadata.create_all(engine)

            Session = sessionmaker(bind=engine)
            main.SessionLocal = Session

            main.app.dependency_overrides[get_email_sender] = (
                lambda: sender
            )

            payload = build_payload().model_dump(mode="json")
            barrier = Barrier(2)

            def request():
                barrier.wait(timeout=10)

                with TestClient(main.app) as client:
                    response = client.post(
                        "/api/surveys/verification/request",
                        json=payload,
                    )

                return response.status_code

            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = [
                    executor.submit(request)
                    for _ in range(2)
                ]

                statuses = [
                    future.result()
                    for future in futures
                ]

            with Session() as db:
                total = db.scalar(
                    select(func.count()).select_from(
                        EmailVerification
                    )
                )

            print("HTTP concorrentes:", statuses)
            print("Verificações registradas:", total)
            print("E-mails simulados:", len(sender.messages))

            assert statuses.count(202) == 1, statuses
            assert statuses.count(429) == 1, statuses
            assert total == 1, total
            assert len(sender.messages) == 1

            print(
                "PASSOU: somente uma solicitação "
                "foi autorizada"
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
    test_concurrent_requests()
