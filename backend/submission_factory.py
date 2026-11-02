from datetime import datetime, timezone
from uuid import uuid4


def build_submission(payload, submission_model):
    """Constrói uma pesquisa validada, sem gravá-la no banco."""

    return submission_model(
        id=str(uuid4()),
        created_at=datetime.now(timezone.utc),
        institution=payload.institution,
        cnpj=payload.cnpj,
        city=payload.city,
        respondent=payload.respondent,
        role=payload.role,
        email=str(payload.email),
        phone=payload.phone,
        answers=[
            answer.model_dump()
            for answer in payload.answers
        ],
        privacy_accepted="true",
        commercial_contact=str(
            payload.commercial_contact
        ).lower(),
    )
