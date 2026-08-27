import re

def rewrite_logic():
    with open('app/services/analytics.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # The block we are replacing starts with 'if total_recent == 0 and prior_count == 0:'
    # and ends at 'a['sparkline_color'] = color'
    
    # We will use regex to replace this entire block.
    pattern = r'if total_recent == 0 and prior_count == 0:[\s\S]*?a\[\'sparkline_color\'\] = color'
    
    new_logic = """# Context-Aware Logic based on Asset Type
            health = ""
            badge = ""
            rec = None
            color = "#10b981" # default to healthy emerald
            
            if a['type'] == 'Web':
                if total_recent == 0 and prior_count == 0:
                    health = "Inactive"
                    badge = "bg-slate-800 text-slate-400 border-slate-700"
                    color = "#334155" # slate-700
                elif total_recent < prior_count * 0.5:
                    health = "Fatigued"
                    badge = "bg-rose-900/30 text-rose-400 border-rose-800/30"
                    rec = "AI Recommendation: Traffic dropping rapidly. Refresh page content or feature this page in the next email newsletter to reactivate intent."
                    color = "#f43f5e" # rose-500
                else:
                    health = "Healthy"
                    badge = "bg-emerald-900/30 text-emerald-400 border-emerald-800/30"
                    
            elif a['type'] == 'LinkedIn':
                if total_recent == 0 and prior_count > 0:
                    health = "Ended"
                    badge = "bg-slate-800 text-slate-400 border-slate-700"
                    color = "#475569" # slate-600
                elif total_recent == 0 and prior_count == 0:
                    health = "Inactive"
                    badge = "bg-slate-800 text-slate-400 border-slate-700"
                    color = "#334155"
                elif total_recent < prior_count * 0.5:
                    health = "Ad Fatigue"
                    badge = "bg-amber-900/30 text-amber-400 border-amber-800/30"
                    rec = "AI Recommendation: Audience fatigue detected. Rotate ad creatives or shift budget to a better-performing channel."
                    color = "#f59e0b" # amber-500
                else:
                    health = "Healthy"
                    badge = "bg-emerald-900/30 text-emerald-400 border-emerald-800/30"
                    
            else: # Email
                # Emails are point-in-time drops. Once sent, they are historical.
                health = "Completed"
                badge = "bg-slate-800 text-slate-400 border-slate-700"
                color = "#475569"
                
            a['health'] = health
            a['badge_class'] = badge
            a['ai_recommendation'] = rec
            a['sparkline_color'] = color"""
            
    new_content = re.sub(pattern, new_logic, content)
    
    with open('app/services/analytics.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
        
rewrite_logic()
