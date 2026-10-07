import os,sqlite3,subprocess,sys
from pathlib import Path

def test_migration_restores_known_location_without_inventing_legacy_outcome(tmp_path):
    path=tmp_path/'outcomes.db';backend=Path(__file__).resolve().parents[1]
    env={**os.environ,'DATABASE_URL':'sqlite:///'+str(path)}
    def run(*args):
        result=subprocess.run([sys.executable,*args],cwd=backend,env=env,capture_output=True,text=True)
        assert result.returncode==0,result.stderr
    run('-m','alembic','upgrade','head');run('-m','app.seed')
    with sqlite3.connect(path) as db:
        asset,location=db.execute('SELECT id,current_location_id FROM assets WHERE current_location_id IS NOT NULL LIMIT 1').fetchone()
        status=db.execute("SELECT id FROM master_data WHERE [group]='asset_status' AND code='retired'").fetchone()[0]
        db.execute('UPDATE assets SET current_location_id=NULL,current_status=?,status_id=?,warehouse_id=NULL WHERE id=?',('RETIRED',status,asset))
        db.execute('UPDATE location_history SET ended_at=CURRENT_TIMESTAMP WHERE asset_id=? AND ended_at IS NULL',(asset,))
        old_history=db.execute('SELECT * FROM location_history ORDER BY id').fetchall()
        # Restore network columns too before replaying later migrations.
        for column in ('port_count','uplink_port_count','sfp_port_count'): db.execute(f'ALTER TABLE assets DROP COLUMN {column}')
        db.execute('ALTER TABLE subnets DROP COLUMN dhcp_start')
        db.execute('ALTER TABLE subnets DROP COLUMN dhcp_end')
        db.execute('ALTER TABLE ip_addresses DROP COLUMN assignment_type')
        for column in ('hostname','mac','asset_id'): db.execute(f'ALTER TABLE ip_addresses DROP COLUMN {column}')
        db.execute('ALTER TABLE maintenance DROP COLUMN resolution_outcome')
        db.execute("UPDATE alembic_version SET version_num='0009'")
    run('-m','alembic','upgrade','head')
    with sqlite3.connect(path) as db:
        assert db.execute('SELECT current_location_id FROM assets WHERE id=?',(asset,)).fetchone()[0]==location
        assert db.execute('SELECT * FROM location_history ORDER BY id').fetchall()[:len(old_history)]==old_history
        assert db.execute('SELECT location_id FROM location_history WHERE asset_id=? AND ended_at IS NULL',(asset,)).fetchone()[0]==location
        assert not db.execute('SELECT id FROM maintenance WHERE resolution_outcome IS NOT NULL').fetchall()
        assert db.execute("SELECT name FROM master_data WHERE [group]='asset_status' AND code='retired'").fetchone()[0]=='Hư / Ngừng sử dụng'
        assert not db.execute('PRAGMA foreign_key_check').fetchall()
