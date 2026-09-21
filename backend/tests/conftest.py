import os
import secrets
from pathlib import Path
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text

# An explicitly supplied throwaway PostgreSQL database is mandatory.
url = os.environ.get('TEST_DATABASE_URL')
if not url or not url.rsplit('/', 1)[-1].startswith('beloria_test'):
    raise RuntimeError('Set TEST_DATABASE_URL to a dedicated PostgreSQL database named beloria_test...')
os.environ['DATABASE_URL'] = url
os.environ['COOKIE_SECURE'] = 'false'
from app.main import app
from app.db import SessionLocal, engine
from app.auth import hasher
from app.models import Business, User

@pytest.fixture(scope='session', autouse=True)
def migrated():
    cfg = Config(str(Path(__file__).parents[1] / 'alembic.ini'))
    command.upgrade(cfg, 'head')
    yield

@pytest.fixture(autouse=True)
def clean(migrated):
    with engine.begin() as connection:
        connection.execute(text('TRUNCATE businesses, login_throttles RESTART IDENTITY CASCADE'))

@pytest.fixture
def setup():
    password = secrets.token_urlsafe(20)
    with SessionLocal.begin() as db:
        for slug in ('alpha', 'beta'):
            business = Business(slug=slug, name=slug.title())
            db.add(business)
            db.flush()
            db.add(User(business_id=business.id, email='gestor@example.com', password_hash=hasher.hash(password), role='gestor'))
    def login(business='alpha', email='gestor@example.com', secret=password):
        client = TestClient(app)
        response = client.post('/api/auth/login', json={'business':business,'email':email,'password':secret})
        assert response.status_code == 200, response.text
        client.headers['X-CSRF-Token'] = response.json()['csrf_token']
        return client
    return {'alpha':login(), 'beta':login('beta'), 'login':login, 'password':password}

def create(client, path, payload):
    response = client.post('/api/'+path, json=payload)
    assert response.status_code == 201, response.text
    return response.json()

def seed(client, password, suffix=''):
    specialty = create(client, 'specialties', {'name':'Cabelo'+suffix})
    professional = create(client,'professionals',{'name':'Ana'+suffix,'contact':'','commission_bps':3333,'engagement':'autonomo','cpf':'52998224725','specialty_ids':[specialty['id']],'email':f'ana{suffix}@example.com','password':password})
    service = create(client,'services',{'name':'Corte'+suffix,'specialty_id':specialty['id'],'price_cents':1001})
    return specialty,professional,service

def attendance(client, professional, service, key=None, **overrides):
    payload={'professional_id':professional['id'],'service_id':service['id'],'payment_method':'pix',**overrides}
    return client.post('/api/attendances',json=payload,headers={'Idempotency-Key':key or secrets.token_hex(12)})

def approve(client, row):
    response=client.post(f"/api/attendances/{row['id']}/review",json={'decision':'approved'})
    assert response.status_code == 200, response.text

@pytest.fixture
def seeded(setup):
    setup['specialty'],setup['professional'],setup['service']=seed(setup['alpha'],setup['password'])
    setup['pro']=setup['login'](email='ana@example.com')
    return setup
