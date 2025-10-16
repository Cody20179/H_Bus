import pymysql
import sqlite3

Infor = {
    "host": "192.168.0.126",
    "user": "root",
    "port": 3307,
    "password": "109109",
    "database": "bus_system",
    "table": "bus_route_stations"
}

db_path = r'D:\2025Cody\python311\Lib\site-packages\openh_webui\data\webui.db'

def init(Parameter):
    mydb = pymysql.connect(
        host=Parameter["host"],
        user=Parameter["user"],
        port=Parameter["port"],
        password=Parameter["password"],
        database=Parameter["database"],
        charset="utf8mb4",               # 關鍵
        cursorclass=pymysql.cursors.DictCursor
    )
    return mydb

def MySQL_Run(query, params=None, Parameter=Infor):
    mydb = init(Parameter)
    mycursor = mydb.cursor()
    
    if params:
        mycursor.execute(query, params)
    else:
        mycursor.execute(query)

    if query.strip().lower().startswith(("select", "show", "desc")):
        result = mycursor.fetchall()
    else:
        mydb.commit()
        # 回傳 lastrowid 以便呼叫端能取得自動增量 id
        last_id = mycursor.lastrowid
        result = {"status": "ok", "lastrowid": last_id}

    mycursor.close()
    mydb.close()

    return (result)

def Sqlite_Run(query, db_path = db_path):
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            if query == "show tables":
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                result = cursor.fetchall()

            elif query.strip().lower().startswith(("select", "show", "desc", "pragma")):
                cursor.execute(query)
                result = cursor.fetchall()
            else:
                cursor.execute(query)
                conn.commit()
                result = "Query executed."
    except Exception as e:
        result = f"Error: {e}"
    
    return result
