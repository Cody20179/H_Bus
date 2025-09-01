from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import httpx

app = FastAPI()

# 允許前端請求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 你的座標清單（經緯度順序要正確！）
coords = [
    (23.993020,121.603219),
    (23.992912,121.617817),
    (23.992744,121.619466),
    (23.991411,121.619984),
    (23.989522,121.619688),
    (23.988424,121.618438),
    (23.991812,121.616885),
    (23.991411,121.619984)
]

@app.get("/snap")
async def snap_route():
    route_param = ';'.join([f"{lat},{lng}" for lat, lng in coords])
    url = f"https://api.nlsc.gov.tw/roadnet/v1/route/snap?route={route_param}"
    async with httpx.AsyncClient() as client:
        r = await client.get(url)
        return r.json()
