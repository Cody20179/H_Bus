# ====================================
# 📦 第三方套件
# ====================================
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from dotenv import load_dotenv
from pydantic import BaseModel, Field
import base64
import hashlib
import json
import os
from decimal import Decimal
from urllib.parse import quote

# ====================================
# ✅ 初始化
# ====================================
load_dotenv()
app = FastAPI()

# ====================================
# 📦 Model 定義
# ====================================
class CreatePaymentIn(BaseModel):
    amount: str = Field(..., description="金額（以元為單位，純數字字串，例如 '10' 或 '199'）")
    order_number: str = Field(..., min_length=1, max_length=64, description="商家訂單編號")

class CreatePaymentOut(BaseModel):
    pay_url: str

# ====================================
# ⚙️ 參數設定
# ====================================
MERCHANT_ID   = os.getenv("MERCHANT_ID", "")
TERMINAL_ID   = os.getenv("TERMINAL_ID", "")
STORE_CODE    = os.getenv("STORE_CODE", "")
KEY_HEX       = os.getenv("KEY", "")
IV_HEX        = os.getenv("IV", "")
LAYMON        = os.getenv("LAYMON", "iqrc.epay365.com.tw")  # 雷門 host，不要加 https://
PUBLIC_BASE   = "https://hualenbus.labelnine.app:7001"""

# ====================================
# 🔐 AES 加解密
# ====================================
def encrypt_aes(data: dict) -> str:
    """依雷門規範 AES-256-CBC + PKCS7 padding + Base64"""
    key = bytes.fromhex(KEY_HEX)
    iv = bytes.fromhex(IV_HEX)
    json_str = json.dumps(data, separators=(",", ":"))
    cipher = AES.new(key, AES.MODE_CBC, iv)
    encrypted_bytes = cipher.encrypt(pad(json_str.encode("utf-8"), 16))
    return base64.b64encode(encrypted_bytes).decode("utf-8")

def decrypt_aes(transaction_data: str) -> dict:
    """AES-256-CBC 解密"""
    key = bytes.fromhex(KEY_HEX)
    iv = bytes.fromhex(IV_HEX)
    encrypted_bytes = base64.b64decode(transaction_data)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    decrypted = unpad(cipher.decrypt(encrypted_bytes), 16).decode("utf-8")
    return json.loads(decrypted)

# ====================================
# 🧾 建立付款連結
# ====================================
@app.post("/payments", response_model=CreatePaymentOut)
def create_payment(body: CreatePaymentIn):
    amt = Decimal(body.amount)
    if amt <= 0 or amt != amt.quantize(Decimal("1")):
        raise HTTPException(status_code=400, detail="amount 必須為正整數")

    payload = {
        "merchant_id": MERCHANT_ID,
        "terminal_id": TERMINAL_ID,
        "store_code": STORE_CODE,  # 有些通道也會檢查這個
        "set_price": str(amt),
        "pos_id": "01",
        "pos_order_number": body.order_number,
        "callback_url": f"{PUBLIC_BASE}/callback",
        "return_url": f"{PUBLIC_BASE}/return",
    }

    # === AES 加密 ===
    transaction_data = encrypt_aes(payload)

    # === SHA256 雜湊（注意：針對未 URL encode 的原始 Base64 字串）===
    hash_digest = hashlib.sha256(transaction_data.encode("utf-8")).hexdigest()

    print("原始 JSON:", payload)
    print("加密後 TransactionData:", transaction_data)
    print("本地算出的 HashDigest:", hash_digest)

    # === URL encode 後組成最終網址 ===
    full_url = (
        f"https://{LAYMON}/calc/pay_encrypt/{STORE_CODE}"
        f"?TransactionData={quote(transaction_data)}&HashDigest={hash_digest}"
    )

    return CreatePaymentOut(pay_url=full_url)

# ====================================
# 🔁 雷門 callback（伺服器對伺服器）
# ====================================
@app.get("/callback")
def callback_check():
    return JSONResponse({"status": "ok", "msg": "callback alive"})

@app.post("/callback")
async def callback(request: Request):
    try:
        body = await request.json()
    except:
        return {"status": "ok"}  # 避免他打空資料報錯

    enc_data = body.get("TransactionData")
    hash_digest = body.get("HashDigest")

    if not enc_data or not hash_digest:
        # 他第一次打來時 often 沒帶這兩個欄位
        return {"status": "ok"}  # 改這裡！不要 raise 錯

    local_hash = hashlib.sha256(enc_data.encode("utf-8")).hexdigest()
    if local_hash != hash_digest:
        # 他可能是測試包，不要報 400
        return {"status": "ok"}  

    try:
        data = decrypt_aes(enc_data)
        order_number = data.get("pos_order_number")
        return {"status": "ok", "data": data}
    except Exception as e:
        return {"status": "ok"}  # 同樣保持 ok，不讓他認為失敗

# ====================================
# 🌐 使用者導回頁
# ====================================
@app.get("/return")
def return_page():
    return RedirectResponse(url=f"{PUBLIC_BASE}?tab=reservations")

# ====================================
# 🚀 執行命令範例
# ====================================
"""
uvicorn Money:app --host 0.0.0.0 --port 7001 --reload --ssl-keyfile "D:/ssl/hualenbus.labelnine.app-key.pem" --ssl-certfile "D:/ssl/hualenbus.labelnine.app-chain.pem"
"""
