import sqlite3
import pandas as pd
conn = sqlite3.connect('capstone.db')

campaign_id = 'CMP_LIVE_DECARBONIZATION_25_26'

query = f"""
SELECT MIN(timestamp) as release_date
FROM ga4_events 
WHERE utm_campaign = '{campaign_id}' 
"""
df = pd.read_sql(query, conn)
print('Earliest event for Decarbonization:')
print(df)

query2 = f"""
SELECT MIN(timestamp) as release_date
FROM ga4_events 
WHERE utm_campaign = 'CMP_PAST_SUSTAINABLE_ENGINEERING' 
"""
df2 = pd.read_sql(query2, conn)
print('Earliest event for Sustainable Engineering:')
print(df2)
