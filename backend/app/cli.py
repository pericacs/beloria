import argparse
from datetime import timedelta
import getpass
import re
from fastapi import HTTPException
from pydantic import TypeAdapter, EmailStr
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from .accounts import change_credentials, create_identity, membership
from .common import audit
from .db import SessionLocal
from .models import Business, Identity, Professional, User, now


def main():
    parser = argparse.ArgumentParser(description="Administrar identidades e vínculos do Beloria (acesso ao servidor necessário)")
    parser.add_argument('--business', help='Identificador interno para criação de negócio; nunca usado no login')
    parser.add_argument('--name', help='Nome do novo negócio')
    parser.add_argument('--email', help='E-mail para uma nova identidade')
    parser.add_argument('--identity-id', type=int, help='Identidade existente, selecionada explicitamente após verificar a titularidade')
    parser.add_argument('--link-business', help='Vincular a identidade a um negócio existente (identificador interno)')
    parser.add_argument('--role', choices=['gestor','profissional'], default='gestor')
    parser.add_argument('--professional-id', type=int)
    parser.add_argument('--list-conflicts', action='store_true')
    parser.add_argument('--set-email', help='Regularizar/alterar o e-mail da identidade selecionada, sem unir contas')
    args = parser.parse_args()
    try:
        with SessionLocal.begin() as db:
            if args.list_conflicts:
                for account in db.scalars(select(Identity).where(Identity.login_enabled.is_(False)).order_by(Identity.id)):
                    names = db.scalars(select(Business.name).join(User, User.business_id == Business.id).where(User.identity_id == account.id)).all()
                    print(f'Identidade {account.id}: {account.email} | {", ".join(names)}')
                return
            account = db.scalar(select(Identity).where(Identity.id == args.identity_id).with_for_update()) if args.identity_id else None
            if args.identity_id and not account:
                parser.error('Identidade não encontrada')
            if args.set_email:
                if not account or args.business or args.link_business or args.email:
                    parser.error('Use somente --identity-id e --set-email para regularizar')
                email = str(TypeAdapter(EmailStr).validate_python(args.set_email))
                change_credentials(db, account, email)
                for user in db.scalars(select(User).where(User.identity_id == account.id)):
                    audit(db, user, 'identity.email_updated_by_system_admin', user, {'identity_id': account.id})
                print('E-mail atualizado; contas mantidas separadas e sessões revogadas.')
                return
            if args.link_business:
                if not account or args.business or args.email:
                    parser.error('Use --identity-id e --link-business para um vínculo explícito')
                business = db.scalar(select(Business).where(Business.slug == args.link_business))
                if not business:
                    parser.error('Negócio não encontrado')
            else:
                if not args.business or not re.fullmatch(r'[a-z0-9][a-z0-9-]{1,79}', args.business) or not args.name or not 1 <= len(args.name.strip()) <= 160:
                    parser.error('Informe --business e --name válidos para criar o negócio')
                start = now()
                business = Business(slug=args.business, name=args.name.strip(), trial_started_at=start, trial_ends_at=start+timedelta(days=15))
                db.add(business)
                db.flush()
            if account:
                if args.email or not account.login_enabled:
                    parser.error('Não informe --email com --identity-id; regularize identidades bloqueadas antes de vinculá-las')
            else:
                if not args.email:
                    parser.error('Informe --email para criar uma identidade ou --identity-id para um vínculo explícito')
                email = str(TypeAdapter(EmailStr).validate_python(args.email))
                password = getpass.getpass('Senha (12 a 128 caracteres): ')
                if not 12 <= len(password) <= 128 or password != getpass.getpass('Confirme a senha: '):
                    parser.error('Senha inválida ou confirmação diferente')
                account = create_identity(db, email, password)
            if args.role == 'profissional':
                professional = db.scalar(select(Professional).where(Professional.id == args.professional_id, Professional.business_id == business.id))
                if not professional:
                    parser.error('Profissional deve pertencer ao negócio selecionado')
            elif args.professional_id:
                parser.error('Gestor não recebe --professional-id')
            user = membership(db, account, business.id, args.role, args.professional_id)
            audit(db, user, 'membership.created_by_system_admin', user, {'identity_id': account.id})
            print(f'Vínculo criado. Identidade: {account.id}. Login: e-mail e senha.')
    except HTTPException as exc:
        parser.exit(1, exc.detail+'\n')
    except IntegrityError:
        parser.exit(1, 'Negócio, e-mail ou vínculo já cadastrado. Nenhum dado foi alterado.\n')


if __name__ == '__main__':
    main()
