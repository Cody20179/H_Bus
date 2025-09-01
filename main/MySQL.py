import pymysql
import sqlite3

Infor = {
    "host": "10.53.1.3",
    "user": "root",
    "port": 7000,
    "password": "dh9j2(HU#s9h",
    "database": "5Glabs",
    "table": "IOT_DPM_C530E"
}

# Infor = {
#     "host": "26.45.49.217",
#     "user": "root",
#     "port": 3306,
#     "password": "109109",
#     "database": "cody",
#     "table": "IOT_DPM_C530E"
# }

db_path = r'D:\2025Cody\python311\Lib\site-packages\open_webui\data\webui.db'

def init(Parameter):
    mydb = pymysql.connect(
        host=Parameter["host"],
        user=Parameter["user"],
        port=Parameter["port"],
        password=Parameter["password"],
        database=Parameter["database"]
    )
    return mydb

def MySQL_Run(query, Parameter=Infor):
    mydb = init(Parameter)
    mycursor = mydb.cursor()
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
