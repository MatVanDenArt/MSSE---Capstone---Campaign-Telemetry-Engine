import sqlite3
import os

DB_PATH = "capstone.db"

def get_asset_impact_matrix(campaign_id: str, timeframe: int = 90) -> list:
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = f"""
        WITH AssetDrops AS (
            -- Web Assets
            SELECT 
                'Web' as type,
                page_viewed as asset_name,
                MIN(timestamp) as release_date,
                COUNT(*) as engagement,
                'ga4' as source
            FROM ga4_events 
            WHERE utm_campaign = '{campaign_id}' AND timestamp >= datetime('now', '-{timeframe} days')
            GROUP BY page_viewed
            
            UNION ALL
            
            -- LinkedIn Ads
            SELECT 
                'LinkedIn' as type,
                ad_id as asset_name,
                MIN(timestamp) as release_date,
                COUNT(*) as engagement,
                'linkedin' as source
            FROM linkedin_events
            WHERE campaign_id = '{campaign_id}' AND timestamp >= datetime('now', '-{timeframe} days')
            GROUP BY ad_id
            
            UNION ALL
            
            -- Mailchimp Emails
            SELECT
                'Email' as type,
                campaign_id as asset_name,
                MIN(timestamp) as release_date,
                COUNT(*) as engagement,
                'mailchimp' as source
            FROM mailchimp_events
            WHERE campaign_id LIKE '%{campaign_id}%' AND action = 'Open' AND timestamp >= datetime('now', '-{timeframe} days')
            GROUP BY campaign_id
        )
        SELECT * FROM AssetDrops ORDER BY release_date ASC
        """
        cursor.execute(query)
        assets = [dict(row) for row in cursor.fetchall()]
        
        # Calculate Accounts Activated and Pipeline for each
        for a in assets:
            if a['type'] == 'Web':
                q = f"""
                SELECT COUNT(DISTINCT u.account_id) as accts, SUM(o.pipeline_value) as pipe
                FROM crm_users u
                LEFT JOIN crm_opps o ON u.user_id = o.user_id
                WHERE u.user_id IN (
                    SELECT user_id FROM ga4_events WHERE utm_campaign = '{campaign_id}' AND page_viewed = '{a['asset_name']}' AND user_id IS NOT NULL
                )
                """
            elif a['type'] == 'LinkedIn':
                q = f"""
                SELECT COUNT(DISTINCT u.account_id) as accts, SUM(o.pipeline_value) as pipe
                FROM crm_users u
                LEFT JOIN crm_opps o ON u.user_id = o.user_id
                WHERE u.user_id IN (
                    SELECT g.user_id FROM ga4_events g
                    JOIN linkedin_events l ON g.cookie_id = l.click_id
                    WHERE l.ad_id = '{a['asset_name']}' AND g.user_id IS NOT NULL
                )
                """
            elif a['type'] == 'Email':
                q = f"""
                SELECT COUNT(DISTINCT u.account_id) as accts, SUM(o.pipeline_value) as pipe
                FROM crm_users u
                LEFT JOIN crm_opps o ON u.user_id = o.user_id
                WHERE u.email IN (
                    SELECT email FROM mailchimp_events WHERE campaign_id = '{a['asset_name']}'
                )
                """
            
            cursor.execute(q)
            res = cursor.fetchone()
            a['accounts_activated'] = res['accts'] or 0
            a['pipeline_influenced'] = res['pipe'] or 0.0
            
            # Format dates for UI
            a['date'] = str(a['release_date']).split(" ")[0]

        conn.close()
        return assets
    except Exception as e:
        print(f"Error in impact matrix: {e}")
        return []

if __name__ == "__main__":
    print(get_asset_impact_matrix("CMP_LIVE_GASTECH_2026"))
