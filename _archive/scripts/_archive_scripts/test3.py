import sqlite3
import pandas as pd
conn = sqlite3.connect('capstone.db')

campaign_id = 'CMP_LIVE_DECARBONIZATION_25_26'
tf_condition = " >= date('now', '-90 days')"

query = f"""
SELECT 
    'Web' as type,
    page_viewed as asset_name,
    MIN(timestamp) as release_date,
    COUNT(*) as engagement,
    'ga4' as source
FROM ga4_events 
WHERE utm_campaign = '{campaign_id}' 
  AND page_viewed NOT IN ('/solutions/decarbonization', '/solutions/energy-security', '/solutions/asset-performance-optimization', '/services/consulting', '/services/engineering', '/about/sustainability', '/contact-sales', '/', '/careers', '/pricing-calculator', '/landing-page/future-of-decarbonized-maintenance')
  AND timestamp {tf_condition}
GROUP BY page_viewed
"""
df = pd.read_sql(query, conn)
print(df[df['asset_name'] == '/insights/industry-report-4'])

li_query = f"""
SELECT 
    'LinkedIn' as type,
    ad_id as asset_name,
    MIN(timestamp) as release_date,
    COUNT(*) as engagement,
    'linkedin' as source
FROM linkedin_events
WHERE campaign_id = '{campaign_id}' AND timestamp {tf_condition}
GROUP BY ad_id
"""
li_df = pd.read_sql(li_query, conn)
print(li_df[li_df['asset_name'] == 'LI_AD_REPORT_PROMO_4'])

