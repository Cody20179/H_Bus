from dotenv import load_dotenv
from pymysql.err import OperationalError
import pymysql
import pandas as pd
import os

load_dotenv()

# ============================================================
# ✅ 改良後的 MySQL_Doing（自動重連＋回傳 DataFrame）
# ============================================================
class MySQL_Doing:
    def __init__(self):
        self.Host = os.getenv("Host", "127.0.0.1")
        self.User = os.getenv("User", "root")
        self.Port = int(os.getenv("Port", 3306))
        self.Password = os.getenv("Password_SQL", "")
        self.Database = os.getenv("Database", "")
        self.conn = self._connect()  # 💡 初始化連線

    def _connect(self):
        """建立新的資料庫連線"""
        return pymysql.connect(
            host=self.Host,
            user=self.User,
            port=self.Port,
            password=self.Password,
            database=self.Database,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True
        )

    def run(self, sql, params=None):
        """每次查詢都開新連線，確保執行安全"""
        try:
            conn = self._connect()
            with conn.cursor() as cursor:
                cursor.execute(sql, params or ())
                if cursor.description:
                    rows = cursor.fetchall()
                    return pd.DataFrame(rows)
                conn.commit()
                return None
        except OperationalError as e:
            print("[MySQL] OperationalError:", e)
            raise
        finally:
            try:
                conn.close()
            except:
                pass
