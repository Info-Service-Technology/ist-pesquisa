import os
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Isola o banco antes da importação de main.py.
_TEST_DATABASE_DIRECTORY = tempfile.TemporaryDirectory(
    prefix="ist-pesquisa-email-request-"
)

os.environ["IST_PESQUISA_DATABASE_PATH"] = str(
    Path(_TEST_DATABASE_DIRECTORY.name) / "test_import.db"
)

import main
from email_sender import get_email_sender
from verification_models import EmailVerification, VerificationBase


class FakeEmailSender:
    def __init__(self):
        self.messages = []

    def send_verification_code(self, recipient, code):
        self.messages.append((recipient, code))


def test_request():
    fake_sender = FakeEmailSender()

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    main.Base.metadata.create_all(engine)
    VerificationBase.metadata.create_all(engine)

    test_session = sessionmaker(bind=engine)

    original_session = main.SessionLocal

    main.SessionLocal = test_session
    main.app.dependency_overrides[get_email_sender] = (
        lambda: fake_sender
    )

    try:
        with tempfile.TemporaryDirectory() as directory:
            # Apenas o segredo de teste, nunca o segredo real.
            original_secret = os.environ.get(
                "EMAIL_VERIFICATION_SECRET"
            )

            os.environ["EMAIL_VERIFICATION_SECRET"] = (
                "segredo-exclusivo-para-teste-automatizado-123456789"
            )

            try:
                from cnpj import valid_cnpj

                def make_cnpj(base):
                    def digit(numbers, weights):
                        total = sum(
                            int(n) * w
                            for n, w in zip(numbers, weights)
                        )
                        remainder = total % 11
                        return str(
                            0 if remainder < 2 else 11 - remainder
                        )

                    first = digit(
                        base,
                        [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2],
                    )
                    second = digit(
                        base + first,
                        [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2],
                    )
                    return base + first + second

                cnpj = make_cnpj("987654320001")
                assert valid_cnpj(cnpj)

                answers = []

                for index, options in sorted(
                    main.VALID_OPTIONS.items()
                ):
                    option = next(
                        value
                        for value in sorted(options)
                        if not value.lower().startswith(
                            ("outro ", "outra ")
                        )
                    )

                    answers.append({
                        "question": index,
                        "selections": [option],
                        "other_detail": None,
                    })

                answers.append({
                    "question": 8,
                    "selections": [
                        "Não identificamos outros desafios atualmente."
                    ],
                    "other_detail": None,
                })

                payload = {
                    "institution": "Instituição Teste",
                    "cnpj": cnpj,
                    "city": "Petrópolis",
                    "respondent": "Responsável Teste",
                    "role": "Gestão",
                    "email": "teste@example.com",
                    "phone": "(24) 99999-9999",
                    "answers": answers,
                    "privacy_accepted": True,
                    "commercial_contact": False,
                    "website": "",
                }

                client = TestClient(main.app)

                response = client.post(
                    "/api/surveys/verification/request",
                    json=payload,
                )

                print("HTTP:", response.status_code)
                print("Resposta:", response.json())

                assert response.status_code == 202

                assert len(fake_sender.messages) == 1

                recipient, code = fake_sender.messages[0]

                assert recipient == "teste@example.com"
                assert len(code) == 6
                assert code.isdigit()

                with test_session() as db:
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

                assert pending == 1
                assert submissions == 0

                # Uma segunda solicitação imediata deve ser bloqueada.
                second_response = client.post(
                    "/api/surveys/verification/request",
                    json=payload,
                )

                assert second_response.status_code == 429, (
                    second_response.status_code,
                    second_response.json(),
                )

                retry_after = second_response.headers.get(
                    "Retry-After"
                )

                assert retry_after is not None
                assert 1 <= int(retry_after) <= 60

                assert len(fake_sender.messages) == 1

                with test_session() as db:
                    pending_after = db.scalar(
                        select(func.count()).select_from(
                            EmailVerification
                        )
                    )

                assert pending_after == 1

                print(
                    "PASSOU: segunda solicitação bloqueada "
                    "com HTTP 429"
                )
                print(
                    "PASSOU: Retry-After =",
                    retry_after,
                    "segundos",
                )
                print(
                    "PASSOU: nenhum código adicional enviado"
                )

                print("PASSOU: código entregue ao emissor simulado")
                print("PASSOU: verificação temporária registrada")
                print("PASSOU: pesquisa definitiva não registrada")

            finally:
                if original_secret is None:
                    os.environ.pop(
                        "EMAIL_VERIFICATION_SECRET",
                        None,
                    )
                else:
                    os.environ[
                        "EMAIL_VERIFICATION_SECRET"
                    ] = original_secret

    finally:
        main.app.dependency_overrides.clear()
        main.SessionLocal = original_session
        engine.dispose()


if __name__ == "__main__":
    test_request()
