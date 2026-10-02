import requests
import json
try:
    res = requests.get("http://localhost:8000/events")
    print(json.dumps(res.json(), indent=2))
except Exception as e:
    print(e)