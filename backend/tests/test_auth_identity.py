import secrets
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.accounts import create_identity, membership
from app.auth import hasher
from app.db import SessionLocal
from app.main import app
from app.models import Business, Identity, User
from conftest import seed


def login(email, password):
    client = TestClient(app)
    response = client.post('/api/auth/login', json={'email': email, 'password': password})
    if response.status_code == 200:
        client.headers['X-CSRF-Token'] = response.json()['csrf_token']
    return client, response


def test_email_password_only_and_single_membership(setup):
    client, response = login('GESTOR@example.com', setup['password'])
    assert response.status_code == 200
    body = response.json()
    assert body['selection_required'] is False
    assert body['business_name'] == 'Alpha'
    assert len(body['businesses']) == 1
    assert client.get('/api/dashboard').status_code == 200
    assert client.post('/api/auth/login',json={'business':'alpha','email':'gestor@example.com','password':setup['password']}).status_code == 422


def shared_identity(setup):
    with SessionLocal.begin() as db:
        account = db.scalar(select(Identity).where(Identity.email == 'gestor@example.com'))
        business = db.scalar(select(Business).where(Business.slug == 'beta'))
        second = membership(db, account, business.id)
        second_id = second.id
    return second_id


def test_multiple_memberships_require_selection_and_rotate_session(setup):
    second_id = shared_identity(setup)
    client, response = login('gestor@example.com', setup['password'])
    result = response.json()
    assert result['selection_required'] is True
    assert {b['name'] for b in result['businesses']} == {'Alpha','Beta'}
    assert 'role' not in result and 'business_name' not in result
    assert client.get('/api/dashboard').status_code == 403
    assert client.get('/api/clients').status_code == 403
    assert client.get('/api/auth/me').json()['selection_required'] is True
    old_cookie = client.cookies.get('beloria_session')
    assert client.post('/api/auth/select-business',json={'membership_id':second_id},headers={'X-CSRF-Token':''}).status_code == 403
    selected = client.post('/api/auth/select-business',json={'membership_id':second_id})
    assert selected.status_code == 200
    assert selected.json()['business_name'] == 'Beta'
    assert selected.json()['selection_required'] is False
    assert client.cookies.get('beloria_session') != old_cookie
    old = TestClient(app); old.cookies.set('beloria_session',old_cookie)
    assert old.get('/api/auth/me').status_code == 401
    client.headers['X-CSRF-Token'] = selected.json()['csrf_token']
    assert client.get('/api/dashboard').status_code == 200


def test_unauthorized_selection_never_changes_scope(setup):
    client = setup['alpha']
    foreign_id = setup['beta'].get('/api/auth/me').json()['id']
    assert client.post('/api/auth/select-business',json={'membership_id':foreign_id}).status_code == 403
    assert client.post('/api/auth/select-business',json={'membership_id':999999}).status_code == 403
    assert client.get('/api/auth/me').json()['business_name'] == 'Alpha'
    client.post('/api/clients',json={'name':'Somente Alpha'})
    assert setup['beta'].get('/api/clients').json()['total'] == 0


def test_specialist_cannot_gain_second_company_even_as_manager(seeded):
    from sqlalchemy.exc import IntegrityError
    with pytest.raises(IntegrityError), SessionLocal.begin() as db:
        pro = db.scalar(select(User).where(User.professional_id == seeded['professional']['id']))
        beta = db.scalar(select(Business).where(Business.slug == 'beta'))
        membership(db, db.get(Identity, pro.identity_id), beta.id)
    client, response = login('ana@example.com', seeded['password'])
    assert response.json()['destination'] == 'specialist'
    assert response.json()['selection_required'] is False
    assert len(response.json()['businesses']) == 1
    assert client.post('/api/clients', json={'name':'Forbidden'}).status_code == 403
    assert client.get('/api/audit').status_code == 403


def test_revoked_membership_cannot_be_selected(setup):
    second_id=shared_identity(setup)
    client,_=login('gestor@example.com',setup['password'])
    with SessionLocal.begin() as db:
        db.get(User,second_id).active=False
    assert client.post('/api/auth/select-business',json={'membership_id':second_id}).status_code==403
    assert len(client.get('/api/auth/me').json()['businesses'])==1


@pytest.mark.parametrize('same_password',[True,False])
def test_duplicate_legacy_identities_are_not_matched_or_merged(setup,same_password):
    secret=setup['password']
    with SessionLocal.begin() as db:
        for business in db.scalars(select(Business)):
            account=Identity(email='duplicate@example.com',password_hash=hasher.hash(secret if same_password or business.slug=='alpha' else secrets.token_urlsafe(24)),login_enabled=False)
            db.add(account);db.flush()
            membership(db,account,business.id)
    client,response=login('duplicate@example.com',secret)
    assert response.status_code==401
    assert 'businesses' not in response.json()
    assert client.get('/api/dashboard').status_code==401
    with SessionLocal() as db:
        assert len(db.scalars(select(Identity).where(Identity.email=='duplicate@example.com')).all())==2


def test_pending_selection_can_logout(setup):
    shared_identity(setup)
    client,_=login('gestor@example.com',setup['password'])
    assert client.post('/api/auth/logout').status_code==204
    assert client.get('/api/auth/me').status_code==401


def test_admin_does_not_reuse_email_and_can_link_explicit_identity(setup,monkeypatch):
    import sys
    from app.cli import main
    monkeypatch.setattr('getpass.getpass',lambda prompt:setup['password'])
    monkeypatch.setattr(sys,'argv',['cli','--business','new-business','--name','New','--email','gestor@example.com'])
    with pytest.raises(SystemExit): main()
    with SessionLocal() as db:
        assert db.scalar(select(Business).where(Business.slug=='new-business')) is None
        identity_id=db.scalar(select(Identity.id).where(Identity.email=='gestor@example.com'))
    monkeypatch.setattr(sys,'argv',['cli','--identity-id',str(identity_id),'--link-business','beta'])
    main()
    assert login('gestor@example.com',setup['password'])[1].json()['selection_required'] is True

def test_admin_regularizes_duplicates_without_merging_or_changing_passwords(setup,monkeypatch):
    import sys
    from app.cli import main
    with SessionLocal.begin() as db:
        ids=[]
        for business in db.scalars(select(Business)):
            account=Identity(email='conflict@example.com',password_hash=hasher.hash(setup['password']),login_enabled=False)
            db.add(account);db.flush();membership(db,account,business.id);ids.append(account.id)
    monkeypatch.setattr(sys,'argv',['cli','--identity-id',str(ids[0]),'--set-email','resolved@example.com'])
    main()
    assert login('resolved@example.com',setup['password'])[1].status_code==200
    assert login('conflict@example.com',setup['password'])[1].status_code==401
    monkeypatch.setattr(sys,'argv',['cli','--identity-id',str(ids[1]),'--set-email','conflict@example.com'])
    main()
    assert login('conflict@example.com',setup['password'])[1].status_code==200
    with SessionLocal() as db:
        assert db.get(Identity,ids[0]).id != db.get(Identity,ids[1]).id
        assert db.scalar(select(User).where(User.identity_id==ids[0])).business_id != db.scalar(select(User).where(User.identity_id==ids[1])).business_id
