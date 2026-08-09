import re

def final_sim_patch():
    with open('simulate_journeys.py', 'r', encoding='utf-8') as f:
        content = f.read()
        
    # 1. Update anonymous sessions
    content = content.replace("num_anonymous = 150000", "num_anonymous = 35000")
    if "num_anonymous = 25000" in content:
        content = content.replace("num_anonymous = 25000", "num_anonymous = 35000")

    # 2. Update CRM touches
    content = content.replace("touches = random.randint(40, 100)", "touches = random.randint(12, 25)")
    content = content.replace("touches = random.randint(15, 35)", "touches = random.randint(4, 12)")
    content = content.replace("touches = random.randint(2, 10)", "touches = random.randint(1, 3)")
    
    # Also if the old original touches are still there (in case my previous patch failed or this is a fresh file):
    content = content.replace("touches = random.randint(8, 25)", "touches = random.randint(12, 25)")
    content = content.replace("touches = random.randint(3, 7)", "touches = random.randint(4, 12)")
    content = content.replace("touches = random.randint(0, 2)", "touches = random.randint(1, 3)")

    # 3. Update Bounce Rates
    # Current bounce logic is: "bounce_flag": random.choice([0, 1])
    # We will replace it with dynamic bounce rate logic.
    old_bounce = '"bounce_flag": random.choice([0, 1])'
    new_bounce = '"bounce_flag": 1 if (utm_source == "linkedin" and random.random() < 0.25) or (utm_source != "linkedin" and random.random() < 0.65) else 0'
    content = content.replace(old_bounce, new_bounce)
    
    # Wait, for Known Users, the bounce flag is always 0.
    # In simulate_journeys.py lines 164, 182, 199, 207 it has "bounce_flag": 0, 
    # Let's leave Known Users at 0, that's fine.

    with open('simulate_journeys.py', 'w', encoding='utf-8') as f:
        f.write(content)

final_sim_patch()
