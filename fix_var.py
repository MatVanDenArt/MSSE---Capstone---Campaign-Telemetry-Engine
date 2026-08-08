import re

def fix_capture_val():
    with open('simulate_journeys.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # Move capture_val = None outside the channel check
    old_code = """                capture_val = None
                if not captured_identity and random.random() < 0.10:
                    capture_val = uid
                    captured_identity = True
                
                ga4_events.append({"""
                
    new_code = """                if not captured_identity and random.random() < 0.10:
                    capture_val = uid
                    captured_identity = True
                
                ga4_events.append({"""
                
    content = content.replace(old_code, new_code)
    
    # And put capture_val = None right below `for _ in range(touches):`
    # Actually wait, `channel = random.choices` is right below it
    content = content.replace("        for _ in range(touches):\n            channel = random.choices", "        for _ in range(touches):\n            capture_val = None\n            channel = random.choices")
    
    with open('simulate_journeys.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Fixed capture_val scoping issue.")

fix_capture_val()
