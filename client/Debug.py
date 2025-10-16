from Backend.MySQL import MySQL_Doing
import pandas as pd
import math

# --- 計算兩點距離 (Haversine公式) ---
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000  # 地球半徑（公尺）
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

# --- 初始化 ---
mysql_doing = MySQL_Doing()
Route_ID = 1

# --- 取得路線排程 ---
route_results = mysql_doing.run(f"SELECT * FROM route_schedule WHERE route_no = {Route_ID} LIMIT 1;")
df_route = pd.DataFrame(route_results)
license_plate = df_route["license_plate"].iloc[0]
direction = df_route["direction"].iloc[0]

# --- 最新車輛位置 ---
car_results = mysql_doing.run(
    f'SELECT * FROM ttcarimport WHERE car_licence = "{license_plate}" ORDER BY Gpstime DESC LIMIT 1;'
)
df_car = pd.DataFrame(car_results)
car_lat = float(df_car["X"].iloc[0])
car_lon = float(df_car["Y"].iloc[0])

# --- 站點資料 ---
station_results = mysql_doing.run(
    f'SELECT * FROM bus_route_stations WHERE route_id = "{Route_ID}" AND direction = "{direction}";'
)
df_station = pd.DataFrame(station_results)

# --- 計算距離並找出最近站 ---
df_station["distance_m"] = df_station.apply(
    lambda row: haversine(car_lat, car_lon, float(row["latitude"]), float(row["longitude"])),
    axis=1
)
nearest = df_station.loc[df_station["distance_m"].idxmin()]

# --- 輸出結果 ---
print(f"車牌：{license_plate}")
print(f"最近的站點：{nearest['stop_name']}（距離約 {nearest['distance_m']:.1f} 公尺）")
print(f"預估順序：第 {nearest['stop_order']} 站 / 總共 {len(df_station)} 站")
print(f"該站點ID：{nearest['station_id']}")
