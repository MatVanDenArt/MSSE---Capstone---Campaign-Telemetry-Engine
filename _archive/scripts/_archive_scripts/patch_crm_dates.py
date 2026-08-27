import re

def patch_simulate_journeys_crm_opps():
    with open('simulate_journeys.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Add user_campaign_map initialization
    if "user_campaign_map = {}" not in content:
        old_init = "    print(f\"Simulating known journeys for {len(crm_users)} CRM users...\")"
        new_init = "    user_campaign_map = {}\n    print(f\"Simulating known journeys for {len(crm_users)} CRM users...\")"
        content = content.replace(old_init, new_init)

    # 2. Add assignment inside the loop
    if "user_campaign_map[uid] = user_campaign" not in content:
        old_loop_assign = "        user_campaign = random.choice(WOOD_CAMPAIGNS)\n        captured_identity = False"
        new_loop_assign = "        user_campaign = random.choice(WOOD_CAMPAIGNS)\n        user_campaign_map[uid] = user_campaign\n        captured_identity = False"
        content = content.replace(old_loop_assign, new_loop_assign)
        
    # 3. Modify crm_opps timestamp right before dataframes dict
    old_etl = "    print(\"Executing Pandas ETL (Identity Resolution Data Flow)...\")\n    dataframes = {"
    new_etl = """    print("Executing Pandas ETL (Identity Resolution Data Flow)...")
    
    # Realign CRM Opps dates with the actual campaign bursts assigned to each user
    if not crm_opps.empty:
        for idx, row in crm_opps.iterrows():
            uid = row['user_id']
            if uid in user_campaign_map:
                campaign = user_campaign_map[uid]
                # Get the burst dates for this campaign
                bursts = list(TRANSIENT_BURST_MAP[campaign].values())
                if bursts:
                    # Pick a random burst
                    base_burst = random.choice(bursts)
                    # Opps typically close 10 to 45 days after a major burst engagement
                    opp_date = base_burst + timedelta(days=random.randint(10, 45))
                    crm_opps.at[idx, 'timestamp'] = min(opp_date, END_DATE).strftime('%Y-%m-%d %H:%M:%S')

    dataframes = {"""
    
    if "Realign CRM Opps dates" not in content:
        content = content.replace(old_etl, new_etl)

    with open('simulate_journeys.py', 'w', encoding='utf-8') as f:
        f.write(content)
        
    print("Patched simulate_journeys.py to fix crm_opps dates")

patch_simulate_journeys_crm_opps()
