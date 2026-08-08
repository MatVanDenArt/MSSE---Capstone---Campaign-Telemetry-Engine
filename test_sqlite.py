import sqlite3
conn = sqlite3.connect('capstone.db')
cursor = conn.cursor()
cursor.execute("SELECT strftime('%Y-%W', timestamp) as w FROM ga4_events LIMIT 5")
print(cursor.fetchall())
