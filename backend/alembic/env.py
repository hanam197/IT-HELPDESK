from alembic import context
from app.database import engine, Base
from app import models

def compare_types(context, inspected_column, metadata_column, inspected_type, metadata_type):
    # Revision 0012 intentionally leaves SQLite VARCHAR(150) intact: SQLite
    # does not enforce string length. PostgreSQL migrates this column to 400.
    if (context.dialect.name == 'sqlite' and inspected_column.table.name == 'assets'
            and inspected_column.name == 'name' and getattr(inspected_type, 'length', None) == 150
            and getattr(metadata_type, 'length', None) == 400):
        return False
    return None

def run():
    with engine.connect() as connection:
        context.configure(connection=connection,target_metadata=Base.metadata,compare_type=compare_types)
        with context.begin_transaction(): context.run_migrations()
run()
