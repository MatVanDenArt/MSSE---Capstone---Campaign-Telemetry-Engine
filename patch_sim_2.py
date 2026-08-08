import re

def patch_simulate_journeys():
    with open('simulate_journeys.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Remove the global lists
    content = re.sub(r'TRANSIENT_REPORTS = \[.*?\] # 14 total \(1-2 per burst\)', '', content, flags=re.DOTALL)
    content = re.sub(r'TRANSIENT_WEB = \[.*?\] # 18 total \(2 per burst\)', '', content, flags=re.DOTALL)
    content = re.sub(r'WOOD_EMAILS = \[.*?\] # 16', '', content, flags=re.DOTALL)
    content = re.sub(r'WOOD_LINKEDIN = \[.*?\] # 16', '', content, flags=re.DOTALL)
    
    # 2. Modify the TRANSIENT_BURST_MAP generation
    old_burst_gen = """TRANSIENT_BURST_MAP = {}
all_transients = TRANSIENT_REPORTS + TRANSIENT_WEB + WOOD_EMAILS + WOOD_LINKEDIN
for campaign in WOOD_CAMPAIGNS:
    TRANSIENT_BURST_MAP[campaign] = {}
    for i, asset in enumerate(all_transients):
        # We assign each transient asset to one of the bursts for this campaign
        burst_idx = i % len(BURST_DATES[campaign])
        drop = BURST_DATES[campaign][burst_idx] + timedelta(days=random.randint(0, 14))
        TRANSIENT_BURST_MAP[campaign][asset] = min(drop, END_DATE)"""
        
    new_burst_gen = """TRANSIENT_BURST_MAP = {}
for campaign in WOOD_CAMPAIGNS:
    TRANSIENT_BURST_MAP[campaign] = {}
    
    for burst_idx, burst_date in enumerate(BURST_DATES[campaign]):
        
        c_prefix = campaign.split('_')[-1].lower()
        
        # 1-2 Case Studies
        num_cs = random.randint(1, 2)
        for i in range(num_cs):
            asset = f"/case-studies/{c_prefix}-b{burst_idx}-cs-{i+1}"
            drop = burst_date + timedelta(days=random.randint(0, 14))
            TRANSIENT_BURST_MAP[campaign][asset] = min(drop, END_DATE)
            
        # 2 Insights
        for i in range(2):
            asset = f"/insights/{c_prefix}-b{burst_idx}-report-{i+1}"
            drop = burst_date + timedelta(days=random.randint(0, 14))
            TRANSIENT_BURST_MAP[campaign][asset] = min(drop, END_DATE)
            
        # 2 Emails
        for i in range(2):
            asset = f"https://woodplc.com?utm_campaign={campaign}_BURST_{burst_idx}_EMAIL_{i+1}"
            drop = burst_date + timedelta(days=random.randint(0, 14))
            TRANSIENT_BURST_MAP[campaign][asset] = min(drop, END_DATE)
            EMAIL_PAGE_MAP[asset] = f"/insights/{c_prefix}-b{burst_idx}-report-1"
            
        # 2 LinkedIn Ads
        for i in range(2):
            asset = f"LI_AD_{campaign}_BURST_{burst_idx}_PROMO_{i+1}"
            drop = burst_date + timedelta(days=random.randint(0, 14))
            TRANSIENT_BURST_MAP[campaign][asset] = min(drop, END_DATE)
            AD_PAGE_MAP[asset] = f"/case-studies/{c_prefix}-b{burst_idx}-cs-1"
"""
    if old_burst_gen in content:
        content = content.replace(old_burst_gen, new_burst_gen)
    else:
        print("COULD NOT FIND old_burst_gen")

    # 3. Modify the simulation loop mapping
    
    # OLD Email block:
    #                 # Email
    #                 email = random.choice(WOOD_EMAILS)
    # NEW Email block:
    old_email = """                # Email
                email = random.choice(WOOD_EMAILS)
                email_drop = TRANSIENT_BURST_MAP[user_campaign].get(email, END_DATE)"""
    new_email = """                # Email
                campaign_emails = [k for k in TRANSIENT_BURST_MAP[user_campaign].keys() if 'EMAIL' in k]
                email = random.choice(campaign_emails) if campaign_emails else 'NO_EMAIL'
                if email == 'NO_EMAIL': continue
                email_drop = TRANSIENT_BURST_MAP[user_campaign].get(email, END_DATE)"""
    content = content.replace(old_email, new_email)
    
    # OLD LinkedIn block:
    old_linkedin = """                # LinkedIn
                ad = random.choice(WOOD_LINKEDIN)
                ad_drop = TRANSIENT_BURST_MAP[user_campaign].get(ad, END_DATE)"""
    new_linkedin = """                # LinkedIn
                campaign_ads = [k for k in TRANSIENT_BURST_MAP[user_campaign].keys() if 'LI_AD' in k]
                ad = random.choice(campaign_ads) if campaign_ads else 'NO_AD'
                if ad == 'NO_AD': continue
                ad_drop = TRANSIENT_BURST_MAP[user_campaign].get(ad, END_DATE)"""
    content = content.replace(old_linkedin, new_linkedin)
    
    # OLD Web/Report block:
    old_web = """                if channel == 'Report':
                    page = random.choice(TRANSIENT_REPORTS)
                    is_core = False
                else:
                    page = random.choice(CORE_WEB + TRANSIENT_WEB)
                    is_core = page in CORE_WEB"""
    new_web = """                if channel == 'Report':
                    campaign_reports = [k for k in TRANSIENT_BURST_MAP[user_campaign].keys() if '/case-studies/' in k]
                    page = random.choice(campaign_reports) if campaign_reports else random.choice(CORE_WEB)
                    is_core = False
                else:
                    campaign_insights = [k for k in TRANSIENT_BURST_MAP[user_campaign].keys() if '/insights/' in k or '/webinars/' in k]
                    page = random.choice(CORE_WEB + campaign_insights)
                    is_core = page in CORE_WEB"""
    content = content.replace(old_web, new_web)

    with open('simulate_journeys.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patched simulate_journeys.py")

patch_simulate_journeys()
