import os
import time
import json
import requests
import aiofiles
from bs4 import BeautifulSoup
from pyproj import Transformer
from datetime import datetime

# Initialize Transformer
# EPSG:4326 (WGS84) -> EPSG:22185 (Campo Inchauspe / Argentina 4)
transformer = Transformer.from_crs("EPSG:4326", "EPSG:22185", always_xy=True)

async def scrape_infomapa_api(address: str, output_dir: str, coordinates: list = None) -> dict:
    """
    Scrapes InfoMapa using direct API calls instead of browser automation.
    """
    print(f"Starting API scrape for: {address}")
    
    # 1. Resolve Coordinates
    lat, lng = None, None
    x, y = None, None
    
    if coordinates:
        lng, lat = coordinates
        print(f"Using provided coordinates: {lat}, {lng}")
    else:
        # Fallback: Geocode using the official proxy endpoint logic
        # We can call the same logic we use in main.py or just request it here
        print("Geocoding address...")
        try:
            geo_url = f"https://ws.rosario.gob.ar/ubicaciones/public/geojson/ubicaciones/all/all/{address}"
            geo_res = requests.get(geo_url, timeout=5)
            if geo_res.status_code == 200:
                data = geo_res.json()
                if data.get("features"):
                    # Take first result
                    feature = data["features"][0]
                    coords = feature.get("geometry", {}).get("coordinates")
                    if coords:
                        lng, lat = coords
                        print(f"Geocoded to: {lat}, {lng}")
        except Exception as e:
            print(f"Geocoding failed: {e}")

    if not lat or not lng:
        return {"error": "No se pudieron obtener las coordenadas para la dirección."}

    # 2. Transform Coordinates to EPSG:22185
    # Check if coordinates are already projected (large numbers) or WGS84 (small numbers)
    # Rosario is approx Lat -32, Lng -60.
    # Projected X/Y are in millions (5,000,000 / 6,000,000)
    
    try:
        # If coordinates are "small" (likely degrees), transform them
        if abs(lng) < 180 and abs(lat) < 90:
             x, y = transformer.transform(lng, lat)
             print(f"Transformed coordinates (from WGS84 to EPSG:22185): X={x}, Y={y}")
        else:
             # Already projected?
             # Note: The API usually returns [X, Y] or [Lng, Lat]. 
             # If we received [6354791, 5438662], we need to be careful about X vs Y order.
             # EPSG:22185 X is Easting (~5.4M), Y is Northing (~6.3M)
             # If val1 > val2, typically Y > X in this region (6.3M > 5.4M)
             val1 = lng
             val2 = lat
             
             if val1 > 6000000 and val2 < 6000000:
                 y = val1
                 x = val2
             elif val2 > 6000000 and val1 < 6000000:
                 y = val2
                 x = val1
             else:
                 # Fallback
                 x, y = lng, lat
                 
             print(f"Using coordinates as-is (assumed EPSG:22185): X={x}, Y={y}")
             
    except Exception as e:
        return {"error": f"Error transformando coordenadas: {e}"}

    # 3. Get PDF Links (Cartobase)
    # POST https://infomapa.rosario.gov.ar/emapa/direccion/cartobase.htm
    # Body: punto_x=...&punto_y=...
    
    pdf_path = None
    pdf_filename = None
    
    try:
        carto_url = "https://infomapa.rosario.gov.ar/emapa/direccion/cartobase.htm"
        carto_data = {"punto_x": x, "punto_y": y}
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        print("Requesting Cartobase info...")
        res = requests.post(carto_url, data=carto_data, headers=headers, timeout=10)
        
        if res.status_code == 200:
            try:
                data = res.json()
            except json.JSONDecodeError:
                print(f"Failed to parse JSON. Response text: {res.text[:200]}")
                # Sometimes it returns text/html error
                return {"error": "El servidor municipal devolvió una respuesta inválida (posiblemente coordenadas incorrectas)."}

            # Response is a list of objects in JSON
            # [{"registro_grafico":[{"link":"/emapa/servlets/verArchivo?path=manzanas/01278.pdf","clave":"Registro Gráfico 01-278"}], ...}]
            
            if isinstance(data, list) and len(data) > 0:
                info = data[0]
                rg = info.get("registro_grafico", [])
                if rg:
                    pdf_link = rg[0].get("link")
                    if pdf_link:
                        # Download PDF
                        full_pdf_url = f"https://infomapa.rosario.gov.ar{pdf_link}"
                        print(f"Found PDF URL: {full_pdf_url}")
                        
                        pdf_res = requests.get(full_pdf_url, stream=True, timeout=15)
                        if pdf_res.status_code == 200:
                            # Save PDF
                            safe_address = address.replace(" ", "_").replace("/", "-")
                            pdf_filename = f"{safe_address}.pdf"
                            pdf_path = os.path.join(output_dir, pdf_filename)
                            
                            with open(pdf_path, 'wb') as f:
                                for chunk in pdf_res.iter_content(chunk_size=8192):
                                    f.write(chunk)
                            print(f"PDF saved to {pdf_path}")
                        else:
                            print(f"Failed to download PDF: {pdf_res.status_code}")
    except Exception as e:
        print(f"Error fetching PDF: {e}")

    # 4. Get Lot Info (GetFeatureInfo)
    # URL structure from HAR
    # We need to build a WMS GetFeatureInfo URL
    # We use a small BBOX around the point
    
    metadata = {
        "Latitud": str(lat),
        "Longitud": str(lng),
        "X": str(x),
        "Y": str(y)
    }
    
    try:
        # Create a small bbox (e.g., 10 meters around)
        delta = 1
        bbox = f"{x-delta},{y-delta},{x+delta},{y+delta}"
        
        wms_url = "https://infomapa.rosario.gov.ar/wms/planobase"
        params = {
            "SERVICE": "WMS",
            "VERSION": "1.1.1",
            "REQUEST": "GetFeatureInfo",
            "LAYERS": "parcelas",
            "QUERY_LAYERS": "parcelas",
            "STYLES": "",
            "BBOX": bbox,
            "FEATURE_COUNT": "10",
            "HEIGHT": "101",
            "WIDTH": "101",
            "FORMAT": "image/jpeg",
            "INFO_FORMAT": "text/html",
            "SRS": "EPSG:22185",
            "X": "50", # Center of 101x101
            "Y": "50"
        }
        
        print("Requesting Feature Info...")
        wms_res = requests.get(wms_url, params=params, headers=headers, timeout=10)
        
        if wms_res.status_code == 200:
            # Parse HTML
            soup = BeautifulSoup(wms_res.text, 'html.parser')
            rows = soup.find_all('tr')
            for row in rows:
                cols = row.find_all('td')
                if len(cols) == 2:
                    key = cols[0].get_text(strip=True).replace(":", "")
                    val = cols[1].get_text(strip=True)
                    if key and val:
                        metadata[key] = val
                        
            print("Metadata extracted:", metadata)
            
    except Exception as e:
        print(f"Error fetching feature info: {e}")

    # 5. Get Map Screenshot (GetMap)
    # We can fetch a static image from WMS
    screenshot_path = None
    try:
        # BBOX for screenshot (approx 200m radius?)
        # 1 unit in EPSG 22185 is approx 1 meter
        radius = 200
        bbox_map = f"{x-radius},{y-radius},{x+radius},{y+radius}"
        
        map_params = {
            "SERVICE": "WMS",
            "VERSION": "1.1.1",
            "REQUEST": "GetMap",
            "LAYERS": "planobase:plano_base,manzanas,parcelas,nombres_de_calles,numeracion_de_calles",
            "STYLES": "",
            "BBOX": bbox_map,
            "WIDTH": "800",
            "HEIGHT": "600",
            "FORMAT": "image/png",
            "SRS": "EPSG:22185"
        }
        
        print("Downloading map screenshot...")
        map_res = requests.get(wms_url, params=map_params, headers=headers, timeout=10)
        
        if map_res.status_code == 200:
            screenshot_filename = f"{address.replace(' ', '_')}_map.png"
            screenshot_path = os.path.join(output_dir, screenshot_filename)
            with open(screenshot_path, 'wb') as f:
                f.write(map_res.content)
            print(f"Map screenshot saved to {screenshot_path}")
            
    except Exception as e:
        print(f"Error fetching map screenshot: {e}")

    return {
        "pdf_path": pdf_path,
        "screenshot_path": screenshot_path,
        "metadata": metadata,
        "global_info": {}, # Can be populated from metadata if needed
        "lots_data": [] # Can be populated if we parse multiple lots
    }
