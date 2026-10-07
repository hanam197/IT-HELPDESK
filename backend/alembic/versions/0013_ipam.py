"""IPAM DHCP ranges and assignment types."""
from alembic import op
import sqlalchemy as sa
revision='0013'
down_revision='0012'
branch_labels=None
depends_on=None

def upgrade():
    op.add_column('subnets',sa.Column('dhcp_start',sa.String(60),nullable=True))
    op.add_column('subnets',sa.Column('dhcp_end',sa.String(60),nullable=True))
    op.add_column('ip_addresses',sa.Column('assignment_type',sa.String(10),nullable=False,server_default='Static'))
    op.execute("UPDATE ip_addresses SET assignment_type='DHCP' WHERE status_id IN (SELECT id FROM master_data WHERE code='dhcp' AND \"group\"='ip_status')")

def downgrade():
    op.drop_column('ip_addresses','assignment_type')
    op.drop_column('subnets','dhcp_end')
    op.drop_column('subnets','dhcp_start')
