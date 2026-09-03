import os
import json
import time
import requests
from datetime import datetime, timedelta

# 1. Load Environment Variables from GitHub Actions
DUFFEL_TOKEN = os.environ.get("DUFFEL_TOKEN")
origin = os.environ.get("ORIGIN", "IAD")
destination = os.environ.get("DESTINATION", "MRU")
start_date_str = os.environ.get("START_DATE", "2026-10-23")
end_date_str = os.environ.get("END_DATE", "2026-12-20")
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
    {"type": "child"},
    {"type": "child"}
]

all_offers = []
url = "https://api.duffel.com/air/offer_requests"

# 5. Query Duffel REST Endpoint Directly for each Date Pair
for outbound_date, return_date, nights in date_pairs:
    payload = {
        "data": {
            "slices": [
                {"origin": origin, "destination": destination, "departure_date": outbound_date},
                {"origin": destination, "destination": origin, "departure_date": return_date}
            ],
            "passengers": passengers_payload,
            "cabin_class": "economy",
            "max_connections": max_connections
        }
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code != 201:
            print(f"Error querying {outbound_date} to {return_date}: {response.text}")
            continue

        res_data = response.json().get("data", {})
        offers = res_data.get("offers", [])

        for offer in offers:
    slices = offer.get("slices", [])
    
    outbound_segments = slices[0].get("segments", []) if len(slices) >= 1 else []
    inbound_segments = slices[1].get("segments", []) if len(slices) >= 2 else []

    # Accurate calculation of stops based on segments
    out_stops = max(0, len(outbound_segments) - 1) + sum(len(s.get("stops", [])) for s in outbound_segments)
    in_stops = max(0, len(inbound_segments) - 1) + sum(len(s.get("stops", [])) for s in inbound_segments)
    max_journey_stops = max(out_stops, in_stops)

    if max_journey_stops <= max_connections:
        # Build Outbound Segment Chain (Leg 1)
        out_flights = []
        for seg in outbound_segments:
            # Read exact origin and destination for THIS specific segment
            seg_origin = seg.get("origin", {}).get("iata_code", "")
            seg_dest = seg.get("destination", {}).get("iata_code", "")
            
            carrier = seg.get("operating_carrier", {}).get("iata_code") or seg.get("marketing_carrier", {}).get("iata_code") or ""
            f_num = seg.get("operating_carrier_flight_number") or seg.get("marketing_carrier_flight_number") or ""
            dep_time = seg.get("departing_at", "")[11:16]
            arr_time = seg.get("arriving_at", "")[11:16]
            
            out_flights.append(f"{carrier}{f_num} [{seg_origin} {dep_time} ➔ {seg_dest} {arr_time}]")

        # Build Inbound Segment Chain (Leg 2)
        in_flights = []
        for seg in inbound_segments:
            seg_origin = seg.get("origin", {}).get("iata_code", "")
            seg_dest = seg.get("destination", {}).get("iata_code", "")
            
            carrier = seg.get("operating_carrier", {}).get("iata_code") or seg.get("marketing_carrier", {}).get("iata_code") or ""
            f_num = seg.get("operating_carrier_flight_number") or seg.get("marketing_carrier_flight_number") or ""
            dep_time = seg.get("departing_at", "")[11:16]
            arr_time = seg.get("arriving_at", "")[11:16]
            
            in_flights.append(f"{carrier}{f_num} [{seg_origin} {dep_time} ➔ {seg_dest} {arr_time}]")

        owner = offer.get("owner", {})
        airline_name = owner.get("name") if owner else "Multiple Airlines"

        all_offers.append({
            "price": float(offer.get("total_amount", 0)),
            "currency": offer.get("total_currency", "USD"),
            "outbound": outbound_date,
            "inbound": return_date,
            "nights": nights,
            "stops": "Non-stop" if max_journey_stops == 0 else f"{max_journey_stops}-stop",
            "airline": airline_name,
            "outbound_route": " ➔ ".join(out_flights),
            "inbound_route": " ➔ ".join(in_flights)
        })
        
        # Be mindful of rate limits
        time.sleep(0.5)

    except Exception as e:
        print(f"Exception encountered for {outbound_date} -> {return_date}: {e}")

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
