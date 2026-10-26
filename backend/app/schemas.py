"""Response models for the non-GeoJSON endpoints."""
from typing import Literal, Optional, Union

from pydantic import BaseModel


class Health(BaseModel):
    status: Literal["healthy", "unhealthy", "demo_mode"]
    database: Literal["connected", "unavailable", "not_connected"]


class ConstituencyMPFound(BaseModel):
    found: Literal[True] = True
    constituency: str
    mp_name: str
    party: str
    current_position: Optional[str]
    source: str


class ConstituencyMPNotFound(BaseModel):
    found: Literal[False] = False
    message: str


ConstituencyMP = Union[ConstituencyMPFound, ConstituencyMPNotFound]


class AdminArea(BaseModel):
    found: bool
    constituency: Optional[str] = None
    type: Optional[str] = None
