import random
import uuid
import pandas as pd
from datetime import datetime, timedelta
from faker import Faker

fake = Faker()

TARGET_ACCOUNTS = [
    "Shell", "Aramco", "Equinor", "BP", "Chevron",
    "ExxonMobil", "TotalEnergies", "ConocoPhillips", "Eni", "Petrobras",
    "Schlumberger", "Halliburton", "Baker Hughes", "Weatherford", "National Oilwell Varco"
]

SENIORITY_LEVELS = ["C-Suite", "VP/Director", "Manager", "IC"]

def _generate_funnel(seed_time, campaign_id, email, user_id_counter, account_id, linkedin_events, ga4_events, mailchimp_events, crm_opps, seniority):
    bucket_roll = random.random()
    cookie_id = str(uuid.uuid4())
    
    if bucket_roll < 0.05:
        # Golden Path (Full Funnel to CRM, takes months)
        li_time = seed_time
        linkedin_events.append({
            "event_id": str(uuid.uuid4()), "campaign_id": campaign_id, "ad_id": "AD_101",
            "click_id": cookie_id, "utm_source": "linkedin", "spend_consumed": round(random.uniform(500.0, 5000.0), 2), "timestamp": li_time
        })
        
        ga4_time = li_time + timedelta(seconds=2)
        ga4_events.append({
            "session_id": str(uuid.uuid4()), "cookie_id": cookie_id, "utm_source": "linkedin", "utm_campaign": campaign_id,
            "page_viewed": "/whitepaper-download", "bounce_flag": False, "user_id_captured": user_id_counter, "timestamp": ga4_time
        })
        
        mc_time = ga4_time + timedelta(days=random.randint(1, 15))
        mailchimp_events.append({
            "event_id": str(uuid.uuid4()), "email": email, "campaign_id": f"NURTURE_{campaign_id}",
            "action": "Open", "url_clicked": None, "timestamp": mc_time
        })
        
        crm_create_time = mc_time + timedelta(days=random.randint(30, 90))
        # Ensure opportunity creation doesn't occur in the future
        if crm_create_time < datetime.now():
            crm_opps.append({
                "event_id": str(uuid.uuid4()), "user_id": user_id_counter, "account_id": account_id,
                "event_type": "Opportunity Created", "pipeline_value": round(random.uniform(5000000, 20000000), 2), "timestamp": crm_create_time
            })
            
            # Only ~15% of opportunities close won, primarily C-Suite or VP/Director
            if random.random() < 0.15 and seniority in ["C-Suite", "VP/Director"]:
                crm_won_time = crm_create_time + timedelta(days=random.randint(90, 540)) # 3 to 18 months
                if crm_won_time < datetime.now():
                    # Massive pipeline values for Wood Group
                    val_tier = random.random()
                    if val_tier < 0.70:
                        pipeline = random.uniform(5000000, 20000000) # $5M - $20M
                    elif val_tier < 0.95:
                        pipeline = random.uniform(20000000, 100000000) # $20M - $100M
                    else:
                        pipeline = random.uniform(100000000, 250000000) # $100M - $250M
                        
                    crm_opps.append({
                        "event_id": str(uuid.uuid4()), "user_id": user_id_counter, "account_id": account_id,
                        "event_type": "Closed Won", "pipeline_value": round(pipeline, 2), "timestamp": crm_won_time
                    })
        
    elif bucket_roll < 0.35:
        # Partial Match
        mc_time = seed_time
        mailchimp_events.append({
            "event_id": str(uuid.uuid4()), "email": email, "campaign_id": f"NURTURE_{campaign_id}",
            "action": "Open", "url_clicked": f"https://example.com?utm_source=mailchimp&utm_campaign={campaign_id}", "timestamp": mc_time
        })
        
        ga4_time = mc_time + timedelta(seconds=10)
        ga4_events.append({
            "session_id": str(uuid.uuid4()), "cookie_id": cookie_id, "utm_source": "mailchimp", "utm_campaign": campaign_id,
            "page_viewed": "/home", "bounce_flag": True, "user_id_captured": None, "timestamp": ga4_time
        })

def generate_b2b_data():
    now = datetime.now()
    
    crm_users = []
    crm_opps = []
    mailchimp_events = []
    linkedin_events = []
    ga4_events = []
    
    user_id_counter = 1
    for account_id, company_name in enumerate(TARGET_ACCOUNTS, start=1):
        domain = company_name.lower().replace(" ", "") + ".com"
        num_users = random.randint(30, 50)
        
        for _ in range(num_users):
            first_name = fake.first_name()
            last_name = fake.last_name()
            email = f"{first_name.lower()}.{last_name.lower()}@{domain}"
            seniority = random.choices(SENIORITY_LEVELS, weights=[5, 15, 30, 50])[0]
            
            crm_users.append({
                "user_id": user_id_counter, "account_id": account_id, "company_name": company_name,
                "email": email, "first_name": first_name, "last_name": last_name, "seniority": seniority
            })
            
            # --- Generate Data for Multiple Campaigns ---
            
            # 1. Live: Gastech 2026
            if random.random() < 0.6:
                days_ago = random.randint(1, 30)
                seed_time = now - timedelta(days=days_ago, hours=random.randint(0, 23))
                _generate_funnel(seed_time, "CMP_LIVE_GASTECH_2026", email, user_id_counter, account_id, linkedin_events, ga4_events, mailchimp_events, crm_opps, seniority)

            # 2. Live: OTC 2026
            if random.random() < 0.4:
                days_ago = random.randint(1, 60)
                seed_time = now - timedelta(days=days_ago, hours=random.randint(0, 23))
                _generate_funnel(seed_time, "CMP_LIVE_OTC_2026", email, user_id_counter, account_id, linkedin_events, ga4_events, mailchimp_events, crm_opps, seniority)

            # 3. Past: Oil & Gas US
            if random.random() < 0.4:
                days_ago = random.randint(150, 300) if random.random() < 0.90 else random.randint(1, 7)
                seed_time = now - timedelta(days=days_ago, hours=random.randint(0, 23))
                _generate_funnel(seed_time, "CMP_PAST_OIL_GAS_US", email, user_id_counter, account_id, linkedin_events, ga4_events, mailchimp_events, crm_opps, seniority)
                
            # 4. Past: Middle East
            if random.random() < 0.3:
                days_ago = random.randint(300, 500) if random.random() < 0.95 else random.randint(1, 15)
                seed_time = now - timedelta(days=days_ago, hours=random.randint(0, 23))
                _generate_funnel(seed_time, "CMP_PAST_MIDDLE_EAST", email, user_id_counter, account_id, linkedin_events, ga4_events, mailchimp_events, crm_opps, seniority)

            # 5. Past: O&M 2026
            if random.random() < 0.2:
                days_ago = random.randint(500, 800) if random.random() < 0.95 else random.randint(1, 15)
                seed_time = now - timedelta(days=days_ago, hours=random.randint(0, 23))
                _generate_funnel(seed_time, "CMP_PAST_O_M_2026", email, user_id_counter, account_id, linkedin_events, ga4_events, mailchimp_events, crm_opps, seniority)
            
            user_id_counter += 1

    # Ghosts (Anonymous bounces)
    num_ghosts = int(user_id_counter * 0.3)
    for _ in range(num_ghosts):
        days_ago = random.randint(1, 90)
        seed_time = now - timedelta(days=days_ago, hours=random.randint(0, 23))
        cookie_id = str(uuid.uuid4())
        campaign_id = random.choice(["CMP_LIVE_GASTECH_2026", "CMP_LIVE_OTC_2026", "CMP_PAST_OIL_GAS_US", "CMP_PAST_MIDDLE_EAST", "CMP_PAST_O_M_2026"])
        
        linkedin_events.append({
            "event_id": str(uuid.uuid4()), "campaign_id": campaign_id, "ad_id": "AD_102",
            "click_id": cookie_id, "utm_source": "linkedin", "spend_consumed": round(random.uniform(5.0, 20.0), 2), "timestamp": seed_time
        })
        
        ga4_events.append({
            "session_id": str(uuid.uuid4()), "cookie_id": cookie_id, "utm_source": "linkedin", "utm_campaign": campaign_id,
            "page_viewed": "/landing-page", "bounce_flag": True, "user_id_captured": None, "timestamp": seed_time + timedelta(seconds=2)
        })

    return {
        "crm_users": pd.DataFrame(crm_users),
        "crm_opps": pd.DataFrame(crm_opps),
        "mailchimp": pd.DataFrame(mailchimp_events),
        "linkedin": pd.DataFrame(linkedin_events),
        "ga4": pd.DataFrame(ga4_events)
    }
