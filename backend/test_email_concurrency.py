import os
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import sessionmaker

import main
from email_confirmation_routes import create_confirmation_router
from email_verification import (
    expiration_time,
    generate_salt,
    hash_code,
)
from test_email_confirmation import build_payload
from verification_models import EmailVerification, VerificationBase


def run_test():
    original_secret = os.environ.get("EMAIL_VERIFICATION_SECRET")
    os.environ["EMAIL_VERIFICATION_SECRET"] = (
        "segredo-exclusivo-para-teste-concorrente-123456789"
    )

    try:
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "concurrency.db"

            engine = create_engine(
                f"sqlite:///{database}",
                connect_args={
                    "check_same_thread": False,
                    "timeout": 10,
                },
            )

            try:
                main.Base.metadata.create_all(engine)
                VerificationBase.metadata.create_all(engine)

                with engine.begin() as connection:
                    connection.execute(text("""
                        CREATE UNIQUE INDEX ux_submissions_cnpj
                        ON submissions(cnpj)
                        WHERE cnpj IS NOT NULL
                    """))

                Session = sessionmaker(bind=engine)

                app = FastAPI()
                app.include_router(
                    create_confirmation_router(
                        Session,
                        main.Submission,
                        main.SurveyPayload,
                    )
                )

                survey = build_payload()
                verification_id = str(uuid4())
                code = "123456"
                salt = generate_salt()

                with Session() as db:
                    db.add(EmailVerification(
                        id=verification_id,
                        cnpj=survey.cnpj,
                        email=str(survey.email),
                        code_salt=salt,
                        code_hash=hash_code(code, salt),
                        payload=survey.model_dump(mode="json"),
                        attempts=0,
                        expires_at=expiration_time(),
                    ))
                    db.commit()

                def confirm():
                    with TestClient(app) as client:
                        response = client.post(
                            "/api/surveys/verification/confirm",
                            json={
                                "verification_id": verification_id,
                                "code": code,
                            },
                        )
                        return response.status_code, response.json()

                with ThreadPoolExecutor(max_workers=2) as executor:
                    futures = [
                        executor.submit(confirm)
                        for _ in range(2)
                    ]
                    results = [future.result() for future in futures]

                print("=== RESPOSTAS CONCORRENTES ===")
                for status, body in results:
                    print("HTTP:", status, body)

                with Session() as db:
                    total = db.scalar(
                        select(func.count()).select_from(
                            main.Submission
                        )
                    )
                    verification = db.get(
                        EmailVerification,
                        verification_id,
                    )

                print("\nPesquisas registradas:", total)
                print(
                    "Código consumido:",
                    verification.verified_at is not None,
                )

                assert total == 1
                assert verification.verified_at is not None
                assert sum(
                    status == 201 for status, _ in results
                ) == 1

                print(
                    "PASSOU: somente uma confirmação "
                    "registrou a pesquisa"
                )
                print("PASSOU: banco real não utilizado")
                # CENÁRIO 2 — Tentativas incorretas simultâneas
                wrong_id = str(uuid4())
                wrong_salt = generate_salt()

                with Session() as db:
                    db.add(EmailVerification(
                        id=wrong_id,
                        cnpj=survey.cnpj,
                        email=str(survey.email),
                        code_salt=wrong_salt,
                        code_hash=hash_code(
                            "654321",
                            wrong_salt,
                        ),
                        payload=survey.model_dump(mode="json"),
                        attempts=0,
                        expires_at=expiration_time(),
                    ))
                    db.commit()

                def wrong_attempt():
                    with TestClient(app) as client:
                        response = client.post(
                            "/api/surveys/verification/confirm",
                            json={
                                "verification_id": wrong_id,
                                "code": "123456",
                            },
                        )
                        return response.status_code

                with ThreadPoolExecutor(max_workers=4) as executor:
                    futures = [
                        executor.submit(wrong_attempt)
                        for _ in range(4)
                    ]
                    wrong_results = [
                        future.result()
                        for future in futures
                    ]

                print(
                    "Respostas incorretas simultâneas:",
                    wrong_results,
                )

                with Session() as db:
                    wrong_verification = db.get(
                        EmailVerification,
                        wrong_id,
                    )

                    total_after = db.scalar(
                        select(func.count()).select_from(
                            main.Submission
                        )
                    )

                print(
                    "Tentativas registradas:",
                    wrong_verification.attempts,
                )

                assert wrong_verification.attempts == 4
                assert wrong_verification.verified_at is None
                assert total_after == 1
                assert all(
                    status == 400
                    for status in wrong_results
                )

                print(
                    "PASSOU: quatro tentativas "
                    "incorretas contabilizadas"
                )
                print(
                    "PASSOU: nenhuma pesquisa "
                    "adicional registrada"
                )
                # CENÁRIO 3 — Duas verificações para o mesmo CNPJ
                duplicate_ids = [
                    str(uuid4()),
                    str(uuid4()),
                ]

                for verification_id in duplicate_ids:
                    salt = generate_salt()

                    with Session() as db:
                        db.add(EmailVerification(
                            id=verification_id,
                            cnpj=survey.cnpj,
                            email=str(survey.email),
                            code_salt=salt,
                            code_hash=hash_code(
                                "123456",
                                salt,
                            ),
                            payload=survey.model_dump(mode="json"),
                            attempts=0,
                            expires_at=expiration_time(),
                        ))
                        db.commit()

                def confirm_duplicate(verification_id):
                    with TestClient(app) as client:
                        response = client.post(
                            "/api/surveys/verification/confirm",
                            json={
                                "verification_id": verification_id,
                                "code": "123456",
                            },
                        )
                        return response.status_code

                with ThreadPoolExecutor(max_workers=2) as executor:
                    futures = [
                        executor.submit(
                            confirm_duplicate,
                            verification_id,
                        )
                        for verification_id in duplicate_ids
                    ]
                    duplicate_results = [
                        future.result()
                        for future in futures
                    ]

                print(
                    "Confirmações do mesmo CNPJ:",
                    duplicate_results,
                )

                with Session() as db:
                    final_total = db.scalar(
                        select(func.count()).select_from(
                            main.Submission
                        )
                    )

                assert final_total == 1
                assert duplicate_results.count(409) == 2

                print(
                    "PASSOU: CNPJ duplicado rejeitado"
                )
                print(
                    "PASSOU: índice UNIQUE preservou "
                    "a integridade da pesquisa"
                )
                # CENÁRIO 4 — Dois códigos disputam CNPJ livre
                free_cnpj = "98765432000279"

                free_payload = survey.model_copy(
                    update={"cnpj": free_cnpj}
                )

                free_ids = []
                free_codes = ["112233", "445566"]

                for code in free_codes:
                    verification_id = str(uuid4())
                    salt = generate_salt()

                    with Session() as db:
                        db.add(EmailVerification(
                            id=verification_id,
                            cnpj=free_cnpj,
                            email=str(free_payload.email),
                            code_salt=salt,
                            code_hash=hash_code(code, salt),
                            payload=free_payload.model_dump(
                                mode="json"
                            ),
                            attempts=0,
                            expires_at=expiration_time(),
                        ))
                        db.commit()

                    free_ids.append(verification_id)

                def confirm_free(verification_id, code):
                    with TestClient(app) as client:
                        response = client.post(
                            "/api/surveys/verification/confirm",
                            json={
                                "verification_id": verification_id,
                                "code": code,
                            },
                        )
                        return response.status_code

                # Duas confirmações simultâneas
                with ThreadPoolExecutor(max_workers=2) as executor:
                    futures = [
                        executor.submit(
                            confirm_free,
                            verification_id,
                            code,
                        )
                        for verification_id, code in zip(
                            free_ids,
                            free_codes,
                        )
                    ]

                    free_results = [
                        future.result()
                        for future in futures
                    ]

                with Session() as db:
                    free_total = db.scalar(
                        select(func.count())
                        .select_from(main.Submission)
                        .where(
                            main.Submission.cnpj == free_cnpj
                        )
                    )

                    all_total = db.scalar(
                        select(func.count())
                        .select_from(main.Submission)
                    )

                print(
                    "Disputa por CNPJ livre:",
                    free_results,
                )
                print(
                    "Registros para novo CNPJ:",
                    free_total,
                )
                print(
                    "Total de pesquisas:",
                    all_total,
                )

                assert sorted(free_results) == [201, 409]
                assert free_total == 1
                assert all_total == 2

                print(
                    "PASSOU: apenas uma verificação "
                    "registrou o novo CNPJ"
                )
                print(
                    "PASSOU: índice UNIQUE impediu "
                    "a duplicidade concorrente"
                )




            finally:
                engine.dispose()

    finally:
        if original_secret is None:
            os.environ.pop("EMAIL_VERIFICATION_SECRET", None)
        else:
            os.environ["EMAIL_VERIFICATION_SECRET"] = original_secret


if __name__ == "__main__":
    run_test()
