import pymysql
import sqlite3
import os
from dotenv import load_dotenv

# 載入 .env 檔
load_dotenv()

Infor = {
    "host": os.getenv("MYSQL_HOST"),
    "user": os.getenv("MYSQL_USER"),
    "port": int(os.getenv("MYSQL_PORT")),  # 若未設置，預設 3306
    "password": os.getenv("MYSQL_PASSWORD"),
    "database": os.getenv("MYSQL_DATABASE"),
    "table": os.getenv("MYSQL_TABLE")
}

db_path = os.getenv("SQLITE_PATH")

def init(Parameter):
    mydb = pymysql.connect(
        host=Parameter["host"],
        user=Parameter["user"],
        port=Parameter["port"],
        password=Parameter["password"],
        database=Parameter["database"],
        charset="utf8mb4",
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
        result = {"status": "ok", "lastrowid": mycursor.lastrowid}

    mycursor.close()
    mydb.close()

    return result

def Sqlite_Run(query, db_path=db_path):
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
