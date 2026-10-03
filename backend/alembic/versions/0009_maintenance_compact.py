"""Two maintenance states and warehouse component references."""
from alembic import op
import sqlalchemy as sa
revision='0009'
down_revision='0008'
branch_labels=None
depends_on=None

def upgrade():
    op.add_column('maintenance',sa.Column('replacement_asset_ids',sa.JSON(),nullable=True))
    db=op.get_bind(); metadata=sa.MetaData()
    master=sa.Table('master_data',metadata,autoload_with=db)
    records=sa.Table('maintenance',metadata,autoload_with=db)
    states={r.code:r.id for r in db.execute(sa.select(master.c.id,master.c.code).where(master.c.group=='maintenance_status'))}
    for code,name,color in [('open','Mới','amber'),('completed','Hoàn tất','green')]:
        if code not in states:
            result=db.execute(master.insert().values(group='maintenance_status',code=code,name=name,color=color,archived=False,created_at=sa.func.current_timestamp(),updated_at=sa.func.current_timestamp()))
            states[code]=result.inserted_primary_key[0]
        db.execute(master.update().where(master.c.id==states[code]).values(name=name,color=color,archived=False))
    old_states={r.id:r.name for r in db.execute(sa.select(master.c.id,master.c.name).where(master.c.group=='maintenance_status'))}
    for row in db.execute(sa.select(records)).mappings():
        status=states['completed' if row['end_at'] else 'open']
        if row['status_id']!=status:
            note='\n'.join(filter(None,[row['note'],'Trạng thái trước chuyển đổi: '+old_states.get(row['status_id'],'—')]))
            db.execute(records.update().where(records.c.id==row['id']).values(status_id=status,note=note))
    db.execute(master.update().where(master.c.group=='maintenance_status',master.c.code.not_in(['open','completed'])).values(archived=True))
    types=sa.Table('asset_types',metadata,autoload_with=db)
    if not db.execute(sa.select(types.c.id).where(sa.func.lower(types.c.name).in_(['linh kiện','component','components']))).first():
        db.execute(types.insert().values(name='Linh kiện',prefix='LK',track_serial=True,track_location=True,allow_assignment=False,allow_station=True,track_network=False,allow_ticket=False,track_maintenance=True,has_ports=False,archived=False,created_at=sa.func.current_timestamp(),updated_at=sa.func.current_timestamp()))

def downgrade():
    raise RuntimeError('Restore the pre-migration backup to recover previous maintenance states and component references.')
