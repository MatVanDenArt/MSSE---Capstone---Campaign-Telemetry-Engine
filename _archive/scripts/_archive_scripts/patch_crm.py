import sqlite3
import random
import pandas as pd

conn = sqlite3.connect('capstone.db')
c = conn.cursor()

# Get all users
users = pd.read_sql('SELECT * FROM crm_users', conn)

# Identify 50% of users to move to the long tail (SMBs)
# Keep the C-Suite and VPs mostly in Tier 1, move ICs and Managers to SMBs
num_to_move = int(len(users) * 0.5)

# Generate 250 unique small company names
adj = ["Advanced", "Dynamic", "Global", "Sustainable", "Precision", "Nexus", "Eco", "Future", "Integrated", "Quantum"]
nouns = ["Engineering", "Energy", "Solutions", "Dynamics", "Technologies", "Consulting", "Partners", "Group", "Services", "Industries"]
smb_names = []
for i in range(250):
    smb_names.append(f"{random.choice(adj)} {random.choice(nouns)} {random.choice(['LLC', 'Ltd', 'Inc', 'Co.'])}")

smb_names = list(set(smb_names))
while len(smb_names) < 250:
    smb_names.append(f"{random.choice(adj)} {random.choice(nouns)} {random.choice(['LLC', 'Ltd', 'Inc', 'Co.'])}")
smb_names = list(set(smb_names))[:250]

# Give each SMB a unique account_id starting from 100
smb_mapping = {name: 100 + i for i, name in enumerate(smb_names)}

users_to_update = users.sample(n=num_to_move, random_state=42)

for index, user in users_to_update.iterrows():
    new_company = random.choice(smb_names)
    new_account_id = smb_mapping[new_company]
    
    c.execute(
        "UPDATE crm_users SET company_name = ?, account_id = ? WHERE user_id = ?",
        (new_company, new_account_id, int(user['user_id']))
    )

conn.commit()
conn.close()

print(f"Successfully moved {num_to_move} CRM users to 250 unique SMB accounts.")
