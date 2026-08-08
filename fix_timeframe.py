with open('simulate_journeys.py', 'r', encoding='utf-8') as f:
    content = f.read()

old_burst = '''    if "PAST" in campaign:
        camp_start = START_DATE + timedelta(days=random.randint(0, 90))
    else:
        camp_start = START_DATE + timedelta(days=random.randint(180, 270))'''

new_burst = '''    if "PAST" in campaign:
        camp_start = START_DATE + timedelta(days=random.randint(0, 90))
    elif "DECARBONIZATION" in campaign:
        camp_start = END_DATE - timedelta(days=180) # Exactly 6 months
    else:
        camp_start = END_DATE - timedelta(days=random.randint(90, 270))'''

content = content.replace(old_burst, new_burst)

with open('simulate_journeys.py', 'w', encoding='utf-8') as f:
    f.write(content)
