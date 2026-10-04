"""Keep signed handover documents with completed stock issues."""
from alembic import op
import sqlalchemy as sa
revision='0011'
down_revision='0010'
branch_labels=None
depends_on=None

def upgrade():
    existing={column['name'] for column in sa.inspect(op.get_bind()).get_columns('inventory_transactions')}
    columns=[sa.Column('handover_filename',sa.String(255),nullable=True),
             sa.Column('handover_storage_key',sa.String(100),nullable=True),
             sa.Column('handover_content_type',sa.String(100),nullable=True),
             sa.Column('handover_size',sa.Integer(),nullable=True),
             sa.Column('handover_snapshot',sa.JSON(),nullable=True)]
    for column in columns:
        if column.name not in existing: op.add_column('inventory_transactions',column)
    indexes={index['name'] for index in sa.inspect(op.get_bind()).get_indexes('inventory_transactions')}
    if 'ix_stock_handover_key' not in indexes:
        op.create_index('ix_stock_handover_key','inventory_transactions',['handover_storage_key'],unique=True)

def downgrade():
    op.drop_index('ix_stock_handover_key',table_name='inventory_transactions')
    for name in ['handover_snapshot','handover_size','handover_content_type','handover_storage_key','handover_filename']:
        op.drop_column('inventory_transactions',name)
