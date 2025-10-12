import os
import json
import hashlib
from base64 import b64encode, b64decode
from urllib.parse import quote

import requests
from fastapi import FastAPI, Request
from dotenv import load_dotenv
from Crypto.Cipher import AES

# 載入環境變數
load_dotenv()

MERCHANT_ID = os.getenv("MERCHANT_ID", "")
TERMINAL_ID = os.getenv("TERMINAL_ID", "")
STORE_CODE  = os.getenv("STORE_CODE", "")
KEY_HEX     = os.getenv("KEY", "")
IV_HEX      = os.getenv("IV", "")
LAYMON      = os.getenv("LAYMON", "iqrc.epay365.com.tw")  # 雷門 host，不要加 https://
NGROK_DOMAIN = os.getenv("NGROK_DOMAIN", "http://127.0.0.1:8000")

KEY = bytes.fromhex(KEY_HEX)
IV  = bytes.fromhex(IV_HEX)

app = FastAPI()

# --- AES256-CBC 加解密 ---
def pad(s):
    pad_len = 16 - (len(s) % 16)
    return s + chr(pad_len) * pad_len

def unpad(s):
    return s[:-ord(s[-1])]

def encrypt_aes(data: str, key: bytes, iv: bytes) -> str:
    cipher = AES.new(key, AES.MODE_CBC, iv)
    ct_bytes = cipher.encrypt(pad(data).encode("utf-8"))
    return b64encode(ct_bytes).decode("utf-8")

def decrypt_aes(enc: str, key: bytes, iv: bytes) -> str:
    cipher = AES.new(key, AES.MODE_CBC, iv)
    pt = cipher.decrypt(b64decode(enc))
    return unpad(pt.decode("utf-8"))

# 測試發送交易
@app.get("/test-pay")
def test_pay():
    payload = {
        "set_price": "100",
        "pos_order_number": "TEST12345",
        "callback_url": f"{NGROK_DOMAIN}/callback",
        "return_url": f"{NGROK_DOMAIN}/return"
    }

    json_str = json.dumps(payload, separators=(',', ':'))
    TransactionData = encrypt_aes(json_str, KEY, IV)
    HashDigest = hashlib.sha256(TransactionData.encode("utf-8")).hexdigest()

    url = f"https://{LAYMON}/calc/pay_encrypt/{STORE_CODE}"
    full_url = f"{url}?TransactionData={quote(TransactionData)}&HashDigest={HashDigest}"

    return {
        "pay_url": full_url
    }

    
# 雷門回傳 callback
@app.post("/callback")
async def callback(request: Request):
    body = await request.json()
    enc_data = body.get("TransactionData")
    hash_digest = body.get("HashDigest")

    # 驗證 hash
    if hashlib.sha256(enc_data.encode("utf-8")).hexdigest() != hash_digest:
        return {"status": "error", "msg": "hash 驗證失敗"}

    # 解密資料
    try:
        decrypted = decrypt_aes(enc_data, KEY, IV)
        data = json.loads(decrypted)
        # 這裡可以更新訂單狀態到你的資料庫
        return {"status": "ok", "data": data}
    except Exception as e:
        return {"status": "error", "msg": str(e)}

# 前端顯示用 (雷門會導回來)
@app.get("/return")
def return_page():
    return {"message": "付款流程結束，這裡顯示給使用者看"}
