from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import create_engine, Column, Integer, String, TIMESTAMP, Boolean, ForeignKey, text, func, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel,Field
from typing import Optional, Literal, List
import bcrypt
import os
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
import pytz
from MySQL import MySQL_Run
import pandas as pd
import uvicorn
import hashlib
import json
import secrets
import string
try:
    import redis  # redis-py
except Exception:  # pragma: no cover
    redis = None

# 設定台北時區
TAIPEI_TZ = pytz.timezone('Asia/Taipei')

def get_taipei_time():
    """取得台北時間"""
    return datetime.now(TAIPEI_TZ)

def get_taiwan_datetime():
    """取得台灣時間的 datetime 物件（無時區資訊，供資料庫使用）"""
    return datetime.now(TAIPEI_TZ).replace(tzinfo=None)

# 載入環境變數
load_dotenv()

# MySQL 資料庫設定
DATABASE_URL = f"mysql+pymysql://root:dh9j2(HU#s9h@10.53.1.3:7000/bus_system"
engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ===== OTP/驗證碼：Redis 設定與工具 =====
REDIS_URL = os.getenv("HBUS_REDIS_URL", os.getenv("REDIS_URL", "redis://localhost:6379/0"))
OTP_TTL_SEC = int(os.getenv("HBUS_OTP_TTL_SEC", "300"))           # 驗證碼有效 5 分鐘
OTP_LEN = int(os.getenv("HBUS_OTP_LEN", "6"))                      # 驗證碼長度 6
OTP_MAX_ATTEMPTS = int(os.getenv("HBUS_OTP_MAX_ATTEMPTS", "5"))   # 最多嘗試次數 5
OTP_RESEND_COOLDOWN = int(os.getenv("HBUS_OTP_RESEND_COOLDOWN", "60"))  # 重送冷卻 60 秒
OTP_RL_DEST_MAX_10MIN = int(os.getenv("HBUS_OTP_RL_DEST_MAX_10MIN", "3"))  # 每目的 10 分鐘最多 3 次
OTP_RL_IP_MAX_1H = int(os.getenv("HBUS_OTP_RL_IP_MAX_1H", "10"))          # 每 IP 1 小時最多 10 次
OTP_DEBUG_RETURN_CODE = os.getenv("HBUS_OTP_DEBUG", "false").lower() in {"1", "true", "yes"}
OTP_FORCE_CODE = os.getenv("HBUS_OTP_FORCE_CODE")  # e.g. "123456" 便於測試
OTP_LOG_ENABLE = os.getenv("HBUS_OTP_LOG", "true").lower() in {"1", "true", "yes"}
OTP_LOG_FILE = os.getenv(
    "HBUS_OTP_LOG_FILE",
    os.path.join(os.path.dirname(__file__), "otp_codes.txt"),
)

# 資料庫模型（匹配實際表結構）
class User(Base):
    __tablename__ = "users"
    user_id = Column(Integer, primary_key=True, autoincrement=True)
    line_id = Column(String(100), unique=True)
    username = Column(String(100))
    password = Column(String(255))  # 雜湊密碼
    email = Column(String(255))
    phone = Column(String(20))
    # 使用台灣時間（無時區資訊）以確保與需求一致
    created_at = Column(TIMESTAMP, default=get_taiwan_datetime)
    updated_at = Column(TIMESTAMP, default=get_taiwan_datetime, onupdate=get_taiwan_datetime)
    last_login = Column(TIMESTAMP, nullable=True)
    status = Column(Enum('active', 'inactive'), default='active')
    # 與資料庫一致，並兼容歷史資料 'None'
    reservation_status = Column(
        Enum('no_reservation', 'pending', 'approved', 'rejected', 'completed', 'None'),
        default='no_reservation'
    )  # 預約狀態
    preferences = Column(String)  # TEXT in MySQL
    privacy_settings = Column(String)  # TEXT in MySQL

class AdminUser(Base):
    __tablename__ = "admin_users"
    admin_id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role_id = Column(Integer, ForeignKey("admin_roles.role_id"))
    last_login = Column(TIMESTAMP, nullable=True)
    login_attempts = Column(Integer, default=0)
    status = Column(Enum('active', 'inactive'), default='active')
    created_by = Column(Integer, ForeignKey("admin_users.admin_id"))
    created_at = Column(TIMESTAMP, default=get_taiwan_datetime)
    updated_at = Column(TIMESTAMP, default=get_taiwan_datetime, onupdate=get_taiwan_datetime)

class AdminRole(Base):
    __tablename__ = "admin_roles"
    role_id = Column(Integer, primary_key=True, autoincrement=True)
    role_name = Column(String(100), unique=True, nullable=False)
    role_description = Column(String)  # TEXT in MySQL
    permissions = Column(String)  # TEXT in MySQL
    is_system_role = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, default=func.now())
    updated_at = Column(TIMESTAMP, default=func.now(), onupdate=func.now())

class InMemoryRedis:
    """極簡 In-Memory Redis 替代品（僅供開發測試）。
    支援本檔案用到的方法：get, setex, delete, incr, expire, ttl, ping, set
    注意：非多進程安全，不適合正式環境。
    """
    def __init__(self):
        import time
        self._now = time
        self._store = {}  # key -> (value:str, expire_at:float|None)

    def _expired(self, key):
        v = self._store.get(key)
        if not v:
            return True
        _, exp = v
        if exp is None:
            return False
        if self._now.time() >= exp:
            self._store.pop(key, None)
            return True
        return False

    def ping(self):
        return True

    def get(self, key):
        if self._expired(key):
            return None
        return self._store.get(key, (None, None))[0]

    def set(self, key, value):
        self._store[key] = (str(value), None)
        return True

    def setex(self, key, ttl, value):
        self._store[key] = (str(value), self._now.time() + int(ttl))
        return True

    def delete(self, *keys):
        c = 0
        for k in keys:
            if k in self._store:
                self._store.pop(k, None)
                c += 1
        return c

    def incr(self, key):
        if self._expired(key):
            self._store.pop(key, None)
        val, exp = self._store.get(key, ("0", None))
        try:
            n = int(val) + 1
        except Exception:
            n = 1
        self._store[key] = (str(n), exp)
        return n

    def expire(self, key, ttl):
        if key in self._store:
            v, _ = self._store[key]
            self._store[key] = (v, self._now.time() + int(ttl))
            return True
        return False

    def ttl(self, key):
        if key not in self._store:
            return -2  # Redis: key 不存在
        v, exp = self._store[key]
        if exp is None:
            return -1  # 沒有 TTL
        remain = int(round(exp - self._now.time()))
        if remain <= 0:
            self._store.pop(key, None)
            return -2
        return remain

# Pydantic 模型（更新以匹配表結構）
class UserCreate(BaseModel):
    line_id: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None  # 明文密碼，會在API中雜湊
    email: Optional[str] = None
    phone: Optional[str] = None
    status: Optional[Literal["active", "inactive"]] = 'active'
    reservation_status: Optional[Literal["no_reservation", "pending", "approved", "rejected", "completed"]] = 'no_reservation'
    preferences: Optional[str] = None
    privacy_settings: Optional[str] = None


class UserUpdate(BaseModel):
    line_id: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None  # 明文密碼，會在API中雜湊
    email: Optional[str] = None
    phone: Optional[str] = None
    last_login: Optional[str] = None
    status: Optional[Literal["active", "inactive"]] = None
    reservation_status: Optional[Literal["no_reservation", "pending", "approved", "rejected", "completed"]] = None
    preferences: Optional[str] = None
    privacy_settings: Optional[str] = None

class AdminUserCreate(BaseModel):
    username: str
    password: str
    role_id: Optional[int] = None
    status: Optional[str] = 'active'
    created_by: Optional[int] = None

class AdminUserUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    role_id: Optional[int] = None
    last_login: Optional[str] = None
    login_attempts: Optional[int] = None
    status: Optional[str] = None
    created_by: Optional[int] = None

class AdminRoleCreate(BaseModel):
    role_name: str
    role_description: Optional[str] = None
    permissions: Optional[str] = None
    is_system_role: Optional[bool] = False

class AdminRoleUpdate(BaseModel):
    role_name: Optional[str] = None
    role_description: Optional[str] = None
    permissions: Optional[str] = None
    is_system_role: Optional[bool] = None

class OTPRequest(BaseModel):
    account: str
    purpose: Optional[str] = "login"  # login | signup | reset
    channel: Optional[str] = None      # email | sms | null

class OTPVerify(BaseModel):
    account: str
    code: str
    purpose: Optional[str] = "login"

class LoginRequest(BaseModel):
    username: str
    password: str


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



# 依賴注入
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 工具函數
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    """從 Bearer token 中獲取當前用戶"""
    token = credentials.credentials
    
    # 簡單的 token 解析 (格式: admin_{user_id}_token)
    if not token.startswith('admin_') or not token.endswith('_token'):
        raise HTTPException(status_code=401, detail="無效的 token 格式")
    
    try:
        # 從 token 中提取用戶 ID
        user_id = int(token.split('_')[1])
        user = db.query(AdminUser).filter(AdminUser.admin_id == user_id).first()
        if not user:
            raise HTTPException(status_code=401, detail="用戶不存在")
        return user
    except (ValueError, IndexError):
        raise HTTPException(status_code=401, detail="無效的 token")

def check_permission(user, permission: str, db: Session) -> bool:
    role = db.query(AdminRole).filter(AdminRole.role_id == user.role_id).first()
    if not role:
        return False
    permissions = role.permissions.split(',') if role.permissions else []  # 假設 permissions 是逗號分隔
    return permission in permissions

# Redis 相關輔助函數
def get_redis():
    if redis is None:
        # 若無 redis 模組，回退至記憶體版（僅開發用）
        if not hasattr(app.state, "redis") or app.state.redis is None:
            print("[OTP] redis 模組未安裝，改用 InMemoryRedis（開發用）")
            app.state.redis = InMemoryRedis()
        return app.state.redis
    if not hasattr(app.state, "redis") or app.state.redis is None:
        try:
            app.state.redis = redis.Redis.from_url(REDIS_URL, decode_responses=True)
            app.state.redis.ping()
        except Exception as e:  # pragma: no cover
            # 連線失敗時回退到 InMemoryRedis：開發測試無阻
            print(f"[OTP] Redis 連線失敗，改用 InMemoryRedis：{e}")
            app.state.redis = InMemoryRedis()
    return app.state.redis

def _norm_account(acc: str) -> str:
    return (acc or "").strip().lower()

def _hash_key(text_value: str) -> str:
    return hashlib.sha256(text_value.encode("utf-8")).hexdigest()

def _otp_keys(purpose: str, acc_hash: str):
    return {
        "code": f"otp:{purpose}:{acc_hash}",
        "tries": f"otp:{purpose}:{acc_hash}:tries",
        "cooldown": f"otp:{purpose}:{acc_hash}:cooldown",
        "lock": f"otp:{purpose}:{acc_hash}:lock",
        "dest_rl": f"otp:rl:dest:{acc_hash}",
    }

def _ip_key(ip: str) -> str:
    return f"otp:rl:ip:{ip}"

def _gen_code(length: int = OTP_LEN) -> str:
    if OTP_FORCE_CODE:
        return OTP_FORCE_CODE[:length]
    return "".join(secrets.choice(string.digits) for _ in range(length))

# FastAPI 應用
app = FastAPI()

# 動態 CORS 設定函數
def is_allowed_origin(origin: str) -> bool:
    """檢查來源是否被允許"""
    allowed_patterns = [
        "http://192.168.0.",  # 192.168.0.x 網段
        ":5678"    
        ":5173"           # 任何使用 5678 port 的地址
    ]
    
    for pattern in allowed_patterns:
        if pattern in origin:
            return True
    return False

# 加入 CORS 設定
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+):(5678|3000|8080)$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# 登入 API
@app.post("/auth/login")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(AdminUser).filter(AdminUser.username == request.username).first()
    
    if not user:
        raise HTTPException(status_code=401, detail="無效憑證")
    
    # 檢查用戶狀態
    if user.status != 'active':
        status_messages = {
            'inactive': '帳號已停用，請聯繫管理員'
        }
        raise HTTPException(status_code=401, detail=status_messages.get(user.status, '帳號狀態異常'))
    
    # 驗證密碼
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="無效憑證")
    
    # 更新 last_login 為台北時間
    user.last_login = get_taiwan_datetime()
    db.commit()
    
    # 獲取角色資訊
    role = db.query(AdminRole).filter(AdminRole.role_id == user.role_id).first()
    
    # 回傳前端期望的格式
    return {
        "access_token": f"admin_{user.admin_id}_token", # 簡化的 token
        "token_type": "bearer",
        "user_id": user.admin_id,
        "username": user.username,
        "role": role.role_name if role else None
    }

# 儀表板統計 API
@app.get("/api/dashboard/member-stats")
def get_member_statistics(db: Session = Depends(get_db)):
    """
    取得會員統計資料
    """
    try:
        # 計算總會員數
        total_members = db.query(User).count()
        
        # 計算活躍會員數 (status = 'active')
        active_members = db.query(User).filter(User.status == 'active').count()
        
        # 計算本月新會員數 (使用台北時區)
        taipei_now = get_taipei_time()
        start_of_month = taipei_now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        # 轉換為無時區的 datetime 供資料庫查詢使用
        start_of_month_naive = start_of_month.replace(tzinfo=None)
        
        # 先檢查 User 模型是否有 created_at 欄位
        try:
            new_members_this_month = db.query(User).filter(User.created_at >= start_of_month_naive).count()
        except AttributeError:
            # 如果沒有 created_at 欄位，則設為 0
            new_members_this_month = 0
        
        return {
            "success": True,
            "data": {
                "total_members": total_members,
                "active_members": active_members,
                "new_members_this_month": new_members_this_month,
                "growth_rate": round((new_members_this_month / max(total_members - new_members_this_month, 1)) * 100, 2) if total_members > 0 else 0
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "data": {
                "total_members": 0,
                "active_members": 0,
                "new_members_this_month": 0,
                "growth_rate": 0
            }
        }

# 會員增長趨勢 API
@app.get("/api/dashboard/member-growth")
def get_member_growth_trend(days: int = 7, db: Session = Depends(get_db)):
    """
    取得會員增長趨勢資料
    參數: days - 查詢天數 (1, 7, 30)
    """
    try:
        from datetime import timedelta
        from sqlalchemy import func, extract
        
        taipei_now = get_taipei_time()
        start_date = taipei_now - timedelta(days=days)
        start_date_naive = start_date.replace(tzinfo=None)
        
        # 根據天數決定分組方式
        if days == 1:
            # 最近1天：按小時分組
            growth_data = []
            for i in range(24):
                hour_start = (taipei_now - timedelta(hours=23-i)).replace(minute=0, second=0, microsecond=0)
                hour_end = hour_start + timedelta(hours=1)
                
                count = db.query(User).filter(
                    User.created_at >= hour_start.replace(tzinfo=None),
                    User.created_at < hour_end.replace(tzinfo=None)
                ).count()
                
                growth_data.append({
                    "period": hour_start.strftime("%H:00"),
                    "count": count,
                    "cumulative": sum([x["count"] for x in growth_data]) + count
                })
                
        elif days == 7:
            # 近7天：按天分組
            growth_data = []
            cumulative_count = db.query(User).filter(
                User.created_at < start_date_naive
            ).count()
            
            for i in range(days):
                day_start = (start_date + timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
                day_end = day_start + timedelta(days=1)
                
                daily_count = db.query(User).filter(
                    User.created_at >= day_start.replace(tzinfo=None),
                    User.created_at < day_end.replace(tzinfo=None)
                ).count()
                
                cumulative_count += daily_count
                
                growth_data.append({
                    "period": day_start.strftime("%m/%d"),
                    "count": daily_count,
                    "cumulative": cumulative_count
                })
                
        else:  # days == 30
            # 近30天：按週分組
            growth_data = []
            cumulative_count = db.query(User).filter(
                User.created_at < start_date_naive
            ).count()
            
            # 分成5週，每週6天
            for week in range(5):
                week_start = start_date + timedelta(days=week*6)
                week_end = week_start + timedelta(days=6)
                
                weekly_count = db.query(User).filter(
                    User.created_at >= week_start.replace(tzinfo=None),
                    User.created_at < week_end.replace(tzinfo=None)
                ).count()
                
                cumulative_count += weekly_count
                
                growth_data.append({
                    "period": f"{week_start.strftime('%m/%d')}",
                    "count": weekly_count,
                    "cumulative": cumulative_count
                })
        
        # 計算統計資料
        total_growth = sum([x["count"] for x in growth_data])
        avg_daily = round(total_growth / max(days, 1), 1)
        
        return {
            "success": True,
            "data": {
                "growth_data": growth_data,
                "total_growth": total_growth,
                "avg_daily": avg_daily,
                "period_days": days
            }
        }
        
    except Exception as e:
        # 回傳預設資料以避免前端錯誤
        default_data = []
        if days == 1:
            default_data = [{"period": f"{i}:00", "count": 0, "cumulative": 0} for i in range(24)]
        elif days == 7:
            default_data = [{"period": f"0{i+1}/0{i+1}", "count": 0, "cumulative": 0} for i in range(7)]
        else:
            default_data = [{"period": f"Week{i+1}", "count": 0, "cumulative": 0} for i in range(5)]
            
        return {
            "success": False,
            "error": str(e),
            "data": {
                "growth_data": default_data,
                "total_growth": 0,
                "avg_daily": 0,
                "period_days": days
            }
        }

# 會員活躍度分析 API
@app.get("/api/dashboard/member-activity")
def get_member_activity(days: int = 7, db: Session = Depends(get_db)):
    """
    取得會員活躍度分析數據
    
    參數:
    - days: 分析天數 (1, 7, 30)
    """
    try:
        # 計算時間範圍
        end_date = get_taipei_time()
        start_date = end_date - timedelta(days=days)
        start_date_naive = start_date.replace(tzinfo=None)
        end_date_naive = end_date.replace(tzinfo=None)
        
        # 定義活躍度標準
        # 高活躍：最近登入 <= 3天
        # 中活躍：最近登入 4-7天  
        # 低活躍：最近登入 8-30天
        # 不活躍：最近登入 > 30天 或從未登入
        
        now_naive = end_date.replace(tzinfo=None)
        high_active_cutoff = now_naive - timedelta(days=3)
        medium_active_cutoff = now_naive - timedelta(days=7)
        low_active_cutoff = now_naive - timedelta(days=30)
        
        # 查詢各活躍度級別的會員數量
        high_active = db.query(User).filter(
            User.status == 'active',
            User.last_login.isnot(None),
            User.last_login >= high_active_cutoff
        ).count()
        
        medium_active = db.query(User).filter(
            User.status == 'active',
            User.last_login.isnot(None),
            User.last_login >= medium_active_cutoff,
            User.last_login < high_active_cutoff
        ).count()
        
        low_active = db.query(User).filter(
            User.status == 'active',
            User.last_login.isnot(None),
            User.last_login >= low_active_cutoff,
            User.last_login < medium_active_cutoff
        ).count()
        
        inactive = db.query(User).filter(
            User.status == 'active'
        ).filter(
            (User.last_login.is_(None)) | 
            (User.last_login < low_active_cutoff)
        ).count()
        
        # 計算總數和活躍率
        total_members = high_active + medium_active + low_active + inactive
        active_members = high_active + medium_active
        active_rate = round((active_members / total_members * 100), 1) if total_members > 0 else 0
        
        # 計算最大值用於百分比計算
        max_count = max(high_active, medium_active, low_active, inactive) if total_members > 0 else 1
        
        # 構建活躍度數據
        activity_data = [
            {
                "label": "高活躍",
                "count": high_active,
                "percentage": round((high_active / max_count * 100), 1) if max_count > 0 else 0
            },
            {
                "label": "中活躍", 
                "count": medium_active,
                "percentage": round((medium_active / max_count * 100), 1) if max_count > 0 else 0
            },
            {
                "label": "低活躍",
                "count": low_active,
                "percentage": round((low_active / max_count * 100), 1) if max_count > 0 else 0
            },
            {
                "label": "不活躍",
                "count": inactive,
                "percentage": round((inactive / max_count * 100), 1) if max_count > 0 else 0
            }
        ]
        
        return {
            "success": True,
            "data": {
                "activity_data": activity_data,
                "summary": {
                    "active_rate": active_rate,
                    "active_members": active_members,
                    "total_members": total_members
                },
                "period_days": days
            }
        }
        
    except Exception as e:
        print(f"會員活躍度查詢錯誤: {e}")
        # 返回預設數據以防錯誤
        return {
            "success": False,
            "data": {
                "activity_data": [
                    {"label": "高活躍", "count": 0, "percentage": 0},
                    {"label": "中活躍", "count": 0, "percentage": 0},
                    {"label": "低活躍", "count": 0, "percentage": 0},
                    {"label": "不活躍", "count": 0, "percentage": 0}
                ],
                "summary": {
                    "active_rate": 0,
                    "active_members": 0,
                    "total_members": 0
                },
                "period_days": days
            }
        }

# 管理員統計 API
@app.get("/api/dashboard/admin-stats")
def get_admin_statistics(db: Session = Depends(get_db)):
    """
    取得管理員統計資料
    """
    try:
        # 計算總管理員數
        total_admins = db.query(AdminUser).count()
        
        # 計算角色數量
        total_roles = db.query(AdminRole).count()
        
        # 假設目前在線管理員為 1 (可以根據實際需求修改)
        online_admins = 1
        
        return {
            "success": True,
            "data": {
                "total_admins": total_admins,
                "online_admins": online_admins,
                "total_roles": total_roles,
                "active_today": 1
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "data": {
                "total_admins": 0,
                "online_admins": 0,
                "total_roles": 0,
                "active_today": 0
            }
        }

# 資料庫狀況 API
@app.get("/api/dashboard/database-stats")
def get_database_statistics(db: Session = Depends(get_db)):
    """
    取得資料庫狀況統計
    """
    try:
        from time import time
        start_time = time()
        
        # 測試資料庫連線
        db.execute(text("SELECT 1"))
        
        connection_time = round((time() - start_time) * 1000, 2)  # 轉換為毫秒
        
        # 取得資料表數量
        result = db.execute(text("SHOW TABLES"))
        total_tables = len(list(result))
        
        return {
            "success": True,
            "data": {
                "status": "正常",
                "connection_time": connection_time,
                "total_tables": total_tables,
                "health": "良好" if connection_time < 100 else "一般"
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "data": {
                "status": "異常",
                "connection_time": 9999,
                "total_tables": 0,
                "health": "異常"
            }
        }

# 用戶管理 API
@app.get("/users")
def get_users(
    page: int = 1,
    limit: int = 10,
    search: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    # 基本查詢
    query = db.query(User)
    
    # 搜尋條件（搜尋用戶名、email、電話）
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (User.username.like(search_pattern)) |
            (User.email.like(search_pattern)) |
            (User.phone.like(search_pattern))
        )
    
    # 狀態篩選
    if status:
        query = query.filter(User.status == status)
    
    # 計算總數
    total = query.count()
    
    # 分頁
    users = query.offset((page - 1) * limit).limit(limit).all()
    
    # 格式化回應
    users_data = []
    for u in users:
        # 兼容舊值：DB 可能存在 'None'，統一轉成 'no_reservation'
        rsv = u.reservation_status
        if rsv == 'None' or rsv is None:
            rsv_out = 'no_reservation'
        else:
            rsv_out = rsv
        users_data.append({
            "user_id": u.user_id,
            "line_id": u.line_id,
            "username": u.username,
            "email": u.email,
            "phone": u.phone,
            "status": u.status,
            "reservation_status": rsv_out,
            "preferences": u.preferences,
            "privacy_settings": u.privacy_settings,
            "created_at": u.created_at.isoformat() if u.created_at else None,
            "updated_at": u.updated_at.isoformat() if u.updated_at else None,
            "last_login": u.last_login.isoformat() if u.last_login else None
        })
    
    return {
        "users": users_data,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit
    }

@app.post("/Create_users")
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    user_data = user.dict(exclude_unset=True)
    
    # 處理密碼雜湊
    if user_data.get('password') and user_data['password'].strip():
        hashed_password = bcrypt.hashpw(user_data['password'].encode('utf-8'), bcrypt.gensalt())
        user_data['password'] = hashed_password.decode('utf-8')
    else:
        # 如果沒有提供密碼或密碼為空，設為 None
        user_data['password'] = None
    
    # 處理可選文字欄位，避免插入空字串或無效值
    optional_fields = ['preferences', 'privacy_settings', 'reservation_status']
    for field in optional_fields:
        if field in user_data:
            if not user_data[field] or not user_data[field].strip():
                user_data[field] = None

    # 預設或相容：reservation_status 未提供或為 'None' 時，轉為 'no_reservation'
    if not user_data.get('reservation_status') or user_data.get('reservation_status') == 'None':
        user_data['reservation_status'] = 'no_reservation'

    # 針對可重複風險欄位做唯一性檢查（若有提供值）
    # username、phone、email、line_id 均不允許重複
    # 空字串一律視為未提供
    conflict_fields = []
    if user_data.get('username') and str(user_data['username']).strip():
        exist = db.query(User).filter(User.username == str(user_data['username']).strip()).first()
        if exist:
            conflict_fields.append('username')
    if user_data.get('phone') and str(user_data['phone']).strip():
        exist = db.query(User).filter(User.phone == str(user_data['phone']).strip()).first()
        if exist:
            conflict_fields.append('phone')
    if user_data.get('email') and str(user_data['email']).strip():
        exist = db.query(User).filter(User.email == str(user_data['email']).strip()).first()
        if exist:
            conflict_fields.append('email')
    if user_data.get('line_id') and str(user_data['line_id']).strip():
        exist = db.query(User).filter(User.line_id == str(user_data['line_id']).strip()).first()
        if exist:
            conflict_fields.append('line_id')

    if conflict_fields:
        raise HTTPException(status_code=409, detail=f"以下欄位已存在: {', '.join(conflict_fields)}")
    
    new_user = User(**user_data)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"user_id": new_user.user_id, "message": "用戶建立成功"}

@app.get("/users/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用戶不存在")
    return {
        "user_id": user.user_id, 
        "line_id": user.line_id, 
        "username": user.username, 
        "email": user.email, 
        "phone": user.phone, 
        "status": user.status,
        "reservation_status": ('no_reservation' if (user.reservation_status in (None, 'None')) else user.reservation_status),
        "preferences": user.preferences, 
        "privacy_settings": user.privacy_settings,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        "last_login": user.last_login.isoformat() if user.last_login else None
    }

@app.put("/users/{user_id}")
def update_user(user_id: int, user_update: UserUpdate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用戶不存在")
    
    update_data = user_update.dict(exclude_unset=True)
    
    # 處理密碼雜湊
    if 'password' in update_data:
        if update_data['password'] and update_data['password'].strip():
            # 如果提供了有效的密碼，進行雜湊處理
            hashed_password = bcrypt.hashpw(update_data['password'].encode('utf-8'), bcrypt.gensalt())
            update_data['password'] = hashed_password.decode('utf-8')
        else:
            # 如果密碼為空或 None，保持原密碼不變
            del update_data['password']

    # 針對可重複風險欄位做唯一性檢查（僅在該欄位真的有『變更』時才檢查）
    for field_name in ['username', 'phone', 'email', 'line_id']:
        if field_name in update_data:
            new_raw = update_data[field_name]
            new_val = str(new_raw).strip() if new_raw is not None else None
            old_val = getattr(user, field_name)
            old_val_norm = str(old_val).strip() if isinstance(old_val, str) else old_val

            # 若此次更新沒有實質變更，跳過唯一性檢查，允許修改其他欄位（例如狀態）
            if (new_val or None) == (old_val_norm or None):
                continue

            # 空字串視為未提供，不做唯一性檢查（等同於不更新該欄位）
            if not new_val:
                continue

            exist = db.query(User).filter(getattr(User, field_name) == new_val, User.user_id != user_id).first()
            if exist:
                raise HTTPException(status_code=409, detail=f"{field_name} 已存在，請使用其他值")

    # 相容與轉換：中文狀態值/舊值
    if 'status' in update_data:
        status_map = {'啟用': 'active', '停用': 'inactive'}
        s = update_data['status']
        update_data['status'] = status_map.get(s, s)
    if 'reservation_status' in update_data:
        rmap = {
            'None': 'no_reservation',
            '未預約': 'no_reservation',
            '審核中': 'pending',
            '已核准': 'approved',
            '已拒絕': 'rejected',
            '已完成': 'completed',
        }
        rs = update_data['reservation_status']
        update_data['reservation_status'] = rmap.get(rs, rs)

    # 僅對有實質變更的欄位進行設置
    changed = {}
    for key, value in update_data.items():
        old = getattr(user, key)
        old_norm = str(old).strip() if isinstance(old, str) else old
        new_norm = str(value).strip() if isinstance(value, str) else value
        if (new_norm or None) != (old_norm or None):
            setattr(user, key, value)
            changed[key] = {'from': old, 'to': value}
    # 明確刷新 updated_at 為台灣時間
    try:
        user.updated_at = get_taiwan_datetime()
    except Exception:
        pass
    db.commit()
    try:
        db.refresh(user)
    except Exception:
        pass
    return {"message": "用戶更新成功", "changed": changed}

@app.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    # 移除權限檢查
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用戶不存在")
    db.delete(user)
    db.commit()
    return {"message": "用戶刪除成功"}


# 用戶登入驗證 API
class UserLogin(BaseModel):
    username: str
    password: str

@app.post("/users/login")
def login_user(login_data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == login_data.username).first()
    if not user:
        raise HTTPException(status_code=401, detail="用戶名或密碼錯誤")
    
    # 檢查用戶狀態：停用則禁止登入
    if user.status != 'active':
        status_messages = {
            'inactive': '帳號已停用，請聯絡管理員'
        }
        raise HTTPException(status_code=401, detail=status_messages.get(user.status, '帳號狀態異常'))
    
    # 檢查用戶是否有密碼設定
    if not user.password:
        raise HTTPException(status_code=401, detail="用戶尚未設定密碼，請聯絡管理員")
    
    # 檢查密碼
    try:
        if not bcrypt.checkpw(login_data.password.encode('utf-8'), user.password.encode('utf-8')):
            raise HTTPException(status_code=401, detail="用戶名或密碼錯誤")
    except ValueError:
        # 密碼格式不正確，可能是舊格式或損壞的資料
        raise HTTPException(status_code=401, detail="密碼格式錯誤，請聯絡管理員重設密碼")
    
    # 更新最後登入時間（台灣時間）
    user.last_login = get_taiwan_datetime()
    db.commit()
    
    return {
        "message": "登入成功",
        "user": {
            "user_id": user.user_id,
            "username": user.username,
            "line_id": user.line_id,
            "email": user.email,
            "phone": user.phone,
            "status": user.status,
            "reservation_status": user.reservation_status
        }
    }

# 管理員用戶 API
@app.get("/api/admin/users")
def get_admin_users(
    page: int = 1,
    limit: int = 10,
    search: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    取得管理員用戶列表（支援分頁和搜尋）
    
    參數:
    - page: 頁碼 (預設 1)
    - limit: 每頁筆數 (預設 10)
    - search: 搜尋關鍵字（搜尋用戶名）
    - status: 狀態篩選 (active, inactive)
    """
    try:
        # 建立基本查詢
        query = db.query(AdminUser, AdminRole).join(
            AdminRole, AdminUser.role_id == AdminRole.role_id, isouter=True
        )
        
        # 搜尋功能
        if search:
            query = query.filter(AdminUser.username.contains(search))
        
        # 狀態篩選
        if status:
            query = query.filter(AdminUser.status == status)
        
        # 計算總筆數
        total = query.count()
        
        # 分頁
        offset = (page - 1) * limit
        admin_users = query.offset(offset).limit(limit).all()
        
        # 格式化結果
        result = []
        for admin_user, admin_role in admin_users:
            result.append({
                "admin_id": admin_user.admin_id,
                "username": admin_user.username,
                "role_id": admin_user.role_id,
                "role_name": admin_role.role_name if admin_role else "未指定",
                "status": admin_user.status,
                "last_login": admin_user.last_login.isoformat() if admin_user.last_login else None,
                "login_attempts": admin_user.login_attempts,
                "created_at": admin_user.created_at.isoformat() if admin_user.created_at else None
            })
        
        return {
            "success": True,
            "data": {
                "admin_users": result,
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total,
                    "pages": (total + limit - 1) // limit
                }
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"取得管理員列表失敗: {str(e)}"
        }

# 取得管理員角色列表
@app.get("/api/admin/roles")
def get_admin_roles(db: Session = Depends(get_db)):
    """取得所有管理員角色"""
    try:
        roles = db.query(AdminRole).all()
        return {
            "success": True,
            "data": [{
                "role_id": role.role_id,
                "role_name": role.role_name,
                "role_description": role.role_description
            } for role in roles]
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"取得角色列表失敗: {str(e)}"
        }

@app.post("/api/admin/users")
def create_admin_user(user: AdminUserCreate, db: Session = Depends(get_db), current_user: AdminUser = Depends(get_current_user)):
    """建立新的管理員用戶"""
    try:
        # 獲取當前用戶角色
        current_role = db.query(AdminRole).filter(AdminRole.role_id == current_user.role_id).first()
        
        # 權限檢查
        if current_role and current_role.role_name == 'super_admin':
            # Super Admin 可以創建任何角色，但不能創建額外的 super_admin
            if user.role_id == 1:  # 嘗試創建 super_admin
                existing_super_admin_count = db.query(AdminUser).join(AdminRole).filter(AdminRole.role_name == 'super_admin').count()
                if existing_super_admin_count >= 1:
                    return {
                        "success": False,
                        "message": "系統只能有一組 Super Admin"
                    }
        elif current_role and current_role.role_name == 'admin':
            # 普通 Admin 只能創建 admin 角色的用戶
            if user.role_id != 2:
                return {
                    "success": False,
                    "message": "普通管理員只能創建 Admin 角色的帳號"
                }
        else:
            return {
                "success": False,
                "message": "沒有權限創建用戶"
            }
        
        # 檢查用戶名是否已存在
        existing_user = db.query(AdminUser).filter(AdminUser.username == user.username).first()
        if existing_user:
            return {
                "success": False,
                "message": "用戶名已存在"
            }
        
        hashed_password = hash_password(user.password)
        new_user = AdminUser(
            username=user.username, 
            password_hash=hashed_password, 
            role_id=user.role_id, 
            status=user.status, 
            created_by=user.created_by
        )
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        return {
            "success": True,
            "data": {
                "admin_id": new_user.admin_id,
                "message": "管理員用戶建立成功"
            }
        }
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "message": f"建立管理員用戶失敗: {str(e)}"
        }

@app.put("/api/admin/users/{admin_id}")
def update_admin_user(admin_id: int, user_update: AdminUserUpdate, db: Session = Depends(get_db), current_user: AdminUser = Depends(get_current_user)):
    """更新管理員用戶"""
    try:            
        # 獲取當前用戶角色
        current_role = db.query(AdminRole).filter(AdminRole.role_id == current_user.role_id).first()
        
        user = db.query(AdminUser).filter(AdminUser.admin_id == admin_id).first()
        if not user:
            return {
                "success": False,
                "message": "管理員用戶不存在"
            }
        
        # 獲取要編輯的用戶角色
        target_role = db.query(AdminRole).filter(AdminRole.role_id == user.role_id).first()
        
        # 權限檢查
        if current_role and current_role.role_name == 'super_admin':
            # Super Admin 可以修改其他用戶的任何屬性，但有特定限制
            if admin_id == current_user.admin_id:
                # Super Admin 不能修改自己的角色權限（包括降級為 Admin）
                if hasattr(user_update, 'role_id') and user_update.role_id and user_update.role_id != user.role_id:
                    return {
                        "success": False,
                        "message": "Super Admin 不能修改自己的角色權限，包括降級為 Admin"
                    }
                # Super Admin 不能把自己的狀態改為停用
                if hasattr(user_update, 'status') and user_update.status and user_update.status == 'inactive':
                    return {
                        "success": False,
                        "message": "Super Admin 不能停用自己的帳號"
                    }
            else:
                # Super Admin 不能修改其他 Super Admin 的任何資訊
                if target_role and target_role.role_name == 'super_admin':
                    return {
                        "success": False,
                        "message": "Super Admin 不能修改其他 Super Admin 的資訊"
                    }
        elif current_role and current_role.role_name == 'admin':
            # 普通 Admin 的權限限制
            
            # 1. 不能修改 super_admin 用戶
            if target_role and target_role.role_name == 'super_admin':
                return {
                    "success": False,
                    "message": "不能修改 Super Admin 用戶"
                }
            
            # 2. 不能修改角色
            if hasattr(user_update, 'role_id') and user_update.role_id and user_update.role_id != user.role_id:
                return {
                    "success": False,
                    "message": "普通管理員無權限修改用戶角色"
                }
            
            # 3. 不能修改狀態
            if hasattr(user_update, 'status') and user_update.status and user_update.status != user.status:
                return {
                    "success": False,
                    "message": "普通管理員無權限修改用戶狀態"
                }
                
            # 4. 只能修改用戶名和密碼
        else:
            return {
                "success": False,
                "message": "沒有權限修改用戶"
            }
        
        # 如果要更新用戶名，檢查是否已存在
        if hasattr(user_update, 'username') and user_update.username and user_update.username != user.username:
            existing_user = db.query(AdminUser).filter(
                AdminUser.username == user_update.username,
                AdminUser.admin_id != admin_id
            ).first()
            if existing_user:
                return {
                    "success": False,
                    "message": "用戶名已存在"
                }
        
        # 更新字段
        for key, value in user_update.dict(exclude_unset=True).items():
            if key == "password":
                # 只有密碼不為空時才更新
                if value and value.strip():
                    setattr(user, "password_hash", hash_password(value))
            else:
                setattr(user, key, value)
        
        db.commit()
        return {
            "success": True,
            "message": "管理員用戶更新成功"
        }
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "message": f"更新管理員用戶失敗: {str(e)}"
        }

@app.delete("/api/admin/users/{admin_id}")
def delete_admin_user(admin_id: int, db: Session = Depends(get_db), current_user: AdminUser = Depends(get_current_user)):
    """刪除管理員用戶"""
    try:
        # 獲取當前用戶角色
        current_role = db.query(AdminRole).filter(AdminRole.role_id == current_user.role_id).first()
        
        user = db.query(AdminUser).filter(AdminUser.admin_id == admin_id).first()
        if not user:
            return {
                "success": False,
                "message": "管理員用戶不存在"
            }
            
        # 獲取要刪除用戶的角色
        target_role = db.query(AdminRole).filter(AdminRole.role_id == user.role_id).first()
        
        # 權限檢查
        if current_role and current_role.role_name == 'super_admin':
            # Super Admin 可以刪除 Admin 用戶，但不能刪除自己或其他 Super Admin
            if admin_id == current_user.admin_id:
                return {
                    "success": False,
                    "message": "不能刪除自己的帳號"
                }
            # Super Admin 不能刪除其他 Super Admin
            if target_role and target_role.role_name == 'super_admin':
                return {
                    "success": False,
                    "message": "Super Admin 不能刪除其他 Super Admin"
                }
        elif current_role and current_role.role_name == 'admin':
            # 普通 Admin 不能刪除任何用戶
            return {
                "success": False,
                "message": "普通管理員沒有權限刪除用戶"
            }
        else:
            return {
                "success": False,
                "message": "沒有權限刪除用戶"
            }
        
        # 檢查是否為系統管理員（可選的保護機制）
        if user.admin_id == 1:  # 假設 ID 1 是超級管理員
            return {
                "success": False,
                "message": "無法刪除超級管理員"
            }
        
        db.delete(user)
        db.commit()
        return {
            "success": True,
            "message": "管理員用戶刪除成功"
        }
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "message": f"刪除管理員用戶失敗: {str(e)}"
        }

# 角色管理 API
@app.get("/roles")
def get_roles(db: Session = Depends(get_db)):
    # 移除權限檢查
    roles = db.query(AdminRole).all()
    return {"roles": [{"role_id": r.role_id, "role_name": r.role_name, "role_description": r.role_description, "permissions": r.permissions, "is_system_role": r.is_system_role} for r in roles]}

@app.post("/roles")
def create_role(role: AdminRoleCreate, db: Session = Depends(get_db)):
    # 移除權限檢查
    new_role = AdminRole(**role.dict())
    db.add(new_role)
    db.commit()
    db.refresh(new_role)
    return {"role_id": new_role.role_id, "message": "角色建立成功"}

@app.put("/roles/{role_id}")
def update_role(role_id: int, role_update: AdminRoleUpdate, db: Session = Depends(get_db)):
    # 移除權限檢查
    role = db.query(AdminRole).filter(AdminRole.role_id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")
    for key, value in role_update.dict(exclude_unset=True).items():
        setattr(role, key, value)
    db.commit()
    return {"message": "角色更新成功"}

@app.delete("/roles/{role_id}")
def delete_role(role_id: int, db: Session = Depends(get_db)):
    # 移除權限檢查
    role = db.query(AdminRole).filter(AdminRole.role_id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="角色不存在")
    db.delete(role)
    db.commit()
    return {"message": "角色刪除成功"}

# 權限 API
@app.get("/permissions")
def get_permissions(db: Session = Depends(get_db)):
    # 移除權限檢查
    roles = db.query(AdminRole).all()
    permissions = {}
    for role in roles:
        permissions[role.role_name] = role.permissions.split(',') if role.permissions else []
    return {"permissions": permissions}

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

# ===== OTP/驗證碼 API =====
@app.post("/auth/otp/request")
def otp_request(req: OTPRequest, request: Request):
    r = get_redis()
    purpose = (req.purpose or "login").strip().lower()
    acc = _norm_account(req.account)
    if not acc:
        raise HTTPException(status_code=400, detail="缺少 account")
    acc_hash = _hash_key(acc)
    keys = _otp_keys(purpose, acc_hash)

    # 檢查是否鎖定
    if r.get(keys["lock"]):
        raise HTTPException(status_code=429, detail="驗證碼已鎖定，請稍後再試")

    # 重送冷卻
    if r.ttl(keys["cooldown"]) > 0:
        raise HTTPException(status_code=429, detail="發送過於頻繁，請稍後再試")

    # 目的地 rate limit（10 分鐘 3 次）
    dest_cnt = r.incr(keys["dest_rl"])
    if dest_cnt == 1:
        r.expire(keys["dest_rl"], 600)
    if dest_cnt > OTP_RL_DEST_MAX_10MIN:
        raise HTTPException(status_code=429, detail="請求次數過多，稍後再試")

    # 來源 IP rate limit（1 小時 10 次）
    ip = request.client.host if request and request.client else "unknown"
    ip_key = _ip_key(ip)
    ip_cnt = r.incr(ip_key)
    if ip_cnt == 1:
        r.expire(ip_key, 3600)
    if ip_cnt > OTP_RL_IP_MAX_1H:
        raise HTTPException(status_code=429, detail="此 IP 請求過多，請稍後再試")

    # 產生並保存驗證碼
    code = _gen_code()
    payload = {
        "code": code,
        "created_at": get_taipei_time().isoformat(),
        "purpose": purpose,
        "attempts_left": OTP_MAX_ATTEMPTS,
    }
    r.setex(keys["code"], OTP_TTL_SEC, json.dumps(payload))
    r.setex(keys["tries"], OTP_TTL_SEC, str(OTP_MAX_ATTEMPTS))
    r.setex(keys["cooldown"], OTP_RESEND_COOLDOWN, "1")

    # 將驗證碼與帳號寫入檔案（測試用途，正式環境請關閉 HBUS_OTP_LOG）
    if OTP_LOG_ENABLE:
        try:
            ts = get_taipei_time().strftime("%Y-%m-%d %H:%M:%S %z")
            with open(OTP_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(f"{ts}\taccount={acc}\tpurpose={purpose}\tcode={code}\n")
        except Exception as e:
            print(f"[OTP] 寫入驗證碼檔案失敗: {e}")

    # 在此整合真實發送（SMS/Email）。目前僅回傳遮罩資訊；若開啟 DEBUG，會回傳 code 方便測試。
    mask = (acc[:3] + "***" + acc[-2:]) if "@" not in acc else (acc.split("@")[0][:1] + "***@" + acc.split("@")[-1])
    resp = {"ok": True, "sent_to": mask, "ttl": OTP_TTL_SEC, "cooldown": OTP_RESEND_COOLDOWN}
    if OTP_DEBUG_RETURN_CODE:
        resp["debug_code"] = code
    return resp

@app.post("/auth/otp/verify")
def otp_verify(req: OTPVerify):
    r = get_redis()
    purpose = (req.purpose or "login").strip().lower()
    acc = _norm_account(req.account)
    if not acc or not req.code:
        raise HTTPException(status_code=400, detail="缺少 account 或 code")
    acc_hash = _hash_key(acc)
    keys = _otp_keys(purpose, acc_hash)

    # 鎖定檢查
    if r.get(keys["lock"]):
        raise HTTPException(status_code=429, detail="已鎖定，請稍後再試")

    raw = r.get(keys["code"])
    if not raw:
        raise HTTPException(status_code=400, detail="驗證碼已過期或不存在")
    try:
        payload = json.loads(raw)
    except Exception:
        payload = {"code": raw, "attempts_left": int(r.get(keys["tries"]) or 0)}

    attempts_left = int(r.get(keys["tries"]) or payload.get("attempts_left") or 0)
    if attempts_left <= 0:
        # 設定鎖定 10 分鐘
        r.setex(keys["lock"], 600, "1")
        r.delete(keys["code"], keys["tries"], keys["cooldown"])
        raise HTTPException(status_code=429, detail="嘗試次數過多，已鎖定")

    if req.code.strip() != str(payload.get("code", "")).strip():
        attempts_left -= 1
        r.setex(keys["tries"], max(r.ttl(keys["code"]), 1), str(attempts_left))
        raise HTTPException(status_code=400, detail=f"驗證碼錯誤，剩餘 {attempts_left} 次")

    # 通過：簽發一次性 ticket（10 分鐘）供後續綁定登入/註冊
    r.delete(keys["tries"], keys["cooldown"])
    r.delete(keys["code"])  # 單次使用
    ticket = secrets.token_urlsafe(24)
    r.setex(f"otp:ticket:{ticket}", 600, json.dumps({"account": acc, "purpose": purpose}))
    return {"ok": True, "ticket": ticket, "expires_in": 600}

@app.post("/auth/otp/consume")
def otp_consume(ticket: str):
    """用 ticket 兌換，完成下一步（例如登入/註冊）。這裡僅驗證 ticket 並刪除。"""
    r = get_redis()
    raw = r.get(f"otp:ticket:{ticket}")
    if not raw:
        raise HTTPException(status_code=400, detail="ticket 無效或已過期")
    r.delete(f"otp:ticket:{ticket}")
    try:
        data = json.loads(raw)
    except Exception:
        data = {"account": None, "purpose": None}
    return {"ok": True, "account": data.get("account"), "purpose": data.get("purpose")}

# ===== 路線站點管理 API =====

class StationCreate(BaseModel):
    route_id: int
    route_name: str
    direction: str
    stop_name: str
    latitude: float
    longitude: float
    stop_order: int
    eta_from_start: int
    address: Optional[str] = None

class StationUpdate(BaseModel):
    route_id: int
    route_name: str
    direction: str
    stop_name: str
    latitude: float
    longitude: float
    stop_order: int
    eta_from_start: int
    address: Optional[str] = None

@app.post("/api/route-stations/create")
def create_route_station(station: StationCreate):
    """創建新的路線站點"""
    try:
        # 先檢查是否已存在相同的記錄
        check_sql = f"""
        SELECT COUNT(*) as count FROM bus_route_stations 
        WHERE route_name = '{station.route_name}' 
        AND direction = '{station.direction}' 
        AND stop_name = '{station.stop_name}' 
        AND stop_order = {station.stop_order}
        """
        
        check_result = MySQL_Run(check_sql)
        if check_result and check_result[0]['count'] > 0:
            raise HTTPException(status_code=400, detail="該站點已存在，請檢查站點名稱和順序")

        # 使用字串格式化而不是參數化查詢，因為 MySQL_Run 不支持參數
        sql = f"""
        INSERT INTO bus_route_stations 
        (route_id, route_name, direction, stop_name, latitude, longitude, stop_order, eta_from_start, address)
        VALUES ({station.route_id}, '{station.route_name}', '{station.direction}', '{station.stop_name}', 
                {station.latitude}, {station.longitude}, {station.stop_order}, {station.eta_from_start}, 
                '{station.address if station.address else ""}')
        """
        
        MySQL_Run(sql)
        return {"message": "站點創建成功", "ok": True}
    except HTTPException:
        raise
    except Exception as e:
        print(f"創建站點失敗: {str(e)}")  # 加入日誌
        raise HTTPException(status_code=500, detail=f"創建站點失敗: {str(e)}")

@app.put("/api/route-stations/update")
def update_route_station(station: StationUpdate):
    """更新路線站點"""
    try:
        # 檢查是否會造成重複記錄（在同一個路線和方向中）
        check_sql = f"""
        SELECT COUNT(*) as count FROM bus_route_stations
        WHERE route_name = '{station.route_name}'
        AND direction = '{station.direction}'
        AND stop_order = {station.stop_order}
        AND NOT (stop_name = '{station.stop_name}')
        """

        check_result = MySQL_Run(check_sql)
        if check_result and check_result[0]['count'] > 0:
            # 如果有衝突，需要重新排列順序
            # 先將衝突的記錄順序往後移
            update_conflict_sql = f"""
            UPDATE bus_route_stations
            SET stop_order = stop_order + 1
            WHERE route_name = '{station.route_name}'
            AND direction = '{station.direction}'
            AND stop_order >= {station.stop_order}
            AND stop_name != '{station.stop_name}'
            ORDER BY stop_order DESC
            """
            MySQL_Run(update_conflict_sql)

        # 更新記錄
        sql = f"""
        UPDATE bus_route_stations
        SET route_name = '{station.route_name}', direction = '{station.direction}',
            stop_name = '{station.stop_name}', latitude = {station.latitude},
            longitude = {station.longitude}, stop_order = {station.stop_order},
            eta_from_start = {station.eta_from_start},
            address = '{station.address if station.address else ""}'
        WHERE route_name = '{station.route_name}' AND direction = '{station.direction}'
        AND stop_name = '{station.stop_name}'
        """

        MySQL_Run(sql)
        return {"message": "站點更新成功", "ok": True}
    except Exception as e:
        print(f"更新站點失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新站點失敗: {str(e)}")

@app.delete("/api/route-stations/delete")
def delete_route_station(route_id: int, stop_order: int):
    """刪除路線站點"""
    try:
        # 先檢查記錄是否存在
        check_sql = f"SELECT COUNT(*) as count FROM bus_route_stations WHERE route_id = {route_id} AND stop_order = {stop_order}"
        check_result = MySQL_Run(check_sql)
        
        if not check_result or check_result[0]['count'] == 0:
            raise HTTPException(status_code=404, detail="找不到要刪除的站點")
        
        sql = f"DELETE FROM bus_route_stations WHERE route_id = {route_id} AND stop_order = {stop_order}"
        
        MySQL_Run(sql)
        return {"message": "站點刪除成功", "ok": True}
    except HTTPException:
        raise
    except Exception as e:
        print(f"刪除站點失敗: {str(e)}")  # 加入日誌
        raise HTTPException(status_code=500, detail=f"刪除站點失敗: {str(e)}")

@app.get("/api/routes")
def get_all_routes():
    """獲取所有路線（從 bus_route_stations 表中提取）"""
    try:
        # 從 bus_route_stations 表中獲取所有不同的路線名稱和對應的 route_id
        rows = MySQL_Run("""
            SELECT DISTINCT route_id, route_name 
            FROM bus_route_stations 
            ORDER BY route_id
        """)
        
        # 如果某些路線沒有 route_id，我們給它們分配一個
        routes = []
        for row in rows:
            if row['route_id'] is None or row['route_id'] == '':
                # 為沒有 route_id 的路線分配一個基於名稱的 ID
                route_name = row['route_name']
                if route_name == '市民小巴-行動遊花蓮':
                    route_id = 4
                else:
                    # 為其他沒有 route_id 的路線生成 ID
                    route_id = hash(route_name) % 10000  # 簡單的雜湊函數
                routes.append({'route_id': route_id, 'route_name': route_name})
            else:
                routes.append({'route_id': row['route_id'], 'route_name': row['route_name']})
        
        return {"routes": routes}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"獲取路線失敗: {str(e)}")

class RouteStationsFilter(BaseModel):
    route_id: Optional[int] = None
    direction: Optional[str] = None

@app.get("/api/route-stations")
def get_route_stations(
    route_id: Optional[int] = None,
    direction: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 20
):
    """獲取篩選後的路線站點（支援分頁和搜尋）"""
    try:
        # 建構查詢條件
        conditions = []
        params = []
        
        if route_id:
            conditions.append("route_id = %s")
            params.append(route_id)
        
        if direction:
            conditions.append("direction = %s")
            params.append(direction)
        
        if search:
            conditions.append("(stop_name LIKE %s OR address LIKE %s)")
            params.extend([f"%{search}%", f"%{search}%"])
        
        # 建構 WHERE 子句
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        # 計算總數
        count_sql = f"SELECT COUNT(*) as total FROM bus_route_stations WHERE {where_clause}"
        count_result = MySQL_Run(count_sql, tuple(params) if params else ())
        total = count_result[0]['total'] if count_result else 0
        
        # 計算分頁
        offset = (page - 1) * page_size
        
        # 建構主要查詢
        sql = f"""
        SELECT * FROM bus_route_stations 
        WHERE {where_clause} 
        ORDER BY route_id, stop_order 
        LIMIT %s OFFSET %s
        """
        
        params.extend([page_size, offset])
        rows = MySQL_Run(sql, tuple(params))
        
        return {
            "stations": rows,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }
    except Exception as e:
        print(f"獲取站點失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=f"獲取站點失敗: {str(e)}")

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8950, reload=True)
