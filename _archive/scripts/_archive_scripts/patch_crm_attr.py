import re

def patch_simulate_journeys_add_campaign():
    with open('simulate_journeys.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # The block we want to replace starts around line 326:
    old_logic = """    # Realign CRM Opps dates with the actual campaign bursts assigned to each user
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
                    crm_opps.at[idx, 'timestamp'] = min(opp_date, END_DATE).strftime('%Y-%m-%d %H:%M:%S')"""
                    
    new_logic = """    # Realign CRM Opps dates with the actual campaign bursts assigned to each user
    if not crm_opps.empty:
        # Add the utm_campaign column to allow strict attribution filtering in analytics.py
        crm_opps['utm_campaign'] = None
        for idx, row in crm_opps.iterrows():
            uid = row['user_id']
            if uid in user_campaign_map:
                campaign = user_campaign_map[uid]
                crm_opps.at[idx, 'utm_campaign'] = campaign
                
                # Get the burst dates for this campaign
                bursts = list(TRANSIENT_BURST_MAP[campaign].values())
                if bursts:
                    # Pick a random burst
                    base_burst = random.choice(bursts)
                    # Opps typically close 10 to 45 days after a major burst engagement
                    opp_date = base_burst + timedelta(days=random.randint(10, 45))
                    crm_opps.at[idx, 'timestamp'] = min(opp_date, END_DATE).strftime('%Y-%m-%d %H:%M:%S')"""
                    
    if old_logic in content:
        content = content.replace(old_logic, new_logic)
        with open('simulate_journeys.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print("Successfully patched simulate_journeys.py to add utm_campaign to crm_opps")
    else:
        print("COULD NOT FIND old_logic")

patch_simulate_journeys_add_campaign()
