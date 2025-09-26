# H_Bus 客戶端與後端整合專案

## 專案簡介
- H_Bus 為花蓮小巴預約與即時資訊平台，整合行動網頁、LINE Login 與預約管理流程。
- 前端採 React + Vite 開發，提供路線查詢、站點到站預估、預約紀錄與個人資訊維護功能。
- 後端使用 FastAPI，負責 LINE OAuth 流程、資料寫入 MariaDB、Redis 快取、郵件提醒任務以及靜態檔案服務。

## 系統架構
- 單一倉庫同時包含前端 (src/) 與後端 (Server.py, Backend/) 程式碼。
- FastAPI 以 uvicorn 啟動，掛載 React 編譯後的 dist/ 靜態資源，並提供 /api/* REST 介面與 /auth/* 登入流程。
- MariaDB 儲存路線、站點、預約、使用者等業務資料；Redis 儲存 LINE OAuth 狀態、session 與暫存資料。
- LINE 官方帳號做為登入入口，可搭配 
grok 暴露本機網址給 LINE 回呼使用。
- Sent_Bus_Eail.py 結合 APScheduler，每日 08:00 依預約情況寄送提醒信件。

`	ext
Client/
├─ Backend/               # MySQL 連線封裝與 Pydantic 定義
├─ Server.py              # FastAPI 入口 (uvicorn Server:app)
├─ Sent_Bus_Eail.py       # 預約提醒郵件排程
├─ requirements.txt       # 後端 Python 套件清單
├─ package.json           # 前端 npm 套件與指令
├─ scripts/               # 站點資料轉換工具
└─ src/                   # React 元件、頁面與服務呼叫
`

## 環境需求
- Python 3.11 以上（建議建立 venv 並啟用 pip）。
- Node.js 18 以上與 npm（建議搭配 corepack enable 使用）。
- MariaDB 10.5 以上（或相容的 MySQL），需開啟 utf8mb4。
- Redis 6 以上，提供 session 與暫存鍵值。
- ngrok 或其他可公開本機服務的穿透工具，用於 LINE OAuth 回呼與前端網址。
- LINE Developers 平台建立的 Channel，取得 CHANNEL_ID 與 CHANNEL_SECRET。

## 安裝與啟動流程
> 實際啟動前請先完成資料庫、Redis、環境變數與 ngrok 設定，以下順序對應需求列點方便檢查。

1. **pip install requirement**  
   `ash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   `

2. **npm i**  
   `ash
   npm install
   `

3. **uvicorn Server:app --host 0.0.0.0 --port 8500**  
   - 後端預設以此指令啟動；若需重新載入可加 --reload。
   - 啟動後會同時服務 /api/* 及 /（React build 後的 dist 目錄）。

4. **MariaDB set**  
   - 建議建立資料庫與使用者：
     `sql
     CREATE DATABASE bus_system CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
     CREATE USER 'hb_user'@'%' IDENTIFIED BY 'StrongPassword!';
     GRANT ALL PRIVILEGES ON bus_system.* TO 'hb_user'@'%';
     FLUSH PRIVILEGES;
     `
   - 需建立或匯入下列表格（欄位需符合程式取用）：
     - us_routes_total：路線主檔。
     - us_route_stations：站點清單，含順/逆向、站點座標與排序。
     - ction_tour_hualien：行動遊花蓮站點資訊。
     - car_backup / car_resource：車輛即時座標與路線資訊。
     - eservation：乘客預約資料（含 eview_status, payment_status）。
     - users：使用者主檔（需具 line_id, username, session_token, email, phone, last_login）。

5. **Redis**  
   - 啟動 Redis 服務，例如：edis-server。
   - 若 Redis 不在預設主機/埠，請設定 REDIS_URL（格式 edis://user:pass@host:port/db）。

6. **env set**  
   - 將 .env、.env.development 依需求填入下節的環境變數。
   - 後端會讀取 .env 取得 LINE、MariaDB、Email、Redis 等設定；前端開發伺服器會依 .env.development 的 VITE_* 變數設定 proxy。

7. **ngrok host in env**  
   - 以 
grok http 8500（或 8400，視實際提供給使用者的入口）產生公開網址。
   - 將產生的 HTTPS 網址回填至 FRONTEND_DEFAULT_URL、VITE_API_BASE_URL、VITE_AUTH_BASE_URL，並於 LINE Developers 後台設定相同的回呼網址。

### 前端開發與部署
- 本地開發：
pm run dev -- --host --port 8400
  - Vite dev server 會透過 proxy 將 /api/*、/auth/*、/me 轉送到後端。
- 建置靜態檔案：
pm run build
  - 產出的 dist/ 已由 FastAPI 掛載，啟動後端即可直接服務前端。
- 預覽建置結果：
pm run preview

### 郵件排程（可選）
- 啟動每日提醒：python Sent_Bus_Eail.py
  - 使用 APScheduler 在 Asia/Taipei 時區的每日 08:00 寄送當日核准預約信件。
  - 需先於 .env 設定 Sender_email 與 Password_email（Gmail 應用程式密碼）。

## 環境變數
| 變數 | 說明 | 範例 |
| --- | --- | --- |
| FRONTEND_DEFAULT_URL | 對使用者公開的前端網址（含 protocol），登入成功後的預設導向並決定 Cookie 屬性。 | https://xxxxx.ngrok-free.app |
| LINE_CHANNEL_ID | LINE 官方帳號的 Channel ID。 | 2008092259 |
| LINE_CHANNEL_SECRET | LINE 官方帳號的 Channel Secret。 | xxxxxxxxxxxxxxxx |
| APP_SESSION_SECRET | 後端簽發 session token 的 HMAC 金鑰，請使用長度充足的隨機字串。 | sd8f7s9df8sdf7 |
| Sender_email | 發送提醒信件的寄件者信箱。 | 
oreply@example.com |
| Password_email | 寄件者信箱的應用程式密碼或 SMTP 密碼。 | bcd efgh ijkl mnop |
| REDIS_URL | Redis 連線字串，未設定時預設 edis://localhost:6379/0。 | edis://:pass@localhost:6379/1 |
| Host | MariaDB 伺服器主機名。 | 127.0.0.1 |
| Port | MariaDB 服務埠號。 | 3306 |
| User | MariaDB 使用者。 | hb_user |
| Password_SQL | MariaDB 使用者密碼。 | StrongPassword! |
| Database | 要使用的資料庫名稱。 | us_system |
| VITE_API_BASE_URL | 前端開發伺服器 proxy 至後端 API 的基底網址。 | https://xxxxx.ngrok-free.app |
| VITE_AUTH_BASE_URL | 前端開發伺服器 proxy 至後端登入路由的基底網址。 | https://xxxxx.ngrok-free.app |

> 建議將 .env 與 .env.development 納入版本控制忽略清單，並於部署環境透過秘密管理機制注入。

## API 參考
### Meta
- GET /healthz
  - 健康檢查端點，供 LB/監控確認服務狀態。
  - 回傳：{"status": "error 404"}（可依實際需求調整內容）。

### 公車資訊 (/api namespace)
- GET /api/All_Route
  - 取得 us_routes_total 全部路線資料。
  - 回傳陣列，欄位包含 oute_id, oute_name, direction, stop_count, status, created_at 等。

- POST /api/Route_Stations
  - 依路線與方向查詢站點。請求 JSON：
    `json
    {
      "route_id": 1,
      "direction": "順行"
    }
    `
  - 回傳 StationOut 陣列，欄位含 stop_name, latitude, longitude, eta_from_start, stop_order。

- GET /api/yo_hualien
  - 讀取 ction_tour_hualien，回傳行動遊花蓮景點（站名、地址、座標）。

- GET /api/GIS_About
  - 回傳 car_backup 最新序號資料，欄位包含 oute, X, Y, direction, Current_Loaction，供前端繪製車輛位置。

### 預約作業
- POST /api/reservation
  - 建立預約。請求 JSON：
    `json
    {
      "user_id": 123,
      "booking_time": "2025-09-26T13:30:00",
      "booking_number": 2,
      "booking_start_station_name": "花蓮轉運站",
      "booking_end_station_name": "太魯閣口"
    }
    `
  - 直接寫入 eservation 表並回傳 { "status": "success" }。

- GET /api/reservations/my
  - 以 query string user_id 查詢該使用者所有預約。
  - 回傳物件 { "status": "success", "data": [...] }，陣列包含預約狀態、付款狀態與站點資訊。

- GET /api/reservations/tomorrow
  - 查詢指定 user_id 明日且已核准的預約。回傳 { "status": "success", "sql": [...] }。

- POST /api/reservations/Canceled
  - 取消預約。請求 JSON：{ "reservation_id": 1, "cancel_reason": "改期" }。
  - 更新 eview_status = 'canceled' 與 cancel_reason。

### 使用者資料
- POST /api/users/update_mail
  - 更新 Email，使用 query string 傳入 user_id, email，例如：/api/users/update_mail?user_id=1&email=test@example.com。

- POST /api/users/update_phone
  - 更新電話，使用 query string 傳入 user_id, phone。

### 認證與 session
- GET /auth/line/login
  - 開始 LINE OAuth，會根據 FRONTEND_DEFAULT_URL 與 eturn_to 決定跳轉目標。
  - 後端會在 Redis 建立 login_state:{state} 暫存 verifier 與 return URL。

- GET /auth/line/callback
  - LINE 登入回呼端點，交換 access token、寫入使用者資料、發出簽名後的 pp_session cookie。

- GET /logout
  - 清除 pp_session cookie，導回預設前端網址。

- GET /me
  - 透過 pp_session cookie 取得登入使用者資訊，若 Redis 或資料庫找不到對應 session 會回傳 401。

> Redis 主要使用下列 key：login_state:{state}, user:{line_id}, session:{token}。過期時間分別為 5 分鐘與 7 天。

## 前端關鍵模組
- src/pages/HomeView.jsx：首頁儀表板，整合路線到站預估、明日預約提示與公告。
- src/pages/Routes.jsx：路線列表與站點查詢，可依方向切換並顯示站點資訊。
- src/pages/Reserve.jsx：預約紀錄查詢與取消作業。
- src/pages/Profile.jsx：顯示登入使用者資訊並提供 Email/電話更新。
- src/services/api.js：封裝上述 REST 呼叫，處理資料格式化與錯誤處理。
- scripts/convert-stations.mjs：將原始 CSV 站點資料轉換為 JS 模組的輔助腳本（
pm run convert:stations）。

## 常見問題與建議
- **CORS**：後端預設允許 localhost、ngrok-free 及數個校內網段。若在其他網域部署需調整 llow_origin_regex。
- **Cookie 安全性**：FRONTEND_DEFAULT_URL 為 HTTPS 時，後端會將 pp_session cookie 設為 Secure + SameSite=None；若為 HTTP，則使用 SameSite=Lax。
- **LINE 回呼**：LINE Developers 後台的 Callback URL 必須與 FRONTEND_DEFAULT_URL + /auth/line/callback 完全一致，否則會出現 Invalid redirect_uri。
- **資料庫結構**：程式大量使用動態欄位命名，若欄位名稱與預期不同請於 DB 層提供 alias（例如 SELECT ... AS stop_name）。
- **排程郵件**：建議另行部署於背景執行的服務（systemd / Docker / PM2），避免與 uvicorn 單一行程耦合。

## 後續動作建議
- 部署前執行 
pm run build 並以 uvicorn 或 gunicorn+uvicorn.workers.UvicornWorker 搭配 
ginx 反向代理。
- 規劃自動化測試：可針對 /api/reservation 與 /api/reservations/* 增加單元/整合測試，確保資料庫變更時行為一致。
- 持續更新 README 中的資料庫欄位說明與開發流程，以符合實際營運需求。
