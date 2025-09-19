import pandas as pd
import pymysql

Infor = {
 'host': '192.168.0.126',
 'user': 'root',
 'port': 3307,
 'password': '109109',
 'database': 'bus_system',
 }

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

def Show_Tables():
    Tables = MySQL_Run("SHOW TABLES")
    Tables = pd.DataFrame(Tables)
    return Tables

def MySQL_Run2(query, params=None, Parameter=Infor):
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
    return result
