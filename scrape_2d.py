import os
import requests
from supabase import create_client, Client
from datetime import datetime

# Environment Variables များ ရယူခြင်း
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_KEY")
API_KEY = os.environ.get("API_KEY")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# Supabase Client တည်ဆောက်ခြင်း
supabase: Client = create_client(url, key)

def check_and_save_holidays():
    """ထိုင်းစတော့ဈေးကွက် ပိတ်ရက် ဟုတ်/မဟုတ် စစ်ဆေးပြီး ပိတ်ရက်ဇယားထဲ သိမ်းဆည်းခြင်း"""
    today_str = datetime.now().strftime("%Y-%m-%d")
    holiday_url = f"https://htayapi.com/twod/thai/2dholiday?key={API_KEY}"
    
    try:
        response = requests.get(holiday_url)
        if response.status_code == 200:
            holidays_list = response.json()
            if isinstance(holidays_list, list):
                for holiday in holidays_list:
                    h_date = holiday.get("date")
                    h_title = holiday.get("title")
                    
                    if h_date:
                        supabase.table("thai_holidays").upsert({
                            "holiday_date": h_date,
                            "title": h_title
                        }, on_conflict="holiday_date").execute()
                        
                        if h_date == today_str:
                            return True
    except Exception as e:
        print(f"⚠️ Holiday API စစ်ဆေးရာတွင် အမှားရှိခဲ့သည်: {e}")
        
    try:
        check_db = supabase.table("thai_holidays").select("*").eq("holiday_date", today_str).execute()
        return len(check_db.data) > 0
    except Exception as db_e:
        print(f"⚠️ DB Holiday စစ်ဆေးရခက်ခဲနေသည်: {db_e}")
        return False

def save_vip_numbers():
    """Daily နှင့် Weekly VIP ဂဏန်းများ ရယူသိမ်းဆည်းခြင်း"""
    today_str = datetime.now().strftime("%Y-%m-%d")
    
    # ၁။ Daily VIP
    try:
        daily_url = f"https://htayapi.com/twod/thai/vipnumbers?key={API_KEY}"
        d_res = requests.get(daily_url)
        if d_res.status_code == 200 and d_res.json():
            daily_data = d_res.json()
            special = daily_data.get("special", "")
            normal = daily_data.get("normal", "")
            
            supabase.table("daily_vip_numbers").upsert({
                "vip_date": today_str,
                "special_numbers": str(special) if special else "",
                "normal_numbers": str(normal) if normal else ""
            }, on_conflict="vip_date").execute()
            print("⭐ Daily VIP ဂဏန်းများ သိမ်းဆည်းပြီးပါပြီ။")
    except Exception as e:
        print(f"⚠️ Daily VIP ရယူရာတွင် အမှားရှိသည်: {e}")

    # ၂။ Weekly VIP
    try:
        weekly_url = f"https://htayapi.com/twod/thai/weeklyvipnumbers?key={API_KEY}"
        w_res = requests.get(weekly_url)
        if w_res.status_code == 200 and w_res.json():
            weekly_data = w_res.json()
            week_range = weekly_data.get("week", today_str)
            vip_nums = weekly_data.get("numbers", "")
            
            supabase.table("weekly_vip_numbers").upsert({
                "week_range": str(week_range),
                "vip_numbers": str(vip_nums) if vip_nums else ""
            }, on_conflict="week_range").execute()
            print("📆 Weekly VIP ဂဏန်းများ သိမ်းဆည်းပြီးပါပြီ။")
    except Exception as e:
        print(f"⚠️ Weekly VIP ရယူရာတွင် အမှားရှိသည်: {e}")

def send_to_telegram(twod_num, threed_num):
    """Telegram သို့ အကြောင်းကြားစာပေးပို့ခြင်း"""
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
        print("🚀 Telegram ထံသို့ Notification ပို့ပြီးပါပြီ။")
    except Exception as e:
        print(f"⚠️ Telegram Error: {e}")

def save_live_and_internet_results():
    """မူလ App စနစ်မပြတ်တောက်စေရန် မူလပုံစံအတိုင်း ရလဒ်များအား Upsert လုပ်ပြီး သိမ်းဆည်းခြင်း"""
    today_str = datetime.now().strftime("%Y-%m-%d")
    current_hour_minute = datetime.now().strftime("%H:%M")
    fetched_at_iso = datetime.now().isoformat()
    
    session = "12:30"
    if "09:00" <= current_hour_minute <= "11:45": session = "11:00"
    elif "11:46" <= current_hour_minute <= "14:00": session = "12:30"
    elif "14:01" <= current_hour_minute <= "15:45": session = "03:00"
    elif "15:46" <= current_hour_minute <= "18:00": session = "04:30"

    live_2d = "--"
    live_3d = "387"
    set_price_val = ""

    # ၁။ Htay API မှ 2D Live ယူခြင်း
    try:
        live_twod_url = f"https://htayapi.com/twod/thai/2dlive?key={API_KEY}"
        res_2d = requests.get(live_twod_url)
        if res_2d.status_code == 200 and res_2d.json():
            data_2d = res_2d.json()
            live_2d = data_2d.get("twod_value") or data_2d.get("twod") or "--"
            set_price_val = data_2d.get("live_set") or data_2d.get("set") or ""
    except Exception as e:
        print(f"⚠️ 2D Live Fetch Error: {e}")

    # ၂။ Htay API မှ 3D Live ယူခြင်း
    try:
        live_threed_url = f"https://htayapi.com/twod/thai/3dlive?key={API_KEY}"
        res_3d = requests.get(live_threed_url)
        if res_3d.status_code == 200 and res_3d.json():
            data_3d = res_3d.json()
            live_3d = data_3d.get("live_3d") or data_3d.get("threed") or "387"
    except Exception as e:
        print(f"⚠️ 3D Live Fetch Error: {e}")

    # ၃။ မူလ App အတွက် twod_results နှင့် threed_results ကို ပုံစံဟောင်းအတိုင်း (id: 1) ဖြင့် သိမ်းခြင်း
    is_new_data = False
    try:
        old_data_res = supabase.table("twod_results").select("live_number").eq("id", 1).execute()
        if old_data_res.data:
            old_twod = old_data_res.data[0].get("live_number")
            if old_twod != live_2d and live_2d != "--":
                is_new_data = True
        else:
            if live_2d != "--":
                is_new_data = True

        # မူလ Column နာမည်များ (live_number, set_price, threed) အတိုင်း Upsert လုပ်ခြင်း
        supabase.table("threed_results").upsert({"id": 1, "threed": str(live_3d), "created_at": fetched_at_iso}).execute()
        supabase.table("twod_results").upsert({
            "id": 1, 
            "live_number": str(live_2d), 
            "set_price": str(set_price_val),
            "updated_at": fetched_at_iso
        }).execute()
        print("📈 မူလ App အတွက် Live ဒေတာများကို ပုံစံဟောင်းအတိုင်း Update လုပ်ပြီးပါပြီ။")
        
        # ဂဏန်းအသစ်ထွက်လာပါက Telegram သို့ ပို့ခြင်း
        if is_new_data:
            send_to_telegram(live_2d, live_3d)
            
    except Exception as db_e:
        print(f"⚠️ မူလ DB Tables များထံ Update သွင်းရာတွင် အမှားရှိသည်: {db_e}")

    # ၄။ Internet 2D Results နှင့် Modern 2D Results များ သိမ်းဆည်းခြင်း
    try:
        internet_url = f"https://htayapi.com/twod/internet/2d-results?date={today_str}&key={API_KEY}"
        res_int = requests.get(internet_url)
        royal_url = f"https://htayapi.com/twod/royalthai/2d-results?date={today_str}&key={API_KEY}"
        res_roy = requests.get(royal_url)
        
        internet_val = ""
        modern_val = ""
        
        if res_int.status_code == 200 and res_int.json():
            int_json = res_int.json()
            if isinstance(int_json, list):
                for item in int_json:
                    if item.get("time") == session:
                        internet_val = item.get("twod") or item.get("result") or ""
            elif isinstance(int_json, dict):
                internet_val = int_json.get("twod") or ""

        if res_roy.status_code == 200 and res_roy.json():
            roy_json = res_roy.json()
            if isinstance(roy_json, list):
                for item in roy_json:
                    if item.get("time") == session:
                        modern_val = item.get("twod") or item.get("result") or ""
            elif isinstance(roy_json, dict):
                modern_val = roy_json.get("twod") or ""

        supabase.table("internet_modern_results").upsert({
            "result_date": today_str,
            "session_time": session,
            "internet_twod": str(internet_val),
            "modern_twod": str(modern_val)
        }, on_conflict="result_date,session_time").execute()
        print("🌐 Internet & Modern 2D ရလဒ်များ ညှိနှိုင်းသိမ်းဆည်းပြီးပါပြီ။")
        
    except Exception as e:
        print(f"⚠️ Internet/Modern 2D ဆွဲယူရာတွင် အမှားရှိသည်: {e}")

def main():
    print("🤖 --- Romeo 2D Engine စတင်မောင်းနှင်နေပါပြီ ---")
    
    is_holiday = check_and_save_holidays()
    if is_holiday:
        print("❌ [🛑 STOP] ယနေ့သည် ထိုင်းစတော့ဈေးကွက် ပိတ်ရက် (Holiday) ဖြစ်နေပါသည်။")
        print("💡 ဒေတာဘေ့စ် ကြောင်မသွားစေရန် ဒေတာအသစ်ဆွဲခြင်းလုပ်ငန်းစဉ်အားလုံးကို အလိုအလျောက် ရပ်နား (Skip) လိုက်ပါပြီ ဆရာ။")
        return
        
    print("✅ ရုံးဖွင့်ရက်ဖြစ်၍ Htay API မှ Features အသစ်များ စတင်ရယူနေပါသည်...")
    save_vip_numbers()
    save_live_and_internet_results()
    print("🎉 --- လုပ်ငန်းစဉ်အားလုံး အောင်မြင်စွာ ပြီးဆုံးပါပြီ ဆရာ ---")

if __name__ == "__main__":
    main()
