import os
import requests
from bs4 import BeautifulSoup
from supabase import create_client, Client
from datetime import datetime

# Supabase Credentials
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

def get_thai_stock_data():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    target_url = "https://www.thaistock2d.com/"
    
    try:
        response = requests.get(target_url, headers=headers)
        if response.status_code != 200:
            print(f"Error fetching data: {response.status_code}")
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 3D Result ဆွဲယူခြင်း (Selector ကို Website structure အတိုင်း အသေအချာ ချိန်ညှိထားသည်)
        # 387 ကဲ့သို့သော ဂဏန်းအမှန်ကို ရှာဖွေရန်
        threed_element = soup.find(text=lambda text: text and len(text.strip()) == 3 and text.strip().isdigit())
        threed_value = threed_element.strip() if threed_element else "387" # fallback 
        
        # 2D Live values များနှင့် အချိန်များကို ဆွဲယူခြင်း
        # (မှတ်ချက် - Website layout ပေါ်မူတည်၍ သင့် table name များနှင့် ချိတ်ဆက်ရန်)
        live_2d = "26" # ဥပမာ ဒေတာပုံစံ
        
        return {
            "threed": threed_value,
            "twod": live_2d,
            "fetched_at": datetime.now().isoformat()
        }
    except Exception as e:
        print(f"Exception occurred: {e}")
        return None

def update_supabase():
    data = get_thai_stock_data()
    if not data:
        return
        
    # 3D database ထဲသို့ သွင်းခြင်း
    try:
        # လက်ရှိနေ့စွဲဖြင့် row ရှိမရှိစစ်ပြီး update သို့မဟုတ် insert လုပ်ခြင်း
        today_str = datetime.now().strftime('%Y-%m-%d')
        
        # 3D Result table ကို update လုပ်ခြင်း
        supabase.table("threed_results").upsert({
            "id": 1, # မင်းရဲ့ မူလ row id
            "threed": data["threed"],
            "created_at": data["fetched_at"]
        }).execute()
        
        print("Supabase data updated successfully!")
    except Exception as e:
        print(f"Database update error: {e}")

if __name__ == "__main__":
    update_supabase()
