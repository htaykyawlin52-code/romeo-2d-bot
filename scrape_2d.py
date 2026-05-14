import os
import requests
from supabase import create_client
from datetime import datetime

# GitHub Secrets ထဲမှ ဆွဲယူမည်
URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_SERVICE_KEY")
supabase = create_client(URL, KEY)

def run_automation():
    api_url = "https://api.thaistock2d.com/live"
    try:
        response = requests.get(api_url)
        if response.status_code != 200:
            print("API Error")
            return
        
        data = response.json()
        results = data.get("result", [])
        today = datetime.now().strftime("%Y-%m-%d")
        
        for item in results:
            open_time = item.get("open_time")
            
            session_map = {
                "11:00:00": "11:00 AM",
                "12:01:00": "12:01 PM",
                "15:00:00": "3:00 PM",
                "16:30:00": "4:30 PM"
            }
            
            session_name = session_map.get(open_time)
            if not session_name:
                continue

            payload = {
                "result_date": today,
                "set_price": str(item.get("set")),
                "value_price": str(item.get("value")),
                "twod_number": str(item.get("twod")),
                "session_name": session_name,
                "is_closing": open_time in ["12:01:00", "16:30:00"]
            }

            # Database ထဲသို့ ထည့်သွင်းခြင်း
            # မှတ်ချက်: result_date နှင့် session_name ကို Unique Constraint လုပ်ထားရန် လိုသည်
            supabase.table("twod_results").upsert(
                payload, on_conflict="result_date,session_name"
            ).execute()
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    run_automation()
