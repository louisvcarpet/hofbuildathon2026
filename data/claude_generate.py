import os
import time
from anthropic import Anthropic
import pandas as pd


api_key = ""


client = Anthropic(api_key=api_key)

# Initialize client
client = Anthropic(api_key=api_key)

FILE_PATH = "data/market_data_intelligent.csv"
TARGET_SIZE_MB = 10
TARGET_SIZE_BYTES = TARGET_SIZE_MB * 1024 * 1024

def get_claude_batch():
    prompt = """Generate 500 rows of high-fidelity, correlated job offer data in CSV format.
    Columns: id,industry,job_title,company name,company_tier,location,base_salary,bonus_amount,equity_val,signing_bonus,working_hours,years_experience,promotion_possibility,remote_onsite.
    Ensure strict economic corrlation: 
    - Geographic correlation: eg. NYC/SF roles pay 30% more than mid-west cities similar roles; more finance jobs should be at places like NYC and chicago, fitting reality, while less ship-building engineers should work at Utah, where there is no water. 
    - Role correlation: eg. Quant Traders/AI Researchers have massive bonuses compared to Accountants.
    - Company Tier (or stage) Corr: eg. Startups offer 5x more equity than Public companies.
    - Role Pyramid: Generate 340 Entry/Junior, 150 Mid/Senior, and 10 Lead/Exec roles.
    - Industry Realism: eg. Quant Finance roles should have bonuses >50percent of base; Accountants should have <15%." etc. 
    - Any other correlation tat makes sense to you. 
    Output ONLY the CSV rows, no intro text. Note: try to be a bit diverse and creative with the data, but keep it realistic. The goal is to create a dataset that could plausibly be real, with all the right correlations and patterns that exist in the real world."""

    response = client.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text

def run_generator():
    print(f"🚀 Starting Claude Synthesis to {TARGET_SIZE_MB}MB...")
    
    # Write header if file doesn't exist
    if not os.path.exists(FILE_PATH):
        with open(FILE_PATH, "w") as f:
            f.write("job_title,industry,company_tier,location,base_salary,bonus_pct,equity_val,signing_bonus,years_exp,remote_status\n")

    while os.path.getsize(FILE_PATH) < TARGET_SIZE_BYTES:
        try:
            batch_data = get_claude_batch()
            
            # Clean up the response (remove any backticks if Claude adds them)
            clean_data = batch_data.replace("```csv", "").replace("```", "").strip()
            
            with open(FILE_PATH, "a", encoding="utf-8") as f:
                f.write(clean_data + "\n")
            
            current_size = os.path.getsize(FILE_PATH) / (1024 * 1024)
            print(f"📊 Current Size: {current_size:.2f} MB / {TARGET_SIZE_MB} MB")
            
            # Sleep to avoid Rate Limits (important for Claude Console credits!)
            time.sleep(2) 
            
        except Exception as e:
            print(f"❌ Error: {e}")
            break

if __name__ == "__main__":
    run_generator()