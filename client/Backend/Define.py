from pydantic import BaseModel,Field
from typing import Optional, Literal
from datetime import datetime

class StationOut(BaseModel):
    route_id: int
    route_name: str
    direction: Optional[str] = None
    stop_name: str
    latitude: float
    longitude: float
    eta_from_start: Optional[int] = None
    stop_order: Optional[int] = None
    created_at: Optional[datetime] = None

class RouteStationsQuery(BaseModel):
    route_id: int = Field(..., ge=1)
    direction: Optional[Literal["去程", "回程", "單程"]] = None

class ReservationReq(BaseModel):
    user_id: int
    booking_time: datetime
    booking_number: int
    booking_start_station_name: str
    booking_end_station_name: str
    
class CancelReq(BaseModel):
    reservation_id: int
    cancel_reason: str 