def update_analytics():
    with open('app/services/analytics.py', 'r', encoding='utf-8') as f:
        content = f.read()

    start_marker = "def get_high_intent_alerts(campaign_id: str) -> list:"
    end_marker = "except Exception as e:\n        return []"
    start_idx = content.find(start_marker)
    end_idx = content.find(end_marker, start_idx) + len(end_marker)
    
    if start_idx == -1 or end_idx < start_idx:
        print("Markers not found!")
        return

    new_func = """def get_prioritized_sales_targets(campaign_id: str) -> list:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Get all users who interacted with this campaign on GA4
        query = '''
        SELECT 
            c.user_id,
            c.first_name, 
            c.last_name, 
            c.company_name, 
            c.seniority, 
            COUNT(g.session_id) as campaign_interactions,
            MAX(g.timestamp) as last_active
        FROM ga4_events g
        JOIN crm_users c ON g.user_id = c.user_id
        WHERE g.utm_campaign = ?
        GROUP BY c.user_id, c.first_name, c.last_name, c.company_name, c.seniority
        ORDER BY campaign_interactions DESC, last_active DESC
        LIMIT 20
        '''
        cursor.execute(query, (campaign_id,))
        users = cursor.fetchall()
        
        # 2. Get Account Momentum (Total unique users per company engaged in this campaign)
        acct_query = '''
        SELECT c.company_name, COUNT(DISTINCT c.user_id) as active_personas
        FROM ga4_events g
        JOIN crm_users c ON g.user_id = c.user_id
        WHERE g.utm_campaign = ?
        GROUP BY c.company_name
        '''
        cursor.execute(acct_query, (campaign_id,))
        acct_rows = cursor.fetchall()
        account_momentum = {row['company_name']: row['active_personas'] for row in acct_rows}
        
        targets = []
        for user in users:
            interactions = user['campaign_interactions']
            company = user['company_name']
            personas = account_momentum.get(company, 1)
            
            if interactions >= 5:
                status = "SQL"
                color = "text-emerald-400"
                bg = "bg-emerald-400/10"
                border = "border-emerald-500/20"
                if 'VP' in user['seniority'] or 'Director' in user['seniority'] or 'C-Level' in user['seniority']:
                    action = f"Executive outreach. Reference the {personas} active personas from their account."
                else:
                    action = "Send 'Technical Deep Dive' sequence. High individual engagement."
            elif interactions >= 2:
                status = "MQL"
                color = "text-brand-400"
                bg = "bg-brand-400/10"
                border = "border-brand-500/20"
                if personas >= 3:
                    action = "Account is heating up. Multi-thread outreach to this contact."
                else:
                    action = "Nurture with relevant case studies to push to SQL."
            else:
                status = "Cold Prospect"
                color = "text-slate-400"
                bg = "bg-dark-700"
                border = "border-dark-600"
                action = "Enroll in standard top-of-funnel nurture."
                
            targets.append({
                'name': f"{user['first_name']} {user['last_name']}",
                'company': company,
                'seniority': user['seniority'],
                'interactions': interactions,
                'last_active': user['last_active'].split(' ')[0],
                'status': status,
                'personas': personas,
                'color': color,
                'bg': bg,
                'border': border,
                'action': action
            })
            
        conn.close()
        return targets[:5]
    except Exception as e:
        print("Error in targets:", e)
        return []"""

    content = content[:start_idx] + new_func + content[end_idx:]

    with open('app/services/analytics.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print('Updated analytics.py')

update_analytics()
