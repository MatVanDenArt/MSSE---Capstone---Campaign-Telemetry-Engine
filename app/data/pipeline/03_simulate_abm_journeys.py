import random
import uuid
import pandas as pd
from datetime import datetime, timedelta
import os
from config import OUTPUT_DIR, TARGET_ACCOUNTS

random.seed(42)

END_DATE = datetime.now()
START_DATE = END_DATE - timedelta(days=545)

def random_date(start, end):
    return start + timedelta(seconds=random.randint(0, int((end - start).total_seconds())))

CORE_WEB = [
    "/solutions/decarbonization", "/solutions/asset-performance-optimization",
    "/services/consulting", "/services/engineering", "/about/sustainability",
    "/careers", "/contact-sales", "/pricing-calculator"
]

WOOD_CAMPAIGNS = [
    "CMP_LIVE_DECARBONIZATION_25_26", "CMP_LIVE_HYDROGEN_INFRASTRUCTURE",
    "CMP_LIVE_DIGITAL_TWIN", "CMP_PAST_SUSTAINABLE_ENGINEERING", "CMP_PAST_ASSET_OPTIMIZATION"
]

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

TRANSIENT_BURST_MAP = {}
EMAIL_PAGE_MAP = {}
AD_PAGE_MAP = {}

for campaign in WOOD_CAMPAIGNS:
    TRANSIENT_BURST_MAP[campaign] = {}
    for burst_idx, burst_date in enumerate(BURST_DATES[campaign]):
        c_prefix = campaign.split('_')[-1].lower()
        
        # Case Studies
        for i in range(random.randint(1, 2)):
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
        skewed_seconds = int(total_seconds * (random.random() ** 4))
        return (drop_date + timedelta(seconds=skewed_seconds)).strftime('%Y-%m-%d %H:%M:%S.%f')

def simulate_abm_journeys():
    print("Simulating ABM Journeys...")
    users_path = os.path.join(OUTPUT_DIR, "crm_users.csv")
    if not os.path.exists(users_path):
        print(f"Error: {users_path} not found. Run 01_generate_crm.py first.")
        return
        
    users_df = pd.read_csv(users_path)
    
    ga4_events = []
    mailchimp_events = []
    linkedin_events = []
    crm_opps = []
    
    for _, row in users_df.iterrows():
        uid = row['user_id']
        email = row['email']
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
                    captured_identity = True
                    
                ga4_events.append({
                    "session_id": str(uuid.uuid4()), "cookie_id": cookie_id, "utm_source": "direct", 
                    "utm_campaign": user_campaign, "page_viewed": page, "bounce_flag": 0, 
                    "timestamp": t_stamp, "user_id_captured": uid
                })

            elif channel == 'Email':
                campaign_emails = [k for k in TRANSIENT_BURST_MAP[user_campaign].keys() if 'EMAIL' in k and k not in seen_campaign_assets]
                if not campaign_emails: continue
                asset = random.choice(campaign_emails)
                seen_campaign_assets.add(asset)
                
                t_stamp = get_asset_timestamp(user_campaign, asset, False)
                action = random.choices(["Open", "Click"], weights=[70, 30])[0]
                
                mailchimp_events.append({
                    "event_id": str(uuid.uuid4()), "email": email, "campaign_id": user_campaign, 
                    "action": action, "url_clicked": asset, "timestamp": t_stamp
                })
                
                if action == 'Click':
                    page = EMAIL_PAGE_MAP.get(asset, "/contact-sales")
                    ga4_events.append({
                        "session_id": str(uuid.uuid4()), "cookie_id": cookie_id, "utm_source": "email", 
                        "utm_campaign": user_campaign, "page_viewed": page, "bounce_flag": 0, 
                        "timestamp": t_stamp, "user_id_captured": uid
                    })

            elif channel == 'LinkedIn':
                campaign_ads = [k for k in TRANSIENT_BURST_MAP[user_campaign].keys() if 'LI_AD' in k and k not in seen_campaign_assets]
                if not campaign_ads: continue
                ad = random.choice(campaign_ads)
                seen_campaign_assets.add(ad)
                
                t_stamp = get_asset_timestamp(user_campaign, ad, False)
                
                linkedin_events.append({
                    "event_id": str(uuid.uuid4()), "campaign_id": user_campaign, "ad_id": ad, 
                    "click_id": cookie_id, "utm_source": "linkedin", "spend_consumed": round(random.uniform(1.5, 8.5), 2), 
                    "timestamp": t_stamp
                })
                
                page = AD_PAGE_MAP.get(ad, "/contact-sales")
                ga4_events.append({
                    "session_id": str(uuid.uuid4()), "cookie_id": cookie_id, "utm_source": "linkedin", 
                    "utm_campaign": user_campaign, "page_viewed": page, "bounce_flag": 0, 
                    "timestamp": t_stamp, "user_id_captured": uid
                })

        if not captured_identity and touches > 0:
            t_stamp = get_asset_timestamp(user_campaign, "/contact-sales", True)
            ga4_events.append({
                "session_id": str(uuid.uuid4()), "cookie_id": cookie_id, "utm_source": "direct", 
                "utm_campaign": user_campaign, "page_viewed": "/contact-sales", "bounce_flag": 0, 
                "timestamp": t_stamp, "user_id_captured": uid
            })

        # Generate ABM Opportunities aligned perfectly with Burst Dates
        if cohort == "SQL" and BURST_DATES[user_campaign]:
            burst_date = random.choice(BURST_DATES[user_campaign])
            opp_date = burst_date + timedelta(days=random.randint(3, 14))
            if opp_date > END_DATE: opp_date = burst_date + timedelta(days=1)
            
            crm_opps.append({
                "event_id": str(uuid.uuid4()), "user_id": uid, "account_id": row['account_id'],
                "event_type": "Opportunity Created", "pipeline_value": round(random.uniform(5000000, 20000000), 2), 
                "timestamp": opp_date.strftime('%Y-%m-%d %H:%M:%S'), "utm_campaign": user_campaign
            })
            
            # Close won logic
            if random.random() < 0.25:
                close_date = opp_date + timedelta(days=random.randint(30, 180))
                if close_date <= END_DATE:
                    crm_opps.append({
                        "event_id": str(uuid.uuid4()), "user_id": uid, "account_id": row['account_id'],
                        "event_type": "Closed Won", "pipeline_value": round(random.uniform(5000000, 20000000), 2), 
                        "timestamp": close_date.strftime('%Y-%m-%d %H:%M:%S'), "utm_campaign": user_campaign
                    })

    # Anonymous traffic
    num_anonymous = 35000
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

        ga4_events.append({
            "session_id": str(uuid.uuid4()), "cookie_id": f"anon_{uuid.uuid4().hex[:8]}", "utm_source": utm_source, 
            "utm_campaign": campaign, "page_viewed": page, "bounce_flag": 1 if (utm_source == "linkedin" and random.random() < 0.25) or (utm_source != "linkedin" and random.random() < 0.65) else 0, 
            "timestamp": t_stamp, "user_id_captured": None
        })

    pd.DataFrame(crm_opps).to_csv(os.path.join(OUTPUT_DIR, "crm_opps_abm.csv"), index=False)
    pd.DataFrame(mailchimp_events).to_csv(os.path.join(OUTPUT_DIR, "mailchimp_abm.csv"), index=False)
    pd.DataFrame(linkedin_events).to_csv(os.path.join(OUTPUT_DIR, "linkedin_abm.csv"), index=False)
    pd.DataFrame(ga4_events).to_csv(os.path.join(OUTPUT_DIR, "ga4_abm.csv"), index=False)
    print("ABM Journeys simulation complete.")

if __name__ == "__main__":
    simulate_abm_journeys()
