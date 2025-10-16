
# 📘 Reservation Snapshot Schema & Triggers 說明

## 🧩 概述

此設計為 **預約系統（reservation system）** 的一部分，
透過 **MariaDB/MySQL 觸發器（Triggers）** 自動產生「預約快照（reservation snapshot）」記錄。

當預約進入最終狀態（完成、被拒、取消、付款失敗等）時，
系統會自動將當前資料寫入 `reservation_record` 表中，以便：

* 保留歷史紀錄
* 稽核追蹤
* 防止關鍵資料遺失

---

## ⚙️ 系統架構

| 元件                   | 說明                       |
| -------------------- | ------------------------ |
| `reservation`        | 主表，用於儲存目前的預約資料（會隨狀態更新）。  |
| `users`              | 使用者資料來源，觸發器會從中取出使用者聯絡資訊。 |
| `reservation_record` | 快照表，用於儲存預約最終狀態的歷史紀錄。     |

---

## 🔍 運作邏輯

### 🎯 觸發條件

當任一條件成立時觸發快照寫入：

```sql
NEW.reservation_status = 1
OR NEW.review_status IN ('rejected', 'canceled')
OR NEW.payment_status IN ('failed', 'refunded')
```

即代表：

* ✅ 預約完成 (`reservation_status = 1`)
* ❌ 被拒絕或取消
* 💸 付款失敗或退款

---

## 🧠 觸發器說明

### 🟢 `AFTER INSERT` — `trg_reservation_snapshot_ai`

> 當新增一筆預約時執行。

若該筆預約在新增時就已進入最終狀態（例如取消或付款失敗），
則立即將其快照寫入 `reservation_record`。

---

### 🟡 `AFTER UPDATE` — `trg_reservation_snapshot_au`

> 當修改預約狀態時執行。

若更新後的預約變為最終狀態，
則會將該筆預約的最新資料寫入（或覆蓋）快照表。

---

## 📦 快照寫入內容

每當觸發器被啟動，會將下列欄位存入 `reservation_record`：

| 類別     | 欄位                                                                         |
| ------ | -------------------------------------------------------------------------- |
| 預約基本資料 | `reservation_id`, `user_id`, `booking_time`, `booking_number`              |
| 起訖站點   | `booking_start_station_name`, `booking_end_station_name`                   |
| 使用者資料  | `line_id`, `username`, `email`, `phone`                                    |
| 狀態欄位   | `payment_status`, `review_status`, `dispatch_status`, `reservation_status` |
| 其他     | `payment_method`, `payment_record`, `cancel_reason`, `snapshot_date`       |

> `snapshot_date` 使用 `CURDATE()` 自動填入快照日期。

---

## 🔁 `ON DUPLICATE KEY UPDATE`

```sql
ON DUPLICATE KEY UPDATE ...
```

這句確保：

* 若同一筆 `reservation_id` 已存在於 `reservation_record`，
  就不新增，而是更新成最新狀態。
* 保證每筆預約在快照表中僅有一條最終紀錄。

> ⚠️ 因此 `reservation_record.reservation_id` 應設為 **PRIMARY KEY** 或 **UNIQUE KEY**。


## ⚠️ 注意事項

1. **確保唯一鍵：**
   `reservation_record.reservation_id` 必須為 `PRIMARY KEY` 或 `UNIQUE`，否則 `ON DUPLICATE KEY UPDATE` 無效。
2. **使用者資料安全：**
   若 `user_id` 為 NULL，觸發器會將 `line_id`、`username`、`email`、`phone` 設為 `NULL`。
3. **效能考量：**
   若系統預約更新頻繁，請評估觸發器對性能的影響。
4. **時間欄位建議：**
   可於 `reservation_record` 加上 `snapshot_timestamp`（`DEFAULT CURRENT_TIMESTAMP`）以追蹤具體寫入時間。

---

## 🧭 運作流程圖（簡化）

```text
┌────────────────────┐
│   INSERT / UPDATE  │
│   on reservation   │
└──────────┬─────────┘
           │
           ▼
   Check final state?
   ├── reservation_status = 1
   ├── review_status ∈ (rejected, canceled)
   └── payment_status ∈ (failed, refunded)
           │
           ▼
┌────────────────────────────┐
│ Fetch user info from users │
└──────────┬─────────────────┘
           ▼
┌────────────────────────────┐
│ Write / Update snapshot in │
│     reservation_record      │
└────────────────────────────┘
```

---

## 🧾 總結

這組觸發器的目的，是讓預約系統具備「**事件完成後自動留痕**」的能力。
無論是付款失敗、被拒、完成或取消，都會即時保存當時的預約與使用者資訊，
確保系統能夠：

* 還原歷史狀態
* 進行稽核與分析
* 提升資料完整性