from datetime import datetime, timezone
from pathlib import Path
import os
from uuid import uuid4
import re

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from sqlalchemy import create_engine, Column, String, DateTime, JSON, text
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.exc import IntegrityError
from cnpj import normalize_cnpj, valid_cnpj
from email_sender import EmailDeliveryError, EmailSender, get_email_sender
from email_verification import (
    expiration_time,
    generate_code,
    generate_salt,
    hash_code,
)
from survey_repository import cnpj_already_submitted
from verification_rate_limit import retry_after_seconds
from verification_models import EmailVerification
from email_confirmation_routes import create_confirmation_router

DEFAULT_DATABASE_PATH = (
    Path(__file__).resolve().parent / "pesquisa.db"
)

DATABASE_PATH = Path(
    os.environ.get(
        "IST_PESQUISA_DATABASE_PATH",
        str(DEFAULT_DATABASE_PATH),
    )
).expanduser().resolve()

DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class Submission(Base):
    __tablename__ = "submissions"

    id = Column(String, primary_key=True)
    created_at = Column(DateTime(timezone=True), nullable=False)
    institution = Column(String, nullable=False)
    cnpj = Column(String(14), nullable=True)
    city = Column(String, nullable=False)
    respondent = Column(String, nullable=False)
    role = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    answers = Column(JSON, nullable=False)
    privacy_accepted = Column(String, nullable=False)
    commercial_contact = Column(String, nullable=False)

Base.metadata.create_all(bind=engine)

app = FastAPI(title="IST Pesquisa API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5175"],
    allow_credentials=False,
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type"],
)


VALID_OPTIONS = {
    0: {
        "Hospital privado",
        "Clínica médica",
        "Laboratório de análises ou diagnóstico",
        "Consultório médico",
        "Outro estabelecimento privado de saúde",
    },
    1: {
        "Acesso ao histórico clínico completo dos pacientes",
        "Informações clínicas dispersas em diferentes sistemas ou registros",
        "Agendamento e faltas de pacientes",
        "Produção de relatórios e indicadores",
        "Processos manuais e retrabalho",
        "Segurança e proteção de dados",
        "Outra dificuldade",
    },
    2: {
        "Prontuário eletrônico integrado",
        "Prontuário eletrônico sem integração externa",
        "Sistema próprio e planilhas",
        "Registros em papel",
        "Outro modelo",
    },
    3: {
        "Sim, frequentemente",
        "Sim, ocasionalmente",
        "Raramente",
        "Não enfrentamos essa dificuldade",
        "Não sei informar",
    },
    4: {
        "Muito alta",
        "Alta",
        "Média",
        "Baixa",
        "Não é uma prioridade",
    },
    5: {
        "Sim, temos interesse",
        "Talvez, dependendo da solução",
        "Não temos interesse",
        "Precisamos entender melhor",
    },
    6: {
        "Até 100 atendimentos",
        "101 a 500 atendimentos",
        "501 a 2.000 atendimentos",
        "2.001 a 5.000 atendimentos",
        "5.001 a 10.000 atendimentos",
        "Mais de 10.000 atendimentos",
    },
    7: {
        "Sim",
        "Não",
        "Gostaria de conversar para identificar oportunidades",
    },
}

class Answer(BaseModel):
    question: int = Field(ge=0, le=8)
    selections: list[str] = Field(min_length=1)
    other_detail: str | None = Field(default=None, max_length=1000)

    @field_validator("selections")
    @classmethod
    def valid_selections(cls, value):
        if any(not option.strip() for option in value):
            raise ValueError("Alternativa vazia")
        if len(value) != len(set(value)):
            raise ValueError("Alternativas duplicadas")
        return value

class SurveyPayload(BaseModel):
    institution: str = Field(min_length=2, max_length=200)
    cnpj: str = Field(min_length=14, max_length=18)
    city: str = Field(min_length=2, max_length=120)
    respondent: str = Field(min_length=2, max_length=150)
    role: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: str = Field(min_length=10, max_length=25)
    answers: list[Answer] = Field(min_length=9, max_length=9)
    privacy_accepted: bool
    commercial_contact: bool = False
    website: str = Field(default="", max_length=100)

    @field_validator("institution", "city", "respondent", "role")
    @classmethod
    def not_blank(cls, value):
        if not value.strip():
            raise ValueError("Campo obrigatório")
        return value.strip()

    @field_validator("cnpj")
    @classmethod
    def validate_cnpj(cls, value):
        if not valid_cnpj(value):
            raise ValueError("CNPJ inválido")
        return normalize_cnpj(value)

    @field_validator("phone")
    @classmethod
    def valid_phone(cls, value):
        digits = re.sub(r"\D", "", value)
        if not 10 <= len(digits) <= 13:
            raise ValueError("Telefone inválido")
        return value

    @model_validator(mode="after")
    def validate_survey(self):
        if not self.privacy_accepted:
            raise ValueError(
                "É necessário confirmar a ciência do aviso de privacidade"
            )

        indices = [answer.question for answer in self.answers]

        if sorted(indices) != list(range(9)):
            raise ValueError(
                "Todas as nove perguntas devem ser respondidas"
            )

        for answer in self.answers:
            if answer.question == 8:
                if len(answer.selections) != 1:
                    raise ValueError(
                        "A pergunta aberta exige uma única resposta"
                    )

                text = answer.selections[0].strip()

                if not 10 <= len(text) <= 2000:
                    raise ValueError(
                        "A descrição deve conter entre 10 e 2000 caracteres"
                    )

                if answer.other_detail is not None:
                    raise ValueError(
                        "Descrição adicional não permitida"
                    )

                continue

            allowed = VALID_OPTIONS[answer.question]

            if not set(answer.selections).issubset(allowed):
                raise ValueError(
                    f"Alternativa inválida na pergunta {answer.question + 1}"
                )

            if answer.question != 1 and len(answer.selections) != 1:
                raise ValueError(
                    "Apenas a pergunta 2 permite múltiplas alternativas"
                )

            has_other = any(
                option.strip().lower().startswith(("outro ", "outra "))
                for option in answer.selections
            )

            detail = (answer.other_detail or "").strip()

            if has_other and len(detail) < 5:
                raise ValueError(
                    "A alternativa Outro exige descrição com pelo menos 5 caracteres"
                )

            if not has_other and answer.other_detail is not None:
                raise ValueError(
                    "Descrição adicional sem alternativa Outro"
                )

        return self

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/api/surveys", status_code=403)
def submit(payload: SurveyPayload):
    """Bloqueia submissões sem confirmação de e-mail."""
    raise HTTPException(
        status_code=403,
        detail=(
            "Confirmação de e-mail obrigatória. "
            "Utilize o fluxo de verificação."
        ),
    )


@app.post("/api/surveys/verification/request", status_code=202)
def request_email_verification(
    payload: SurveyPayload,
    sender: EmailSender = Depends(get_email_sender),
):
    if payload.website:
        return {"received": True}

    db = SessionLocal()

    try:
        # Reserva a escrita antes de consultar o limite.
        # Impede duas solicitações simultâneas de passarem
        # pela verificação usando o mesmo estado do banco.
        db.execute(text("BEGIN IMMEDIATE"))

        if cnpj_already_submitted(db, payload.cnpj, Submission):
            raise HTTPException(
                status_code=409,
                detail="Esta unidade já respondeu à pesquisa.",
            )

        retry_after = retry_after_seconds(db, payload.cnpj)

        if retry_after > 0:
            raise HTTPException(
                status_code=429,
                detail=(
                    "Muitas solicitações de verificação. "
                    "Aguarde antes de solicitar outro código."
                ),
                headers={"Retry-After": str(retry_after)},
            )

        code = generate_code()
        salt = generate_salt()

        verification = EmailVerification(
            id=str(uuid4()),
            cnpj=payload.cnpj,
            email=str(payload.email),
            code_salt=salt,
            code_hash=hash_code(code, salt),
            payload=payload.model_dump(mode="json"),
            attempts=0,
            expires_at=expiration_time(),
        )

        db.add(verification)

        # Libera a transação antes da operação externa.
        db.commit()

        try:
            sender.send_verification_code(
                recipient=str(payload.email),
                code=code,
            )
        except EmailDeliveryError:
            raise HTTPException(
                status_code=503,
                detail="Serviço de verificação temporariamente indisponível.",
            )

        return {
            "verification_id": verification.id,
            "expires_in_seconds": 600,
        }

    except HTTPException:
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Conflito ao solicitar verificação.",
        )
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Falha ao solicitar verificação.",
        )
    finally:
        db.close()


app.include_router(
    create_confirmation_router(
        SessionLocal,
        Submission,
        SurveyPayload,
    )
)
