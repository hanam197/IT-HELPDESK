"""Maintenance records asset issues independently of tickets; reuse type_id."""
from alembic import op
import sqlalchemy as sa

revision='0008'
down_revision='0007'
branch_labels=None
depends_on=None
CATEGORIES={'hardware':'Hardware','network':'Network','software':'Software','power':'Power','peripheral':'Peripheral','other':'Other'}


def upgrade():
    db=op.get_bind(); metadata=sa.MetaData()
    master=sa.Table('master_data',metadata,autoload_with=db)
    maintenance=sa.Table('maintenance',metadata,autoload_with=db)
    tickets=sa.Table('tickets',metadata,autoload_with=db)
    categories={r.code:r.id for r in db.execute(sa.select(master.c.id,master.c.code).where(master.c.group=='maintenance_type'))}
    for code,name in CATEGORIES.items():
        if code not in categories:
            result=db.execute(master.insert().values(group='maintenance_type',code=code,name=name,color='slate',archived=False,created_at=sa.func.current_timestamp(),updated_at=sa.func.current_timestamp()))
            categories[code]=result.inserted_primary_key[0]
    previous={r.id:r for r in db.execute(sa.select(master)).mappings()}
    for row in db.execute(sa.select(maintenance)).mappings():
        changes={}; notes=[row['note']] if row['note'] else []
        category=previous[row['type_id']]
        if category['code'] not in CATEGORIES or category['group']!='maintenance_type':
            changes['type_id']=categories['other']
            notes.append('Loại bảo trì trước chuyển đổi: '+category['name'])
        if row.get('ticket_id'):
            number=db.execute(sa.select(tickets.c.number).where(tickets.c.id==row['ticket_id'])).scalar()
            notes.append('Tham chiếu cũ trước khi tách phiếu hỗ trợ: '+str(number or row['ticket_id']))
        if notes: changes['note']='\n'.join(notes)
        if changes: db.execute(maintenance.update().where(maintenance.c.id==row['id']).values(**changes))
    db.execute(master.update().where(master.c.group=='maintenance_type').values(archived=master.c.code.not_in(list(CATEGORIES))))
    # Maintenance has no inbound FKs; rebuilding it on SQLite preserves Asset/Ticket history.
    naming={'fk':'fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s'}
    foreign_key=next(f for f in sa.inspect(db).get_foreign_keys('maintenance') if f['constrained_columns']==['ticket_id'])
    with op.batch_alter_table('maintenance',naming_convention=naming) as batch:
        batch.drop_constraint(foreign_key['name'] or 'fk_maintenance_ticket_id_tickets',type_='foreignkey')
        batch.drop_column('ticket_id')


def downgrade():
    raise RuntimeError('Restore a pre-migration backup to recover original Ticket links and maintenance types.')
