import requests
import json

BASE_URL = "http://127.0.0.1:5555/api/dashboard"

def test_endpoint(name, path, method="GET", data=None):
    url = f"{BASE_URL}{path}"
    print(f"Testing {name:.<20} {url:.<45}", end=" ")
    try:
        if method == "GET":
            r = requests.get(url)
        else:
            r = requests.post(url, json=data)
        
        if r.status_code == 404:
            print("❌ 404 NOT FOUND")
        elif r.status_code == 200:
            print(f"✅ 200 OK")
        else:
            print(f"⚠️ {r.status_code} {r.text[:50]}")
    except Exception as e:
        print(f"💀 CONNECTION FAILED: {e}")

if __name__ == "__main__":
    print("\n🔍 STARTING API ROUTE AUDIT\n" + "="*80)
    test_endpoint("Status", "/status")
    test_endpoint("Pending Summary", "/pending-summary")
    test_endpoint("Audit Full", "/audit/full")
    test_endpoint("History", "/history/2026-01-28")
    
    # Testing Close Day (Logic might fail if date is wrong, but 404 means route is missing)
    test_endpoint("Close Day", "/close-day", method="POST", data={"date": "2026-01-30"})
    print("="*80 + "\n")
