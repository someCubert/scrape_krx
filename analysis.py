import sqlite3
import os
import pandas as pd 
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta

db_path = 'foreign_ownership.db'
conn = sqlite3.connect(db_path)

def calculate_date(date_str, days):
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    
    new_date_obj = date_obj + timedelta(days=days)
    new_date_str = new_date_obj.strftime('%Y-%m-%d')
    
    return new_date_str

# date_str = '2025-01-11'
# days = 20
# new_date_str = calculate_date(date_str, days)

def policy_change_analysis(conn, date_str, before_days, after_days):
    before = calculate_date(date_str, before_days)
    after = calculate_date(date_str, after_days)

    query = f"SELECT * FROM foreign_ownership WHERE date <= '{after}' AND date >= '{before}'"
    df = pd.read_sql_query(query, conn)
    print(df)

policy_change_analysis(conn, '2024-01-11', -10, 10)

conn.close()