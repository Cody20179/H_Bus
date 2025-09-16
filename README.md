# H_Bus 專案說明（前後端串接與 API 文件）

本文件整理 H_Bus 專案的功能、架構、前後端網路串接方式，以及目前後端 API 介面與前端呼叫方式，方便本機開發與部署維運。

專案重點目錄：

- `Backend/`：FastAPI 後端服務與資料庫連線
- `client/`：React + Vite 前端（主要使用）
- `Backend/dist/`：已建置的前端靜態檔案（可選：由 FastAPI 提供）
- `my-bus-system/`：另一個 Vue 原型（次要；本文聚焦在 `client/`）

## 功能總覽

- 路線清單與路線站點查詢（資料由 MySQL 提供）
- 花蓮地點清單（示範資料表 `action_tour_hualien`）
- 會員登入：LINE Login（PKCE），登入後下發應用端 Cookie `app_session`
- 使用者基本資料查詢 `/me`
- 預約建立與我的預約查詢
- 前端在 API 不可用時可回落到本機靜態資料（`src/data/stations.js`）

## 架構與網路串接

後端以 FastAPI 提供 REST API；前端以 React + Vite 為 SPA。開發模式下，Vite 以 Proxy 方式將 `/api/*` 與 `/auth/*` 轉送到後端，避免 CORS 問題。

- 後端服務：`Backend/Server.py`（FastAPI）
  - 預設對外位址（開發預設值）：`http://192.168.0.126:8500`
  - 連線資料庫：MySQL（於 `Backend/MySQL.py` 設定），Redis（Session / Token 快取）
- 前端服務：`client/`（React + Vite）
  - 開發 Proxy（`client/vite.config.js`）：
    - `/api` -> `VITE_API_BASE_URL` 或 `http://192.168.0.126:8500`（預設）
    - `/auth` -> `https://<your-ngrok>.ngrok-free.app`（LINE Login 回呼網域）
  - 前端呼叫 API 的基底：
    - 一般 API：`VITE_API_BASE_URL`，若為開發模式未設定則預設使用 `/api`（交由 Vite 代理）
    - 身分相關 API：`VITE_AUTH_BASE_URL`（建議設為 `/auth` 以走 Vite 代理，或直接填 ngrok 完整網址）

生產部署常見做法：

- 由後端 Nginx/反向代理託管前端與 API，同網域供應（建議 Path 前綴分流或以子網域區分）。
- 若由 FastAPI 直接提供前端（`Backend/dist`），可在 `Server.py` 掛載 `StaticFiles`（程式現有註解可參考）。
- LINE Login 的 Callback 網域需為外部可達（示範使用 ngrok）。Cookie `app_session` 在 HTTPS 下會以 `SameSite=None; Secure` 設置。

## 環境需求

後端（FastAPI）：

- Python 3.11+（建議）
- 套件：`fastapi`, `uvicorn[standard]`, `httpx`, `redis`, `pandas`, `python-dotenv`, `pymysql`
- 服務：MySQL、Redis

前端（React + Vite）：

- Node.js 18+（或相容版本）

資料庫（以 `Backend/MySQL.py` 為準）：

- MySQL 伺服器：`host=192.168.0.126`, `port=3307`, `database=bus_system`（開發示範值）
- 注意：目前憑證硬編於程式（開發用），建議改為環境變數設定

Redis：

- `REDIS_URL`（預設 `redis://localhost:6379/0`）

LINE Login 與 Session 相關環境變數（於 `.env`）：

- `LINE_CHANNEL_ID`
- `LINE_CHANNEL_SECRET`
- `APP_SESSION_SECRET`（簽章用）
- `REDIS_URL`（可選）
- `BASE_URL`（建議新增；目前程式用常數，請同步調整）

前端環境變數（`client/.env`，開發建議）：

- `VITE_API_BASE_URL=http://192.168.0.126:8500`（或後端實際位址）
- `VITE_AUTH_BASE_URL=/auth`（建議用 Vite 代理；或設為 `https://<your-ngrok>.ngrok-free.app`）

## 啟動方式（開發）

後端（於 `Backend/`）：

1. 安裝套件：`pip install -r requirements.txt`（若無檔請依上方清單安裝）
2. 啟動 API：`uvicorn Server:app --host 0.0.0.0 --port 8500 --reload`

前端（於 `client/`）：

1. 安裝依賴：`npm install`
2. 開發啟動：`npm run dev`
3. 瀏覽器開啟：`http://localhost:5173`

Vite 代理行為：

- `GET /api/All_Route` 會被代理至 `http://192.168.0.126:8500/All_Route`
- `GET /auth/me` 會被代理至 `https://<your-ngrok>.ngrok-free.app/me`（或以 `VITE_AUTH_BASE_URL` 明確指定）

## 後端 API 一覽（FastAPI）

通用：

- CORS 允許來源（正則）：本機、Lan、校內段與 `*.ngrok-free.app`。
- Cookie 名稱：`app_session`（登入後發放）。

健康檢查：

- `GET /healthz` → `{ "status": "error 404" }`（供 LB 健檢）

路線與站點：

- `GET /All_Route`：回傳所有路線（資料表：`bus_routes_total`）。
  - 典型欄位：`route_id`, `route_name`, `direction`, `start_stop`, `end_stop`, `stop_count`, `status`, `created_at` 等（以 DB 實際欄位為準）。
- `POST /Route_Stations`：依路線查詢站點清單（資料表：`bus_route_stations`）。
  - Request Body（JSON）：`{ "route_id": number, "direction": string | null }`
  - Response（陣列，每筆對應 `Define.StationOut`）：
    - `route_id`, `route_name`, `direction`, `stop_name`, `latitude`, `longitude`, `eta_from_start`, `stop_order`, `created_at`
  - 備註：若 `direction` 不提供則不篩選方向；回傳依 `stop_order` 排序。

花蓮地點（示範）：

- `GET /yo_hualien`：回傳 `station_name`, `address`, `latitude`, `longitude`。

預約：

- `POST /reservation`：建立預約（目前以 QueryString 讀取參數）。
  - 參數（Query）：`user_id`, `booking_time`(ISO 字串), `booking_number`, `booking_start_station_name`, `booking_end_station_name`
  - 寫入資料表：`reservation`
- `GET /reservations/my?user_id=...`：查詢我的預約清單。
  - 回傳欄位：`user_id`, `booking_time`, `booking_number`, `booking_start_station_name`, `booking_end_station_name`, `review_status`, `payment_status`
  - 備註：前端 `getMyReservations(userId)` 直接對此端點發送請求。

LINE Login 與 Session：

- `GET /auth/line/login?return_to=<URL>`：導轉至 LINE 授權頁（使用 PKCE）
- `GET /auth/line/callback`：LINE 回呼（交換 Token、取回 Profile、簽發 `app_session` Cookie、寫入/更新 `users` 資料表）
- `GET /logout`：刪除 Cookie 並導回前端（`/profile` 頁）
- `GET /me`：以 Cookie 取得登入使用者資料
  - 回傳：`user_id, line_id, username, email, phone, last_login`
  - Cookie：`app_session`（HTTP-only；在 HTTPS 環境為 `SameSite=None; Secure`）

## 前端呼叫方式與整合點

集中封裝於 `client/src/services/api.js`：

- `getRoutes()` → `GET /All_Route`
- `getRouteStops(routeId, direction)` → `POST /Route_Stations`（JSON Body）
- `getStations()` → `GET /yo_hualien`
- 預約：
  - `getMyReservations(userId)` → `GET /reservations/my?user_id=...`
  - `createReservation(payload)` → `POST /reservations?...`（目前前端以 QueryString 傳參；對應後端 `POST /reservation` 的行為習慣）
  - `cancelReservation`, `updateReservation`, `getReservation`：前端已預留，但後端尚未對應實作（見下方 TODO）

身分整合（`client/src/pages/Profile.jsx`）：

- 以 `VITE_AUTH_BASE_URL` 呼叫 `/me` 檢查登入狀態（`credentials: 'include'`）
- 登出：導轉至 `<AUTH_BASE>/logout`
- 提示：在開發環境可將 `VITE_AUTH_BASE_URL` 設為 `/auth`，透過 Vite 代理走 ngrok 目標

API 失敗回退（`Routes.jsx`）：

- 若 `getRoutes()` 失敗則會以 `src/data/stations.js` 整理出路線清單顯示。

## 資料庫表與欄位（使用情境）

- `bus_routes_total`：路線總表（用於 `/All_Route`）
- `bus_route_stations`：路線各站（用於 `/Route_Stations`）
  - 欄位會在後端做欄名對齊與型別轉換，例如 `station_name/stop_name`, `order_no/seq -> stop_order` 等
- `action_tour_hualien`：花蓮地點清單（示範，`/yo_hualien`）
- `reservation`：預約資料（`/reservation`, `/reservations/my`）
- `users`：使用者與 LINE 資訊、`session_token`（`/auth/*`, `/me`）

實務建議：將資料庫連線設定改由環境變數管理，避免憑證硬編；寫入類 SQL 改用參數化避免 SQL Injection。

## TODO / 待補實作

- 後端未提供但前端已預留的預約 API：
  - `DELETE /reservations/{id}`（取消預約）
  - `PUT /reservations/{id}`（更新預約）
  - `GET /reservations/{id}`（單筆查詢）
- 將 `BASE_URL` 與 MySQL 憑證改為環境變數
- 視需要於 `Server.py` 掛載 `StaticFiles` 以提供 `Backend/dist` 前端靜態檔

## 參考檔案

- 後端主程式：`Github/H_Bus/Backend/Server.py`
- 資料模型：`Github/H_Bus/Backend/Define.py`
- MySQL 工具：`Github/H_Bus/Backend/MySQL.py`
- 前端 API 封裝：`Github/H_Bus/client/src/services/api.js`
- 前端 Vite 代理：`Github/H_Bus/client/vite.config.js`

Redis / Memurai 啟動方式

在 Windows 環境中，建議使用 Memurai 作為 Redis 的替代方案，請先確認服務已經啟動。

可以在 services.msc 中找到 Memurai 服務，若尚未啟動可手動按 Start，或在 PowerShell 輸入：

net start memurai


Memurai 預設會安裝 memurai-cli.exe（路徑通常在 C:\Program Files\Memurai\bin），可執行：

memurai-cli.exe ping


若回應 PONG，即表示服務運作正常。

啟動整體系統的步驟

啟動 Memurai（確認已登入並啟動）。

進入 Backend/ 目錄，啟動後端服務：

uvicorn Server:app --host 0.0.0.0 --port 8500 --reload


進入 client/ 目錄，先執行：

npm install


然後啟動前端開發伺服器：

npm run dev


確認 .env.development、.env.production 或其他 .env.* 檔案內，已正確設定以下環境變數：

VITE_API_BASE_URL

VITE_AUTH_BASE_URL

最後開啟瀏覽器，進入 http://localhost:5173，即可存取前端開發環境。