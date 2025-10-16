from Backend.MySQL import MySQL_Doing
import pandas as pd
import math

# --- 計算兩點距離 (Haversine公式) ---
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000  # 地球半徑（公尺）
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

# --- 統一方向名稱 ---
def normalize_direction(x):
    t = str(x or "").strip()
    if "返" in t or "回" in t or t == "1":
        return "返程"
    return "去程"

# --- 連線 ---
db = MySQL_Doing()

# 撈出所有「正常營運」的班次
dfB = pd.DataFrame(db.run('SELECT * FROM route_schedule WHERE operation_status = "正常營運"'))
if dfB.empty:
    print("❌ 沒有正常營運的班次")
    exit()

dfB["direction"] = dfB["direction"].map(normalize_direction)
print("🚌 營運班次：")
print(dfB[["route_no", "direction", "license_plate"]])

# 撈出所有站點
dfA = pd.DataFrame(db.run('SELECT route_id, direction, latitude, longitude, stop_name FROM bus_route_stations'))
if dfA.empty:
    print("❌ 找不到站點資料")
    exit()

dfA["direction"] = dfA["direction"].map(normalize_direction)
print("\n📍 站點資料：")
print(dfA.head())

# 結果儲存
results = []

# --- 主流程：逐台車找最近站 ---
for _, row in dfB.iterrows():
    plate = row["license_plate"]
    route_id = int(row["route_no"])
    direction = row["direction"]

    # 抓該車的最新位置（注意 X=經度, Y=緯度）
    sql = f'SELECT Y AS latitude, X AS longitude FROM ttcarimport WHERE car_licence = "{plate}" ORDER BY seq DESC LIMIT 1'
    dfC = pd.DataFrame(db.run(sql))
    if dfC.empty:
        print(f"⚠️ 找不到 {plate} 的座標")
        continue

    car_lat = float(dfC.iloc[0]["latitude"])
    car_lon = float(dfC.iloc[0]["longitude"])

    # 找該路線該方向的所有站
    df_route = dfA.loc[(dfA["route_id"] == route_id) & (dfA["direction"] == direction)].copy()
    if df_route.empty:
        print(f"⚠️ 找不到 {route_id} {direction} 的站點資料")
        continue

    # 計算距離
    df_route.loc[:, "distance_m"] = df_route.apply(
        lambda s: haversine(car_lat, car_lon, float(s["latitude"]), float(s["longitude"])),
        axis=1
    )

    # 找出最近站
    nearest = df_route.loc[df_route["distance_m"].idxmin()]

    results.append({
        "license_plate": plate,
        "route_id": route_id,
        "direction": direction,
        "nearest_stop": nearest["stop_name"],
        "distance_m": round(nearest["distance_m"], 1)
    })

# --- 結果輸出 ---
if results:
    df_result = pd.DataFrame(results)
    print("\n🚏 最近站點結果：")
    print(df_result)
else:
    print("❌ 沒有任何車輛找到最近站點。")
