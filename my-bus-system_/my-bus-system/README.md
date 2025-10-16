# 前端：Vue 3 + TypeScript + Vite

這個模板可幫助你以 Vue 3 與 TypeScript 在 Vite 環境快速啟動。此模板使用 Vue 3 `<script setup>` SFCs，參考官方 [script setup 文件](https://v3.vuejs.org/api/sfc-script-setup.html#sfc-script-setup) 了解更多。

更多專案設定與 IDE 支援建議，請見 [Vue Docs TypeScript Guide](https://vuejs.org/guide/typescript/overview.html#project-setup)。

---

# 後端：花蓮市民小巴系統（FastAPI）

以下為常用後端操作導覽：新增路線/站點、OTP 測試方式、管理員角色限制等。所有 API 路徑皆與現行系統一致、穩定。

## 後端啟動

- 檔案位置：`H_Bus/my-bus-system/app.py`
- 開發啟動（自動重載）：

  ```bash
  uvicorn app:app --reload --host 0.0.0.0 --port 8500
  ```

- CORS：允許 localhost 與常見內網網段（5173/3000/8080）供前端開發使用。
- 資料庫：MySQL 連線字串目前在 `app.py` 內部設定（內網/測試用途），未來可環境變數化而不影響現有行為。

## 認證概覽

- 管理員登入：`POST /auth/login`
  - Body：`{ "username": "...", "password": "..." }`
  - 回傳：`{ access_token: "admin_<id>_token", token_type: "bearer", ... }`
  - 之後以 Bearer Token 呼叫需要權限的管理端 API。

- 會員登入：`POST /users/login`
  - Body：`{ "username": "...", "password": "..." }`
  - 回傳成功與會員基本資料；會員 API 與管理端分離。

## 管理員角色與限制

角色存於 `admin_roles`，指派到 `admin_users`。

- `super_admin`：
  - 可建立非重複的任何管理員帳號。
  - 系統僅允許一組 `super_admin`。
  - 不能修改自己的角色或停用自己；不能修改/刪除其他 `super_admin`。

- `admin`：
  - 僅能建立與管理 `dispatcher` 帳號。
  - 不能修改角色；不能管理 `super_admin` 或其他 `admin`。

- `dispatcher`：
  - 執行角色，無管理員管理權限。

常用管理端 API（需 Bearer Token）：

- 列表管理員：`GET /api/admin/users`
- 新增管理員：`POST /api/admin/users`
- 更新管理員：`PUT /api/admin/users/{admin_id}`
- 刪除管理員：`DELETE /api/admin/users/{admin_id}`
- 角色列表：`GET /api/admin/roles` 與 `GET /roles`
- 角色管理：`POST/PUT/DELETE /roles`

## OTP 測試與除錯

OTP 預設使用 Redis；若無法連線，會自動改用記憶體版（開發用途，無持久化）。

- 環境變數（選用）：
  - `HBUS_REDIS_URL` 或 `REDIS_URL`：Redis 連線 URL
  - `HBUS_OTP_TTL_SEC`（預設 300）：驗證碼有效秒數
  - `HBUS_OTP_LEN`（預設 6）：驗證碼位數
  - `HBUS_OTP_MAX_ATTEMPTS`（預設 5）：最大嘗試次數
  - `HBUS_OTP_RESEND_COOLDOWN`（預設 60）：再次發送冷卻秒數
  - `HBUS_OTP_DEBUG=1`：回傳驗證碼至 API（僅測試）
  - `HBUS_OTP_LOG=1`：將驗證碼寫入 `otp_codes.txt`（除錯）

- 申請驗證碼：
  ```bash
  curl -X POST http://localhost:8500/auth/otp/request \
    -H 'Content-Type: application/json' \
    -d '{"account":"test@example.com","purpose":"login"}'
  ```

- 驗證驗證碼：
  ```bash
  curl -X POST http://localhost:8500/auth/otp/verify \
    -H 'Content-Type: application/json' \
    -d '{"account":"test@example.com","purpose":"login","code":"123456"}'
  ```

- 兌換 ticket：
  ```bash
  curl -X POST http://localhost:8500/auth/otp/consume -d 'ticket=<ticket>'
  ```

## 路線：新增 / 更新 / 刪除 / 列表

以下端點需管理員 Bearer Token：

- 新增路線：`POST /api/routes/create`
  - Body 範例：
    ```json
    {
      "route_name": "市民小巴-行動遊花蓮",
      "direction": "單向",
      "start_stop": "起點站",
      "end_stop": "終點站",
      "stop_count": 10,
      "status": 1
    }
    ```

- 更新路線：`PUT /api/routes/update`
  - 提供 `route_id` 與要更新的欄位。

- 刪除路線：`DELETE /api/routes/delete`
  - Body：`{ "route_id": <id> }`
  - 會一併刪除對應之 `bus_route_stations` 資料。

- 路線列表（摘要）：
  - `GET /All_Route`（來自 `bus_routes_total`）
  - `GET /api/routes`（由站點彙整，`route_id, route_name` 去重）

## 路線站點：新增 / 更新 / 刪除 / 查詢

以下端點需管理員 Bearer Token（公開查詢端點除外）。

- 新增站點：`POST /api/route-stations/create`
  - Body 範例：
    ```json
    {
      "route_id": 4,
      "route_name": "市民小巴-行動遊花蓮",
      "direction": "去程",
      "stop_name": "某某站",
      "latitude": 23.99,
      "longitude": 121.60,
      "stop_order": 1,
      "eta_from_start": 0,
      "address": "花蓮市..."
    }
    ```

- 更新站點：`PUT /api/route-stations/update`
  - 支援 `original_stop_name` / `original_stop_order` 以利安全定位更新。

- 刪除站點：`DELETE /api/route-stations/delete?route_id=<id>&stop_order=<n>`

- 查詢某路線站點：`POST /Route_Stations`
  - Body：`{ "route_id": 4, "direction": "去程" }`

- 站點篩選＋分頁：`GET /api/route-stations`
  - 參數：`route_id`, `direction`, `search`, `page`, `page_size`

## 預約：列表 / 新增 / 更新 / 刪除

以下端點需管理員 Bearer Token：

- 列表：`GET /api/reservations`（支援 `search`, `payment_status`, `review_status`, `dispatch_status`）
- 新增：`POST /api/reservations`
- 更新：`PUT /api/reservations/{reservation_id}`
- 刪除：`DELETE /api/reservations/{reservation_id}`

## 範例：管理員 Token 流程

1) 登入
```bash
curl -X POST http://localhost:8500/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"pass"}'
```

2) 帶 Token 呼叫受保護 API
```bash
curl -H 'Authorization: Bearer admin_1_token' http://localhost:8500/api/admin/users
```

## 備註

- DB 輔助：`H_Bus/my-bus-system/MySQL.py` 內的 `MySQL_Run`。
- OTP 退回：若 Redis 不可用，系統會改用記憶體模式（開發用，無持久化）。
- 安全性：管理端 Bearer Token 僅為簡化格式（`admin_{id}_token`），無簽章/過期，僅做為本系統使用。
