from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Literal, List
from datetime import datetime   
from MySQL import MySQL_Run
import pandas as pd
import uvicorn

app = FastAPI(title="花蓮小巴會員管理系統")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://127.0.0.1",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://192.168.0.126:5173",
        "null",                     # ← 允許從 file:// 開啟的頁面（origin 會是字串 "null"）
        "*",                        # 若你不帶 cookie/認證，可直接用萬用字元
    ],
    allow_credentials=False,        # 若未使用 cookie 或 Authorization，可設 False
    allow_methods=["*"],            # 讓預檢 OPTIONS 能過
    allow_headers=["*"],
)

class Route(BaseModel):
    route_id: int
    route_name: str
    stop_count: int
    direction: Literal["單向", "雙向"]
    start_stop: Optional[str] = None
    end_stop: Optional[str] = None
    status: int
    created_at: Optional[datetime] = None

# ====== 請求模型 ======
class RouteStationsQuery(BaseModel):
    route_id: int = Field(..., ge=1)
    # 可選：若你要過濾去/回/單程
    direction: Optional[Literal["去程", "回程", "單程"]] = None

# ====== 回應模型（對齊你實際的欄位）======
class StationOut(BaseModel):
    route_id: int
    route_name: str
    direction: Optional[str] = None
    stop_name: str
    latitude: float
    longitude: float
    eta_from_start: Optional[int] = None  # 分鐘(或秒) 看你DB定義
    stop_order: Optional[int] = None
    created_at: Optional[datetime] = None

@app.get("/")
def root():
    return {
        "message": "Hualien Mini Bus Backend System",
        "status": "Running",
        "features": ["User Management", "Access Control", "Database Integration"]
    }

@app.get("/All_Route", response_model=List[Route])
def All_Route():
    rows = MySQL_Run("SELECT * FROM bus_routes_total")
    columns = [c[0] for c in MySQL_Run("SHOW COLUMNS FROM bus_routes_total")]
    df = pd.DataFrame(rows, columns=columns)
    if "created_at" in df.columns:
        df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce") \
            .apply(lambda x: x.to_pydatetime() if pd.notnull(x) else None)
    records = df.where(pd.notnull(df), None).to_dict(orient="records")
    return records

@app.post("/Route_Stations", response_model=List[StationOut])
def get_route_stations(q: RouteStationsQuery):
    # --- 參數化查詢（你的 MySQL_Run 若支援 params，優先這個寫法） ---
    sql = "SELECT * FROM bus_route_stations WHERE route_id = %s"
    params = [q.route_id]
    if q.direction:
        sql += " AND direction = %s"
        params.append(q.direction)

    try:
        rows = MySQL_Run(sql, params)  # 若你的 MySQL_Run 不支援 params，就 fallback 用 f-string，但要小心注入
    except TypeError:
        # Fallback：有些自寫函式沒有 params 參數
        # 請務必確認 direction 的字串來源可信
        if q.direction:
            rows = MySQL_Run(f"SELECT * FROM bus_route_stations WHERE route_id = {int(q.route_id)} AND direction = '{q.direction}'")
        else:
            rows = MySQL_Run(f"SELECT * FROM bus_route_stations WHERE route_id = {int(q.route_id)}")

    columns = [c[0] for c in MySQL_Run("SHOW COLUMNS FROM bus_route_stations")]
    df = pd.DataFrame(rows, columns=columns)

    # --- 沒資料的處理（擇一：回404 或 回[]）---
    if df.empty:
        # 選擇一：回空陣列（前端好處理）
        return []
        # 選擇二：回 404
        # raise HTTPException(status_code=404, detail=f"route_id={q.route_id} 無站點資料")

    # --- 欄位名稱正規化（把 DB 欄位映射成 API 欄位）---
    col_map = {
        "station_name": "stop_name",
        "stop_name": "stop_name",
        "est_time": "eta_from_start",
        "eta_from_start": "eta_from_start",
        "order_no": "stop_order",
        "seq": "stop_order",
        # 你若有 station_id 欄位但不打算輸出，就不要映射
    }
    # 只 rename 存在的欄位，避免 KeyError
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

    # --- 型別防呆：數值、時間、NaN 轉換 ---
    # 經緯度
    if "latitude" in df.columns:
        df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    if "longitude" in df.columns:
        df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")

    # 到站時間 / 順序
    if "eta_from_start" in df.columns:
        df["eta_from_start"] = pd.to_numeric(df["eta_from_start"], errors="coerce").astype("Int64")
    if "stop_order" in df.columns:
        df["stop_order"] = pd.to_numeric(df["stop_order"], errors="coerce").astype("Int64")

    # created_at -> datetime（避免 pandas.Timestamp 造成驗證錯誤）
    if "created_at" in df.columns:
        df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce") \
            .apply(lambda x: x.to_pydatetime() if pd.notnull(x) else None)

    # 只保留我們要輸出的欄位（避免多餘欄位觸發驗證錯）
    desired_cols = [
        "route_id", "route_name", "direction", "stop_name",
        "latitude", "longitude", "eta_from_start", "stop_order", "created_at"
    ]
    keep_cols = [c for c in desired_cols if c in df.columns]
    df = df[keep_cols]

    # NaN -> None
    records = df.where(pd.notnull(df), None).to_dict(orient="records")

    # （可選）逐筆建模，能更早在後端發現資料異常
    data: List[StationOut] = [StationOut(**r) for r in records]
    return data




if __name__ == "__main__":
    uvicorn.run("HBus_Server:app", host="0.0.0.0", port=8500, reload=True)
