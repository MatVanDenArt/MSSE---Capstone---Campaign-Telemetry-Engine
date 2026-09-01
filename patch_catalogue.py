import json

path = 'app/data/pipeline/content_catalogue.json'
with open(path, 'r') as f:
    data = json.load(f)

for cmp, assets in data.items():
    cmp_prefix = cmp.replace('CMP_', '').lower()
    clean_name = cmp_prefix.replace('_', ' ').title()
    
    if "DECARBONIZATION" in cmp:
        assets.extend([
            {'url': f'email-{cmp_prefix}-1', 'title': f'Email: Q1 Emissions Digest', 'asset_type': 'Email', 'intent_topic': 'Emissions Reduction'},
            {'url': f'email-{cmp_prefix}-2', 'title': f'Email: Webinar Invitation - Carbon Capture', 'asset_type': 'Email', 'intent_topic': 'Carbon Capture (CCUS)'},
            {'url': f'email-{cmp_prefix}-3', 'title': f'Email: Feature - Shell Flaring Case Study', 'asset_type': 'Email', 'intent_topic': 'Emissions Reduction'}
        ])
        assets.extend([
            {'url': f'li-ad-{cmp_prefix}-1', 'title': f'LinkedIn Promo: Energy Optimization Report', 'asset_type': 'LinkedIn Ad', 'intent_topic': 'Asset Optimization'},
            {'url': f'li-ad-{cmp_prefix}-2', 'title': f'LinkedIn Promo: CCUS ROI Calculator', 'asset_type': 'LinkedIn Ad', 'intent_topic': 'Carbon Capture (CCUS)'},
            {'url': f'li-ad-{cmp_prefix}-3', 'title': f'LinkedIn Promo: Automating EPA Compliance', 'asset_type': 'LinkedIn Ad', 'intent_topic': 'Regulatory Compliance'}
        ])
    else:
        # Add Emails
        assets.extend([
            {'url': f'email-{cmp_prefix}-1', 'title': f'Email: {clean_name} Newsletter', 'asset_type': 'Email', 'intent_topic': 'General Engineering'},
            {'url': f'email-{cmp_prefix}-2', 'title': f'Email: Upcoming Webinar Invitation', 'asset_type': 'Email', 'intent_topic': 'General Engineering'},
            {'url': f'email-{cmp_prefix}-3', 'title': f'Email: Case Study Feature', 'asset_type': 'Email', 'intent_topic': 'General Engineering'}
        ])
        
        # Add LinkedIn Ads
        assets.extend([
            {'url': f'li-ad-{cmp_prefix}-1', 'title': f'LinkedIn Promo: Download Our Latest Report', 'asset_type': 'LinkedIn Ad', 'intent_topic': 'General Engineering'},
            {'url': f'li-ad-{cmp_prefix}-2', 'title': f'LinkedIn Promo: ROI Calculator', 'asset_type': 'LinkedIn Ad', 'intent_topic': 'General Engineering'},
            {'url': f'li-ad-{cmp_prefix}-3', 'title': f'LinkedIn Promo: Connect with our Experts', 'asset_type': 'LinkedIn Ad', 'intent_topic': 'General Engineering'}
        ])

with open(path, 'w') as f:
    json.dump(data, f, indent=2)
print('Catalogue updated')
