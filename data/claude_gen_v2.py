import os
import time
from anthropic import Anthropic

# Using the key you provided - Keep this local!
api_key = ""
client = Anthropic(api_key=api_key)

FILE_PATH = "data/market_data_intelligent.csv"
TARGET_SIZE_MB = 2
TARGET_SIZE_BYTES = TARGET_SIZE_MB * 1024 * 1024

def get_claude_batch():
    # Reduced to 60 rows to fit within token limits safely
    prompt = """
    Generate 50 rows of high-fidelity, correlated job offer data in CSV format.
    Columns: id,industry,job_title,company name,company_tier,location,base_salary,bonus_amount,equity_val,signing_bonus,working_hours,years_experience,promotion_possibility,remote_onsite.
    Ensure strict economic corrlation: 
    - Geographic correlation: eg. NYC/SF roles pay 30% more than mid-west cities similar roles; more finance jobs should be at places like NYC and chicago, fitting reality, while less ship-building engineers should work at Utah, where there is no water. 
    - Role correlation: eg. Quant Traders/AI Researchers have massive bonuses compared to Accountants.
    - Company Tier (or stage) Corr: eg. Startups offer 5x more equity than Public companies.
    - Role Pyramid: Generate 34 Entry/Junior, 15 Mid/Senior, and 1 Lead/Exec roles.
    - Industry Realism: eg. Quant Finance roles should have bonuses >50percent of base; Accountants should have <15%." etc. 
    - Any other correlation tat makes sense to you. 
    Output ONLY the CSV rows, no intro text, no backticks, no markdown, no anything else. 
    Note: try to be a bit diverse and creative with the data, but keep it realistic. The goal is to create a dataset that could plausibly be real, with all the right correlations and patterns that exist in the real world.
    """

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text

def run_generator():
    print(f"🚀 Starting Claude Synthesis to {TARGET_SIZE_MB}MB...")
    
    # Ensure the directory exists
    os.makedirs(os.path.dirname(FILE_PATH), exist_ok=True)

    # Correct Header to match your prompt
    header = "id,industry,job_title,company_name,company_tier,location,base_salary,bonus_amount,equity_val,signing_bonus,working_hours,years_experience,promotion_possibility,remote_onsite\n"

    if not os.path.exists(FILE_PATH):
        with open(FILE_PATH, "w", encoding="utf-8") as f:
            f.write(header)

    while os.path.getsize(FILE_PATH) < TARGET_SIZE_BYTES:
        try:
            batch_data = get_claude_batch().strip()
            
            # Filter out any header rows Claude might repeat
            lines = [l for l in batch_data.split('\n') if not l.startswith('id,')]
            clean_data = '\n'.join(lines)
            
            with open(FILE_PATH, "a", encoding="utf-8") as f:
                f.write(clean_data + "\n")
            
            current_size = os.path.getsize(FILE_PATH) / (1024 * 1024)
            print(f"📊 Progress: {current_size:.2f} MB / {TARGET_SIZE_MB} MB")
            
            time.sleep(1)  # Sleep to avoid hitting rate limits
            
        except Exception as e:
            print(f"❌ Error: {e}")
            break

if __name__ == "__main__":
    run_generator()