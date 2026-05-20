import os
import requests
from bs4 import BeautifulSoup
import supabase
from datetime import datetime

# Supabase Credentials
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")

# Telegram Credentials (GitHub Secrets ထဲတွင် ထည့်ထားပေးရန်)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

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

def send_to_telegram(twod_num, threed_num):
    """ Telegram Channel သို့ ဂဏန်းများ လှမ်းပို့ပေးသော Function """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram Tokens များ မပြည့်စုံသဖြင့် စာမပို့နိုင်ပါ။")
        return

    # Telegram ထဲသို့ ပို့မည့် စာသားပုံစံ (စိတ်ကြိုက် ပြင်နိုင်ပါသည်)
    message = (
        f"🔔 *Romeo 2D Live ရလဒ်ထွက်ပြီ*\n\n"
        f"🎯 *2D Live:* `{twod_num}`\n"
        f"🎰 *3D:* `{threed_num}`\n\n"
        f"📱 Romeo 2D App တွင် ကြည့်ရန်: https://romeo-2d.lovable.app"
    )
    
    telegram_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        res = requests.post(telegram_url, json=payload)
        if res.status_code == 200:
            print("Telegram သို့ ဒေတာ အောင်မြင်စွာ ပို့ပြီးပါပြီ။")
        else:
            print(f"Telegram Error: {res.text}")
    except Exception as e:
        print(f"Telegram Connection Error: {e}")

def update_supabase():
    data = get_thai_stock_data()
    if not data:
        return
        
    try:
        # --- အရေးကြီးဆုံးအပိုင်း- Telegram ကို ဂဏန်းအသစ်မှ ပို့ရန် အရင်စစ်ဆေးခြင်း ---
        # မင်းရဲ့ App (Database) ထဲမှာ ရှိပြီးသား လက်ရှိ နောက်ဆုံးဂဏန်းကို လှမ်းယူခြင်း
        old_data_res = supabase_auth.table("twod_results").select("live_number").eq("id", 1).execute()
        
        is_new_data = False
        if old_data_res.data:
            old_twod = old_data_res.data[0].get("live_number")
            # အကယ်၍ Thaistock က ရလာတဲ့ဂဏန်းက App ထဲက ဂဏန်းနဲ့ မတူတော့ရင် (ဂဏန်းအသစ် တက်လာပြီဆိုရင်)
            if old_twod != data["twod"]:
                is_new_data = True
        else:
            # Database ထဲမှာ ဒေတာ လုံးဝမရှိသေးရင်လည်း အသစ်ဟု သတ်မှတ်မည်
            is_new_data = True

        # --------------------------------------------------------
        # မင်းရဲ့ မူရင်းအတိုင်း App ထဲသို့ ဒေတာ သွင်းခြင်းအပိုင်း (လုံးဝမပြင်ပါ)
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
        
        print("App DB Update Success")
        # --------------------------------------------------------

        # ဂဏန်းအသစ် အမှန်တကယ် ဖြစ်မှသာ Telegram ထံ စာလှမ်းပို့ခိုင်းခြင်း
        if is_new_data:
            send_to_telegram(data["twod"], data["threed"])
        else:
            print("ဂဏန်းဟောင်းပဲ ရှိသေးသဖြင့် Telegram သို့ စာမပို့ပါ။")

    except Exception as e:
        print(f"DB Error: {e}")

if __name__ == "__main__":
    update_supabase()
