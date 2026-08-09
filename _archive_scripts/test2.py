import sqlite3
import pandas as pd
conn = sqlite3.connect('capstone.db')

campaign_id = "CMP_LIVE_DECARBONIZATION_25_26"

recent_views = pd.read_sql(f"SELECT * FROM ga4_events WHERE page_viewed = '/insights/industry-report-4' AND timestamp >= date('now', '-90 days') AND utm_campaign = '{campaign_id}'", conn)
print('Views for this campaign in last 90 days:', len(recent_views))

all_camp_views = pd.read_sql(f"SELECT utm_campaign, COUNT(*) FROM ga4_events WHERE page_viewed = '/insights/industry-report-4' GROUP BY utm_campaign", conn)
print('\nViews by campaign:')
print(all_camp_views)
