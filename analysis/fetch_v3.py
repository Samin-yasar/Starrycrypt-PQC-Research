#!/usr/bin/env python3
"""
StarryCrypt-PQC Fetch Telemetry v3 Data
Fetches all benchmark records from benchmark_sessions_v3 and exports them to a CSV.
"""

import os
import sys
import json
import csv
import urllib.request
from datetime import datetime

SUPABASE_URL = "https://bcwdpzwsgirhgojkroga.supabase.co"
ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJjd2RwendzZ2lyaGdvamtyb2dhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzc0OTk0MDcsImV4cCI6MjA5MzA3NTQwN30.t8l5kvMDGoSzUuJTmNrKwm-jhFOl6vU23TN1wzN4b_o"

def fetch_all_records():
    headers = {
        "apikey": ANON_KEY,
        "Authorization": f"Bearer {ANON_KEY}",
        "Content-Type": "application/json"
    }
    
    all_records = []
    limit = 1000
    offset = 0
    
    print("Fetching records from Supabase...", flush=True)
    while True:
        url = f"{SUPABASE_URL}/rest/v1/benchmark_sessions_v3?select=*&order=created_at.asc&limit={limit}&offset={offset}"
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                if not data:
                    break
                all_records.extend(data)
                print(f"  Fetched {len(all_records)} records so far...", flush=True)
                if len(data) < limit:
                    break
                offset += limit
        except Exception as e:
            print(f"Error fetching data: {e}", file=sys.stderr)
            sys.exit(1)
            
    return all_records

def main():
    records = fetch_all_records()
    if not records:
        print("No records found in benchmark_sessions_v3 table.", file=sys.stderr)
        return

    # Ensure output directory exists
    out_dir = "performance_data"
    os.makedirs(out_dir, exist_ok=True)
    
    date_str = datetime.now().strftime("%Y-%m-%d")
    out_filename = os.path.join(out_dir, f"starrycrypt_telemetry_v3_{date_str}.csv")
    
    # Get header from the keys of the first record, ensuring sorted order or sensible order
    fieldnames = list(records[0].keys())
    
    # Write to CSV
    print(f"Writing {len(records)} records to {out_filename}...", flush=True)
    try:
        with open(out_filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in records:
                # Format JSONB arrays/objects as string if they are dicts/lists
                formatted_row = {}
                for k, v in row.items():
                    if isinstance(v, (dict, list)):
                        formatted_row[k] = json.dumps(v)
                    else:
                        formatted_row[k] = v
                writer.writerow(formatted_row)
        print("Done!", flush=True)
    except Exception as e:
        print(f"Error writing CSV file: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
