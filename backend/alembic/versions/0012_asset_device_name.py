"""Allow complete device names composed of type, model and serial."""
from alembic import op
import sqlalchemy as sa
revision='0012'
down_revision='0011'
branch_labels=None
depends_on=None

def upgrade():
    # SQLite does not enforce VARCHAR lengths; leave its data and dependent tables intact.
    if op.get_bind().dialect.name!='sqlite':
        op.alter_column('assets','name',existing_type=sa.String(150),type_=sa.String(400),existing_nullable=False)

def downgrade():
    if op.get_bind().dialect.name!='sqlite':
        op.alter_column('assets','name',existing_type=sa.String(400),type_=sa.String(150),existing_nullable=False)
