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
