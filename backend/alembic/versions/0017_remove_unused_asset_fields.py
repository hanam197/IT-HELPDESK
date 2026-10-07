"""Remove superseded asset purchase fields and unused serial feature toggle.

Purchase source belongs to stock receipts; maintenance owns repair costs.
Backup the database before applying: downgrade restores columns, not their data.
"""
from alembic import op
import sqlalchemy as sa

revision = '0017'
down_revision = '0016'
branch_labels = None
depends_on = None

FIELDS = {
    'assets': {'purchase_date': sa.DateTime(timezone=True),
               'warranty_expiry': sa.DateTime(timezone=True),
               'vendor': sa.String(150), 'cost': sa.Numeric(14, 2),
               'notes': sa.Text()},
    'asset_types': {'track_serial': sa.Boolean()},
}

def upgrade():
    for table, fields in FIELDS.items():
        existing = {c['name'] for c in sa.inspect(op.get_bind()).get_columns(table)}
        for name in fields:
            if name in existing:
                op.drop_column(table, name)

def downgrade():
    for table, fields in FIELDS.items():
        for name, datatype in fields.items():
            op.add_column(table, sa.Column(name, datatype, nullable=name != 'track_serial',
                                          server_default=sa.true() if name == 'track_serial' else None))
