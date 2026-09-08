import random
import uuid
import pandas as pd
import json
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

# Stagger campaigns 3 months apart over the 18-month duration:
# Month 0:  CMP_PAST_ASSET_OPTIMIZATION (past, ~10 mo)
# Month 3:  CMP_PAST_SUSTAINABLE_ENGINEERING (past, ~10 mo)
# Month 6:  CMP_LIVE_HYDROGEN_INFRASTRUCTURE (live, to present)
# Month 9:  CMP_LIVE_DIGITAL_TWIN (live, to present)
# Month 12: CMP_LIVE_DECARBONIZATION_25_26 (live, 6 mo to present)

CAMPAIGN_SCHEDULE = [
    ("CMP_PAST_ASSET_OPTIMIZATION", 0, 10, False),
    ("CMP_PAST_SUSTAINABLE_ENGINEERING", 3, 10, False),
    ("CMP_LIVE_HYDROGEN_INFRASTRUCTURE", 6, 12, True),
    ("CMP_LIVE_DIGITAL_TWIN", 9, 9, True),
    ("CMP_LIVE_DECARBONIZATION_25_26", 12, 6, True)
]

WOOD_CAMPAIGNS = [c[0] for c in CAMPAIGN_SCHEDULE]

BURST_DATES = {}
for campaign, start_month, dur_month, is_live in CAMPAIGN_SCHEDULE:
    c_start = START_DATE + timedelta(days=int(start_month * 30.4))
    c_end = END_DATE if is_live else min(END_DATE, c_start + timedelta(days=int(dur_month * 30.4)))
    
    bursts = []
    curr = c_start
    cadence = 60 if "DECARBONIZATION" in campaign else 50
    while curr <= c_end:
        bursts.append(curr)
        curr += timedelta(days=cadence)
    BURST_DATES[campaign] = bursts

# Load Content Catalogue
catalogue_path = os.path.join(os.path.dirname(__file__), "content_catalogue.json")
with open(catalogue_path, "r", encoding="utf-8") as f:
    CONTENT_CATALOGUE = json.load(f)

TRANSIENT_BURST_MAP = {}
EMAIL_PAGE_MAP = {}
AD_PAGE_MAP = {}

for campaign in WOOD_CAMPAIGNS:
    TRANSIENT_BURST_MAP[campaign] = {}
    
    campaign_assets = CONTENT_CATALOGUE.get(campaign, [])
    case_studies = [a['url'] for a in campaign_assets if a['asset_type'] == 'Case Study']
    reports = [a['url'] for a in campaign_assets if a['asset_type'] == 'Report']
    webinars = [a['url'] for a in campaign_assets if a['asset_type'] == 'Webinar']
    emails = [a['url'] for a in campaign_assets if a['asset_type'] == 'Email']
    ads = [a['url'] for a in campaign_assets if a['asset_type'] == 'LinkedIn Ad']
    
    cs_idx = 0
    rep_idx = 0
    web_idx = 0
    email_idx = 0
    ad_idx = 0
    
    for burst_idx, burst_date in enumerate(BURST_DATES[campaign]):
        
        # Case Studies (1 unique case study per burst from curated catalogue)
        if cs_idx < len(case_studies):
            asset = case_studies[cs_idx]
            cs_idx += 1
        elif case_studies:
            asset = case_studies[burst_idx % len(case_studies)]
        else:
            asset = f"/case-studies/{campaign.lower()}-b{burst_idx+1}"
        drop = burst_date + timedelta(days=random.randint(0, 14))
        TRANSIENT_BURST_MAP[campaign][asset] = min(drop, END_DATE)
            
        # Insights (Reports & Webinars combined, 1 unique insight per burst from curated catalogue)
        insights_pool = reports + webinars
        if rep_idx < len(insights_pool):
            asset = insights_pool[rep_idx]
            rep_idx += 1
        elif insights_pool:
            asset = insights_pool[burst_idx % len(insights_pool)]
        else:
            asset = f"/insights/{campaign.lower()}-b{burst_idx+1}"
        drop = burst_date + timedelta(days=random.randint(0, 14))
        TRANSIENT_BURST_MAP[campaign][asset] = min(drop, END_DATE)
            
        # Emails (1 unique email per burst from curated catalogue)
        if email_idx < len(emails):
            asset = emails[email_idx]
            email_idx += 1
        elif emails:
            asset = emails[burst_idx % len(emails)]
        else:
            asset = f"email-{campaign.lower()}-{burst_idx+1}"
            
        mailchimp_url = f"https://example.com?utm_source=mailchimp&utm_campaign={asset}"
        drop = burst_date + timedelta(days=random.randint(0, 14))
        TRANSIENT_BURST_MAP[campaign][mailchimp_url] = min(drop, END_DATE)
        
        # Pick an active report/webinar for the email click
        insights_list = [k for k in TRANSIENT_BURST_MAP[campaign].keys() if ('/insights/' in k or '/webinars/' in k) and 'http' not in k]
        EMAIL_PAGE_MAP[mailchimp_url] = random.choice(insights_list) if insights_list else "/contact-sales"
            
        # LinkedIn Ads (1 unique ad per burst from curated catalogue)
        if ad_idx < len(ads):
            asset = ads[ad_idx]
            ad_idx += 1
        elif ads:
            asset = ads[burst_idx % len(ads)]
        else:
            asset = f"li-ad-{campaign.lower()}-{burst_idx+1}"
            
        drop = burst_date + timedelta(days=random.randint(0, 14))
        TRANSIENT_BURST_MAP[campaign][asset] = min(drop, END_DATE)
        
        # Pick an active case study for the ad click
        cs_list = [k for k in TRANSIENT_BURST_MAP[campaign].keys() if '/case-studies/' in k and 'http' not in k and 'li-ad' not in k]
        AD_PAGE_MAP[asset] = random.choice(cs_list) if cs_list else "/contact-sales"

def get_asset_timestamp(campaign, asset, is_core):
    if is_core:
        camp_start = BURST_DATES[campaign][0] if campaign in BURST_DATES and BURST_DATES[campaign] else START_DATE
        camp_end = BURST_DATES[campaign][-1] + timedelta(days=60) if "PAST" in campaign else END_DATE
        camp_end = min(camp_end, END_DATE)
        return random_date(camp_start, camp_end).strftime('%Y-%m-%d %H:%M:%S.%f')
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
                campaign_emails = [k for k in TRANSIENT_BURST_MAP[user_campaign].keys() if 'email' in k.lower() and k not in seen_campaign_assets]
                if not campaign_emails: continue
                asset = random.choice(campaign_emails)
                seen_campaign_assets.add(asset)
                
                t_stamp = get_asset_timestamp(user_campaign, asset, False)
                base_dt = datetime.strptime(t_stamp, '%Y-%m-%d %H:%M:%S.%f')
                
                # An email touchpoint always registers an Open event (with 35% re-opening 2-3 times)
                num_opens = random.choices([1, 2, 3], weights=[65, 25, 10])[0]
                for o_idx in range(num_opens):
                    open_dt = base_dt if o_idx == 0 else min(base_dt + timedelta(hours=random.randint(2, 48)), END_DATE)
                    open_stamp = open_dt.strftime('%Y-%m-%d %H:%M:%S.%f')
                    mailchimp_events.append({
                        "event_id": str(uuid.uuid4()), "email": email, "campaign_id": user_campaign, 
                        "action": "Open", "url_clicked": asset, "timestamp": open_stamp
                    })
                
                # ~30% of users who open also click through to the landing asset
                if random.random() < 0.30:
                    click_dt = min(base_dt + timedelta(seconds=random.randint(15, 180)), END_DATE)
                    click_stamp = click_dt.strftime('%Y-%m-%d %H:%M:%S.%f')
                    mailchimp_events.append({
                        "event_id": str(uuid.uuid4()), "email": email, "campaign_id": user_campaign, 
                        "action": "Click", "url_clicked": asset, "timestamp": click_stamp
                    })
                    
                    page = EMAIL_PAGE_MAP.get(asset, "/contact-sales")
                    ga4_events.append({
                        "session_id": str(uuid.uuid4()), "cookie_id": cookie_id, "utm_source": "email", 
                        "utm_campaign": user_campaign, "page_viewed": page, "bounce_flag": 0, 
                        "timestamp": click_stamp, "user_id_captured": uid
                    })

            elif channel == 'LinkedIn':
                campaign_ads = [k for k in TRANSIENT_BURST_MAP[user_campaign].keys() if 'li-ad' in k.lower() and k not in seen_campaign_assets]
                if not campaign_ads: continue
                ad = random.choice(campaign_ads)
                seen_campaign_assets.add(ad)
                
                t_stamp = get_asset_timestamp(user_campaign, ad, False)
                
                linkedin_events.append({
                    "event_id": str(uuid.uuid4()), "campaign_id": user_campaign, "ad_id": ad, 
                    "click_id": cookie_id, "utm_source": "linkedin", "spend_consumed": round(random.uniform(250.0, 1500.0), 2), 
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
            campaign_ads = [k for k in TRANSIENT_BURST_MAP[campaign].keys() if 'li-ad' in k.lower()]
            ad = random.choice(campaign_ads) if campaign_ads else 'NO_AD'
            page = AD_PAGE_MAP.get(ad, "/contact-sales")
            t_stamp = get_asset_timestamp(campaign, ad, False) if ad != 'NO_AD' else get_asset_timestamp(campaign, "/contact-sales", True)
        elif utm_source == 'email':
            campaign_emails = [k for k in TRANSIENT_BURST_MAP[campaign].keys() if 'email' in k.lower()]
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
