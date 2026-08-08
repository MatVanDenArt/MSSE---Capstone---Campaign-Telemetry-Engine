import re

def patch_analytics_sparkline():
    with open('app/services/analytics.py', 'r', encoding='utf-8') as f:
        content = f.read()
        
    old_logic = """            sparkline = [0] * 30
            total_recent = sum(r["c"] for r in recent_rows)
            for r in recent_rows:
                sparkline.append(r["c"])
            a['sparkline'] = sparkline[-30:]"""
            
    new_logic = """            import datetime
            today = datetime.date.today()
            date_counts = {r['dt']: r['c'] for r in recent_rows}
            sparkline = []
            for i in range(29, -1, -1):
                d = (today - datetime.timedelta(days=i)).isoformat()
                sparkline.append(date_counts.get(d, 0))
            a['sparkline'] = sparkline
            total_recent = sum(sparkline)"""
            
    content = content.replace(old_logic, new_logic)

    with open('app/services/analytics.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patched analytics.py sparkline logic")

patch_analytics_sparkline()
