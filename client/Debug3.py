# ====================================
# 🧩 專案內部模組
# ====================================
from Backend import Define
from Backend.MySQL import MySQL_Doing

# ====================================
# 📦 第三方套件
# ====================================
from fastapi import FastAPI, Request, HTTPException, APIRouter, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from dotenv import load_dotenv
from pydantic import BaseModel, Field
import pandas as pd
import redis
import httpx

# ====================================
# ✅ 標準庫
# ====================================
import os
import json
import time
import hmac
import base64
import hashlib
import secrets
import requests
import urllib.parse
import numpy as np
import pandas as pd
from datetime import datetime
from urllib.parse import urlparse, quote
from binascii import unhexlify
from base64 import b64encode, b64decode
from decimal import Decimal, InvalidOperation
from typing import List

MySQL_Doing = MySQL_Doing()

def Get_GIS_About():
    """
    以 route_schedule 主導，回傳前端所需欄位：
    - route: 路線 ID
    - X, Y: 車輛經緯度（X=lng, Y=lat）
    - direction: 去程/返程
    - Current_Loaction: 最近站名
    - license_plate: 車牌號碼
    """

    # ---------- 1️⃣ 今日排班（正常營運） ----------
    sch = MySQL_Doing.run("""
        SELECT
          CAST(route_no AS SIGNED) AS route_id,
          direction,
          license_plate
        FROM route_schedule
        WHERE date = CURDATE()
          AND operation_status = '正常營運'
    """)

    if getattr(sch, "empty", False):
        return {"status": "success", "data": []}

    # ---------- 2️⃣ 取得所有車輛最新定位 ----------
    plates = sch["license_plate"].dropna().astype(str).unique().tolist()
    if not plates:
        return {"status": "success", "data": []}

    esc = [p.replace("'", "''") for p in plates]
    in_list = "','".join(esc)

    pos = MySQL_Doing.run(f"""
        SELECT
          car_licence AS license_plate,
          X, Y, Speed, Deg, acc, rcv_dt
        FROM ttcarimport
        WHERE car_licence IN ('{in_list}')
        AND rcv_dt = (
            SELECT MAX(rcv_dt)
            FROM ttcarimport t2
            WHERE t2.car_licence = ttcarimport.car_licence
        )
    """)

    if getattr(pos, "empty", False):
        return {"status": "success", "data": []}

    # ---------- 3️⃣ 站點資料 ----------
    route_ids = sch["route_id"].dropna().astype(int).unique().tolist()
    id_list = ",".join(str(i) for i in route_ids)
    stops = MySQL_Doing.run(f"""
        SELECT
          CAST(route_id AS SIGNED) AS route_id,
          direction,
          stop_name,
          CAST(latitude AS DECIMAL(12,8)) AS latitude,
          CAST(longitude AS DECIMAL(12,8)) AS longitude,
          CAST(stop_order AS SIGNED) AS stop_order
        FROM bus_route_stations
        WHERE route_id IN ({id_list})
        ORDER BY route_id, direction, stop_order
    """)

    if getattr(stops, "empty", False):
        return {"status": "success", "data": []}

    # ---------- 4️⃣ 合併車輛與站點，計算最近站 ----------
    import math
    def haversine(lat1, lon1, lat2, lon2):
        R = 6371000  # 地球半徑（公尺）
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    rows = []
    for _, row in sch.iterrows():
        route_id = int(row["route_id"])
        direction = str(row["direction"]).strip()
        plate = str(row["license_plate"])

        # 統一方向文字
        if direction in ["返程", "回", "1"]:
            direction = "回程"
        elif direction in ["去程", "往", "0"]:
            direction = "去程"

        # 找出該車的座標
        car = pos[pos["license_plate"] == plate]
        if car.empty:
            rows.append(dict(
                route=str(route_id),
                X=None, Y=None,
                direction=direction,
                Current_Loaction=None,
                license_plate=plate
            ))
            continue

        car_lat = float(car["Y"].iloc[0])
        car_lon = float(car["X"].iloc[0])

        # 該路線的所有站
        df_stations = stops[stops["route_id"] == route_id]
        if df_stations.empty:
            rows.append(dict(
                route=str(route_id),
                X=car_lon, Y=car_lat,
                direction=direction,
                Current_Loaction=None,
                license_plate=plate
            ))
            continue

        # 計算距離，找最近站
        df_stations["distance_m"] = df_stations.apply(
            lambda s: haversine(car_lat, car_lon, float(s["latitude"]), float(s["longitude"])),
            axis=1
        )
        nearest = df_stations.loc[df_stations["distance_m"].idxmin()]

        rows.append(dict(
            route=str(route_id),
            X=car_lon,
            Y=car_lat,
            direction=direction,
            Current_Loaction=str(nearest["stop_name"]),
            license_plate=plate
        ))

    # ---------- 5️⃣ 回傳結果 ----------
    df = pd.DataFrame(rows, columns=["route", "X", "Y", "direction", "Current_Loaction", "license_plate"])
    print(df[["route", "X", "Y", "direction", "Current_Loaction", "license_plate"]].to_dict())
    return df[["route", "X", "Y", "direction", "Current_Loaction", "license_plate"]].to_dict()
Data = Get_GIS_About()
print(Data)