import re

def update_analytics():
    with open('app/services/analytics.py', 'r', encoding='utf-8') as f:
        content = f.read()
        
    old_code = """        import urllib.parse
        for a in assets:
            raw_name = a['asset_name']
            if a['type'] == 'Web':
                name = raw_name.replace('/', ' ').replace('-', ' ').title().strip()
                if not name: name = "Homepage"
                a['formatted_name'] = name
            elif a['type'] == 'Email':
                parsed = urllib.parse.urlparse(raw_name)
                qs = urllib.parse.parse_qs(parsed.query)
                if 'utm_campaign' in qs:
                    name = qs['utm_campaign'][0].replace('CMP_', '').replace('LIVE_', '').replace('PAST_', '').replace('_', ' ').title()
                else:
                    name = parsed.path.split('/')[-1].replace('-', ' ').title()
                if not name: name = "Email Link"
                a['formatted_name'] = name
            elif a['type'] == 'LinkedIn':
                name = raw_name.replace("LI_AD_", "").replace("_", " ").title()
                a['formatted_name'] = name
            else:
                a['formatted_name'] = raw_name"""

    new_code = """        import urllib.parse
        for a in assets:
            raw_name = a['asset_name']
            if a['type'] == 'Web':
                parts = [p for p in raw_name.split('/') if p]
                if len(parts) >= 2:
                    subtype = parts[0].replace('-', ' ').title()
                    # special case for grammar
                    if subtype.lower() == 'webinars': subtype = 'Webinar'
                    a['subtype'] = subtype
                    name = " ".join(parts[1:]).replace('-', ' ').title().strip()
                elif len(parts) == 1:
                    a['subtype'] = 'Web Page'
                    name = parts[0].replace('-', ' ').title().strip()
                else:
                    a['subtype'] = 'Web Page'
                    name = "Homepage"
                a['formatted_name'] = name
            elif a['type'] == 'Email':
                a['subtype'] = 'Email Drop'
                parsed = urllib.parse.urlparse(raw_name)
                qs = urllib.parse.parse_qs(parsed.query)
                if 'utm_campaign' in qs:
                    name = qs['utm_campaign'][0].replace('CMP_', '').replace('LIVE_', '').replace('PAST_', '').replace('_', ' ').title()
                else:
                    name = parsed.path.split('/')[-1].replace('-', ' ').title()
                if not name: name = "Email Link"
                a['formatted_name'] = name
            elif a['type'] == 'LinkedIn':
                a['subtype'] = 'Social Ad'
                name = raw_name.replace("LI_AD_", "").replace("_", " ").title()
                a['formatted_name'] = name
            else:
                a['subtype'] = 'Asset'
                a['formatted_name'] = raw_name"""

    if old_code in content:
        content = content.replace(old_code, new_code)
        with open('app/services/analytics.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print("Updated analytics.py successfully.")
    else:
        print("Failed to find the code block in analytics.py.")

def update_timeline():
    with open('app/templates/components/timeline.html', 'r', encoding='utf-8') as f:
        content = f.read()
        
    old_tag = "{{ m.type }} ASSET"
    new_tag = "{{ m.subtype | default(m.type ~ ' ASSET') }}"
    
    if old_tag in content:
        content = content.replace(old_tag, new_tag)
        with open('app/templates/components/timeline.html', 'w', encoding='utf-8') as f:
            f.write(content)
        print("Updated timeline.html successfully.")
    else:
        print("Failed to find the tag in timeline.html.")

update_analytics()
update_timeline()
