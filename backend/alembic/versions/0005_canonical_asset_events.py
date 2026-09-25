"""Canonical asset state and immutable business event snapshots."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.orm import Session
revision='0005'
down_revision='0004'
branch_labels=None
depends_on=None

def upgrade():
    op.add_column('assets',sa.Column('current_status',sa.String(20),nullable=False,server_default='AVAILABLE'))
    if op.get_bind().dialect.name=='sqlite':
        op.execute('ALTER TABLE assets ADD COLUMN current_location_id INTEGER REFERENCES locations(id)')
        op.execute('ALTER TABLE assets ADD COLUMN current_assignee_id INTEGER REFERENCES users(id)')
    else:
        op.add_column('assets',sa.Column('current_location_id',sa.Integer(),sa.ForeignKey('locations.id',name='fk_asset_current_location')))
        op.add_column('assets',sa.Column('current_assignee_id',sa.Integer(),sa.ForeignKey('users.id',name='fk_asset_current_assignee')))
    op.add_column('asset_operations',sa.Column('before_state',sa.JSON(),nullable=True))
    op.add_column('asset_operations',sa.Column('after_state',sa.JSON(),nullable=True))
    op.add_column('asset_operations',sa.Column('source_ref',sa.String(120),nullable=True))
    op.create_index('uq_asset_event_source','asset_operations',['source_ref'],unique=True)
    from app.migrate_asset_events import upgrade_data
    with Session(bind=op.get_bind()) as db:
        upgrade_data(db); db.flush()
        db.commit()

def downgrade():
    # Dropping snapshot columns would permanently lose event before/after evidence.
    raise RuntimeError('Migration 0005 preserves immutable history. Restore a pre-upgrade backup to roll back.')
