"""Offline business-data reset. Preview by default; always back up before --apply."""
import argparse
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tarfile
from datetime import datetime, timezone
from sqlalchemy import MetaData, delete, func, select
from .database import engine, settings

KEEP = {'alembic_version', 'master_data', 'asset_types', 'locations', 'warehouses', 'users'}

def inventory(connection, metadata):
    return {t.name: connection.scalar(select(func.count()).select_from(t))
            for t in metadata.sorted_tables}

def reset(backup_root, apply=False):
    metadata = MetaData()
    metadata.reflect(bind=engine)
    users = metadata.tables['users']
    with engine.connect() as connection:
        counts = inventory(connection, metadata)
        admins = connection.scalar(select(func.count()).select_from(users).where(
            users.c.role == 'ADMIN', users.c.archived == False))
    if not admins:
        raise RuntimeError('An active administrator is required before reset')
    plan = {'delete': {k: v for k, v in counts.items() if k not in KEEP},
            'keep_configuration': sorted(KEEP - {'users'}),
            'keep_users': 'ADMIN only', 'active_admins': admins}
    print(json.dumps(plan, indent=2))
    if not apply:
        return None
    destination = Path(backup_root).resolve() / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    destination.mkdir(parents=True, mode=0o700)
    os.chmod(destination.parent, 0o700)
    database = destination / 'database.backup'
    if engine.dialect.name == 'sqlite':
        with sqlite3.connect(engine.url.database) as source, sqlite3.connect(database) as target:
            source.backup(target)
    elif engine.dialect.name == 'postgresql':
        # Supply password through child environment, never command arguments or logs.
        url = engine.url
        env = {**os.environ, 'PGPASSWORD': url.password or ''}
        subprocess.run(['pg_dump', '-Fc', '-h', url.host or 'localhost', '-p', str(url.port or 5432),
                        '-U', url.username or '', '-d', url.database, '-f', str(database)],
                       env=env, check=True)
    else:
        raise RuntimeError('Unsupported database backup dialect')
    os.chmod(database, 0o600)
    uploads = Path(settings.upload_dir).resolve()
    with tarfile.open(destination / 'uploads.tar.gz', 'w:gz') as archive:
        if uploads.exists():
            archive.add(uploads, arcname='uploads')
    (destination / 'manifest.json').write_text(json.dumps({'dialect': engine.dialect.name,
        'before': counts, 'plan': plan}, indent=2))
    # Run offline: backup and transaction must see the same quiescent database.
    with engine.begin() as connection:
        if engine.dialect.name == 'sqlite':
            connection.exec_driver_sql('PRAGMA defer_foreign_keys=ON')
        for table in reversed(metadata.sorted_tables):
            if table.name not in KEEP:
                connection.execute(delete(table))
        connection.execute(delete(users).where(users.c.role != 'ADMIN'))
        after = inventory(connection, metadata)
        if any(after[k] for k in after if k not in KEEP):
            raise RuntimeError('Reset verification failed')
    # Preserve location images because locations are retained configuration.
    if uploads.exists():
        for path in uploads.iterdir():
            if path.name == 'location-photos':
                continue
            if path.is_dir() and not path.is_symlink():
                shutil.rmtree(path)
            else:
                path.unlink()
    (destination / 'after.json').write_text(json.dumps(after, indent=2))
    print('Backup and reset verified:', destination)
    return destination

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--backup-dir', default='../backups')
    args = parser.parse_args()
    reset(args.backup_dir, args.apply)

if __name__ == '__main__':
    main()
