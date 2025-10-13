# =========================
# 基底映像
# =========================
FROM jupyter/base-notebook:latest

WORKDIR /home/jovyan/work/Git/H_Bus

# =========================
# 安裝系統相依套件
# =========================
RUN apt update && apt install -y \
    curl gnupg lsb-release build-essential \
    nodejs npm iputils-ping \
    && apt clean && rm -rf /var/lib/apt/lists/*

# =========================
# 複製專案程式碼
# =========================
COPY client ./client
COPY my-bus-system ./my-bus-system
COPY README.md ./

# =========================
# 安裝 Python 套件
# =========================
WORKDIR /home/jovyan/work/Git/H_Bus/my-bus-system
RUN pip install --no-cache-dir requests fastapi uvicorn

# =========================
# 安裝前端相依並編譯
# =========================
WORKDIR /home/jovyan/work/Git/H_Bus/client
RUN npm install && npm run build

# =========================
# 開放常用埠
# =========================
EXPOSE 7000-7015 7022

# =========================
# 不自動啟動任何服務，交給使用者手動跑
# =========================
CMD ["/bin/bash"]
