from datetime import date, datetime, timezone
from sqlalchemy import String, Text, ForeignKey, Boolean, Date, DateTime, Numeric, Integer, JSON, Index, text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base

def now():
    return datetime.now(timezone.utc)

class Record:
    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now, onupdate=now)
    archived: Mapped[bool] = mapped_column(Boolean, default=False)

class User(Record, Base):
    __tablename__ = 'users'
    username: Mapped[str] = mapped_column(String(100), unique=True)
    name: Mapped[str] = mapped_column(String(150))
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(30), default='VIEWER')
    department: Mapped[str | None] = mapped_column(String(100))

class MasterData(Record, Base):
    __tablename__ = 'master_data'
    group: Mapped[str] = mapped_column(String(60))
    code: Mapped[str] = mapped_column(String(60))
    name: Mapped[str] = mapped_column(String(100))
    color: Mapped[str] = mapped_column(String(30), default='slate')
    __table_args__ = (UniqueConstraint('group', 'code'),)

class AssetType(Record, Base):
    __tablename__ = 'asset_types'
    name: Mapped[str] = mapped_column(String(100), unique=True)
    prefix: Mapped[str] = mapped_column(String(20))
    track_serial: Mapped[bool] = mapped_column(default=True)
    track_location: Mapped[bool] = mapped_column(default=True)
    allow_assignment: Mapped[bool] = mapped_column(default=False)
    allow_station: Mapped[bool] = mapped_column(default=True)
    track_network: Mapped[bool] = mapped_column(default=True)
    allow_ticket: Mapped[bool] = mapped_column(default=True)
    track_maintenance: Mapped[bool] = mapped_column(default=True)
    has_ports: Mapped[bool] = mapped_column(default=False)

class Location(Record, Base):
    __tablename__ = 'locations'
    name: Mapped[str] = mapped_column(String(100))
    kind: Mapped[str] = mapped_column(String(30))
    parent_id: Mapped[int | None] = mapped_column(ForeignKey('locations.id'))
    description: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(default=True)
    physical_location: Mapped[str | None] = mapped_column(String(200))
    department: Mapped[str | None] = mapped_column(String(100))
    floor: Mapped[str | None] = mapped_column(String(80))
    area: Mapped[str | None] = mapped_column(String(80))
    photo: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (UniqueConstraint('parent_id', 'name'),)

class Asset(Record, Base):
    __tablename__ = 'assets'
    warehouse_id: Mapped[int | None] = mapped_column(ForeignKey('warehouses.id'))
    current_status: Mapped[str] = mapped_column(String(20),default='AVAILABLE')
    current_location_id: Mapped[int | None] = mapped_column(ForeignKey('locations.id'))
    current_assignee_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'))
    code: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(150))
    type_id: Mapped[int] = mapped_column(ForeignKey('asset_types.id'))
    status_id: Mapped[int] = mapped_column(ForeignKey('master_data.id'))
    brand: Mapped[str | None] = mapped_column(String(100))
    model: Mapped[str] = mapped_column(String(100))
    serial: Mapped[str] = mapped_column(String(150), unique=True)
    received_date: Mapped[date | None] = mapped_column(Date)
    handover_date: Mapped[date | None] = mapped_column(Date)
    purchase_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    warranty_expiry: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    vendor: Mapped[str | None] = mapped_column(String(150))
    cost: Mapped[float | None] = mapped_column(Numeric(14, 2))
    description: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    photo: Mapped[str | None] = mapped_column(Text)

class LocationHistory(Record, Base):
    __tablename__ = 'location_history'
    asset_id: Mapped[int] = mapped_column(ForeignKey('assets.id'))
    from_location_id: Mapped[int | None] = mapped_column(ForeignKey('locations.id'))
    location_id: Mapped[int] = mapped_column(ForeignKey('locations.id'))
    technician_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    reason: Mapped[str] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (Index('uq_current_location', 'asset_id', unique=True, postgresql_where=text('ended_at IS NULL'), sqlite_where=text('ended_at IS NULL')),)

class Assignment(Record, Base):
    __tablename__ = 'assignments'
    asset_id: Mapped[int] = mapped_column(ForeignKey('assets.id'))
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    department: Mapped[str | None] = mapped_column(String(100))
    assigned_by: Mapped[int] = mapped_column(ForeignKey('users.id'))
    expected_return: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    returned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    condition_out: Mapped[str] = mapped_column(Text)
    condition_in: Mapped[str | None] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (Index('uq_active_assignment', 'asset_id', unique=True, postgresql_where=text('returned_at IS NULL'), sqlite_where=text('returned_at IS NULL')),)

class AssetOperation(Record, Base):
    __tablename__ = 'asset_operations'
    before_state: Mapped[dict | None] = mapped_column(JSON)
    after_state: Mapped[dict | None] = mapped_column(JSON)
    source_ref: Mapped[str | None] = mapped_column(String(120),unique=True)
    number: Mapped[str] = mapped_column(String(40), unique=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey('assets.id'))
    operation_type: Mapped[str] = mapped_column(String(30))
    from_entity_type: Mapped[str | None] = mapped_column(String(30))
    from_entity_id: Mapped[int | None] = mapped_column(Integer)
    to_entity_type: Mapped[str | None] = mapped_column(String(30))
    to_entity_id: Mapped[int | None] = mapped_column(Integer)
    operation_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    condition_before: Mapped[str | None] = mapped_column(Text)
    condition_after: Mapped[str | None] = mapped_column(Text)
    performed_by: Mapped[int] = mapped_column(ForeignKey('users.id'))
    reason: Mapped[str | None] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)

class Warehouse(Record, Base):
    __tablename__ = 'warehouses'
    code: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    location_id: Mapped[int] = mapped_column(ForeignKey('locations.id'))
    description: Mapped[str | None] = mapped_column(Text)

class InventoryItem(Record, Base):
    __tablename__ = 'inventory_items'
    code: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(150))
    category: Mapped[str] = mapped_column(String(80))
    unit: Mapped[str] = mapped_column(String(30), default='pcs')
    quantity: Mapped[float] = mapped_column(Numeric(14, 3), default=0)
    minimum_stock: Mapped[float] = mapped_column(Numeric(14, 3), default=0)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey('warehouses.id'))
    bin_shelf: Mapped[str | None] = mapped_column(String(80))
    description: Mapped[str | None] = mapped_column(Text)

class InventoryTransaction(Record, Base):
    __tablename__ = 'inventory_transactions'
    recipient_user_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'))
    recipient_location_id: Mapped[int | None] = mapped_column(ForeignKey('locations.id'))
    number: Mapped[str] = mapped_column(String(40), unique=True)
    transaction_type: Mapped[str] = mapped_column(String(20))
    warehouse_id: Mapped[int] = mapped_column(ForeignKey('warehouses.id'))
    asset_id: Mapped[int | None] = mapped_column(ForeignKey('assets.id'))
    item_id: Mapped[int | None] = mapped_column(ForeignKey('inventory_items.id'))
    quantity: Mapped[float] = mapped_column(Numeric(14, 3), default=1)
    transaction_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    source_vendor: Mapped[str | None] = mapped_column(String(150))
    condition: Mapped[str | None] = mapped_column(Text)
    performed_by: Mapped[int] = mapped_column(ForeignKey('users.id'))
    note: Mapped[str | None] = mapped_column(Text)

class Ticket(Record, Base):
    __tablename__ = 'tickets'
    number: Mapped[str] = mapped_column(String(40), unique=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    category_id: Mapped[int] = mapped_column(ForeignKey('master_data.id'))
    subcategory: Mapped[str | None] = mapped_column(String(100))
    priority_id: Mapped[int] = mapped_column(ForeignKey('master_data.id'))
    status_id: Mapped[int] = mapped_column(ForeignKey('master_data.id'))
    asset_id: Mapped[int | None] = mapped_column(ForeignKey('assets.id'))
    location_id: Mapped[int | None] = mapped_column(ForeignKey('locations.id'))
    reporter_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    technician_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'))
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class TicketActivity(Record, Base):
    __tablename__ = 'ticket_activities'
    ticket_id: Mapped[int] = mapped_column(ForeignKey('tickets.id'))
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    kind: Mapped[str] = mapped_column(String(40))
    body: Mapped[str] = mapped_column(Text)
    internal: Mapped[bool] = mapped_column(default=False)

class VLAN(Record, Base):
    __tablename__ = 'vlans'
    tag: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(100))
    site_id: Mapped[int] = mapped_column(ForeignKey('locations.id'))
    description: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (UniqueConstraint('site_id', 'tag'),)

class Subnet(Record, Base):
    __tablename__ = 'subnets'
    cidr: Mapped[str] = mapped_column(String(60), unique=True)
    gateway: Mapped[str | None] = mapped_column(String(60))
    dns: Mapped[str | None] = mapped_column(String(200))
    vlan_id: Mapped[int] = mapped_column(ForeignKey('vlans.id'))
    site_id: Mapped[int] = mapped_column(ForeignKey('locations.id'))
    description: Mapped[str | None] = mapped_column(Text)

class NetworkInterface(Record, Base):
    __tablename__ = 'interfaces'
    asset_id: Mapped[int] = mapped_column(ForeignKey('assets.id'))
    name: Mapped[str] = mapped_column(String(100))
    mac: Mapped[str] = mapped_column(String(17), unique=True)
    hostname: Mapped[str | None] = mapped_column(String(150))

class IPAddress(Record, Base):
    __tablename__ = 'ip_addresses'
    address: Mapped[str] = mapped_column(String(60), unique=True)
    interface_id: Mapped[int | None] = mapped_column(ForeignKey('interfaces.id'))
    subnet_id: Mapped[int] = mapped_column(ForeignKey('subnets.id'))
    status_id: Mapped[int] = mapped_column(ForeignKey('master_data.id'))
    description: Mapped[str | None] = mapped_column(Text)

class SwitchPort(Record, Base):
    __tablename__ = 'switch_ports'
    switch_id: Mapped[int] = mapped_column(ForeignKey('assets.id'))
    name: Mapped[str] = mapped_column(String(40))
    mode_id: Mapped[int] = mapped_column(ForeignKey('master_data.id'))
    native_vlan_id: Mapped[int | None] = mapped_column(ForeignKey('vlans.id'))
    tagged_vlans: Mapped[list] = mapped_column(JSON, default=list)
    connected_asset_id: Mapped[int | None] = mapped_column(ForeignKey('assets.id'))
    status_id: Mapped[int] = mapped_column(ForeignKey('master_data.id'))
    __table_args__ = (UniqueConstraint('switch_id', 'name'), UniqueConstraint('connected_asset_id'))

class Maintenance(Record, Base):
    __tablename__ = 'maintenance'
    number: Mapped[str] = mapped_column(String(40), unique=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey('assets.id'))
    type_id: Mapped[int] = mapped_column(ForeignKey('master_data.id'))
    status_id: Mapped[int] = mapped_column(ForeignKey('master_data.id'))
    problem: Mapped[str] = mapped_column(Text)
    diagnosis: Mapped[str | None] = mapped_column(Text)
    action_taken: Mapped[str | None] = mapped_column(Text)
    technician_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    vendor: Mapped[str | None] = mapped_column(String(150))
    cost: Mapped[float | None] = mapped_column(Numeric(14, 2))
    parts_replaced: Mapped[str | None] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)
    ticket_id: Mapped[int | None] = mapped_column(ForeignKey('tickets.id'))
    previous_status_id: Mapped[int | None] = mapped_column(ForeignKey('master_data.id'))

class Article(Record, Base):
    __tablename__ = 'articles'
    number: Mapped[str] = mapped_column(String(40), unique=True)
    title: Mapped[str] = mapped_column(String(200))
    category_id: Mapped[int] = mapped_column(ForeignKey('master_data.id'))
    summary: Mapped[str | None] = mapped_column(Text)
    problem: Mapped[str | None] = mapped_column(Text)
    symptoms: Mapped[str | None] = mapped_column(Text)
    cause: Mapped[str | None] = mapped_column(Text)
    resolution: Mapped[str] = mapped_column(Text)
    commands: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[str | None] = mapped_column(Text)
    author_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    status_id: Mapped[int] = mapped_column(ForeignKey('master_data.id'))

class TicketArticle(Record, Base):
    __tablename__ = 'ticket_articles'
    ticket_id: Mapped[int] = mapped_column(ForeignKey('tickets.id'))
    article_id: Mapped[int] = mapped_column(ForeignKey('articles.id'))
    __table_args__ = (UniqueConstraint('ticket_id', 'article_id'),)

class Attachment(Record, Base):
    __tablename__ = 'attachments'
    ticket_id: Mapped[int] = mapped_column(ForeignKey('tickets.id'))
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    filename: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str] = mapped_column(String(100), unique=True)

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey('users.id'))
    action: Mapped[str] = mapped_column(String(80))
    object_type: Mapped[str] = mapped_column(String(80))
    object_id: Mapped[int] = mapped_column(Integer)
    old_value: Mapped[dict | None] = mapped_column(JSON)
    new_value: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

class Counter(Base):
    __tablename__ = 'counters'
    key: Mapped[str] = mapped_column(String(40), primary_key=True)
    value: Mapped[int] = mapped_column(Integer, default=0)
