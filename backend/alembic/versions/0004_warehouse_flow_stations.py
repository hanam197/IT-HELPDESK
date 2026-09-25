"""Warehouse custody, issue recipients and station information."""
from alembic import op
import sqlalchemy as sa
revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None

def upgrade():
    if op.get_bind().dialect.name == 'sqlite':
        op.execute('ALTER TABLE assets ADD COLUMN warehouse_id INTEGER REFERENCES warehouses(id)')
        op.execute('ALTER TABLE inventory_transactions ADD COLUMN recipient_user_id INTEGER REFERENCES users(id)')
        op.execute('ALTER TABLE inventory_transactions ADD COLUMN recipient_location_id INTEGER REFERENCES locations(id)')
    else:
        op.add_column('assets', sa.Column('warehouse_id', sa.Integer(), sa.ForeignKey('warehouses.id', name='fk_assets_warehouse'), nullable=True))
        op.add_column('inventory_transactions', sa.Column('recipient_user_id', sa.Integer(), sa.ForeignKey('users.id', name='fk_stock_recipient_user'), nullable=True))
        op.add_column('inventory_transactions', sa.Column('recipient_location_id', sa.Integer(), sa.ForeignKey('locations.id', name='fk_stock_recipient_location'), nullable=True))
    op.add_column('locations', sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.true()))
    for name, size in [('physical_location',200),('department',100),('floor',80),('area',80)]:
        op.add_column('locations', sa.Column(name, sa.String(size), nullable=True))
    op.add_column('locations', sa.Column('photo', sa.Text(), nullable=True))

def downgrade():
    if op.get_bind().dialect.name == 'sqlite':
        for name in ['active','physical_location','department','floor','area','photo']:
            op.execute(f'ALTER TABLE locations DROP COLUMN {name}')
        op.execute('ALTER TABLE inventory_transactions DROP COLUMN recipient_user_id')
        op.execute('ALTER TABLE inventory_transactions DROP COLUMN recipient_location_id')
        op.execute('ALTER TABLE assets DROP COLUMN warehouse_id')
        return
    with op.batch_alter_table('locations') as batch:
        for name in ['active','physical_location','department','floor','area','photo']: batch.drop_column(name)
    with op.batch_alter_table('inventory_transactions') as batch:
        batch.drop_constraint('fk_stock_recipient_user', type_='foreignkey')
        batch.drop_constraint('fk_stock_recipient_location', type_='foreignkey')
        batch.drop_column('recipient_user_id'); batch.drop_column('recipient_location_id')
    with op.batch_alter_table('assets') as batch:
        batch.drop_constraint('fk_assets_warehouse', type_='foreignkey')
        batch.drop_column('warehouse_id')
