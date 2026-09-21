import secrets
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from app.main import app
from app.db import SessionLocal, engine
from app.models import Attendance, Payout, PayoutItem, Service
from app.documents import valid_cpf, valid_cnpj
from conftest import approve, attendance, create, seed

def test_sessions_csrf_logout_and_invalid_password(setup):
    client=setup['alpha']
    response=client.get('/api/auth/me')
    assert response.json()['role']=='gestor'
    assert 'HttpOnly' in setup['login']().post('/api/auth/login',json={'business':'alpha','email':'gestor@example.com','password':setup['password']}).headers['set-cookie']
    assert client.post('/api/clients',json={'name':'X'},headers={'X-CSRF-Token':''}).status_code==403
    assert client.post('/api/auth/logout').status_code==204
    assert client.get('/api/auth/me').status_code==401
    assert TestClient(app).post('/api/auth/login',json={'business':'alpha','email':'gestor@example.com','password':'invalid'}).status_code==401

def test_throttle(setup):
    client=TestClient(app)
    for _ in range(10):
        assert client.post('/api/auth/login',json={'business':'none','email':'none@example.com','password':'bad'}).status_code==401
    assert client.post('/api/auth/login',json={'business':'none','email':'none@example.com','password':'bad'}).status_code==429

def test_tenant_isolation_all_relationships(seeded):
    a,b=seeded['alpha'],seeded['beta']
    specialty,professional,service=seed(b,seeded['password'])
    for resource in ('specialties','professionals','clients','services','attendances','payouts','audit'):
        rows=a.get('/api/'+resource).json()['items']
        if resource in ('specialties','professionals','services'):
            assert len(rows)==1
    assert a.put(f"/api/services/{service['id']}",json={'name':'hack','specialty_id':specialty['id'],'price_cents':0}).status_code==404
    assert a.post('/api/services',json={'name':'hack','specialty_id':specialty['id'],'price_cents':0}).status_code==404
    assert attendance(a,professional,seeded['service']).status_code==404
    assert attendance(a,seeded['professional'],service).status_code==404
    foreign_client=create(b,'clients',{'name':'Foreign'})
    assert attendance(a,seeded['professional'],seeded['service'],client_id=foreign_client['id']).status_code==404
    assert a.post('/api/clients',json={'name':'X','business_id':2}).status_code==422
    foreign_row=attendance(b,professional,service).json()
    assert a.post(f"/api/attendances/{foreign_row['id']}/review",json={'decision':'approved'}).status_code==404
    approve(b,foreign_row)
    assert a.post('/api/payouts',json={'attendance_ids':[foreign_row['id']],'reference':'x'},headers={'Idempotency-Key':secrets.token_hex(12)}).status_code==404
    assert a.get('/api/dashboard').json()['attendance_count']==0

def test_database_cross_tenant_constraint(seeded):
    foreign=seed(seeded['beta'],seeded['password'])[0]
    with pytest.raises(IntegrityError), SessionLocal.begin() as db:
        db.add(Service(business_id=1,name='bad',specialty_id=foreign['id'],price_cents=10))
        db.flush()

def test_professional_permissions_and_mixed_payout_privacy(seeded):
    a,pro=seeded['alpha'],seeded['pro']
    _,other,service=seed(a,seeded['password'],'2')
    own=attendance(pro,seeded['professional'],seeded['service']).json()
    other_row=attendance(a,other,service).json()
    assert attendance(pro,other,service).status_code==403
    for path in ('clients','services','professionals','specialties'):
        assert pro.post('/api/'+path,json={}).status_code==403
    assert pro.get('/api/audit').status_code==403
    assert pro.post('/api/payouts',json={'attendance_ids':[own['id']],'reference':'x'},headers={'Idempotency-Key':secrets.token_hex(12)}).status_code==403
    assert pro.post(f"/api/attendances/{own['id']}/review",json={'decision':'approved'}).status_code==403
    assert pro.get('/api/attendances').json()['total']==1
    assert pro.get(f"/api/dashboard?professional_id={other['id']}").status_code==403
    for row in (own,other_row): approve(a,row)
    response=a.post('/api/payouts',json={'attendance_ids':[own['id'],other_row['id']],'reference':'batch'},headers={'Idempotency-Key':secrets.token_hex(12)})
    assert response.status_code==201
    payout=pro.get('/api/payouts').json()['items'][0]
    assert payout['total_cents']==own['commission_cents']
    assert payout['attendance_ids']==[own['id']]
    assert pro.get('/api/dashboard').json()['revenue_cents']==own['price_cents']

def test_snapshot_rounding_approval_rejection_and_audit(seeded):
    a=seeded['alpha']
    row=attendance(a,seeded['professional'],seeded['service']).json()
    assert row['price_cents']==1001 and row['commission_bps']==3333 and row['commission_cents']==334
    assert a.get('/api/dashboard').json()['revenue_cents']==0
    professional=seeded['professional']
    update={key:professional[key] for key in ('name','contact','commission_bps','engagement','cpf','cnpj','specialty_ids','email','active')}
    update['commission_bps']=5000
    assert a.put(f"/api/professionals/{professional['id']}",json=update).status_code==200
    assert a.put(f"/api/services/{seeded['service']['id']}",json={'name':'New','specialty_id':seeded['specialty']['id'],'price_cents':9999}).status_code==200
    approve(a,row)
    assert a.post(f"/api/attendances/{row['id']}/review",json={'decision':'rejected','reason':'x'}).status_code==409
    stored=a.get('/api/attendances').json()['items'][0]
    assert stored['price_cents']==1001 and stored['commission_cents']==334 and stored['service_name']=='Corte'
    second=attendance(a,professional,seeded['service']).json()
    assert a.post(f"/api/attendances/{second['id']}/review",json={'decision':'rejected'}).status_code==422
    assert a.post(f"/api/attendances/{second['id']}/review",json={'decision':'rejected','reason':'Lançamento incorreto'}).status_code==200
    totals=a.get('/api/dashboard').json()
    assert totals['revenue_cents']==1001 and totals['payable_cents']==334 and totals['pending_cents']==0
    audit=a.get('/api/audit').json()['items']
    assert any(x['action']=='attendance.rejected' and x['details']['reason']=='Lançamento incorreto' and x['user_email']=='gestor@example.com' for x in audit)
    assert a.get('/api/attendances?page_size=1&page=2').json()['total']==2
    assert a.get('/api/attendances?start=2099-01-01').json()['total']==0
    assert a.get('/api/dashboard?start=2026-02-02&end=2026-01-01').status_code==422

def test_financial_idempotency_and_rejection(seeded):
    a=seeded['alpha'];key=secrets.token_hex(12)
    first=attendance(a,seeded['professional'],seeded['service'],key)
    assert first.status_code==201
    assert attendance(a,seeded['professional'],seeded['service'],key).json()['id']==first.json()['id']
    assert attendance(a,seeded['professional'],seeded['service'],key,payment_method='dinheiro').status_code==409
    body={'attendance_ids':[first.json()['id']],'reference':'receipt'}
    payout_key=secrets.token_hex(12)
    assert a.post('/api/payouts',json=body,headers={'Idempotency-Key':payout_key}).status_code==409
    approve(a,first.json())
    response=a.post('/api/payouts',json=body,headers={'Idempotency-Key':payout_key})
    assert response.status_code==201
    assert a.post('/api/payouts',json=body,headers={'Idempotency-Key':payout_key}).json()['id']==response.json()['id']
    assert a.post('/api/payouts',json={**body,'reference':'different'},headers={'Idempotency-Key':payout_key}).status_code==409
    assert a.post('/api/payouts',json=body,headers={'Idempotency-Key':secrets.token_hex(12)}).status_code==409
    assert a.get('/api/dashboard').json()['paid_cents']==334

@pytest.mark.parametrize('same_key',[True,False])
def test_concurrent_payouts(seeded,same_key):
    a=seeded['alpha'];row=attendance(a,seeded['professional'],seeded['service']).json();approve(a,row)
    barrier=Barrier(2);key=secrets.token_hex(12)
    def pay(index):
        with TestClient(app) as client:
            client.cookies.update(a.cookies)
            client.headers['X-CSRF-Token']=a.headers['X-CSRF-Token']
            barrier.wait(timeout=10)
            return client.post('/api/payouts',json={'attendance_ids':[row['id']],'reference':'concurrent'},headers={'Idempotency-Key':key if same_key else key+str(index)})
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses=list(pool.map(pay,range(2)))
    assert sorted(r.status_code for r in responses)==([201,201] if same_key else [201,409])
    with SessionLocal() as db:
        assert len(db.scalars(select(Payout)).all())==1
        assert len(db.scalars(select(PayoutItem)).all())==1

@pytest.mark.parametrize('same_key',[True,False])
def test_concurrent_attendance_creation(seeded,same_key):
    a=seeded['alpha'];barrier=Barrier(2);key=secrets.token_hex(12)
    def create_row(index):
        with TestClient(app) as client:
            client.cookies.update(a.cookies);client.headers['X-CSRF-Token']=a.headers['X-CSRF-Token'];barrier.wait(timeout=10)
            return attendance(client,seeded['professional'],seeded['service'],key if same_key else key+str(index))
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses=list(pool.map(create_row,range(2)))
    assert all(r.status_code==201 for r in responses)
    assert a.get('/api/attendances').json()['total']==(1 if same_key else 2)

def test_deactivation_blocks_session_and_new_links(seeded):
    a=seeded['alpha'];p=seeded['professional']
    update={key:p[key] for key in ('name','contact','commission_bps','engagement','cpf','cnpj','specialty_ids','email')};update['active']=False
    assert a.put(f"/api/professionals/{p['id']}",json=update).status_code==200
    assert seeded['pro'].get('/api/auth/me').status_code==401
    assert attendance(a,p,seeded['service']).status_code==404
    assert a.put(f"/api/specialties/{seeded['specialty']['id']}",json={'name':'Cabelo','active':False}).status_code==200
    assert a.post('/api/services',json={'name':'X','specialty_id':seeded['specialty']['id'],'price_cents':1}).status_code==404

@pytest.mark.parametrize('value,valid',[('52998224725',True),('11111111111',False),('52998224724',False)])
def test_cpf(value,valid):
    assert valid_cpf(value)==valid

@pytest.mark.parametrize('value,valid',[('11222333000181',True),('12ABC34501DE35',True),('00000000E08G12',True),('11222333000182',False),('AAAAAAAAAAAA00',False),('11111111111111',False)])
def test_cnpj(value,valid):
    assert valid_cnpj(value)==valid

def test_large_payout_total_uses_bigint(seeded):
    a=seeded['alpha'];p=seeded['professional'];s=seeded['service']
    update={key:p[key] for key in ('name','contact','engagement','cpf','cnpj','specialty_ids','email','active')};update['commission_bps']=10000
    assert a.put(f"/api/professionals/{p['id']}",json=update).status_code==200
    assert a.put(f"/api/services/{s['id']}",json={'name':'High value','specialty_id':seeded['specialty']['id'],'price_cents':100_000_000}).status_code==200
    rows=[attendance(a,p,s).json() for _ in range(22)]
    for row in rows: approve(a,row)
    response=a.post('/api/payouts',json={'attendance_ids':[row['id'] for row in rows],'reference':'large batch'},headers={'Idempotency-Key':secrets.token_hex(12)})
    assert response.status_code==201, response.text
    assert response.json()['total_cents']==2_200_000_000

def test_password_whitespace_is_preserved():
    from app.schemas import LoginInput, ProfessionalInput
    secret='  secret with spaces  '
    assert LoginInput(business='alpha',email='x@example.com',password=secret).password==secret
    professional=ProfessionalInput(name='Ana',commission_bps=0,engagement='autonomo',cpf='52998224725',specialty_ids=[1],email='ana@example.com',password=secret)
    assert professional.password==secret
