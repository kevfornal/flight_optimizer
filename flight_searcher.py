import os
import json
import time
from datetime import datetime, timedelta
from duffel_api import Duffel

# 1. Fetch Environment Variables passed from GitHub Actions
DUFFEL_TOKEN = os.environ.get("DUFFEL_TOKEN")
origin = os.environ.get("ORIGIN", "IAD")
destination = os.environ.get("DESTINATION", "SEZ")
start_date_str = os.environ.get("START_DATE", "2026-09-01")
end_date_str = os.environ.get("END_DATE", "2026-11-01")
min_stay = int(os.environ.get("MIN_STAY", "7"))
max_stay = int(os.environ.get("MAX_STAY", "10"))
max_connections = int(os.environ.get("MAX_CONNECTIONS", "1"))

if not DUFFEL_TOKEN:
    raise ValueError("DUFFEL_TOKEN environment variable is missing!")

# 2. Initialize Duffel API Client
client = Duffel(access_token=DUFFEL_TOKEN)

# 3. Generate Date Ranges
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

# 4. Loop Through Flight Searches
all_offers = []

passengers_list = [
    {"type": "adult"},
    {"type": "adult"},
    {"type": "child", "age": 4},
    {"type": "child", "age": 6}
]
for outbound_date, return_date, nights in date_pairs:
    try:
        offer_request = client.offer_requests.create(
            slices=[
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
        #    passengers=[
		#{
		#	"type": "adult", "type": "adult",
		#	"type": "child", "type": "child"
		#}
	    #],
            cabin_class="economy"
        )

        for offer in offer_request.offers:
            # Calculate highest number of stops across all flight legs
            max_stops = max(len(slice_item.segments) - 1 for slice_item in offer.slices)
            
            if max_stops <= max_connections:
                airline_name = offer.owner.name if offer.owner else "Multiple Airlines"
                
                all_offers.append({
                    "price": float(offer.total_amount),
                    "currency": offer.total_currency,
                    "outbound": outbound_date,
                    "inbound": return_date,
                    "nights": nights,
                    "stops": "Non-stop" if max_stops == 0 else f"{max_stops}-stop",
                    "airline": airline_name
                })

        # Small delay to keep from exceeding API rate limits on big ranges
        time.sleep(0.1)

    except Exception as e:
        print(f"Error for {outbound_date} to {return_date} ({nights} nights): {e}")

# 5. Sort Offers & Export to results.json
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

print(f"Search complete! Saved {len(all_offers)} offers to results.json.")
