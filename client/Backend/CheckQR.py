from Backend.MySQL import MySQL_Doing
from dotenv import load_dotenv
import base64, hmac, hashlib, json, os, time
import pandas as pd

MySQL_Doing = MySQL_Doing()
load_dotenv()


def _b64url_decode(data: str) -> bytes:
    pad = '=' * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + pad)


def _sign(raw: bytes, secret: str) -> str:
    sig = hmac.new(secret.encode(), raw, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(sig).decode().rstrip('=')


def verify_boarding_token(token: str) -> dict:
    """驗證乘車編碼：簽章、時效、資料庫資格。"""
    if not token or '.' not in token:
        return {"ok": False, "reason": "格式錯誤"}

    # 解析 token
    try:
        b64p, sig = token.split('.', 1)
        raw = _b64url_decode(b64p)
        data = json.loads(raw.decode('utf-8'))
    except Exception:
        return {"ok": False, "reason": "解碼失敗"}

    # 驗簽
    secret = os.getenv("APP_SESSION_SECRET") or os.getenv("APP_SECRET") or "dev-secret"
    if _sign(raw, secret) != sig:
        return {"ok": False, "reason": "簽章不符"}

    # 檢查有效期
    if int(data.get('exp', 0)) < int(time.time()):
        return {"ok": False, "reason": "已過期"}

    # 取必要欄位
    rid = int(data.get('rid') or 0)
    uid = int(data.get('uid') or 0)
    if not rid or not uid:
        return {"ok": False, "reason": "內容缺失"}

    # 以 DB 再驗狀態仍合格
    sql = f"""
        SELECT r.reservation_id, r.user_id, r.payment_status, r.review_status
        FROM reservation r
        WHERE r.reservation_id = {rid}
    """
    res = MySQL_Doing.run(sql)

    # 支援 DataFrame 或 list 結果
    if isinstance(res, pd.DataFrame):
        if res.empty:
            return {"ok": False, "reason": "查無訂位"}
        df = res
    else:
        df = pd.DataFrame(res or [])
        if df.empty:
            return {"ok": False, "reason": "查無訂位"}

    row = df.iloc[0]
    try:
        db_uid = int(row.get('user_id')) if isinstance(row, dict) else int(row['user_id'])
        pay_ok = (row.get('payment_status') if isinstance(row, dict) else row['payment_status']) == 'paid'
        rev_ok = (row.get('review_status') if isinstance(row, dict) else row['review_status']) == 'approved'
    except Exception:
        # 萬一欄位名異常
        return {"ok": False, "reason": "欄位異常"}

    if db_uid != uid:
        return {"ok": False, "reason": "使用者不符"}
    if not (pay_ok and rev_ok):
        return {"ok": False, "reason": "資格未通過"}

    return {"ok": True, "reservation_id": rid, "user_id": uid}


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("用法: python Debug4.py <token>")
        raise SystemExit(1)
    token = sys.argv[1]
    result = verify_boarding_token(token)
    print(result)

