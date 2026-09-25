"""Run the real Alembic upgrade over legacy rows, independent of current ORM defaults."""
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys


def test_upgrade_preserves_legacy_location_and_assignment_history(tmp_path):
    database=tmp_path/'legacy.db'
    backend=Path(__file__).resolve().parents[1]
    env={**os.environ,'DATABASE_URL':'sqlite:///'+str(database)}
    def upgrade(version):
        result=subprocess.run([sys.executable,'-m','alembic','upgrade',version],cwd=backend,env=env,capture_output=True,text=True)
        assert result.returncode==0,result.stderr
    upgrade('0004')
    with sqlite3.connect(database) as db:
        def insert(table,**values):
            values={'created_at':'2026-01-01 00:00:00','updated_at':'2026-01-01 00:00:00','archived':0,**values}
            columns=','.join('"'+k+'"' for k in values)
            return db.execute(f'INSERT INTO {table} ({columns}) VALUES ({",".join("?" for _ in values)})',list(values.values())).lastrowid
        user=insert('users',username='legacy',name='Người dùng cũ',role='ADMIN',password_hash='unused')
        status=insert('master_data',group='asset_status',code='assigned',name='Assigned',color='slate')
        kind=insert('asset_types',name='Laptop',prefix='LAP',track_location=1,allow_assignment=1,track_network=1,allow_ticket=1,track_maintenance=1,has_ports=0)
        site=insert('locations',name='Q7',kind='site')
        team=insert('locations',name='QC',kind='team',parent_id=site)
        station=insert('locations',name='QC-01',kind='station',parent_id=team)
        asset=insert('assets',code='LEGACY-01',name='Legacy',type_id=kind,status_id=status,model='M1',serial='LEGACY-01')
        insert('location_history',asset_id=asset,location_id=station,technician_id=user,reason='Lắp đặt',created_at='2026-01-02 00:00:00')
        insert('assignments',asset_id=asset,user_id=user,assigned_by=user,condition_out='Tốt',created_at='2026-01-03 00:00:00')
    upgrade('head')
    with sqlite3.connect(database) as db:
        state=db.execute('select current_status,current_location_id,current_assignee_id from assets').fetchone()
        assert state==('IN_USE',station,user)
        rows=db.execute('select operation_type,before_state,after_state from asset_operations order by operation_date,id').fetchall()
        assert [r[0] for r in rows]==['RECEIVED','MOVED','ISSUED']
        assert json.loads(rows[0][2])['current_status']=='AVAILABLE'
        assert json.loads(rows[-1][2])['current_assignee']['id']==user
        assert json.loads(rows[-1][2])['current_location']['id']==station
        assert db.execute('select count(*) from assignments').fetchone()[0]==1
        assert db.execute('select count(*) from location_history').fetchone()[0]==1
        assert not db.execute('pragma foreign_key_check').fetchall()
        assert {r[0] for r in db.execute("select code from master_data where \"group\"='asset_status' and archived=0")}=={'available','in_use','maintenance','retired'}
    upgrade('head')
    with sqlite3.connect(database) as db:
        assert db.execute('select count(*) from asset_operations').fetchone()[0]==3
