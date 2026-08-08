import re

def fix_analytics():
    with open('app/services/analytics.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # LinkedIn bug: WHERE l.ad_id = '{a['asset_name']}' AND g.user_id IS NOT NULL AND l.timestamp {tf_condition}
    old_li_sql = "WHERE l.ad_id = '{a['asset_name']}' AND g.user_id IS NOT NULL AND l.timestamp {tf_condition}"
    new_li_sql = "WHERE l.ad_id = '{a['asset_name']}' AND l.campaign_id = '{campaign_id}' AND g.user_id IS NOT NULL AND l.timestamp {tf_condition}"
    
    if old_li_sql in content:
        content = content.replace(old_li_sql, new_li_sql)
        print("Patched LinkedIn Individuals query.")

    # Email bug: WHERE url_clicked = '{a['asset_name']}' AND user_id IS NOT NULL AND timestamp {tf_condition}
    old_mc_sql = "WHERE url_clicked = '{a['asset_name']}' AND user_id IS NOT NULL AND timestamp {tf_condition}"
    new_mc_sql = "WHERE url_clicked = '{a['asset_name']}' AND campaign_id LIKE '%{campaign_id}%' AND user_id IS NOT NULL AND timestamp {tf_condition}"
    
    if old_mc_sql in content:
        content = content.replace(old_mc_sql, new_mc_sql)
        print("Patched Email Individuals query.")

    with open('app/services/analytics.py', 'w', encoding='utf-8') as f:
        f.write(content)

fix_analytics()
