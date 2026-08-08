def check_lines():
    with open('app/templates/components/mod_audience_journey.html', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    for i, line in enumerate(lines):
        if 'id="network-container"' in line or 'Network Graph' in line or 'User Cards' in line or 'Audience User Journey' in line or '<!-- Network Graph -->' in line or '<!-- User Cards -->' in line:
            print(f'{i}: {line.strip()}')

check_lines()
