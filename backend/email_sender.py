import logging
import os
from typing import Protocol

import boto3
from fastapi import HTTPException
from botocore.exceptions import BotoCoreError, ClientError


class EmailDeliveryError(Exception):
    """Falha ao entregar uma mensagem de verificação."""


class EmailSender(Protocol):
    def send_verification_code(
        self,
        recipient: str,
        code: str,
    ) -> None:
        ...


class DisabledEmailSender:
    """Bloqueia envios enquanto não houver provedor configurado."""

    def send_verification_code(
        self,
        recipient: str,
        code: str,
    ) -> None:
        raise EmailDeliveryError(
            "Provedor de e-mail ainda não configurado"
        )



logger = logging.getLogger(__name__)


class SESEmailSender:
    """Envia códigos de verificação usando Amazon SES."""

    def __init__(self, region: str, sender_email: str):
        self.sender_email = sender_email
        self.client = boto3.client(
            "ses",
            region_name=region,
        )

    def send_verification_code(
        self,
        recipient: str,
        code: str,
    ) -> None:
        try:
            self.client.send_email(
                Source=self.sender_email,
                Destination={
                    "ToAddresses": [recipient],
                },
                Message={
                    "Subject": {
                        "Data": "IST Pesquisa - Código de verificação",
                        "Charset": "UTF-8",
                    },
                    "Body": {
                        "Text": {
                            "Data": (
                                "Seu código de verificação é: "
                                f"{code}\n\n"
                                "Este código expira em 10 minutos.\n"
                                "Se você não solicitou este código, "
                                "ignore esta mensagem."
                            ),
                            "Charset": "UTF-8",
                        },
                    },
                },
            )
        except (BotoCoreError, ClientError) as exc:
            logger.error(
                "Falha no envio do código pelo Amazon SES: %s",
                type(exc).__name__,
            )
            raise EmailDeliveryError(
                "Falha no envio pelo Amazon SES"
            ) from exc


def get_email_sender() -> EmailSender:
    """Retorna o provedor configurado para a aplicação."""
    provider = os.environ.get(
        "EMAIL_PROVIDER", "disabled"
    ).strip().lower()

    if provider != "ses":
        return DisabledEmailSender()

    region = os.environ.get("AWS_REGION", "").strip()
    sender_email = os.environ.get(
        "SES_SENDER_EMAIL", ""
    ).strip()

    if not region or not sender_email:
        raise HTTPException(
            status_code=503,
            detail="Serviço de verificação temporariamente indisponível.",
        )

    return SESEmailSender(
        region=region,
        sender_email=sender_email,
    )
