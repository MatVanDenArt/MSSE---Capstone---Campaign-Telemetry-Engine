import sqlite3
import pandas as pd
conn = sqlite3.connect('capstone.db')
print("Tables:", conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall())
df = pd.read_sql("SELECT * FROM crm_opps", conn)
print(df.head())
print("Min Date:", df['created_date'].min())
print("Max Date:", df['created_date'].max())
conn.close()
