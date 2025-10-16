# ====================================
# 🧩 專案內部模組
# ====================================
from Backend import Define
from Backend.MySQL import MySQL_Doing

# ====================================
# 📦 第三方套件
# ====================================
from fastapi import FastAPI, Request, HTTPException, APIRouter, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from dotenv import load_dotenv
from pydantic import BaseModel, Field
import pandas as pd
import redis
import httpx

# ====================================
# ✅ 標準庫
# ====================================
import os
import json
import time
import hmac
import base64
import hashlib
import secrets
import requests
import tempfile
import qrcode
import urllib.parse
import numpy as np
import pandas as pd
from datetime import datetime
from urllib.parse import urlparse, quote
from binascii import unhexlify
from base64 import b64encode, b64decode
from decimal import Decimal, InvalidOperation
from typing import List

api = APIRouter(prefix='/api')

load_dotenv()
MySQL_Doing = MySQL_Doing()

app = FastAPI(
    title="H_Bus API",
    version="V0.1.0",
    description="H_Bus 服務的最小 API 範本，含健康檢查與根路由。",
)

# === 加入 CORS 設定 ===    
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://([a-zA-Z0-9-]+\.ngrok-free\.app|localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|140\.134\.\d+\.\d+|10\.\d+\.\d+\.\d+)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# === Redis 初始化 ===
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# === URL 相關設定 ===
BASE_URL = os.getenv("FRONTEND_DEFAULT_URL")
FRONTEND_DEFAULT_URL = f"{BASE_URL}/profile"
FRONTEND_DEFAULT_HOST = urlparse(FRONTEND_DEFAULT_URL).hostname if FRONTEND_DEFAULT_URL.startswith(('http://', 'https://')) else None
r = redis.from_url(REDIS_URL, decode_responses=True)

# === LINE 相關設定 ===
CHANNEL_ID = os.getenv("LINE_CHANNEL_ID")
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
CALLBACK_PATH = "/auth/line/callback"
AUTHORIZE_URL = "https://access.line.me/oauth2/v2.1/authorize"
TOKEN_URL = "https://api.line.me/oauth2/v2.1/token"
PROFILE_URL = "https://api.line.me/v2/profile"
APP_SESSION_SECRET = os.getenv("APP_SESSION_SECRET", "my-secret")

# === 金流 相關設定 ===
MERCHANT_ID   = os.getenv("MERCHANT_ID", "")
TERMINAL_ID   = os.getenv("TERMINAL_ID", "")
STORE_CODE    = os.getenv("STORE_CODE", "")
KEY_HEX       = os.getenv("KEY", "")
IV_HEX        = os.getenv("IV", "")
LAYMON        = os.getenv("LAYMON", "iqrc.epay365.com.tw")  # 雷門 host，不要加 https://
PUBLIC_BASE   = os.getenv("FRONTEND_DEFAULT_URL", "").rstrip("/") 

if not all([MERCHANT_ID, TERMINAL_ID, STORE_CODE, KEY_HEX, IV_HEX, PUBLIC_BASE]):
    raise RuntimeError("環境變數缺失：請確認 MERCHANT_ID / TERMINAL_ID / STORE_CODE / KEY / IV / PUBLIC_BASE_URL")

KEY = bytes.fromhex(KEY_HEX)
IV  = bytes.fromhex(IV_HEX)

# === Session 與 Token 工具 ===
class SessionManager:
    @staticmethod
    def b64url(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).decode().rstrip("=")
    @staticmethod
    def _sign(data: bytes) -> str:
        sig = hmac.new(APP_SESSION_SECRET.encode(), data, hashlib.sha256).digest()
        return base64.urlsafe_b64encode(sig).decode().rstrip("=")
    @staticmethod
    def make_session_token(user_id: str, ttl: int = 7*24*3600) -> str:
        payload = {"uid": user_id, "exp": int(time.time()) + ttl}
        raw = json.dumps(payload, separators=(",", ":")).encode()
        return f"{base64.urlsafe_b64encode(raw).decode().rstrip('=')}.{SessionManager._sign(raw)}"
    @staticmethod
    def verify_session_token(token: str | None) -> str | None:
        if not token or "." not in token:
            return None
        try:
            b64p, sig = token.split(".", 1)
            payload = base64.urlsafe_b64decode(b64p + "===")
            if SessionManager._sign(payload) != sig:
                return None
            obj = json.loads(payload.decode())
            if obj.get("exp", 0) < int(time.time()):
                return None
            return obj.get("uid")
        except Exception:
            return None

# === LINE OAuth 流程 ===
class LineAuth:
    @staticmethod
    def get_login_url(state, challenge):
        redirect_uri = f"{BASE_URL}{CALLBACK_PATH}"
        params = {
            "response_type": "code",
            "client_id": CHANNEL_ID,
            "redirect_uri": redirect_uri,
            "state": state,
            "scope": "openid profile",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
        return f"{AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"

    @staticmethod
    async def exchange_token(code, verifier):
        redirect_uri = f"{BASE_URL}{CALLBACK_PATH}"
        form = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "client_id": CHANNEL_ID,
            "client_secret": CHANNEL_SECRET,
            "code_verifier": verifier,
        }
        async with httpx.AsyncClient() as client:
            tr = await client.post(TOKEN_URL, data=form, headers={"Content-Type":"application/x-www-form-urlencoded"})
            if tr.status_code != 200:
                raise HTTPException(400, f"Token error: {tr.text}")
            token = tr.json()
            prof = await client.get(PROFILE_URL, headers={"Authorization": f"Bearer {token['access_token']}"})
            if prof.status_code != 200:
                raise HTTPException(400, f"Profile error: {prof.text}")
            profile = prof.json()
        return token, profile

# === Helper: return_to 安全檢查 ===
def _is_safe_return_to(url: str) -> bool:
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        host = parsed.hostname or ""
        # 允許本機/內網
        if host in ("localhost", "127.0.0.1") or host.startswith("192.168.") or host.startswith("10."):
            return True
        # 允許 ngrok
        if host.endswith(".ngrok-free.app"):
            return True
        # 允許環境變數清單
        allowed_env = os.getenv("ALLOWED_RETURN_ORIGINS", "")
        if allowed_env:
            allowed_list = [o.strip() for o in allowed_env.split(",") if o.strip()]
            origin = f"{parsed.scheme}://{parsed.hostname}:{parsed.port}" if parsed.port else f"{parsed.scheme}://{parsed.hostname}"
            if origin in allowed_list:
                return True
        return False
    except Exception:
        return False

def _default_frontend_url(request: Request, path: str = "/profile") -> str:
    """登入後預設導向網址：優先使用 ngrok/指定網域，其餘回退環境變數"""
    try:
        origin = request.headers.get("origin")
        if origin:
            parsed = urlparse(origin)
            host = parsed.hostname or ""
            if host and (host.endswith(".ngrok-free.app") or (FRONTEND_DEFAULT_HOST and host == FRONTEND_DEFAULT_HOST)):
                candidate = f"{origin.rstrip('/')}{path}"
                if _is_safe_return_to(candidate):
                    return candidate
    except Exception:
        pass
    if FRONTEND_DEFAULT_URL.startswith(("http://", "https://")):
        return FRONTEND_DEFAULT_URL
    return f"http://{FRONTEND_DEFAULT_URL.lstrip('/') }"

def _build_login_url(request: Request, return_to: str | None = None) -> str:
    """組出 LINE Login 的登入 URL，並帶上 return_to。"""
    try:
        rt = return_to or _default_frontend_url(request)
        q = urllib.parse.urlencode({"return_to": rt})
        return f"{BASE_URL}/auth/line/login?{q}"
    except Exception:
        return f"{BASE_URL}/auth/line/login"

def _unauthorized_response(request: Request, detail: str):
    """依請求型態決定回傳 302 導轉或 401 JSON，避免僅在前端顯示而無指引。"""
    login_url = _build_login_url(request)
    accept = (request.headers.get("accept") or "").lower()
    sec_mode = (request.headers.get("sec-fetch-mode") or "").lower()
    sec_dest = (request.headers.get("sec-fetch-dest") or "").lower()
    wants_html = ("text/html" in accept) and ("application/json" not in accept)
    is_navigation = (sec_mode == "navigate") or (sec_dest in {"document", "iframe"})

    if wants_html or is_navigation:
        # 瀏覽器直接導向登入頁
        return RedirectResponse(login_url, status_code=302)
    # API/fetch：回 401 並附上登入入口，讓前端可決定導向
    raise HTTPException(status_code=401, detail={"detail": detail, "login_url": login_url})
    
# --- AES256-CBC 加解密 ---
def unpad(s: str) -> str:
    pad_len = ord(s[-1])
    return s[:-pad_len]

def encrypt_aes(data: dict) -> str:
    """依雷門規範 AES-256-CBC + PKCS7 padding + Base64"""
    key = bytes.fromhex(KEY_HEX)
    iv = bytes.fromhex(IV_HEX)
    json_str = json.dumps(data, separators=(",", ":"))
    cipher = AES.new(key, AES.MODE_CBC, iv)
    encrypted_bytes = cipher.encrypt(pad(json_str.encode("utf-8"), 16))
    return base64.b64encode(encrypted_bytes).decode("utf-8")


def decrypt_aes(enc: str, key: bytes, iv: bytes) -> str:
    cipher = AES.new(key, AES.MODE_CBC, iv)
    pt = cipher.decrypt(b64decode(enc))
    return unpad(pt.decode("utf-8"))

# ====== 請款請求模型 ======
class CreatePaymentIn(BaseModel):
    amount: str = Field(..., description="金額（以元為單位，純數字字串，例如 '10' 或 '199'）")
    order_number: str = Field(..., min_length=1, max_length=64, description="商家訂單編號")
    # 若要自訂導回路徑，可開額外欄位；目前用固定 /return
    # return_path: str | None = "/return"

class CreatePaymentOut(BaseModel):
    pay_url: str

# === 前端路線資訊 ===
@app.get("/healthz", tags=["meta"], summary="健康檢查")
def healthz():
    """用於監控或負載平衡器的健康檢查端點"""
    return {"status": "error 404"}

@api.get("/All_Route", tags=["Client"], summary="所有路線")
def All_Route():
    rows = MySQL_Doing.run("SELECT * FROM bus_routes_total")

    df_cols = MySQL_Doing.run("SHOW COLUMNS FROM bus_routes_total")
    columns = df_cols["Field"].tolist()

    df = pd.DataFrame(rows, columns=columns)

    if "created_at" in df.columns:
        df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce") \
            .apply(lambda x: x.to_pydatetime() if pd.notnull(x) else None)

    records = df.where(pd.notnull(df), None).to_dict(orient="records")
    return records

@api.post("/Route_Stations", response_model=List[Define.StationOut], tags=["Client"], summary="所有站點")
def get_route_stations(q: Define.RouteStationsQuery):
    sql = "SELECT * FROM bus_route_stations WHERE route_id = %s"
    params = [q.route_id]
    if q.direction:
        sql += " AND direction = %s"
        params.append(q.direction)

    try:
        rows = MySQL_Doing.run(sql, params)
    except TypeError:
        if q.direction:
            rows = MySQL_Doing.run(f"SELECT * FROM bus_route_stations WHERE route_id = {int(q.route_id)} AND direction = '{q.direction}'")
        else:
            rows = MySQL_Doing.run(f"SELECT * FROM bus_route_stations WHERE route_id = {int(q.route_id)}")

    df_cols = MySQL_Doing.run("SHOW COLUMNS FROM bus_route_stations")
    columns = df_cols["Field"].tolist()
    df = pd.DataFrame(rows, columns=columns)

    if df.empty:
        return []
    col_map = {
        "station_name": "stop_name",
        "stop_name": "stop_name",
        "est_time": "eta_from_start",
        "eta_from_start": "eta_from_start",
        "order_no": "stop_order",
        "seq": "stop_order",
    }
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

    if "latitude" in df.columns:
        df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    if "longitude" in df.columns:
        df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    if "eta_from_start" in df.columns:
        df["eta_from_start"] = pd.to_numeric(df["eta_from_start"], errors="coerce").astype("Int64")
    if "stop_order" in df.columns:
        df["stop_order"] = pd.to_numeric(df["stop_order"], errors="coerce").astype("Int64")
    if "created_at" in df.columns:
        df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce") \
            .apply(lambda x: x.to_pydatetime() if pd.notnull(x) else None)
    desired_cols = [
        "route_id", "route_name", "direction", "stop_name",
        "latitude", "longitude", "eta_from_start", "stop_order", "created_at"
    ]
    keep_cols = [c for c in desired_cols if c in df.columns]
    df = df[keep_cols]
    records = df.where(pd.notnull(df), None).to_dict(orient="records")
    data: List[Define.StationOut] = [Define.StationOut(**r) for r in records]
    return data

@api.get("/yo_hualien", tags=["Client"], summary="行動遊花蓮")
def yo_hualien():
    rows = MySQL_Doing.run("SELECT station_name, address, latitude, longitude FROM action_tour_hualien")
    columns = ["station_name", "address", "latitude", "longitude"]
    df = pd.DataFrame(rows, columns=columns)
    return df.to_dict(orient="records") 

@api.get("/GIS_About", tags=["Client"], summary="取得最新車輛資訊")
def Get_GIS_About():
    """
    以 route_schedule 主導，回傳前端所需欄位：
    - route: 路線 ID
    - X, Y: 車輛經緯度（X=lng, Y=lat）
    - direction: 去程/返程
    - Current_Loaction: 最近站名
    - license_plate: 車牌號碼
    """

    # ---------- 1️⃣ 今日排班（正常營運） ----------
    sch = MySQL_Doing.run("""
        SELECT
          CAST(route_no AS SIGNED) AS route_id,
          direction,
          license_plate
        FROM route_schedule
        WHERE date = CURDATE()
          AND operation_status = '正常營運'
    """)

    if getattr(sch, "empty", False):
        return {"status": "success", "data": []}

    # ---------- 2️⃣ 取得所有車輛最新定位 ----------
    plates = sch["license_plate"].dropna().astype(str).unique().tolist()
    if not plates:
        return {"status": "success", "data": []}

    esc = [p.replace("'", "''") for p in plates]
    in_list = "','".join(esc)

    pos = MySQL_Doing.run(f"""
        SELECT
          car_licence AS license_plate,
          X, Y, Speed, Deg, acc, rcv_dt
        FROM ttcarimport
        WHERE car_licence IN ('{in_list}')
        AND rcv_dt = (
            SELECT MAX(rcv_dt)
            FROM ttcarimport t2
            WHERE t2.car_licence = ttcarimport.car_licence
        )
    """)

    if getattr(pos, "empty", False):
        return {"status": "success", "data": []}

    # ---------- 3️⃣ 站點資料 ----------
    route_ids = sch["route_id"].dropna().astype(int).unique().tolist()
    id_list = ",".join(str(i) for i in route_ids)
    stops = MySQL_Doing.run(f"""
        SELECT
          CAST(route_id AS SIGNED) AS route_id,
          direction,
          stop_name,
          CAST(latitude AS DECIMAL(12,8)) AS latitude,
          CAST(longitude AS DECIMAL(12,8)) AS longitude,
          CAST(stop_order AS SIGNED) AS stop_order
        FROM bus_route_stations
        WHERE route_id IN ({id_list})
        ORDER BY route_id, direction, stop_order
    """)

    if getattr(stops, "empty", False):
        return {"status": "success", "data": []}

    # ---------- 4️⃣ 合併車輛與站點，計算最近站 ----------
    import math
    def haversine(lat1, lon1, lat2, lon2):
        R = 6371000  # 地球半徑（公尺）
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    rows = []
    for _, row in sch.iterrows():
        route_id = int(row["route_id"])
        direction = str(row["direction"]).strip()
        plate = str(row["license_plate"])

        # 統一方向文字
        if direction in ["返程", "回", "1"]:
            direction = "回程"
        elif direction in ["去程", "往", "0"]:
            direction = "去程"

        # 找出該車的座標
        car = pos[pos["license_plate"] == plate]
        if car.empty:
            rows.append(dict(
                route=str(route_id),
                X=None, Y=None,
                direction=direction,
                Current_Loaction=None,
                license_plate=plate
            ))
            continue

        car_lat = float(car["Y"].iloc[0])
        car_lon = float(car["X"].iloc[0])

        # 該路線的所有站
        df_stations = stops[stops["route_id"] == route_id]
        if df_stations.empty:
            rows.append(dict(
                route=str(route_id),
                X=car_lon, Y=car_lat,
                direction=direction,
                Current_Loaction=None,
                license_plate=plate
            ))
            continue

        # 計算距離，找最近站
        df_stations["distance_m"] = df_stations.apply(
            lambda s: haversine(car_lat, car_lon, float(s["latitude"]), float(s["longitude"])),
            axis=1
        )
        nearest = df_stations.loc[df_stations["distance_m"].idxmin()]

        rows.append(dict(
            route=str(route_id),
            X=car_lon,
            Y=car_lat,
            direction=direction,
            Current_Loaction=str(nearest["stop_name"]),
            license_plate=plate
        ))

    # ---------- 5️⃣ 回傳結果 ----------
    df = pd.DataFrame(rows, columns=["route", "X", "Y", "direction", "Current_Loaction", "license_plate"])
    print(df[["route", "X", "Y", "direction", "Current_Loaction", "license_plate"]].to_dict())
    return df[["route", "X", "Y", "direction", "Current_Loaction", "license_plate"]].to_dict()

@api.get("/GIS_ByRoute", tags=["Client"], summary="Get current bus and nearest stop by route_id")
def get_gis_by_route(route_id: int):
    """
    Given route_id, return current car position and nearest stop info.
    Returns fields: route_id, direction, license_plate, car_lon, car_lat, rcv_dt,
    nearest_stop_name, nearest_distance_m, nearest_stop_order, total_stops, station_id.
    """
    # 1) Find plate and direction from schedule (latest by date)
    rs = MySQL_Doing.run(
        f"""
        SELECT route_no AS route_id, direction, license_plate
        FROM route_schedule
        WHERE route_no = {int(route_id)}
        ORDER BY date DESC
        LIMIT 1
        """
    )

    if not rs or (hasattr(rs, "empty") and rs.empty):
        raise HTTPException(status_code=404, detail="route not found in schedule")

    try:
        row = rs.iloc[0] if hasattr(rs, "iloc") else rs[0]
        direction = str(row["direction"]) if isinstance(row, dict) else str(row.direction)
        plate = (row["license_plate"] if isinstance(row, dict) else row.license_plate)
    except Exception:
        if hasattr(rs, "to_dict"):
            d = rs.to_dict("records")[0]
            direction = str(d.get("direction", ""))
            plate = d.get("license_plate")
        else:
            d = rs[0] if isinstance(rs, list) and rs else {}
            direction = str((d or {}).get("direction", ""))
            plate = (d or {}).get("license_plate")

    if not plate:
        raise HTTPException(status_code=404, detail="license plate not found for route")

    # 2) Latest car position (ttcarimport)
    pos = MySQL_Doing.run(
        f"""
        SELECT car_licence AS plate, X, Y, Speed, Deg, acc, rcv_dt
        FROM ttcarimport
        WHERE car_licence = '{plate.replace("'", "''")}'
        ORDER BY seq DESC
        LIMIT 1
        """
    )

    if not pos or (hasattr(pos, "empty") and pos.empty):
        raise HTTPException(status_code=404, detail="car position not found")

    if hasattr(pos, "to_dict"):
        p = pos.to_dict("records")[0]
    else:
        p = pos[0]

    # Note: follow convention Y=lat, X=lng used in Get_GIS_About
    try:
        car_lng = float(p.get("X"))
        car_lat = float(p.get("Y"))
    except Exception:
        car_lng = None
        car_lat = None

    # 3) Stops for this route and direction
    stops = MySQL_Doing.run(
        f"""
        SELECT
          CAST(route_id AS SIGNED) AS route_id,
          direction,
          stop_name,
          CAST(latitude AS DECIMAL(12,8)) AS latitude,
          CAST(longitude AS DECIMAL(12,8)) AS longitude,
          CAST(stop_order AS SIGNED) AS stop_order,
          station_id
        FROM bus_route_stations
        WHERE route_id = {int(route_id)}
          AND direction = '{direction.replace("'", "''")}'
        ORDER BY stop_order
        """
    )

    if not stops or (hasattr(stops, "empty") and stops.empty):
        raise HTTPException(status_code=404, detail="stops not found for route/direction")

    def _haversine_np(lat1, lon1, lat2, lon2):
        R = 6371000.0
        lat1 = _np.radians(lat1); lon1 = _np.radians(lon1)
        lat2 = _np.radians(lat2); lon2 = _np.radians(lon2)
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = _np.sin(dlat/2.0)**2 + _np.cos(lat1) * _np.cos(lat2) * _np.sin(dlon/2.0)**2
        return 2 * R * _np.arcsin(_np.sqrt(a))

    if hasattr(stops, "to_dict"):
        sdf = stops
    else:
        sdf_cols = ["route_id", "direction", "stop_name", "latitude", "longitude", "stop_order", "station_id"]
        sdf = pd.DataFrame(stops, columns=sdf_cols)

    dist = _haversine_np(
        float(car_lat), float(car_lng),
        sdf["latitude"].astype(float).to_numpy(),
        sdf["longitude"].astype(float).to_numpy()
    )
    idx = int(_np.argmin(dist))
    nearest = sdf.iloc[idx]

    return {
        "route_id": int(route_id),
        "direction": direction,
        "license_plate": plate,
        "car_lon": car_lng,
        "car_lat": car_lat,
        "rcv_dt": p.get("rcv_dt"),
        "nearest_stop_name": str(nearest.get("stop_name") or ""),
        "nearest_distance_m": float(dist[idx]),
        "nearest_stop_order": int(nearest.get("stop_order") or 0),
        "total_stops": int(len(sdf)),
        "station_id": (int(nearest.get("station_id")) if pd.notna(nearest.get("station_id")) else None),
    }

@api.post("/reservation", tags=["Client"], summary="送出預約")
def push_reservation(req: Define.ReservationReq):
    sql = f"""
    INSERT INTO reservation (
        user_id, booking_time, booking_number, 
        booking_start_station_name, booking_end_station_name
    ) VALUES (
        '{req.user_id}', 
        '{req.booking_time}', 
        '{req.booking_number}', 
        '{req.booking_start_station_name}', 
        '{req.booking_end_station_name}'
    )
    """
    MySQL_Doing.run(sql)
    return {"status": "success", "sql": sql}

@api.get("/reservations/my", tags=["Client"], summary="預約查詢")
def show_reservations(user_id: str):
    sql = f"""
    SELECT reservation_id, user_id, booking_time, booking_number, 
           booking_start_station_name, booking_end_station_name,
           review_status, payment_status, dispatch_status
    FROM reservation
    WHERE user_id = '{user_id}'
      AND (review_status IS NULL OR review_status <> 'canceled')
    ORDER BY booking_time DESC
    """
    results = MySQL_Doing.run(sql)

    # 如果是 DataFrame，轉成 dict
    if hasattr(results, "to_dict"):
        records = results.where(pd.notnull(results), None).to_dict(orient="records")
    else:
        # 已經是 list/dict 的情況
        records = results

    # 確保 numpy.int64 → int
    for r in records:
        for k, v in r.items():
            if isinstance(v, (pd._libs.missing.NAType, type(None))):
                r[k] = None
            elif hasattr(v, "item"):  # numpy scalar
                r[k] = v.item()

    return {"status": "success", "data": records}

@api.get("/reservations/tomorrow", tags=["Client"], summary="預約查詢")
def tomorrow_reservations(user_id: str):
    sql = f"""
    SELECT reservation_id, user_id, booking_time, booking_number, 
           booking_start_station_name, booking_end_station_name,
           review_status, payment_status
    FROM reservation where 
    review_status = 'approved' AND
    DATE(booking_time) = DATE_ADD(CURDATE(), INTERVAL 1 DAY) AND
    user_id = '{user_id}'
    """
    print("查詢明日預約 user_id=", user_id)
    print("SQL=", sql)
    results = MySQL_Doing.run(sql)

    return {"status": "success", "sql": results}

@api.post("/reservations/Canceled", tags=["Client"], summary="取消預約")
def Cancled_reservation(req: Define.CancelReq):
    sql = f"""
    UPDATE reservation
    SET review_status = 'canceled',
        cancel_reason = '{req.cancel_reason}'
    WHERE reservation_id = {req.reservation_id};
    """
    Results = MySQL_Doing.run(sql)
    return {"status": "success", "sql": Results}

@api.get("/privacy", tags=["Client"], summary="privacy")
async def get_privacy():
    gist_url = "https://gist.githubusercontent.com/Cody20179/ef17eeb9e2880a3a677bb5c74232c003/raw/gistfile1.txt"
    resp = requests.get(gist_url)
    return {"content": resp.text}

@api.post("/car_backup_insert", tags=["Car"], summary="插入車輛備份資料")
def insert_car_backup(data: Define.CarBackupInsert):
    # 若未提供 rcv_dt，使用伺服器當前時間
    rcv_dt = data.rcv_dt or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    acc_value = "b'1'" if data.acc else "b'0'" if data.acc is not None else "NULL"

    sql = f"""
    INSERT INTO car_backup (
        rcv_dt, car_licence, Gpstime, X, Y, Speed, Deg, acc, route, direction, Current_Loaction
    ) VALUES (
        '{rcv_dt}', '{data.car_licence}', '{data.Gpstime}',
        {data.X}, {data.Y}, {data.Speed}, {data.Deg},
        {acc_value},
        {f"'{data.route}'" if data.route else "NULL"},
        {f"'{data.direction}'" if data.direction else "NULL"},
        {f"'{data.Current_Loaction}'" if data.Current_Loaction else "NULL"}
    );
    """

    try:
        MySQL_Doing.run(sql)
        return {"status": "success", "rcv_dt": rcv_dt, "sql": sql}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/qrcode/{reservation_id}", tags=["Client"], summary="取得預約上車 QRCode（PNG）")
def qrcode_reservation(reservation_id: int, save: bool = False):
    """
    產出一張 PNG QRCode 並回傳。
    內容： reservation_id|user_id|line_id
    """
    rid = int(str(reservation_id).strip())

    # 查 DB：JOIN users 拿 line_id
    sql = f"""
        SELECT r.reservation_id, r.user_id, u.line_id, r.payment_status, r.review_status
        FROM reservation AS r
        LEFT JOIN users AS u ON r.user_id = u.user_id
        WHERE r.reservation_id = {rid}
        LIMIT 1;
    """
    row = MySQL_Doing.run(sql)

    if row is None or len(row) == 0:
        raise HTTPException(status_code=404, detail=f"reservation {rid} not found")

    rec = row.iloc[0].to_dict() if hasattr(row, "iloc") else row[0]

    # 組合 QR 內容
    uid = rec.get("user_id")
    lid = rec.get("line_id", "")
    payload = f"{rid}|{uid}|{lid}"

    import qrcode
    from io import BytesIO
    img = qrcode.make(payload)
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    # 不落地 → 直接回傳
    return StreamingResponse(buf, media_type="image/png")

@app.post("/qrcode/verify", tags=["Client"], summary="驗證 QRCode 訂單")
def verify_qrcode(data: dict = Body(...)):
    """
    驗證掃描的 QRCode 字串是否有效。
    內容格式： reservation_id|user_id|line_id
    回傳：是否有效 + 訂單資訊
    """
    qr_text = str(data.get("qrcode", "")).strip()
    if not qr_text or "|" not in qr_text:
        raise HTTPException(status_code=400, detail="Invalid QRCode content")

    parts = qr_text.split("|")
    if len(parts) < 3:
        raise HTTPException(status_code=400, detail="QRCode format error")

    reservation_id, user_id, line_id = parts[0], parts[1], parts[2]

    # 查詢 DB，確認三者一致 & 已付款
    sql = f"""
        SELECT r.reservation_id, r.user_id, u.line_id, r.payment_status, r.review_status, r.dispatch_status
        FROM reservation AS r
        LEFT JOIN users AS u ON r.user_id = u.user_id
        WHERE r.reservation_id = {reservation_id}
          AND r.user_id = {user_id}
          AND u.line_id = '{line_id}'
        LIMIT 1;
    """
    row = MySQL_Doing.run(sql)
    if row is None or len(row) == 0:
        raise HTTPException(status_code=404, detail="QRCode verification failed")

    rec = row.iloc[0].to_dict() if hasattr(row, "iloc") else row[0]
    paid = str(rec.get("payment_status", "")).lower() == "paid"
    assigned = str(rec.get("dispatch_status", "")).lower() == "assigned"

    return {
        "valid": paid and assigned,
        "reservation_id": rec["reservation_id"],
        "user_id": rec["user_id"],
        "line_id": rec.get("line_id"),
        "payment_status": rec["payment_status"],
        "dispatch_status": rec["dispatch_status"],
        "review_status": rec["review_status"],
        "message": "驗證通過" if paid and assigned else "尚未付款或未派車"
    }

@api.get("/announcements", tags=["Client"], summary="取得服務公告列表")
def get_announcements():
    sql = "SELECT id, title, content, created_at FROM announcements ORDER BY created_at DESC"
    rows = MySQL_Doing.run(sql)
    if hasattr(rows, "to_dict"):
        return {"status": "success", "data": rows.to_dict(orient="records")}
    return {"status": "success", "data": rows}

@api.post("/announcements/add", tags=["Admin"], summary="新增服務公告")
def add_announcement(title: str = Body(...), content: str = Body(...)):
    sql = f"""
    INSERT INTO announcements (title, content)
    VALUES ('{title}', '{content}');
    """
    MySQL_Doing.run(sql)
    return {"status": "success"}

@api.delete("/announcements/delete/{ann_id}", tags=["Admin"], summary="刪除公告")
def delete_announcement(ann_id: int):
    sql = f"DELETE FROM announcements WHERE id = {ann_id}"
    MySQL_Doing.run(sql)
    return {"status": "success"}

@api.get("/Generate_QRCode", tags=["Utility"], summary="產生路線站點 QRCode 並下載")
def generate_qr_code(
    base_url: str,
    route_id: int,
    stop_count: int,
):
    """
    依據路線 ID 與站點數產生 QR Code 圖片壓縮包，並提供下載。
    - base_url: 前端或公開網址 (例如 https://xxx.ngrok-free.app)
    - route_id: 路線 ID
    - stop_count: 站點數量
    """
    try:
        # 建立暫存目錄
        temp_dir = tempfile.mkdtemp(prefix="qrcodes_")
        for stop_order in range(1, stop_count + 1):
            url = f"{base_url}/routes/{route_id}/stop/{stop_order}"
            img = qrcode.make(url)
            img.save(os.path.join(temp_dir, f"route{route_id}_stop{stop_order}.png"))

        # 壓縮成 zip 方便下載
        zip_path = os.path.join(temp_dir, f"route{route_id}_qrcodes.zip")
        import zipfile
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for fname in os.listdir(temp_dir):
                if fname.endswith(".png"):
                    zf.write(os.path.join(temp_dir, fname), arcname=fname)

        return FileResponse(
            zip_path,
            media_type="application/zip",
            filename=f"route{route_id}_qrcodes.zip",
        )

    except Exception as e:
        return {"status": "error", "message": str(e)}
    
# === 使用者更新資訊 ===
@api.post("/users/update_mail", tags=["Users"], summary="更新使用者Email")
def update_mail(user_id: int, email: str):
    sql = f"""
    UPDATE users
    SET email = '{email}',
        updated_at = NOW()
    WHERE user_id = {user_id};
    """
    results = MySQL_Doing.run(sql)
    return {"status": "success", "sql": sql, "results": results}

@api.post("/users/update_phone", tags=["Users"], summary="更新使用者Email")
def update_phone(user_id: int, phone: str):
    sql = f"""
    UPDATE users
    SET phone = '{phone}',
        updated_at = NOW()
    WHERE user_id = {user_id};
    """
    results = MySQL_Doing.run(sql)
    return {"status": "success", "sql": sql, "results": results}

# === LINE 登入與使用者權限相關API資訊 ===
@app.get("/auth/line/login", tags=["Auth"], summary="Line 登入")
def login(request: Request):
    force = request.query_params.get("force")
    uid = SessionManager.verify_session_token(request.cookies.get("app_session"))
    q_return_to = request.query_params.get("return_to")

    if q_return_to and _is_safe_return_to(q_return_to):
        resolved_return_to = q_return_to
    else:
        resolved_return_to = _default_frontend_url(request)

    # 防呆：如果 Redis 有但 MySQL 查不到 → 視為無效 session
    if not force and uid and r.exists(f"user:{uid}"):
        db_check = MySQL_Doing.run(f"SELECT 1 FROM users WHERE line_id='{uid}' LIMIT 1;")
        if db_check:
            return RedirectResponse(resolved_return_to)
        else:
            print(f"[WARN] Redis 有 session，但 MySQL 查不到 user={uid}，強制重登")
            r.delete(f"user:{uid}")  # 清理 Redis
            # 不 return，繼續往下走 LINE OAuth

    # 強制走 LINE OAuth
    state = secrets.token_urlsafe(16)
    verifier = secrets.token_urlsafe(64)
    challenge = SessionManager.b64url(hashlib.sha256(verifier.encode()).digest())
    r.setex(f"login_state:{state}", 300, json.dumps({"verifier": verifier, "return_to": resolved_return_to}))
    url = LineAuth.get_login_url(state, challenge)
    return RedirectResponse(url)

@app.get("/logout", tags=["Auth"], summary="登出")
def logout(request: Request):
    redirect_url = _default_frontend_url(request)
    resp = RedirectResponse(redirect_url)
    resp.delete_cookie("app_session")
    return resp

@app.get("/auth/line/callback", tags=["Auth"], summary="Line 登入回呼")
async def callback(request: Request, code: str | None = None, state: str | None = None):
    data = r.get(f"login_state:{state}")
    if not code or not state or not data:
        raise HTTPException(400, "Invalid state or code")

    st = json.loads(data)
    r.delete(f"login_state:{state}")
    verifier = st["verifier"]
    return_to = st.get("return_to")

    # ===== 1. 向 LINE API 換 token & profile =====
    token, profile = await LineAuth.exchange_token(code, verifier)
    uid = profile["userId"]

    # ===== 2. 產生 session token =====
    app_token = SessionManager.make_session_token(uid)

    # ===== 3. 存到 Redis (短期快取) =====
    r.setex(f"user:{uid}", token["expires_in"], json.dumps({
        "profile": profile,
        "access_token": token["access_token"],
        "refresh_token": token["refresh_token"],
        "exp": int(time.time()) + token["expires_in"],
        "session_token": app_token
    }))
    r.setex(f"session:{app_token}", 7*24*3600, uid)

    # ===== 4. 寫入 MySQL (長期存放) =====
    LineID = profile["userId"]
    UserName = profile["displayName"]
    print(f"[DEBUG] LINE Profile: {profile}")
    print(f"[DEBUG] LineID={LineID}, UserName={UserName}, AppToken={app_token}")
    try:
        MySQL_Doing.run(f"""
        INSERT INTO users (line_id, username, password, session_token, last_login)
        VALUES ('{LineID}', '{UserName}', '', '{app_token}', NOW())
        ON DUPLICATE KEY UPDATE session_token='{app_token}', last_login=NOW();
        """)
    except Exception as e:
        print(f"MySQL insert error: {e}")

    # ===== 5. 設定 Cookie 並跳轉到前端 =====
    # 固定跳轉到前端 Profile 頁
    redirect_url = _default_frontend_url(request)
    if return_to and _is_safe_return_to(return_to):
        redirect_url = return_to

    resp = RedirectResponse(redirect_url)
    is_https = str(BASE_URL or '').lower().startswith('https://')
    samesite = "none" if is_https else "lax"
    secure = True if is_https else False
    resp.set_cookie("app_session", app_token, httponly=True, max_age=7*24*3600, samesite=samesite, secure=secure)
    return resp

@app.get("/me", tags=["Auth"], summary="取得使用者資訊")
async def me(request: Request):
    app_token = request.cookies.get("app_session")
    if not app_token:
        return _unauthorized_response(request, "not logged in")

    result = MySQL_Doing.run(f"""
        SELECT user_id, line_id, username, email, phone, last_login
        FROM users
        WHERE session_token = '{app_token}'
        LIMIT 1;
    """)

    if result.empty:
        # 防呆：自動清理 Redis 裡壞掉的 session
        uid = SessionManager.verify_session_token(app_token)
        if uid:
            r.delete(f"user:{uid}")
            r.delete(f"session:{app_token}")
            print(f"[CLEANUP] 清掉無效 session: user={uid}")
        return _unauthorized_response(request, "session not found")

    row = result.iloc[0].to_dict()
    return {
        "user_id": row["user_id"],
        "line_id": row["line_id"],
        "username": row["username"],
        "email": row["email"],
        "phone": row["phone"],
        "last_login": row["last_login"],
    }

# ====================================
# 🧾 建立付款連結
# ====================================
@app.post("/payments", response_model=CreatePaymentOut)
def create_payment(body: CreatePaymentIn):
    amt = Decimal(body.amount)
    if amt <= 0 or amt != amt.quantize(Decimal("1")):
        raise HTTPException(status_code=400, detail="amount 必須為正整數")

    payload = {
        "set_price": str(amt),
        "pos_id": "01",
        "pos_order_number": body.order_number,
        "callback_url": f"{PUBLIC_BASE}/callback",
        "return_url": f"{PUBLIC_BASE}/return",
        "nonce": secrets.token_hex(8),  # 加這行
    }

    # === AES 加密 ===
    transaction_data = encrypt_aes(payload)

    # === SHA256 雜湊（注意：針對未 URL encode 的原始 Base64 字串）===
    hash_digest = hashlib.sha256(transaction_data.encode("utf-8")).hexdigest()

    print("原始 JSON:", payload)
    print("加密後 TransactionData:", transaction_data)
    print("本地算出的 HashDigest:", hash_digest)

    # === URL encode 後組成最終網址 ===
    full_url = (
        f"https://{LAYMON}/calc/pay_encrypt/{STORE_CODE}"
        f"?TransactionData={quote(transaction_data)}&HashDigest={hash_digest}"
    )

    return CreatePaymentOut(pay_url=full_url)

# ====================================
# 🔁 雷門 callback（伺服器對伺服器）
# ====================================
@app.post("/callback")
async def callback(request: Request):
    body = await request.json()
    enc_data = body.get("TransactionData")
    hash_digest = body.get("HashDigest")

    if not enc_data or not hash_digest:
        raise HTTPException(status_code=400, detail="缺少必要欄位")

    # 驗證 hash
    local_hash = hashlib.sha256(enc_data.encode("utf-8")).hexdigest()
    if local_hash != hash_digest:
        raise HTTPException(status_code=400, detail="Hash 驗證失敗")

    try:
        data = decrypt_aes(enc_data)
        order_number = data.get("pos_order_number")
        if order_number:
            sql = f"UPDATE reservation SET payment_status = 'paid' WHERE reservation_id = '{order_number}'"
            MySQL_Doing.run(sql)

        # return {"status": "ok", "data": data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"解密失敗: {e}")

# ====================================
# 🌐 使用者導回頁
# ====================================
@app.get("/return")
def return_page():
    return RedirectResponse(url=f"{PUBLIC_BASE}?tab=reservations")

# === 前端靜態檔案服務 ===
app.include_router(api)
app.mount('/', StaticFiles(directory='dist', html=True), name='client')

# === FastAPI 把 API 跟前端打包 ===
@app.exception_handler(StarletteHTTPException)
async def spa_fallback(request: Request, exc: StarletteHTTPException):
    try:
        if exc.status_code == 404 and request.method in ("GET", "HEAD"):
            path = request.url.path or "/"
            accept = (request.headers.get("accept") or "").lower()
            # only for browser navigations to non-API paths
            if (
                not path.startswith("/api")
                and not path.startswith("/auth")
                and ("text/html" in accept or accept == "*/*")
            ):
                index_path = os.path.join("dist", "index.html")
                if os.path.exists(index_path):
                    return FileResponse(index_path)
    except Exception:
        pass
    raise exc
