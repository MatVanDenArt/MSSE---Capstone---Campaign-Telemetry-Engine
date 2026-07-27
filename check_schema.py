import sqlite3

c = sqlite3.connect('capstone.db')
print(c.execute("PRAGMA table_info(linkedin_events)").fetchall())
