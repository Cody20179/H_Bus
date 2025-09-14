from __future__ import annotations

import asyncio
import math
import os
import random
from datetime import datetime
from typing import Dict, List, Tuple, Deque, Iterable, Optional
from collections import deque

from fastapi import FastAPI, Body, HTTPException, Request
from fastapi.responses import PlainTextResponse
import uvicorn


app = FastAPI(title="小巴 - 即時隨機GIS模擬器")


# 目標參考點（緯度, 經度）
BASE_POINTS: List[Tuple[float, float]] = [
    (23.99302, 121.603219),
    (23.992912, 121.617817),
    (23.992744, 121.619466),
    (23.991411, 121.619984),
    (23.989522, 121.619688),
]


# 模擬參數（可用環境變數覆蓋）
NUM_VEHICLES = int(os.getenv("HBUS_VEHICLES", "5"))
INTERVAL_SEC = int(os.getenv("HBUS_INTERVAL_SEC", "1"))  # 預設5分鐘=300秒
VENDOR_CODE = int(os.getenv("HBUS_VENDOR_CODE", "12345678"))
JITTER_RADIUS_M = float(os.getenv("HBUS_JITTER_RADIUS_M", "50"))  # 每次更新的擾動半徑（公尺）


def meters_to_deg_lat(meters: float) -> float:
    return meters / 111_320.0


def meters_to_deg_lon(meters: float, lat_deg: float) -> float:
    return meters / (111_320.0 * max(0.000001, math.cos(math.radians(lat_deg))))


def jitter_around(lat: float, lon: float, radius_m: float) -> Tuple[float, float]:
    # 在指定半徑內隨機偏移（均勻分布）
    r = radius_m * math.sqrt(random.random())
    theta = random.uniform(0, 2 * math.pi)
    dlat = meters_to_deg_lat(r * math.sin(theta))
    dlon = meters_to_deg_lon(r * math.cos(theta), lat)
    return lat + dlat, lon + dlon


def format_time_now() -> str:
    return datetime.now().strftime("%Y/%m/%d %H:%M:%S")


def make_plate(idx: int) -> str:
    return f"ABC-{idx:04d}"


def make_record(plate: str, lat: float, lon: float) -> Dict:
    speed = round(random.uniform(0, 50), 1)  # km/h
    heading = round(random.uniform(0, 359), 1)
    quality = random.randint(10, 30)
    satellites = random.randint(4, 12)
    return {
        "車牌": plate,
        "日期時間": format_time_now(),
        "車輛狀態": 0,
        "是否補傳": 0,
        "定位狀態": "A",
        "東經": round(lon, 6),
        "北緯": round(lat, 6),
        "速度": speed,
        "車頭方向": heading,
        "訊號品質": quality,
        "衛星數": satellites,
        "廠商代號": VENDOR_CODE,
        "結束字元": "\r",
    }


# 內存中保存每台車的最新資料
latest_by_plate: Dict[str, Dict] = {}
# 追蹤每台車的歷史軌跡（固定長度，可動態調整）
HISTORY_LEN = int(os.getenv("HBUS_HISTORY_LEN", "120"))  # 約 120 點
history_by_plate: Dict[str, Deque[Dict]] = {}


async def generator_task():
    """背景產生器：根據目前 NUM_VEHICLES 與 BASE_POINTS 產生資料。
    支援在執行期透過 /sim/config 調整，必要時會重啟此任務。
    """
    global latest_by_plate
    # 初始化車牌與 anchor
    app.state.plates = [make_plate(i + 1) for i in range(NUM_VEHICLES)]
    app.state.anchors = [BASE_POINTS[i % len(BASE_POINTS)] for i in range(NUM_VEHICLES)]

    while True:
        await update_once_current()
        await asyncio.sleep(INTERVAL_SEC)


async def update_once_current():
    """產生一次最新數據（供背景循環或 /sim/tick 呼叫）。"""
    plates: List[str] = getattr(app.state, 'plates', [])
    anchors: List[Tuple[float, float]] = getattr(app.state, 'anchors', [])
    if not plates:
        return
    for plate, (base_lat, base_lon) in zip(plates, anchors):
        lat, lon = jitter_around(base_lat, base_lon, JITTER_RADIUS_M)
        rec = make_record(plate, lat, lon)
        latest_by_plate[plate] = rec
        dq = history_by_plate.get(plate)
        if dq is None:
            dq = history_by_plate[plate] = deque(maxlen=HISTORY_LEN)
        dq.append(rec)


@app.on_event("startup")
async def on_startup():
    # 啟動背景產生器
    app.state._task = asyncio.create_task(generator_task())


@app.get("/realtime")
def get_realtime() -> List[Dict]:
    # 回傳所有車輛的最新資料（列表）
    return list(latest_by_plate.values())


@app.post("/realtime")
def get_realtime_by_plate(payload = Body(...)) -> PlainTextResponse:
    """
    以 POST 方式取得單一車輛的最新 GIS 資料。

    支援的輸入格式（任擇其一）：
    - 純數字（1~N）：代表第 N 台車（對應 ABC-000N）
    - 純字串：若為車牌（如 ABC-0003）則回傳該車資料；若可轉為數字亦視同索引
    - JSON 物件：可提供以下鍵之一
        - 車號 / 車牌 / plate / Plate / license：車牌字串
        - 序號 / 編號 / index / id：1~N 的整數索引
        - 路徑 / 路線 / route / path：1~len(BASE_POINTS) 的整數，對應參考點；將回傳分配到該點的第一台車
    """

    def plate_by_index(i: int) -> str:
        if i < 1 or i > NUM_VEHICLES:
            raise HTTPException(status_code=400, detail=f"索引超出範圍 1~{NUM_VEHICLES}")
        return make_plate(i)

    # 1) 原始型別：數字或字串
    if isinstance(payload, int):
        plate = plate_by_index(payload)
        rec = latest_by_plate.get(plate)
        if rec is None:
            raise HTTPException(status_code=404, detail=f"找不到車號 {plate} 的資料")
        return PlainTextResponse(_record_to_line(rec))
    if isinstance(payload, str):
        # 若是數字字串視為索引，否則視為車牌
        s = payload.strip()
        if s.isdigit():
            plate = plate_by_index(int(s))
        else:
            plate = s
        rec = latest_by_plate.get(plate)
        if rec is None:
            raise HTTPException(status_code=404, detail=f"找不到車號 {plate} 的資料")
        return PlainTextResponse(_record_to_line(rec))

    # 2) JSON 物件
    if isinstance(payload, dict):
        plate = (
            payload.get("車號")
            or payload.get("車牌")
            or payload.get("plate")
            or payload.get("Plate")
            or payload.get("license")
        )

        if plate:
            plate = str(plate)
            rec = latest_by_plate.get(plate)
            if rec is None:
                raise HTTPException(status_code=404, detail=f"找不到車號 {plate} 的資料")
            return PlainTextResponse(_record_to_line(rec))

        # 索引鍵
        index_val = (
            payload.get("序號")
            or payload.get("編號")
            or payload.get("index")
            or payload.get("id")
        )
        if index_val is not None:
            try:
                idx = int(index_val)
            except Exception:
                raise HTTPException(status_code=400, detail="序號/index 必須為整數")
            plate = plate_by_index(idx)
            rec = latest_by_plate.get(plate)
            if rec is None:
                raise HTTPException(status_code=404, detail=f"找不到車號 {plate} 的資料")
            return rec

        # 路徑/路線：用 1~len(BASE_POINTS) 對應參考點，選回第一個分配到該點的車
        route_val = (
            payload.get("路徑")
            or payload.get("路線")
            or payload.get("route")
            or payload.get("path")
        )
        if route_val is not None:
            try:
                ridx = int(route_val)
            except Exception:
                raise HTTPException(status_code=400, detail="路徑/路線 必須為整數")
            if ridx < 1 or ridx > len(BASE_POINTS):
                raise HTTPException(status_code=400, detail=f"路徑/路線 範圍 1~{len(BASE_POINTS)}")
            # 找到第一台分配到該 anchor 的車（依初始化 anchors 的邏輯）
            # anchors[i] = BASE_POINTS[i % len(BASE_POINTS)]
            target_anchor = BASE_POINTS[ridx - 1]
            # 根據 anchors 分配規則，符合條件的車牌索引為 {i | i % len(BASE_POINTS) == ridx-1}
            candidates: List[str] = []
            for i in range(NUM_VEHICLES):
                if (i % len(BASE_POINTS)) == (ridx - 1):
                    candidates.append(make_plate(i + 1))
            # 回傳第一個有資料的
            for plate in candidates:
                rec = latest_by_plate.get(plate)
                if rec is not None:
                    return PlainTextResponse(_record_to_line(rec))
            raise HTTPException(status_code=404, detail=f"該路徑目前沒有可用車輛資料")

    # 其他型別不支援
    raise HTTPException(status_code=400, detail="請輸入 1~N、車號/車牌、或包含路徑/序號的 JSON")


def _record_to_line(rec: Dict) -> str:
    """將單筆記錄轉成指定 CSV 字串（含尾逗號與 CR）。"""
    plate = rec.get("車牌", "")
    dt = rec.get("日期時間", "")
    vstate = rec.get("車輛狀態", 0)
    retry = rec.get("是否補傳", 0)
    fix = rec.get("定位狀態", "A")
    lon = float(rec.get("東經", 0.0))
    lat = float(rec.get("北緯", 0.0))
    speed = float(rec.get("速度", 0.0))
    heading = float(rec.get("車頭方向", 0.0))
    quality = int(rec.get("訊號品質", 0))
    sats = int(rec.get("衛星數", 0))
    vendor = int(rec.get("廠商代號", VENDOR_CODE))
    # 注意順序與格式，小數位與樣例一致，最後保留逗號，並接 CR
    line = (
        f"{plate},{dt},{vstate},{retry},{fix},{lon:.6f},{lat:.6f},{speed:.1f},{heading:.1f},{quality},{sats},{vendor},\r"
    )
    return line


@app.get("/Buson")
def bus_on_first() -> Dict | str:
    # 維持與原本路徑相近的用途：取第一台車資料
    if not latest_by_plate:
        # 若尚未生成，臨時返回一筆固定格式（與原本字串類似）
        return "ABC-0123,2014/10/10 10:10:10,0,0,A,121.374193,25.000137,13.2,120.0,20,5,12345678,\r"
    # 否則回傳任一台車的JSON（更易於後續處理）
    first_key = next(iter(latest_by_plate))
    return latest_by_plate[first_key]


# ====== 實用計算工具 ======
def haversine_km(a_lat: float, a_lon: float, b_lat: float, b_lon: float) -> float:
    R = 6371.0088
    dlat = math.radians(b_lat - a_lat)
    dlon = math.radians(b_lon - a_lon)
    lat1 = math.radians(a_lat)
    lat2 = math.radians(b_lat)
    s = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 2 * R * math.asin(math.sqrt(max(0.0, s)))

def _as_feature(rec: Dict) -> Dict:
    return {
        "type": "Feature",
        "geometry": { "type": "Point", "coordinates": [rec.get("東經"), rec.get("北緯")] },
        "properties": {k: v for k, v in rec.items() if k not in ("東經", "北緯")}
    }


# ====== 進階 API：GeoJSON、最近車、半徑內、歷史 ======
@app.get("/realtime/geojson")
def realtime_geojson() -> Dict:
    feats = [_as_feature(r) for r in latest_by_plate.values()]
    return { "type": "FeatureCollection", "features": feats }


@app.get("/realtime/nearest")
def realtime_nearest(lat: float, lon: float, k: int = 1) -> List[Dict]:
    """找距離 (lat,lon) 最近的 k 台車，回傳附帶距離(km)。"""
    rows = []
    for rec in latest_by_plate.values():
        d = haversine_km(lat, lon, float(rec.get("北緯", 0.0)), float(rec.get("東經", 0.0)))
        item = dict(rec)
        item["距離_km"] = round(d, 3)
        rows.append(item)
    rows.sort(key=lambda r: r.get("距離_km", 9e9))
    return rows[:max(1, int(k))]


@app.get("/realtime/within")
def realtime_within(lat: float, lon: float, radius_m: float = 300.0) -> List[Dict]:
    """找半徑 radius_m 內的所有車輛。"""
    km = max(0.0, float(radius_m)) / 1000.0
    rows = []
    for rec in latest_by_plate.values():
        d = haversine_km(lat, lon, float(rec.get("北緯", 0.0)), float(rec.get("東經", 0.0)))
        if d <= km:
            item = dict(rec)
            item["距離_km"] = round(d, 3)
            rows.append(item)
    rows.sort(key=lambda r: r.get("距離_km", 9e9))
    return rows


@app.get("/realtime/vehicle/{plate}")
def realtime_vehicle(plate: str) -> Dict:
    rec = latest_by_plate.get(plate)
    if not rec:
        raise HTTPException(status_code=404, detail=f"找不到車號 {plate}")
    return rec


@app.get("/realtime/history")
def realtime_history(plate: str, n: int = 20, as_geojson: bool = False) -> Dict:
    dq = history_by_plate.get(plate)
    if not dq:
        raise HTTPException(status_code=404, detail=f"找不到車號 {plate} 的歷史資料")
    n = max(1, min(int(n), HISTORY_LEN))
    rows = list(dq)[-n:]
    if as_geojson:
        return {
            "type": "FeatureCollection",
            "features": [_as_feature(r) for r in rows]
        }
    return { "plate": plate, "points": rows, "count": len(rows) }


@app.get("/health")
def health():
    return {
        "ok": True,
        "vehicles": len(getattr(app.state, 'plates', [])),
        "interval_sec": INTERVAL_SEC,
        "jitter_radius_m": JITTER_RADIUS_M,
        "history_len": HISTORY_LEN,
    }


# ===== 動態設定：讓數據「會動」且可即時調整 =====
def _restart_sim():
    """重啟背景產生器（用於調整車數或 anchor 點）。"""
    task = getattr(app.state, '_task', None)
    if task and not task.done():
        task.cancel()
    # 清空當前資料
    latest_by_plate.clear()
    history_by_plate.clear()
    # 重新啟動
    app.state._task = asyncio.create_task(generator_task())


@app.get("/sim/config")
def sim_get_config():
    return {
        "num_vehicles": NUM_VEHICLES,
        "interval_sec": INTERVAL_SEC,
        "jitter_radius_m": JITTER_RADIUS_M,
        "history_len": HISTORY_LEN,
        "plates": getattr(app.state, 'plates', []),
        "anchors": getattr(app.state, 'anchors', []),
    }


@app.post("/sim/config")
async def sim_set_config(payload: Dict = Body(...)):
    global NUM_VEHICLES, INTERVAL_SEC, JITTER_RADIUS_M, HISTORY_LEN, BASE_POINTS
    need_restart = False
    if 'interval_sec' in payload:
        INTERVAL_SEC = float(payload['interval_sec'])
    if 'jitter_radius_m' in payload:
        JITTER_RADIUS_M = float(payload['jitter_radius_m'])
    if 'history_len' in payload:
        HISTORY_LEN = int(payload['history_len'])
        # 更新 deque 的長度
        for k, dq in list(history_by_plate.items()):
            history_by_plate[k] = deque(list(dq)[-HISTORY_LEN:], maxlen=HISTORY_LEN)
    if 'num_vehicles' in payload:
        NUM_VEHICLES = int(payload['num_vehicles'])
        need_restart = True
    if 'points' in payload or 'base_points' in payload:
        pts = payload.get('points') or payload.get('base_points')
        if not isinstance(pts, list) or not pts:
            raise HTTPException(status_code=400, detail='points 需要非空陣列')
        try:
            BASE_POINTS = [(float(p['lat']), float(p['lon'])) for p in pts]
        except Exception:
            raise HTTPException(status_code=400, detail='points 需為 {lat, lon} 陣列')
        need_restart = True
    if need_restart:
        _restart_sim()
        # 等待第一筆資料
        await asyncio.sleep(0)
    else:
        # 立即 tick 一次讓前端看到變化（如 interval/jitter）
        await update_once_current()
    return {"ok": True, **sim_get_config()}


@app.post("/sim/tick")
async def sim_tick():
    await update_once_current()
    return {"ok": True, "count": len(latest_by_plate)}


@app.post("/sim/reset")
async def sim_reset():
    _restart_sim()
    await asyncio.sleep(0)
    return {"ok": True}


if __name__ == "__main__":
    uvicorn.run("Realtime_Bus:app", host="0.0.0.0", port=8501, reload=True)
