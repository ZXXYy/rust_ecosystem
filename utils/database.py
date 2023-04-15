import sqlite3
import sys
import logging
from sqlite3 import Error
import os

conn = None
ROOT_PATH = os.path.dirname(os.path.abspath(__file__))
DB_PATH  = f"{ROOT_PATH}/.."

logging.basicConfig(format='%(asctime)s %(levelname)-3s: %(message)s',
                    datefmt='%m/%d/%Y %H:%M:%S')
logging.getLogger().setLevel(logging.INFO)


def create_connection(db_file):
    """Create a connection to sqlite3 database."""
    try:
        return sqlite3.connect(db_file, timeout=10)  # connection via sqlite3
    except Error as e:
        logging.error(e)
        sys.exit(1)


if not conn:
    conn = create_connection(f"{DB_PATH}/CVEfixes.db")
    print("connect to CVEFIXes")


def table_exists(table_name):
    """Checks table exists or not."""
    query = ("SELECT name FROM sqlite_master WHERE TYPE='table' AND name='"
             + table_name + "';")
    cursor = conn.cursor()
    cursor.execute(query)
    result = cursor.fetchone()
    if result is not None:
        return True
    else:
        return False


def execute_sql_cmd(query):
    cursor = conn.cursor()
    cursor.execute(query)


def execute_data_cmd(query, data):
    cursor = conn.cursor()
    cursor.execute(query, data)
    conn.commit()


def fetchone_query(table_name, col, value):
    """
    checks whether table exists or not
    :returns boolean yes/no
    """
    query = ("SELECT " + col + " FROM " + table_name + " WHERE repo_url='" + value + "'")
    cursor = conn.cursor()
    cursor.execute(query)
    result = cursor.fetchone()
    return True if result is not None else False


def write_database(table, df):
    try:
        if df is not None and not df.empty:
            with conn:
                # ---appending each function data to the tables---
                df = df.applymap(str)
                df.to_sql(name=table, con=conn, if_exists="append", index=False)
    except Exception as e:
        print('Problem while writing to database!', e)

