import sys
import os
import aiofiles

# Add project root to sys.path to allow running as script
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from app.graph import app_graph
from app.core.config import settings
import asyncio
from app.api_scraper import scrape_infomapa_api
from app.extractor import extract_data_from_pdf
import json
import requests
from urllib.parse import quote
import re
import shutil

app = FastAPI(title="InfoMapa Scraper API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development, allow all. In production, specify domain.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount data directory to serve images
# Ensure data directory exists
if not os.path.exists("data"):
    os.makedirs("data")
app.mount("/data", StaticFiles(directory="data"), name="data")

import glob
from datetime import datetime

class ScrapeRequest(BaseModel):
    address: str

class HistoryItem(BaseModel):
    filename: str
    address: str
    date: str
    timestamp: float

async def sync_legacy_history(data_dir: str):
    """
    Scans for existing _debug folders and creates corresponding _data.json files
    if they don't exist, to populate history with previous searches.
    """
    try:
        # Find all debug directories
        debug_dirs = glob.glob(os.path.join(data_dir, "*_debug"))
        
        for debug_path in debug_dirs:
            if not os.path.isdir(debug_path):
                continue
                
            dir_name = os.path.basename(debug_path)
            # base_name is dir_name without _debug
            base_name = dir_name.replace("_debug", "")
            json_filename = f"{base_name}_data.json"
            json_path = os.path.join(data_dir, json_filename)
            
            # Check if JSON exists
            should_regenerate = False
            if not os.path.exists(json_path):
                should_regenerate = True
            else:
                # Check if it's empty/broken
                try:
                    async with aiofiles.open(json_path, mode='r', encoding='utf-8') as f:
                        content = await f.read()
                        existing_data = json.loads(content)
                        # If lots_data is empty but lots exist in folder, regenerate
                        if not existing_data.get("lots_data") and os.path.exists(os.path.join(debug_path, "lots")):
                             files = glob.glob(os.path.join(debug_path, "lots", "*.png"))
                             if files:
                                 print(f"Detected incomplete history for {base_name}, regenerating...")
                                 should_regenerate = True
                except:
                    should_regenerate = True

            # If JSON doesn't exist or is broken, create it from artifacts
            if should_regenerate:
                print(f"Recovering legacy search: {base_name}")
                
                # Infer address
                address = base_name.replace("_", " ").strip()
                
                # Timestamp from folder
                timestamp = os.path.getmtime(debug_path)
                date_str = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
                
                # Images
                map_screenshot_path = os.path.join(data_dir, f"{base_name}_map.png")
                full_map_path = os.path.join(debug_path, "full_map.jpg")
                
                map_screenshot_url = transform_path_to_url(map_screenshot_path) if os.path.exists(map_screenshot_path) else None
                image_url = transform_path_to_url(full_map_path) if os.path.exists(full_map_path) else None
                
                # Lots
                lots_data = []
                lots_dir = os.path.join(debug_path, "lots")
                if os.path.exists(lots_dir):
                    lot_files = sorted(glob.glob(os.path.join(lots_dir, "*.png")))
                    lots_dir_url = transform_path_to_url(lots_dir)
                    for lf in lot_files:
                        fname = os.path.basename(lf)
                        
                        # Extract lot number from filename (e.g. lote_005.png -> 5)
                        lot_num = "?"
                        match = re.search(r"lote_(\d+)", fname)
                        if match:
                            try:
                                lot_num = str(int(match.group(1)))
                            except:
                                pass
                                
                        lots_data.append({
                            "filename": fname,
                            "image_url": f"{lots_dir_url}/{fname}",
                            "lot_number": lot_num,
                            "dimensions": [],
                            "other_text": "Datos recuperados"
                        })
                
                session_data = {
                    "address": address,
                    "timestamp": timestamp,
                    "date": date_str,
                    "metadata": {"Note": "Legacy import"}, # Metadata lost unless re-parsed
                    "map_screenshot_url": map_screenshot_url,
                    "image_url": image_url,
                    "global_info": {},
                    "lots_data": lots_data
                }
                
                async with aiofiles.open(json_path, mode='w', encoding='utf-8') as f:
                    await f.write(json.dumps(session_data, indent=2, ensure_ascii=False))
                    
    except Exception as e:
        print(f"Error syncing legacy history: {e}")

@app.get("/history", response_model=list[HistoryItem])
async def get_history():
    """List all saved searches."""
    history = []
    data_dir = "data"
    if not os.path.exists(data_dir):
        return []
    
    # Sync legacy folders first
    await sync_legacy_history(data_dir)
        
    # Find all *_data.json files
    files = glob.glob(os.path.join(data_dir, "*_data.json"))
    
    for f in files:
        try:
            filename = os.path.basename(f)
            # Read minimal info or just use filename/mtime
            # Let's read the file to get the real address and timestamp
            async with aiofiles.open(f, mode='r', encoding='utf-8') as file:
                content = await file.read()
                data = json.loads(content)
                
            history.append({
                "filename": filename,
                "address": data.get("address", filename.replace("_data.json", "").replace("_", " ")),
                "date": data.get("date", datetime.fromtimestamp(os.path.getmtime(f)).strftime("%Y-%m-%d %H:%M")),
                "timestamp": data.get("timestamp", os.path.getmtime(f))
            })
        except Exception as e:
            print(f"Error reading history file {f}: {e}")
            
    # Sort by timestamp desc
    history.sort(key=lambda x: x["timestamp"], reverse=True)
    return history

@app.get("/history/{filename}")
async def get_history_item(filename: str):
    """Get details of a specific saved search."""
    filepath = os.path.join("data", filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="History item not found")
        
    try:
        async with aiofiles.open(filepath, mode='r', encoding='utf-8') as file:
            content = await file.read()
            return json.loads(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/history/{filename}")
async def delete_history_item(filename: str):
    """Delete a saved search."""
    filepath = os.path.join("data", filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="History item not found")
        
    try:
        # 1. Delete JSON
        os.remove(filepath)
        
        # 2. Determine base name
        # filename is like "ADDRESS_data.json"
        base_name = filename.replace("_data.json", "")
        
        # 3. Delete debug directory
        debug_dir = os.path.join("data", f"{base_name}_debug")
        if os.path.exists(debug_dir):
            shutil.rmtree(debug_dir)
            
        # 4. Delete map screenshot if exists (legacy or new structure)
        map_img = os.path.join("data", f"{base_name}_map.png")
        if os.path.exists(map_img):
            os.remove(map_img)

        # 5. Delete PDF if exists
        pdf_file = os.path.join("data", f"{base_name}.pdf")
        if os.path.exists(pdf_file):
            os.remove(pdf_file)
            
        return {"status": "success", "message": "Deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/proxy/locations/{query}")
async def proxy_locations(query: str):
    """
    Proxy request to Rosario API to avoid CORS issues and improve stability.
    """
    if len(query) < 3:
        return {"features": []}
        
    try:
        # Construct the official API URL
        encoded_query = quote(query)
        url = f"https://ws.rosario.gob.ar/ubicaciones/public/geojson/ubicaciones/all/all/{encoded_query}"
        
        # Make the request from the server side
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"features": [], "error": f"Upstream API error: {response.status_code}"}
            
    except Exception as e:
        print(f"Error proxying location request: {e}")
        return {"features": [], "error": str(e)}

@app.websocket("/ws/scrape")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Receive address from client
            data = await websocket.receive_text()
            
            # Parse input (JSON or String)
            address = ""
            coordinates = None
            try:
                parsed = json.loads(data)
                if isinstance(parsed, dict):
                    address = parsed.get("address", "")
                    coordinates = parsed.get("coordinates")
                else:
                    address = str(parsed)
            except:
                address = data

            await websocket.send_json({"status": "started", "message": f"Iniciando búsqueda para {address}..."})
            
            # Prepare session data for saving
            session_data = {
                "address": address,
                "timestamp": datetime.now().timestamp(),
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "metadata": {},
                "map_screenshot_url": None,
                "image_url": None,
                "global_info": {},
                "lots_data": []
            }
            
            try:
                # 1. Scrape (API Version)
                await websocket.send_json({"status": "progress", "message": "Consultando API Oficial..."})
                
                # We do this manually instead of using graph to control flow
                output_dir = "data"
                if not os.path.exists(output_dir):
                    os.makedirs(output_dir)
                    
                # Use API scraper instead of Playwright
                scrape_result = await scrape_infomapa_api(address, output_dir, coordinates)
                
                if not scrape_result.get("pdf_path"):
                     error_msg = scrape_result.get("error", "No se pudo descargar el plano.")
                     await websocket.send_json({"status": "error", "message": error_msg})
                     continue
                     
                # Send screenshot URL immediately
                screenshot_url = transform_path_to_url(scrape_result.get("screenshot_path"))
                
                # Update session data
                session_data["metadata"] = scrape_result.get("metadata", {})
                session_data["map_screenshot_url"] = screenshot_url
                
                await websocket.send_json({
                    "status": "map_ready", 
                    "screenshot_url": screenshot_url,
                    "metadata": scrape_result.get("metadata")
                })
                
                # 2. Extract (Streaming)
                await websocket.send_json({"status": "progress", "message": "Procesando plano y detectando lotes..."})
                
                async def progress_callback(event_type: str, event_data: any):
                    # Transform paths to URLs in event data
                    if event_type == "lots_found":
                        # Convert file names to full URLs
                        debug_dir = event_data.get("debug_dir")
                        files = event_data.get("files", [])
                        lots_dir_url = transform_path_to_url(os.path.join(debug_dir, "lots"))
                        
                        lot_urls = []
                        for f in files:
                            lot_obj = {
                                "filename": f,
                                "image_url": f"{lots_dir_url}/{f}",
                                "lot_number": "?",
                                "dimensions": [],
                                "other_text": ""
                            }
                            lot_urls.append(lot_obj)
                            # Add to session data (initial)
                            session_data["lots_data"].append(lot_obj)
                        
                        await websocket.send_json({
                            "status": "lots_found",
                            "lots": lot_urls
                        })
                        
                    elif event_type == "lot_data":
                         # Single lot extracted
                         # Update session data
                         for i, lot in enumerate(session_data["lots_data"]):
                             if lot["filename"] == event_data["filename"]:
                                 session_data["lots_data"][i].update(event_data)
                                 break
                                 
                         await websocket.send_json({
                             "status": "lot_update",
                             "data": event_data
                         })
                         
                    elif event_type == "global_info":
                        session_data["global_info"] = event_data
                        await websocket.send_json({
                            "status": "global_info",
                            "data": event_data
                        })
                    
                    elif event_type == "full_map":
                        full_map_url = transform_path_to_url(event_data.get("path"))
                        session_data["image_url"] = full_map_url
                        await websocket.send_json({
                            "status": "full_map_ready",
                            "image_url": full_map_url
                        })

                # Call extractor with callback
                extract_result = await extract_data_from_pdf(
                    scrape_result["pdf_path"], 
                    target_lot=scrape_result.get("metadata", {}).get("lote"),
                    progress_callback=progress_callback
                )
                
                if extract_result.get("error"):
                     await websocket.send_json({"status": "error", "message": extract_result["error"]})
                else:
                     # Save session data to JSON
                     try:
                         # Sanitize address for filename
                         safe_address = "".join([c if c.isalnum() or c in (' ', '-', '_') else '_' for c in address]).strip().replace(' ', '_')
                         filename = f"{safe_address}_data.json"
                         filepath = os.path.join("data", filename)
                         
                         async with aiofiles.open(filepath, mode='w', encoding='utf-8') as f:
                             await f.write(json.dumps(session_data, indent=2, ensure_ascii=False))
                             
                         print(f"Saved session data to {filepath}")
                     except Exception as save_err:
                         print(f"Error saving session data: {save_err}")

                     await websocket.send_json({"status": "complete", "message": "Proceso finalizado con éxito."})

            except Exception as e:
                await websocket.send_json({"status": "error", "message": str(e)})
                
    except WebSocketDisconnect:
        print("Client disconnected")

def transform_path_to_url(path: str) -> str:
    """Converts a local file path to a URL served by FastAPI."""
    if not path:
        return None
        
    # Normalize path separators
    path = path.replace("\\", "/")
    
    # Check if it's already a relative URL or absolute path inside data
    if "/data/" in path:
        # Extract everything after /data/
        parts = path.split("/data/")
        if len(parts) > 1:
            return f"/data/{parts[-1]}"
            
    # Fallback for simple filenames in root data
    if os.path.basename(path) == path:
         return f"/data/{path}"
         
    return path

@app.post("/scrape")
async def scrape_address(request: ScrapeRequest):
    """
    Scrapes the InfoMapa website for the given address, downloads the PDF,
    and extracts data using LLM.
    """
    initial_state = {
        "address": request.address,
        "pdf_path": None,
        "extracted_data": None,
        "error": None
    }
    
    # Run the graph
    result = await app_graph.ainvoke(initial_state)
    
    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])
        
    extracted_data = result["extracted_data"]
    
    # Post-process to fix image URLs
    if extracted_data:
        # Fix main image path
        if "image_path" in extracted_data:
            extracted_data["image_url"] = transform_path_to_url(extracted_data["image_path"])
        
        # Include screenshot URL if available
        if "screenshot_path" in result and result["screenshot_path"]:
             extracted_data["map_screenshot_url"] = transform_path_to_url(result["screenshot_path"])

        # Fix lots data image paths (we need to know where they are)
        # The lots_data usually contains filenames, we need full URLs.
        # But wait, extractor.py returns "lots_data" which is a list of dicts.
        # It has "filename" inside extract_single_lot_data (added by me).
        # We need to construct the full URL for each lot.
        
        debug_dir = extracted_data.get("debug_dir")
        if debug_dir and "lots_data" in extracted_data:
            lots_dir_url = transform_path_to_url(os.path.join(debug_dir, "lots"))
            for lot in extracted_data["lots_data"]:
                if "filename" in lot:
                    lot["image_url"] = f"{lots_dir_url}/{lot['filename']}"
        
    return {
        "status": "success",
        "data": extracted_data,
        "pdf_path": result["pdf_path"]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
