import re

def update_simulation():
    with open('simulate_journeys.py', 'r', encoding='utf-8') as f:
        content = f.read()
        
    # 1. Increase CRM touches
    content = content.replace("touches = random.randint(8, 25)", "touches = random.randint(40, 100)")
    content = content.replace("touches = random.randint(3, 7)", "touches = random.randint(15, 35)")
    content = content.replace("touches = random.randint(0, 2)", "touches = random.randint(2, 10)")

    # 2. Increase Email click rates
    content = content.replace("if rand < 0.05:", "if rand < 0.25:  # Boosted Email Click Rate")
    content = content.replace("elif rand < 0.25:", "elif rand < 0.65:  # Boosted Email Open Rate")

    # 3. Increase LinkedIn ad click chances inside the CRM loop
    # Currently it's random.choices(["Web", "LinkedIn", "Email"], weights=[60, 25, 15])
    # Let's change weights to [40, 45, 15]
    content = content.replace("weights=[60, 25, 15]", "weights=[40, 45, 15]")

    # 4. Increase Anonymous Sessions
    content = content.replace("num_anonymous = 25000", "num_anonymous = 150000")

    with open('simulate_journeys.py', 'w', encoding='utf-8') as f:
        f.write(content)

update_simulation()
