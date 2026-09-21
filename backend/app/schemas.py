from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints, field_validator, model_validator
from .documents import normalize_document, valid_cnpj, valid_cpf

class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

class LoginInput(Input):
    business: str = Field(min_length=1, max_length=80)
    email: EmailStr
    password: Annotated[str, StringConstraints(strip_whitespace=False)] = Field(min_length=1, max_length=128)

class SpecialtyInput(Input):
    name: str = Field(min_length=1, max_length=120)
    active: bool = True

class ClientInput(Input):
    name: str = Field(min_length=1, max_length=160)
    contact: str = Field(default="", max_length=160)
    active: bool = True

class ServiceInput(SpecialtyInput):
    specialty_id: int = Field(gt=0)
    price_cents: int = Field(ge=0, le=100_000_000, strict=True)

class ProfessionalInput(ClientInput):
    commission_bps: int = Field(ge=0, le=10000, strict=True)
    engagement: Literal["MEI", "autonomo", "CLT"]
    cpf: str | None = None
    cnpj: str | None = None
    specialty_ids: list[int] = Field(min_length=1, max_length=100)
    email: EmailStr
    password: Annotated[str, StringConstraints(strip_whitespace=False)] | None = Field(default=None, min_length=12, max_length=128)

    @field_validator("cpf", "cnpj", mode="before")
    @classmethod
    def normalize(cls, value):
        return normalize_document(value)

    @model_validator(mode="after")
    def documents(self):
        if self.cpf and not valid_cpf(self.cpf):
            raise ValueError("CPF invÃ¡lido")
        if self.cnpj and not valid_cnpj(self.cnpj):
            raise ValueError("CNPJ invÃ¡lido")
        if self.engagement == "MEI" and not self.cnpj:
            raise ValueError("CNPJ obrigatÃ³rio para MEI")
        if self.engagement != "MEI" and not self.cpf:
            raise ValueError("CPF obrigatÃ³rio para autÃ´nomo ou CLT")
        self.specialty_ids = sorted(set(self.specialty_ids))
        return self

class AttendanceInput(Input):
    professional_id: int = Field(gt=0)
    client_id: int | None = Field(default=None, gt=0)
    service_id: int = Field(gt=0)
    payment_method: Literal["pix", "dinheiro", "credito", "debito"]

class ReviewInput(Input):
    decision: Literal["approved", "rejected"]
    reason: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def reason_required(self):
        if self.decision == "rejected" and not self.reason:
            raise ValueError("Informe o motivo da rejeiÃ§Ã£o")
        return self

class PayoutInput(Input):
    attendance_ids: list[int] = Field(min_length=1, max_length=200)
    reference: str = Field(min_length=1, max_length=200)
