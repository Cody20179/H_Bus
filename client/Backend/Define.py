﻿from pydantic import BaseModel,Field
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
    direction: Optional[Literal["去程", "返程", "回程", "0", "1"]] = None

class ReservationReq(BaseModel):
    user_id: int
    booking_time: datetime
    booking_number: int
    booking_start_station_name: str
    booking_end_station_name: str
    
class CancelReq(BaseModel):
    reservation_id: int
    cancel_reason: str 

# === 鞈?璅∪? ===
class CarBackupInsert(BaseModel):
    rcv_dt: Optional[str] = None 
    car_licence: str
    Gpstime: str
    X: float
    Y: float
    Speed: int
    Deg: int
    acc: Optional[bool] = None     # ???寞?撣?
    route: Optional[str] = None
    direction: Optional[str] = None
    Current_Loaction: Optional[str] = None

