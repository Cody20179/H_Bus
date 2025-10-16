uvicorn Money:app --host 0.0.0.0 --port 7001 --reload --ssl-keyfile "D:/ssl/hualenbus.labelnine.app-key.pem" --ssl-certfile "D:/ssl/hualenbus.labelnine.app-chain.pem"
uvicorn Server:app --host 0.0.0.0 --port 8700 --reload --ssl-keyfile "D:/ssl/hualenbus.labelnine.app-key.pem" --ssl-certfile "D:/ssl/hualenbus.labelnine.app-chain.pem"
uvicorn Server:app --host 0.0.0.0 --port 8700 --reload --ssl-keyfile "D:/ssl/lab109.257895412.xyz-key.pem" --ssl-certfile "D:/ssl/lab109.257895412.xyz-chain.pem"
# 🚌 H_Bus 專案環境部署指引

本映像提供完整開發環境（Node.js + Python + FastAPI），  
不包含 `.env`、SSL 憑證、Redis、MariaDB。  
他們需在 Docker 外或自行建立。

---

## 📦 建立映像

```bash
docker build -t hbus_env:latest .

docker run -it \
  -p 7001:7001 \
  -v $(pwd)/ssl:/home/jovyan/ssl \
  --name hbus_env \
  hbus_env:latest

進入後端程式目錄(Example)：
cd /home/jovyan/work/Git/H_Bus/my-bus-system 

啟動服務(Example)：
uvicorn Server:app \
  --host 0.0.0.0 \
  --port 7001 \
  --reload \
  --ssl-keyfile "/home/jovyan/ssl/hualenbus.labelnine.app-key.pem" \
  --ssl-certfile "/home/jovyan/ssl/hualenbus.labelnine.app-chain.pem"

開發者需自行準備 
# .env (都在client下)
- Route (https)
FRONTEND_DEFAULT_URL = https://hualenbus.labelnine.app:7001 (Example)

 - Line
LINE_CHANNEL_ID =
LINE_CHANNEL_SECRET =

 - Session PW
APP_SESSION_SECRET =

 - Google Email Api Key
Sender_email = ""
Password_email = ""

 - MySQL
Host = "host"
User = "root"
Port = 3307
Password_SQL = "pw"
Database = 'bus_system'

 - Payment Api
MERCHANT_ID = XXX
TERMINAL_ID = XXX
STORE_CODE  = XXX
KEY = ""
IV  = ""
LAYMON = "iqrc.epay365.com.tw"

# .env.development
VITE_API_BASE_URL=https://hualenbus.labelnine.app:7001
VITE_AUTH_BASE_URL=https://hualenbus.labelnine.app:7001

# .env.production
VITE_API_BASE_URL=/api
VITE_AUTH_BASE_URL=

# Redis 與 MariaDB(要匯入資料表)
這兩個可在 Docker 以外安裝，

# 自建 SSL 憑證 (Example)
/home/jovyan/ssl/
 ├─ hualenbus.labelnine.app-key.pem
 └─ hualenbus.labelnine.app-chain.pem

# 更新程式碼
容器內的程式碼位於：
/home/jovyan/work/Git/H_Bus/
可透過 git 更新
git pull

# 前端啟動範例
如需重新 build
cd /home/jovyan/work/Git/H_Bus/client
npm run build

# 備註
映像僅含 Python/Node.js 依賴與程式碼。
不含任何 .env、SSL、Redis、MariaDB。
Port 可自行指定，例如：

docker run -it -p 8080:7001 hbus_env:latest

