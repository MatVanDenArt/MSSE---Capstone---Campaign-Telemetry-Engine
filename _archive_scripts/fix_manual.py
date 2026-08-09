import re

with open('app/services/analytics.py', 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace('LEFT JOIN crm_opps o ON u.user_id = o.user_id', 'LEFT JOIN crm_opps o ON u.account_id = o.account_id')
text = text.replace("a['asset_name'] = a['formatted_name']", "a['raw_name'] = a['asset_name']\n            a['asset_name'] = a['formatted_name']")
text = text.replace('def get_asset_fatigue(campaign_id: str) -> list:', 'def get_asset_fatigue(campaign_id: str, timeframe: int = 0) -> list:')

with open('app/services/analytics.py', 'w', encoding='utf-8') as f:
    f.write(text)
print('Applied manual fixes!')
