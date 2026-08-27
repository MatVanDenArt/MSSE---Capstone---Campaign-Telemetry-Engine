missing_functions = """
def get_channel_roi_data(campaign_id: str) -> dict:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # LinkedIn
        cursor.execute('''
            SELECT COUNT(DISTINCT c.company_name), SUM(e.spend_consumed)
            FROM linkedin_events e JOIN crm_users c ON e.user_id = c.user_id 
            WHERE e.campaign_id = ?
        ''', (campaign_id,))
        li_row = cursor.fetchone()
        li_accounts = li_row[0] or 0
        li_spend = li_row[1] or 0
        
        cursor.execute('''
            SELECT DISTINCT c.company_name
            FROM linkedin_events e JOIN crm_users c ON e.user_id = c.user_id 
            WHERE e.campaign_id = ? LIMIT 10
        ''', (campaign_id,))
        li_list = [r[0] for r in cursor.fetchall()]

        # Email
        cursor.execute('''
            SELECT COUNT(DISTINCT c.company_name), COUNT(e.event_id)
            FROM mailchimp_events e JOIN crm_users c ON e.user_id = c.user_id 
            WHERE e.campaign_id = ?
        ''', (campaign_id,))
        em_row = cursor.fetchone()
        em_accounts = em_row[0] or 0
        em_clicks = em_row[1] or 0
        
        cursor.execute('''
            SELECT DISTINCT c.company_name
            FROM mailchimp_events e JOIN crm_users c ON e.user_id = c.user_id 
            WHERE e.campaign_id = ? LIMIT 10
        ''', (campaign_id,))
        em_list = [r[0] for r in cursor.fetchall()]

        # Web
        cursor.execute('''
            SELECT COUNT(DISTINCT c.company_name), COUNT(e.session_id)
            FROM ga4_events e JOIN crm_users c ON e.user_id = c.user_id 
            WHERE e.utm_campaign = ?
        ''', (campaign_id,))
        web_row = cursor.fetchone()
        web_accounts = web_row[0] or 0
        web_views = web_row[1] or 0
        
        cursor.execute('''
            SELECT DISTINCT c.company_name
            FROM ga4_events e JOIN crm_users c ON e.user_id = c.user_id 
            WHERE e.utm_campaign = ? LIMIT 10
        ''', (campaign_id,))
        web_list = [r[0] for r in cursor.fetchall()]
        
        conn.close()
        
        return {
            'linkedin': {'accounts_reached': li_accounts, 'total_spend': li_spend, 'accounts': li_list},
            'email': {'accounts_engaged': em_accounts, 'total_clicks': em_clicks, 'accounts': em_list},
            'web': {'accounts_identified': web_accounts, 'total_pageviews': web_views, 'accounts': web_list}
        }
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return {'error': str(e)}

def get_ui_lab_funnel_data(campaign_id: str) -> dict:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM ga4_events WHERE utm_campaign = ?", (campaign_id,))
        visitors = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT COUNT(*) FROM ga4_events WHERE utm_campaign = ? AND bounce_flag = 0", (campaign_id,))
        engaged = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT COUNT(DISTINCT user_id) FROM ga4_events WHERE utm_campaign = ? AND user_id IS NOT NULL", (campaign_id,))
        known = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT COUNT(DISTINCT user_id) FROM crm_opps WHERE user_id IN (SELECT user_id FROM ga4_events WHERE utm_campaign = ?)", (campaign_id,))
        pipeline = cursor.fetchone()[0] or 0
        
        # Activated is roughly midway between known and pipeline
        activated = int((known + pipeline) / 2) if known > 0 else 0
        
        conn.close()
        return {'visitors': visitors, 'engaged': engaged, 'known': known, 'activated': activated, 'pipeline': pipeline}
    except Exception as e:
        return {'error': str(e)}

def get_ui_lab_heatmap_data(campaign_id: str) -> dict:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Aggregate GA4 events by day
        cursor.execute('''
            SELECT date(timestamp) as day, COUNT(*) as interactions
            FROM ga4_events
            WHERE utm_campaign = ?
            GROUP BY day
        ''', (campaign_id,))
        
        days_data = {}
        for row in cursor.fetchall():
            days_data[row['day']] = row['interactions']
            
        conn.close()
        return {'heatmap': days_data}
    except Exception as e:
        return {'error': str(e)}

def get_high_intent_alerts(campaign_id: str) -> list:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get recent events from ga4 tied to CRM users
        query = '''
        SELECT c.company_name, c.seniority, g.timestamp, g.page_viewed
        FROM ga4_events g
        JOIN crm_users c ON g.user_id = c.user_id
        WHERE g.utm_campaign = ?
        ORDER BY g.timestamp DESC
        LIMIT 5
        '''
        cursor.execute(query, (campaign_id,))
        alerts = []
        for row in cursor.fetchall():
            alerts.append({
                'company': row['company_name'],
                'seniority': row['seniority'],
                'time': row['timestamp'].split(' ')[1][:5], # just HH:MM
                'action': 'downloaded ' + row['page_viewed'].split('/')[-1] if 'pdf' in row['page_viewed'] else 'viewed ' + row['page_viewed'],
                'raw_timestamp': row['timestamp']
            })
        conn.close()
        return alerts
    except Exception as e:
        return []
"""

with open("app/services/analytics.py", "a") as f:
    f.write("\n\n" + missing_functions + "\n")
