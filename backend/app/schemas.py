from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, create_model
from sqlalchemy import inspect
from . import models as m

RESOURCES = {'users': m.User, 'master-data': m.MasterData, 'asset-types': m.AssetType, 'locations': m.Location, 'assets': m.Asset, 'assignments': m.Assignment, 'location-history': m.LocationHistory, 'asset-operations': m.AssetOperation, 'warehouses': m.Warehouse, 'inventory-items': m.InventoryItem, 'inventory-transactions': m.InventoryTransaction, 'tickets': m.Ticket, 'ticket-activities': m.TicketActivity, 'vlans': m.VLAN, 'subnets': m.Subnet, 'interfaces': m.NetworkInterface, 'ip-addresses': m.IPAddress, 'switch-ports': m.SwitchPort, 'maintenance': m.Maintenance, 'articles': m.Article, 'ticket-articles': m.TicketArticle, 'audit-logs': m.AuditLog}
READ_ONLY = {'assignments', 'location-history', 'asset-operations', 'inventory-transactions', 'ticket-activities', 'audit-logs'}
SYSTEM_FIELDS = {'id', 'created_at', 'updated_at', 'archived', 'password_hash', 'number', 'reporter_id', 'author_id', 'resolved_at', 'end_at', 'previous_status_id'}

class StrictSchema(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)

# Generate typed Pydantic DTOs from column metadata; domain validation stays in services.
def build_schema(model, partial=False):
    fields = {}
    for c in inspect(model).columns:
        if c.name in SYSTEM_FIELDS: continue
        if model is m.Asset and c.name in {'code', 'warehouse_id','current_status','current_location_id','current_assignee_id'}: continue
        if model is m.Location and c.name == 'photo': continue
        if model is m.InventoryItem and c.name == 'quantity': continue
        t = c.type.python_type
        if c.nullable: t = t | None
        default = None if partial or c.nullable else c.default.arg if c.default is not None and c.default.is_scalar else None if c.default is not None else ...
        if model is m.Asset and c.name=='name': default=None
        if t is str:
            fields[c.name] = (t, Field(default=default, min_length=1, max_length=getattr(c.type, 'length', None) or 50000))
        else: fields[c.name] = (t, default)
    if model is m.User:
        fields['password'] = (str, Field(default=None if partial else ..., min_length=12, max_length=128))
    return create_model(model.__name__ + ('Update' if partial else 'Create'), __base__=StrictSchema, **fields)

SCHEMAS = {key: (build_schema(model), build_schema(model, True)) for key, model in RESOURCES.items() if key not in READ_ONLY}
class Login(StrictSchema):
    username: str
    password: str
class Move(StrictSchema):
    location_id: int
    reason: str = Field(min_length=3, max_length=2000)
    note: str | None = None
class Assign(StrictSchema):
    user_id: int
    department: str | None = None
    expected_return: datetime | None = None
    condition_out: str = Field(min_length=2)
    note: str | None = None
class Return(StrictSchema):
    condition_in: str = Field(min_length=2)
    location_id: int | None = None
    note: str | None = None
class Transfer(Assign):
    condition_in: str = Field(min_length=2)
class Comment(StrictSchema):
    body: str = Field(min_length=1, max_length=20000)
    internal: bool = False

class StockMovement(StrictSchema):
    transaction_type: Literal['RECEIVE', 'ISSUE']
    warehouse_id: int = Field(gt=0)
    asset_id: int | None = Field(default=None, gt=0)
    item_id: int | None = Field(default=None, gt=0)
    new_item: dict | None = None
    quantity: Decimal = Field(default=1, gt=0, max_digits=14, decimal_places=3, allow_inf_nan=False)
    transaction_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    recipient_user_id: int | None = Field(default=None, gt=0)
    recipient_location_id: int | None = Field(default=None, gt=0)
    source_vendor: str | None = Field(default=None, max_length=150)
    condition: str = Field(default='Good', min_length=2, max_length=2000)
    note: str | None = Field(default=None, max_length=5000)

class Retire(StrictSchema):
    reason: str = Field(min_length=3,max_length=2000)

class Reassign(StrictSchema):
    user_id: int = Field(gt=0)
    reason: str = Field(min_length=3,max_length=2000)
    note: str | None = None
