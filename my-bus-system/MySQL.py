import pymysql
import sqlite3

Infor = {
    "host": "10.53.1.3",
    "user": "root",
    "port": 7000,
    "password": "dh9j2(HU#s9h",
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
        result = "Query executed."

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
