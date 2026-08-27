import re

def patch_lifecycles():
    with open('simulate_journeys.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # We need to replace the burst date generation loop:
    # # Generate Burst Dates (Every ~60 days) for each campaign
    # BURST_DATES = {}
    # for campaign in WOOD_CAMPAIGNS:
    #     BURST_DATES[campaign] = []
    #     current_burst = START_DATE + timedelta(days=random.randint(0, 14))
    #     while current_burst < END_DATE:
    #         BURST_DATES[campaign].append(current_burst)
    #         current_burst += timedelta(days=60 + random.randint(-10, 10))

    new_loop = """# Generate Burst Dates for each campaign based on specific lifecycles
BURST_DATES = {}
for campaign in WOOD_CAMPAIGNS:
    BURST_DATES[campaign] = []
    
    if campaign == "CMP_LIVE_DECARBONIZATION_25_26":
        camp_start = END_DATE - timedelta(days=90)
        camp_end = END_DATE
    elif campaign == "CMP_LIVE_HYDROGEN_INFRASTRUCTURE":
        camp_start = END_DATE - timedelta(days=180)
        camp_end = END_DATE
    elif campaign == "CMP_LIVE_DIGITAL_TWIN":
        camp_start = END_DATE - timedelta(days=120)
        camp_end = END_DATE
    elif campaign == "CMP_PAST_SUSTAINABLE_ENGINEERING":
        camp_start = START_DATE
        camp_end = END_DATE - timedelta(days=180)
    elif campaign == "CMP_PAST_ASSET_OPTIMIZATION":
        camp_start = START_DATE + timedelta(days=145)
        camp_end = END_DATE - timedelta(days=60)
    else:
        camp_start = START_DATE
        camp_end = END_DATE

    current_burst = camp_start + timedelta(days=random.randint(0, 7))
    while current_burst < camp_end:
        BURST_DATES[campaign].append(current_burst)
        current_burst += timedelta(days=45 + random.randint(-10, 15))
        
    # Ensure there is always at least one burst for logic safety
    if not BURST_DATES[campaign]:
        BURST_DATES[campaign].append(camp_start + timedelta(days=1))
"""

    pattern = r"# Generate Burst Dates \(Every ~60 days\) for each campaign[\s\S]*?current_burst \+= timedelta\(days=60 \+ random\.randint\(-10, 10\)\)"
    
    new_content = re.sub(pattern, new_loop, content)
    
    # We also need to update generate_decay_date to respect the individual campaign's camp_end
    # Actually, we don't need to change generate_decay_date because it caps at END_DATE, and the bursts will naturally dictate the timeline.
    # However, let's make generate_decay_date respect a passed-in limit if possible, or just leave it capping at END_DATE which is fine since bursts stop before camp_end anyway.
    
    with open('simulate_journeys.py', 'w', encoding='utf-8') as f:
        f.write(new_content)

    print("Patched lifecycles successfully.")

patch_lifecycles()
