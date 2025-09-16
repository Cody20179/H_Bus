from fastapi import FastAPI
from pydantic import BaseModel
import json, hashlib, base64
from Crypto.Cipher import AES
import requests

app = FastAPI()

# === 測試用參數 (請換成 Excel 裡的資料) ===
MERCHANT_ID = "e4f76eb8-d236-45fb-984b-92b2d1912492"
KEY_HEX = "3abae022acd6fc873821411c0b402c0fbe90d90bdda295ed15296f8ae465bf8b"
IV_HEX = "12fe9f5e0c3cc7c664894f19ba265050"

key = bytes.fromhex(KEY_HEX)
iv = bytes.fromhex(IV_HEX)

# === AES 加解密工具 ===
def aes_encrypt(plaintext: str) -> str:
    cipher = AES.new(key, AES.MODE_CBC, iv=iv)
    pad_len = AES.block_size - (len(plaintext.encode()) % AES.block_size)
    padded = plaintext + chr(pad_len) * pad_len
    encrypted = cipher.encrypt(padded.encode())
    return base64.b64encode(encrypted).decode()

def aes_decrypt(enc_b64: str) -> str:
    enc = base64.b64decode(enc_b64)
    cipher = AES.new(key, AES.MODE_CBC, iv=iv)
    decrypted_padded = cipher.decrypt(enc)
    pad_len = decrypted_padded[-1]
    return decrypted_padded[:-pad_len].decode()

# === 建立付款 (API 4.1) ===
@app.post("/create_payment")
async def create_payment(amount: int = 100, order_id: str = "ORDER123456"):
    data = {
        "set_price": str(amount),
        "pos_order_number": order_id,
        "callback_url": "https://yourdomain.com/api/pay/callback",
        "return_url": "https://yourdomain.com/pay/result"
    }
    json_data = json.dumps(data, separators=(",", ":"))
    TransactionData = aes_encrypt(json_data)
    HashDigest = hashlib.sha256(TransactionData.encode()).hexdigest()

    payment_url = (
        f"https://iqrc.epay365.com.tw/calc/pay_encrypt/{MERCHANT_ID}"
        f"?TransactionData={TransactionData}&HashDigest={HashDigest}"
    )
    return {"payment_url": payment_url}

# === Callback 接收 (API 4.2) ===
class CallbackBody(BaseModel):
    TransactionData: str
    HashDigest: str

@app.post("/api/pay/callback")
async def callback(body: CallbackBody):
    calc_hash = hashlib.sha256(body.TransactionData.encode()).hexdigest()
    if calc_hash != body.HashDigest:
        return {"status": "error", "message": "Hash 校驗失敗"}

    decrypted = aes_decrypt(body.TransactionData)
    result = json.loads(decrypted)
    print("付款結果：", result)

    return {"status": "ok", "data": result}

# === 退款 (API 4.3) ===
@app.post("/refund")
async def refund(order_id: str, refund_type: str = "linepay", amount: str = None):
    data = {"order_id": order_id, "refund_type": refund_type}
    if amount:
        data["partial_refund_amount"] = amount

    json_data = json.dumps(data, separators=(",", ":"))
    TransactionData = aes_encrypt(json_data)
    HashDigest = hashlib.sha256(TransactionData.encode()).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "X-ePay-MerchantID": MERCHANT_ID,
        "X-ePay-TerminalID": "61000101"  # 測試端末代碼，需替換
    }

    payload = {"TransactionData": TransactionData, "HashDigest": HashDigest}
    url = f"https://iqrc.epay365.com.tw/api/refund/{MERCHANT_ID}"
    resp = requests.post(url, headers=headers, json=payload)
    return resp.json()

# === 查詢 (API 4.4) ===
@app.post("/query")
async def query(order_id: str = None, pos_order_number: str = None):
    data = {}
    if order_id:
        data["order_id"] = order_id
    if pos_order_number:
        data["pos_order_number"] = pos_order_number

    json_data = json.dumps(data, separators=(",", ":"))
    TransactionData = aes_encrypt(json_data)
    HashDigest = hashlib.sha256(TransactionData.encode()).hexdigest()

    headers = {
        "Content-Type": "application/json",
        "X-ePay-MerchantID": MERCHANT_ID,
        "X-ePay-TerminalID": "61000101"  # 測試端末代碼，需替換
    }

    payload = {"TransactionData": TransactionData, "HashDigest": HashDigest}
    url = f"https://iqrc.epay365.com.tw/api/query/{MERCHANT_ID}"
    resp = requests.post(url, headers=headers, json=payload)
    return resp.json()
