# Flight Search Optimizer ✈️

An automated multi-date flight search matrix generator and pricing optimizer built using the Duffel API. This tool scans flexible date ranges across multiple airline carriers to identify optimal routing, price anomalies, and cost-effective travel itineraries.

---

## 🌟 Key Features

* **Multi-Date Matrix Scanning:** Evaluates prices across flexible departure/return windows to uncover hidden flight deals.
* **Carrier Aggregation:** Connects directly via the Duffel REST API to query real-time flight offers across major international and domestic airlines.
* **Smart Route Optimization:** Filters and ranks itineraries by price, layover duration, and overall travel time score.
* **Automated Data Export:** Outputs search results into structured JSON or clean Markdown/Excel matrices for fast comparison.

---

## 🛠️ Tech Stack & Requirements

* **Language:** Python 3.10+
* **API Integration:** Duffel Flight Search API (`duffel-api` or `requests`)
* **Data Processing:** `pandas`
* **Configuration:** `python-dotenv`

---

## 🚀 Step-by-Step Setup & Installation

### 1. Clone the Repository
```bash
git clone [https://github.com/](https://github.com/)<your-username>/flight-search-optimizer.git
cd flight-search-optimizer
