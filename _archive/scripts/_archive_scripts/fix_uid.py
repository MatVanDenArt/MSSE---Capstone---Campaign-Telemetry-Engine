import sys
with open('simulate_journeys.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace("(counts['ga4'], counts['mc'], uid))", "(counts['ga4'], counts['mc'], uid, uid))")

with open('simulate_journeys.py', 'w', encoding='utf-8') as f:
    f.write(content)
