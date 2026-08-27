import re

def fix_naming_bug():
    with open('app/services/analytics.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace all occurrences of replace('/', '') with replace('/', ' ')
    content = content.replace("replace('/', '')", "replace('/', ' ')")
    
    with open('app/services/analytics.py', 'w', encoding='utf-8') as f:
        f.write(content)
        
def fix_chart_bug():
    with open('app/templates/components/timeline.html', 'r', encoding='utf-8') as f:
        content = f.read()
        
    # We want to add suggestedMax to the y-axis in timeline.html
    # Look for: y: { display: false, min: -1 }
    # Replace with: y: { display: false, min: -1, suggestedMax: 10 }
    content = content.replace("y: { display: false, min: -1 }", "y: { display: false, min: -1, suggestedMax: 10 }")
    
    with open('app/templates/components/timeline.html', 'w', encoding='utf-8') as f:
        f.write(content)

fix_naming_bug()
fix_chart_bug()
print("Fixed naming bug and chart bug.")
