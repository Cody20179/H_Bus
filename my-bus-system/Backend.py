from fastapi import FastAPI, HTTPException, Depends, status, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import create_engine, Column, Integer, String, TIMESTAMP, Boolean, ForeignKey, text, func, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, Literal, List, Tuple, Dict, Set
import bcrypt
import os
from dotenv import load_dotenv
from collections import defaultdict
from calendar import monthrange
from datetime import datetime, timezone, timedelta, date
import pytz
from MySQL import MySQL_Run
import pandas as pd
import uvicorn
import hashlib
import json
import secrets
import string
import io
import zipfile
import qrcode
import logging
from pathlib import Path
try:
    import redis  # redis-py
except Exception:  # pragma: no cover
    redis = None

BASE_DIR = Path(__file__).resolve().parent
DIST_DIR = BASE_DIR / 'dist'
INDEX_FILE = DIST_DIR / 'index.html'
logger = logging.getLogger('uvicorn.error')

# Setting Taipei time zone
TAIPEI_TZ = pytz.timezone('Asia/Taipei')

def get_taipei_time():
    """Obtain Taipei time"""
    return datetime.now(TAIPEI_TZ)

def get_taiwan_datetime():
    """Get the datetime object of Taiwan time (without time zone information, for database use)"""
    return datetime.now(TAIPEI_TZ).replace(tzinfo=None)

# ===== Appointment analysis shared tool =====
RESERVATION_STATUS_PRIORITY = [
    "pending",
    "approved",
    "assigned",
    "in_progress",
    "completed",
    "canceled",
    "rejected",
    "failed",
]

REVIEW_STATUS_PRIORITY = [
    "pending",
    "approved",
    "rejected",
    "canceled",
]


def _add_month(value: date) -> date:
    if value.month == 12:
        return date(value.year + 1, 1, 1)
    return date(value.year, value.month + 1, 1)


def _month_last_day(value: date) -> date:
    return date(value.year, value.month, monthrange(value.year, value.month)[1])


def _parse_month_string(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m").date().replace(day=1)
    except Exception:
        raise HTTPException(status_code=400, detail="The month format must be YYYY-MM")


def _normalize_datetime(value) -> Optional[datetime]:
    if isinstance(value, datetime):
        if value.tzinfo:
            return value.astimezone(TAIPEI_TZ).replace(tzinfo=None)
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return None


def _generate_week_ranges(target_year: int, target_month: int) -> List[Dict[str, date]]:
    last_day = monthrange(target_year, target_month)[1]
    ranges: List[Dict[str, date]] = []
    day = 1
    week_index = 1
    while day <= last_day:
        start_date = date(target_year, target_month, day)
        end_day = min(day + 6, last_day)
        end_date = date(target_year, target_month, end_day)
        ranges.append({
            "week": week_index,
            "start": start_date,
            "end": end_date,
            "label": f"{start_date.month}/{start_date.day}-{end_date.month}/{end_date.day}",
        })
        day += 7
        week_index += 1
    return ranges


def _normalize_status(value, fallback: str = 'unknown') -> str:
    if value is None:
        return fallback
    value_str = str(value).strip()
    if not value_str:
        return fallback
    lower = value_str.lower()
    if lower in {"# 角色管理 API", 'none', 'null'}:
        return fallback
    return lower


def _sort_status_keys(keys: Set[str], priority: List[str]) -> List[str]:
    if not keys:
        return []
    working = set(keys)
    unknown_present = 'unknown' in working
    if unknown_present:
        working.remove('unknown')
    ordered = [item for item in priority if item in working]
    remainder = sorted(working - set(ordered))
    result = ordered + remainder
    if unknown_present:
        result.append('unknown')
    return result


def _fetch_reservations_in_range(start_dt: datetime, end_dt: datetime):
    sql = """
        SELECT
            COALESCE(created_at, booking_time) AS event_time,
            reservation_status,
            review_status
        FROM reservation
        WHERE (
            (created_at IS NOT NULL AND created_at >= %s AND created_at < %s)
            OR (created_at IS NULL AND booking_time IS NOT NULL AND booking_time >= %s AND booking_time < %s)
        )
    """
    return MySQL_Run(sql, (start_dt, end_dt, start_dt, end_dt)) or []


def _ensure_datetime_window(start: date, end: date) -> Tuple[datetime, datetime]:
    start_dt = datetime.combine(start, datetime.min.time())
    end_dt = datetime.combine(end + timedelta(days=1), datetime.min.time())
    return start_dt, end_dt


# Loading environment variables
load_dotenv()

# MySQL archive settings
DATABASE_URL = f"mysql+pymysql://root:109109@192.168.0.126:3307/bus_system"
engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ===== OTP/Verification Code: Redis Settings and Tools =====
REDIS_URL = os.getenv("HBUS_REDIS_URL", os.getenv("REDIS_URL", "redis://localhost:6379/0"))
OTP_TTL_SEC = int(os.getenv("HBUS_OTP_TTL_SEC", "300"))           # Verification code is valid for 5 minutes
OTP_LEN = int(os.getenv("HBUS_OTP_LEN", "6"))                      # Verification code length 6
OTP_MAX_ATTEMPTS = int(os.getenv("HBUS_OTP_MAX_ATTEMPTS", "5"))   # Maximum number of attempts 5
OTP_RESEND_COOLDOWN = int(os.getenv("HBUS_OTP_RESEND_COOLDOWN", "60"))  # Resend cooldown 60 seconds
OTP_RL_DEST_MAX_10MIN = int(os.getenv("HBUS_OTP_RL_DEST_MAX_10MIN", "3"))  # Up to 3 times per purpose 10 minutes
OTP_RL_IP_MAX_1H = int(os.getenv("HBUS_OTP_RL_IP_MAX_1H", "10"))          # Up to 10 times per IP 1 hour
OTP_DEBUG_RETURN_CODE = os.getenv("HBUS_OTP_DEBUG", "false").lower() in {"1", "true", "yes"}
OTP_FORCE_CODE = os.getenv("HBUS_OTP_FORCE_CODE")  # e.g. "123456" for easy testing
OTP_LOG_ENABLE = os.getenv("HBUS_OTP_LOG", "true").lower() in {"1", "true", "yes"}
OTP_LOG_FILE = os.getenv(
    "HBUS_OTP_LOG_FILE",
    os.path.join(os.path.dirname(__file__), "otp_codes.txt"),
)

# Database model (matches actual table structure)
class User(Base):
    __tablename__ = "users"
    user_id = Column(Integer, primary_key=True, autoincrement=True)
    line_id = Column(String(100), unique=True)
    username = Column(String(100))
    password = Column(String(255))  # Hash password
    email = Column(String(255))
    phone = Column(String(20))
    # Use Taiwan time (without time zone information) to ensure consistency with requirements
    created_at = Column(TIMESTAMP, default=get_taiwan_datetime)
    updated_at = Column(TIMESTAMP, default=get_taiwan_datetime, onupdate=get_taiwan_datetime)
    last_login = Column(TIMESTAMP, nullable=True)
    status = Column(Enum('active', 'inactive'), default='active')
    # Consistent with the database and compatible with historical data 'None'
    reservation_status = Column(
        Enum('no_reservation', 'pending', 'approved', 'rejected', 'completed', 'None'),
        default='no_reservation'
    )  # Appointment status
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
            return -2  # Redis: key does not exist
        v, exp = self._store[key]
        if exp is None:
            return -1  # No TTL
        remain = int(round(exp - self._now.time()))
        if remain <= 0:
            self._store.pop(key, None)
            return -2
        return remain

# Pydantic model (updated to match table structure)
class UserCreate(BaseModel):
    line_id: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None  # Plain text passwords will be made up in the API
    email: Optional[str] = None
    phone: Optional[str] = None
    status: Optional[Literal["active", "inactive"]] = 'active'
    reservation_status: Optional[Literal["no_reservation", "pending", "approved", "rejected", "completed"]] = 'no_reservation'
    preferences: Optional[str] = None
    privacy_settings: Optional[str] = None


class UserUpdate(BaseModel):
    line_id: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None  # Plain text passwords will be made up in the API
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
    direction: Literal["unidirectional", "Two-way"]
    start_stop: Optional[str] = None
    end_stop: Optional[str] = None
    status: int
    created_at: Optional[datetime] = None

# ====== Request model ======
class RouteStationsQuery(BaseModel):
    route_id: int = Field(..., ge=1)
    # Optional: If you want to filter out/return/single-way
    direction: Optional[Literal["Going", "Return", "One Way"]] = None

# ====== Response model (align your actual column) ======
class StationOut(BaseModel):
    route_id: int
    route_name: str
    direction: Optional[str] = None
    stop_name: str
    latitude: float
    longitude: float
    eta_from_start: Optional[int] = None  # Minutes (or seconds) depends on your DB definition
    stop_order: Optional[int] = None
    created_at: Optional[datetime] = None

# ======= Reservation Model ======
class ReservationCreate(BaseModel):
    user_id: Optional[int] = None
    booking_time: Optional[datetime] = None
    booking_number: Optional[int] = None
    booking_start_station_name: Optional[str] = None
    booking_end_station_name: Optional[str] = None
    payment_method: Optional[str] = None
    payment_record: Optional[str] = None
    payment_status: Optional[Literal['pending','paid','failed','refunded']] = 'pending'
    review_status: Optional[Literal['pending','approved','rejected','canceled']] = 'pending'
    dispatch_status: Optional[Literal['not_assigned','assigned']] = 'not_assigned'

class ReservationUpdate(BaseModel):
    user_id: Optional[int] = None
    booking_time: Optional[datetime] = None
    booking_number: Optional[int] = None
    booking_start_station_name: Optional[str] = None
    booking_end_station_name: Optional[str] = None
    payment_method: Optional[str] = None
    payment_record: Optional[str] = None
    payment_status: Optional[Literal['pending','paid','failed','refunded']] = None
    review_status: Optional[Literal['pending','approved','rejected','canceled']] = None
    dispatch_status: Optional[Literal['not_assigned','assigned']] = None


class CarResourceCreate(BaseModel):
    car_licence: str = Field(..., min_length=1, max_length=20)
    max_passengers: int = Field(..., ge=1)
    car_status: Optional[Literal['service','paused','maintenance','retired']] = 'service'
    commission_date: Optional[date] = None
    last_service_date: Optional[date] = None

class CarResourceUpdate(BaseModel):
    car_licence: Optional[str] = Field(None, min_length=1, max_length=20)
    max_passengers: Optional[int] = Field(None, ge=1)
    car_status: Optional[Literal['service','paused','maintenance','retired']] = None
    commission_date: Optional[date] = None
    last_service_date: Optional[date] = None

class QrCodeRequest(BaseModel):
    base_url: HttpUrl
    route_id: int = Field(..., gt=0, le=10000)
    stop_count: int = Field(..., gt=0, le=200)
    output_prefix: Optional[str] = Field(None, max_length=64)

# Dependency injection
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Tool functions
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    """Get the current user from Bearer token"""
    token = credentials.credentials
    
    # Simple token parsing (format: admin_{user_id}_token)
    if not token.startswith('admin_') or not token.endswith('_token'):
        raise HTTPException(status_code=401, detail="Invalid token format")
    
    try:
        # Extract user ID from token
        user_id = int(token.split('_')[1])
        user = db.query(AdminUser).filter(AdminUser.admin_id == user_id).first()
        if not user:
            raise HTTPException(status_code=401, detail="The user does not exist")
        return user
    except (ValueError, IndexError):
        raise HTTPException(status_code=401, detail="Invalid token")

def check_permission(user, permission: str, db: Session) -> bool:
    role = db.query(AdminRole).filter(AdminRole.role_id == user.role_id).first()
    if not role:
        return False
    permissions = role.permissions.split(',') if role.permissions else []  # Assume permissions are comma separated
    return permission in permissions

def get_role_by_id(db: Session, role_id: Optional[int]) -> Optional[AdminRole]:
    if role_id is None:
        return None
    return db.query(AdminRole).filter(AdminRole.role_id == role_id).first()

def get_role_name(db: Session, role_id: Optional[int]) -> Optional[str]:
    role = get_role_by_id(db, role_id)
    return (role.role_name if role else None)

def current_role_name(db: Session, current_user: AdminUser) -> Optional[str]:
    role = get_role_by_id(db, current_user.role_id)
    return role.role_name if role else None

# Redis related helper functions
def get_redis():
    if redis is None:
        # If there is no redis module, fall back to memory version (for development only)
        if not hasattr(app.state, "redis") or app.state.redis is None:
            print("[OTP] Redis module is not installed, use InMemoryRedis instead (for development)")
            app.state.redis = InMemoryRedis()
        return app.state.redis
    if not hasattr(app.state, "redis") or app.state.redis is None:
        try:
            app.state.redis = redis.Redis.from_url(REDIS_URL, decode_responses=True)
            app.state.redis.ping()
        except Exception as e:  # pragma: no cover
            # Failed to InMemoryRedis: Developing and testing without any obstacles
            print(f"[OTP] Redis 連線失敗，改用 InMemoryRedis：{e}")
            app.state.redis = InMemoryRedis()
    return app.state.redis

def _norm_account(acc: str) -> str:
    return (acc or "# 角色管理 API").strip().lower()

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
    return "# 角色管理 API".join(secrets.choice(string.digits) for _ in range(length))

# FastAPI Application
app = FastAPI()
app.mount('/assets', StaticFiles(directory=DIST_DIR / 'assets', check_dir=False), name='assets')

# Dynamic CORS setting function
def is_allowed_origin(origin: str) -> bool:
    """Check if the source is allowed"""
    allowed_patterns = [
        "http://localhost:5173",
        "http://127.0.0.1:5173", 
        "http://192.168.0.",  # 192.168.0.x network segment
        "http://192.168.1.",  # 192.168.1.x network segment
        "http://10.0.0.",     # 10.0.0.x network segment
        ":5173"               # Any address using port 5173
    ]
    
    for pattern in allowed_patterns:
        if pattern in origin:
            return True
    return False

# Join CORS settings
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+|10\.\d+\.\d+\.\d+):(5173|3000|8080)$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Login API
@app.post("/auth/login")
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(AdminUser).filter(AdminUser.username == request.username).first()
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid voucher")
    
    # Check user status
    if user.status != 'active':
        status_messages = {
            'inactive': "The account has been disabled, please contact the administrator"
        }
        raise HTTPException(status_code=401, detail=status_messages.get(user.status, "Account status abnormal"))
    
    # Verify password
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid voucher")
    
    # Update last_login for Taipei time
    user.last_login = get_taiwan_datetime()
    db.commit()
    
    # Get role information
    role = db.query(AdminRole).filter(AdminRole.role_id == user.role_id).first()
    
    # Return the expected format of the front-end
    return {
        "access_token": f"admin_{user.admin_id}_token", # Simplified token
        "token_type": "bearer",
        "user_id": user.admin_id,
        "username": user.username,
        "role": role.role_name if role else None
    }

# Dashboard Statistics API
@app.get("/api/dashboard/member-stats")
def get_member_statistics(db: Session = Depends(get_db)):
    """
    取得會員統計資料
    """
    try:
        # Calculate the total number of members
        total_members = db.query(User).count()
        
        # Calculate the number of active members (status = 'active')
        active_members = db.query(User).filter(User.status == 'active').count()
        
        # Calculate the number of new members this month (using Taipei time zone)
        taipei_now = get_taipei_time()
        start_of_month = taipei_now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        # Convert to a time zone-free datetime for database query
        start_of_month_naive = start_of_month.replace(tzinfo=None)
        
        # First check whether the User model has created_at column
        try:
            new_members_this_month = db.query(User).filter(User.created_at >= start_of_month_naive).count()
        except AttributeError:
            # If there is no created_at field, set to 0
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

# Member Growth Trends API
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
        
        # Determine the grouping method according to the number of days
        if days == 1:
            # Last 1 day: Grouped by hour
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
            # Last 7 days: Grouped by day
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
            # Last 30 days: Grouped by week
            growth_data = []
            cumulative_count = db.query(User).filter(
                User.created_at < start_date_naive
            ).count()
            
            # Divided into 5 weeks, 6 days a week
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
        
        # Calculate statistics
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
        # Return preset information to avoid front-end errors
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

# Appointment Statistics (this month/today/status)
@app.get("/api/dashboard/reservation-stats")
def get_reservation_stats(db: Session = Depends(get_db)):
    """
    回傳預約統計：
    - this_month: 本月建立的預約數（以 created_at 為主，若無則以 booking_time）
    - today_new: 今日新建立的預約數
    - pending: 審核中筆數（review_status='pending'）
    - completed: 已完成筆數（reservation_status='completed'）
    - last_month: 上月建立的預約數
    - growth_rate: 相較上月成長率（%）
    """
    try:
        now = get_taipei_time()
        # The first day of this month is 00:00
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        # Next month's first day 00:00
        if start_of_month.month == 12:
            next_month = start_of_month.replace(year=start_of_month.year + 1, month=1)
        else:
            next_month = start_of_month.replace(month=start_of_month.month + 1)
        # Today 00:00
        start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # The first day of last month ends
        if start_of_month.month == 1:
            last_month_start = start_of_month.replace(year=start_of_month.year - 1, month=12)
        else:
            last_month_start = start_of_month.replace(month=start_of_month.month - 1)

        # Convert to naive datetime (remove tzinfo)
        som = start_of_month.replace(tzinfo=None)
        next_m = next_month.replace(tzinfo=None)
        today0 = start_of_today.replace(tzinfo=None)
        lm_start = last_month_start.replace(tzinfo=None)

        # Priority is used to calculate with created_at. If the data does not have created_at, fallback is used to booking_time
        def _count_between(col: str, start_dt, end_dt):
            sql = f"SELECT COUNT(*) as c FROM reservation WHERE {col} >= %s AND {col} < %s"
            try:
                res = MySQL_Run(sql, (start_dt, end_dt))
                return int(res[0]['c']) if res else 0
            except Exception:
                return 0

        # Try creating_at
        this_month = _count_between('created_at', som, next_m)
        today_new = _count_between('created_at', today0, now.replace(tzinfo=None))
        last_month = _count_between('created_at', lm_start, som)

        # If all are 0, use booking_time instead
        if this_month == 0 and last_month == 0 and today_new == 0:
            this_month = _count_between('booking_time', som, next_m)
            today_new = _count_between('booking_time', today0, now.replace(tzinfo=None))
            last_month = _count_between('booking_time', lm_start, som)

        # Status statistics
        try:
            pending = MySQL_Run("SELECT COUNT(*) as c FROM reservation WHERE review_status = 'pending'")[0]['c']
        except Exception:
            pending = 0
        try:
            completed = MySQL_Run("SELECT COUNT(*) as c FROM reservation WHERE reservation_status = 'completed'")[0]['c']
        except Exception:
            completed = 0

        growth_rate = 0.0
        try:
            if last_month > 0:
                growth_rate = round((this_month - last_month) / last_month * 100.0, 2)
        except Exception:
            growth_rate = 0.0

        return {
            "success": True,
            "data": {
                "this_month": this_month,
                "today_new": today_new,
                "pending": pending,
                "completed": completed,
                "last_month": last_month,
                "growth_rate": growth_rate,
            },
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "data": {
                "this_month": 0,
                "today_new": 0,
                "pending": 0,
                "completed": 0,
                "last_month": 0,
                "growth_rate": 0.0,
            },
        }

@app.get("/api/dashboard/reservations/trend")
def get_reservation_trend(
    mode: Literal['monthly', 'range'] = Query('monthly'),
    year: Optional[int] = None,
    month: Optional[int] = None,
    start_month: Optional[str] = Query(None, description="Starting month YYYY-MM"),
    end_month: Optional[str] = Query(None, description="End month YYYY-MM"),
):
    try:
        mode_value = (mode or 'monthly').lower()
        if mode_value not in ('monthly', 'range'):
            raise HTTPException(status_code=400, detail="mode only supports monthly or range")

        now = get_taipei_time()

        if mode_value == 'monthly':
            target_year = year or now.year
            target_month = month or now.month
            if target_month < 1 or target_month > 12:
                raise HTTPException(status_code=400, detail="month needs to be between 1-12")

            start_date = date(target_year, target_month, 1)
            last_day = monthrange(target_year, target_month)[1]
            end_date = date(target_year, target_month, last_day)
            start_dt, end_dt = _ensure_datetime_window(start_date, end_date)

            rows = _fetch_reservations_in_range(start_dt, end_dt)
            weeks = _generate_week_ranges(target_year, target_month)
            week_totals = [0 for _ in weeks]
            for row in rows:
                event_dt = _normalize_datetime(row.get('event_time'))
                if not event_dt:
                    continue
                event_date = event_dt.date()
                if event_date < start_date or event_date > end_date:
                    continue
                diff = (event_date - start_date).days
                index = min(diff // 7, len(weeks) - 1)
                week_totals[index] += 1

            total = sum(week_totals)
            weeks_output = []
            for info, count in zip(weeks, week_totals):
                weeks_output.append({
                    "week": info['week'],
                    "label": info['label'],
                    "start_date": info['start'].isoformat(),
                    "end_date": info['end'].isoformat(),
                    "count": count,
                })

            return {
                "success": True,
                "data": {
                    "mode": "monthly",
                    "year": target_year,
                    "month": target_month,
                    "weeks": weeks_output,
                    "total": total,
                },
            }

        # range mode
        if not start_month or not end_month:
            raise HTTPException(status_code=400, detail="range mode requires start_month and end_month")

        start_date = _parse_month_string(start_month)
        end_marker = _parse_month_string(end_month)
        if end_marker < start_date:
            raise HTTPException(status_code=400, detail="end_month cannot be earlier than start_month")

        end_date = _month_last_day(end_marker)
        start_dt, end_dt = _ensure_datetime_window(start_date, end_date)
        rows = _fetch_reservations_in_range(start_dt, end_dt)

        month_totals: Dict[str, int] = defaultdict(int)
        for row in rows:
            event_dt = _normalize_datetime(row.get('event_time'))
            if not event_dt:
                continue
            event_date = event_dt.date()
            if event_date < start_date or event_date > end_date:
                continue
            key = event_date.strftime("%Y-%m")
            month_totals[key] += 1

        months_output = []
        total = 0
        cursor = start_date
        while cursor <= end_date:
            key = cursor.strftime("%Y-%m")
            count = month_totals.get(key, 0)
            months_output.append({
                "month": key,
                "label": f"{cursor.year}年{cursor.month}月",
                "count": count,
            })
            total += count
            cursor = _add_month(cursor)

        return {
            "success": True,
            "data": {
                "mode": "range",
                "start_month": start_date.strftime("%Y-%m"),
                "end_month": end_date.strftime("%Y-%m"),
                "months": months_output,
                "total": total,
            },
        }
    except HTTPException:
        raise
    except Exception as exc:
        print("get_reservation_trend error:", exc)
        raise HTTPException(status_code=500, detail="An error occurred while retrieving appointment trend data")


@app.get("/api/dashboard/reservations/status")
def get_reservation_status_distribution(
    mode: Literal['monthly', 'range'] = Query('monthly'),
    year: Optional[int] = None,
    month: Optional[int] = None,
    start_month: Optional[str] = Query(None, description="Date format YYYY-MM"),
    end_month: Optional[str] = Query(None, description="Date format YYYY-MM"),
):
    try:
        mode_value = (mode or 'monthly').lower()
        if mode_value not in ('monthly', 'range'):
            raise HTTPException(status_code=400, detail="Mode parameters only support monthly or range")

        now = get_taipei_time()

        if mode_value == 'monthly':
            target_year = year or now.year
            target_month = month or now.month
            if target_month < 1 or target_month > 12:
                raise HTTPException(status_code=400, detail="month needs to be between 1-12")

            start_date = date(target_year, target_month, 1)
            last_day = monthrange(target_year, target_month)[1]
            end_date = date(target_year, target_month, last_day)
            start_dt, end_dt = _ensure_datetime_window(start_date, end_date)

            rows = _fetch_reservations_in_range(start_dt, end_dt)
            weeks = _generate_week_ranges(target_year, target_month)
            week_buckets: List[Dict[str, object]] = []
            for _ in weeks:
                week_buckets.append({
                    "reservation_status": defaultdict(int),
                    "review_status": defaultdict(int),
                    "total": 0,
                })

            reservation_keys: Set[str] = set()
            review_keys: Set[str] = set()

            for row in rows:
                event_dt = _normalize_datetime(row.get('event_time'))
                if not event_dt:
                    continue
                event_date = event_dt.date()
                if event_date < start_date or event_date > end_date:
                    continue
                diff = (event_date - start_date).days
                index = min(diff // 7, len(weeks) - 1)
                bucket = week_buckets[index]
                bucket['total'] = bucket['total'] + 1

                r_status = _normalize_status(row.get('reservation_status'))
                rv_status = _normalize_status(row.get('review_status'))
                bucket['reservation_status'][r_status] += 1
                bucket['review_status'][rv_status] += 1
                reservation_keys.add(r_status)
                review_keys.add(rv_status)

            reservation_key_order = _sort_status_keys(reservation_keys, RESERVATION_STATUS_PRIORITY)
            review_key_order = _sort_status_keys(review_keys, REVIEW_STATUS_PRIORITY)

            weeks_output = []
            total = 0
            for info, bucket in zip(weeks, week_buckets):
                total += bucket['total']
                weeks_output.append({
                    "week": info['week'],
                    "label": info['label'],
                    "start_date": info['start'].isoformat(),
                    "end_date": info['end'].isoformat(),
                    "total": bucket['total'],
                    "reservation_status": {key: bucket['reservation_status'].get(key, 0) for key in reservation_key_order},
                    "review_status": {key: bucket['review_status'].get(key, 0) for key in review_key_order},
                })

            return {
                "success": True,
                "data": {
                    "mode": "monthly",
                    "year": target_year,
                    "month": target_month,
                    "weeks": weeks_output,
                    "total": total,
                    "reservation_status_keys": reservation_key_order,
                    "review_status_keys": review_key_order,
                },
            }

        # range mode
        if not start_month or not end_month:
            raise HTTPException(status_code=400, detail="range mode requires start_month and end_month")

        start_date = _parse_month_string(start_month)
        end_marker = _parse_month_string(end_month)
        if end_marker < start_date:
            raise HTTPException(status_code=400, detail="The end month cannot be earlier than the beginning month")

        end_date = _month_last_day(end_marker)
        start_dt, end_dt = _ensure_datetime_window(start_date, end_date)
        rows = _fetch_reservations_in_range(start_dt, end_dt)

        month_stats: Dict[str, Dict[str, object]] = {}
        reservation_keys: Set[str] = set()
        review_keys: Set[str] = set()

        for row in rows:
            event_dt = _normalize_datetime(row.get('event_time'))
            if not event_dt:
                continue
            event_date = event_dt.date()
            if event_date < start_date or event_date > end_date:
                continue
            key = event_date.strftime("%Y-%m")
            stats = month_stats.get(key)
            if stats is None:
                stats = {
                    "reservation_status": defaultdict(int),
                    "review_status": defaultdict(int),
                    "total": 0,
                }
                month_stats[key] = stats

            stats['total'] = stats['total'] + 1
            r_status = _normalize_status(row.get('reservation_status'))
            rv_status = _normalize_status(row.get('review_status'))
            stats['reservation_status'][r_status] += 1
            stats['review_status'][rv_status] += 1
            reservation_keys.add(r_status)
            review_keys.add(rv_status)

        reservation_key_order = _sort_status_keys(reservation_keys, RESERVATION_STATUS_PRIORITY)
        review_key_order = _sort_status_keys(review_keys, REVIEW_STATUS_PRIORITY)

        months_output = []
        total = 0
        cursor = start_date
        while cursor <= end_date:
            key = cursor.strftime("%Y-%m")
            stats = month_stats.get(key)
            if stats is None:
                stats = {
                    "reservation_status": defaultdict(int),
                    "review_status": defaultdict(int),
                    "total": 0,
                }
            total += stats['total']
            months_output.append({
                "month": key,
                "label": f"{cursor.year}年{cursor.month}月",
                "total": stats['total'],
                "reservation_status": {item: stats['reservation_status'].get(item, 0) for item in reservation_key_order},
                "review_status": {item: stats['review_status'].get(item, 0) for item in review_key_order},
            })
            cursor = _add_month(cursor)

        return {
            "success": True,
            "data": {
                "mode": "range",
                "start_month": start_date.strftime("%Y-%m"),
                "end_month": end_date.strftime("%Y-%m"),
                "months": months_output,
                "total": total,
                "reservation_status_keys": reservation_key_order,
                "review_status_keys": review_key_order,
            },
        }
    except HTTPException:
        raise
    except Exception as exc:
        print("get_reservation_status_distribution error:", exc)
        raise HTTPException(status_code=500, detail="An error occurred while obtaining the appointment status information")


# Route statistics (total/enabled/site coverage)
@app.get("/api/dashboard/route-stats")
def get_route_stats():
    """
    回傳路線統計：
    - total: bus_routes_total 總路線數
    - active: 啟用路線數（status = 1）
    - inactive: 停用路線數
    - on_time_rate: 以有站點的路線比率作為近似值（DISTINCT route_id / total）
    """
    try:
        t_total = MySQL_Run("SELECT COUNT(*) as c FROM bus_routes_total")[0]['c']
        try:
            t_active = MySQL_Run("SELECT COUNT(*) as c FROM bus_routes_total WHERE status = 1")[0]['c']
        except Exception:
            t_active = 0
        inactive = max(t_total - t_active, 0)
        try:
            with_stations = MySQL_Run("SELECT COUNT(DISTINCT route_id) as c FROM bus_route_stations")[0]['c']
        except Exception:
            with_stations = 0
        #rate = round((with_stations / max(t_total, 1)) * 100.0, 1)
        return {
            "success": True,
            "data": {
                "total": int(t_total),
                "active": int(t_active),
                "inactive": int(inactive),
                #"on_time_rate": rate,
                "routes_with_stations": int(with_stations),
            },
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "data": {
                "total": 0,
                "active": 0,
                "inactive": 0,
                "on_time_rate": 0.0,
                "routes_with_stations": 0,
            },
        }
        

# Member Activity Analysis API
@app.get("/api/dashboard/member-activity")
def get_member_activity(days: int = 7, db: Session = Depends(get_db)):
    """
    取得會員活躍度分析數據
    
    參數:
    - days: 分析天數 (1, 7, 30)
    """
    try:
        # Calculate the time range
        end_date = get_taipei_time()
        start_date = end_date - timedelta(days=days)
        start_date_naive = start_date.replace(tzinfo=None)
        end_date_naive = end_date.replace(tzinfo=None)
        
        # Define activity criteria
        # Highly active: Last login <= 3 days
        # Moderately active: last logged in 4-7 days
        # Low active: Last login 8-30 days
        # Inactive: last logged in > 30 days or never logged in
        
        now_naive = end_date.replace(tzinfo=None)
        high_active_cutoff = now_naive - timedelta(days=3)
        medium_active_cutoff = now_naive - timedelta(days=7)
        low_active_cutoff = now_naive - timedelta(days=30)
        
        # Check the number of members at each activity level
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
        
        # Calculate total number and activity rate
        total_members = high_active + medium_active + low_active + inactive
        active_members = high_active + medium_active
        active_rate = round((active_members / total_members * 100), 1) if total_members > 0 else 0
        
        # Calculate the maximum value for percentage calculation
        max_count = max(high_active, medium_active, low_active, inactive) if total_members > 0 else 1
        
        # Build activity data
        activity_data = [
            {
                "label": "Highly active",
                "count": high_active,
                "percentage": round((high_active / max_count * 100), 1) if max_count > 0 else 0
            },
            {
                "label": "Active", 
                "count": medium_active,
                "percentage": round((medium_active / max_count * 100), 1) if max_count > 0 else 0
            },
            {
                "label": "Low active",
                "count": low_active,
                "percentage": round((low_active / max_count * 100), 1) if max_count > 0 else 0
            },
            {
                "label": "Inactive",
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
        # Return preset data to prevent errors
        return {
            "success": False,
            "data": {
                "activity_data": [
                    {"label": "Highly active", "count": 0, "percentage": 0},
                    {"label": "Active", "count": 0, "percentage": 0},
                    {"label": "Low active", "count": 0, "percentage": 0},
                    {"label": "Inactive", "count": 0, "percentage": 0}
                ],
                "summary": {
                    "active_rate": 0,
                    "active_members": 0,
                    "total_members": 0
                },
                "period_days": days
            }
        }

# Administrator Statistics API
@app.get("/api/dashboard/admin-stats")
def get_admin_statistics(db: Session = Depends(get_db)):
    """
    取得管理員統計資料
    """
    try:
        # Calculate the total number of administrators
        total_admins = db.query(AdminUser).count()
        
        # Calculate the number of roles
        total_roles = db.query(AdminRole).count()
        
        # Assume that the current online administrator is 1 (can be modified according to actual needs)
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

# Database Status API
@app.get("/api/dashboard/database-stats")
def get_database_statistics(db: Session = Depends(get_db)):
    """
    取得資料庫狀況統計
    """
    try:
        from time import time
        start_time = time()
        
        # Test database connection
        db.execute(text("SELECT 1"))
        
        connection_time = round((time() - start_time) * 1000, 2)  # Convert to milliseconds
        
        # Number of data sheets obtained
        result = db.execute(text("SHOW TABLES"))
        total_tables = len(list(result))
        
        return {
            "success": True,
            "data": {
                "status": "normal",
                "connection_time": connection_time,
                "total_tables": total_tables,
                "health": "good" if connection_time < 100 else "generally"
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "data": {
                "status": "abnormal",
                "connection_time": 9999,
                "total_tables": 0,
                "health": "abnormal"
            }
        }

# User Management API
@app.get("/users")
def get_users(
    page: int = 1,
    limit: int = 10,
    search: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    # Basic query
    query = db.query(User)
    
    # Search criteria (ID, username, LINE ID, Email, phone number)
    if search:
        search_pattern = f"%{search}%"
        try:
            # Try to convert the input into an integer for exact comparison of user_id
            search_id = int(search)
        except (TypeError, ValueError):
            search_id = None

        conditions = [
            User.username.like(search_pattern),
            User.email.like(search_pattern),
            User.phone.like(search_pattern),
            User.line_id.like(search_pattern),
        ]
        # Allow search by ID (precise or CAST blur)
        if search_id is not None:
            conditions.append(User.user_id == search_id)
        # CAST user_id fuzzy string, compatible with input prefix/mixed string
        try:
            from sqlalchemy import cast, String
            conditions.append(cast(User.user_id, String).like(search_pattern))
        except Exception:
            pass

        from sqlalchemy import or_
        query = query.filter(or_(*conditions))
    
    # Status Filter
    if status:
        query = query.filter(User.status == status)
    
    # Calculate the total number
    total = query.count()
    
    # Pagination
    users = query.offset((page - 1) * limit).limit(limit).all()
    
    # Format response
    users_data = []
    for u in users:
        # Compatible with old values: DB may have 'None', and it will be converted to 'no_reservation'
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

# # Remove the created_user that was not protected by permission in the early stage and use the protected version below instead

@app.get("/users/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="The user does not exist")
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

# # Remove the early update_user that was not protected by permission and use the protected version below

# # Remove the delete_user that was not protected by permission in the early stage and use the protected version below instead


# User Login Verification API
class UserLogin(BaseModel):
    username: str
    password: str

@app.post("/users/login")
def login_user(login_data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == login_data.username).first()
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    
    # Check user status: login is prohibited if deactivated
    if user.status != 'active':
        status_messages = {
            'inactive': "The account has been disabled, please contact the administrator"
        }
        raise HTTPException(status_code=401, detail=status_messages.get(user.status, "Account status abnormal"))
    
    # Check whether the user has password settings
    if not user.password:
        raise HTTPException(status_code=401, detail="The user has not set a password yet, please contact the administrator")
    
    # Check password
    try:
        if not bcrypt.checkpw(login_data.password.encode('utf-8'), user.password.encode('utf-8')):
            raise HTTPException(status_code=401, detail="Incorrect username or password")
    except ValueError:
        # The password is incorrect, it may be an old format or a corrupted information
        raise HTTPException(status_code=401, detail="Password format is wrong, please contact the administrator to reset the password")
    
    # Update the last login time (Taiwan time)
    user.last_login = get_taiwan_datetime()
    db.commit()
    
    return {
        "message": "Login successfully",
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

# Administrator User API
@app.get("/api/admin/users")
def get_admin_users(
    page: int = 1,
    limit: int = 10,
    search: Optional[str] = None,
    status: Optional[str] = None,
    order: Literal['asc', 'desc'] = 'desc',
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
        # Create basic inquiry
        query = db.query(AdminUser, AdminRole).join(
            AdminRole, AdminUser.role_id == AdminRole.role_id, isouter=True
        )
        
        # Search function
        if search:
            query = query.filter(AdminUser.username.contains(search))
        
        # Status Filter
        if status:
            query = query.filter(AdminUser.status == status)
        
        # Sort
        order_value = (order or 'desc').lower()
        if order_value not in ('asc', 'desc'):
            order_value = 'desc'
        order_column = AdminUser.admin_id.desc() if order_value == 'desc' else AdminUser.admin_id.asc()
        query = query.order_by(order_column)

        # Calculate the total number of transactions
        total = query.count()
        
        # Pagination
        offset = (page - 1) * limit
        admin_users = query.offset(offset).limit(limit).all()
        
        # Format the results
        result = []
        for admin_user, admin_role in admin_users:
            result.append({
                "admin_id": admin_user.admin_id,
                "username": admin_user.username,
                "role_id": admin_user.role_id,
                "role_name": admin_role.role_name if admin_role else "not specified",
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

# Get the administrator role list
@app.get("/api/admin/roles")
def get_admin_roles(db: Session = Depends(get_db)):
    """Obtain all administrator roles"""
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
    """Create a new administrator user"""
    try:
        # Get the current user role
        current_role = db.query(AdminRole).filter(AdminRole.role_id == current_user.role_id).first()
        
        # Permission Check
        target_role_name = get_role_name(db, user.role_id)
        if not target_role_name:
            return {"success": False, "message": "The specified role does not exist"}

        trn = target_role_name.lower()

        if current_role and (current_role.role_name or "# 角色管理 API").lower() == 'super_admin':
            # Super Admin can create any role other than super_admin (if super_admin already exists)
            if trn == 'super_admin':
                existing_super_admin_count = (
                    db.query(AdminUser)
                    .join(AdminRole, AdminUser.role_id == AdminRole.role_id)
                    .filter(func.lower(AdminRole.role_name) == 'super_admin')
                    .count()
                )
                if existing_super_admin_count >= 1:
                    return {
                        "success": False,
                        "message": "The system can only have one group of Super Admins"
                    }
        elif current_role and (current_role.role_name or "# 角色管理 API").lower() == 'admin':
            # Admin can only create Dispatcher accounts
            if trn != 'dispatcher':
                return {
                    "success": False,
                    "message": "Senior administrators can only create accounts with the Dispatcher role"
                }
        else:
            return {
                "success": False,
                "message": "No permission to create a user"
            }
        
        # Check if the username already exists
        existing_user = db.query(AdminUser).filter(AdminUser.username == user.username).first()
        if existing_user:
            return {
                "success": False,
                "message": "The username already exists"
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
                "message": "Administrator user creation successfully"
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
    """Update administrator user"""
    try:            
        # Get the current user role
        current_role = db.query(AdminRole).filter(AdminRole.role_id == current_user.role_id).first()
        
        user = db.query(AdminUser).filter(AdminUser.admin_id == admin_id).first()
        if not user:
            return {
                "success": False,
                "message": "Administrator user does not exist"
            }
        
        # Get the user role to be edited
        target_role = db.query(AdminRole).filter(AdminRole.role_id == user.role_id).first()
        
        # Permission Check
        if current_role and (current_role.role_name or "# 角色管理 API").lower() == 'super_admin':
            # Super Admin can modify any attributes of other users, but with specific restrictions
            if admin_id == current_user.admin_id:
                # Super Admin cannot modify its role permissions (including downgrading to Admin)
                if hasattr(user_update, 'role_id') and user_update.role_id and user_update.role_id != user.role_id:
                    return {
                        "success": False,
                        "message": "Super Admin cannot modify its role permissions, including downgrading to Admin"
                    }
                # Super Admin cannot change its status to disable
                if hasattr(user_update, 'status') and user_update.status and user_update.status == 'inactive':
                    return {
                        "success": False,
                        "message": "Super Admin cannot disable your account"
                    }
            else:
                # Super Admin cannot modify any other Super Admin information
                if target_role and target_role.role_name == 'super_admin':
                    return {
                        "success": False,
                        "message": "Super Admin cannot modify other Super Admin information"
                    }
        elif current_role and (current_role.role_name or "# 角色管理 API").lower() == 'admin':
            # Admin permission restrictions: Only Dispatcher can be operated, the user role is immutable, and the remaining information can be changed (including status/password/user name)
            if target_role and (target_role.role_name or "# 角色管理 API").lower() == 'super_admin':
                return {"success": False, "message": "Super Admin users cannot be modified"}
            if target_role and (target_role.role_name or "# 角色管理 API").lower() == 'admin':
                return {"success": False, "message": "Senior administrators cannot modify other Admin users"}
            # Cannot modify roles
            if hasattr(user_update, 'role_id') and user_update.role_id and user_update.role_id != user.role_id:
                return {"success": False, "message": "No permission to modify user role"}
        else:
            return {
                "success": False,
                "message": "No permission to modify the user"
            }
        
        # If you want to update the username, check if it already exists
        if hasattr(user_update, 'username') and user_update.username and user_update.username != user.username:
            existing_user = db.query(AdminUser).filter(
                AdminUser.username == user_update.username,
                AdminUser.admin_id != admin_id
            ).first()
            if existing_user:
                return {
                    "success": False,
                    "message": "The username already exists"
                }
        
        # Update fields
        for key, value in user_update.dict(exclude_unset=True).items():
            if key == "password":
                # Updated only if the password is not empty
                if value and value.strip():
                    setattr(user, "password_hash", hash_password(value))
            else:
                setattr(user, key, value)
        
        db.commit()
        return {
            "success": True,
            "message": "Administrator user update successfully"
        }
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "message": f"更新管理員用戶失敗: {str(e)}"
        }

@app.delete("/api/admin/users/{admin_id}")
def delete_admin_user(admin_id: int, db: Session = Depends(get_db), current_user: AdminUser = Depends(get_current_user)):
    """Delete the administrator user"""
    try:
        # Get the current user role
        current_role = db.query(AdminRole).filter(AdminRole.role_id == current_user.role_id).first()
        
        user = db.query(AdminUser).filter(AdminUser.admin_id == admin_id).first()
        if not user:
            return {
                "success": False,
                "message": "Administrator user does not exist"
            }
            
        # Get the role of the user to be deleted
        target_role = db.query(AdminRole).filter(AdminRole.role_id == user.role_id).first()
        
        # Permission Check
        if current_role and (current_role.role_name or "# 角色管理 API").lower() == 'super_admin':
            # Super Admin can delete Admin users, but cannot delete themselves or other Super Admins
            if admin_id == current_user.admin_id:
                return {
                    "success": False,
                    "message": "Can't delete your account"
                }
            # Super Admin Cannot delete other Super Admin
            if target_role and (target_role.role_name or "# 角色管理 API").lower() == 'super_admin':
                return {
                    "success": False,
                    "message": "Super Admin Cannot delete other Super Admin"
                }
        elif current_role and (current_role.role_name or "# 角色管理 API").lower() == 'admin':
            # Admin can only delete Dispatcher
            if not (target_role and (target_role.role_name or "# 角色管理 API").lower() == 'dispatcher'):
                return {"success": False, "message": "Advanced administrators can only delete Dispatcher users"}
        else:
            return {
                "success": False,
                "message": "No permission to delete users"
            }
        
        # Check whether you are a system administrator (optional protection mechanism)
        if user.admin_id == 1:  # Assume ID 1 is the super administrator
            return {
                "success": False,
                "message": "Cannot delete super administrator"
            }
        
        db.delete(user)
        db.commit()
        return {
            "success": True,
            "message": "Administrator user deletion successfully"
        }
    except Exception as e:
        db.rollback()
        return {
            "success": False,
            "message": f"刪除管理員用戶失敗: {str(e)}"
        }
'''
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
'''

@app.get("/")
def root():
    return {
        "message": "Hualien Mini Bus Backend System",
        "status": "Running",
        "features": ["User Management", "Access Control", "Database Integration"]
    }

@app.get("/All_Route", response_model=List[Route])
def All_Route():
    try:
        rows = MySQL_Run("SELECT * FROM bus_routes_total")

        # MySQL_Run may return list of dicts (DictCursor) or list of tuples.
        if not rows:
            return []

        # If rows are dicts, build DataFrame directly
        if isinstance(rows, list) and isinstance(rows[0], dict):
            df = pd.DataFrame(rows)
        else:
            # fallback: get columns and construct DataFrame
            cols = MySQL_Run("SHOW COLUMNS FROM bus_routes_total")
            try:
                columns = [c[0] for c in cols]
            except Exception:
                # if cols are dicts
                columns = [c.get('Field') or list(c.values())[0] for c in cols]
            df = pd.DataFrame(rows, columns=columns)

        if "created_at" in df.columns:
            df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")\
                .apply(lambda x: x.to_pydatetime() if pd.notnull(x) else None)

        records = df.where(pd.notnull(df), None).to_dict(orient="records")
        return records
    except Exception as e:
        print(f"All_Route error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# New route request model
class RouteCreate(BaseModel):
    route_name: str
    direction: Optional[str] = None
    start_stop: Optional[str] = None
    end_stop: Optional[str] = None
    stop_count: Optional[int] = 0
    status: Optional[int] = 1


@app.post("/api/routes/create")
def create_route(route: RouteCreate, current_user: AdminUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create a new route record in bus_routes_total"""
    try:
        # (Using parameterized checks instead, removing early non-parametric checks to avoid SQL injection risks)

        # Use parameterized queries to avoid SQL injection
        stop_count = int(route.stop_count or 0)
        status = int(route.status or 1)

        # direction can only be 'one-way' or 'two-way' (bus_routes_total schema)
        direction_val = route.direction if route.direction in ("unidirectional", "Two-way") else None

        # Check the route of the same name (parameterization)
        check_sql = "SELECT COUNT(*) as count FROM bus_routes_total WHERE route_name = %s"
        check_result = MySQL_Run(check_sql, (route.route_name,))
        if check_result and check_result[0].get('count', 0) > 0:
            raise HTTPException(status_code=400, detail="The route name already exists")

        # Construct the columns and parameters of INSERT
        cols = ['route_name', 'stop_count', 'status']
        placeholders = ['%s', '%s', '%s']
        params = [route.route_name, stop_count, status]
        if direction_val:
            cols.insert(2, 'direction')
            placeholders.insert(2, '%s')
            params.insert(2, direction_val)
        if route.start_stop:
            cols.append('start_stop')
            placeholders.append('%s')
            params.append(route.start_stop)
        if route.end_stop:
            cols.append('end_stop')
            placeholders.append('%s')
            params.append(route.end_stop)

        sql = f"INSERT INTO bus_routes_total ({', '.join(cols)}) VALUES ({', '.join(placeholders)})"
        insert_res = MySQL_Run(sql, tuple(params))

        # MySQL_Run will return dict {status, lastrowid} to non-SELECT
        new_route_id = None
        try:
            if isinstance(insert_res, dict) and insert_res.get('lastrowid'):
                new_route_id = int(insert_res.get('lastrowid'))
        except Exception:
            new_route_id = None

        # If you don't get lastrowid, try using SELECT LAST_INSERT_ID() as fallback (but please note that the connection will be different)
        if not new_route_id:
            try:
                last = MySQL_Run("SELECT LAST_INSERT_ID() as id")
                if last and isinstance(last, list) and len(last) > 0:
                    if isinstance(last[0], dict):
                        new_route_id = int(last[0].get('id') or last[0].get('LAST_INSERT_ID()') or 0)
                    else:
                        new_route_id = int(last[0][0])
            except Exception:
                new_route_id = None

    # No longer automatically create placeholder sites in bus_route_stations

        return {"message": "Successful route addition", "ok": True, "route_id": new_route_id}
    except HTTPException:
        raise
    except Exception as e:
        print(f"新增路線失敗: {e}")
        raise HTTPException(status_code=500, detail=f"新增路線失敗: {str(e)}")


class RouteUpdate(BaseModel):
    route_id: int
    route_name: Optional[str] = None
    direction: Optional[str] = None
    start_stop: Optional[str] = None
    end_stop: Optional[str] = None
    stop_count: Optional[int] = None
    status: Optional[int] = None


@app.put("/api/routes/update")
def update_route(route: RouteUpdate, current_user: AdminUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """Update the field of bus_routes_total (partially updated)"""
    try:
        # Confirm route presence
        check_sql = "SELECT COUNT(*) as cnt FROM bus_routes_total WHERE route_id = %s"
        check_res = MySQL_Run(check_sql, (route.route_id,))
        if not check_res or check_res[0].get('cnt', 0) == 0:
            raise HTTPException(status_code=404, detail="The specified route cannot be found")

        updates = []
        params = []

        if route.route_name is not None:
            # Check the same name (exclude yourself)
            exist_sql = "SELECT COUNT(*) as c FROM bus_routes_total WHERE route_name = %s AND route_id != %s"
            exist_res = MySQL_Run(exist_sql, (route.route_name, route.route_id))
            if exist_res and exist_res[0].get('c', 0) > 0:
                raise HTTPException(status_code=400, detail="The route name already exists")
            updates.append("route_name = %s")
            params.append(route.route_name)

        if route.direction is not None:
            if route.direction not in ("unidirectional", "Two-way"):
                raise HTTPException(status_code=400, detail="direction must be 'one-way' or 'two-way'")
            updates.append("direction = %s")
            params.append(route.direction)

        if route.start_stop is not None:
            updates.append("start_stop = %s")
            params.append(route.start_stop)

        if route.end_stop is not None:
            updates.append("end_stop = %s")
            params.append(route.end_stop)

        if route.stop_count is not None:
            updates.append("stop_count = %s")
            params.append(int(route.stop_count))

        if route.status is not None:
            updates.append("status = %s")
            params.append(int(route.status))

        if not updates:
            return {"message": "No columns need to be updated", "ok": True}

        params.append(route.route_id)
        sql = f"UPDATE bus_routes_total SET {', '.join(updates)} WHERE route_id = %s"
        MySQL_Run(sql, tuple(params))

        return {"message": "Route update successfully", "ok": True}
    except HTTPException:
        raise
    except Exception as e:
        print(f"更新路線失敗: {e}")
        raise HTTPException(status_code=500, detail=f"更新路線失敗: {str(e)}")


class RouteDelete(BaseModel):
    route_id: int


@app.delete("/api/routes/delete")
def delete_route(req: RouteDelete, current_user: AdminUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete route: The corresponding bus_route_stations and bus_routes_total records will be deleted at the same time (if present)."""
    try:
        rid = int(req.route_id)

        # First confirm whether there is this route (priority check bus_routes_total)
        try:
            chk = MySQL_Run("SELECT COUNT(*) as cnt FROM bus_routes_total WHERE route_id = %s", (rid,))
        except TypeError:
            chk = MySQL_Run(f"SELECT COUNT(*) as cnt FROM bus_routes_total WHERE route_id = {rid}")

        exists = False
        if chk and isinstance(chk, list) and chk[0].get('cnt', 0) > 0:
            exists = True
        else:
            # If there is no record in bus_routes_total, check bus_route_stations
            try:
                chk2 = MySQL_Run("SELECT COUNT(*) as cnt FROM bus_route_stations WHERE route_id = %s", (rid,))
            except TypeError:
                chk2 = MySQL_Run(f"SELECT COUNT(*) as cnt FROM bus_route_stations WHERE route_id = {rid}")
            if chk2 and isinstance(chk2, list) and chk2[0].get('cnt', 0) > 0:
                exists = True

        if not exists:
            raise HTTPException(status_code=404, detail="The specified route cannot be found")

        # Delete the site for this route (if any)
        try:
            MySQL_Run("DELETE FROM bus_route_stations WHERE route_id = %s", (rid,))
        except TypeError:
            MySQL_Run(f"DELETE FROM bus_route_stations WHERE route_id = {rid}")

        # Delete route records in bus_routes_total (if any)
        try:
            MySQL_Run("DELETE FROM bus_routes_total WHERE route_id = %s", (rid,))
        except TypeError:
            MySQL_Run(f"DELETE FROM bus_routes_total WHERE route_id = {rid}")

        return {"message": "Route deletion successfully", "ok": True}
    except HTTPException:
        raise
    except Exception as e:
        print(f"刪除路線失敗: {e}")
        raise HTTPException(status_code=500, detail=f"刪除路線失敗: {str(e)}")

@app.post("/Route_Stations", response_model=List[StationOut])
def get_route_stations(q: RouteStationsQuery):
    # --- Parameterized query (If your MySQL_Run supports params, this writing method will be preferred) ---
    sql = "SELECT * FROM bus_route_stations WHERE route_id = %s"
    params = [q.route_id]
    if q.direction:
        sql += " AND direction = %s"
        params.append(q.direction)

    try:
        rows = MySQL_Run(sql, params)  # If your MySQL_Run does not support params, fallback uses f-string, but be careful to inject it.
    except TypeError:
        # Fallback: Some self-written functions do not have params parameters
        # Please make sure that the source of the direction string is credible
        if q.direction:
            rows = MySQL_Run(f"SELECT * FROM bus_route_stations WHERE route_id = {int(q.route_id)} AND direction = '{q.direction}'")
        else:
            rows = MySQL_Run(f"SELECT * FROM bus_route_stations WHERE route_id = {int(q.route_id)}")

    columns = [c[0] for c in MySQL_Run("SHOW COLUMNS FROM bus_route_stations")]
    df = pd.DataFrame(rows, columns=columns)

    # --- Processing of no information (choose one: reply 404 or return [])--
    if df.empty:
        # Select one: Return to empty array (the front-end is easy to handle)
        return []
        # Select 2: Return 404
        # raise HTTPException(status_code=404, detail=f"route_id={q.route_id} No site profile")

    # --- Regularize column names (map DB columns into API columns)---
    col_map = {
        "station_name": "stop_name",
        "stop_name": "stop_name",
        "est_time": "eta_from_start",
        "eta_from_start": "eta_from_start",
        "order_no": "stop_order",
        "seq": "stop_order",
        # If you have the station_id field but do not intend to output it, don't map it
    }
    # Only rename exists field to avoid KeyError
    df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})

    # --- Type prevention: numerical, time, NaN conversion ---
    # Latitude and longitude
    if "latitude" in df.columns:
        df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    if "longitude" in df.columns:
        df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")

    # Arrival time/order
    if "eta_from_start" in df.columns:
        df["eta_from_start"] = pd.to_numeric(df["eta_from_start"], errors="coerce").astype("Int64")
    if "stop_order" in df.columns:
        df["stop_order"] = pd.to_numeric(df["stop_order"], errors="coerce").astype("Int64")

    # created_at -> datetime (avoid pandas.Timestamp causing verification errors)
    if "created_at" in df.columns:
        df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")\
            .apply(lambda x: x.to_pydatetime() if pd.notnull(x) else None)

    # Only keep the fields we want to output (avoid unnecessary fields trigger verification errors)
    desired_cols = [
        "route_id", "route_name", "direction", "stop_name",
        "latitude", "longitude", "eta_from_start", "stop_order", "created_at"
    ]
    keep_cols = [c for c in desired_cols if c in df.columns]
    df = df[keep_cols]

    # NaN -> None
    records = df.where(pd.notnull(df), None).to_dict(orient="records")

    # (Optional) Transaction-by-transaction modeling can detect data anomalies earlier on the backend
    data: List[StationOut] = [StationOut(**r) for r in records]
    return data

# ===== OTP/Verification Code API =====
@app.post("/auth/otp/request")
def otp_request(req: OTPRequest, request: Request):
    r = get_redis()
    purpose = (req.purpose or "login").strip().lower()
    acc = _norm_account(req.account)
    if not acc:
        raise HTTPException(status_code=400, detail="Missing account")
    acc_hash = _hash_key(acc)
    keys = _otp_keys(purpose, acc_hash)

    # Check if it is locked
    if r.get(keys["lock"]):
        raise HTTPException(status_code=429, detail="The verification code is locked, please try again later")

    # Resend to cool
    if r.ttl(keys["cooldown"]) > 0:
        raise HTTPException(status_code=429, detail="Send too frequently, please try again later")

    # Destination rate limit (10 minutes 3 times)
    dest_cnt = r.incr(keys["dest_rl"])
    if dest_cnt == 1:
        r.expire(keys["dest_rl"], 600)
    if dest_cnt > OTP_RL_DEST_MAX_10MIN:
        raise HTTPException(status_code=429, detail="Too many requests, try again later")

    # Source IP rate limit (1 hour 10 times)
    ip = request.client.host if request and request.client else "unknown"
    ip_key = _ip_key(ip)
    ip_cnt = r.incr(ip_key)
    if ip_cnt == 1:
        r.expire(ip_key, 3600)
    if ip_cnt > OTP_RL_IP_MAX_1H:
        raise HTTPException(status_code=429, detail="There are too many requests for this IP, please try again later")

    # Generate and save the verification code
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

    # Write the verification code and account to the file (for test purposes, please turn off HBUS_OTP_LOG in the formal environment)
    if OTP_LOG_ENABLE:
        try:
            ts = get_taipei_time().strftime("%Y-%m-%d %H:%M:%S %z")
            with open(OTP_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(f"{ts}\taccount={acc}\tpurpose={purpose}\tcode={code}\n")
        except Exception as e:
            print(f"[OTP] 寫入驗證碼檔案失敗: {e}")

    # Integrate real sending (SMS/Email) here.Currently, only mask information is transmitted back; if DEBUG is enabled, code will be transmitted back for easy testing.
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
        raise HTTPException(status_code=400, detail="Missing account or code")
    acc_hash = _hash_key(acc)
    keys = _otp_keys(purpose, acc_hash)

    # Lock check
    if r.get(keys["lock"]):
        raise HTTPException(status_code=429, detail="Locked, please try again later")

    raw = r.get(keys["code"])
    if not raw:
        raise HTTPException(status_code=400, detail="The verification code has expired or does not exist")
    try:
        payload = json.loads(raw)
    except Exception:
        payload = {"code": raw, "attempts_left": int(r.get(keys["tries"]) or 0)}

    attempts_left = int(r.get(keys["tries"]) or payload.get("attempts_left") or 0)
    if attempts_left <= 0:
        # Set lock for 10 minutes
        r.setex(keys["lock"], 600, "1")
        r.delete(keys["code"], keys["tries"], keys["cooldown"])
        raise HTTPException(status_code=429, detail="Too many attempts, locked")

    if req.code.strip() != str(payload.get("code", "# 角色管理 API")).strip():
        attempts_left -= 1
        r.setex(keys["tries"], max(r.ttl(keys["code"]), 1), str(attempts_left))
        raise HTTPException(status_code=400, detail=f"驗證碼錯誤，剩餘 {attempts_left} 次")

    # Passed: Issuing a one-time ticket (10 minutes) for subsequent binding login/registration
    r.delete(keys["tries"], keys["cooldown"])
    r.delete(keys["code"])  # single use
    ticket = secrets.token_urlsafe(24)
    r.setex(f"otp:ticket:{ticket}", 600, json.dumps({"account": acc, "purpose": purpose}))
    return {"ok": True, "ticket": ticket, "expires_in": 600}

@app.post("/auth/otp/consume")
def otp_consume(ticket: str):
    """Redeem with ticket to complete the next step (such as login/register).Here only the ticket is verified and deleted."""
    r = get_redis()
    raw = r.get(f"otp:ticket:{ticket}")
    if not raw:
        raise HTTPException(status_code=400, detail="ticket invalid or expired")
    r.delete(f"otp:ticket:{ticket}")
    try:
        data = json.loads(raw)
    except Exception:
        data = {"account": None, "purpose": None}
    return {"ok": True, "account": data.get("account"), "purpose": data.get("purpose")}

# ===== Route Site Management API =====

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
    # optional Original recognition field (provided by the front end) for safe update positioning
    original_stop_name: Optional[str] = None
    original_stop_order: Optional[int] = None

@app.post("/api/route-stations/create")
def create_route_station(station: StationCreate, current_user: AdminUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create a new route site"""
    try:
        # If the front-end does not provide route_name, try to use route_id to search back
        if not station.route_name or str(station.route_name).strip() == "# 角色管理 API":
            try:
                rr = MySQL_Run("SELECT route_name FROM bus_routes_total WHERE route_id = %s", (station.route_id,))
                if rr and isinstance(rr, list) and len(rr) > 0 and isinstance(rr[0], dict):
                    station.route_name = rr[0].get('route_name') or station.route_name
            except Exception:
                pass

        # Automatic vacancies: Under the same route, the site order of >= new order is +1 in the overall order (allows direct order)
        try:
            MySQL_Run(
                """
                UPDATE bus_route_stations
                SET stop_order = stop_order + 1
                WHERE route_id = %s AND stop_order >= %s
                """,
                (station.route_id, station.stop_order)
            )
        except Exception:
            # Ignore vacancy errors (can be inserted if there is no unique constraint)
            pass

        # Parameterized INSERT
        sql = """
        INSERT INTO bus_route_stations 
        (route_id, route_name, direction, stop_name, latitude, longitude, stop_order, eta_from_start, address)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            station.route_id,
            station.route_name,
            station.direction,
            station.stop_name,
            station.latitude,
            station.longitude,
            station.stop_order,
            station.eta_from_start,
            station.address or "# 角色管理 API"
        )
        MySQL_Run(sql, params)
        return {"message": "Site creation successfully", "ok": True}
    except HTTPException:
        raise
    except Exception as e:
        print(f"創建站點失敗: {str(e)}")  # Join the log
        raise HTTPException(status_code=500, detail=f"創建站點失敗: {str(e)}")

@app.put("/api/route-stations/update")
def update_route_station(station: StationUpdate, current_user: AdminUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """Update route site: Allow free order change, and the backend automatically reorders to avoid conflicts."""
    try:
        # Support front-end transmission original_stop_order or original_stop_name as the original positioning value
        orig_order = getattr(station, 'original_stop_order', None)
        orig_name = getattr(station, 'original_stop_name', None)

        # If you change stop_order: Use list movement algorithm to maintain uniqueness
        try:
            if orig_order is not None and station.stop_order is not None and int(station.stop_order) != int(orig_order):
                new_order = int(station.stop_order)
                old_order = int(orig_order)
                if new_order < old_order:
                    # Move up: new..old-1 All +1
                    MySQL_Run(
                        """
                        UPDATE bus_route_stations
                        SET stop_order = stop_order + 1
                        WHERE route_id = %s AND stop_order >= %s AND stop_order < %s
                        """,
                        (station.route_id, new_order, old_order)
                    )
                else:
                    # Move down: old+1..new All -1
                    MySQL_Run(
                        """
                        UPDATE bus_route_stations
                        SET stop_order = stop_order - 1
                        WHERE route_id = %s AND stop_order <= %s AND stop_order > %s
                        """,
                        (station.route_id, new_order, old_order)
                    )
        except Exception:
            # Reorder failure does not block
            pass

        if orig_order is not None:
            where_sql = "WHERE route_id = %s AND stop_order = %s"
            where_params = (station.route_id, orig_order)
        elif orig_name:
            where_sql = "WHERE route_id = %s AND stop_name = %s"
            where_params = (station.route_id, orig_name)
        else:
            # Finally fallback uses route_id + stop_order (when the form does not provide original_*)
            where_sql = "WHERE route_id = %s AND stop_order = %s"
            where_params = (station.route_id, station.stop_order)

        sql = f"""
        UPDATE bus_route_stations
        SET route_name = %s, direction = %s,
            stop_name = %s, latitude = %s,
            longitude = %s, stop_order = %s,
            eta_from_start = %s,
            address = %s
        {where_sql}
        """

        params = (
            station.route_name,
            station.direction,
            station.stop_name,
            station.latitude,
            station.longitude,
            station.stop_order,
            station.eta_from_start,
            station.address or "# 角色管理 API"
        ) + tuple(where_params)

        MySQL_Run(sql, params)
        return {"message": "Site update successfully", "ok": True}
    except Exception as e:
        print(f"更新站點失敗: {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新站點失敗: {str(e)}")

@app.delete("/api/route-stations/delete")
def delete_route_station(route_id: int, stop_order: int, current_user: AdminUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """Delete the route site"""
    try:
        # Check whether the record exists (parameterization)
        check_sql = "SELECT COUNT(*) as count FROM bus_route_stations WHERE route_id = %s AND stop_order = %s"
        check_result = MySQL_Run(check_sql, (route_id, stop_order))

        if not check_result or check_result[0].get('count', 0) == 0:
            raise HTTPException(status_code=404, detail="The site you want to delete cannot be found")

        sql = "DELETE FROM bus_route_stations WHERE route_id = %s AND stop_order = %s"
        MySQL_Run(sql, (route_id, stop_order))
        return {"message": "Site deletion successfully", "ok": True}
    except HTTPException:
        raise
    except Exception as e:
        print(f"刪除站點失敗: {str(e)}")  # Join the log
        raise HTTPException(status_code=500, detail=f"刪除站點失敗: {str(e)}")

@app.get("/api/routes")
def get_all_routes():
    """Get all routes (extracted from the bus_route_stations table)"""
    try:
        # Get all different route names and corresponding route_id from the bus_route_stations table
        rows = MySQL_Run("""
            SELECT DISTINCT route_id, route_name 
            FROM bus_route_stations 
            ORDER BY route_id
        """)
        
        # If some routes do not have route_id, we assign them one
        routes = []
        for row in rows:
            if row['route_id'] is None or row['route_id'] == "# 角色管理 API":
                # Assign a name-based ID to routes without route_id
                route_name = row['route_name']
                if route_name == "Citizen minibus-Motion Tour Hualien":
                    route_id = 4
                else:
                    # Generate ID for other routes without route_id
                    route_id = hash(route_name) % 10000  # Simple hash function
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
    page_size: int = 20,
    order: Literal['asc', 'desc'] = 'desc'
):
    """Get filtered route sites (paging and searching support)"""
    try:
        # Construct query conditions
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
        
        # Construct WHERE clause
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        
        # Calculate the total number
        count_sql = f"SELECT COUNT(*) as total FROM bus_route_stations WHERE {where_clause}"
        count_result = MySQL_Run(count_sql, tuple(params) if params else ())
        total = count_result[0]['total'] if count_result else 0
        
        # Calculate paging
        offset = (page - 1) * page_size
        
        # Construct the main query
        order_value = (order or 'desc').lower()
        if order_value not in ('asc', 'desc'):
            order_value = 'desc'
        order_clause = 'DESC' if order_value == 'desc' else 'ASC'
        sql = f"""
        SELECT * FROM bus_route_stations 
        WHERE {where_clause} 
        ORDER BY route_id {order_clause}, stop_order 
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

# =================  Reservation APIs  =================

def _ensure_admin_or_super(db: Session, current_user: AdminUser):
    role = get_role_by_id(db, current_user.role_id)
    if not role or (role.role_name or "# 角色管理 API").lower() not in ('super_admin', 'admin'):
        raise HTTPException(status_code=403, detail="No permission to perform this operation")

@app.get("/api/reservations")
def list_reservations(
    page: int = 1,
    limit: int = 20,
    search: Optional[str] = None,
    payment_status: Optional[str] = None,
    review_status: Optional[str] = None,
    dispatch_status: Optional[str] = None,
    order: Literal['asc', 'desc'] = 'desc'
):
    try:
        cond = []
        params: List = []
        if search:
            cond.append("(booking_start_station_name LIKE %s OR booking_end_station_name LIKE %s OR CAST(user_id AS CHAR) LIKE %s)")
            s = f"%{search}%"
            params.extend([s, s, s])
        if payment_status:
            cond.append("payment_status = %s")
            params.append(payment_status)
        if review_status:
            cond.append("review_status = %s")
            params.append(review_status)
        if dispatch_status:
            cond.append("dispatch_status = %s")
            params.append(dispatch_status)

        where_clause = " AND ".join(cond) if cond else "1=1"

        cnt_sql = f"SELECT COUNT(*) as total FROM reservation WHERE {where_clause}"
        total = MySQL_Run(cnt_sql, tuple(params))[0]['total']

        offset = (page - 1) * limit
        order_value = (order or 'desc').lower()
        if order_value not in ('asc', 'desc'):
            order_value = 'desc'
        order_clause = 'DESC' if order_value == 'desc' else 'ASC'
        list_sql = f"""
            SELECT reservation_id, user_id, booking_time, booking_number,
                   booking_start_station_name, booking_end_station_name,
                   payment_method, payment_record, payment_status,
                   review_status, dispatch_status, reservation_status,
                   created_at, updated_at
            FROM reservation
            WHERE {where_clause}
            ORDER BY reservation_id {order_clause}
            LIMIT %s OFFSET %s
        """
        rows = MySQL_Run(list_sql, tuple(params + [limit, offset]))
        return {
            "success": True,
            "data": rows,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        }
    except Exception as e:
        print("list_reservations error:", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/reservations")
def create_reservation(payload: ReservationCreate, current_user: AdminUser = Depends(get_current_user), db: Session = Depends(get_db)):
    _ensure_admin_or_super(db, current_user)
    try:
        cols = []
        vals = []
        params: List = []
        data = payload.dict(exclude_unset=True)
        for k in [
            'user_id','booking_time','booking_number','booking_start_station_name',
            'booking_end_station_name','payment_method','payment_record',
            'payment_status','review_status','dispatch_status']:
            if k in data and data[k] is not None:
                cols.append(k)
                vals.append('%s')
                params.append(data[k])
        if not cols:
            raise HTTPException(status_code=400, detail="Necessary columns are missing")
        sql = f"INSERT INTO reservation ({', '.join(cols)}) VALUES ({', '.join(vals)})"
        res = MySQL_Run(sql, tuple(params))
        new_id = None
        if isinstance(res, dict) and res.get('lastrowid'):
            new_id = int(res['lastrowid'])
        return {"success": True, "reservation_id": new_id}
    except Exception as e:
        print("create_reservation error:", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/reservations/{reservation_id}")
def update_reservation(reservation_id: int, payload: ReservationUpdate, current_user: AdminUser = Depends(get_current_user), db: Session = Depends(get_db)):
    _ensure_admin_or_super(db, current_user)
    try:
        data = payload.dict(exclude_unset=True)
        if not data:
            return {"success": True, "message": "No changes"}
        sets = []
        params: List = []
        for k, v in data.items():
            sets.append(f"{k} = %s")
            params.append(v)
        params.append(reservation_id)
        sql = f"UPDATE reservation SET {', '.join(sets)} WHERE reservation_id = %s"
        MySQL_Run(sql, tuple(params))
        return {"success": True}
    except Exception as e:
        print("update_reservation error:", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/reservations/{reservation_id}")
def delete_reservation(reservation_id: int, current_user: AdminUser = Depends(get_current_user), db: Session = Depends(get_db)):
    _ensure_admin_or_super(db, current_user)
    try:
        chk = MySQL_Run("SELECT COUNT(*) as c FROM reservation WHERE reservation_id = %s", (reservation_id,))
        if not chk or chk[0]['c'] == 0:
            raise HTTPException(status_code=404, detail="The appointment does not exist")
        MySQL_Run("DELETE FROM reservation WHERE reservation_id = %s", (reservation_id,))
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        print("delete_reservation error:", e)
        raise HTTPException(status_code=500, detail=str(e))

# =================  Car Resource APIs  =================

# =================  Members APIs  =================

def _serialize_member(row: dict):
    data = dict(row)
    for key in ('created_at', 'updated_at', 'last_login'):
        value = data.get(key)
        if value is not None and hasattr(value, 'isoformat'):
            data[key] = value.isoformat()
    return data

@app.get("/api/members")
def list_members(
    page: int = 1,
    limit: int = 10,
    search: Optional[str] = None,
    status: Optional[str] = None,
    order: Literal['asc', 'desc'] = 'desc'
):
    try:
        page = max(page, 1)
        limit = max(limit, 1)
        conditions: List[str] = []
        params: List = []
        if status:
            conditions.append('status = %s')
            params.append(status)
        if search:
            keyword = f"%{search}%"
            conditions.append('(CAST(user_id AS CHAR) LIKE %s OR username LIKE %s OR line_id LIKE %s OR email LIKE %s OR phone LIKE %s)')
            params.extend([keyword, keyword, keyword, keyword, keyword])
        where_clause = ' AND '.join(conditions) if conditions else '1=1'
        count_sql = f"SELECT COUNT(*) as total FROM users WHERE {where_clause}"
        count_res = MySQL_Run(count_sql, tuple(params) if params else ())
        total = count_res[0]['total'] if count_res else 0
        offset = (page - 1) * limit
        order_value = (order or 'desc').lower()
        if order_value not in ('asc', 'desc'):
            order_value = 'desc'
        list_sql = f"""
            SELECT user_id, username, line_id, email, phone, status, reservation_status,
                   preferences, privacy_settings, created_at, updated_at, last_login
            FROM users
            WHERE {where_clause}
            ORDER BY user_id {'DESC' if order_value == 'desc' else 'ASC'}
            LIMIT %s OFFSET %s
        """
        rows = MySQL_Run(list_sql, tuple(params + [limit, offset]))
        return {
            'success': True,
            'users': [_serialize_member(r) for r in rows],
            'total': total,
            'page': page,
            'limit': limit,
            'total_pages': (total + limit - 1) // limit
        }
    except Exception as e:
        print('list_members error:', e)
        raise HTTPException(status_code=500, detail=str(e))

def _serialize_car_resource(row: dict):
    data = dict(row)
    for key in ('commission_date', 'last_service_date'):
        value = data.get(key)
        if value is not None and hasattr(value, "isoformat"):
            data[key] = value.isoformat()
    return data

@app.get("/api/cars")
def list_cars(
    page: int = 1,
    limit: int = 20,
    search: Optional[str] = None,
    status: Optional[str] = None,
    order: Literal['asc', 'desc'] = 'desc'
):
    try:
        page = max(page, 1)
        limit = max(limit, 1)
        valid_status = {'service', 'paused', 'maintenance', 'retired'}
        conditions: List[str] = []
        params: List = []
        if search:
            conditions.append("car_licence LIKE %s")
            params.append(f"%{search}%")
        if status:
            if status not in valid_status:
                raise HTTPException(status_code=400, detail="Invalid vehicle status")
            conditions.append("car_status = %s")
            params.append(status)
        where_clause = " AND ".join(conditions) if conditions else "1=1"
        cnt_sql = f"SELECT COUNT(*) as total FROM car_resource WHERE {where_clause}"
        cnt_res = MySQL_Run(cnt_sql, tuple(params))
        total = cnt_res[0]['total'] if cnt_res else 0
        offset = (page - 1) * limit
        order_value = (order or 'desc').lower()
        if order_value not in ('asc', 'desc'):
            order_value = 'desc'
        order_clause = 'DESC' if order_value == 'desc' else 'ASC'
        list_sql = f"""
            SELECT car_id, car_licence, max_passengers, car_status, commission_date, last_service_date
            FROM car_resource
            WHERE {where_clause}
            ORDER BY car_id {order_clause}
            LIMIT %s OFFSET %s
        """
        rows = MySQL_Run(list_sql, tuple(params + [limit, offset]))
        return {
            "success": True,
            "data": [_serialize_car_resource(r) for r in rows],
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "pages": (total + limit - 1) // limit
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        print("list_cars error:", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/cars")
def create_car_resource(payload: CarResourceCreate, current_user: AdminUser = Depends(get_current_user), db: Session = Depends(get_db)):
    _ensure_admin_or_super(db, current_user)
    try:
        data = payload.dict(exclude_unset=True)
        licence = (data.get('car_licence') or "# 角色管理 API").strip()
        if not licence:
            raise HTTPException(status_code=400, detail="License plate number must not be empty")
        data['car_licence'] = licence
        if data.get('max_passengers') is not None and data['max_passengers'] < 1:
            raise HTTPException(status_code=400, detail="The number of people that can be accommodated must be greater than 0")
        columns: List[str] = []
        placeholders: List[str] = []
        params: List = []
        for key in ['car_licence','max_passengers','car_status','commission_date','last_service_date']:
            if key in data and data[key] is not None:
                columns.append(key)
                placeholders.append('%s')
                params.append(data[key])
        if not columns:
            raise HTTPException(status_code=400, detail="Necessary columns are missing")
        sql = f"INSERT INTO car_resource ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
        res = MySQL_Run(sql, tuple(params))
        new_id = None
        if isinstance(res, dict) and res.get('lastrowid'):
            new_id = int(res['lastrowid'])
        return {"success": True, "car_id": new_id}
    except HTTPException:
        raise
    except Exception as e:
        print("create_car_resource error:", e)
        msg = str(e)
        if 'Duplicate entry' in msg and 'car_licence' in msg:
            raise HTTPException(status_code=400, detail="License plate number already exists")
        raise HTTPException(status_code=500, detail=msg)

@app.put("/api/cars/{car_id}")
def update_car_resource(car_id: int, payload: CarResourceUpdate, current_user: AdminUser = Depends(get_current_user), db: Session = Depends(get_db)):
    _ensure_admin_or_super(db, current_user)
    try:
        data = payload.dict(exclude_unset=True)
        if 'car_licence' in data and data['car_licence'] is not None:
            data['car_licence'] = data['car_licence'].strip()
            if not data['car_licence']:
                raise HTTPException(status_code=400, detail="License plate number must not be empty")
        if 'max_passengers' in data and data['max_passengers'] is not None and data['max_passengers'] < 1:
            raise HTTPException(status_code=400, detail="The number of people that can be accommodated must be greater than 0")
        if not data:
            return {"success": True, "message": "No changes"}
        sets: List[str] = []
        params: List = []
        for key, value in data.items():
            sets.append(f"{key} = %s")
            params.append(value)
        params.append(car_id)
        sql = f"UPDATE car_resource SET {', '.join(sets)} WHERE car_id = %s"
        MySQL_Run(sql, tuple(params))
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        print("update_car_resource error:", e)
        msg = str(e)
        if 'Duplicate entry' in msg and 'car_licence' in msg:
            raise HTTPException(status_code=400, detail="License plate number already exists")
        raise HTTPException(status_code=500, detail=msg)

@app.delete("/api/cars/{car_id}")
def delete_car_resource(car_id: int, current_user: AdminUser = Depends(get_current_user), db: Session = Depends(get_db)):
    _ensure_admin_or_super(db, current_user)
    try:
        chk = MySQL_Run("SELECT COUNT(*) as c FROM car_resource WHERE car_id = %s", (car_id,))
        if not chk or chk[0]['c'] == 0:
            raise HTTPException(status_code=404, detail="The vehicle does not exist")
        MySQL_Run("DELETE FROM car_resource WHERE car_id = %s", (car_id,))
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        print("delete_car_resource error:", e)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/cars/stats")
def get_car_stats():
    try:
        total_res = MySQL_Run("SELECT COUNT(*) as total FROM car_resource")
        total = total_res[0]['total'] if total_res else 0

        status_rows = MySQL_Run("SELECT car_status, COUNT(*) as count FROM car_resource GROUP BY car_status")
        status_counts = {key: 0 for key in ['service', 'paused', 'maintenance', 'retired']}
        for row in status_rows:
            key = row.get('car_status')
            if key in status_counts:
                status_counts[key] = row.get('count', 0)

        new_rows = MySQL_Run("""
            SELECT COUNT(*) AS cnt
            FROM car_resource
            WHERE commission_date IS NOT NULL
              AND DATE_FORMAT(commission_date, '%Y-%m') = DATE_FORMAT(CURDATE(), '%Y-%m')
        """)
        new_this_month = new_rows[0]['cnt'] if new_rows else 0

        return {
            'success': True,
            'data': {
                'total': total,
                'new_this_month': new_this_month,
                'status_counts': status_counts
            }
        }
    except Exception as e:
        print('get_car_stats error:', e)
        raise HTTPException(status_code=500, detail=str(e))

# ============ Member Management: Permission Protection ===========

@app.post("/Create_users")
def create_user(user: UserCreate, db: Session = Depends(get_db), current_user: AdminUser = Depends(get_current_user)):
    # Only super_admin and admin can add new members; dispatcher prohibits
    role = get_role_by_id(db, current_user.role_id)
    if not role or role.role_name not in ("super_admin", "admin"):
        raise HTTPException(status_code=403, detail="No permission to add new members")

    user_data = user.dict(exclude_unset=True)
    
    # Handle passwords
    if user_data.get('password') and isinstance(user_data['password'], str) and user_data['password'].strip():
        hashed_password = bcrypt.hashpw(user_data['password'].encode('utf-8'), bcrypt.gensalt())
        user_data['password'] = hashed_password.decode('utf-8')
    else:
        user_data['password'] = None
    
    optional_fields = ['preferences', 'privacy_settings', 'reservation_status']
    for field in optional_fields:
        if field in user_data:
            if not user_data[field] or (isinstance(user_data[field], str) and not user_data[field].strip()):
                user_data[field] = None

    if not user_data.get('reservation_status') or user_data.get('reservation_status') == 'None':
        user_data['reservation_status'] = 'no_reservation'

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
    return {"user_id": new_user.user_id, "message": "User creation successfully"}

@app.put("/users/{user_id}")
def update_user(user_id: int, user: UserUpdate, db: Session = Depends(get_db), current_user: AdminUser = Depends(get_current_user)):
    role = get_role_by_id(db, current_user.role_id)
    if not role or role.role_name not in ("super_admin", "admin"):
        raise HTTPException(status_code=403, detail="No permission to update members")

    user_data = user.dict(exclude_unset=True)
    target = db.query(User).filter(User.user_id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="The user does not exist")

    if 'password' in user_data and user_data['password']:
        hashed_password = bcrypt.hashpw(user_data['password'].encode('utf-8'), bcrypt.gensalt())
        user_data['password'] = hashed_password.decode('utf-8')
    elif 'password' in user_data:
        user_data['password'] = target.password

    # Clean up blank strings
    for k in ['preferences', 'privacy_settings']:
        if k in user_data and isinstance(user_data[k], str) and not user_data[k].strip():
            user_data[k] = None

    for key, value in user_data.items():
        setattr(target, key, value)
    try:
        target.updated_at = get_taiwan_datetime()
    except Exception:
        pass
    db.commit()
    return {"message": "User update successfully"}

@app.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), current_user: AdminUser = Depends(get_current_user)):
    role = get_role_by_id(db, current_user.role_id)
    if not role or role.role_name not in ("super_admin", "admin"):
        raise HTTPException(status_code=403, detail="No permission to delete a member")

    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="The user does not exist")
    db.delete(user)
    db.commit()
    return {"message": "User deletion successfully"}




def _sanitize_qr_prefix(candidate: Optional[str], route_id: int) -> str:
    raw_value = (candidate or f"route_{route_id}").strip()
    cleaned = ''.join(ch if ch.isalnum() or ch in {'-', '_'} else '_' for ch in raw_value)
    cleaned = cleaned.strip('_-')
    return cleaned or f"route_{route_id}"

@app.post("/api/tools/qr-codes")
def generate_route_qr_codes(
    payload: QrCodeRequest,
    current_user: AdminUser = Depends(get_current_user),
):
    if payload.stop_count > 200:
        raise HTTPException(status_code=400, detail="Stop count is limited to 200 per request.")

    base_url = payload.base_url.rstrip("/")
    prefix = _sanitize_qr_prefix(payload.output_prefix, payload.route_id)

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for stop in range(1, payload.stop_count + 1):
            stop_url = f"{base_url}/routes/{payload.route_id}/stop/{stop}"
            qr_image = qrcode.make(stop_url)
            image_buffer = io.BytesIO()
            qr_image.save(image_buffer, format="PNG")
            image_buffer.seek(0)
            archive.writestr(f"{prefix}_stop{stop}.png", image_buffer.read())

    zip_buffer.seek(0)
    filename = f"{prefix}_qr_codes.zip"
    headers = {"Content-Disposition": f"attachment; filename={filename}"}
    return StreamingResponse(zip_buffer, media_type="application/zip", headers=headers)

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8500, reload=True)

@app.get("/", response_class=FileResponse)
def serve_frontend_root():
    if INDEX_FILE.exists():
        return FileResponse(INDEX_FILE)
    raise HTTPException(status_code=404, detail="Frontend build not found")


@app.get("/{full_path:path}", response_class=FileResponse)
def serve_frontend_router(full_path: str):
    if full_path.startswith("api/") or full_path.startswith("auth/"):
        raise HTTPException(status_code=404, detail="Not Found")
    candidate = DIST_DIR / full_path
    if candidate.is_file():
        return FileResponse(candidate)
    if INDEX_FILE.exists():
        return FileResponse(INDEX_FILE)
    raise HTTPException(status_code=404, detail="Frontend build not found")

