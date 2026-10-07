"""Record IP/device information directly, without interface or status selection."""
from alembic import op
import sqlalchemy as sa
revision='0014'
down_revision='0013'
branch_labels=None
depends_on=None

def upgrade():
    # Nullable references do not require rebuilding SQLite's historical tables.
    if op.get_bind().dialect.name=='sqlite':
        op.execute('ALTER TABLE ip_addresses ADD COLUMN asset_id INTEGER REFERENCES assets(id)')
    else:
        op.add_column('ip_addresses',sa.Column('asset_id',sa.Integer(),nullable=True))
    op.add_column('ip_addresses',sa.Column('mac',sa.String(17),nullable=True))
    op.add_column('ip_addresses',sa.Column('hostname',sa.String(150),nullable=True))
    if op.get_bind().dialect.name!='sqlite':
        op.create_foreign_key('fk_ip_asset','ip_addresses','assets',['asset_id'],['id'])
    op.execute('UPDATE ip_addresses SET asset_id=(SELECT asset_id FROM interfaces WHERE interfaces.id=ip_addresses.interface_id), mac=(SELECT mac FROM interfaces WHERE interfaces.id=ip_addresses.interface_id), hostname=(SELECT hostname FROM interfaces WHERE interfaces.id=ip_addresses.interface_id) WHERE interface_id IS NOT NULL')
    op.execute('UPDATE ip_addresses SET status_id=(SELECT id FROM master_data WHERE "group"=\'ip_status\' AND code=\'used\') WHERE EXISTS (SELECT 1 FROM master_data WHERE "group"=\'ip_status\' AND code=\'used\')')

def downgrade():
    if op.get_bind().dialect.name!='sqlite': op.drop_constraint('fk_ip_asset','ip_addresses',type_='foreignkey')
    for column in ('hostname','mac','asset_id'): op.drop_column('ip_addresses',column)
