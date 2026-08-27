import sqlite3
import traceback
from app.services.analytics import get_kpi_benchmarks

try:
    get_kpi_benchmarks('CMP_LIVE_DECARBONIZATION_25_26', 0)
except Exception as e:
    pass

conn = sqlite3.connect('capstone.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

def run(q):
    try:
        cursor.execute(q)
    except Exception as e:
        print(e)

print('Q1')
run("SELECT SUM(spend_consumed) as spend FROM linkedin_events WHERE 1=1 AND timestamp < datetime('2026-06-30', '-0 days')")
print('Q2')
run("SELECT COUNT(*) as conv_count FROM ga4_events WHERE user_id IS NOT NULL AND timestamp < datetime('2026-06-30', '-0 days')")
print('Q3')
run("SELECT COUNT(DISTINCT account_id) as acct_count FROM crm_users WHERE user_id IN (SELECT user_id FROM ga4_events WHERE user_id IS NOT NULL AND timestamp < datetime('2026-06-30', '-0 days'))")
print('Q4')
run("SELECT date(timestamp) as day, COUNT(*) as c FROM ga4_events WHERE utm_campaign = 'CMP_LIVE_DECARBONIZATION_25_26' AND user_id IS NOT NULL GROUP BY day ORDER BY day")
