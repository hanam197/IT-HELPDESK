"""Align legacy nullable asset identity storage across SQLite and PostgreSQL.

New API writes still require model and serial. Legacy records can be represented
without inventing identity values; SQLite already permits this storage shape.
"""
from alembic import op
import sqlalchemy as sa

revision = '0018'
down_revision = '0017'
branch_labels = None
depends_on = None

def upgrade():
    if op.get_bind().dialect.name != 'sqlite':
        for name, size in [('model', 100), ('serial', 150)]:
            op.alter_column('assets', name, existing_type=sa.String(size), nullable=True)

def downgrade():
    if op.get_bind().dialect.name != 'sqlite':
        for name, size in [('model', 100), ('serial', 150)]:
            op.alter_column('assets', name, existing_type=sa.String(size), nullable=False)
