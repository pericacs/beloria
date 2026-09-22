"""Read-only report safe before the commercial migration; no credentials printed."""
from sqlalchemy import text
from .db import engine


def main():
    with engine.connect() as db:
        rows=db.execute(text("SELECT identity_id, count(DISTINCT business_id) AS companies FROM users GROUP BY identity_id HAVING count(DISTINCT business_id)>1 AND bool_or(role='profissional') ORDER BY identity_id")).all()
        print(f'Identidades de especialistas com conflitos: {len(rows)}')
        for identity_id,count in rows:
            print(f'Identidade #{identity_id}: {count} empresas; preservar vínculos e revisar individualmente.')
        print('A migração sinaliza conflitos e bloqueia o acesso dessas identidades; não remove vínculos.')
        print('Empresas anteriores: acesso legado para revisão de contratação, sem novo trial.')


if __name__=='__main__':
    main()
