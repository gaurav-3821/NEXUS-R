import urllib.request
import urllib.error
import json

base_url = "http://localhost:8000/api/v1"
endpoints = [
    ("/memory", "GET"),
    ("/models/status", "GET"),
    ("/models/list-local", "GET"),
    ("/providers", "GET")
]

import os

token = ""
try:
    with open(".nexus_token", "r") as f:
        token = f.read().strip()
except Exception:
    pass

results = []

for endpoint, method in endpoints:
    url = base_url + endpoint + ("?token=" + token if token else "")
    req = urllib.request.Request(url, method=method)
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            results.append({"endpoint": endpoint, "status": response.status, "data": data})
    except urllib.error.URLError as e:
        status = e.code if hasattr(e, 'code') else str(e.reason)
        results.append({"endpoint": endpoint, "status": status, "error": str(e)})

with open("api_test_results.json", "w") as f:
    json.dump(results, f, indent=2)
print("Done testing APIs")
