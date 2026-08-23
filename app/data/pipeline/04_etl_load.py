import pandas as pd
import sqlite3
import os
from config import OUTPUT_DIR

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "capstone.db")

def _load_and_concat(base_file, abm_file):
    base_path = os.path.join(OUTPUT_DIR, base_file)
    abm_path = os.path.join(OUTPUT_DIR, abm_file)
    
    dfs = []
    if os.path.exists(base_path):
        dfs.append(pd.read_csv(base_path))
    if os.path.exists(abm_path):
        dfs.append(pd.read_csv(abm_path))
        
    if not dfs:
        return pd.DataFrame()
    return pd.concat(dfs, ignore_index=True)

def etl_load():
    print(f"Loading data into {DB_PATH}...")
    conn = sqlite3.connect(DB_PATH)
    
    # 1. CRM Users
    users_path = os.path.join(OUTPUT_DIR, "crm_users.csv")
    if os.path.exists(users_path):
        crm_users = pd.read_csv(users_path)
        crm_users.to_sql("crm_users", conn, if_exists="replace", index=False)
        print("Loaded crm_users")
        
    # 2. CRM Opps
    opps_df = _load_and_concat("crm_opps_baseline.csv", "crm_opps_abm.csv")
    if not opps_df.empty:
        opps_df.to_sql("crm_opps", conn, if_exists="replace", index=False)
        print("Loaded crm_opps")
        
    # Load raw events for ETL matching
    mc_df = _load_and_concat("mailchimp_baseline.csv", "mailchimp_abm.csv")
    li_df = _load_and_concat("linkedin_baseline.csv", "linkedin_abm.csv")
    ga4_df = _load_and_concat("ga4_baseline.csv", "ga4_abm.csv")
    
    # --- IDENTITY RESOLUTION ---
    # 1. Retroactive Cookie Stitching (GA4)
    if not ga4_df.empty:
        converted_cookies = ga4_df[ga4_df['user_id_captured'].notna()][['cookie_id', 'user_id_captured']].drop_duplicates()
        ga4_df = ga4_df.drop(columns=['user_id_captured']).merge(converted_cookies, on='cookie_id', how='left')
        ga4_df.rename(columns={'user_id_captured': 'user_id'}, inplace=True)
    
    # 2. Mailchimp email -> user_id matching
    if not mc_df.empty and 'crm_users' in locals() and not crm_users.empty:
        mc_df = mc_df.merge(crm_users[['email', 'user_id']], on='email', how='left')
        
    # 3. LinkedIn cookie_id -> user_id matching
    if not li_df.empty and not ga4_df.empty:
        if 'click_id' in li_df.columns:
            li_df.rename(columns={'click_id': 'cookie_id'}, inplace=True)
        ga4_cookie_user = ga4_df[['cookie_id', 'user_id']].dropna().drop_duplicates()
        li_df = li_df.merge(ga4_cookie_user, on='cookie_id', how='left')

    # Ensure timestamp consistency
    for df in [opps_df, mc_df, li_df, ga4_df]:
        if not df.empty and 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'], format='mixed')

    # --- SAVE TO DB ---
    if not mc_df.empty:
        mc_df.to_sql("mailchimp_events", conn, if_exists="replace", index=False)
        print("Loaded mailchimp_events")
        
    if not li_df.empty:
        li_df.to_sql("linkedin_events", conn, if_exists="replace", index=False)
        print("Loaded linkedin_events")
        
    if not ga4_df.empty:
        ga4_df.to_sql("ga4_events", conn, if_exists="replace", index=False)
        print("Loaded ga4_events")

    # 6. Build Content Metadata Table
    print("Building Content Metadata table...")
    if not ga4_df.empty:
        distinct_urls = ga4_df['page_viewed'].dropna().unique()
        metadata_records = []
        for url in distinct_urls:
            url_lower = url.lower()
            if 'decarbonization' in url_lower: topic = "Decarbonization"
            elif 'digital_twin' in url_lower or 'digital' in url_lower: topic = "Digital Twin"
            elif 'decommissioning' in url_lower or 'decom' in url_lower: topic = "Decommissioning"
            elif 'hydrogen' in url_lower: topic = "Hydrogen & CCUS"
            elif 'carbon' in url_lower or 'ccus' in url_lower: topic = "Hydrogen & CCUS"
            else: topic = "General Engineering"
            
            if 'case-studies' in url_lower: asset_type = "Case Study"
            elif 'insights' in url_lower or 'report' in url_lower: asset_type = "Report"
            elif 'webinar' in url_lower: asset_type = "Webinar"
            else: asset_type = "Web Page"
            
            metadata_records.append({"url": url, "intent_topic": topic, "asset_type": asset_type})
            
        pd.DataFrame(metadata_records).to_sql("content_metadata", conn, if_exists="replace", index=False)
        print("Loaded content_metadata")

    # 7. Build Master Summary Table
    print("Building Master Summary table...")
    cursor = conn.cursor()
    cursor.execute("DROP TABLE IF EXISTS master_summary")
    cursor.execute('''
        CREATE TABLE master_summary AS
        SELECT 
            u.user_id,
            u.account_id,
            u.company_name,
            u.email,
            u.seniority,
            u.persona_type,
            (SELECT COUNT(*) FROM ga4_events WHERE user_id = u.user_id) as ga4_events,
            (SELECT COUNT(*) FROM mailchimp_events WHERE email = u.email) as mc_events,
            (SELECT COUNT(*) FROM linkedin_events l JOIN ga4_events g ON l.cookie_id = g.cookie_id WHERE g.user_id = u.user_id) as li_events,
            (SELECT SUM(spend_consumed) FROM linkedin_events l JOIN ga4_events g ON l.cookie_id = g.cookie_id WHERE g.user_id = u.user_id) as spend_consumed,
            (SELECT COUNT(*) FROM crm_opps WHERE user_id = u.user_id) as opp_count
        FROM crm_users u
    ''')
    
    conn.commit()
    conn.close()
    print("ETL Load Complete.")

if __name__ == "__main__":
    etl_load()
