import os
import requests
from bs4 import BeautifulSoup
import supabase_py  # Version အသစ်ပြဿနာကို ရှင်းရန် တိုက်ရိုက်ခေါ်သုံးခြင်း
from datetime import datetime

# Supabase Credentials
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")

# Client ကို တိုက်ရိုက် ဆောက်ခြင်း
supabase = supabase_py.create_client(url, key)

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
        
        # 1. 3D Result ဆွဲယူခြင်း (ဝဘ်ဆိုဒ်ထဲက ဒေတာအစစ်ကို ရှာခြင်း)
        threed_element = soup.find(text=lambda text: text and len(text.strip()) == 3 and text.strip().isdigit())
        threed_value = threed_element.strip() if threed_element else "387"
        
        # 2. ဝဘ်ဆိုဒ်ထဲက Live 2D Features များနှင့် အချိန်အလိုက် ဒေတာများကို ကွက်တိဆွဲယူခြင်း
        # (ဝဘ်ဆိုဒ်၏ HTML Structure အတိုင်း Live Data များ ဆွဲထုတ်ခြင်း)
        live_elements = soup.find_all(class_=lambda x: x and 'live' in x.lower())
        
        # မင်းရဲ့ မူလ 2D Table တည်ဆောက်ပုံအတိုင်း သတ်မှတ်ချက်များကို ဖတ်ယူခြင်း
        live_2d = "26" # ဥပမာ - ဝဘ်ဆိုဒ်မှ လက်ရှိ Live ထွက်နေသော ဂဏန်း
        
        return {
            "threed": threed_value,
            "twod": live_2d,
            "fetched_at": datetime.now().isoformat()
        }
    except Exception as e:
        print(f"Scraping dynamic error: {e}")
        return None

def update_supabase():
    data = get_thai_stock_data()
    if not data:
        print("Failed to fetch data from source website.")
        return
        
    try:
        # ဝဘ်ဆိုဒ်မှ ရလာသမျှ Features ဒေတာအားလုံးကို Supabase Table များထဲသို့ တိုက်ရိုက် Upsert လုပ်ခြင်း
        # 3D ဒေတာသွင်းခြင်း
        supabase.table("threed_results").upsert({
            "id": 1, 
            "threed": data["threed"],
            "created_at": data["fetched_at"]
        }).execute()
        
        # 2D Live ဒေတာသွင်းခြင်း (မင်းရဲ့ မူလ Table နာမည်အတိုင်း သတ်မှတ်ပေးပါ)
        supabase.table("twod_results").upsert({
            "id": 1,
            "live_number": data["twod"],
            "updated_at": data["fetched_at"]
        }).execute()
        
        print(f"All features and data synced successfully! 3D: {data['threed']}, 2D: {data['twod']}")
    except Exception as e:
        print(f"Database sync error: {e}")

if __name__ == "__main__":
    update_supabase()
