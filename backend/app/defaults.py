"""Initial vocabulary. Display names and custom entries are editable in Settings."""
from sqlalchemy import select
from .models import MasterData

DEFAULT_MASTER_DATA = {'asset_status': ['Available', 'In Use', 'Maintenance', 'Retired', 'Disposed'], 'ticket_status': ['Open', 'Assigned', 'In Progress', 'Waiting', 'Resolved', 'Closed', 'Cancelled'], 'priority': ['Low', 'Medium', 'High', 'Critical'], 'ticket_category': ['Hardware', 'Network', 'Printer', 'Software', 'Access Request', 'Other'], 'ip_status': ['Available', 'Used', 'Reserved', 'DHCP', 'Conflict'], 'port_mode': ['Access', 'Trunk', 'General', 'Unknown'], 'port_status': ['Up', 'Down', 'Disabled'], 'maintenance_type': ['Hardware', 'Network', 'Software', 'Power', 'Peripheral', 'Other'], 'maintenance_status': ['Open', 'Completed'], 'kb_category': ['Network', 'WiFi', 'Printer', 'Windows', 'Ubuntu', 'PDA', 'Camera', 'WMS', 'Hardware', 'Other'], 'article_status': ['Draft', 'Published', 'Archived']}

def install_defaults(db):
    for group,names in DEFAULT_MASTER_DATA.items():
        for name in names:
            code=name.lower().replace(" ","_")
            if not db.scalar(select(MasterData.id).where(MasterData.group==group,MasterData.code==code)):
                db.add(MasterData(group=group,code=code,name=name))
    db.flush()
