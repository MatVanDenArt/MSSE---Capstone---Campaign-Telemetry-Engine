import pandas as pd
import random
import os
from faker import Faker
from config import TARGET_ACCOUNTS, SENIORITY_LEVELS, OUTPUT_DIR

fake = Faker()
Faker.seed(42)
random.seed(42)

def generate_crm_users():
    print("Generating CRM Users...")
    crm_users = []
    user_id_counter = 1
    
    for account_id, company_name in enumerate(TARGET_ACCOUNTS, start=1):
        domain = company_name.lower().replace(" ", "") + ".com"
        num_users = random.randint(30, 50)
        
        for _ in range(num_users):
            first_name = fake.first_name()
            last_name = fake.last_name()
            email = f"{first_name.lower()}.{last_name.lower()}@{domain}"
            seniority = random.choices(SENIORITY_LEVELS, weights=[5, 15, 30, 50])[0]
            persona_type = random.choices(["Technical", "Commercial"], weights=[60, 40])[0]
            
            crm_users.append({
                "user_id": user_id_counter, 
                "account_id": account_id, 
                "company_name": company_name,
                "email": email, 
                "first_name": first_name, 
                "last_name": last_name, 
                "seniority": seniority, 
                "persona_type": persona_type
            })
            user_id_counter += 1
            
    df = pd.DataFrame(crm_users)
    output_path = os.path.join(OUTPUT_DIR, "crm_users.csv")
    df.to_csv(output_path, index=False)
    print(f"Generated {len(df)} users to {output_path}")

if __name__ == "__main__":
    generate_crm_users()
