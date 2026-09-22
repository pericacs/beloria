"""Expire only a named synthetic company in an explicitly disposable PostgreSQL DB."""
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
url=os.environ['E2E_DATABASE_URL']
parsed=make_url(url)
if not parsed.database.startswith('beloria_test') or parsed.host not in ('127.0.0.1','localhost'):
    raise RuntimeError('Requires a local disposable beloria_test... database')
with create_engine(url).begin() as db:
    result=db.execute(text("UPDATE businesses SET trial_started_at=now()-interval '16 days', trial_ends_at=now()-interval '1 day' WHERE name=:name AND NOT legacy_access"),{'name':sys.argv[1]})
    if result.rowcount!=1: raise RuntimeError('Expected exactly one synthetic company')
