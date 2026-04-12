"""PropAPI Python SDK — 土地リスク調査 API クライアント."""

from propapi.client import PropAPI, AsyncPropAPI
from propapi.models import (
    InspectResponse,
    HazardResponse,
    ZoningResponse,
    FloodDetail,
    LandslideDetail,
    TsunamiDetail,
    LiquefactionDetail,
    CompositeScore,
    LocationInfo,
    InspectMeta,
)
from propapi.exceptions import PropAPIError, AuthenticationError, RateLimitError

__version__ = "0.1.0"

__all__ = [
    "PropAPI",
    "AsyncPropAPI",
    "InspectResponse",
    "HazardResponse",
    "ZoningResponse",
    "FloodDetail",
    "LandslideDetail",
    "TsunamiDetail",
    "LiquefactionDetail",
    "CompositeScore",
    "LocationInfo",
    "InspectMeta",
    "PropAPIError",
    "AuthenticationError",
    "RateLimitError",
]
