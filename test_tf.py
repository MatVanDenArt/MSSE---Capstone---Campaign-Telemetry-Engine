import sqlite3
import pandas as pd
conn = sqlite3.connect('capstone.db')

campaign_id = 'CMP_LIVE_DECARBONIZATION_25_26'
tf_condition = " >= date('now', '-30 days')"

query = f"""
SELECT 
    'Web' as type,
    page_viewed as asset_name,
    MIN(timestamp) as release_date,
    COUNT(*) as engagement,
    'ga4' as source
FROM ga4_events 
WHERE utm_campaign = '{campaign_id}' 
  AND timestamp {tf_condition}
GROUP BY page_viewed
"""
df = pd.read_sql(query, conn)
print('30 DAYS:')
print(df[df['asset_name'] == '/insights/industry-report-4'])

tf_condition_7 = " >= date('now', '-7 days')"
query_7 = f"""
SELECT 
    'Web' as type,
    page_viewed as asset_name,
    MIN(timestamp) as release_date,
    COUNT(*) as engagement,
    'ga4' as source
FROM ga4_events 
WHERE utm_campaign = '{campaign_id}' 
  AND timestamp {tf_condition_7}
GROUP BY page_viewed
"""
df_7 = pd.read_sql(query_7, conn)
print('\n7 DAYS:')
print(df_7[df_7['asset_name'] == '/insights/industry-report-4'])
