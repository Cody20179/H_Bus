from Backend.MySQL import MySQL_Doing
import pandas as pd
import math

mysql_doing = MySQL_Doing()

# 你想查的路線與車牌
route_id = 2
license_plate = "ABS-002"

# ---------- 函式：Haversine 計算兩點距離 ----------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000  # 地球半徑（公尺）
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

# ---------- 取得最新車輛位置 ----------
car_query = f"""
SELECT * FROM ttcarimport 
WHERE car_licence = '{license_plate}'
ORDER BY Gpstime DESC 
LIMIT 1;
"""
df_car = pd.DataFrame(mysql_doing.run(car_query))
if df_car.empty:
    print("❌ 找不到該車輛資料")
    exit()

car_lat = float(df_car["X"].iloc[0])
car_lon = float(df_car["Y"].iloc[0])

# ---------- 取得該路線的站點 ----------
station_query = f"""
SELECT station_id, stop_name, latitude, longitude, stop_order, direction
FROM bus_route_stations 
WHERE route_id = {route_id};
"""
df_stations = pd.DataFrame(mysql_doing.run(station_query))
if df_stations.empty:
    print("❌ 找不到該路線的站點資料")
    exit()

# ---------- 計算距離 ----------
df_stations["distance_m"] = df_stations.apply(
    lambda row: haversine(car_lat, car_lon, float(row["latitude"]), float(row["longitude"])),
    axis=1
)

# ---------- 找出最近的站點 ----------
nearest = df_stations.loc[df_stations["distance_m"].idxmin()]

# ---------- 輸出結果 ----------
print(f"車牌：{license_plate}")
print(f"最近的站點：{nearest['stop_name']}（距離約 {nearest['distance_m']:.1f} 公尺）")
print(f"方向：{nearest['direction']}")
print(f"預估順序：第 {nearest['stop_order']} 站 / 總共 {len(df_stations)} 站")
print(f"該站點 ID：{nearest['station_id']}")
