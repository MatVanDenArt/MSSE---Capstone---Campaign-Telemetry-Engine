import re

def patch_analytics_launch_profile():
    with open('app/services/analytics.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # The block we want to replace starts around line 476:
    old_logic = """            # Fetch sparkline (last 30 days) and prior 30 days
            if a['type'] == 'Web':
                cursor.execute(f"SELECT date(timestamp) as dt, COUNT(*) as c FROM ga4_events WHERE utm_campaign = '{campaign_id}' AND page_viewed = '{raw_asset}' AND timestamp >= date('now', '-30 days') GROUP BY dt ORDER BY dt")
                recent_rows = cursor.fetchall()
                cursor.execute(f"SELECT COUNT(*) as c FROM ga4_events WHERE utm_campaign = '{campaign_id}' AND page_viewed = '{raw_asset}' AND timestamp >= date('now', '-60 days') AND timestamp < date('now', '-30 days')")
                prior_count = (cursor.fetchone() or {"c":0})["c"] or 0
            elif a['type'] == 'LinkedIn':
                cursor.execute(f"SELECT date(timestamp) as dt, COUNT(*) as c FROM linkedin_events WHERE campaign_id = '{campaign_id}' AND ad_id = '{raw_asset}' AND timestamp >= date('now', '-30 days') GROUP BY dt ORDER BY dt")
                recent_rows = cursor.fetchall()
                cursor.execute(f"SELECT COUNT(*) as c FROM linkedin_events WHERE campaign_id = '{campaign_id}' AND ad_id = '{raw_asset}' AND timestamp >= date('now', '-60 days') AND timestamp < date('now', '-30 days')")
                prior_count = (cursor.fetchone() or {"c":0})["c"] or 0
            else: # Email
                cursor.execute(f"SELECT date(timestamp) as dt, COUNT(*) as c FROM mailchimp_events WHERE campaign_id LIKE '%{campaign_id}%' AND url_clicked = '{raw_asset}' AND timestamp >= date('now', '-30 days') GROUP BY dt ORDER BY dt")
                recent_rows = cursor.fetchall()
                cursor.execute(f"SELECT COUNT(*) as c FROM mailchimp_events WHERE campaign_id LIKE '%{campaign_id}%' AND url_clicked = '{raw_asset}' AND timestamp >= date('now', '-60 days') AND timestamp < date('now', '-30 days')")
                prior_count = (cursor.fetchone() or {"c":0})["c"] or 0
                
            import datetime
            today = datetime.date.today()
            date_counts = {r['dt']: r['c'] for r in recent_rows}
            sparkline = []
            for i in range(29, -1, -1):
                d = (today - datetime.timedelta(days=i)).isoformat()
                sparkline.append(date_counts.get(d, 0))"""
                
    new_logic = """            import datetime
            # Instead of a trailing 30-day window from today, use a 'launch profile' window 
            # (30 days from the asset's release date) to ensure historical assets show a valid graph!
            rel_date_str = a['release_date'].split(' ')[0]
            rel_date = datetime.date.fromisoformat(rel_date_str)
            
            if a['type'] == 'Web':
                cursor.execute(f"SELECT date(timestamp) as dt, COUNT(*) as c FROM ga4_events WHERE utm_campaign = '{campaign_id}' AND page_viewed = '{raw_asset}' AND timestamp >= '{rel_date_str}' AND timestamp < date('{rel_date_str}', '+30 days') GROUP BY dt ORDER BY dt")
                recent_rows = cursor.fetchall()
                # For health checks, we still want to compare the trailing 30 vs prior 30 from TODAY
                cursor.execute(f"SELECT COUNT(*) as c FROM ga4_events WHERE utm_campaign = '{campaign_id}' AND page_viewed = '{raw_asset}' AND timestamp >= date('now', '-30 days')")
                total_recent = (cursor.fetchone() or {"c":0})["c"] or 0
                cursor.execute(f"SELECT COUNT(*) as c FROM ga4_events WHERE utm_campaign = '{campaign_id}' AND page_viewed = '{raw_asset}' AND timestamp >= date('now', '-60 days') AND timestamp < date('now', '-30 days')")
                prior_count = (cursor.fetchone() or {"c":0})["c"] or 0
            elif a['type'] == 'LinkedIn':
                cursor.execute(f"SELECT date(timestamp) as dt, COUNT(*) as c FROM linkedin_events WHERE campaign_id = '{campaign_id}' AND ad_id = '{raw_asset}' AND timestamp >= '{rel_date_str}' AND timestamp < date('{rel_date_str}', '+30 days') GROUP BY dt ORDER BY dt")
                recent_rows = cursor.fetchall()
                cursor.execute(f"SELECT COUNT(*) as c FROM linkedin_events WHERE campaign_id = '{campaign_id}' AND ad_id = '{raw_asset}' AND timestamp >= date('now', '-30 days')")
                total_recent = (cursor.fetchone() or {"c":0})["c"] or 0
                cursor.execute(f"SELECT COUNT(*) as c FROM linkedin_events WHERE campaign_id = '{campaign_id}' AND ad_id = '{raw_asset}' AND timestamp >= date('now', '-60 days') AND timestamp < date('now', '-30 days')")
                prior_count = (cursor.fetchone() or {"c":0})["c"] or 0
            else: # Email
                cursor.execute(f"SELECT date(timestamp) as dt, COUNT(*) as c FROM mailchimp_events WHERE campaign_id LIKE '%{campaign_id}%' AND url_clicked = '{raw_asset}' AND timestamp >= '{rel_date_str}' AND timestamp < date('{rel_date_str}', '+30 days') GROUP BY dt ORDER BY dt")
                recent_rows = cursor.fetchall()
                cursor.execute(f"SELECT COUNT(*) as c FROM mailchimp_events WHERE campaign_id LIKE '%{campaign_id}%' AND url_clicked = '{raw_asset}' AND timestamp >= date('now', '-30 days')")
                total_recent = (cursor.fetchone() or {"c":0})["c"] or 0
                cursor.execute(f"SELECT COUNT(*) as c FROM mailchimp_events WHERE campaign_id LIKE '%{campaign_id}%' AND url_clicked = '{raw_asset}' AND timestamp >= date('now', '-60 days') AND timestamp < date('now', '-30 days')")
                prior_count = (cursor.fetchone() or {"c":0})["c"] or 0
                
            date_counts = {r['dt']: r['c'] for r in recent_rows}
            sparkline = []
            for i in range(30):
                d = (rel_date + datetime.timedelta(days=i)).isoformat()
                sparkline.append(date_counts.get(d, 0))"""
                
    if old_logic in content:
        content = content.replace(old_logic, new_logic)
        
        # We also need to remove `total_recent = sum(sparkline)` because we calculated it manually above
        # The sum(sparkline) would be the sum over the launch 30 days, not the recent 30 days!
        content = content.replace("total_recent = sum(sparkline)", "# total_recent calculated manually above")
        
        with open('app/services/analytics.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print("Successfully patched launch profile sparklines")
    else:
        print("COULD NOT FIND old_logic")

patch_analytics_launch_profile()
