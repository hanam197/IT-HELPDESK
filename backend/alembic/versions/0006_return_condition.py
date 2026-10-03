"""Add a non-issuable state for assets returned needing repair."""
from alembic import op
import sqlalchemy as sa
revision='0006'
down_revision='0005'
branch_labels=None
depends_on=None


def upgrade():
    connection=op.get_bind()
    existing=connection.execute(sa.text('SELECT id FROM master_data WHERE "group"=:group AND code=:code'),{'group':'asset_status','code':'repair_needed'}).scalar()
    if existing is None:
        connection.execute(sa.text('INSERT INTO master_data ("group",code,name,color,archived,created_at,updated_at) VALUES (:group,:code,:name,:color,false,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)'),{'group':'asset_status','code':'repair_needed','name':'Repair Needed','color':'amber'})


def downgrade():
    # Retain the vocabulary so existing asset and maintenance references remain valid.
    pass
