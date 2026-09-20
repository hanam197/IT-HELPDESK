"""Initial vocabulary. Display names and custom entries are editable in Settings."""
from sqlalchemy import select
from .models import MasterData

DEFAULT_MASTER_DATA = {'asset_status': ['Available', 'In Use', 'Assigned', 'Backup', 'Maintenance', 'Repair', 'Broken', 'Retired', 'Lost'], 'ticket_status': ['Open', 'Assigned', 'In Progress', 'Waiting', 'Resolved', 'Closed', 'Cancelled'], 'priority': ['Low', 'Medium', 'High', 'Critical'], 'ticket_category': ['Hardware', 'Network', 'Printer', 'Software', 'Access Request', 'Other'], 'ip_status': ['Available', 'Used', 'Reserved', 'DHCP', 'Conflict'], 'port_mode': ['Access', 'Trunk', 'General', 'Unknown'], 'port_status': ['Up', 'Down', 'Disabled'], 'maintenance_type': ['Repair', 'Preventive Maintenance', 'Cleaning', 'Upgrade', 'Replacement', 'Inspection'], 'maintenance_status': ['Open', 'Diagnosing', 'Repairing', 'Waiting Parts', 'Completed', 'Cancelled'], 'kb_category': ['Network', 'WiFi', 'Printer', 'Windows', 'Ubuntu', 'PDA', 'Camera', 'WMS', 'Hardware', 'Other'], 'article_status': ['Draft', 'Published', 'Archived']}

def install_defaults(db):
    for group,names in DEFAULT_MASTER_DATA.items():
        for name in names:
            code=name.lower().replace(" ","_")
            if not db.scalar(select(MasterData.id).where(MasterData.group==group,MasterData.code==code)):
                db.add(MasterData(group=group,code=code,name=name))
    db.flush()
