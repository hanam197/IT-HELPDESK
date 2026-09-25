from datetime import timedelta
from sqlalchemy import select
from .database import SessionLocal, settings
from . import models as m
from .security import passwords
from .services import save, move, assign, activity, master
from .schemas import Move, Assign
from .asset_events import snapshot, set_status, emit

def seed():
    if len(settings.seed_password)<12: raise RuntimeError('SEED_PASSWORD must be at least 12 characters')
    with SessionLocal() as db:
        if db.scalar(select(m.User).limit(1)): return
        for username,name,role,department in [('admin','Nguyen Minh Anh','ADMIN','IT Operations'),('manager','Tran Quang Huy','IT_MANAGER','IT Operations'),('support','Le Hoang Nam','IT_SUPPORT','IT Support'),('viewer','Nguyen Van An','VIEWER','Warehouse')]:
            db.add(m.User(username=username,name=name,password_hash=passwords.hash(settings.seed_password),role=role,department=department))
        db.flush(); user=db.get(m.User,1)
        groups={'asset_status':['Available','In Use','Maintenance','Retired'],'ticket_status':['Open','Assigned','In Progress','Waiting','Resolved','Closed','Cancelled'],'priority':['Low','Medium','High','Critical'],'ticket_category':['Hardware','Network','Printer','Software','Access Request','Other'],'ip_status':['Available','Used','Reserved','DHCP','Conflict'],'port_mode':['Access','Trunk','General','Unknown'],'port_status':['Up','Down','Disabled'],'maintenance_type':['Repair','Preventive Maintenance','Cleaning','Upgrade','Replacement','Inspection'],'maintenance_status':['Open','Diagnosing','Repairing','Waiting Parts','Completed','Cancelled'],'kb_category':['Network','WiFi','Printer','Windows','Ubuntu','PDA','Camera','WMS','Hardware','Other'],'article_status':['Draft','Published','Archived']}
        for group,names in groups.items():
            for name in names:
                code=name.lower().replace(' ','_')
                if not db.scalar(select(m.MasterData.id).where(m.MasterData.group==group,m.MasterData.code==code)):
                    db.add(m.MasterData(group=group,code=code,name=name))
        db.flush(); types={}
        for name,prefix,assignable,ports in [('Desktop','PC',True,False),('Laptop','LAP',True,False),('PDA','PDA',True,False),('Label Printer','PRN',False,False),('A4 Printer','A4',False,False),('Scanner','SCN',True,False),('Monitor','MON',False,False),('Access Point','AP',False,False),('Switch','SW',False,True),('Router','RTR',False,False),('Firewall','FW',False,False),('Camera','CAM',False,False),('NVR','NVR',False,False),('UPS','UPS',False,False),('Server','SRV',False,False),('Other','OTH',False,False)]:
            t=m.AssetType(name=name,prefix=prefix,allow_assignment=assignable,has_ports=ports); db.add(t); db.flush(); types[name]=t
        sites={}; stations={}
        for site in ['Q7','HN']:
            row=m.Location(name=site,kind='site'); db.add(row); db.flush(); sites[site]=row
            for area in ['OUTBOUND','INBOUND','QC','INVENTORY','TRANSPORT','OFFICE','IT STORAGE']:
                a=m.Location(name=area,kind='team',parent_id=row.id); db.add(a); db.flush(); stations[site+'/'+area]=a
                for station in {'OUTBOUND':['DG-01BD','DG-12AD','DG-18BD'],'QC':['QC-01','QC-08'],'INBOUND':['IB-01'],'TRANSPORT':['TRANS-002']}.get(area,[]):
                    s=m.Location(name=station,kind='station',parent_id=a.id); db.add(s); db.flush(); stations[site+'/'+station]=s
        for site in sites:
            storage=m.Location(name='WAREHOUSE',kind='station',parent_id=stations[site+'/IT STORAGE'].id)
            db.add(storage); db.flush()
            db.add(m.Warehouse(code='WH-'+site,name=site+' IT Warehouse',location_id=storage.id))
        db.flush()
        vlan=save(db,'vlans',{'tag':20,'name':'Warehouse devices','site_id':sites['Q7'].id,'description':'Printers, PDAs and workstations'},user)
        for tag,name in [(10,'Corporate'),(6,'Guest WiFi')]: save(db,'vlans',{'tag':tag,'name':name,'site_id':sites['Q7'].id},user)
        subnet=save(db,'subnets',{'cidr':'192.168.20.0/24','gateway':'192.168.20.1','dns':'1.1.1.1,8.8.8.8','vlan_id':vlan.id,'site_id':sites['Q7'].id},user)
        assets={}
        fixtures=[('PRN-012','Outbound label printer','Label Printer','Zebra','ZT411','in_use','DG-18BD'),('PDA-035','Warehouse handheld scanner','PDA','Zebra','TC52','available','DG-01BD'),('LAP-023','Operations laptop','Laptop','Dell','Latitude 5440','available','OFFICE'),('SW-005','SWKHOMAT1','Switch','Cisco','SG350-28P','in_use','IT STORAGE'),('AP-018','Outbound access point','Access Point','Ubiquiti','U6 Pro','in_use','DG-18BD'),('CAM-025','Loading dock camera','Camera','Hikvision','DS-2CD','in_use','TRANS-002'),('PRN-018','QC label printer','Label Printer','Zebra','ZD421','in_use','QC-08'),('A4-003','Office multifunction printer','A4 Printer','Brother','MFC-L5900','in_use','OFFICE')]
        for idx,(code,name,type_name,brand,model,status,station) in enumerate(fixtures):
            a=save(db,'assets',{'code':code,'name':name,'type_id':types[type_name].id,'status_id':master(db,'asset_status',status),'brand':brand,'model':model,'serial':f'{brand.upper()}-2026-{idx+1000}','received_date':(m.now()-timedelta(days=120)).date(),'handover_date':(m.now()-timedelta(days=110)).date(),'description':f'{name} serving Q7 operations.'},user); assets[code]=a
            before=snapshot(db,a)
            move(db,a.id,Move(location_id=stations['Q7/DG-12AD'].id,reason='Lắp đặt ban đầu'),user,warehouse_flow=True)
            set_status(db,a,'IN_USE')
            emit(db,a,'ISSUED',user,before,description='Cấp cho trạm vận hành')
            move(db,a.id,Move(location_id=stations['Q7/'+station].id,reason='Relocated for current operations'),user)
            interface=save(db,'interfaces',{'asset_id':a.id,'name':'Ethernet 1','mac':'7C:71:76:36:F5:F9' if idx==0 else f'AA:BB:CC:DD:EE:{idx:02X}','hostname':code.lower()},user)
            save(db,'ip-addresses',{'address':f'192.168.20.{80+idx}','interface_id':interface.id,'subnet_id':subnet.id,'status_id':master(db,'ip_status','used')},user)
        for i in range(90,95): save(db,'ip-addresses',{'address':f'192.168.20.{i}','subnet_id':subnet.id,'status_id':master(db,'ip_status','available')},user)
        for i in range(1,13):
            save(db,'switch-ports',{'switch_id':assets['SW-005'].id,'name':f'Gi{i}','mode_id':master(db,'port_mode','trunk' if i in [1,9] else 'access'),'native_vlan_id':vlan.id,'tagged_vlans':[vlan.id] if i in [1,9] else [],'connected_asset_id':assets['PRN-012'].id if i==3 else assets['AP-018'].id if i==9 else None,'status_id':master(db,'port_status','up' if i in [1,3,9] else 'down')},user)
        for code,uid in [('PDA-035',4),('LAP-023',2)]: assign(db,assets[code].id,Assign(user_id=uid,department='Operations',condition_out='Good, tested and complete',expected_return=m.now()+timedelta(days=90)),user)
        specs=[('Printer skipping labels','PRN-012','Printer','High','In Progress'),('PDA cannot connect to WiFi','PDA-035','Network','High','Open'),('Laptop battery drains quickly','LAP-023','Hardware','Medium','Waiting'),('QC printer sensor failure','PRN-018','Printer','Critical','Assigned'),('Camera image is blurry','CAM-025','Hardware','Low','Open'),('Update office printer driver','A4-003','Software','Medium','Resolved'),('Intermittent label alignment','PRN-012','Printer','Low','Closed'),('Printer ribbon calibration','PRN-012','Printer','Medium','Resolved')]
        for idx,(title,code,category,priority,status) in enumerate(specs):
            t=save(db,'tickets',{'title':title,'description':title+'. Reported by the warehouse operations team during the morning shift. Please investigate and verify with the user.','category_id':master(db,'ticket_category',category.lower()),'priority_id':master(db,'priority',priority.lower()),'status_id':master(db,'ticket_status',status.lower().replace(' ','_')),'asset_id':assets[code].id,'location_id':stations['Q7/DG-18BD'].id,'technician_id':3 if idx%2==0 else None,'due_at':m.now()+timedelta(hours=idx-3)},user)
            t.created_at=m.now()-timedelta(days=idx%6,hours=2)
            activity(db,t,user,'Device reachable on the network. Inspecting hardware and recent configuration.','comment')
            if idx==3: save(db,'maintenance',{'asset_id':assets[code].id,'type_id':master(db,'maintenance_type','repair'),'status_id':master(db,'maintenance_status','waiting_parts'),'problem':'Label sensor is failing intermittently','diagnosis':'Sensor replacement required','technician_id':3,'ticket_id':t.id,'vendor':'Zebra Service Vietnam','cost':85,'due_at':m.now()-timedelta(days=1)},user)
        for title,cat,summary,resolution in [('Trace MAC Address to Switch Port','Network','Locate a connected device using its MAC address.','## 1. Find the MAC address\nCheck the asset network tab.\n\n## 2. Inspect the switch\n```text\nshow mac address-table address 7c71.7636.f5f9\nshow interfaces status\n```\n\n## 3. Verify\nConfirm the connected asset and document the port in IPAM.'),('Calibrate a Zebra label printer','Printer','Resolve label alignment and sensor issues.','## Calibration\n1. Check label stock and ribbon.\n2. Clean the media sensor.\n3. Run media calibration.\n4. Print three test labels.'),('Reconnect a warehouse PDA to WiFi','PDA','Restore the warehouse wireless connection.','## Troubleshooting\n1. Confirm the warehouse SSID.\n2. Check signal and IP allocation.\n3. Reconnect and verify WMS access.\n4. Record findings in the ticket.')]:
            a=save(db,'articles',{'title':title,'category_id':master(db,'kb_category',cat.lower()),'summary':summary,'resolution':resolution,'tags':cat.lower()+',troubleshooting','status_id':master(db,'article_status','published')},user)
            save(db,'ticket-articles',{'ticket_id':1,'article_id':a.id},user)
        db.commit(); print('Demo data ready. Accounts: admin, manager, support, viewer. Use configured SEED_PASSWORD.')
if __name__=='__main__': seed()
