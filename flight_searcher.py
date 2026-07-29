import os
import json
import time
from datetime import datetime, timedelta
from duffel_api import Duffel

# --- CONFIGURATION FROM ENV / INPUTS ---
DUFFEL_TOKEN = os.environ.get("DUFFEL_TOKEN")
ORIGIN = os.environ.get("ORIGIN", "IAD")
DESTINATION = os.environ.get("DESTINATION", "SEZ")
START_SEARCH = datetime.strptime(os.environ.get("START_DATE", "2026-09-01"), "%Y-%m-%d").date()
END_SEARCH = datetime.strptime(os.environ.get("END_DATE", "2026-09-10"), "%Y-%m-%d").date()
MIN_STAY = int(os.environ.get("MIN_STAY", 7))
MAX_STAY = int(os.environ.get("MAX_STAY", 10))
# 0 = Direct/Non-stop only, 1 = Up to 1-stop, 2 = Up to 2-stops
MAX_CONNECTIONS = int(os.environ.get("MAX_CONNECTIONS", 1)) 

client = Duffel(access_token=DUFFEL_TOKEN)

def get_daterange(start, end):
    for n in range(int((end - start).days) + 1):
        yield start + timedelta(n)

def search_flights():
    passengers = [{"type": "adult"}, {"type": "adult"}, {"type": "child"}, {"type": "child"}]
    results = []

    print(f"Searching {ORIGIN} -> {DESTINATION} (Max Connections: {MAX_CONNECTIONS})...")

    for depart_date in get_daterange(START_SEARCH, END_SEARCH):
        for nights in range(MIN_STAY, MAX_STAY + 1):
            ret_date = depart_date + timedelta(days=nights)
            
            try:
                # Duffel API supports max_connections parameter directly!
                offer_request = duffel.offer_requests.create(
                    slice=[
                        {"origin": origin, "destination": destination, "outbound_date": depart_date.isoformat()},
                        {"origin": destination, "destination": origin, "return_date": ret_date.isoformat()}
                    ],
                    max_connections=MAX_CONNECTIONS # Filter out multi-stop connections
                ).execute()

                # Access offers directly from the returned OfferRequest object:
                offers = offer_request.offers
                
                if offer_req.offers:
                    # Sort offers prioritizing non-stop (0 stops) first, then price
                    sorted_offers = sorted(
                        offer_req.offers,
                        key=lambda o: (
                            max(len(s.segments) for s in o.slices) - 1, # Connection count priority
                            float(o.total_amount)                       # Price priority
                        )
                    )
                    
                    cheapest = sorted_offers[0]
                    # Calculate total stops across outbound and inbound slices
                    max_stops = max(len(s.segments) - 1 for s in cheapest.slices)

                    results.append({
                        "outbound": depart_date.isoformat(),
                        "inbound": ret_date.isoformat(),
                        "nights": nights,
                        "price": float(cheapest.total_amount),
                        "currency": cheapest.total_currency,
                        "airline": cheapest.owner.name,
                        "stops": "Non-stop" if max_stops == 0 else f"{max_stops}-Stop"
                    })

                time.sleep(0.2)

            except Exception as e:
                print(f"Error for {depart_date} ({nights} nights): {e}")

    # Sort final dataset by price
    sorted_results = sorted(results, key=lambda x: x["price"])

    # Export output data for the frontend to render
    output_data = {
        "last_updated": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "params": {
            "origin": ORIGIN,
            "destination": DESTINATION,
            "start": START_SEARCH.isoformat(),
            "end": END_SEARCH.isoformat(),
            "min_stay": MIN_STAY,
            "max_stay": MAX_STAY
        },
        "offers": sorted_results
    }

    with open("results.json", "w") as f:
        json.dump(output_data, f, indent=2)

if __name__ == "__main__":
    search_flights()
