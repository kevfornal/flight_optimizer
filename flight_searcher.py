import os
import json
import time
import requests
from datetime import datetime, timedelta

# 1. Load Environment Variables from GitHub Actions
DUFFEL_TOKEN = os.environ.get("DUFFEL_TOKEN")
origin = os.environ.get("ORIGIN", "IAD")
destination = os.environ.get("DESTINATION", "SEZ")
start_date_str = os.environ.get("START_DATE", "2026-09-01")
end_date_str = os.environ.get("END_DATE", "2026-11-01")
min_stay = int(os.environ.get("MIN_STAY", "7"))
max_stay = int(os.environ.get("MAX_STAY", "10"))
max_connections = int(os.environ.get("MAX_CONNECTIONS", "2"))

if not DUFFEL_TOKEN:
    raise ValueError("DUFFEL_TOKEN environment variable is missing!")

# 2. Setup Direct API Request Headers (Specifying Duffel API v2)
headers = {
    "Authorization": f"Bearer {DUFFEL_TOKEN}",
    "Duffel-Version": "v2",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

# 3. Generate Search Date Combinations
start_dt = datetime.strptime(start_date_str, "%Y-%m-%d")
end_dt = datetime.strptime(end_date_str, "%Y-%m-%d")

date_pairs = []
curr = start_dt
while curr <= end_dt:
    for stay in range(min_stay, max_stay + 1):
        ret_date = curr + timedelta(days=stay)
        if ret_date <= end_dt + timedelta(days=max_stay):
            date_pairs.append((
                curr.strftime("%Y-%m-%d"),
                ret_date.strftime("%Y-%m-%d"),
                stay
            ))
    curr += timedelta(days=1)

print(f"Generated {len(date_pairs)} date combinations to query.")

# 4. Define Passenger Payload (Duffel requires 'age' for 'child')
passengers_payload = [
    {"type": "adult"},
    {"type": "adult"},
    {"type": "child", "age": 4},
    {"type": "child", "age": 6}
]

all_offers = []
url = "https://api.duffel.com/air/offer_requests"

# 5. Query Duffel REST Endpoint Directly
for outbound_date, return_date, nights in date_pairs:
    payload = {
        "data": {
            "slices": [
                {
                    "origin": origin,
                    "destination": destination,
                    "departure_date": outbound_date
                },
                {
                    "origin": destination,
                    "destination": origin,
                    "departure_date": return_date
                }
            ],
            "passengers": passengers_payload,
            "cabin_class": "economy"
        }
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code == 201:
            data = response.json().get("data", {})
            offers = data.get("offers", [])
            
            for offer in offers:
                # Determine max connections across outbound and inbound legs
                max_stops = max(len(slice_item.get("segments", [])) - 1 for slice_item in offer.get("slices", []))
                
                if max_stops <= max_connections:
                    owner = offer.get("owner", {})
                    airline_name = owner.get("name") if owner else "Multiple Airlines"
                    
                    all_offers.append({
                        "price": float(offer.get("total_amount", 0)),
                        "currency": offer.get("total_currency", "USD"),
                        "outbound": outbound_date,
                        "inbound": return_date,
                        "nights": nights,
                        "stops": "Non-stop" if max_stops == 0 else f"{max_stops}-stop",
                        "airline": airline_name
                    })
        else:
            print(f"Duffel API Error {response.status_code} for {outbound_date}: {response.text}")

        # Sleep briefly to avoid hitting Duffel's request rate limit
        time.sleep(0.15)

    except Exception as e:
        print(f"Request failed for {outbound_date} to {return_date}: {e}")

# 6. Sort & Write Results
all_offers.sort(key=lambda x: x["price"])

output_data = {
    "last_updated": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
    "params": {
        "origin": origin,
        "destination": destination,
        "start_date": start_date_str,
        "end_date": end_date_str
    },
    "offers": all_offers
}

with open("results.json", "w") as f:
    json.dump(output_data, f, indent=2)

print(f"Done! Successfully processed and saved {len(all_offers)} offers to results.json.")
