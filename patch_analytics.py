import re

def patch_analytics():
    with open('app/services/analytics.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # We want to insert the sparkline logic right before a['asset_name'] = a['formatted_name']
    sparkline_logic = """
            # --- Added Sparkline & Health Logic ---
            raw_asset = a['asset_name']
            
            # Fetch sparkline (last 30 days) and prior 30 days
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
                
            sparkline = [0] * 30
            total_recent = sum(r["c"] for r in recent_rows)
            for r in recent_rows:
                sparkline.append(r["c"])
            a['sparkline'] = sparkline[-30:]
            
            if total_recent == 0 and prior_count == 0:
                health = "Saturated"
                badge = "bg-slate-800 text-slate-400 border-slate-700"
                rec = "AI Recommendation: Audience fatigue detected. Repurpose into a webinar or wait 30 days before re-promoting."
                color = "#334155" # slate-700
            elif prior_count == 0 or total_recent > prior_count * 0.8:
                health = "Healthy"
                badge = "bg-emerald-900/30 text-emerald-400 border-emerald-800/30"
                rec = "AI Recommendation: High intent signal. Consider promoting via LinkedIn targeted ads to similar accounts."
                color = "#10b981" # emerald-500
            elif total_recent < prior_count * 0.3:
                health = "Action Required"
                badge = "bg-rose-900/30 text-rose-400 border-rose-800/30"
                rec = "AI Recommendation: Engagement dropping rapidly. Include in the upcoming newsletter to reactivate intent."
                color = "#f43f5e" # rose-500
            else:
                health = "Saturated"
                badge = "bg-amber-900/30 text-amber-400 border-amber-800/30"
                rec = "AI Recommendation: Audience fatigue detected. Repurpose into a webinar or wait 30 days before re-promoting."
                color = "#f59e0b" # amber-500
                
            a['health'] = health
            a['badge_class'] = badge
            a['ai_recommendation'] = rec
            a['sparkline_color'] = color
            # ----------------------------------------
            
            a['asset_name'] = a['formatted_name']"""
    
    content = content.replace("            a['asset_name'] = a['formatted_name']", sparkline_logic)
    
    with open('app/services/analytics.py', 'w', encoding='utf-8') as f:
        f.write(content)
        
patch_analytics()
