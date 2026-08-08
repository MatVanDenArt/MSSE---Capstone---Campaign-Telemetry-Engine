def fix_simulate():
    with open('simulate_journeys.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # We just need to insert `seen_campaign_assets = set()` before the loop at the same indentation level
    content = content.replace('        for _ in range(touches):', '        seen_campaign_assets = set()\n        for _ in range(touches):')

    # Update Report block
    old_report = '''                if channel == 'Report':
                    campaign_reports = [k for k in TRANSIENT_BURST_MAP[user_campaign].keys() if '/case-studies/' in k]
                    page = random.choice(campaign_reports) if campaign_reports else random.choice(CORE_WEB)
                    is_core = False
                else:
                    campaign_insights = [k for k in TRANSIENT_BURST_MAP[user_campaign].keys() if '/insights/' in k or '/webinars/' in k]
                    page = random.choice(CORE_WEB + campaign_insights)
                    is_core = page in CORE_WEB'''

    new_report = '''                if channel == 'Report':
                    campaign_reports = [k for k in TRANSIENT_BURST_MAP[user_campaign].keys() if '/case-studies/' in k and k not in seen_campaign_assets]
                    page = random.choice(campaign_reports) if campaign_reports else random.choice(CORE_WEB)
                    if page not in CORE_WEB: seen_campaign_assets.add(page)
                    is_core = page in CORE_WEB
                else:
                    campaign_insights = [k for k in TRANSIENT_BURST_MAP[user_campaign].keys() if ('/insights/' in k or '/webinars/' in k) and k not in seen_campaign_assets]
                    page = random.choice(campaign_insights) if (campaign_insights and random.random() < 0.7) else random.choice(CORE_WEB)
                    if page not in CORE_WEB: seen_campaign_assets.add(page)
                    is_core = page in CORE_WEB'''

    content = content.replace(old_report, new_report)

    # Update Email block
    old_email = '''                campaign_emails = [k for k in TRANSIENT_BURST_MAP[user_campaign].keys() if 'EMAIL' in k]
                if not campaign_emails: continue
                asset = random.choice(campaign_emails)'''

    new_email = '''                campaign_emails = [k for k in TRANSIENT_BURST_MAP[user_campaign].keys() if 'EMAIL' in k and k not in seen_campaign_assets]
                if not campaign_emails: continue
                asset = random.choice(campaign_emails)
                seen_campaign_assets.add(asset)'''

    content = content.replace(old_email, new_email)

    # Update LinkedIn block
    old_li = '''                campaign_ads = [k for k in TRANSIENT_BURST_MAP[user_campaign].keys() if 'LI_AD' in k]
                if not campaign_ads: continue
                ad = random.choice(campaign_ads)'''

    new_li = '''                campaign_ads = [k for k in TRANSIENT_BURST_MAP[user_campaign].keys() if 'LI_AD' in k and k not in seen_campaign_assets]
                if not campaign_ads: continue
                ad = random.choice(campaign_ads)
                seen_campaign_assets.add(ad)'''

    content = content.replace(old_li, new_li)

    with open('simulate_journeys.py', 'w', encoding='utf-8') as f:
        f.write(content)

fix_simulate()
