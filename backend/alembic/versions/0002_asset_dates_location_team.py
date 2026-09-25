"""Asset receiving dates and Site-Team-Station hierarchy.

Revision ID: 0002
Revises: 0001
"""
from alembic import op
import sqlalchemy as sa

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None

def upgrade():
    columns={column['name'] for column in sa.inspect(op.get_bind()).get_columns('assets')}
    if 'received_date' not in columns:
        op.add_column('assets',sa.Column('received_date',sa.Date(),nullable=True))
    if 'handover_date' not in columns:
        op.add_column('assets',sa.Column('handover_date',sa.Date(),nullable=True))
    op.execute("UPDATE assets SET model = 'UNKNOWN-' || CAST(id AS VARCHAR) WHERE model IS NULL OR trim(model) = ''")
    op.execute("UPDATE assets SET serial = 'UNKNOWN-' || CAST(id AS VARCHAR) WHERE serial IS NULL OR trim(serial) = ''")
    # SQLite batch table recreation cannot drop `assets` while many history tables
    # reference it. API validation still enforces both fields for local SQLite;
    # PostgreSQL receives the database-level NOT NULL constraints.
    if op.get_bind().dialect.name != 'sqlite':
        op.alter_column('assets','model',existing_type=sa.String(length=100),nullable=False)
        op.alter_column('assets','serial',existing_type=sa.String(length=150),nullable=False)
    op.execute("UPDATE locations SET kind = 'team' WHERE kind = 'area'")

def downgrade():
    op.execute("UPDATE locations SET kind = 'area' WHERE kind = 'team'")
    if op.get_bind().dialect.name != 'sqlite':
        op.alter_column('assets','serial',existing_type=sa.String(length=150),nullable=True)
        op.alter_column('assets','model',existing_type=sa.String(length=100),nullable=True)
    op.drop_column('assets','handover_date')
    op.drop_column('assets','received_date')
