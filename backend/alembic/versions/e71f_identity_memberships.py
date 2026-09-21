"""Separate login identity from business membership without merging accounts."""
from alembic import op
import sqlalchemy as sa

revision = 'e71f_identity_memberships'
down_revision = 'ddd468014c2d'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('identities',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('email', sa.String(254), nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('login_enabled', sa.Boolean(), nullable=False))
    op.create_index('ix_identities_email', 'identities', ['email'])
    # One identity per old user, even when email/password hashes happen to match.
    op.execute('''INSERT INTO identities (id, email, password_hash, login_enabled)
        SELECT id, lower(trim(email)), password_hash,
            count(*) OVER (PARTITION BY lower(trim(email))) = 1
        FROM users''')
    op.execute("SELECT setval(pg_get_serial_sequence('identities','id'), COALESCE((SELECT max(id) FROM identities),1), EXISTS(SELECT 1 FROM identities))")
    op.create_index('uq_identity_login_email', 'identities', ['email'], unique=True, postgresql_where=sa.text('login_enabled'))
    op.add_column('users', sa.Column('identity_id', sa.Integer(), nullable=True))
    op.execute('UPDATE users SET identity_id = id')
    op.alter_column('users', 'identity_id', nullable=False)
    op.create_foreign_key('fk_users_identity', 'users', 'identities', ['identity_id'], ['id'])
    op.create_index('ix_users_identity_id', 'users', ['identity_id'])
    op.create_unique_constraint('uq_user_identity_id', 'users', ['identity_id','id'])
    op.create_unique_constraint('uq_identity_business', 'users', ['identity_id','business_id'])
    # Old sessions must not cross the change of authentication model.
    op.execute('DELETE FROM auth_sessions')
    op.add_column('auth_sessions', sa.Column('identity_id', sa.Integer(), nullable=False))
    op.alter_column('auth_sessions', 'user_id', nullable=True)
    op.create_foreign_key('fk_session_identity', 'auth_sessions', 'identities', ['identity_id'], ['id'])
    op.create_foreign_key('fk_session_membership_identity', 'auth_sessions', 'users', ['identity_id','user_id'], ['identity_id','id'])


def downgrade():
    # Mirrors keep current credentials, roles and all financial/audit IDs intact.
    op.execute('DELETE FROM auth_sessions')
    op.drop_constraint('fk_session_membership_identity', 'auth_sessions', type_='foreignkey')
    op.drop_constraint('fk_session_identity', 'auth_sessions', type_='foreignkey')
    op.drop_column('auth_sessions', 'identity_id')
    op.alter_column('auth_sessions', 'user_id', nullable=False)
    op.drop_constraint('uq_identity_business', 'users', type_='unique')
    op.drop_constraint('uq_user_identity_id', 'users', type_='unique')
    op.drop_index('ix_users_identity_id', table_name='users')
    op.drop_constraint('fk_users_identity', 'users', type_='foreignkey')
    op.drop_column('users', 'identity_id')
    op.drop_table('identities')
