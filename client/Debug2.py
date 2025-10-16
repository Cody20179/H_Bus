from Backend.MySQL import MySQL_Doing
import pandas as pd
import math
import os

mysql_doing = MySQL_Doing()

df = pd.read_csv("E:\CODY\Program\H_Bus\Client\到站時刻.csv")
times = df["Unnamed: 7"].iloc[16:27].tolist()
formatted = ",".join(times)
print(formatted)