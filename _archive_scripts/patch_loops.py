import re

def patch_simulate_journeys_loops():
    with open('simulate_journeys.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Remove the global lists
    content = re.sub(r'TRANSIENT_REPORTS = \[.*?\] # 14 total \(1-2 per burst\)\s*', '', content, flags=re.DOTALL)
    content = re.sub(r'TRANSIENT_WEB = \[.*?\] # 18 total \(2 per burst\)\s*', '', content, flags=re.DOTALL)
    content = re.sub(r'WOOD_EMAILS = \[.*?\] # 16\s*', '', content, flags=re.DOTALL)
    content = re.sub(r'WOOD_LINKEDIN = \[.*?\] # 16\s*', '', content, flags=re.DOTALL)
    
    # 3. Modify the simulation loop mapping
    
    old_email = """                # Email
                email = random.choice(WOOD_EMAILS)
                email_drop = TRANSIENT_BURST_MAP[user_campaign].get(email, END_DATE)"""
    new_email = """                # Email
                campaign_emails = [k for k in TRANSIENT_BURST_MAP[user_campaign].keys() if 'EMAIL' in k]
                email = random.choice(campaign_emails) if campaign_emails else 'NO_EMAIL'
                if email == 'NO_EMAIL': continue
                email_drop = TRANSIENT_BURST_MAP[user_campaign].get(email, END_DATE)"""
    if old_email in content:
        content = content.replace(old_email, new_email)
    else: print("COULD NOT FIND old_email")
    
    old_linkedin = """                # LinkedIn
                ad = random.choice(WOOD_LINKEDIN)
                ad_drop = TRANSIENT_BURST_MAP[user_campaign].get(ad, END_DATE)"""
    new_linkedin = """                # LinkedIn
                campaign_ads = [k for k in TRANSIENT_BURST_MAP[user_campaign].keys() if 'LI_AD' in k]
                ad = random.choice(campaign_ads) if campaign_ads else 'NO_AD'
                if ad == 'NO_AD': continue
                ad_drop = TRANSIENT_BURST_MAP[user_campaign].get(ad, END_DATE)"""
    if old_linkedin in content:
        content = content.replace(old_linkedin, new_linkedin)
    else: print("COULD NOT FIND old_linkedin")
    
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
    if old_web in content:
        content = content.replace(old_web, new_web)
    else: print("COULD NOT FIND old_web")

    with open('simulate_journeys.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Patched simulate_journeys.py loops")

patch_simulate_journeys_loops()
