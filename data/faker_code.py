import csv
import random
import os
from faker import Faker

fake = Faker()
FILE_NAME = "faker_data_10MB.csv"
TARGET_SIZE_MB = 10
TARGET_SIZE_BYTES = TARGET_SIZE_MB * 1024 * 1024

# 1. Define Industry Archetypes to ensure data "makes sense"
# Format: "Industry": (Base Min/Max in $k, Bonus % Range, Hours Range, Equity/RSU Probability)
ARCHETYPES = {
    "Quant Finance": {"base": (160, 350), "bonus": (0.4, 1.5), "hours": (50, 65), "equity": 0.1},
    "Investment Banking": {"base": (120, 220), "bonus": (0.6, 1.2), "hours": (75, 95), "equity": 0.0},
    "Big Tech (FAANG)": {"base": (140, 260), "bonus": (0.1, 0.25), "hours": (35, 45), "equity": 0.9},
    "AI Startup": {"base": (100, 190), "bonus": (0.0, 0.15), "hours": (50, 70), "equity": 1.0},
    "Management Consulting": {"base": (100, 180), "bonus": (0.2, 0.4), "hours": (60, 80), "equity": 0.0},
    "Fintech": {"base": (110, 210), "bonus": (0.1, 0.3), "hours": (40, 55), "equity": 0.5}
}

headers = [
    "id", "industry", "job_title", "base_salary", "bonus_amount", 
    "equity_percent", "signing_bonus", "working_hours", 
    "promotion_possibility", "remote_onsite", "location", "company_name"
]

print(f"🚀 Generating {TARGET_SIZE_MB}MB of logically consistent data...")

with open(FILE_NAME, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(headers)
    
    row_count = 0
    while os.path.getsize(FILE_NAME) < TARGET_SIZE_BYTES:
        # Pick a random industry archetype
        ind_name = random.choice(list(ARCHETYPES.keys()))
        arc = ARCHETYPES[ind_name]
        
        # Calculate consistent financials
        base = random.randint(*arc["base"]) * 1000
        bonus = int(base * random.uniform(*arc["bonus"]))
        hours = random.randint(*arc["hours"])
        
        # Equity is common in startups/tech, rare in banking
        equity = round(random.uniform(0.01, 0.25), 3) if random.random() < arc["equity"] else 0
        
        # Signing bonuses are usually 10-20% of base or zero
        signing = random.choice([0, 0, 10000, 25000, 50000]) if base > 150000 else 0

        row = [
            row_count,
            ind_name,
            fake.job().split('(')[0].strip(), # Get a clean job title
            base,
            bonus,
            equity,
            signing,
            hours,
            random.choice(["Low", "Medium", "High"]),
            random.choice(["Onsite", "Hybrid", "Hybrid", "Remote"]), # Weight toward Hybrid/Onsite
            fake.city(),
            fake.company()
        ]
        
        writer.writerow(row)
        row_count += 1

print(f"✅ Done! Created {FILE_NAME} with {row_count} rows.")
print(f"📁 Final File Size: {os.path.getsize(FILE_NAME) / (1024*1024):.2f} MB")