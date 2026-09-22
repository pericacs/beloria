from datetime import timedelta
from typing import Annotated, Literal
from pydantic import EmailStr, Field, StringConstraints, field_validator, model_validator
from .schemas import Input
from .documents import normalize_document, valid_cpf, valid_cnpj

Secret = Annotated[str, StringConstraints(strip_whitespace=False, min_length=12, max_length=128)]

class CompanySignup(Input):
    company_name: str = Field(min_length=1,max_length=160)
    responsible_name: str = Field(min_length=1,max_length=160)
    contact: str = Field(default='',max_length=160)
    email: EmailStr
    password: Secret

class SpecialistProfile(Input):
    name: str = Field(min_length=1,max_length=160)
    contact: str = Field(default='',max_length=160)
    engagement: Literal['MEI','autonomo','CLT']
    cpf: str | None = None
    cnpj: str | None = None

    @field_validator('cpf','cnpj',mode='before')
    @classmethod
    def normalize(cls,value):
        return normalize_document(value)

    @model_validator(mode='after')
    def documents(self):
        if self.cpf and not valid_cpf(self.cpf): raise ValueError('CPF inválido')
        if self.cnpj and not valid_cnpj(self.cnpj): raise ValueError('CNPJ inválido')
        if self.engagement == 'MEI' and not self.cnpj: raise ValueError('CNPJ obrigatório para MEI')
        if self.engagement != 'MEI' and not self.cpf: raise ValueError('CPF obrigatório para autônomo ou CLT')
        return self

class SpecialistSignup(SpecialistProfile):
    email: EmailStr
    password: Secret

class JoinReview(Input):
    decision: Literal['approved','rejected']
    reason: str | None = Field(default=None,max_length=500)
    specialty_ids: list[int] = Field(default_factory=list,max_length=100)
    commission_bps: int | None = Field(default=None,ge=0,le=10000,strict=True)

    @model_validator(mode='after')
    def required(self):
        if self.decision=='rejected' and not self.reason: raise ValueError('Informe o motivo da rejeição')
        if self.decision=='approved' and (not self.specialty_ids or self.commission_bps is None): raise ValueError('Defina especialidades e comissão para aprovar')
        self.specialty_ids=sorted(set(self.specialty_ids))
        return self

class InviteInput(Input):
    valid_days: int = Field(default=7,ge=1,le=30)

class BusinessAccessInput(Input):
    access_blocked: bool
    reason: str = Field(min_length=1,max_length=500)
