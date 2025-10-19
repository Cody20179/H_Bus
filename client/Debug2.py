from Backend.MySQL import MySQL_Doing
import pandas as pd
import math
import os

mysql_doing = MySQL_Doing()
ID = [46, 42, 43, 47, 45, 44, 41, 48]
for i in range(1, 9):
    df = pd.read_csv("E:\CODY\Program\H_Bus\Client\到站時刻.csv")
    times = df[f"Unnamed: {i}"].iloc[31:39].tolist()
    formatted = ",".join(times)
    print(f"Column {i}:, ID: {ID[i-1]}")
    # print(formatted)
    print(fr"""
    UPDATE bus_route_stations
    SET schedule = '{formatted}'
    WHERE station_id = {ID[i-1]};
    """)