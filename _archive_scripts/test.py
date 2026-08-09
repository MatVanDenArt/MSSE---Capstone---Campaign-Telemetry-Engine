import sqlite3
import pandas as pd
conn = sqlite3.connect('capstone.db')

clicks = pd.read_sql("SELECT * FROM linkedin_events WHERE ad_id = 'LI_AD_REPORT_PROMO_4'", conn)
print('Total Clicks for LI_AD_REPORT_PROMO_4:', len(clicks))

ga4_views = pd.read_sql("SELECT * FROM ga4_events WHERE page_viewed = '/insights/industry-report-4'", conn)
print('Total Views for Industry Report 4:', len(ga4_views))

print('\nTotal Rows in ga4_events:', pd.read_sql('SELECT COUNT(*) FROM ga4_events', conn).iloc[0,0])
print('Total Rows in linkedin_events:', pd.read_sql('SELECT COUNT(*) FROM linkedin_events', conn).iloc[0,0])
print('Total Rows in mailchimp_events:', pd.read_sql('SELECT COUNT(*) FROM mailchimp_events', conn).iloc[0,0])
