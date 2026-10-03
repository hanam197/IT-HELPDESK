"""Explicit maintenance outcomes, preserving pre-disposal asset locations."""
from alembic import op
import sqlalchemy as sa
revision='0010'
down_revision='0009'
branch_labels=None
depends_on=None

def upgrade():
    op.add_column('maintenance',sa.Column('resolution_outcome',sa.String(20),nullable=True))
    db=op.get_bind(); metadata=sa.MetaData()
    assets=sa.Table('assets',metadata,autoload_with=db)
    history=sa.Table('location_history',metadata,autoload_with=db)
    warehouses=sa.Table('warehouses',metadata,autoload_with=db)
    master=sa.Table('master_data',metadata,autoload_with=db)
    db.execute(master.update().where(master.c.group=='asset_status',master.c.code=='retired').values(name='Hư / Ngừng sử dụng',color='red'))
    for asset in db.execute(sa.select(assets).where(assets.c.current_status!='DISPOSED',assets.c.current_location_id.is_(None))).mappings():
        last=db.execute(sa.select(history).where(history.c.asset_id==asset['id']).order_by(history.c.created_at.desc(),history.c.id.desc()).limit(1)).mappings().first()
        location=last['location_id'] if last else None
        if asset['warehouse_id']:
            location=db.execute(sa.select(warehouses.c.location_id).where(warehouses.c.id==asset['warehouse_id'])).scalar() or location
        if location:
            db.execute(assets.update().where(assets.c.id==asset['id']).values(current_location_id=location))
            if last and last['ended_at'] is not None:
                db.execute(history.insert().values(asset_id=asset['id'],location_id=location,from_location_id=last['location_id'],technician_id=last['technician_id'],reason='Khôi phục vị trí ghi nhận gần nhất trước thanh lý',created_at=sa.func.current_timestamp(),updated_at=sa.func.current_timestamp(),archived=False))
    # Completed legacy records retain an unknown outcome rather than inventing repair results.

def downgrade():
    raise RuntimeError('Restore the backup to recover the previous maintenance and location schema.')
