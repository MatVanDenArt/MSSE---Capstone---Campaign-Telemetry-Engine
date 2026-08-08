def add_scoped():
    with open('app/services/analytics.py', 'r', encoding='utf-8') as f:
        content = f.read()

    new_func = """def get_scoped_audience_data(campaign_id: str) -> dict:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Get users interacting with the campaign
        query = '''
        SELECT 
            c.user_id,
            c.first_name, 
            c.last_name, 
            c.company_name, 
            c.seniority, 
            COUNT(g.session_id) as interactions
        FROM ga4_events g
        JOIN crm_users c ON g.user_id = c.user_id
        WHERE g.utm_campaign = ?
        GROUP BY c.user_id, c.first_name, c.last_name, c.company_name, c.seniority
        ORDER BY interactions DESC
        LIMIT 50
        '''
        cursor.execute(query, (campaign_id,))
        rows = cursor.fetchall()
        
        user_ids = [str(r["user_id"]) for r in rows]
        assets_map = {}
        
        if user_ids:
            placeholders = ",".join("?" for _ in user_ids)
            ga4_query = f'''
            SELECT user_id, page_viewed as asset, COUNT(*) as freq
            FROM ga4_events
            WHERE utm_campaign = ? AND user_id IN ({placeholders}) AND page_viewed IS NOT NULL
            GROUP BY user_id, page_viewed
            '''
            params = [campaign_id] + user_ids
            cursor.execute(ga4_query, params)
            for row in cursor.fetchall():
                uid = str(int(row["user_id"]))
                if uid not in assets_map:
                    assets_map[uid] = {}
                asset_name = row["asset"].replace('/', ' ').replace('-', ' ').title().strip()
                if not asset_name: asset_name = "Homepage"
                asset_name += " (Web)"
                assets_map[uid][asset_name] = assets_map[uid].get(asset_name, 0) + row["freq"]

        users = []
        for row in rows:
            user_id = str(row["user_id"])
            full_name = f"{row['first_name']} {row['last_name']}"
            interactions = int(row["interactions"])
            seniority = row["seniority"]
            company = row["company_name"]
            
            user_assets_dict = assets_map.get(user_id, {})
            sorted_assets = sorted(user_assets_dict.items(), key=lambda item: item[1], reverse=True)
            
            structured_assets = []
            for k, v in sorted_assets:
                a_type = "Email" if " (Email)" in k else "Web"
                clean_name = k.replace(" (Web)", "").replace(" (Email)", "")
                structured_assets.append({
                    "name": clean_name,
                    "type": a_type,
                    "count": v
                })
                
            users.append({
                "id": user_id,
                "name": full_name,
                "company": company,
                "seniority": seniority,
                "interactions": interactions,
                "assets": structured_assets
            })
            
        conn.close()
        return {"users": users}
    except Exception as e:
        print("Error in scoped audience:", e)
        return {"users": []}

"""

    content = content.replace('def get_audience_network_data', new_func + 'def get_audience_network_data')

    with open('app/services/analytics.py', 'w', encoding='utf-8') as f:
        f.write(content)

add_scoped()
