"""Política de frequência para solicitações de verificação."""

from datetime import datetime, timedelta, timezone
from math import ceil

from sqlalchemy import select

from verification_models import EmailVerification


MIN_REQUEST_INTERVAL_SECONDS = 60
MAX_REQUESTS_PER_HOUR = 5
REQUEST_WINDOW_SECONDS = 3600


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def retry_after_seconds(db, cnpj: str) -> int:
    """Retorna 0 se uma nova solicitação estiver permitida."""

    now = datetime.now(timezone.utc)
    window_start = now - timedelta(
        seconds=REQUEST_WINDOW_SECONDS
    )

    statement = (
        select(EmailVerification.created_at)
        .where(
            EmailVerification.cnpj == cnpj,
            EmailVerification.created_at >= window_start,
        )
        .order_by(EmailVerification.created_at.desc())
    )

    timestamps = [
        _as_utc(value)
        for value in db.scalars(statement).all()
    ]

    if not timestamps:
        return 0

    waits = []

    interval_end = timestamps[0] + timedelta(
        seconds=MIN_REQUEST_INTERVAL_SECONDS
    )

    if interval_end > now:
        waits.append(
            ceil((interval_end - now).total_seconds())
        )

    if len(timestamps) >= MAX_REQUESTS_PER_HOUR:
        window_end = timestamps[
            MAX_REQUESTS_PER_HOUR - 1
        ] + timedelta(
            seconds=REQUEST_WINDOW_SECONDS
        )

        if window_end > now:
            waits.append(
                ceil((window_end - now).total_seconds())
            )

    return max(waits, default=0)
