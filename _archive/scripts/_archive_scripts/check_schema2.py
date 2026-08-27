import sqlite3
conn = sqlite3.connect('capstone.db')
c = conn.cursor()
c.execute('SELECT sql FROM sqlite_master WHERE type="table" AND name="ga4_events"')
print(c.fetchone()[0])
c.execute('SELECT sql FROM sqlite_master WHERE type="table" AND name="mailchimp_events"')
print(c.fetchone()[0])
