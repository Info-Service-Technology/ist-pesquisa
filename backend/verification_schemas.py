from pydantic import BaseModel, Field, field_validator
from uuid import UUID


class EmailConfirmationPayload(BaseModel):
    verification_id: UUID
    code: str = Field(min_length=6, max_length=6)

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str) -> str:
        if not value.isascii() or not value.isdigit():
            raise ValueError(
                "O código deve conter exatamente seis dígitos ASCII"
            )
        return value
