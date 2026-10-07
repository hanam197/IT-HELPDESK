from datetime import datetime, timezone
from sqlalchemy import select
from app import models as m
from app.database import SessionLocal
from app.dashboard_analytics import activity_analytics


def test_activity_uses_vietnam_day_boundaries_complete_history_and_zero_days():
    with SessionLocal() as db:
        asset=db.scalar(select(m.Asset.id)); user=db.scalar(select(m.User.id))
        rows=[('2035-05-31T17:00:00','RECEIVED'),('2035-05-31T16:59:00','RECEIVED'),('2035-06-07T16:59:00','ISSUED'),('2035-06-07T17:00:00','ISSUED'),('2035-06-04T06:00:00','UPDATED'),('2035-06-04T06:00:00','LEGACY_EVENT')]
        rows += [('2035-06-05T06:00:00','RETURNED')]*14
        for index,(date,kind) in enumerate(rows):
            db.add(m.AssetOperation(number=f'ANALYTICS-TEST-{index}',asset_id=asset,performed_by=user,operation_type=kind,operation_date=datetime.fromisoformat(date).replace(tzinfo=timezone.utc)))
        db.flush()
        result=activity_analytics(db,7,datetime(2035,6,7,5,tzinfo=timezone.utc))
        assert result['from']=='2035-06-01' and result['to']=='2035-06-07'
        assert result['total']==17 and result['previous_total']==1
        assert len(result['daily'])==7
        assert result['daily'][0]['received']==1
        assert result['daily'][1]['total']==0
        assert result['daily'][4]['returned']==14
        assert result['daily'][-1]['issued']==1
        assert sum(day['total'] for day in result['daily'])==result['total']
        assert sum(day['other'] for day in result['daily'])==1
        db.rollback()


def test_dashboard_analytics_period_and_empty_location_drilldown(client):
    for days in (7,30,90):
        result=client.get('/api/dashboard',params={'days':days})
        assert result.status_code==200,result.text
        data=result.json()
        assert len(data['analytics']['daily'])==days
        assert data['analytics']['total']==sum(day['total'] for day in data['analytics']['daily'])
        assert 'stats' in data and 'attention' in data
    assert client.get('/api/dashboard?days=1').status_code==422
    assert client.get('/api/dashboard?days=91').status_code==422
    result=client.get('/api/assets',params={'location':'Chưa có vị trí'})
    assert result.status_code==200,result.text
    assert all(asset['current_location_id'] is None for asset in result.json()['items'])
