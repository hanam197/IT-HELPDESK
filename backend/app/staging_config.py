"""Move retained configuration and ADMIN accounts into a fresh staging database."""
import argparse
from datetime import date, datetime
from decimal import Decimal
import json
import os
from pathlib import Path
from sqlalchemy import MetaData, delete, func, select, text, Date, DateTime, Numeric
from .database import engine

TABLES = {'users', 'master_data', 'asset_types', 'locations', 'warehouses'}

def export_config(path):
    metadata = MetaData()
    metadata.reflect(bind=engine)
    records = {}
    with engine.connect() as db:
        for table in metadata.sorted_tables:
            if table.name not in TABLES:
                continue
            query = select(table).order_by(table.c.id)
            if table.name == 'users':
                query = query.where(table.c.role == 'ADMIN')
            records[table.name] = [dict(row) for row in db.execute(query).mappings()]
        revision = db.scalar(text('select version_num from alembic_version'))
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Contains password hashes; never include this file in source control.
    with open(path, 'x', opener=lambda name, flags: os.open(name, flags, 0o600)) as output:
        json.dump({'revision': revision, 'tables': records}, output, default=str, indent=2)
    print('Configuration bundle created; keep private:', path)

def import_config(path):
    bundle = json.loads(Path(path).read_text())
    if set(bundle['tables']) != TABLES:
        raise RuntimeError('Unexpected configuration tables')
    admins = bundle['tables']['users']
    if not admins or any(row['role'] != 'ADMIN' for row in admins) or not any(not row['archived'] for row in admins):
        raise RuntimeError('Bundle must contain an active ADMIN and no other users')
    metadata = MetaData()
    metadata.reflect(bind=engine)
    with engine.begin() as db:
        if db.scalar(text('select version_num from alembic_version')) != bundle['revision']:
            raise RuntimeError('Source and target migrations must match')
        for table in metadata.sorted_tables:
            if table.name not in TABLES | {'alembic_version'} and db.scalar(select(func.count()).select_from(table)):
                raise RuntimeError('Target must have no business data')
        if db.scalar(select(func.count()).select_from(metadata.tables['users'])):
            raise RuntimeError('Target already has accounts; import into a fresh database only')
        for table in reversed(metadata.sorted_tables):
            if table.name in TABLES:
                db.execute(delete(table))
        for table in metadata.sorted_tables:
            if table.name not in TABLES:
                continue
            pending = list(bundle['tables'][table.name])
            inserted = set()
            while pending:
                ready = [r for r in pending if table.name != 'locations' or not r['parent_id'] or r['parent_id'] in inserted]
                if not ready:
                    raise RuntimeError('Location hierarchy has a cycle or missing parent')
                for source in ready:
                    row = dict(source)
                    for column in table.columns:
                        value = row.get(column.name)
                        if value is not None and isinstance(column.type, DateTime):
                            row[column.name] = datetime.fromisoformat(value)
                        elif value is not None and isinstance(column.type, Date):
                            row[column.name] = date.fromisoformat(value)
                        elif value is not None and isinstance(column.type, Numeric):
                            row[column.name] = Decimal(value)
                    db.execute(table.insert().values(**row))
                    inserted.add(row['id'])
                    pending.remove(source)
            if engine.dialect.name == 'postgresql':
                db.execute(text("SELECT setval(pg_get_serial_sequence(:table, 'id'), "
                                "COALESCE((SELECT MAX(id) FROM \"" + table.name + "\"), 1), "
                                "EXISTS(SELECT 1 FROM \"" + table.name + "\"))"), {'table': table.name})
    print('Configuration imported; business tables remain empty.')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['export', 'import'])
    parser.add_argument('path')
    args = parser.parse_args()
    (export_config if args.action == 'export' else import_config)(args.path)

if __name__ == '__main__':
    main()
