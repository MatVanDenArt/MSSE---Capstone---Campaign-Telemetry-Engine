import sqlite3
import random
import uuid
from datetime import datetime, timedelta
import pandas as pd

DB_PATH = r"c:\Users\mpser\Downloads\Quantic\Capstone\capstone.db"

START_DATE = datetime(2025, 1, 1)
END_DATE = datetime(2026, 6, 30)

def random_date(start, end):
    return start + timedelta(seconds=random.randint(0, int((end - start).total_seconds())))

CORE_WEB = [
    "/solutions/decarbonization",
    "/solutions/asset-performance-optimization",
    "/services/consulting",
    "/services/engineering",
    "/about/sustainability",
    "/careers",
    "/contact-sales",
    "/pricing-calculator"
]

WOOD_CAMPAIGNS = [
    "CMP_LIVE_DECARBONIZATION_25_26",
    "CMP_LIVE_HYDROGEN_INFRASTRUCTURE",
    "CMP_LIVE_DIGITAL_TWIN",
    "CMP_PAST_SUSTAINABLE_ENGINEERING",
    "CMP_PAST_ASSET_OPTIMIZATION"
]

# 1. GENERATE BURST DATES
BURST_DATES = {}
for campaign in WOOD_CAMPAIGNS:
    BURST_DATES[campaign] = []
    if "PAST" in campaign:
        camp_start = START_DATE + timedelta(days=random.randint(0, 90))
        num_bursts = random.randint(4, 9)
    elif "DECARBONIZATION" in campaign:
        camp_start = END_DATE - timedelta(days=180) # Exactly 6 months
        num_bursts = 3
    else:
        camp_start = END_DATE - timedelta(days=random.randint(90, 270))
        num_bursts = random.randint(4, 9)
        
    current_burst = camp_start
    for _ in range(num_bursts):
        BURST_DATES[campaign].append(current_burst)
        if "DECARBONIZATION" in campaign:
            current_burst += timedelta(days=60)
        else:
            current_burst += timedelta(days=random.randint(30, 60))
        if current_burst > END_DATE: break

# 2. GENERATE TRANSIENT ASSETS FOR BURSTS
TRANSIENT_BURST_MAP = {}
EMAIL_PAGE_MAP = {}
AD_PAGE_MAP = {}

for campaign in WOOD_CAMPAIGNS:
    TRANSIENT_BURST_MAP[campaign] = {}
    for burst_idx, burst_date in enumerate(BURST_DATES[campaign]):
        c_prefix = campaign.split('_')[-1].lower()
        
        # Case Studies
        num_cs = random.randint(1, 2)
        for i in range(num_cs):
            asset = f"/case-studies/{c_prefix}-b{burst_idx}-cs-{i+1}"
            drop = burst_date + timedelta(days=random.randint(0, 14))
            TRANSIENT_BURST_MAP[campaign][asset] = min(drop, END_DATE)
            
        # Insights
        for i in range(2):
            asset = f"/insights/{c_prefix}-b{burst_idx}-report-{i+1}"
            drop = burst_date + timedelta(days=random.randint(0, 14))
            TRANSIENT_BURST_MAP[campaign][asset] = min(drop, END_DATE)
            
        # Emails
        for i in range(1):
            asset = f"https://woodplc.com?utm_campaign={campaign}_BURST_{burst_idx}_EMAIL_{i+1}"
            drop = burst_date + timedelta(days=random.randint(0, 14))
            TRANSIENT_BURST_MAP[campaign][asset] = min(drop, END_DATE)
            EMAIL_PAGE_MAP[asset] = f"/insights/{c_prefix}-b{burst_idx}-report-1"
            
        # LinkedIn Ads
        for i in range(random.randint(1, 2)):
            asset = f"LI_AD_{campaign}_BURST_{burst_idx}_PROMO_{i+1}"
            drop = burst_date + timedelta(days=random.randint(0, 14))
            TRANSIENT_BURST_MAP[campaign][asset] = min(drop, END_DATE)
            AD_PAGE_MAP[asset] = f"/case-studies/{c_prefix}-b{burst_idx}-cs-1"

def get_asset_timestamp(campaign, asset, is_core):
    if is_core:
        camp_start = BURST_DATES[campaign][0] if campaign in BURST_DATES and BURST_DATES[campaign] else START_DATE
        return random_date(camp_start, END_DATE).strftime('%Y-%m-%d %H:%M:%S.%f')
    else:
        drop_date = TRANSIENT_BURST_MAP[campaign].get(asset, START_DATE)
        end_val = min(drop_date + timedelta(days=45), END_DATE)
        if end_val <= drop_date: end_val = drop_date + timedelta(days=1)
        total_seconds = int((end_val - drop_date).total_seconds())
        # Power-law decay: random.random()**4 skews heavily towards 0
        skewed_seconds = int(total_seconds * (random.random() ** 4))
        return (drop_date + timedelta(seconds=skewed_seconds)).strftime('%Y-%m-%d %H:%M:%S.%f')

def run_simulation():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM ga4_events")
    cursor.execute("DELETE FROM mailchimp_events")
    cursor.execute("DELETE FROM linkedin_events")

    cursor.execute("SELECT user_id, email, company_name FROM crm_users")
    users = cursor.fetchall()
    
    user_interaction_counts = {u[0]: {'ga4': 0, 'mc': 0, 'li': 0} for u in users}

    print(f"Simulating journeys for {len(users)} users...")

    for user in users:
        uid = user[0]
        email = user[1]
        cookie_id = f"cookie_{uid}"
        
        rand = random.random()
        if rand < 0.15:
            cohort = "SQL"
            touches = random.randint(12, 25)
        elif rand < 0.50:
            cohort = "MQL"
            touches = random.randint(4, 12)
        else:
            cohort = "Cold"
            touches = random.randint(1, 3)

        user_campaign = random.choice(WOOD_CAMPAIGNS)
        seen_campaign_assets = set()
        captured_identity = False

        for _ in range(touches):
            capture_val = None
            channel = random.choices(['Web', 'Report', 'Email', 'LinkedIn'], weights=[40, 15, 30, 15])[0]

            if channel in ['Web', 'Report']:
                if channel == 'Report':
                    campaign_reports = [k for k in TRANSIENT_BURST_MAP[user_campaign].keys() if '/case-studies/' in k and k not in seen_campaign_assets]
                    page = random.choice(campaign_reports) if campaign_reports else random.choice(CORE_WEB)
                    if page not in CORE_WEB: seen_campaign_assets.add(page)
                else:
                    campaign_insights = [k for k in TRANSIENT_BURST_MAP[user_campaign].keys() if ('/insights/' in k or '/webinars/' in k) and k not in seen_campaign_assets]
                    page = random.choice(campaign_insights) if (campaign_insights and random.random() < 0.7) else random.choice(CORE_WEB)
                    if page not in CORE_WEB: seen_campaign_assets.add(page)
                
                is_core = page in CORE_WEB
                t_stamp = get_asset_timestamp(user_campaign, page, is_core)
                
                if not captured_identity and random.random() < 0.10:
                    capture_val = uid
                    captured_identity = True
                    
                cursor.execute("""
                    INSERT INTO ga4_events (session_id, cookie_id, utm_source, utm_campaign, page_viewed, bounce_flag, timestamp, user_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (str(uuid.uuid4()), cookie_id, "direct", user_campaign, page, 0, t_stamp, uid))
                user_interaction_counts[uid]['ga4'] += 1

            elif channel == 'Email':
                campaign_emails = [k for k in TRANSIENT_BURST_MAP[user_campaign].keys() if 'EMAIL' in k and k not in seen_campaign_assets]
                if not campaign_emails: continue
                asset = random.choice(campaign_emails)
                seen_campaign_assets.add(asset)
                
                t_stamp = get_asset_timestamp(user_campaign, asset, False)
                action = random.choices(["Open", "Click"], weights=[70, 30])[0]
                
                cursor.execute("""
                    INSERT INTO mailchimp_events (event_id, email, campaign_id, action, url_clicked, timestamp, user_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (str(uuid.uuid4()), email, user_campaign, action, asset, t_stamp, uid))
                user_interaction_counts[uid]['mc'] += 1
                
                if action == 'Click':
                    page = EMAIL_PAGE_MAP.get(asset, "/contact-sales")
                    cursor.execute("""
                        INSERT INTO ga4_events (session_id, cookie_id, utm_source, utm_campaign, page_viewed, bounce_flag, timestamp, user_id)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (str(uuid.uuid4()), cookie_id, "email", user_campaign, page, 0, t_stamp, uid))
                    user_interaction_counts[uid]['ga4'] += 1

            elif channel == 'LinkedIn':
                campaign_ads = [k for k in TRANSIENT_BURST_MAP[user_campaign].keys() if 'LI_AD' in k and k not in seen_campaign_assets]
                if not campaign_ads: continue
                ad = random.choice(campaign_ads)
                seen_campaign_assets.add(ad)
                
                t_stamp = get_asset_timestamp(user_campaign, ad, False)
                
                cursor.execute("""
                    INSERT INTO linkedin_events (event_id, campaign_id, ad_id, cookie_id, utm_source, spend_consumed, timestamp, user_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (str(uuid.uuid4()), user_campaign, ad, cookie_id, "linkedin", round(random.uniform(1.5, 8.5), 2), t_stamp, uid))
                user_interaction_counts[uid]['li'] += 1
                
                page = AD_PAGE_MAP.get(ad, "/contact-sales")
                cursor.execute("""
                    INSERT INTO ga4_events (session_id, cookie_id, utm_source, utm_campaign, page_viewed, bounce_flag, timestamp, user_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (str(uuid.uuid4()), cookie_id, "linkedin", user_campaign, page, 0, t_stamp, uid))
                user_interaction_counts[uid]['ga4'] += 1

        if not captured_identity and touches > 0:
            t_stamp = get_asset_timestamp(user_campaign, "/contact-sales", True)
            cursor.execute("""
                INSERT INTO ga4_events (session_id, cookie_id, utm_source, utm_campaign, page_viewed, bounce_flag, timestamp, user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (str(uuid.uuid4()), cookie_id, "direct", user_campaign, "/contact-sales", 0, t_stamp, uid))
            user_interaction_counts[uid]['ga4'] += 1

    num_anonymous = 35000
    print(f"Injecting {num_anonymous} top-of-funnel anonymous sessions clustered around campaign bursts...")
    
    # Inject anonymous
    for _ in range(num_anonymous):
        campaign = random.choices(WOOD_CAMPAIGNS, weights=[30, 25, 20, 15, 10])[0]
        utm_source = random.choices(['linkedin', 'direct', 'email'], weights=[60, 30, 10])[0]
        
        if utm_source == 'linkedin':
            campaign_ads = [k for k in TRANSIENT_BURST_MAP[campaign].keys() if 'LI_AD' in k]
            ad = random.choice(campaign_ads) if campaign_ads else 'NO_AD'
            page = AD_PAGE_MAP.get(ad, "/contact-sales")
            t_stamp = get_asset_timestamp(campaign, ad, False) if ad != 'NO_AD' else get_asset_timestamp(campaign, "/contact-sales", True)
        elif utm_source == 'email':
            campaign_emails = [k for k in TRANSIENT_BURST_MAP[campaign].keys() if 'EMAIL' in k]
            asset = random.choice(campaign_emails) if campaign_emails else 'NO_EMAIL'
            page = EMAIL_PAGE_MAP.get(asset, "/contact-sales")
            t_stamp = get_asset_timestamp(campaign, asset, False) if asset != 'NO_EMAIL' else get_asset_timestamp(campaign, "/contact-sales", True)
        else:
            campaign_insights = [k for k in TRANSIENT_BURST_MAP[campaign].keys() if '/insights/' in k or '/webinars/' in k]
            page = random.choice(campaign_insights) if (campaign_insights and random.random() < 0.6) else random.choice(CORE_WEB)
            is_core = page in CORE_WEB
            t_stamp = get_asset_timestamp(campaign, page, is_core)

        cursor.execute("""
            INSERT INTO ga4_events (session_id, cookie_id, utm_source, utm_campaign, page_viewed, bounce_flag, timestamp, user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (str(uuid.uuid4()), f"anon_{uuid.uuid4().hex[:8]}", utm_source, campaign, page, 
              1 if (utm_source == "linkedin" and random.random() < 0.25) or (utm_source != "linkedin" and random.random() < 0.65) else 0, 
              t_stamp, None))
              
    print("Syncing Master Summary table with exact event counts...")
    for uid, counts in user_interaction_counts.items():
        cursor.execute("""
            UPDATE master_summary 
            SET ga4_events = ?, mc_events = ?, spend_consumed = (SELECT SUM(spend_consumed) FROM linkedin_events WHERE user_id=?)
            WHERE user_id = ?
        """, (counts['ga4'], counts['mc'], uid, uid))

    print("Aligning CRM Opportunities to campaign bursts to ensure logical correlation...")
    cursor.execute("SELECT event_id, utm_campaign FROM crm_opps")
    opps = cursor.fetchall()
    for event_id, camp in opps:
        if camp in BURST_DATES and BURST_DATES[camp]:
            burst_date = random.choice(BURST_DATES[camp])
            opp_date = burst_date + timedelta(days=random.randint(3, 14))
            if opp_date > END_DATE: opp_date = burst_date + timedelta(days=1)
            cursor.execute("UPDATE crm_opps SET timestamp = ? WHERE event_id = ?", (opp_date.strftime('%Y-%m-%d %H:%M:%S'), event_id))

    conn.commit()
    conn.close()
    print("Simulation Complete. 18-Month funnel injected with perfect logical alignment.")

if __name__ == "__main__":
    run_simulation()
