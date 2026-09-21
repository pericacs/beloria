from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from . import auth, catalog, finance, reporting
from .db import engine

app = FastAPI(title="Beloria", version="0.1.0")
for router in (auth.router, catalog.router, finance.router, reporting.router):
    app.include_router(router, prefix="/api")

@app.middleware("http")
async def response_security(request: Request, call_next):
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    return response

@app.exception_handler(IntegrityError)
async def conflict(request: Request, exc: IntegrityError):
    return JSONResponse(status_code=409, content={"detail": "Conflito de cadastro ou operaÃ§Ã£o jÃ¡ registrada. Confira os dados."})

@app.get("/api/health")
def health():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ok"}

@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    fields = {"name": "nome", "email": "e-mail", "password": "senha", "cpf": "CPF", "cnpj": "CNPJ", "commission_bps": "comissão", "specialty_ids": "especialidades", "price_cents": "preço", "reason": "motivo", "reference": "referência", "start": "data inicial", "end": "data final"}
    messages = []
    for error in exc.errors():
        label = fields.get(str(error["loc"][-1]), "dados informados")
        if error["type"] == "value_error" and error.get("ctx", {}).get("error"):
            messages.append(str(error["ctx"]["error"]))
        elif error["type"] == "missing":
            messages.append(f"Preencha o campo {label}.")
        else:
            messages.append(f"Confira o campo {label}: valor inválido ou fora dos limites permitidos.")
    return JSONResponse(status_code=422, content={"detail": " ".join(messages)})
