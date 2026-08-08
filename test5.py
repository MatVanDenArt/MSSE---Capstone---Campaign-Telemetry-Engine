import sqlite3
import pandas as pd
conn = sqlite3.connect('capstone.db')

campaign_id = 'CMP_LIVE_DECARBONIZATION_25_26'

query = f"""
SELECT 
    page_viewed as asset_name,
    MIN(timestamp) as release_date,
    COUNT(*) as engagement
FROM ga4_events 
WHERE utm_campaign = '{campaign_id}' 
GROUP BY page_viewed
"""
df = pd.read_sql(query, conn)
print('ALL TIME:')
print(df[df['asset_name'].str.contains('expert-panel-3')])
print(df[df['asset_name'].str.contains('digital-transformation-1')])
