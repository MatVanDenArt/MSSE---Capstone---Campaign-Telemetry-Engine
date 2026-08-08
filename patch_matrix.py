import re

def fix_matrix_timeframe():
    with open('app/services/analytics.py', 'r', encoding='utf-8') as f:
        content = f.read()
        
    # We need to find `def get_asset_impact_matrix`
    # and replace `tf_condition = f">= datetime('now', '-{timeframe} days')" if timeframe > 0 else "IS NOT NULL"`
    # with `tf_condition = "IS NOT NULL"  # Always show all-time impact in the matrix`
    
    old_line = 'tf_condition = f">= datetime(\'now\', \'-{timeframe} days\')" if timeframe > 0 else "IS NOT NULL"'
    new_line = 'tf_condition = "IS NOT NULL"  # Always show all-time impact in the matrix to reflect full asset performance'
    
    if old_line in content:
        content = content.replace(old_line, new_line)
        
        with open('app/services/analytics.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print("Patched successfully.")
    else:
        print("Could not find the line to patch.")

fix_matrix_timeframe()
