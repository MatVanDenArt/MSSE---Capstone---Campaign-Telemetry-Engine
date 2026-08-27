import sqlite3
import datetime
import json
conn = sqlite3.connect('capstone.db')
cursor = conn.cursor()

campaign_id = 'CMP_LIVE_DECARBONIZATION_25_26'
raw_asset = 'https://woodplc.com?utm_campaign=CMP_LIVE_DECARBONIZATION_25_26_BURST_0_EMAIL_2'

cursor.execute(f"SELECT date(timestamp) as dt, COUNT(*) as c FROM mailchimp_events WHERE campaign_id = '{campaign_id}' AND url_clicked = '{raw_asset}' AND timestamp >= date('now', '-30 days') GROUP BY dt ORDER BY dt")
recent_rows = [{'dt': r[0], 'c': r[1]} for r in cursor.fetchall()]
print(f'Recent rows: {recent_rows}')

today = datetime.date.today()
date_counts = {r['dt']: r['c'] for r in recent_rows}
sparkline = []
for i in range(29, -1, -1):
    d = (today - datetime.timedelta(days=i)).isoformat()
    sparkline.append(date_counts.get(d, 0))
    
print(f'Sparkline: {sparkline}')
print(f'Sum: {sum(sparkline)}')
