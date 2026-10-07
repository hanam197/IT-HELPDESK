import os
from pathlib import Path
import sqlite3
import subprocess
import sys


def test_issue_migration_removes_ticket_fk_preserves_records_and_state(tmp_path):
    database=tmp_path/'maintenance.db';backend=Path(__file__).resolve().parents[1]
    env={**os.environ,'DATABASE_URL':'sqlite:///'+str(database)}
    def run(*args):
        result=subprocess.run([sys.executable,*args],cwd=backend,env=env,capture_output=True,text=True)
        assert result.returncode==0,result.stderr
    run('-m','alembic','upgrade','head');run('-m','app.seed')
    with sqlite3.connect(database) as db:
        # Recreate the previous schema after seeding with current application models.
        db.execute('ALTER TABLE maintenance DROP COLUMN replacement_asset_ids')
        # Restore network columns too before replaying later migrations.
        for column in ('port_count','uplink_port_count','sfp_port_count'): db.execute(f'ALTER TABLE assets DROP COLUMN {column}')
        db.execute('ALTER TABLE subnets DROP COLUMN dhcp_start')
        db.execute('ALTER TABLE subnets DROP COLUMN dhcp_end')
        db.execute('ALTER TABLE ip_addresses DROP COLUMN assignment_type')
        for column in ('hostname','mac','asset_id'): db.execute(f'ALTER TABLE ip_addresses DROP COLUMN {column}')
        db.execute('ALTER TABLE maintenance DROP COLUMN resolution_outcome')
        db.execute('ALTER TABLE maintenance ADD COLUMN ticket_id INTEGER REFERENCES tickets(id)')
        db.execute("UPDATE alembic_version SET version_num='0007'")
        record=db.execute('SELECT id,asset_id,problem,diagnosis FROM maintenance LIMIT 1').fetchone()
        old_status=db.execute("INSERT INTO master_data ([group],code,name,color,archived,created_at,updated_at) VALUES ('maintenance_status','waiting_parts','Waiting Parts','amber',0,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)").lastrowid
        db.execute('UPDATE maintenance SET status_id=? WHERE id=?',(old_status,record[0]))
        old_type=db.execute("INSERT INTO master_data (\"group\",code,name,color,archived,created_at,updated_at) VALUES ('maintenance_type','repair','Repair','slate',0,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)").lastrowid
        db.execute('UPDATE maintenance SET ticket_id=1,type_id=?,note=? WHERE id=?',(old_type,'Giữ ghi chú gốc',record[0]))
        before_asset=db.execute('SELECT current_status,current_location_id,current_assignee_id,warehouse_id FROM assets WHERE id=?',(record[1],)).fetchone()
        before_events=db.execute('SELECT count(*) FROM asset_operations').fetchone()[0]
        before_count=db.execute('SELECT count(*) FROM maintenance').fetchone()[0]
        ticket=db.execute('SELECT number FROM tickets WHERE id=1').fetchone()[0]
    run('-m','alembic','upgrade','head')
    with sqlite3.connect(database) as db:
        assert 'ticket_id' not in {r[1] for r in db.execute('PRAGMA table_info(maintenance)')}
        assert not any(r[2]=='tickets' for r in db.execute('PRAGMA foreign_key_list(maintenance)'))
        assert db.execute('SELECT count(*) FROM maintenance').fetchone()[0]==before_count
        assert db.execute('SELECT problem,diagnosis FROM maintenance WHERE id=?',(record[0],)).fetchone()==record[2:]
        note=db.execute('SELECT note FROM maintenance WHERE id=?',(record[0],)).fetchone()[0]
        assert 'Giữ ghi chú gốc' in note and 'Repair' in note and ticket in note
        assert db.execute('SELECT current_status,current_location_id,current_assignee_id,warehouse_id FROM assets WHERE id=?',(record[1],)).fetchone()==before_asset
        assert db.execute('SELECT count(*) FROM asset_operations').fetchone()[0]==before_events
        assert {r[0] for r in db.execute("SELECT code FROM master_data WHERE \"group\"='maintenance_type' AND archived=0")}=={'hardware','network','software','power','peripheral','other'}
        assert not db.execute('PRAGMA foreign_key_check').fetchall()
        assert {r[0] for r in db.execute("SELECT code FROM master_data WHERE [group]='maintenance_status' AND archived=0")}=={'open','completed'}
        assert 'replacement_asset_ids' in {r[1] for r in db.execute('PRAGMA table_info(maintenance)')}
        assert 'Waiting Parts' in note
    run('-m','alembic','upgrade','head')
