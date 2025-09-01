from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import create_engine, Column, String, TIMESTAMP, JSON, Boolean, Integer, ForeignKey, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
import uuid
import os
from dotenv import load_dotenv
from pydantic import BaseModel
import bcrypt
import uvicorn

DB_USER = "postgres"
DB_PASSWORD = "109109"
DB_HOST = "192.168.0.126"
DB_PORT = "5432"
DB_NAME = "postgres"

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class LoginRequest(BaseModel):
    username: str
    password: str

# 使用者會員管理表模型（對應現有表）
class User(Base):
    __tablename__ = "users"
    __table_args__ = {'schema': 'bus_system'}
    
    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    line_id = Column(String(100), unique=True)
    username = Column(String(100))
    email = Column(String(255))
    phone = Column(String(20))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    last_login = Column(TIMESTAMP(timezone=True))
    status = Column(String(20), default='active')
    preferences = Column(JSON, default={})
    privacy_settings = Column(JSON, default={})

# 權限角色表模型
class AdminRole(Base):
    __tablename__ = "admin_roles"
    __table_args__ = {'schema': 'bus_system'}
    
    role_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role_name = Column(String(100), unique=True, nullable=False)
    role_description = Column(String)
    permissions = Column(JSON, default={})
    is_system_role = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

# 後台帳號權限管理表模型
class AdminUser(Base):
    __tablename__ = "admin_users"
    __table_args__ = {'schema': 'bus_system'}
    
    admin_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role_id = Column(UUID(as_uuid=True), ForeignKey('bus_system.admin_roles.role_id'))
    last_login = Column(TIMESTAMP(timezone=True))
    login_attempts = Column(Integer, default=0)
    status = Column(String(20), default='active')
    created_by = Column(UUID(as_uuid=True), ForeignKey('bus_system.admin_users.admin_id'))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # 關聯
    role = relationship("AdminRole")

app = FastAPI(title="花蓮小巴會員管理系統")

# 模擬當前登入的用戶（實際應用中應從 JWT token 獲取）
current_admin_user = None

def get_db():
    """取得資料庫連線"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(db):
    """獲取當前登入的用戶"""
    if not current_admin_user:
        raise HTTPException(status_code=401, detail="未登入")
    
    user = db.query(AdminUser).filter(AdminUser.admin_id == current_admin_user).first()
    if not user:
        raise HTTPException(status_code=401, detail="用戶不存在")
    return user

def check_permission(user, action):
    """檢查用戶權限"""
    if not user.role:
        return False
    
    permissions = user.role.permissions
    
    # admin 可以做所有事情
    if user.role.role_name == "super_admin" or permissions.get("all") == True:
        return True
    
    # user 只能讀取
    if user.role.role_name == "user":
        return action == "read"
    
    return False

@app.post("/auth/login")
def login(request: LoginRequest, db = Depends(get_db)):
    """管理員登入 - 使用 bcrypt 驗證雜湊密碼"""
    global current_admin_user
    
    # 從資料庫查詢用戶
    admin_user = db.query(AdminUser).filter(AdminUser.username == request.username).first()
    
    if not admin_user:
        raise HTTPException(status_code=401, detail="用戶名不存在")
    
    # 使用 bcrypt 驗證雜湊密碼
    try:
        if not bcrypt.checkpw(request.password.encode('utf-8'), admin_user.password_hash.encode('utf-8')):
            raise HTTPException(status_code=401, detail="密碼錯誤")
    except Exception as e:
        raise HTTPException(status_code=401, detail="密碼驗證失敗")
    
    # 登入成功，設定當前用戶
    current_admin_user = admin_user.admin_id
    
    return {
        "message": "登入成功",
        "username": admin_user.username,
        "role": admin_user.role.role_name if admin_user.role else "unknown",
        "user_id": str(admin_user.admin_id)
    }


@app.get("/users")
def read_users(db = Depends(get_db)):
    """讀取所有用戶"""
    current_user = get_current_user(db)
    
    # 檢查權限
    if not check_permission(current_user, "read"):
        raise HTTPException(status_code=403, detail="權限不足")
    
    users = db.query(User).all()
    return [{"user_id": str(u.user_id), "username": u.username, "email": u.email, "status": u.status} for u in users]

@app.get("/users/{user_id}")
def read_user(user_id: str, db = Depends(get_db)):
    """讀取單個用戶"""
    current_user = get_current_user(db)
    
    # 檢查權限
    if not check_permission(current_user, "read"):
        raise HTTPException(status_code=403, detail="權限不足")
    
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用戶不存在")
    
    return {
        "user_id": str(user.user_id),
        "username": user.username,
        "email": user.email,
        "phone": user.phone,
        "status": user.status,
        "created_at": user.created_at
    }

@app.post("/users")
def create_user(username: str, email: str, db = Depends(get_db)):
    """建立新用戶（只有 admin 可以）"""
    current_user = get_current_user(db)
    
    # 檢查權限
    if not check_permission(current_user, "write"):
        raise HTTPException(status_code=403, detail="權限不足，只有 admin 可以建立用戶")
    
    user = User(username=username, email=email)
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return {
        "user_id": str(user.user_id),
        "username": user.username,
        "email": user.email,
        "message": "用戶建立成功"
    }

@app.put("/users/{user_id}")
def update_user(user_id: str, username: str = None, email: str = None, db = Depends(get_db)):
    """更新用戶（只有 admin 可以）"""
    current_user = get_current_user(db)
    
    # 檢查權限
    if not check_permission(current_user, "write"):
        raise HTTPException(status_code=403, detail="權限不足，只有 admin 可以更新用戶")
    
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用戶不存在")
    
    if username:
        user.username = username
    if email:
        user.email = email
    
    db.commit()
    db.refresh(user)
    
    return {
        "user_id": str(user.user_id),
        "username": user.username,
        "email": user.email,
        "message": "用戶更新成功"
    }

@app.delete("/users/{user_id}")
def delete_user(user_id: str, db = Depends(get_db)):
    """刪除用戶（只有 admin 可以）"""
    current_user = get_current_user(db)
    
    # 檢查權限
    if not check_permission(current_user, "write"):
        raise HTTPException(status_code=403, detail="權限不足，只有 admin 可以刪除用戶")
    
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用戶不存在")
    
    db.delete(user)
    db.commit()
    
    return {"message": "用戶刪除成功"}

@app.get("/permissions")
def get_permissions(db = Depends(get_db)):
    """查看當前用戶權限"""
    current_user = get_current_user(db)
    
    return {
        "username": current_user.username,
        "role": current_user.role.role_name if current_user.role else "unknown",
        "permissions": current_user.role.permissions if current_user.role else {},
        "can_read": check_permission(current_user, "read"),
        "can_write": check_permission(current_user, "write")
    }

@app.get("/routes/description")
def get_all_route_descriptions(db = Depends(get_db)):
    """回傳所有 route 的 description（需有 read 權限）"""
    current_user = get_current_user(db)
    if not check_permission(current_user, "read"):
        raise HTTPException(status_code=403, detail="權限不足")
    
    res = db.execute(text("SELECT route_id, route, description FROM bus_system.bus_routes")).fetchall()
    if not res:
        return {"routes": []}
    
    routes = [{"route": row[1], "route_id": str(row[0]), "description": row[2]} for row in res]
    return {"routes": routes}

@app.get("/routes/{route}/stations/{station_order}")
def get_station_details(route: str, station_order: int, db = Depends(get_db)):
    """回傳指定路線與站別順序的站點詳細資訊（需有 read 權限）
    
    若 station_order 為 0，則回傳該路線所有站點的資訊列表。
    """
    current_user = get_current_user(db)
    if not check_permission(current_user, "read"):
        raise HTTPException(status_code=403, detail="權限不足")
    
    # 取得 route_id
    route_res = db.execute(text("SELECT route_id FROM bus_system.bus_routes WHERE route = :route"), {"route": route}).fetchone()
    if not route_res:
        raise HTTPException(status_code=404, detail="route 不存在")
    
    route_id = route_res[0]
    
    # 動態表名
    table_name = f"bus_route_{route}"
    
    if station_order == 0:
        # 查詢所有站點
        query = text(f"SELECT station_name, longitude, latitude, interval_minutes, station_order FROM bus_system.{table_name} WHERE route_id = :route_id ORDER BY station_order")
        res = db.execute(query, {"route_id": route_id}).fetchall()
        
        if not res:
            return {"stations": []}
        
        stations = [
            {
                "station_name": row[0],
                "longitude": float(row[1]) if row[1] else None,
                "latitude": float(row[2]) if row[2] else None,
                "interval_minutes": row[3],
                "station_order": row[4]
            }
            for row in res
        ]
        return {"stations": stations}
    else:
        # 查詢單個站點
        query = text(f"SELECT station_name, longitude, latitude, interval_minutes FROM bus_system.{table_name} WHERE route_id = :route_id AND station_order = :station_order")
        res = db.execute(query, {"route_id": route_id, "station_order": station_order}).fetchone()
        
        if not res:
            raise HTTPException(status_code=404, detail="站點不存在")
        
        station_name, longitude, latitude, interval_minutes = res
        return {
            "station_name": station_name,
            "longitude": float(longitude) if longitude else None,
            "latitude": float(latitude) if latitude else None,
            "interval_minutes": interval_minutes
        }

@app.get("/")
def root():
    return {
        "message": "花蓮小巴會員管理系統",
        "status": "運行中",
        "features": ["用戶管理", "權限控制", "資料庫串聯"]
    }

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8001, reload=True)