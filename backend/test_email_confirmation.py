import os
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import main
from email_confirmation_routes import create_confirmation_router
from email_verification import (
    expiration_time,
    generate_salt,
    hash_code,
)
from submission_factory import build_submission
from verification_models import EmailVerification, VerificationBase


def make_cnpj(base):
    def digit(numbers, weights):
        total = sum(int(n) * w for n, w in zip(numbers, weights))
        remainder = total % 11
        return str(0 if remainder < 2 else 11 - remainder)

    first = digit(
        base,
        [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2],
    )
    second = digit(
        base + first,
        [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2],
    )
    return base + first + second


def build_payload():
    answers = []

    for index, options in sorted(main.VALID_OPTIONS.items()):
        option = next(
            value
            for value in sorted(options)
            if not value.lower().startswith(("outro ", "outra "))
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

    return main.SurveyPayload.model_validate({
        "institution": "Instituição Teste",
        "cnpj": make_cnpj("987654320001"),
        "city": "Petrópolis",
        "respondent": "Responsável Teste",
        "role": "Gestão",
        "email": "teste@example.com",
        "phone": "(24) 99999-9999",
        "answers": answers,
        "privacy_accepted": True,
        "commercial_contact": False,
        "website": "",
    })


def run_test():
    original_secret = os.environ.get(
        "EMAIL_VERIFICATION_SECRET"
    )

    os.environ["EMAIL_VERIFICATION_SECRET"] = (
        "segredo-exclusivo-para-teste-automatizado-123456789"
    )

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    try:
        main.Base.metadata.create_all(engine)
        VerificationBase.metadata.create_all(engine)

        Session = sessionmaker(bind=engine)

        app = FastAPI()
        app.include_router(
            create_confirmation_router(
                Session,
                main.Submission,
                main.SurveyPayload,
            )
        )

        client = TestClient(app)
        survey = build_payload()

        code = "123456"
        salt = generate_salt()
        verification_id = str(uuid4())

        with Session() as db:
            db.add(
                EmailVerification(
                    id=verification_id,
                    cnpj=survey.cnpj,
                    email=str(survey.email),
                    code_salt=salt,
                    code_hash=hash_code(code, salt),
                    payload=survey.model_dump(mode="json"),
                    attempts=0,
                    expires_at=expiration_time(),
                )
            )
            db.commit()

        response = client.post(
            "/api/surveys/verification/confirm",
            json={
                "verification_id": verification_id,
                "code": code,
            },
        )

        print("Primeira confirmação:", response.status_code)
        print("Resposta:", response.json())

        assert response.status_code == 201

        with Session() as db:
            submissions = db.scalar(
                select(func.count()).select_from(
                    main.Submission
                )
            )
            verification = db.get(
                EmailVerification,
                verification_id,
            )

            assert submissions == 1
            assert verification.verified_at is not None

        print("PASSOU: pesquisa registrada após confirmação")

        repeated = client.post(
            "/api/surveys/verification/confirm",
            json={
                "verification_id": verification_id,
                "code": code,
            },
        )

        print("Segunda confirmação:", repeated.status_code)

        assert repeated.status_code == 410

        with Session() as db:
            submissions = db.scalar(
                select(func.count()).select_from(
                    main.Submission
                )
            )

        assert submissions == 1

        print("PASSOU: código não pode ser reutilizado")
        print("PASSOU: apenas uma pesquisa registrada")
        print("PASSOU: banco real não utilizado")
        # CENÁRIO 2 — Código incorreto
        wrong_id = str(uuid4())
        wrong_salt = generate_salt()

        with Session() as db:
            db.add(EmailVerification(
                id=wrong_id,
                cnpj=survey.cnpj,
                email=str(survey.email),
                code_salt=wrong_salt,
                code_hash=hash_code("654321", wrong_salt),
                payload=survey.model_dump(mode="json"),
                attempts=0,
                expires_at=expiration_time(),
            ))
            db.commit()

        for attempt in range(1, 6):
            response = client.post(
                "/api/surveys/verification/confirm",
                json={
                    "verification_id": wrong_id,
                    "code": "123456",
                },
            )

            expected = 429 if attempt == 5 else 400

            print(
                f"Tentativa incorreta {attempt}:",
                response.status_code,
            )

            assert response.status_code == expected

        with Session() as db:
            verification = db.get(
                EmailVerification,
                wrong_id,
            )
            assert verification.attempts == 5
            assert verification.verified_at is None

        print("PASSOU: bloqueio após cinco tentativas")

        # CENÁRIO 3 — Código expirado
        from datetime import datetime, timedelta, timezone

        expired_id = str(uuid4())
        expired_salt = generate_salt()

        with Session() as db:
            db.add(EmailVerification(
                id=expired_id,
                cnpj=survey.cnpj,
                email=str(survey.email),
                code_salt=expired_salt,
                code_hash=hash_code("123456", expired_salt),
                payload=survey.model_dump(mode="json"),
                attempts=0,
                expires_at=(
                    datetime.now(timezone.utc)
                    - timedelta(minutes=1)
                ),
            ))
            db.commit()

        response = client.post(
            "/api/surveys/verification/confirm",
            json={
                "verification_id": expired_id,
                "code": "123456",
            },
        )

        print("Código expirado:", response.status_code)

        assert response.status_code == 410

        with Session() as db:
            verification = db.get(
                EmailVerification,
                expired_id,
            )
            assert verification.verified_at is None

        print("PASSOU: código expirado rejeitado")

        # Nenhuma tentativa inválida pode registrar pesquisa.
        with Session() as db:
            total = db.scalar(
                select(func.count()).select_from(
                    main.Submission
                )
            )

        assert total == 1

        print("PASSOU: nenhuma pesquisa adicional registrada")


    finally:
        engine.dispose()

        if original_secret is None:
            os.environ.pop(
                "EMAIL_VERIFICATION_SECRET",
                None,
            )
        else:
            os.environ[
                "EMAIL_VERIFICATION_SECRET"
            ] = original_secret


if __name__ == "__main__":
    run_test()
