import sqlite3

def test_chart():
    conn = sqlite3.connect('capstone.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    timeframe = 30
    campaign_id = 'CMP_LIVE_GASTECH_2026'
    
    tf_condition = f"AND timestamp >= datetime('now', '-{timeframe} days')" if timeframe > 0 else ""
    date_format = "'%Y-%m-%d'" if timeframe > 0 and timeframe <= 90 else "'%Y-%m'"
    
    query = f"SELECT strftime({date_format}, timestamp) as period, COUNT(*) as count FROM ga4_events WHERE utm_campaign = '{campaign_id}' {tf_condition} GROUP BY period ORDER BY period"
    
    print(query)
    
    cursor.execute(query)
    rows = cursor.fetchall()
    print([dict(r) for r in rows])
    
if __name__ == "__main__":
    test_chart()
