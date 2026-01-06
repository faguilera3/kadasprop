import requests

base_url = "https://infomapa.rosario.gov.ar/wms/planobase"
layers_to_check = [
    "nombres_de_calles",
    "planobase:normas_urbanisticas",
    "normas_urbanisticas",
    "planobase:semaforos",
    "semaforos",
    "planobase:alumbrado_publico",
    "alumbrado_publico",
    "planobase:agua_potable",
    "agua_potable"
]

params = {
    "SERVICE": "WMS",
    "VERSION": "1.1.0",
    "REQUEST": "GetMap",
    "LAYERS": "", # To be filled
    "STYLES": "",
    "BBOX": "6060000,6360000,6070000,6370000", # Approx coords, actually EPSG:22185 or 4326?
    # Let's use EPSG:4326 bbox for Rosario approx: -33.0, -60.7
    "SRS": "EPSG:4326",
    "BBOX": "-60.7,-33.0,-60.6,-32.9",
    "WIDTH": "256",
    "HEIGHT": "256",
    "FORMAT": "image/png",
    "TRANSPARENT": "TRUE"
}

for layer in layers_to_check:
    p = params.copy()
    p["LAYERS"] = layer
    try:
        r = requests.get(base_url, params=p, timeout=5)
        if r.status_code == 200 and r.headers['Content-Type'].startswith('image'):
            print(f"[OK] Layer '{layer}' exists.")
        else:
            print(f"[FAIL] Layer '{layer}' returned {r.status_code} {r.headers.get('Content-Type')}")
            print(r.content[:500]) # Print first 500 chars
    except Exception as e:
        print(f"[ERR] Layer '{layer}': {e}")
