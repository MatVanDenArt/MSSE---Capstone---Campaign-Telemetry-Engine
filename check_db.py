import sqlite3
try:
    conn = sqlite3.connect("app/data/capstone.db")
    cursor = conn.cursor()
    cursor.execute("SELECT count(*) FROM action_triggers")
    print(f"Action triggers count: {cursor.fetchone()[0]}")
    conn.close()
except Exception as e:
    print(f"Error: {e}")
