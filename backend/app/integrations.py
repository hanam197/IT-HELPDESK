"""Adapter contract for future read-only network inventory integrations."""
from typing import Protocol
from pydantic import BaseModel

class PortObservation(BaseModel):
    name: str
    mode: str
    native_vlan: int | None = None
    tagged_vlans: list[int] = []
    mac_addresses: list[str] = []
    up: bool

class NetworkInventoryProvider(Protocol):
    async def read_ports(self, asset_code: str) -> list[PortObservation]: ...
# Future adapters return observations. A reconciliation service must validate
# and persist them through domain services, with a service-account audit actor.
