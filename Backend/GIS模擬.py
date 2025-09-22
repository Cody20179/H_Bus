from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional
from MySQL import MySQL_Run2

app = FastAPI(
    title="H_Bus GIS API",
    version="V0.1.0",
    description="H_Bus 的資料庫數據傳遞。",
)

# === Pydantic Model ===
class CarGPS(BaseModel):
    rcv_dt: str
    car_licence: str
    Gpstime: str
    X: str
    Y: str
    Speed: Optional[int] = None
    Deg: Optional[int] = None
    acc: bool

app = FastAPI()

# === Pydantic Model ===
class CarGPS(BaseModel):
    rcv_dt: str
    car_licence: str
    Gpstime: str
    X: str
    Y: str
    Speed: Optional[int] = None
    Deg: Optional[int] = None
    acc: bool

# 1. 查詢所有資料
@app.get("/gps", tags=["GIS SQL"], summary="查詢所有資料")
def get_all():
    sql = "SELECT * FROM ttcarimport ORDER BY seq DESC LIMIT 100"
    return MySQL_Run2(sql)

# 2. 新增一筆資料
@app.post("/gps", tags=["GIS SQL"], summary="新增一筆資料")
def insert_data(data: CarGPS):
    """插入一筆新的 GPS 資料"""
    sql = """
        INSERT INTO ttcarimport (rcv_dt, car_licence, Gpstime, X, Y, Speed, Deg, acc)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    params = (data.rcv_dt, data.car_licence, data.Gpstime, data.X, data.Y,
              data.Speed, data.Deg, data.acc)
    MySQL_Run2(sql, params)
    return {"status": "success"}

# 3. 查詢某個車牌最新紀錄
@app.get("/gps/{car_licence}", tags=["GIS SQL"], summary="查詢某個車牌最新紀錄")
def get_latest_by_car(car_licence: str):
    sql = """
        SELECT * FROM ttcarimport 
        WHERE car_licence=%s 
        ORDER BY Gpstime DESC LIMIT 1
    """
    result = MySQL_Run2(sql, (car_licence,))
    return result