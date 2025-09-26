from dotenv import load_dotenv
import pymysql
import pandas as pd
import os

load_dotenv()

Infor = {
 'host': os.getenv("Host", "127.0.0.1"),
 'user': os.getenv("User", "root"),
 'port': int(os.getenv("Port", 3306)),
 'password': os.getenv("Password_SQL", ""),
 'database': os.getenv("Database", ""),
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

class MySQL_Doing:
    def __init__(self):
        self.Host = os.getenv("Host", "127.0.0.1")
        self.User = os.getenv("User", "root")
        self.Port = int(os.getenv("Port", 3306))
        self.Password = os.getenv("Password_SQL", "")
        self.Database = os.getenv("Database", "")

    def _connect(self):
        """每次呼叫都新建連線，保證最新資料"""
        return pymysql.connect(
            host=self.Host,
            user=self.User,
            port=self.Port,
            password=self.Password,
            database=self.Database,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor
        )

    def run(self, sql: str):
        """通用 SQL 執行，查詢回傳 DataFrame，其它回傳影響筆數"""
        mydb = self._connect()
        try:
            with mydb.cursor() as cursor:
                cursor.execute(sql)
                if sql.strip().lower().startswith(("select", "show", "desc")):
                    result = pd.DataFrame(cursor.fetchall())
                else:
                    mydb.commit()
                    result = cursor.rowcount
            return result
        finally:
            mydb.close()

    def select_all(self, tablename):
        return self.run(f"SELECT * FROM {tablename};")

    def insert(self, tablename, columns, values):
        vals_str_list = []
        for v in values:
            if isinstance(v, str) and v.startswith("b'"):
                vals_str_list.append(v)
            elif isinstance(v, (int, float)):
                vals_str_list.append(str(v))
            else:
                vals_str_list.append(f"'{v}'")
        cols_str = ", ".join(columns)
        vals_str = ", ".join(vals_str_list)
        sql = f"INSERT INTO {tablename} ({cols_str}) VALUES ({vals_str});"
        return self.run(sql)

    def update(self, tablename, set_clause, where_clause="1=1"):
        return self.run(f"UPDATE {tablename} SET {set_clause} WHERE {where_clause};")

    def delete(self, tablename, where_clause="1=1"):
        return self.run(f"DELETE FROM {tablename} WHERE {where_clause};")

    def create_table(self, sql):
        return self.run(sql)

    def create_database(self, dbname):
        return self.run(f"CREATE DATABASE {dbname};")

    def drop_table(self, tablename):
        return self.run(f"DROP TABLE {tablename};")

    def drop_database(self, dbname):
        return self.run(f"DROP DATABASE {dbname};")

    def alter_table(self, sql):
        return self.run(sql)

    def truncate(self, tablename):
        return self.run(f"TRUNCATE TABLE {tablename};")

    def close(self):
        self.mydb.close()