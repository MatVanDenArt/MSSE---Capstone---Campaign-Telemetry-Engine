import sqlite3
import pandas as pd
conn = sqlite3.connect('capstone.db')
df = pd.read_sql_query("SELECT date(timestamp) as d, count(*) as c FROM ga4_events WHERE utm_campaign='CMP_LIVE_DECARBONIZATION_25_26' GROUP BY d ORDER BY c DESC LIMIT 10", conn)
print(df)
