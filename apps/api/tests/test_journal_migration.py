"""Upgrade con datos reales: conserva historia y admite ejecutar el SQL dos veces."""

import os
from dataclasses import replace
from datetime import datetime, timezone
from uuid import uuid4

import pytest

DSN = os.getenv("FIERRO_TEST_PG_DSN", "")
pytestmark = pytest.mark.skipif(not DSN, reason="FIERRO_TEST_PG_DSN no definido")


def test_legacy_journal_and_notes_migrate_once(monkeypatch):
    import psycopg
    from fastapi.testclient import TestClient
    from fierro_api import main, migrate
    from fierro_api.auth import AuthUser, create_user
    from fierro_api.tenancy import build_specs, seed_tenants
    from psycopg import sql
    from psycopg.conninfo import make_conninfo

    schema = 'journal_upgrade_' + uuid4().hex
    dsn = make_conninfo(DSN, options=f'-csearch_path={schema},public')
    paths = migrate.discover()
    migration = next(p for p in paths if p.stem == '011_ranch_journal')
    with psycopg.connect(DSN, autocommit=True) as conn:
        conn.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
    try:
        with monkeypatch.context() as patch:
            patch.setattr(migrate, 'discover', lambda: [p for p in paths if p < migration])
            migrate.apply_migrations(dsn)
        seed_tenants(dsn, build_specs(orgs=2, ranches_per_org=1, devices_per_ranch=1))
        create_user(dsn, email='legacy@example.test', org_slug='los-encinos')
        occurred = datetime(2025, 1, 2, 12, tzinfo=timezone.utc)
        created = datetime(2025, 1, 3, 13, tzinfo=timezone.utc)
        old_id = uuid4()
        long_note = '  Nota antigua sin recortar: ' + 'ñ' * 5000 + '  '
        with psycopg.connect(dsn) as conn, conn.cursor() as cur:
            cur.execute('SELECT id, org_id FROM users WHERE email=%s', ('legacy@example.test',))
            author_id, org_id = cur.fetchone()
            old_notes = [('legacy', long_note), ('empty', ''), ('null', None), ('blank', '  ')]
            for tag, notes in old_notes:
                cur.execute(
                    'INSERT INTO animals(org_id, tag_id, notes, updated_at) VALUES (%s,%s,%s,%s)',
                    (org_id, tag, notes, created),
                )
            cur.execute("SELECT id FROM animals WHERE tag_id='legacy'")
            animal_id = cur.fetchone()[0]
            cur.execute(
                'INSERT INTO animal_journal '
                '(entry_id, animal_id, author_id, occurred_at, created_at, category, body) '
                "VALUES (%s,%s,%s,%s,%s,'salud','Revisión antigua')",
                (old_id, animal_id, author_id, occurred, created),
            )
        assert migrate.apply_migrations(dsn) == ['011_ranch_journal']
        assert migrate.apply_migrations(dsn) == []
        with psycopg.connect(dsn) as conn, conn.cursor() as cur:
            cur.execute(migration.read_text())
            cur.execute(migration.read_text())
            cur.execute('SELECT count(*) FROM journal_entries')
            assert cur.fetchone() == (2,)
            cur.execute('SELECT count(*) FROM journal_entry_animals')
            assert cur.fetchone() == (2,)
            cur.execute('SELECT author_id, occurred_at, created_at FROM journal_entries '
                        'WHERE entry_id=%s', (old_id,))
            assert cur.fetchone() == (author_id, occurred, created)
            cur.execute("SELECT author_id, body, occurred_at, created_at FROM journal_entries "
                        "WHERE source='ficha'")
            assert cur.fetchone() == (None, long_note, created, created)
            cur.execute('SELECT notes FROM animals WHERE id=%s', (animal_id,))
            assert cur.fetchone() == (long_note,)
            # La protección entre organizaciones también existe en la base.
            cur.execute("SELECT id FROM organizations WHERE slug='valle-verde'")
            other_org = cur.fetchone()[0]
            cur.execute('INSERT INTO animals(org_id, tag_id) VALUES (%s,%s) RETURNING id',
                        (other_org, 'legacy'))
            other_animal = cur.fetchone()[0]
            with pytest.raises(psycopg.errors.ForeignKeyViolation), conn.transaction():
                cur.execute('INSERT INTO journal_entry_animals VALUES (%s,%s,%s)',
                            (old_id, other_animal, org_id))
        monkeypatch.setattr(main, 'settings', replace(main.settings, dsn=dsn))
        user = AuthUser(author_id, 'legacy@example.test', org_id, 'los-encinos', False)
        main.app.dependency_overrides[main.current_user] = lambda: user
        try:
            with TestClient(main.app) as client:
                rows = client.get('/v1/animals/legacy/journal').json()['entries']
                assert len(rows) == 2
                legacy = next(e for e in rows if e['entry_id'] == str(old_id))
                assert legacy['author'] == 'legacy@example.test'
                note = next(e for e in rows if e['source'] == 'ficha')
                assert note['body'] == long_note and note['author'] is None
                assert client.get('/v1/animals/legacy').json()['notes'] == long_note
                # La web antigua reenvía el texto completo incluso al cambiar solo el alias.
                assert client.put('/v1/animals/legacy', json={
                    'alias': 'Pinta', 'notes': long_note,
                }).status_code == 200
                assert len(client.get('/v1/animals/legacy/journal').json()['entries']) == 2
                main.app.dependency_overrides[main.current_user] = lambda: replace(
                    user, org_id=other_org, org_slug='valle-verde',
                )
                assert client.get('/v1/journal').json()['entries'] == []
        finally:
            main.app.dependency_overrides.pop(main.current_user, None)
    finally:
        with psycopg.connect(DSN, autocommit=True) as conn:
            conn.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))
