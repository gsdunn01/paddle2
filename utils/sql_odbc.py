"""A dummy docstring."""
from typing import Any
import pyodbc
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

def get_db_conn_string() -> str:
    """."""
    
    #DESKTOP-1Q8OND1\SQLEXPRESS01
    sql: str = ("Driver={ODBC Driver 17 for SQL Server};"
                          r"Server=DESKTOP-1Q8OND1\SQLEXPRESS01;"
                          "Database=paddle;"
                          "Trusted_Connection=yes;")
    return sql

def get_db_conn() -> pyodbc.Connection:
    """A dummy docstring."""
    conn = pyodbc.connect(get_db_conn_string(), autocommit=True)
    return conn

def exec_sql_bulk(sqls: list[str]) -> None:
    """A dummy docstring."""
    counts = 0
    conn: pyodbc.Connection = get_db_conn()
    cursor: pyodbc.Cursor = conn.cursor()
    insert_stmt="BEGIN TRANSACTION; "
    for sql in sqls:
        counts += 1
        insert_stmt += sql + "; "
        #The modulus is the batch size
        if counts % 100 == 0:
            insert_stmt+="COMMIT TRANSACTION"
            final_sql = "SET NOCOUNT ON; "
            final_sql+=insert_stmt
            cursor.execute(final_sql)
            cursor.commit()
            insert_stmt="BEGIN TRANSACTION; "
    #get the last batch
    if insert_stmt!="BEGIN TRANSACTION; ":
        insert_stmt+="COMMIT TRANSACTION"
        final_sql = "SET NOCOUNT ON; "
        final_sql+=insert_stmt
        cursor.execute(final_sql)
        cursor.commit()
    sqls.clear()

def exec_sql(sql: str) -> None:
    """."""
    conn: Any
    conn = get_db_conn()
    cursor: Any
    cursor = conn.cursor()
    cursor.execute(sql)
    cursor.commit()
    conn.close()
 
def get_df(sql: str) -> pd.DataFrame:    
    conn: pyodbc.Connection = get_db_conn()
    cursor: pyodbc.Cursor = conn.cursor()
    cursor.execute(sql)
    
    connection_url = URL.create("mssql+pyodbc", query={"odbc_connect": get_db_conn_string()})    
    engine = create_engine(connection_url)
    df: pd.DataFrame = pd.read_sql(sql,engine)
    
    #columns=[col[0] for col in cursor.description]
    #df: pd.DataFrame = pd.DataFrame(cursor.fetchall(),columns)        
    return df
 