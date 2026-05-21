import os
import requests
from bs4 import BeautifulSoup
import supabase
from datetime import datetime, timedelta

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
    # ဆရာကြီး ခိုင်းသည့်အတိုင်း မူရင်း Website ကို တိုက်ရိုက် သုံးခြင်း
    target_url = "https://www.thaistock2d.com/"
    
    try:
        response = requests.get(target_url, headers=headers, timeout=15)
        if response.status_code != 200:
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # --- ၁။ 3D ဂဏန်း မူရင်းအတိုင်း ရှာဖွေခြင်း ---
        threed_element = soup.find(text=lambda text: text and len(text.strip()) == 3 and text.strip().isdigit())
        threed_value = threed_element.strip() if threed_element else "387"
        
        # --- ၂။ လက်ရှိ မြန်မာစံတော်ချိန် အလိုက် မည်သည့်ပွဲစဉ်ဖြစ်ကြောင်း သတ်မှတ်ခြင်း ---
        # (GitHub Server အချိန်ကို မြန်မာစံတော်ချိန် UTC+6:30 သို့ ပြောင်းလဲခြင်း)
        now_mmt = datetime.utcnow() + timedelta(hours=6, minutes=30)
        current_hour_minute = now_mmt.strftime("%H:%M")
        
        target_session = "11:00 AM" # Default အနေဖြင့် ထားခြင်း
        if "10:30" <= current_hour_minute < "11:45":
            target_session = "11:00 AM"
        elif "11:45" <= current_hour_minute < "14:30":
            target_session = "12:01 PM"
        elif "14:30" <= current_hour_minute < "16:00":
            target_session = "03:00 PM"
        elif "16:00" <= current_hour_minute < "18:00":
            target_session = "04:30 PM"

        # --- ၃။ Website ပေါ်က Map/Card ဇယားကွက်ထဲမှ Target အချိန်ကို ရှာဖွေခြင်း ---
        live_2d = "--"
        
        # ဝဘ်ဆိုဒ်ထဲက အချိန်ပြထားတဲ့ Card တွေကို လိုက်ရှာခြင်း
        cards = soup.find_all(['div', 'section'], class_=lambda c: c and any(x in c.lower() for x in ['card', 'session', 'time'])) or soup.find_all(text=lambda t: t and target_session in t)
        
        # ဇယားကွက်စာသားကို ရှာပြီး ၎င်းနှင့်သက်ဆိုင်သည့် ၂ လုံးဂဏန်း (2D) ကို တိုက်ရိုက်ဆွဲထုတ်ခြင်း
        for element in soup.find_all(['div', 'span', 'p']):
            if element.text and target_session in element.text:
                # ၎င်း အချိန်ဇယား Card တစ်ခုလုံး သို့မဟုတ် ၎င်း၏ အနီးနား Parent အိမ်ကို ယူခြင်း
                parent = element.find_parent(['div', 'section']) or element.parent
                if parent:
                    # ၎င်းဇယားကွက်ထဲမှ ၂ လုံးဂဏန်း သို့မဟုတ် '--' ကို ရှာခြင်း
                    for sub in parent.find_all(['span', 'div', 'p', 'h1', 'h2', 'h3']):
                        txt = sub.text.strip()
                        if txt == "--" or (txt.isdigit() and len(txt) == 2):
                            live_2d = txt
                            # အကယ်၍ ဂဏန်းအစစ် တွေ့သွားပါက Loop ကို တန်းရပ်မည်
                            if txt.isdigit():
                                break
                if live_2d != "--":
                    break
        
        # အကယ်၍ အပေါ်က Card စနစ် ရှုပ်ထွေးပြီး ရှာမတွေ့ပါက ပုံမှန် Text စစ်ထုတ်စနစ်ဖြင့် ထပ်မံ အရန်ရှာခြင်း
        if live_2d == "--":
            found_session = False
            for el in soup.find_all(text=True):
                if target_session in el:
                    found_session = True
                if found_session:
                    stripped = el.strip()
                    if stripped.isdigit() and len(stripped) == 2:
                        live_2d = stripped
                        break
                    elif stripped == "--":
                        live_2d = "--"
                        break

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

    # မူရင်း စာသားပုံစံအတိုင်း လုံးဝ ပြောင်းလဲခြင်း မရှိပါ
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
        # --- အရေးကြီးဆုံး စစ်ဆေးချက်- Website ပေါ်က Map ဇယားကွက်ထဲမှာ ဂဏန်းပေါ်မှသာ Telegram ပို့ရန် ---
        old_data_res = supabase_auth.table("twod_results").select("live_number").eq("id", 1).execute()
        
        is_new_data = False
        if old_data_res.data:
            old_twod = old_data_res.data[0].get("live_number")
            
            # စည်းကမ်းချက်- Website ပေါ်က ဇယားကွက်ထဲမှာ '--' မဟုတ်တော့ဘဲ ဂဏန်းအစစ်ပေါ်လာပြီ၊ ပြီးတော့ ဒေတာဟောင်းနဲ့လည်း မတူဘူးဆိုမှ
            if data["twod"] != "--" and old_twod != data["twod"]:
                is_new_data = True
        else:
            if data["twod"] != "--":
                is_new_data = True

        # --------------------------------------------------------
        # မင်းရဲ့ မူရင်းအတိုင်း App ထဲသို့ ဒေတာ သွင်းခြင်းအပိုင်း (လုံးဝမပြင်ပါ)
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

        # သတ်မှတ်ထားသော အချိန်ဇယားကွက်ထဲမှာ ဂဏန်းအသစ်တကယ် ထွက်လာမှသာ Telegram ပို့မည်
        if is_new_data:
            send_to_telegram(data["twod"], data["threed"])
        else:
            print("ဝဘ်ဆိုဒ် ဇယားကွက်ထဲတွင် '--' ဖြစ်နေခြင်း (သို့မဟုတ်) ဂဏန်းဟောင်းဖြစ်နေသဖြင့် Telegram သို့ မပို့ပါ။")

    except Exception as e:
        print(f"DB Error: {e}")

if __name__ == "__main__":
    update_supabase()
