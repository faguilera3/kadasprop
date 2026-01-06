import base64
import io
import json
import os
import cv2
import fitz  # PyMuPDF
import asyncio
from typing import Dict, Any, List, Callable, Awaitable
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from app.core.config import settings
from app.image_utils import load_image_from_bytes, encode_image_to_bytes
# Import external segmentation script
from segmentacion.extractor_lotes import process_cadastral_map

# Initialize LLM
llm = ChatOpenAI(model="gpt-5-nano", api_key=settings.OPENAI_API_KEY)

def encode_image(image_bytes):
    return base64.b64encode(image_bytes).decode('utf-8')

async def extract_single_lot_data(image_bytes: bytes, lot_filename: str) -> Dict[str, Any]:
    """Extracts data from a single lot crop using LLM."""
    base64_image = encode_image(image_bytes)
    
    prompt_text = f"""
    Analyze this single lot crop from a cadastral map. 
    Filename reference: {lot_filename}
    
    Extract all visible text inside this lot boundary:

    1. Lot Number:
    - Identify the main lot number (usually a large number like 1, 2, 3, 14, etc.).
    - If there is a smaller number immediately adjacent to or visually attached to the main lot number, include it
    as a superscript (e.g., 17 with a small 1 should be shown as 17¹).

    2. Dimensions:
   - Extract all numeric measurements along the lot edges (e.g., 8.66, 10.00, 25.98).

    3. PH information:
   - Extract any PH reference if present (e.g., PH 1234, PH 4596).

    4. Any other visible text inside the lot boundary.

    
    Return JSON:
    {{
        "lot_number": "string or null",
        "dimensions": ["string"],
        "ph_info": "string or null",
        "other_text": "string or null"
    }}
    """
    
    message = HumanMessage(
        content=[
            {"type": "text", "text": prompt_text},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
        ]
    )
    
    try:
        response = await llm.ainvoke([message])
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        result = json.loads(content.strip())
        # Inject filename into the result
        result["filename"] = lot_filename
        return result
    except Exception as e:
        print(f"Error extracting lot {lot_filename}: {e}")
        return {"error": str(e), "filename": lot_filename}

async def extract_global_info(image_bytes: bytes) -> Dict[str, Any]:
    """Extracts street names and block info from the full map."""
    base64_image = encode_image(image_bytes)
    
    prompt_text = """
    Analyze this cadastral map.
    Focus on the OUTER text:
    1. Street Names surrounding the block.
    2. Block (Manzana) Number or Code.
    3. Section (Sección) if visible.
    4. Any titles or headers (e.g., "ZEBALLOS DR. ESTANISLAO").
    
    Return JSON:
    {
        "streets": ["string"],
        "block_info": "string",
        "headers": ["string"]
    }
    """
    
    message = HumanMessage(
        content=[
            {"type": "text", "text": prompt_text},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
        ]
    )
    
    try:
        response = await llm.ainvoke([message])
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        return json.loads(content.strip())
    except Exception as e:
        return {"error": str(e)}

async def extract_data_from_pdf(
    pdf_path: str, 
    target_lot: str = None, 
    screenshot_path: str = None,
    progress_callback: Callable[[str, Any], Awaitable[None]] = None
) -> Dict[str, Any]:
    """
    Converts PDF to image, uses external script for segmentation, and LLM for extraction.
    Supports streaming progress via progress_callback(event_type, data).
    """
    try:
        # Open PDF
        doc = fitz.open(pdf_path)
        if doc.page_count < 1:
            return {"error": "Empty PDF"}
        
        # Get first page
        page = doc[0]
        
        # Render page to image (pixmap) - High quality
        pix = page.get_pixmap(matrix=fitz.Matrix(3, 3)) 
        image_bytes = pix.tobytes("jpeg")
        doc.close()
        
        # 1. Load and Preprocess
        cv_image = load_image_from_bytes(image_bytes)
        
        # Create debug directory
        base_name = os.path.splitext(os.path.basename(pdf_path))[0]
        debug_dir = os.path.join(os.path.dirname(pdf_path), f"{base_name}_debug")
        if not os.path.exists(debug_dir):
            os.makedirs(debug_dir)
            
        # Save raw full map
        raw_image_path = os.path.join(debug_dir, "full_map.jpg")
        cv2.imwrite(raw_image_path, cv_image)
        
        image_bytes_encoded = encode_image_to_bytes(cv_image)
        
        # Notify full map ready
        if progress_callback:
            await progress_callback("full_map", {"path": raw_image_path})
        
        # 2. Start Global Info Extraction (Background)
        print("Extracting global info (streets, headers)...")
        # We start it, but don't await immediately if we want to proceed to segmentation
        global_info_task = asyncio.create_task(extract_global_info(image_bytes_encoded))
        
        # 3. External Segmentation
        print("Running external segmentation...")
        lots_output_dir = os.path.join(debug_dir, "lots")
        if not os.path.exists(lots_output_dir):
            os.makedirs(lots_output_dir)
            
        # Run segmentation in a thread to avoid blocking the event loop
        # process_cadastral_map(raw_image_path, lots_output_dir)
        await asyncio.to_thread(process_cadastral_map, raw_image_path, lots_output_dir)
        
        # 4. Process Extracted Lots
        print("Processing extracted lots with LLM...")
        # Filter out debug images like 'debug_detected_lots.jpg'
        lot_files = sorted([f for f in os.listdir(lots_output_dir) if f.endswith(('.png', '.jpg')) and not f.startswith('debug_')])
        
        # Notify lots found (images ready)
        if progress_callback:
            await progress_callback("lots_found", {"files": lot_files, "debug_dir": debug_dir})
            
        # Helper wrapper to notify on completion
        async def extract_and_notify(l_bytes, l_file):
            res = await extract_single_lot_data(l_bytes, l_file)
            if progress_callback:
                await progress_callback("lot_data", res)
            return res

        tasks = []
        for lot_file in lot_files:
            lot_path = os.path.join(lots_output_dir, lot_file)
            with open(lot_path, "rb") as f:
                lot_bytes = f.read()
            # Use wrapper if callback exists, else direct call
            if progress_callback:
                tasks.append(extract_and_notify(lot_bytes, lot_file))
            else:
                tasks.append(extract_single_lot_data(lot_bytes, lot_file))
            
        # Wait for global info and notify
        global_info = await global_info_task
        if progress_callback:
            await progress_callback("global_info", global_info)

        # Wait for all lots
        lots_data = await asyncio.gather(*tasks)
        
        # 5. Filter for target lot if requested
        filtered_data = lots_data
        if target_lot:
            print(f"Filtering for target lot: {target_lot}")
            # Try to match exact string or simple variations
            matches = []
            for data in lots_data:
                extracted_num = data.get("lot_number")
                if extracted_num and str(extracted_num).strip() == str(target_lot).strip():
                    matches.append(data)
            
            if matches:
                filtered_data = matches
            else:
                print(f"Target lot {target_lot} not found in extracted data.")
                # We keep all data if not found, or maybe just return empty?
                # Usually better to return everything and let user see.
        
        return {
            "global_info": global_info,
            "lots_data": filtered_data,
            "total_lots_found": len(lots_data),
            "image_path": raw_image_path,
            "debug_dir": debug_dir
        }
            
    except Exception as e:
        print(f"Extraction error: {e}")
        return {"error": str(e)}
