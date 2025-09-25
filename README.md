# H_Bus 專案說明

H_Bus 是一個「公車路線與預約」的全端範例專案：
- 前端使用 React + Vite，提供路線瀏覽、站點查詢、附近站點地圖、個人頁面與預約管理。
- 後端使用 FastAPI 提供 REST API，整合 MySQL（資料儲存）、Redis（session 快取）、LINE Login（OAuth 登入）。
- 開發/展示常透過 ngrok 對外公開 callback 與前端網址。

---

## 專案結構

```
Github/H_Bus/
├─ Backend/                   # 後端 FastAPI 服務
│  ├─ Server.py               # 主應用：API、CORS、LINE OAuth、靜態檔託管
│  ├─ MySQL.py                # MySQL 封裝（pymysql），含簡易 ORM/工具
│  ├─ Define.py               # Pydantic 模型（請求/回應 schema）
│  ├─ dist/                   # 由前端 build 產物拷貝至此，FastAPI 負責提供
│  ├─ .env                    # 後端環境變數（不要上傳到版本庫）
│  ├─ Debus.ipynb             # 內部測試/實驗 Notebook（含 Redis/MySQL 片段）
│  ├─ GIS.yaml                # GIS 相關設定（示意）
│  ├─ GIS模擬.py               # GIS 測試/模擬程式（示意）
│  └─ Sent_Bus_Eail.py        # 郵件相關腳本（示意）
│
└─ client/                    # 前端 React + Vite 專案
   ├─ package.json            # 前端依賴與指令
   ├─ src/
   │  ├─ pages/               # Routes.jsx, Profile.jsx 等頁面
   │  ├─ components/          # RouteDetail.jsx, NearbyStations.jsx 等元件
   │  ├─ services/api.js      # 與後端 API 互動封裝
   │  └─ data/                # 靜態站點資料（由 scripts 轉換產生）
   └─ scripts/
      ├─ convert-stations.mjs # CSV → JS 的站點資料轉換腳本
      └─ convert-stations.ps1 # 同上 PowerShell 版本
```

---

## 主要技術與服務

- 後端：FastAPI、Starlette、httpx、python-dotenv、pydantic、pandas
- 資料庫：MySQL（pymysql）
- 快取 / Session：Redis
- 登入：LINE Login（OAuth 2.0 / OpenID Connect）
- 前端：React、React Router、Vite、Leaflet
- 通道：ngrok（方便 LINE 回呼與前端對外存取）

---

## 環境變數（Backend/.env）

請在 `Backend/.env` 設定必要變數（請勿提交到版本庫）：

```
# LINE Login
LINE_CHANNEL_ID=...
LINE_CHANNEL_SECRET=...

# Session
APP_SESSION_SECRET=...  # 用於簽發/驗證自家 session token

# 前端入口（常為 ngrok 產生之 HTTPS 網址，用於 CORS 及回呼）
FRONTEND_DEFAULT_URL=https://<your-id>.ngrok-free.app

# Redis（預設本機）
REDIS_URL=redis://localhost:6379/0

# MySQL（供 MySQL_Doing 使用；MySQL_Run 目前在 MySQL.py 中用 Infor 常數）
Host=127.0.0.1
User=root
Port=3306
Password_SQL=your_password
Database=bus_system
```

注意：`MySQL.py` 內的 `Infor` 目前採用硬編碼（host/user/port/password/database）。正式環境建議改為走環境變數或安全管道，避免把密碼寫進程式碼。

---

## 開發前置

- Python 3.10+（建議使用虛擬環境）
- Node.js 18+ / 20+
- MySQL 8.x（或相容版本）
- Redis 6+（或相容版本）
- ngrok（可選，用於對外 callback 與前端網址）

---

## 安裝與啟動

### 1) 後端（FastAPI）

1. 切到 Backend 目錄並安裝相依：
   - 建議的 Python 套件：`fastapi`, `uvicorn[standard]`, `redis`, `httpx`, `pymysql`, `python-dotenv`, `pandas`, `pydantic`
   - 例：
     ```bash
     cd Backend
     pip install fastapi "uvicorn[standard]" redis httpx pymysql python-dotenv pandas pydantic
     ```
2. 啟動 API：
   ```bash
   uvicorn Server:app --reload --host 0.0.0.0 --port 8000
   ```
3. Redis 與 MySQL 請先就緒，並確認 `Backend/.env` 已設定正確變數。

### 2) 前端（React + Vite）

1. 安裝依賴並啟動開發伺服器：
   ```bash
   cd client
   npm install
   # 在開發模式建議設定 API 端點（避免同源 /api 代理問題）
   set VITE_API_BASE_URL=http://localhost:8000/api  # Windows（PowerShell 可用 $env:VITE_API_BASE_URL）
   npm run dev
   ```
   - 沒設 `VITE_API_BASE_URL` 時，程式會在 dev 模式預設呼叫 `/api`；若未設定 Vite 代理，建議手動指定完整 URL。

2. 產出正式前端靜態檔案：
   ```bash
   npm run build
   # 將 client/dist 內容拷貝到 Backend/dist，交由 FastAPI 提供
   # 例如：
   # Windows PowerShell
   Remove-Item -Recurse -Force ..\Backend\dist\*
   Copy-Item -Recurse -Force dist\* ..\Backend\dist\
   ```
   - Backend 會以 `StaticFiles(directory='dist', html=True)` 對外提供（見 `Backend/Server.py:504`）。

---

## 重要 API（擇要）

- `GET /healthz`：健康檢查。
- `GET /api/All_Route`：取得所有公車路線。
- `POST /api/Route_Stations`：查詢路線的站點列表。
  - Body 例：`{ "route_id": 1, "direction": "去程|回程|循環" }`（`direction` 可省略）
- `GET /api/yo_hualien`：旅遊/站點資料（範例）。
- `POST /api/reservation`：新增預約。
- `GET /api/reservations/my?user_id=...`：查詢我的預約。
- `GET /api/reservations/tomorrow?user_id=...`：查詢明日預約（已核准）。
- `POST /api/reservations/Canceled`：取消預約。
- `POST /api/users/update_mail?user_id=...&email=...`：更新使用者 Email。
- `POST /api/users/update_phone?user_id=...&phone=...`：更新使用者手機。
- `GET /auth/line/login`：發起 LINE Login。
- `GET /auth/line/callback`：LINE Login 回呼。
- `GET /logout`：登出（清除 cookie）。
- `GET /me`：查詢目前登入使用者（依 cookie session）。

端點定義與實作可見：`Backend/Server.py`（例如：`Backend/Server.py:380` 登入、`Backend/Server.py:416` 回呼）。

---

## 前端頁面與功能（擇要）

- `client/src/pages/Routes.jsx`：路線列表、站點查詢。
- `client/src/components/RouteDetail.jsx`：單一路線細節與站序。
- `client/src/components/NearbyStations.jsx`：附近站點（Leaflet 地圖、定位）。
- `client/src/pages/Profile.jsx`：LINE 登入、我的預約、聯絡方式更新、登出。
- `client/src/services/api.js`：與後端 API 溝通。

靜態站點資料可透過轉換腳本產生：
```
cd client
npm run convert:stations  src/data/Station.csv  src/data/stations.js
```
生成後可由元件匯入使用，例如 `client/src/components/NearbyStations.jsx`。

---

## CORS 與 ngrok 說明

- 後端允許的 CORS 來源在 `Server.py` 中以正則表示式包含 `*.ngrok-free.app` 與常見私網/本機網段。
- `FRONTEND_DEFAULT_URL` 建議設定為對外可達的 HTTPS 網址（例如 ngrok），以配合 LINE OAuth 的 redirect_uri 與前端導頁。

---

## 安全注意事項

- 請勿將 `Backend/.env`、密鑰（LINE_CHANNEL_SECRET、APP_SESSION_SECRET）及資料庫密碼提交到版本庫。
- 若敏感資訊已意外提交，請儘速「重設金鑰」並清理 commit 歷史。
- 建議將 `MySQL.py` 內的硬編碼連線資訊改為走環境變數或安全設定來源。

---

## 疑難排解（FAQ）

- 前端開發時 API 404 或 CORS 錯誤：
  - 確認 `VITE_API_BASE_URL` 指向正確（如 `http://localhost:8000/api`）。
  - 或設定 Vite 代理到後端 `/api`。
- LINE Login 回呼失敗：
  - 確認 `FRONTEND_DEFAULT_URL` 與 LINE Developers 的回呼網址一致（HTTPS、可對外）。
  - 檢查 `LINE_CHANNEL_ID/SECRET` 是否正確，伺服器系統時間是否同步。
- Redis 未連上：
  - 檢查 `REDIS_URL` 與 Redis 服務狀態。
- MySQL 連線錯誤：
  - 檢查帳密、連線埠與 DB 名稱，並確保有對應資料表。

---

## 授權

未指定擁有授權。若需對外發布，請先補上 LICENSE 並審視第三方服務條款。

