from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    JSON,
    String,
)

from sqlalchemy.orm import declarative_base


VerificationBase = declarative_base()


class EmailVerification(VerificationBase):
    __tablename__ = "email_verifications"

    id = Column(String(36), primary_key=True)

    cnpj = Column(String(14), nullable=False, index=True)
    email = Column(String(320), nullable=False)

    code_salt = Column(String(32), nullable=False)
    code_hash = Column(String(64), nullable=False)

    payload = Column(JSON, nullable=False)

    attempts = Column(Integer, nullable=False, default=0)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    expires_at = Column(
        DateTime(timezone=True),
        nullable=False,
    )

    verified_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )
