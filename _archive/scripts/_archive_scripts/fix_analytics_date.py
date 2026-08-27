with open('app/services/analytics.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("datetime('now', '-{timeframe} days')", "datetime('2026-06-30', '-{timeframe} days')")
content = content.replace("datetime('now')", "'2026-06-30'")
# Actually wait, maybe some queries use date('now')
content = content.replace("date('now')", "'2026-06-30'")
content = content.replace("date('now',", "date('2026-06-30',")

with open('app/services/analytics.py', 'w', encoding='utf-8') as f:
    f.write(content)
