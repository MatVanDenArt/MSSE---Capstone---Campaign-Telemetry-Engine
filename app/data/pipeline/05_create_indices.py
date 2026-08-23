import sqlite3
from pathlib import Path

def create_indices():
    print("Creating database indices for optimal read performance...")
    
    # Locate the database file (root of the workspace)
    db_path = Path(__file__).parent.parent.parent.parent / "capstone.db"
    
    if not db_path.exists():
        print(f"[ERROR] Database not found at {db_path}. Ensure ETL pipeline ran first.")
        return
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    indices = [
        "CREATE INDEX IF NOT EXISTS idx_crm_opps_campaign ON crm_opps(utm_campaign);",
        "CREATE INDEX IF NOT EXISTS idx_crm_users_account ON crm_users(account_id);",
        "CREATE INDEX IF NOT EXISTS idx_crm_users_user ON crm_users(user_id);",
        "CREATE INDEX IF NOT EXISTS idx_ga4_events_user ON ga4_events(user_id);",
        "CREATE INDEX IF NOT EXISTS idx_ga4_events_campaign ON ga4_events(utm_campaign);",
        "CREATE INDEX IF NOT EXISTS idx_ga4_events_cookie ON ga4_events(cookie_id);",
        "CREATE INDEX IF NOT EXISTS idx_linkedin_events_campaign ON linkedin_events(campaign_id);",
        "CREATE INDEX IF NOT EXISTS idx_linkedin_events_cookie ON linkedin_events(cookie_id);",
        "CREATE INDEX IF NOT EXISTS idx_mailchimp_events_email ON mailchimp_events(email);",
        "CREATE INDEX IF NOT EXISTS idx_mailchimp_events_campaign ON mailchimp_events(campaign_id);",
        "CREATE INDEX IF NOT EXISTS idx_crm_users_company ON crm_users(company_name);"
    ]
    
    for idx_sql in indices:
        try:
            cursor.execute(idx_sql)
        except Exception as e:
            print(f"Warning on index creation: {e}")
            
    conn.commit()
    conn.close()
    
    print("Indices successfully created.")

if __name__ == "__main__":
    create_indices()
