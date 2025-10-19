from Backend.MySQL import MySQL_Doing
from dotenv import load_dotenv
import pandas as pd
import base64, hmac, hashlib, json, os, time
import qrcode

MySQL_Doing = MySQL_Doing()
load_dotenv()

def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")

def _b64url_decode(data: str) -> bytes:
    pad = '=' * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad)

def _sign(raw: bytes, secret: str) -> str:
    sig = hmac.new(secret.encode(), raw, hashlib.sha256).digest()
    return _b64url(sig)

def get_passenger_info(reservation_id: int):
    """
    依 reservation_id 查詢乘客與訂位資訊，回傳是否符合乘車資格
    條件：payment_status='paid' 且 review_status='approved'
    """
    sql = f"""
        SELECT r.reservation_id, r.user_id, r.payment_status, r.review_status,
               r.dispatch_status, r.booking_start_station_name, r.booking_end_station_name,
               u.username, u.email, u.phone, u.status
        FROM reservation r
        JOIN users u ON r.user_id = u.user_id
        WHERE r.reservation_id = {int(reservation_id)};
    """
    results = MySQL_Doing.run(sql)
    if results is None or len(results) == 0:
        return {"valid": False, "message": "找不到該筆訂位"}

    df = pd.DataFrame(results)
    row = df.loc[0]
    qualified = (row.get("payment_status") == "paid") and (row.get("review_status") == "approved")

    return {
        "reservation_id": int(row.get("reservation_id")),
        "user_id": int(row.get("user_id")),
        "username": row.get("username"),
        "email": row.get("email"),
        "phone": row.get("phone"),
        "status": row.get("status"),
        "payment_status": row.get("payment_status"),
        "review_status": row.get("review_status"),
        "dispatch_status": row.get("dispatch_status"),
        "start_station": row.get("booking_start_station_name"),
        "end_station": row.get("booking_end_station_name"),
        "qualified": qualified,
        "message": "乘車資格通過" if qualified else "未符合乘車資格",
    }

def generate_boarding_token(reservation_id: int, ttl_seconds: int = 3600) -> str:
    """產生乘車編碼（帶簽章），有效期預設 1 小時"""
    info = get_passenger_info(reservation_id)
    if not info.get("qualified"):
        raise ValueError(info.get("message") or "未符合乘車資格")

    secret = os.getenv("APP_SESSION_SECRET") or os.getenv("APP_SECRET") or "dev-secret"
    payload = {
        "rid": int(info["reservation_id"]),
        "uid": int(info["user_id"]),
        "q": True,
        "exp": int(time.time()) + int(ttl_seconds),
        "s": info.get("start_station") or "",
        "e": info.get("end_station") or "",
    }
    raw = json.dumps(payload, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    token = f"{_b64url(raw)}.{_sign(raw, secret)}"
    return token

def save_qr_png(token: str, path: str) -> None:
    img = qrcode.make(token)
    img.save(path)

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法: python Debug3.py <reservation_id> [ttl秒]。會列印token並輸出 QR PNG")
        sys.exit(1)
    rid = int(sys.argv[1])
    ttl = int(sys.argv[2]) if len(sys.argv) >= 3 else 3600
    token = generate_boarding_token(rid, ttl_seconds=ttl)
    print(token)
    out = f"boarding_{rid}.png"
    save_qr_png(token, out)
    print(f"已輸出 QR 圖片: {out}")

