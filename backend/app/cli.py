import argparse
import getpass
import re
from pydantic import TypeAdapter, EmailStr
from sqlalchemy.exc import IntegrityError
from .auth import hasher
from .common import audit
from .db import SessionLocal
from .models import Business, User

def main():
    parser = argparse.ArgumentParser(description="Criar um negócio e seu primeiro gestor")
    parser.add_argument("--business", required=True, help="Identificador minúsculo, sem espaços")
    parser.add_argument("--name", required=True, help="Nome do negócio")
    parser.add_argument("--email", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,79}", args.business) or not 1 <= len(args.name.strip()) <= 160:
        parser.error("Identificador ou nome inválido")
    email = str(TypeAdapter(EmailStr).validate_python(args.email)).lower()
    password = getpass.getpass("Senha do gestor (12 a 128 caracteres): ")
    if not 12 <= len(password) <= 128 or password != getpass.getpass("Confirme a senha: "):
        parser.error("Senha inválida ou confirmação diferente")
    try:
        with SessionLocal.begin() as db:
            business = Business(slug=args.business, name=args.name.strip())
            db.add(business)
            db.flush()
            user = User(business_id=business.id, email=email, password_hash=hasher.hash(password), role="gestor")
            db.add(user)
            db.flush()
            audit(db, user, "business.created", business)
    except IntegrityError:
        parser.exit(1, "Negócio já cadastrado. Nenhum dado foi alterado.\n")
    print("Negócio e gestor criados.")

if __name__ == "__main__":
    main()
