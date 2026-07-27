import sqlite3
import pandas as pd

def run_etl(dataframes: dict, db_path: str = "capstone.db"):
    crm_users = dataframes["crm_users"]
    crm_opps = dataframes["crm_opps"]
    mailchimp = dataframes["mailchimp"]
    linkedin = dataframes["linkedin"]
    ga4 = dataframes["ga4"]
    
    # 1. Retroactive Cookie Stitching (GA4)
    if not ga4.empty:
        converted_cookies = ga4[ga4['user_id_captured'].notna()][['cookie_id', 'user_id_captured']].drop_duplicates()
        ga4 = ga4.drop(columns=['user_id_captured']).merge(converted_cookies, on='cookie_id', how='left')
        ga4.rename(columns={'user_id_captured': 'user_id'}, inplace=True)
    
    # 2. Mailchimp email -> user_id matching
    if not mailchimp.empty and not crm_users.empty:
        mailchimp = mailchimp.merge(crm_users[['email', 'user_id']], on='email', how='left')
        
    # 3. LinkedIn cookie_id -> user_id matching
    if not linkedin.empty and not ga4.empty:
        linkedin.rename(columns={'click_id': 'cookie_id'}, inplace=True)
        ga4_cookie_user = ga4[['cookie_id', 'user_id']].dropna().drop_duplicates()
        linkedin = linkedin.merge(ga4_cookie_user, on='cookie_id', how='left')

    # Ensure timestamp consistency
    for df in [crm_opps, mailchimp, linkedin, ga4]:
        if not df.empty and 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Write source tables to DB
    conn = sqlite3.connect(db_path)
    
    crm_users.to_sql("crm_users", conn, if_exists="replace", index=False)
    crm_opps.to_sql("crm_opps", conn, if_exists="replace", index=False)
    mailchimp.to_sql("mailchimp_events", conn, if_exists="replace", index=False)
    linkedin.to_sql("linkedin_events", conn, if_exists="replace", index=False)
    ga4.to_sql("ga4_events", conn, if_exists="replace", index=False)
    
    # Master Outer Merge (The B2B Identity Graph)
    if not crm_users.empty:
        master = crm_users.copy()
        
        if not crm_opps.empty:
            opps_agg = crm_opps.groupby('user_id')['pipeline_value'].sum().reset_index()
            master = pd.merge(master, opps_agg, on='user_id', how='outer')
            
        if not mailchimp.empty and 'user_id' in mailchimp.columns:
            mc_agg = mailchimp.groupby('user_id').size().reset_index(name='mc_events')
            master = pd.merge(master, mc_agg, on='user_id', how='outer')
            
        if not ga4.empty and 'user_id' in ga4.columns:
            ga4_agg = ga4.groupby('user_id').size().reset_index(name='ga4_events')
            master = pd.merge(master, ga4_agg, on='user_id', how='outer')
            
        if not linkedin.empty and 'user_id' in linkedin.columns:
            li_agg = linkedin.groupby('user_id')['spend_consumed'].sum().reset_index()
            master = pd.merge(master, li_agg, on='user_id', how='outer')
            
        master.to_sql("master_summary", conn, if_exists="replace", index=False)
        
    conn.close()
    print("ETL complete. Database capstone.db updated via outer joins.")
