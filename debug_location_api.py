import requests
import json

def test_api():
    url = "https://ws.rosario.gob.ar/ubicaciones/public/geojson/ubicaciones/all/all/ALEM%20LEAN"
    try:
        response = requests.get(url, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type')}")
        
        try:
            data = response.json()
            print("\nResponse structure:")
            print(json.dumps(data, indent=2)[:500] + "...")
        except Exception as e:
            print(f"JSON Error: {e}")
            print("Raw content:", response.content[:200])
            
    except Exception as e:
        print(f"Request Error: {e}")

if __name__ == "__main__":
    test_api()
