Import os
import requests
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
    # BeautifulSoup ဝဘ်ဆိုဒ်ဆွဲမည့်အစား ပိုငြိမ်ပြီး ဒေတာမှန်သည့် တရားဝင် API သို့ တိုက်ရိုက်ပြောင်းလဲခြင်း
    target_url = "https://api.thaistock2d.com/live"
    
    try:
        response = requests.get(target_url, timeout=10)
        if response.status_code != 200:
            return None
            
        api_data = response.json()
        
        # API ထဲမှ Live 2D တန်ဖိုးကို ဆွဲထုတ်ခြင်း
        live_2d = api_data.get("twod", "--")
        
        # 3D အတွက် API ထဲမှ Live တန်ဖိုးအစစ်ကို ယူခြင်း (ဝဘ်ဆိုဒ်တွင် ဂဏန်းအသစ်ထွက်လျှင် ချက်ချင်းလိုက်ပြောင်းမည်၊ မပါက "387")
        live_3d = api_data.get("threed") or api_data.get("3d") or "387"
        
        # ဆရာကြီး၏ မူရင်း return format အတိုင်း ကွက်တိ ပြန်ပေးခြင်း
        return {
            "threed": live_3d,
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

    # Telegram ထဲသို့ ပို့မည့် စာသားပုံစံ (ဆရာကြီး၏ မူရင်းစာသား ပုံစံအတိုင်း လုံးဝ မပြောင်းလဲပါ)
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
            # ဒေတာအလွတ် '--' ဖြစ်မနေမှသာ ပို့ရန်ပါ တစ်ခါတည်း ညှိပေးထားပါသည်
            if old_twod != data["twod"] and data["twod"] != "--":
                is_new_data = True
        else:
            # Database ထဲမှာ ဒေတာ လုံးဝမရှိသေးရင်လည်း အသစ်ဟု သတ်မှတ်မည်
            if data["twod"] != "--":
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
