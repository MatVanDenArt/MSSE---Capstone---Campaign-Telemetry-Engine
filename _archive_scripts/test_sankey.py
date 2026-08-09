import sqlite3

def run():
    conn = sqlite3.connect(r'c:\Users\mpser\Downloads\Quantic\Capstone\capstone.db')
    cursor = conn.cursor()
    
    print("Testing GA4:")
    cursor.execute("SELECT COUNT(*) FROM ga4_events g JOIN crm_users c ON g.user_id = c.user_id")
    print("ga4 count:", cursor.fetchone()[0])
    
    print("Testing LinkedIn:")
    cursor.execute("SELECT COUNT(*) FROM linkedin_events l JOIN crm_users c ON l.user_id = c.user_id")
    print("li count:", cursor.fetchone()[0])
    
    print("Testing Mailchimp:")
    cursor.execute("SELECT COUNT(*) FROM mailchimp_events m JOIN crm_users c ON m.user_id = c.user_id")
    print("mc count:", cursor.fetchone()[0])
    
    cursor.execute("SELECT DISTINCT campaign_id FROM linkedin_events")
    print("campaigns:", cursor.fetchall())

run()
