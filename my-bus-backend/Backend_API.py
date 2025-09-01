# Backend_API.py
import os
import csv
import json
import tempfile
import secrets
from datetime import datetime, timedelta
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Request, Response, Depends, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from passlib.hash import bcrypt
import jwt

# -------------------------
# Config (可用環境變數覆寫)
# -------------------------
CSV_PATH = os.getenv('USERS_CSV', 'users.csv')
JWT_SECRET = os.getenv('JWT_SECRET', 'please_change_this_secret')
ACCESS_EXPIRE_MINUTES = int(os.getenv('ACCESS_EXPIRE_MINUTES', '15'))
FRONTEND_ORIGINS = os.getenv('FRONTEND_ORIGINS', 'http://localhost:5173')  # 用逗號分隔多個 origin
COOKIE_NAME = os.getenv('COOKIE_NAME', 'access_token')
COOKIE_SECURE = os.getenv('COOKIE_SECURE', 'false').lower() == 'true'  # production: True
COOKIE_SAMESITE = os.getenv('COOKIE_SAMESITE', 'lax')  # 'lax' or 'strict'

CSV_HEADERS = ['id', 'username', 'password_hash', 'role', 'permissions']

# ---------------
# FastAPI App
# ---------------
app = FastAPI(title="Auth CSV Example")

origins = [o.strip() for o in FRONTEND_ORIGINS.split(',') if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------
# Pydantic models
# ---------------
class LoginIn(BaseModel):
    username: str
    password: str

# ----------------
# CSV utilities
# ----------------
def ensure_csv_exists():
    """確保 CSV 存在並有 header。"""
    created = False
    if not os.path.exists(CSV_PATH):
        with open(CSV_PATH, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADERS)
        created = True
    else:
        # 檢查 header 是否存在（簡易）
        with open(CSV_PATH, newline='', encoding='utf-8') as f:
            rdr = csv.reader(f)
            first = next(rdr, None)
        if not first or any(h not in first for h in CSV_HEADERS):
            # 備份並覆寫（保守做法）
            with open(CSV_PATH, 'r', encoding='utf-8') as f:
                existing = f.read()
            with open(CSV_PATH, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(CSV_HEADERS)
                f.write(existing)
            created = True
    return created

def load_users():
    """讀取 CSV 回傳 dict keyed by username"""
    ensure_csv_exists()
    with open(CSV_PATH, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        users = {}
        for r in reader:
            try:
                perms = json.loads(r.get('permissions') or '[]')
            except:
                perms = []
            # 忽略空行或不完整行
            if not r.get('username') or not r.get('id'):
                continue
            users[r['username']] = {
                'id': int(r['id']),
                'username': r['username'],
                'password_hash': r.get('password_hash', ''),
                'role': r.get('role', ''),
                'permissions': perms
            }
        return users

def save_users(users_dict):
    """users_dict keyed by username -> save to CSV atomically"""
    rows = sorted(users_dict.values(), key=lambda x: x['id'])
    fd, tmp_path = tempfile.mkstemp(prefix='users_', suffix='.csv', dir='.')
    try:
        with os.fdopen(fd, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADERS)
            for u in rows:
                writer.writerow([u['id'], u['username'], u.get('password_hash',''), u.get('role',''), json.dumps(u.get('permissions',[]), ensure_ascii=False)])
        os.replace(tmp_path, CSV_PATH)
    except Exception:
        try:
            os.remove(tmp_path)
        except:
            pass
        raise

def next_user_id(users):
    if not users:
        return 1
    return max(u['id'] for u in users.values()) + 1

def append_user_row(id, username, password_hash, role, permissions):
    ensure_csv_exists()
    with open(CSV_PATH, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([id, username, password_hash, role, json.dumps(permissions, ensure_ascii=False)])

# ----------------
# JWT helpers
# ----------------
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    token = jwt.encode(to_encode, JWT_SECRET, algorithm="HS256")
    return token

def decode_token(token: str):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token 過期")
    except Exception:
        raise HTTPException(status_code=401, detail="Token 無效")

def get_token_from_request(request: Request):
    token = None
    if COOKIE_NAME in request.cookies:
        token = request.cookies.get(COOKIE_NAME)
    else:
        auth = request.headers.get("Authorization")
        if auth and auth.startswith("Bearer "):
            token = auth.split(" ", 1)[1]
    if not token:
        raise HTTPException(status_code=401, detail="未提供 token")
    return token

async def get_current_user(request: Request):
    token = get_token_from_request(request)
    payload = decode_token(token)
    users = load_users()
    for u in users.values():
        if u['id'] == int(payload.get('sub')):
            # 附帶 id 欄，回傳使用者物件
            return u
    raise HTTPException(status_code=401, detail="使用者不存在")

# ---------------
# Endpoints (auth)
# ---------------
@app.post("/api/auth/login")
async def login(data: LoginIn, response: Response):
    users = load_users()
    u = users.get(data.username)
    if not u:
        raise HTTPException(status_code=401, detail="帳號或密碼錯誤")

    if not bcrypt.verify(data.password, u['password_hash']):
        raise HTTPException(status_code=401, detail="帳號或密碼錯誤")

    token = create_access_token({"sub": u['id'], "username": u['username'], "role": u['role']},
                                expires_delta=timedelta(minutes=ACCESS_EXPIRE_MINUTES))

    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite=COOKIE_SAMESITE,
        secure=COOKIE_SECURE,
        max_age=ACCESS_EXPIRE_MINUTES * 60
    )

    return {
        "success": True,
        "user": {
            "id": u['id'],
            "username": u['username'],
            "role": u.get('role'),
            "permissions": u.get('permissions', [])
        }
    }

@app.get("/api/auth/me")
async def me(user=Depends(get_current_user)):
    return {"success": True, "user": {"id": user['id'], "username": user['username'], "role": user.get('role'), "permissions": user.get('permissions', [])}}

@app.post("/api/auth/logout")
async def logout(response: Response):
    response.delete_cookie(COOKIE_NAME)
    return {"success": True, "message": "已登出"}

# ----------------
# User management endpoints (CSV)
# ----------------
@app.get("/api/users")
async def list_users(current=Depends(get_current_user)):
    # 只有 admin 可以列出所有使用者
    if current.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="無權限")
    users = load_users()
    out = []
    for u in users.values():
        out.append({'id': u['id'], 'username': u['username'], 'role': u.get('role'), 'permissions': u.get('permissions', [])})
    return {"success": True, "users": out}

@app.post("/api/users")
async def create_user(data: dict = Body(...), current=Depends(get_current_user)):
    # 只有 admin 可以新增
    if current.get('role') != 'admin':
        raise HTTPException(status_code=403, detail="無新增使用者權限")
    username = data.get('username')
    password = data.get('password')
    role = data.get('role', 'user')
    permissions = data.get('permissions', [])
    if not username or not password:
        raise HTTPException(status_code=400, detail="缺少 username 或 password")
    users = load_users()
    if username in users:
        raise HTTPException(status_code=400, detail="使用者已存在")
    nid = next_user_id(users)
    pwd_hash = bcrypt.hash(password)
    users[username] = {'id': nid, 'username': username, 'password_hash': pwd_hash, 'role': role, 'permissions': permissions}
    save_users(users)
    return {'success': True, 'user': {'id': nid, 'username': username, 'role': role, 'permissions': permissions}}

@app.put("/api/users/{user_id}")
async def update_user(user_id: int, data: dict = Body(...), current=Depends(get_current_user)):
    users = load_users()
    # 找 target user
    target = None
    for u in users.values():
        if u['id'] == user_id:
            target = u
            break
    if not target:
        raise HTTPException(status_code=404, detail="使用者不存在")
    # 權限：admin 或 自己
    if current.get('role') != 'admin' and current.get('id') != user_id:
        raise HTTPException(status_code=403, detail="無權限")
    # 本人不可改 role
    if 'role' in data and current.get('role') != 'admin':
        data.pop('role', None)
    # 更新 username、role、permissions
    old_username = target['username']
    new_username = data.get('username', old_username)
    if new_username != old_username:
        if new_username in users and users[new_username]['id'] != user_id:
            raise HTTPException(status_code=400, detail="新的 username 已存在")
        # 移動 key
        users.pop(old_username)
        target['username'] = new_username
        users[new_username] = target
    # 更新其它欄位
    if 'role' in data and current.get('role') == 'admin':
        target['role'] = data.get('role')
    if 'permissions' in data:
        target['permissions'] = data.get('permissions', [])
    save_users(users)
    return {'success': True, 'user': {'id': target['id'], 'username': target['username'], 'role': target.get('role'), 'permissions': target.get('permissions', [])}}

@app.put("/api/users/{user_id}/password")
async def change_password(user_id: int, data: dict = Body(...), current=Depends(get_current_user)):
    old_pwd = data.get('old_password')
    new_pwd = data.get('new_password')
    if not new_pwd:
        raise HTTPException(status_code=400, detail="new_password 必填")
    users = load_users()
    target = None
    for u in users.values():
        if u['id'] == user_id:
            target = u
            break
    if not target:
        raise HTTPException(status_code=404, detail="使用者不存在")
    if current.get('role') != 'admin':
        if current.get('id') != user_id:
            raise HTTPException(status_code=403, detail="無權限")
        if not old_pwd or not bcrypt.verify(old_pwd, target['password_hash']):
            raise HTTPException(status_code=401, detail="舊密碼錯誤")
    target['password_hash'] = bcrypt.hash(new_pwd)
    users[target['username']] = target
    save_users(users)
    return {'success': True, 'message': '密碼已更新'}

# ----------------
# CSV auto-create default admin on startup
# ----------------
def create_default_admin_if_needed():
    created = ensure_csv_exists()
    users = load_users()
    if users:
        return
    default_pw = os.getenv('DEFAULT_ADMIN_PW')
    if not default_pw:
        default_pw = secrets.token_urlsafe(9)
        print("[注意] 未提供 DEFAULT_ADMIN_PW，系統自動產生 admin 密碼（請登入後立即修改）:")
        print("    ADMIN username: admin")
        print(f"    ADMIN password: {default_pw}")
    pw_hash = bcrypt.hash(default_pw)
    append_user_row(1, 'admin', pw_hash, 'admin', ['routes:read', 'routes:write'])
    print("[Info] 已在 users.csv 建立預設 admin 帳號 (username='admin')")

@app.on_event("startup")
async def startup_event():
    create_default_admin_if_needed()

# ----------------
# Run server (if executed directly)
# ----------------
if __name__ == "__main__":
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', '8000'))
    uvicorn.run("Backend_API:app", host=host, port=port, reload=True)
