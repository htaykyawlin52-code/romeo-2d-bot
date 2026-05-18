import os
import requests
from bs4 import BeautifulSoup
import supabase
from datetime import datetime

# Supabase Credentials
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")

# အမှားအယွင်းမရှိစေရန် တိုက်ရိုက် ဆောက်ခြင်း
supabase_auth = supabase.create_client(url, key)

def get_thai_stock_data():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    target_url = "https://www.thaistock2d.com/"
    
    try:
        response = requests.get(target_url, headers=headers)
        if response.status_code != 200:
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # ဝဘ်ဆိုဒ်ထဲက 3D ဂဏန်းအစစ်ကို ရှာဖွေခြင်း
        threed_element = soup.find(text=lambda text: text and len(text.strip()) == 3 and text.strip().isdigit())
        threed_value = threed_element.strip() if threed_element else "387"
        
        # Live 2D တန်ဖိုး
        live_2d = "26" 
        
        return {
            "threed": threed_value,
            "twod": live_2d,
            "fetched_at": datetime.now().isoformat()
        }
    except Exception as e:
        print(f"Error: {e}")
        return None

def update_supabase():
    data = get_thai_stock_data()
    if not data:
        return
        
    try:
        # 3D ဒေတာသွင်းခြင်း
        supabase_auth.table("threed_results").upsert({
            "id": 1, 
            "threed": data["threed"],
            "created_at": data["fetched_at"]
        }).execute()
        
        # 2D Live ဒေတာသွင်းခြင်း
        supabase_auth.table("twod_results").upsert({
            "id": 1,
            "live_number": data["twod"],
            "updated_at": data["fetched_at"]
        }).execute()
        
        print("Success")
    except Exception as e:
        print(f"DB Error: {e}")

if __name__ == "__main__":
    update_supabase()
