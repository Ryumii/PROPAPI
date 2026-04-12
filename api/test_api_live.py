"""Quick API integration test against local server."""
import json
import urllib.request

API_KEY = "cs_live_gt7w1vk6-Aw6MvFSUE4EDKvSbxk4q-QdO5WktuI0-Ko"
BASE = "http://localhost:8000"

def api_get(path: str) -> dict:
    req = urllib.request.Request(f"{BASE}{path}", headers={"X-API-Key": API_KEY})
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())

def api_post(path: str, body: dict) -> dict:
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=data,
        headers={"Content-Type": "application/json", "X-API-Key": API_KEY},
        method="POST",
    )
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())

# 1) Health check
print("=== /v1/health ===")
r = api_get("/v1/health")
print(json.dumps(r, indent=2, ensure_ascii=False))
print()

# 2) Inspect (Tokyo Tower)
print("=== POST /v1/land/inspect (Tokyo Tower) ===")
r = api_post("/v1/land/inspect", {
    "lat": 35.6586, "lng": 139.7454,
    "options": {"include_hazard": True, "include_zoning": True}
})
print(json.dumps(r, indent=2, ensure_ascii=False))
print()

# 3) Hazard only
print("=== GET /v1/hazard ===")
r = api_get("/v1/hazard?lat=35.6586&lng=139.7454")
print(json.dumps(r, indent=2, ensure_ascii=False))
print()

# 4) Zoning only
print("=== GET /v1/zoning ===")
r = api_get("/v1/zoning?lat=35.6586&lng=139.7454")
print(json.dumps(r, indent=2, ensure_ascii=False))
print()

# 5) Test with flood risk area (Edogawa-ku, more likely to have flood data)
print("=== POST /v1/land/inspect (Edogawa-ku) ===")
r = api_post("/v1/land/inspect", {
    "lat": 35.7069, "lng": 139.8683,
    "options": {"include_hazard": True, "include_zoning": True}
})
print(json.dumps(r, indent=2, ensure_ascii=False))
