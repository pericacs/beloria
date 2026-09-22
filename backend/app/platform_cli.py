"""Explicit server-only creation of a NEW platform administrator, never promotion by email."""
import argparse
import getpass
from fastapi import HTTPException
from pydantic import EmailStr, TypeAdapter
from .accounts import create_identity
from .db import SessionLocal
from .commercial_models import PlatformAdmin, PlatformAudit


def main():
    parser=argparse.ArgumentParser(description='Criar administrador Beloria sem vínculo com empresa cliente')
    parser.add_argument('--email')
    args=parser.parse_args()
    email=str(TypeAdapter(EmailStr).validate_python(args.email or input('E-mail do administrador Beloria: ').strip()))
    password=getpass.getpass('Senha (12 a 128 caracteres): ')
    if not 12<=len(password)<=128 or password!=getpass.getpass('Confirme a senha: '): parser.error('Senha inválida ou confirmação diferente')
    try:
        with SessionLocal.begin() as db:
            account=create_identity(db,email,password)
            db.add(PlatformAdmin(identity_id=account.id))
            db.add(PlatformAudit(identity_id=account.id,action='platform_admin.created_by_server',details={}))
    except HTTPException as exc: parser.exit(1,exc.detail+'\n')
    print('Administrador Beloria criado. Entre com e-mail e senha em /beloria.')

if __name__=='__main__': main()
