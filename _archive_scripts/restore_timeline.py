with open('app/templates/components/timeline.html', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("backgroundColor: '#10b981',", "backgroundColor: 'rgba(16, 185, 129, 0.4)',")
content = content.replace("barThickness: 20,", "barThickness: 8,")

with open('app/templates/components/timeline.html', 'w', encoding='utf-8') as f:
    f.write(content)

with open('simulate_journeys.py', 'r', encoding='utf-8') as f:
    sim_content = f.read()

sim_content = sim_content.replace('touches = random.randint(6, 12)', 'touches = random.randint(12, 25)')
sim_content = sim_content.replace('touches = random.randint(3, 5)', 'touches = random.randint(4, 12)')
sim_content = sim_content.replace('touches = random.randint(1, 2)', 'touches = random.randint(1, 3)')

with open('simulate_journeys.py', 'w', encoding='utf-8') as f:
    f.write(sim_content)
