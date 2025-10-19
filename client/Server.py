# ====================================
# 🧩 專案內部模組
# ====================================
from Backend import Define
from Backend.MySQL import MySQL_Doing
# === 產生乘車 QR 與驗證乘車資格 ===
from Backend.CreateUserQR import generate_boarding_token, save_qr_png
from Backend.CheckQR import verify_boarding_token
# ====================================
# 📦 第三方套件
# ====================================
from fastapi import FastAPI, Request, HTTPException, APIRouter, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from io import BytesIO
import pandas as pd
import redis
import httpx
import qrcode
# ====================================
# ✅ 標準庫
# ====================================
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from zoneinfo import ZoneInfo
from datetime import datetime
from urllib.parse import urlparse, quote
from base64 import b64decode
from decimal import Decimal
from typing import List, Tuple, Optional
from threading import RLock
import os, json, time, math, base64, requests
import urllib, hmac, hashlib, secrets, tempfile, smtplib

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

# Simple in-process cache to reduce DB load when users toggle directions rapidly
_ROUTE_STOPS_CACHE: dict[Tuple[int, str], Tuple[float, list]] = {}
_ROUTE_STOPS_TTL_SEC = 120  # 2 minutes
_ROUTE_STOPS_LOCK = RLock()


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

# === email 相關設定 ===
SENDER_EMAIL = os.getenv("Sender_email")
SENDER_PASS  = os.getenv("Password_email")

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

# --- 計算兩點距離 (Haversine公式) ---
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000  # 地球半徑（公尺）
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

# --- 統一方向 ---
def normalize_direction(x):
    t = str(x or "").strip()
    if "返" in t or "回" in t or t == "1":
        return "回程"
    return "去程"

# ========== 全域設定 ==========
TZ_NAME = os.getenv("TZ", "Asia/Taipei")
MAIL_SEND_HOUR = int(os.getenv("MAIL_SEND_HOUR", "8"))
MAIL_SEND_MIN = int(os.getenv("MAIL_SEND_MIN", "0"))
TZ = ZoneInfo(TZ_NAME)

# ========== 信件樣板 ==========
MAIL_SUBJECT = "【乘車提醒】您今日的預約資訊"
MAIL_TEXT_TEMPLATE = """親愛的乘客您好，

以下為您今日 ({today}) 的預約資訊：
{lines}

若資訊有誤或需更改，請盡速與我們聯繫。祝您旅途順利！

— 花蓮小巴預約系統
"""
# ========== 郵件發送 ==========
def send_email(receiver_email: str, subject: str, text: str):
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = SENDER_EMAIL
    message["To"] = receiver_email
    message.attach(MIMEText(text, "plain", "utf-8"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(SENDER_EMAIL, SENDER_PASS)
        server.sendmail(SENDER_EMAIL, receiver_email, message.as_string())
# ========== 查詢今天預約 & 準備寄信名單 ==========
def fetch_today_reservations() -> pd.DataFrame:
    sql = """
    SELECT 
        u.email,
        r.user_id,
        r.reservation_id,
        r.booking_time,
        r.booking_number,
        r.booking_start_station_name,
        r.booking_end_station_name
    FROM reservation r
    JOIN users u ON u.user_id = r.user_id
    WHERE r.review_status = 'approved'
      AND DATE(r.booking_time) = CURDATE()
      AND u.email IS NOT NULL
      AND u.email <> '';
    """
    rows = MySQL_Doing.run(sql)
    return pd.DataFrame(rows)
# ========== 組信內容（依 email 彙整多筆預約） ==========
def build_and_send_emails():
    now = datetime.now(TZ)
    print(f"[{now:%Y-%m-%d %H:%M:%S}] Checking today's reservations...")

    try:
        df = fetch_today_reservations()
    except Exception as e:
        print(f"DB error: {e}")
        return

    if df.empty:
        print(f"[{now:%Y-%m-%d %H:%M:%S}] No approved reservations found today.")
        return

    grouped = df.groupby("email", dropna=True)
    success, fail = 0, 0

    for email, g in grouped:
        lines = [
            f"- 預約編號: {r['reservation_id']}｜時間: {r['booking_time']}｜"
            f"人數: {r['booking_number']}｜{r['booking_start_station_name']} → {r['booking_end_station_name']}"
            for _, r in g.iterrows()
        ]
        body = MAIL_TEXT_TEMPLATE.format(today=f"{now:%Y-%m-%d}", lines="\n".join(lines))

        try:
            send_email(email, MAIL_SUBJECT, body)
            print(f"✔ Sent: {email} ({len(g)} records)")
            success += 1
        except Exception as e:
            print(f"✘ Failed: {email} → {e}")
            fail += 1

    print(f"[{datetime.now(TZ):%Y-%m-%d %H:%M:%S}] Completed — Success: {success}, Fail: {fail}")

# ========== 排程器啟動 ==========
def start_scheduler():
    scheduler = BackgroundScheduler(timezone=TZ)
    scheduler.add_job(
        build_and_send_emails,
        CronTrigger(hour=MAIL_SEND_HOUR, minute=MAIL_SEND_MIN, timezone=TZ),
        id="daily_send",
        replace_existing=True
    )
    scheduler.start()
    app.state.scheduler = scheduler
    print(f"[scheduler] started — will send emails daily at {MAIL_SEND_HOUR:02d}:{MAIL_SEND_MIN:02d} ({TZ_NAME})")


    sched = getattr(app.state, "scheduler", None)
    if sched:
        sched.shutdown()
        print("[scheduler] stopped")

@app.on_event("startup")
def on_startup():
    start_scheduler()

@app.on_event("shutdown")
def on_shutdown():
    sched = getattr(app.state, "scheduler", None)
    if sched:
        sched.shutdown()
        print("[scheduler] stopped")
        
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

@api.post("/Route_Stations",
    response_model=List[Define.StationOut],
    tags=["Client"],
    summary="所有站點"
)
def get_route_stations(q: Define.RouteStationsQuery):
    # === 建立查詢語句 ===
    sql = "SELECT * FROM bus_route_stations WHERE route_id = %s"
    params = [q.route_id]
    if q.direction:
        sql += " AND direction = %s"
        params.append(q.direction)

    # === 嘗試查詢資料 ===
    try:
        rows = MySQL_Doing.run(sql, params)
    except TypeError:
        # 某些自定義封裝不支援 %s 語法時 fallback
        if q.direction:
            rows = MySQL_Doing.run(
                f"SELECT * FROM bus_route_stations "
                f"WHERE route_id = {int(q.route_id)} AND direction = '{q.direction}'"
            )
        else:
            rows = MySQL_Doing.run(
                f"SELECT * FROM bus_route_stations WHERE route_id = {int(q.route_id)}"
            )

    # === 取出欄位結構 ===
    df_cols = MySQL_Doing.run("SHOW COLUMNS FROM bus_route_stations")
    if isinstance(df_cols, pd.DataFrame):
        columns = df_cols["Field"].tolist()
    elif isinstance(df_cols, list) and len(df_cols) > 0:
        if isinstance(df_cols[0], dict):
            columns = [c["Field"] for c in df_cols]
        else:
            columns = [c[0] for c in df_cols]
    else:
        columns = []

    # === 組成 DataFrame ===
    df = pd.DataFrame(rows, columns=columns)
    if df.empty:
        return []

    # === 欄位對應與格式轉換 ===
    col_map = {
        "station_name": "stop_name",
        "stop_name": "stop_name",
        "est_time": "eta_from_start",
        "eta_from_start": "eta_from_start",
        "order_no": "stop_order",
        "seq": "stop_order",
        "schedule": "schedule",
    }
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

    # 數值轉換
    for col in ["latitude", "longitude", "eta_from_start", "stop_order"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # 時間轉換
    if "created_at" in df.columns:
        df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce").apply(
            lambda x: x.to_pydatetime() if pd.notnull(x) else None
        )

    # === 保留需要的欄位 ===
    desired_cols = [
        "station_id",
        "route_id",
        "route_name",
        "direction",
        "stop_name",
        "latitude",
        "longitude",
        "eta_from_start",
        "stop_order",
        "schedule",
        "address",
        "status",
        "created_at",
    ]
    keep_cols = [c for c in desired_cols if c in df.columns]
    df = df[keep_cols]

    # === 轉換為 JSON 物件 ===
    records = df.where(pd.notnull(df), None).to_dict(orient="records")
    data: List[Define.StationOut] = [Define.StationOut(**r) for r in records]
    return data

@api.get("/Route_ScheduleTime", tags=["Client"], summary="取得路線時刻表（僅以頭尾站決定當前班次）")
def get_route_schedule_time(route_id: int, direction: str = None):
    """
    只用「頭站與尾站」的時刻表決定當前班次索引 k：
      - 若 now <= head[k] 的第一個班次 → k 即為該索引
      - 若落在 (tail[k-1], tail[k]] 之間 → k
      - 若超過最後一個 tail → k = 最後一班
    接著每一站都取自己 full_schedule 的第 k 筆（若沒有第 k 筆就取最後一筆）。
    這樣所有站的時間屬於同一輪，不會倒退。
    """
    # 讀站點與時刻
    sql = f"""
    SELECT stop_name, schedule, 
            COALESCE(stop_order, 9999) AS ord
    FROM bus_route_stations
    WHERE route_id = {route_id} {f"AND direction='{direction}'" if direction else ""}
    """

    rows = MySQL_Doing.run(sql)
    df = pd.DataFrame(rows)
    if df.empty:
        return {"status": "success", "route_id": route_id, "direction": direction, "data": []}

    # 依序排序（頭→尾）
    df = df.sort_values("ord").reset_index(drop=True)

    # 工具：把 "HH:MM,..." 轉成 time 物件陣列
    def parse_times(s: str):
        out = []
        if not s:
            return out
        for t in str(s).split(","):
            t = t.strip()
            try:
                out.append(datetime.strptime(t, "%H:%M").time())
            except ValueError:
                pass
        return out

    # 頭站、尾站
    head_name = df.iloc[0]["stop_name"]
    tail_name = df.iloc[-1]["stop_name"]
    head_times = parse_times(df.iloc[0]["schedule"])
    tail_times = parse_times(df.iloc[-1]["schedule"])

    # 沒時刻直接回傳
    if not head_times or not tail_times:
        data = [{
            "stop_name": r["stop_name"],
            "next_time": None,
            "full_schedule": (r["schedule"] or "").strip()
        } for _, r in df.iterrows()]
        return {"status": "success", "route_id": route_id, "direction": direction, "data": data}

    # 若長度不同，對齊為較短的長度（避免索引超界）
    L = min(len(head_times), len(tail_times))
    head_times = head_times[:L]
    tail_times = tail_times[:L]

    now = datetime.now().time()

    # ---- 決定當前班次索引 k（只看頭尾站）----
    # 規則：
    # 1) 若 now <= 第一個 head → k=該 head 的索引
    # 2) 否則找最小 k 使 now <= tail[k]
    # 3) 否則 k=L-1
    def locate_cycle_index(now_t):
        # 先看 head
        for i, ht in enumerate(head_times):
            if now_t <= ht:
                return i
        # 再看 tail
        for i, tt in enumerate(tail_times):
            if now_t <= tt:
                return i
        return L - 1

    k = locate_cycle_index(now)

    # ---- 逐站取第 k 筆時刻（若該站不足 k+1 筆，就取最後一筆）----
    results = []
    for _, r in df.iterrows():
        full = (r["schedule"] or "").strip()
        times = parse_times(full)
        if not times:
            results.append({"stop_name": r["stop_name"], "next_time": None, "full_schedule": full})
            continue
        idx = min(k, len(times) - 1)
        results.append({
            "stop_name": r["stop_name"],
            "next_time": times[idx].strftime("%H:%M"),
            "full_schedule": full
        })

    return {
        "status": "success",
        "route_id": route_id,
        "direction": direction,
        "data": results
    }

@api.get("/yo_hualien", tags=["Client"], summary="行動遊花蓮")
def yo_hualien():
    rows = MySQL_Doing.run("SELECT station_name, address, latitude, longitude FROM action_tour_hualien")
    columns = ["station_name", "address", "latitude", "longitude"]
    df = pd.DataFrame(rows, columns=columns)
    return df.to_dict(orient="records") 

@api.get("/GIS_About", tags=["Client"], summary="取得最新車輛資訊")
def Get_GIS_About():
    Results = MySQL_Doing.run("""
    Select route from car_resource
    where route != 'None'
    """)

    print(Results["route"].tolist())
    Results = MySQL_Doing.run("""
    SELECT c.route, c.X, c.Y, c.direction, c.Current_Loaction
    FROM car_backup c
    JOIN (
        SELECT route, MAX(seq) AS max_seq
        FROM car_backup
        WHERE route IN ('1', '2', '3')
        GROUP BY route
    ) t ON c.route = t.route AND c.seq = t.max_seq;
    """)
    return Results

@api.get("/GIS_AllFast", tags=["Client"], summary="今日正常營運路線即時摘要（30秒快取）")
def gis_all_fast():
    print("=== [DEBUG] /GIS_AllFast 開始 ===")

    # 1️⃣ 抓取今日正常營運車輛
    df_routes = pd.DataFrame(MySQL_Doing.run('''
        SELECT route_no, direction, license_plate 
        FROM route_schedule 
        WHERE operation_status = "正常營運"
    '''))
    if df_routes.empty:
        print("[WARN] 無正常營運路線")
        return {}

    df_routes["direction"] = df_routes["direction"].map(normalize_direction)
    print(f"[DEBUG] 讀取 route_schedule 共 {len(df_routes)} 筆")

    # 2️⃣ 讀取所有站點
    df_stops = pd.DataFrame(MySQL_Doing.run('''
        SELECT route_id, direction, latitude, longitude, stop_name 
        FROM bus_route_stations
    '''))
    df_stops["direction"] = df_stops["direction"].map(normalize_direction)
    print(f"[DEBUG] 讀取 bus_route_stations 共 {len(df_stops)} 筆")

    results = []

    # 3️⃣ 每台車找最近站點
    for _, r in df_routes.iterrows():
        route_id = int(r["route_no"])
        plate = str(r["license_plate"])
        direction = r["direction"]

        print(f"\n[DEBUG] 處理路線 {route_id}, 車牌 {plate}, 方向 {direction}")

        # --- 抓車機資料 ---
        sql = f'''
            SELECT 
                X AS longitude,
                Y AS latitude
            FROM ttcarimport 
            WHERE car_licence = "{plate}" 
            ORDER BY seq DESC 
            LIMIT 1
        '''
        df_car = pd.DataFrame(MySQL_Doing.run(sql))
        print(f"[DEBUG] 車牌 {plate} GPS 筆數: {len(df_car)}")

        if df_car.empty:
            print(f"[WARN] 車牌 {plate} 無最新位置，略過")
            continue

        # --- 經緯度轉換 + 檢查 ---
        try:
            car_lat = float(df_car.iloc[0]["latitude"])   # 緯度（應約23.x）
            car_lon = float(df_car.iloc[0]["longitude"])  # 經度（應約121.x）
        except Exception as e:
            print(f"[ERROR] 無法轉換經緯度 ({plate}): {e}")
            continue

        # 自動偵測經緯度是否顛倒
        if abs(car_lat) > 90 or abs(car_lon) > 180:
            print(f"[WARN] 座標顛倒 lat={car_lat}, lon={car_lon} → 交換")
            car_lat, car_lon = car_lon, car_lat

        # 粗略檢查是否在台灣範圍內
        if not (21.5 <= car_lat <= 25.5 and 119.0 <= car_lon <= 123.0):
            print(f"[WARN] 座標異常 lat={car_lat}, lon={car_lon}")

        print(f"[DEBUG] 正常化後座標: lat={car_lat}, lon={car_lon}")

        # --- 尋找相同路線、方向的站 ---
        df_route_stops = df_stops.loc[
            (df_stops["route_id"] == route_id) &
            (df_stops["direction"] == direction)
        ].copy()

        print(f"[DEBUG] 匹配站點數: {len(df_route_stops)}")
        if df_route_stops.empty:
            print(f"[WARN] 路線 {route_id} ({direction}) 無對應站點")
            continue

        # --- 計算距離 ---
        try:
            df_route_stops.loc[:, "distance_m"] = df_route_stops.apply(
                lambda s: haversine(car_lat, car_lon, float(s["latitude"]), float(s["longitude"])),
                axis=1
            )
        except Exception as e:
            print(f"[ERROR] 計算距離失敗: {e}")
            continue

        nearest_idx = df_route_stops["distance_m"].idxmin()
        nearest = df_route_stops.loc[nearest_idx]
        print(f"[DEBUG] 最接近站點: {nearest['stop_name']} (距離 {nearest['distance_m']:.2f} 公尺)")

        # --- 輸出 ---
        results.append({
            "route": route_id,
            "X": car_lon,      # 經度
            "Y": car_lat,      # 緯度
            "direction": direction,
            "Current_Loaction": nearest["stop_name"]
        })

    print(f"\n[DEBUG] 結果共 {len(results)} 筆")
    for i, r in enumerate(results):
        print(f"  [{i}] route={r['route']}, dir={r['direction']}, stop={r['Current_Loaction']}")

    print("=== [DEBUG] /GIS_AllFast 結束 ===\n")

    return pd.DataFrame(results).to_dict()


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
    # print("查詢明日預約 user_id=", user_id)
    # print("SQL=", sql)
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


    qr_text = str(data.get("qrcode", "")).strip()
    if not qr_text:
        raise HTTPException(status_code=400, detail="Empty QRCode")

    try:
        # 嘗試解密
        decrypted = decrypt_aes(qr_text, KEY, IV)
        obj = json.loads(decrypted)

        rid = obj.get("reservation_id")
        uid = obj.get("user_id")
        lid = obj.get("line_id")

        if not rid or not uid:
            raise HTTPException(status_code=400, detail="Missing fields")

        return {"status": "success", "data": obj}

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"QRCode decrypt failed: {e}")

@api.post("/car_insert", tags=["Car"], summary="插入車輛即時定位資料")
def insert_car(data: Define.CarInsertRequest):
    rcv_dt = data.rcv_dt or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    sql = f"""
    INSERT INTO ttcarimport (rcv_dt, car_licence, Gpstime, X, Y, Speed, Deg, acc)
    VALUES (
        '{rcv_dt}',
        '{data.car_licence}',
        '{data.Gpstime}',
        {data.X},
        {data.Y},
        {data.Speed},
        {data.Deg},
        {1 if str(data.acc) in ["1", "true", "True"] else 0}
    );
    """

    MySQL_Doing.run(sql)
    
    return {"status": "success", "message": "資料已插入"}

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
    # === 路線排班相關操作 ===

@api.get("/route_schedule", tags=["Admin"], summary="取得所有排班")
def get_route_schedule():
    sql = """
    SELECT id, route_no, direction, special_type, operation_status,
           date, departure_time, license_plate, driver_name, employee_id
    FROM route_schedule
    ORDER BY route_no ASC, departure_time ASC
    """
    rows = MySQL_Doing.run(sql)
    if hasattr(rows, "to_dict"):
        return {"status": "success", "data": rows.to_dict(orient="records")}
    return {"status": "success", "data": rows}

@api.post("/route_schedule/add", tags=["Admin"], summary="新增排班")
def add_route_schedule(data: dict = Body(...)):
    sql = f"""
    INSERT INTO route_schedule
      (route_no, direction, special_type, operation_status, date, departure_time, license_plate, driver_name, employee_id)
    VALUES
      ('{data.get("route_no")}', '{data.get("direction")}', {f"'{data.get('special_type')}'" if data.get("special_type") else "NULL"},
       '{data.get("operation_status", "正常營運")}', '{data.get("date")}', '{data.get("departure_time")}',
       '{data.get("license_plate")}', '{data.get("driver_name")}', '{data.get("employee_id")}')
    """
    MySQL_Doing.run(sql)
    return {"status": "success", "message": "新增成功"}

@api.put("/route_schedule/update/{id}", tags=["Admin"], summary="更新排班")
def update_route_schedule(id: int, data: dict = Body(...)):
    sql = f"""
    UPDATE route_schedule SET
        route_no = '{data.get("route_no")}',
        direction = '{data.get("direction")}',
        special_type = {f"'{data.get('special_type')}'" if data.get("special_type") else "NULL"},
        operation_status = '{data.get("operation_status", "正常營運")}',
        date = '{data.get("date")}',
        departure_time = '{data.get("departure_time")}',
        license_plate = '{data.get("license_plate")}',
        driver_name = '{data.get("driver_name")}',
        employee_id = '{data.get("employee_id")}'
    WHERE id = {id}
    """
    MySQL_Doing.run(sql)
    return {"status": "success", "message": f"排班 {id} 更新成功"}

@api.delete("/route_schedule/delete/{id}", tags=["Admin"], summary="刪除排班")
def delete_route_schedule(id: int):
    sql = f"DELETE FROM route_schedule WHERE id = {id}"
    MySQL_Doing.run(sql)
    return {"status": "success", "message": f"排班 {id} 已刪除"}

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
            # print(f"[WARN] Redis 有 session，但 MySQL 查不到 user={uid}，強制重登")
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
    # print(f"[DEBUG] LINE Profile: {profile}")
    # print(f"[DEBUG] LineID={LineID}, UserName={UserName}, AppToken={app_token}")
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
            # print(f"[CLEANUP] 清掉無效 session: user={uid}")
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

@api.get("/boarding_qr/{reservation_id}", tags=["Client"], summary="產生乘車用 QRCode（PNG）")
def create_boarding_qr(reservation_id: int, download: bool = False):
    """
    依據 reservation_id 產生乘車 QR 圖片。
    - 驗證付款與審核狀態
    - 回傳 PNG 檔（或提供下載）
    """
    try:
        token = generate_boarding_token(reservation_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"產生失敗: {e}")

    import tempfile, os
    temp_dir = tempfile.mkdtemp(prefix="boarding_")
    img_path = os.path.join(temp_dir, f"boarding_{reservation_id}.png")
    save_qr_png(token, img_path)

    if download:
        # 讓用戶直接下載
        return FileResponse(
            img_path,
            media_type="image/png",
            filename=f"boarding_{reservation_id}.png"
        )
    else:
        # 預設直接串流圖片
        buf = BytesIO()
        img = qrcode.make(token)
        img.save(buf, format="PNG")
        buf.seek(0)
        return StreamingResponse(buf, media_type="image/png")


@api.post("/boarding_qr/verify", tags=["Client"], summary="驗證乘車 QRCode")
def verify_boarding_qr(data: Define.BoardingQRVerifyRequest):
    """
    驗證乘車 QR 編碼是否合法與是否具乘車資格。
    """
    token = data.qrcode.strip()
    if not token:
        raise HTTPException(status_code=400, detail="缺少 qrcode")

    result = verify_boarding_token(token)

    if not result.get("ok"):
        print("[DEBUG] verify_boarding_token 驗證失敗:", result)
        return {"status": "error", "reason": result.get("reason")}

    print("[DEBUG] verify_boarding_token 驗證通過:", result)

    # --- 驗證通過後，自動更新 dispatch_status ---
    try:
        reservation_id = result.get("reservation_id") or result.get("data", {}).get("reservation_id")

        print(f"[DEBUG] 抓到 reservation_id = {reservation_id}")

        if reservation_id:
            sql = f"""
                UPDATE reservation
                SET dispatch_status = 'assigned', updated_at = NOW()
                WHERE reservation_id = {int(reservation_id)};
            """
            print(f"[DEBUG] 準備執行 SQL:\n{sql.strip()}")
            MySQL_Doing.run(sql)
            print("[DEBUG] SQL 執行完成")

            # 驗證是否真的有更新
            check_sql = f"SELECT dispatch_status FROM reservation WHERE reservation_id = {int(reservation_id)};"
            df = MySQL_Doing.run(check_sql)
            print(f"[DEBUG] 更新後查詢結果:\n{df}")
        else:
            print("[DEBUG] reservation_id 沒抓到，跳過更新。")

    except Exception as e:
        print(f"[ERROR] 更新 dispatch_status 失敗: {e}")

    return {"status": "success", "data": result}
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

    # print("原始 JSON:", payload)
    # print("加密後 TransactionData:", transaction_data)
    # print("本地算出的 HashDigest:", hash_digest)

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

# ------------------------------
# 新增：今日正常營運路線的即時摘要（30秒快取）
# ------------------------------
_GIS_ALL_CACHE = {"ts": 0.0, "data": None}
_GIS_ALL_TTL = 30  # seconds
_GIS_ALL_LOCK = RLock()

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

"""
docker compose down
docker compose build
docker compose up -d

"""