# -*- coding: utf-8 -*-
"""
每天 08:00 自動：
1) 查詢 reservation：今天、review_status='approved'
2) 連 users 表拿 email
3) 依使用者彙整並寄出確認信

依賴：
- 你的 MySQL_Run 函式 (from MySQL import MySQL_Run)
- Gmail 應用程式密碼 (建議放在 .env)
"""

import os
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv

# === 載入環境變數（建議使用 .env 管理） ===
# .env 範例：
# EMAIL_ADDRESS=your@gmail.com
# EMAIL_PASSWORD=your_16_chars_app_password
load_dotenv()

SENDER_EMAIL = os.getenv("EMAIL_ADDRESS", "tailin1125@gmail.com")
SENDER_PASS  = os.getenv("EMAIL_PASSWORD", "ceaa fcfl wubf mjss")  # 建議改為 .env
TZ = ZoneInfo("Asia/Taipei")

# === 你專案內的 MySQL 執行器 ===
from MySQL import MySQL_Run  # 確保路徑/模組名正確

# ========== 信件樣板 ==========
MAIL_SUBJECT = "【乘車提醒】您今日的預約資訊"
MAIL_TEXT_TEMPLATE = """親愛的乘客您好，

以下為您今日 ({today}) 的預約資訊：
{lines}

若資訊有誤或需更改，請盡速與我們聯繫。祝您旅途順利！

— 花蓮小巴預約系統
"""

# ========== 郵件發送 ==========
def send_email(receiver_email: str, subject: str, text: str):
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = SENDER_EMAIL
    message["To"] = receiver_email

    part1 = MIMEText(text, "plain", "utf-8")
    message.attach(part1)

    smtp_server = "smtp.gmail.com"
    port = 465  # SSL

    with smtplib.SMTP_SSL(smtp_server, port) as server:
        server.login(SENDER_EMAIL, SENDER_PASS)
        server.sendmail(SENDER_EMAIL, receiver_email, message.as_string())

# ========== 查詢今天預約 & 準備寄信名單 ==========
def fetch_today_reservations() -> pd.DataFrame:
    """
    回傳欄位：
      email, user_id, reservation_id, booking_time, booking_number,
      booking_start_station_name, booking_end_station_name, review_status, payment_status
    僅限今天 + approved
    """
    sql = """
    SELECT 
        u.email,
        r.user_id,
        r.reservation_id,
        r.booking_time,
        r.booking_number,
        r.booking_start_station_name,
        r.booking_end_station_name,
        r.review_status,
        r.payment_status
    FROM reservation r
    JOIN users u ON u.user_id = r.user_id
    WHERE r.review_status = 'approved'
      AND DATE(r.booking_time) = CURDATE()
      AND u.email IS NOT NULL
      AND u.email <> '';
    """
    rows = MySQL_Run(sql)
    df = pd.DataFrame(rows)
    # 安全處理：若表空或欄位大小寫/命名不同，可在此做 rename
    return df

# ========== 組信內容（依 email 彙整多筆預約） ==========
def build_and_send_emails():
    now = datetime.now(TZ)
    print(f"[{now:%Y-%m-%d %H:%M:%S}] 開始檢查今日預約…")

    try:
        df = fetch_today_reservations()
    except Exception as e:
        print(f"[{datetime.now(TZ):%Y-%m-%d %H:%M:%S}] 查詢 DB 失敗：{e}")
        return

    if df.empty:
        print(f"[{datetime.now(TZ):%Y-%m-%d %H:%M:%S}] 今日無符合條件的預約。")
        return

    # 確保必要欄位存在
    required_cols = {
        "email", "reservation_id", "booking_time", "booking_number",
        "booking_start_station_name", "booking_end_station_name"
    }
    missing = required_cols - set(df.columns)
    if missing:
        print(f"[{datetime.now(TZ):%Y-%m-%d %H:%M:%S}] 结果少欄位: {missing}")
        return

    # 依 email 分組
    grouped = df.groupby("email", dropna=True)

    success, fail = 0, 0
    for email, g in grouped:
        # 針對同一位使用者可能有多筆預約
        lines = []
        for _, r in g.iterrows():
            # booking_time 轉可讀
            bt = str(r["booking_time"])
            # 若是 ISO 格式字串，可截掉秒後面的部分
            # 你也可以用 pandas 轉型後再格式化：
            # bt = pd.to_datetime(r["booking_time"]).strftime("%Y-%m-%d %H:%M")
            line = (
                f"- 預約編號: {r['reservation_id']}｜"
                f"時間: {bt}｜"
                f"人數: {r['booking_number']}｜"
                f"{r['booking_start_station_name']} → {r['booking_end_station_name']}"
            )
            lines.append(line)

        body = MAIL_TEXT_TEMPLATE.format(
            today=f"{now:%Y-%m-%d}",
            lines="\n".join(lines)
        )

        try:
            send_email(email, MAIL_SUBJECT, body)
            print(f"✔ 已寄出：{email}（{len(g)} 筆）")
            success += 1
        except Exception as e:
            print(f"✘ 寄送失敗：{email} → {e}")
            fail += 1

    print(f"[{datetime.now(TZ):%Y-%m-%d %H:%M:%S}] 寄送完成：成功 {success} 位、失敗 {fail} 位。")

# ========== 主程式：每天 08:00 自動執行 ==========
def main():
    scheduler = BlockingScheduler(timezone=TZ)
    # 每天 08:00 觸發
    scheduler.add_job(build_and_send_emails, CronTrigger(hour=16, minute=50), id="daily_0800_send")

    print("排程已啟動（Asia/Taipei）。每天 08:00 寄送今日乘車提醒。")
    print("按 Ctrl+C 可停止。")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("排程停止。")

if __name__ == "__main__":
    main()
    # import threading

    # def wait_for_exit(scheduler):
    #     input("按 Enter 結束排程...\n")
    #     scheduler.shutdown()

    # scheduler = BlockingScheduler(timezone=TZ)
    # scheduler.add_job(build_and_send_emails, CronTrigger(hour=8, minute=0))
    # threading.Thread(target=wait_for_exit, args=(scheduler,), daemon=True).start()
    # scheduler.start()