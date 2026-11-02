from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError

from email_verification import (
    MAX_VERIFICATION_ATTEMPTS,
    is_expired,
    verify_code,
)
from submission_factory import build_submission
from verification_models import EmailVerification
from verification_schemas import EmailConfirmationPayload


def create_confirmation_router(
    session_factory,
    submission_model,
    survey_payload_model,
):
    router = APIRouter()

    @router.post(
        "/api/surveys/verification/confirm",
        status_code=201,
    )
    def confirm_email(payload: EmailConfirmationPayload):
        db = session_factory()

        try:
            verification = db.get(
                EmailVerification,
                str(payload.verification_id),
            )

            if verification is None:
                raise HTTPException(
                    status_code=404,
                    detail="Verificação não encontrada.",
                )

            if verification.verified_at is not None:
                raise HTTPException(
                    status_code=410,
                    detail="Código já utilizado.",
                )

            if is_expired(verification.expires_at):
                raise HTTPException(
                    status_code=410,
                    detail="Código expirado.",
                )

            if verification.attempts >= MAX_VERIFICATION_ATTEMPTS:
                raise HTTPException(
                    status_code=429,
                    detail="Limite de tentativas excedido.",
                )

            if not verify_code(
                payload.code,
                verification.code_salt,
                verification.code_hash,
            ):
                now = datetime.now(timezone.utc)

                result = db.execute(
                    update(EmailVerification)
                    .where(
                        EmailVerification.id == verification.id,
                        EmailVerification.verified_at.is_(None),
                        EmailVerification.expires_at > now,
                        EmailVerification.attempts
                        < MAX_VERIFICATION_ATTEMPTS,
                    )
                    .values(
                        attempts=EmailVerification.attempts + 1
                    )
                    .execution_options(synchronize_session=False)
                )

                if result.rowcount != 1:
                    db.rollback()
                    raise HTTPException(
                        status_code=409,
                        detail="Verificação não está mais disponível.",
                    )

                db.commit()
                db.refresh(verification)
                attempts = verification.attempts

                if attempts >= MAX_VERIFICATION_ATTEMPTS:
                    raise HTTPException(
                        status_code=429,
                        detail="Limite de tentativas excedido.",
                    )

                raise HTTPException(
                    status_code=400,
                    detail="Código inválido.",
                )

            survey = survey_payload_model.model_validate(
                verification.payload
            )

            if (
                survey.cnpj != verification.cnpj
                or str(survey.email) != verification.email
            ):
                raise HTTPException(
                    status_code=409,
                    detail="Dados da verificação inconsistentes.",
                )

            now = datetime.now(timezone.utc)

            # Atualização condicional para impedir que duas
            # confirmações consumam a mesma verificação.
            result = db.execute(
                update(EmailVerification)
                .where(
                    EmailVerification.id == verification.id,
                    EmailVerification.verified_at.is_(None),
                    EmailVerification.attempts
                    < MAX_VERIFICATION_ATTEMPTS,
                    EmailVerification.expires_at > now,
                )
                .values(verified_at=now)
                .execution_options(synchronize_session=False)
            )

            if result.rowcount != 1:
                db.rollback()
                raise HTTPException(
                    status_code=409,
                    detail="Verificação não está mais disponível.",
                )

            item = build_submission(
                survey,
                submission_model,
            )

            db.add(item)
            db.commit()

            return {
                "received": True,
                "id": item.id,
            }

        except HTTPException:
            db.rollback()
            raise

        except IntegrityError:
            db.rollback()
            raise HTTPException(
                status_code=409,
                detail="Esta unidade já respondeu à pesquisa.",
            )

        except Exception:
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Falha ao confirmar verificação.",
            )

        finally:
            db.close()

    return router
