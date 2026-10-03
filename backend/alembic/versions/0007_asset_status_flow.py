"""Canonical five-state lifecycle; preserve original evidence in audit logs."""
from copy import deepcopy
from alembic import op
import sqlalchemy as sa

revision='0007'
down_revision='0006'
branch_labels=None
depends_on=None

STATES={'AVAILABLE':'available','IN_USE':'in_use','MAINTENANCE':'maintenance','RETIRED':'retired','DISPOSED':'disposed'}
NAMES={'available':'Available','in_use':'In Use','maintenance':'Maintenance','retired':'Retired','disposed':'Disposed'}
ALIASES={'assigned':'IN_USE','active':'IN_USE','repair_needed':'MAINTENANCE','repair':'MAINTENANCE','broken':'MAINTENANCE','damaged':'MAINTENANCE','waiting_repair':'MAINTENANCE','lost':'RETIRED'}

def canonical(value):
    key=str(value or '').lower()
    if key in STATES.values(): return key.upper()
    if key in ALIASES: return ALIASES[key]
    raise RuntimeError(f'Unknown legacy asset status: {value!r}; map explicitly before migrating')


def upgrade():
    db=op.get_bind(); metadata=sa.MetaData()
    master=sa.Table('master_data',metadata,autoload_with=db)
    assets=sa.Table('assets',metadata,autoload_with=db)
    maintenance=sa.Table('maintenance',metadata,autoload_with=db)
    events=sa.Table('asset_operations',metadata,autoload_with=db)
    rows=list(db.execute(sa.select(master).where(master.c.group=='asset_status')).mappings())
    codes={r['id']:r['code'] for r in rows}
    for code,name in NAMES.items():
        if code not in codes.values():
            result=db.execute(master.insert().values(group='asset_status',code=code,name=name,color='slate',archived=False,created_at=sa.func.current_timestamp(),updated_at=sa.func.current_timestamp()))
            codes[result.inserted_primary_key[0]]=code
    ids={code:id for id,code in codes.items() if code in NAMES}
    for row in db.execute(sa.select(assets)).mappings():
        status=canonical(row['current_status'])
        db.execute(assets.update().where(assets.c.id==row['id']).values(current_status=status,status_id=ids[STATES[status]]))
    for row in db.execute(sa.select(maintenance.c.id,maintenance.c.previous_status_id)).mappings():
        if row['previous_status_id'] is not None:
            status=canonical(codes[row['previous_status_id']])
            db.execute(maintenance.update().where(maintenance.c.id==row['id']).values(previous_status_id=ids[STATES[status]]))
    # Only normalize the status vocabulary; event identity, actor, time and repair details stay intact.
    for row in db.execute(sa.select(events)).mappings():
        changed={}
        for field in ('before_state','after_state'):
            value=deepcopy(row[field])
            if value and value.get('current_status'):
                value['current_status']=canonical(value['current_status'])
                if value!=row[field]: changed[field]=value
        if changed: db.execute(events.update().where(events.c.id==row['id']).values(**changed))
    db.execute(master.update().where(master.c.group=='asset_status').values(archived=master.c.code.not_in(list(NAMES))))
    # SQLite cannot add a CHECK without rebuilding a table referenced throughout the database.
    if db.dialect.name=='sqlite':
        allowed=','.join("'"+state+"'" for state in STATES)
        for action in ('INSERT','UPDATE'):
            op.execute(f"CREATE TRIGGER ck_asset_status_{action.lower()} BEFORE {action} ON assets WHEN NEW.current_status NOT IN ({allowed}) OR NEW.current_status IS NULL BEGIN SELECT RAISE(ABORT, 'Invalid asset status'); END")
    else:
        op.create_check_constraint('ck_asset_current_status','assets',"current_status IN ('AVAILABLE','IN_USE','MAINTENANCE','RETIRED','DISPOSED')")


def downgrade():
    raise RuntimeError('Asset lifecycle history must be preserved. Restore a pre-upgrade backup to roll back.')
