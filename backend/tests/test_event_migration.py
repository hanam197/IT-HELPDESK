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
        assert {r[0] for r in db.execute("select code from master_data where \"group\"='asset_status' and archived=0")}=={'available','in_use','maintenance','retired','disposed'}
    upgrade('head')
    with sqlite3.connect(database) as db:
        assert db.execute('select count(*) from asset_operations').fetchone()[0]==3


def test_five_status_upgrade_preserves_snapshots_repairs_and_foreign_keys(tmp_path):
    database=tmp_path/'status-flow.db'
    backend=Path(__file__).resolve().parents[1]
    env={**os.environ,'DATABASE_URL':'sqlite:///'+str(database)}
    def upgrade(version):
        result=subprocess.run([sys.executable,'-m','alembic','upgrade',version],cwd=backend,env=env,capture_output=True,text=True)
        assert result.returncode==0,result.stderr
    upgrade('0006')
    with sqlite3.connect(database) as db:
        def insert(table,**values):
            values={'created_at':'2026-01-01 00:00:00','updated_at':'2026-01-01 00:00:00','archived':0,**values}
            columns=','.join('"'+k+'"' for k in values)
            return db.execute(f'INSERT INTO {table} ({columns}) VALUES ({",".join("?" for _ in values)})',list(values.values())).lastrowid
        user=insert('users',username='migration',name='Migration tester',role='ADMIN',password_hash='unused')
        kind=insert('asset_types',name='Legacy laptop',prefix='LAP',track_location=1,allow_assignment=1,track_network=1,allow_ticket=1,track_maintenance=1,has_ports=0)
        repair_type=insert('master_data',group='maintenance_type',code='repair',name='Repair',color='slate')
        repair_status=insert('master_data',group='maintenance_status',code='open',name='Open',color='slate')
        for index,state in enumerate(['REPAIR_NEEDED','BROKEN','DAMAGED','WAITING_REPAIR']):
            row=db.execute('SELECT id FROM master_data WHERE "group"=? AND code=?',('asset_status',state.lower())).fetchone()
            sid=row[0] if row else insert('master_data',group='asset_status',code=state.lower(),name=state,color='slate')
            asset=insert('assets',code='OLD-'+state,name='Old asset',type_id=kind,status_id=sid,current_status=state,model='Old',serial=state)
            snapshot=json.dumps({'current_status':state,'maintenance':{'problem':'Hỏng màn hình','action_taken':'Chờ linh kiện'}})
            insert('asset_operations',number='OLD-EVENT-'+state,asset_id=asset,operation_type='RETURNED',operation_date='2026-01-01 00:00:00',performed_by=user,before_state=json.dumps({'current_status':'IN_USE'}),after_state=snapshot,reason='Thu hồi')
            insert('maintenance',number='OLD-REPAIR-'+state,asset_id=asset,type_id=repair_type,status_id=repair_status,previous_status_id=sid,technician_id=user,problem='Hỏng màn hình',diagnosis='Đứt cáp',action_taken='Chờ linh kiện',start_at='2026-01-01 00:00:00')
    upgrade('head')
    with sqlite3.connect(database) as db:
        assert {r[0] for r in db.execute('SELECT current_status FROM assets')}=={'MAINTENANCE'}
        assert {r[0] for r in db.execute('SELECT code FROM master_data WHERE "group"=\'asset_status\' AND archived=0')}=={'available','in_use','maintenance','retired','disposed'}
        for before,after,actor,when in db.execute('SELECT before_state,after_state,performed_by,operation_date FROM asset_operations'):
            assert json.loads(before)['current_status']=='IN_USE'
            state=json.loads(after)
            assert state['current_status']=='MAINTENANCE' and state['maintenance']['problem']=='Hỏng màn hình'
            assert state['maintenance']['action_taken']=='Chờ linh kiện' and actor==user and when=='2026-01-01 00:00:00'
        for code,problem,diagnosis in db.execute('SELECT d.code,m.problem,m.diagnosis FROM maintenance m JOIN master_data d ON d.id=m.previous_status_id'):
            assert (code,problem,diagnosis)==('maintenance','Hỏng màn hình','Đứt cáp')
        assert not db.execute('PRAGMA foreign_key_check').fetchall()
        try:
            db.execute("UPDATE assets SET current_status='BROKEN'")
            raise AssertionError('Database accepted obsolete status')
        except sqlite3.IntegrityError: pass
    upgrade('head')
    with sqlite3.connect(database) as db:
        assert db.execute('SELECT count(*) FROM asset_operations').fetchone()[0]==4
