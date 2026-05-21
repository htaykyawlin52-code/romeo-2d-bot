import os
import requests
import re
import supabase
from datetime import datetime

# Supabase Credentials
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")

# Telegram Credentials
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# Client တိုက်ရိုက်ဆောက်ခြင်း
supabase_auth = supabase.create_client(url, key)

def get_thai_stock_data():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    # thaistock2d.com ဝဘ်ဆိုဒ်မှ တိုက်ရိုက် ရယူခြင်း
    target_url = "https://www.thaistock2d.com/"
    
    try:
        response = requests.get(target_url, headers=headers, timeout=15)
        if response.status_code != 200:
            return None
            
        html_content = response.text
        
        # --- ၁။ 3D အတွက် မူရင်းအတိုင်း ကိန်းသေ ထားခြင်း ---
        threed_value = "387"
        
        # --- ၂။ HTML စာသားထဲမှ ၂ လုံးဂဏန်း (2D Live) ကို တိုက်ရိုက် ရှာဖွေဖြတ်ယူခြင်း ---
        # ဝဘ်ဆိုဒ်ပေါ်တွင် ပေါ်နေသော ဂဏန်းအစစ်ကို စာသားထဲမှ တိုက်ရိုက်ဆွဲထုတ်သည်
        live_2d = "--"
        
        # HTML Tag များအကြားရှိ ၂ လုံးဂဏန်း သန့်သန့်များကို ရှာဖွေခြင်း
        numbers = re.findall(r'>\s*(\d{2})\s*<', html_content)
        
        if numbers:
            # ဝဘ်ဆိုဒ်ထိပ်ဆုံးတွင် ပေါ်လေ့ရှိသော ပထမဆုံး ၂ လုံးဂဏန်း (Live) ကို ယူခြင်း
            live_2d = numbers[0]
                
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
        print("Telegram Tokens များ မပြည့်စုံသဖြင့် สารမပို့နိုင်ပါ။")
        return

    # ဆရာကြီး၏ မူရင်းစာသား ပုံစံအတိုင်း လုံးဝ ပြောင်းလဲခြင်း မရှိပါ
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
        # --- ဆရာကြီး၏ မူရင်း နောက်ဆုံးဂဏန်း စစ်ဆေးချက် ---
        old_data_res = supabase_auth.table("twod_results").select("live_number").eq("id", 1).execute()
        
        is_new_data = False
        if old_data_res.data:
            old_twod = old_data_res.data[0].get("live_number")
            # ဝဘ်ဆိုဒ်ပေါ်တွင် ဒေတာပေါ်လာပြီး ဂဏန်းဟောင်းမဟုတ်မှသာ ပို့မည်
            if old_twod != data["twod"] and data["twod"] != "--":
                is_new_data = True
        else:
            if data["twod"] != "--":
                is_new_data = True

        # --------------------------------------------------------
        # ဆရာကြီး၏ မူရင်းအတိုင်း App (Supabase) ထဲသို့ ဒေတာ သွင်းခြင်းအပိုင်း (လုံးဝမပြင်ပါ)
        supabase_auth.table("threed_results").upsert({
            "id": 1, 
            "threed": data["threed"],
            "created_at": data["fetched_at"]
        }).execute()
        
        supabase_auth.table("twod_results").upsert({
            "id": 1,
            "live_number": data["twod"],
            "updated_at": data["fetched_at"]
        }).execute()
        
        print("App DB Update Success")
        # --------------------------------------------------------

        # ဂဏန်းအသစ် အမှန်တကယ် ပေါ်လာမှသာ Telegram ပို့ခိုင်းခြင်း
        if is_new_data:
            send_to_telegram(data["twod"], data["threed"])
        else:
            print("ဝဘ်ဆိုဒ်တွင် '--' ဖြစ်နေခြင်း သို့မဟုတ် ဂဏန်းဟောင်းဖြစ်သဖြင့် မပို့ပါ။")

    except Exception as e:
        print(f"DB Error: {e}")

if __name__ == "__main__":
    update_supabase()
