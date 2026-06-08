import os
import requests
import supabase
from datetime import datetime

# Supabase Credentials
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")

# Telegram Credentials
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# Htay API Key (GitHub Secrets မှ လှမ်းယူခြင်း)
API_KEY = os.environ.get("API_KEY")

# Client ဆောက်ခြင်း
supabase_auth = supabase.create_client(url, key)

def get_thai_stock_data():
    # Htay API ရဲ့ 2D Live ဒေတာယူမည့် URL လိပ်စာအသစ်
    target_url = "https://htayapi.com/twod/thai/2dlive"
    
    if not API_KEY:
        print("Error: API_KEY ကို GitHub Secrets တွင် ရှာမတွေ့ပါ။")
        return None

    # Htay API သတ်မှတ်ချက်အရ Header ထဲတွင် သော့အချုပ်ကို ထည့်သွင်းခြင်း
    headers = {
        "X-HTAYAPI-KEY": API_KEY
    }
    
    try:
        response = requests.get(target_url, headers=headers, timeout=20)
        if response.status_code != 200:
            print(f"API Error Status Code: {response.status_code}")
            return None
        
        api_data = response.json()
        if not api_data:
            return None
            
        # Htay API ရဲ့ JSON ပုံစံအတိုင်း ဒေတာများ ဆွဲထုတ်ခြင်း
        # Htay API တွင် live_2d အတွက် 'twod_value' သို့မဟုတ် 'twod' ကို သုံးလေ့ရှိသည်
        live_2d = api_data.get("twod_value") or api_data.get("twod") or "--"
        
        # 3D အတွက် ဒေတာ (မပါလာပါက default အဟောင်းအတိုင်း ထားသည်)
        live_3d = api_data.get("threed") or api_data.get("3d") or "387"
        
        return {
            "threed": live_3d,
            "twod": live_2d,
            "fetched_at": datetime.now().isoformat()
        }
    except Exception as e:
        print(f"Scrape Error: {e}")
        return None

def send_to_telegram(twod_num, threed_num):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return

    message = (
        f"🔔 *Romeo 2D Live ရလဒ်ထွက်ပြီ*\n\n"
        f"🎯 *2D Live:* `{twod_num}`\n"
        f"🎰 *3D:* `{threed_num}`\n\n"
        f"📱 Romeo 2D App တွင် ကြည့်ရန်: https://romeo-2d.lovable.app"
    )
    
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage", json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram Error: {e}")

def update_supabase():
    data = get_thai_stock_data()
    if not data:
        print("API မှ ဒေတာမရပါ၊ ကျော်သွားပါသည်။")
        return
        
    try:
        old_data_res = supabase_auth.table("twod_results").select("live_number").eq("id", 1).execute()
        
        is_new_data = False
        if old_data_res.data:
            old_twod = old_data_res.data[0].get("live_number")
            if old_twod != data["twod"] and data["twod"] != "--":
                is_new_data = True
        else:
            if data["twod"] != "--":
                is_new_data = True

        # Database သွင်းခြင်း
        supabase_auth.table("threed_results").upsert({"id": 1, "threed": data["threed"], "created_at": data["fetched_at"]}).execute()
        supabase_auth.table("twod_results").upsert({"id": 1, "live_number": data["twod"], "updated_at": data["fetched_at"]}).execute()
        
        if is_new_data:
            send_to_telegram(data["twod"], data["threed"])
        
    except Exception as e:
        print(f"DB Update Error: {e}")

if __name__ == "__main__":
    update_supabase()
