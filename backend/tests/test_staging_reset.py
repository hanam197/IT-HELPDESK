"""Verify destructive reset and recoverable backups on an isolated database."""
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

def test_reset_preview_backup_restore_and_configuration_retention(tmp_path):
    database = tmp_path / 'isolated.db'
    uploads = tmp_path / 'uploads'
    env = {**os.environ, 'DATABASE_URL': 'sqlite:///' + str(database),
           'UPLOAD_DIR': str(uploads), 'SEED_PASSWORD': 'TestPassword2026!'}
    def run(*args):
        return subprocess.run([sys.executable, *args], cwd=ROOT, env=env,
                              check=True, capture_output=True, text=True)
    run('-m', 'alembic', 'upgrade', 'head')
    run('-m', 'app.seed')
    for folder in ('asset-photos', 'location-photos', 'handovers'):
        (uploads / folder).mkdir(parents=True)
        (uploads / folder / 'sample').write_text('test file')
    with sqlite3.connect(database) as db:
        before = db.execute('select count(*) from assets').fetchone()[0]
        config = db.execute('select count(*) from locations').fetchone()[0]
    run('-m', 'app.staging_reset', '--backup-dir', str(tmp_path / 'backups'))
    with sqlite3.connect(database) as db:
        assert db.execute('select count(*) from assets').fetchone()[0] == before
    assert not (tmp_path / 'backups').exists()
    run('-m', 'app.staging_reset', '--apply', '--backup-dir', str(tmp_path / 'backups'))
    backup = next((tmp_path / 'backups').iterdir())
    with sqlite3.connect(database) as db:
        assert db.execute('select count(*) from assets').fetchone()[0] == 0
        assert db.execute('select count(*) from locations').fetchone()[0] == config
        assert db.execute('select role from users').fetchall() == [('ADMIN',)]
        assert not db.execute('PRAGMA foreign_key_check').fetchall()
    with sqlite3.connect(backup / 'database.backup') as db:
        assert db.execute('select count(*) from assets').fetchone()[0] == before
        assert db.execute('select count(*) from users').fetchone()[0] == 4
    assert (uploads / 'location-photos' / 'sample').exists()
    assert not (uploads / 'asset-photos').exists()
    assert (backup / 'uploads.tar.gz').exists()
    assert json.loads((backup / 'after.json').read_text())['assets'] == 0
    bundle = tmp_path / 'config.json'
    run('-m', 'app.staging_config', 'export', str(bundle))
    target = tmp_path / 'staging.db'
    env['DATABASE_URL'] = 'sqlite:///' + str(target)
    run('-m', 'alembic', 'upgrade', 'head')
    run('-m', 'app.staging_config', 'import', str(bundle))
    run('-m', 'alembic', 'check')
    with sqlite3.connect(target) as db:
        assert db.execute('select count(*) from locations').fetchone()[0] == config
        assert db.execute('select role from users').fetchall() == [('ADMIN',)]
        assert db.execute('select count(*) from assets').fetchone()[0] == 0
        assert not db.execute('PRAGMA foreign_key_check').fetchall()
