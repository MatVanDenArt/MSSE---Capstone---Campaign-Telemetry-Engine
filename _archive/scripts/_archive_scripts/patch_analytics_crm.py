def update_analytics():
    with open('app/services/analytics.py', 'r', encoding='utf-8') as f:
        content = f.read()
        
    new_content = content.replace(
        "user_id IN (SELECT user_id FROM ga4_events WHERE utm_campaign = '{campaign_id}')", 
        "utm_campaign = '{campaign_id}'"
    )
    new_content = new_content.replace(
        "user_id IN (SELECT user_id FROM ga4_events WHERE utm_campaign = '{cid}')", 
        "utm_campaign = '{cid}'"
    )
    new_content = new_content.replace(
        "user_id IN (SELECT user_id FROM ga4_events WHERE utm_campaign = ?)", 
        "utm_campaign = ?"
    )

    with open('app/services/analytics.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
        
    print('Updated analytics.py')

update_analytics()
