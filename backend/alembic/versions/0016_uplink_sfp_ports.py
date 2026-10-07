"""Add dedicated uplink and optical SFP capacities."""
from alembic import op
import sqlalchemy as sa
revision='0016'
down_revision='0015'
branch_labels=None
depends_on=None

def upgrade():
    for name in ('uplink_port_count','sfp_port_count'):
        op.add_column('assets',sa.Column(name,sa.Integer(),nullable=True))

def downgrade():
    for name in ('sfp_port_count','uplink_port_count'): op.drop_column('assets',name)
