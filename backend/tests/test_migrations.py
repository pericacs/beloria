from pathlib import Path
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from app.db import engine


def test_migration_roundtrip_and_metadata(migrated):
    config=Config(str(Path(__file__).parents[1]/'alembic.ini'))
    command.downgrade(config,'base')
    assert 'businesses' not in inspect(engine).get_table_names()
    command.upgrade(config,'head')
    assert 'payout_items' in inspect(engine).get_table_names()
    command.check(config)
    with engine.connect() as connection:
        assert int(connection.scalar(text('SHOW server_version_num'))) >= 160000

def test_identity_migration_preserves_duplicate_accounts_and_financial_history():
    import secrets
    from app.auth import hasher
    from fastapi.testclient import TestClient
    from app.main import app
    config=Config(str(Path(__file__).parents[1]/'alembic.ini'))
    command.downgrade(config,'ddd468014c2d')
    password=secrets.token_urlsafe(24)
    password_hash=hasher.hash(password)
    with engine.begin() as c:
        c.execute(text("INSERT INTO businesses(id,slug,name) VALUES(901,'old-alpha','Old Alpha'),(902,'old-beta','Old Beta')"))
        c.execute(text("INSERT INTO users(id,business_id,email,password_hash,role,active) VALUES (901,901,'same@example.com',:hash,'gestor',true),(902,902,'SAME@example.com',:hash,'gestor',true),(903,902,'unique@example.com',:hash,'gestor',true)"),{'hash':password_hash})
        c.execute(text("INSERT INTO payouts(id,business_id,reference,request_key,request_fingerprint,total_cents,created_by,created_at) VALUES(901,901,'historic','historic','historic',12345,901,now())"))
        c.execute(text("INSERT INTO audit_events(id,business_id,user_id,action,entity,entity_id,details,created_at) VALUES(901,901,901,'historic','payouts',901,'{}',now())"))
        c.execute(text("INSERT INTO auth_sessions(token_hash,user_id,csrf_token,expires_at) VALUES('old',901,'old',now()+interval '1 hour')"))
    try:
        command.upgrade(config,'head')
        with engine.connect() as c:
            assert c.scalar(text('SELECT count(*) FROM identities'))==3
            assert c.scalar(text('SELECT count(DISTINCT identity_id) FROM users'))==3
            assert c.scalar(text('SELECT count(*) FROM identities WHERE NOT login_enabled'))==2
            assert c.scalar(text('SELECT count(*) FROM auth_sessions'))==0
            assert c.scalar(text('SELECT total_cents FROM payouts WHERE id=901'))==12345
            assert c.scalar(text('SELECT user_id FROM audit_events WHERE id=901'))==901
        client=TestClient(app)
        assert client.post('/api/auth/login',json={'email':'same@example.com','password':password}).status_code==401
        assert client.post('/api/auth/login',json={'email':'unique@example.com','password':password}).status_code==200
        command.downgrade(config,'ddd468014c2d')
        with engine.connect() as c:
            assert c.scalar(text('SELECT count(*) FROM users'))==3
            assert c.scalar(text('SELECT password_hash FROM users WHERE id=901'))==password_hash
            assert c.scalar(text('SELECT created_by FROM payouts WHERE id=901'))==901
    finally:
        command.upgrade(config,'head')

def test_commercial_migration_preserves_and_flags_old_specialist_links():
    import secrets
    from app.auth import hasher
    from fastapi.testclient import TestClient
    from app.main import app
    config=Config(str(Path(__file__).parents[1]/'alembic.ini'))
    from alembic.script import ScriptDirectory
    previous=ScriptDirectory.from_config(config).get_revision('3be600b16a15').down_revision
    command.downgrade(config,previous)
    password=secrets.token_urlsafe(24); encoded=hasher.hash(password)
    with engine.begin() as c:
        c.execute(text("INSERT INTO businesses(id,slug,name) VALUES(801,'legacy-a','Legacy A'),(802,'legacy-b','Legacy B')"))
        c.execute(text("INSERT INTO identities(id,email,password_hash,login_enabled) VALUES(801,'legacy-specialist@example.com',:hash,true)"),{'hash':encoded})
        c.execute(text("INSERT INTO professionals(id,business_id,name,contact,commission_bps,engagement,active) VALUES(801,801,'Legacy','',3500,'autonomo',true)"))
        c.execute(text("INSERT INTO users(id,business_id,identity_id,email,password_hash,role,professional_id,active) VALUES(801,801,801,'legacy-specialist@example.com',:hash,'profissional',801,true),(802,802,801,'legacy-specialist@example.com',:hash,'gestor',null,true)"),{'hash':encoded})
    try:
        command.upgrade(config,'head')
        with engine.connect() as c:
            assert c.scalar(text('SELECT specialist_conflict FROM identities WHERE id=801')) is True
            assert c.scalar(text('SELECT count(*) FROM users WHERE identity_id=801'))==2
            assert c.scalar(text('SELECT count(*) FROM businesses WHERE legacy_access AND trial_started_at IS NULL AND trial_ends_at IS NULL'))==2
            assert c.scalar(text('SELECT count(*) FROM platform_admins'))==0
            assert c.scalar(text('SELECT count(*) FROM specialist_claims'))==0
        client=TestClient(app)
        response=client.post('/api/auth/login',json={'email':'legacy-specialist@example.com','password':password})
        assert response.status_code==200
        assert response.json()['destination']=='conflict'
        assert client.get('/api/dashboard').status_code==403
    finally:
        command.upgrade(config,'head')


def test_commercial_downgrade_refuses_loss_of_new_history():
    from app.commercial_models import PlatformAudit
    from app.db import SessionLocal
    from alembic.script import ScriptDirectory
    config=Config(str(Path(__file__).parents[1]/'alembic.ini'))
    with SessionLocal.begin() as db:
        db.add(PlatformAudit(action='preserve',details={}))
    previous=ScriptDirectory.from_config(config).get_revision('3be600b16a15').down_revision
    import pytest
    with pytest.raises(RuntimeError,match='Commercial data exists'):
        command.downgrade(config,previous)
    with engine.connect() as c:
        assert c.scalar(text("SELECT count(*) FROM platform_audit WHERE action='preserve'"))==1
