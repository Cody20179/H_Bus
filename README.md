# 🚌 Hualien Bus System — 後端伺服器與前端介面

一個整合路線資訊、訂單管理與電子支付的巴士系統。
本專案包含 FastAPI 後端、React 前端與 MariaDB/Redis 資料庫。

---

## 📁 專案結構

```
H_Bus/
 ├─ Server.py               # FastAPI 主程式
 ├─ Backend/                # MySQL、Redis、加密與公用模組
 ├─ Client/                 # React 前端
 │   ├─ src/
 │   └─ package.json
 ├─ .env                    # 系統環境設定檔
 ├─ requirements.txt        # Python 套件
 └─ README.md
```

---

## ⚙️ 1. 建立 `.env`

在專案根目錄建立 `.env` 檔案，內容如下：

```bash
# Route(https)
FRONTEND_DEFAULT_URL=https://你的網域

# Line
LINE_CHANNEL_ID=你的_LINE_開發者_ID
LINE_CHANNEL_SECRET=你的_LINE_SECRET

# Session PW
APP_SESSION_SECRET=自訂密碼

# Email
Sender_email=你的_Gmail_帳號
Password_email=你的_Google_App_Password

# MySQL
Host=xxx.xxx.xxx.xxx
User=root
Port=3307
Password_SQL=你的密碼
Database=bus_system

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Payment
MERCHANT_ID=106952201270001
TERMINAL_ID=70002146
STORE_CODE=e4f76eb8-d236-45fb-984b-92b2d1912492
KEY=3abae022acd6fc873821411c0b402c0fbe90d90bdda295ed15296f8ae465bf8b
IV=12fe9f5e0c3cc7c664894f19ba265050
LAYMON=iqrc.epay365.com.tw
```

---

## 🧱 2. 資料庫設定

### MariaDB

1. 安裝 MariaDB  
   ```bash
   sudo apt install mariadb-server
   ```
2. 建立資料庫：
   ```sql
   CREATE DATABASE bus_system CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
   ```
3. 匯入資料表（如有提供 `bus_system.sql`）：
   ```bash
   mysql -u root -p bus_system < bus_system.sql
   ```

### Redis

安裝與啟動：
```bash
sudo apt install redis-server
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

---

## 🐍 3. 安裝 Python 套件 從此開始進入 Client 資料夾
pip install -r requirements.txt

## 💻 4. 安裝前端套件

進入前端目錄並安裝依賴：
npm install
---

## 🚀 5. 啟動系統

### 啟動前後端：

先進行 npm run build 建立dict

伺服器預設會啟動在：
```
uvicorn Server:app --host 0.0.0.0 --port 8700 --reload --ssl-keyfile "位置-key.pem" --ssl-certfile "位置.-chain.pem"
```