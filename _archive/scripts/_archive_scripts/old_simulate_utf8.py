import sqlite3
import random
import uuid
from datetime import datetime, timedelta

DB_PATH = r"c:\Users\mpser\Downloads\Quantic\Capstone\capstone.db"

# 18-Month Timeline: Jan 1 2025 to Jun 30 2026
START_DATE = datetime(2025, 1, 1)
END_DATE = datetime(2026, 6, 30)

def random_date(start, end):
    return start + timedelta(seconds=random.randint(0, int((end - start).total_seconds())))

# Campaign Touchpoints for "The Future of Decarbonized Maintenance"
WOOD_REPORTS = [
    "/reports/annual-decarbonization-index-2025",
    "/whitepapers/digital-first-maintenance",
    "/case-studies/aramco-emissions-reduction",
    "/insights/beyond-labor-led-maintenance"
]

WOOD_WEB = [
    "/solutions/decarbonization",
    "/solutions/asset-performance-optimization",
    "/services/consulting",
    "/services/engineering",
    "/about/sustainability",
    "/careers",
    "/contact-sales",
    "/pricing-calculator",
    "/webinars/future-of-maintenance",
    "/blog/hydrogen-infrastructure-trends",
    "/blog/ai-in-predictive-maintenance",
    "/blog/scope-3-emissions",
    "/landing-page/future-of-decarbonized-maintenance"
]

WOOD_EMAILS = [
    "https://woodplc.com?utm_campaign=CMP_Q1_NEWSLETTER",
    "https://woodplc.com?utm_campaign=CMP_Q2_NEWSLETTER",
    "https://woodplc.com?utm_campaign=CMP_Q3_NEWSLETTER",
    "https://woodplc.com?utm_campaign=CMP_Q4_NEWSLETTER",
    "https://woodplc.com?utm_campaign=CMP_NURTURE_DECARBONIZATION_1",
    "https://woodplc.com?utm_campaign=CMP_NURTURE_DECARBONIZATION_2",
    "https://woodplc.com?utm_campaign=CMP_NURTURE_DECARBONIZATION_3",
    "https://woodplc.com?utm_campaign=CMP_WEBINAR_INVITE_MAINTENANCE",
    "https://woodplc.com?utm_campaign=CMP_REPORT_LAUNCH_INDEX",
    "https://woodplc.com?utm_campaign=CMP_CASE_STUDY_ARAMCO"
]

WOOD_LINKEDIN = [
    "LI_AD_DECARB_REPORT_STATIC",
    "LI_AD_PREDICTIVE_MAINTENANCE_VIDEO",
    "LI_AD_WEBINAR_PROMO",
    "LI_AD_ARAMCO_CASE_STUDY_CAROUSEL"
]

WOOD_CAMPAIGNS = [
    "CMP_LIVE_DECARBONIZATION_25_26",
    "CMP_LIVE_HYDROGEN_INFRASTRUCTURE",
    "CMP_LIVE_DIGITAL_TWIN",
    "CMP_PAST_SUSTAINABLE_ENGINEERING",
    "CMP_PAST_ASSET_OPTIMIZATION"
]

def run_simulation():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Clear old tables
    cursor.execute("DELETE FROM ga4_events")
    cursor.execute("DELETE FROM mailchimp_events")
    cursor.execute("DELETE FROM linkedin_events")

    # Fetch users
    cursor.execute("SELECT user_id, email, company_name FROM crm_users")
    users = cursor.fetchall()
    
    # Track interaction volumes to update master_summary later
    user_interaction_counts = {u[0]: {'ga4': 0, 'mc': 0, 'li': 0} for u in users}

    print(f"Simulating journeys for {len(users)} users...")

    for user in users:
        uid = user[0]
        email = user[1]
        
        # Determine Cohort via random chance (15% SQL, 35% MQL, 50% Cold)
        rand = random.random()
        if rand < 0.15:
            cohort = "SQL"
            touches = random.randint(8, 25)
        elif rand < 0.50:
            cohort = "MQL"
            touches = random.randint(3, 7)
        else:
            cohort = "Cold"
            touches = random.randint(0, 2)

        # Generate timeline for user
        # SQLs span the whole 18 months. Cold drops off early.
        if cohort == "Cold":
            user_start = random_date(START_DATE, END_DATE - timedelta(days=90))
            user_end = user_start + timedelta(days=random.randint(1, 14))
        elif cohort == "MQL":
            user_start = random_date(START_DATE, END_DATE - timedelta(days=180))
            user_end = user_start + timedelta(days=random.randint(30, 180))
        else:
            user_start = random_date(START_DATE, START_DATE + timedelta(days=180))
            user_end = random_date(END_DATE - timedelta(days=90), END_DATE)

        user_campaign = random.choice(WOOD_CAMPAIGNS)

        for _ in range(touches):
            t_stamp = random_date(user_start, user_end).strftime('%Y-%m-%d %H:%M:%S.%f')
            channel = random.choices(['Web', 'Report', 'Email', 'LinkedIn'], weights=[40, 15, 30, 15])[0]

            if channel in ['Web', 'Report']:
                page = random.choice(WOOD_REPORTS) if channel == 'Report' else random.choice(WOOD_WEB)
                cursor.execute("""
                    INSERT INTO ga4_events (session_id, cookie_id, utm_source, utm_campaign, page_viewed, bounce_flag, timestamp, user_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (str(uuid.uuid4()), f"cookie_{uid}", "direct", user_campaign, page, 0, t_stamp, uid))
                user_interaction_counts[uid]['ga4'] += 1

            elif channel == 'Email':
                asset = random.choice(WOOD_EMAILS)
                action = random.choices(["Open", "Click"], weights=[70, 30])[0]
                cursor.execute("""
                    INSERT INTO mailchimp_events (event_id, email, campaign_id, action, url_clicked, timestamp, user_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (str(uuid.uuid4()), email, user_campaign, action, asset, t_stamp, uid))
                user_interaction_counts[uid]['mc'] += 1

            elif channel == 'LinkedIn':
                ad = random.choice(WOOD_LINKEDIN)
                cursor.execute("""
                    INSERT INTO linkedin_events (event_id, campaign_id, ad_id, cookie_id, utm_source, spend_consumed, timestamp, user_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (str(uuid.uuid4()), user_campaign, ad, f"cookie_{uid}", "linkedin", round(random.uniform(1.5, 8.5), 2), t_stamp, uid))
                user_interaction_counts[uid]['li'] += 1

    # Sync Master Summary
    print("Syncing Master Summary table with exact event counts...")
    for uid, counts in user_interaction_counts.items():
        cursor.execute("""
            UPDATE master_summary 
            SET ga4_events = ?, mc_events = ?, spend_consumed = (SELECT SUM(spend_consumed) FROM linkedin_events WHERE user_id=?)
            WHERE user_id = ?
        """, (counts['ga4'], counts['mc'], uid, uid))

    conn.commit()
    conn.close()
    print("Simulation Complete. 18-Month funnel injected.")

if __name__ == "__main__":
    run_simulation()
