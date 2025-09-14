from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, HTMLResponse
from typing import List
from datetime import datetime
from urllib.parse import urlparse
from dotenv import load_dotenv
from MySQL import MySQL_Run
import pandas as pd
import secrets, hashlib, urllib.parse, base64, json, time, hmac, os, redis, httpx
import Define

load_dotenv()
app = FastAPI(
    title="H_Bus API",
    version="V0.1.0",
    description="H_Bus 服務的最小 API 範本，含健康檢查與根路由。",
)

# 加入 CORS 設定
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+):(5173|3000|8080)$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# === Redis 初始化 ===
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
BASE_URL = "https://3f918fa9866f.ngrok-free.app"
Front_End_Route = "http://192.168.0.126:5173/profile"
r = redis.from_url(REDIS_URL, decode_responses=True)

# === LINE 設定 ===
CHANNEL_ID = os.getenv("LINE_CHANNEL_ID")
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
BASE_URL = "https://3f918fa9866f.ngrok-free.app"
CALLBACK_PATH = "/auth/line/callback"
AUTHORIZE_URL = "https://access.line.me/oauth2/v2.1/authorize"
TOKEN_URL = "https://api.line.me/oauth2/v2.1/token"
PROFILE_URL = "https://api.line.me/v2/profile"
APP_SESSION_SECRET = os.getenv("APP_SESSION_SECRET", "my-secret")

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
        allowed_origins = [
            "http://127.0.0.1:5173",
            "http://localhost:5173",
        ]
        origin = f"{parsed.scheme}://{parsed.hostname}:{parsed.port}" if parsed.port else f"{parsed.scheme}://{parsed.hostname}"
        return origin in allowed_origins
    except Exception:
        return False
    
"""
For App Client
"""
@app.get("/", tags=["meta"], summary="根路由")
def read_root():
    """根路由，返回簡單的歡迎信息"""
    return {"hello": "world"}

@app.get("/healthz", tags=["meta"], summary="健康檢查")
def healthz():
    """用於監控或負載平衡器的健康檢查端點"""
    return {"status": "error 404"}

@app.get("/All_Route", tags=["Client"], summary="所有路線")
def All_Route():
    rows = MySQL_Run("SELECT * FROM bus_routes_total")
    columns = [c['Field'] for c in MySQL_Run("SHOW COLUMNS FROM bus_routes_total")]
    df = pd.DataFrame(rows, columns=columns)
    if "created_at" in df.columns:
        df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce") \
            .apply(lambda x: x.to_pydatetime() if pd.notnull(x) else None)
    records = df.where(pd.notnull(df), None).to_dict(orient="records")
    return records

@app.post("/Route_Stations", response_model=List[Define.StationOut], tags=["Client"], summary="所有站點")
def get_route_stations(q: Define.RouteStationsQuery):
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

    columns = [c['Field'] for c in MySQL_Run("SHOW COLUMNS FROM bus_route_stations")]
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
    data: List[Define.StationOut] = [Define.StationOut(**r) for r in records]
    return data

@app.get("/yo_hualien", tags=["Client"], summary="行動遊花蓮")
def yo_hualien():
    rows = MySQL_Run("SELECT station_name, address, latitude, longitude FROM action_tour_hualien")
    columns = ["station_name", "address", "latitude", "longitude"]
    df = pd.DataFrame(rows, columns=columns)
    return df.to_dict(orient="records") 

@app.post("/reservation", tags=["Client"], summary="送出預約")
def push_reservation(
    user_id: str,
    booking_time: datetime,
    booking_number: str,
    booking_start_station_name: str,
    booking_end_station_name: str,
):
    sql = f"""
    INSERT INTO reservation (
        user_id, booking_time, booking_number, 
        booking_start_station_name, booking_end_station_name
    ) VALUES (
        '{user_id}', 
        '{booking_time}', 
        '{booking_number}', 
        '{booking_start_station_name}', 
        '{booking_end_station_name}'
    )
    """
    MySQL_Run(sql)
    return {"status": "success", "sql": sql}

@app.get("/reservations/my", tags=["Client"], summary="預約查詢")
def show_reservations(user_id: str):
    sql = f"""
    SELECT user_id, booking_time, booking_number, 
           booking_start_station_name, booking_end_station_name,
           review_status, payment_status
    FROM reservation where user_id = '{user_id}'
    """
    results = MySQL_Run(sql)

    return {"status": "success", "sql": results}

"""
For Line Login API
"""
@app.get("/auth/line/login")
def login(request: Request):
    uid = SessionManager.verify_session_token(request.cookies.get("app_session"))
    return_to = request.query_params.get("return_to")
    if uid and r.exists(f"user:{uid}"):
        if return_to and _is_safe_return_to(return_to):
            return RedirectResponse(return_to)
        return RedirectResponse("/dashboard")
    state = secrets.token_urlsafe(16)
    verifier = secrets.token_urlsafe(64)
    challenge = SessionManager.b64url(hashlib.sha256(verifier.encode()).digest())
    r.setex(f"login_state:{state}", 300, json.dumps({"verifier": verifier, "return_to": return_to}))
    url = LineAuth.get_login_url(state, challenge)
    return RedirectResponse(url)

@app.get("/logout")
def logout():
    resp = RedirectResponse(Front_End_Route)
    resp.delete_cookie("app_session")
    return resp

@app.get("/auth/line/callback")
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
        MySQL_Run(f"""
        INSERT INTO users (line_id, username, password, session_token, last_login)
        VALUES ('{LineID}', '{UserName}', '', '{app_token}', NOW())
        ON DUPLICATE KEY UPDATE session_token='{app_token}', last_login=NOW();
        """)
    except Exception as e:
        print(f"MySQL insert error: {e}")

    # ===== 5. 設定 Cookie 並跳轉到前端 =====
    # 固定跳轉到前端 Profile 頁
    redirect_url = "http://127.0.0.1:5173/profile"
    if return_to and _is_safe_return_to(return_to):
        redirect_url = return_to

    resp = RedirectResponse(redirect_url)
    is_https = str(BASE_URL or '').lower().startswith('https://')
    samesite = "none" if is_https else "lax"
    secure = True if is_https else False
    resp.set_cookie("app_session", app_token, httponly=True, max_age=7*24*3600, samesite=samesite, secure=secure)
    return resp

@app.get("/me")
async def me(request: Request):
    app_token = request.cookies.get("app_session")
    if not app_token:
        raise HTTPException(401, "not logged in")

    # 查 MySQL (session_token → 使用者)
    result = MySQL_Run(f"SELECT user_id, line_id, username, email, phone, last_login FROM users WHERE session_token = '{app_token}' LIMIT 1;")
    if not result:
        raise HTTPException(401, "session not found")

    user = result[0]
    return {
        "user_id": user["user_id"],
        "line_id": user["line_id"],
        "username": user["username"],
        "email": user.get("email", ""),
        "phone": user.get("phone", ""),
        "last_login": user["last_login"],
    }

# if __name__ == "__main__":
#     uvicorn Server:app --host 0.0.0.0 --port 8500 --reload
#       uvicorn Login:app --host 0.0.0.0 --port 8000 --reload
#     uvicorn.run("Server:app", host="0.0.0.0", port=8500, reload=True)
