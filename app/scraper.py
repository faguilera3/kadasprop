import asyncio
import os
import time
from playwright.async_api import async_playwright, Page

async def scrape_infomapa(address: str, output_dir: str) -> str:
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=True) # Set to False for debugging
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()
        
        screenshot_path = None # Initialize variable

        try:
            # 1. Navigate to the page
            print(f"Navigating to InfoMapa...")
            await page.goto("https://infomapa.rosario.gov.ar/emapa/mapa.htm", timeout=60000)
            
            # 2. Type address in search bar
            print(f"Searching for address: {address} (Updated Version)")
            
            # Use the identified ID
            search_input = page.locator("#txtDireccionesLugares")
            await search_input.wait_for(state="visible")
            
            await search_input.click()
            # Type fast to trigger autocomplete
            await search_input.press_sequentially(address, delay=20)
            
            # 3. Wait for autocomplete results and click the first one
            print("Waiting for autocomplete results...")
            
            # User provided specific class for the list item
            # Wait for at least one item
            try:
                # Wait for the list container or items
                await page.wait_for_selector("li.ubicaciones-li", timeout=5000)
                
                items = page.locator("li.ubicaciones-li")
                count = await items.count()
                print(f"Found {count} autocomplete items.")
                
                if count > 0:
                    first_item = items.first
                    print(f"Clicking first item: {await first_item.text_content()}")
                    await first_item.click(force=True)
                else:
                    print("No items found despite wait.")
                    await search_input.press("Enter")
                    
            except Exception as e:
                print(f"Autocomplete wait failed: {e}")
                # Fallback
                await search_input.press("Enter")
            
            # 4. Switch to Info Tool and Get Data (New Flow)
            print("Waiting for map to load and initial popup...", flush=True)
            
            # Wait for the initial popup to ensure address was found/map moved
            try:
                # Wait briefly for the initial popup close button or content
                # This confirms the search was successful and map is centered
                await page.wait_for_selector(".olPopupCloseBox", timeout=10000)
            except:
                print("Initial popup not found, but continuing...", flush=True)

            print("Executing sequence: Info Icon -> Close Popup -> Click Pin", flush=True)
            
            # 1. Click Info Icon
            # <div id="info-capa-icon">
            info_icon = page.locator("#info-capa-icon")
            await info_icon.wait_for(state="visible")
            await info_icon.click()
            await page.wait_for_timeout(500) # Small pause
            
            # 2. Close existing popup
            # Find close buttons
            close_btns = page.locator(".olPopupCloseBox")
            count = await close_btns.count()
            if count > 0:
                print(f"Closing {count} popups...", flush=True)
                # Click the last one (usually the top-most)
                await close_btns.last.click()
                await page.wait_for_timeout(500)
            
            # --- TAKE CLEAN MAP SCREENSHOT HERE ---
            print("Taking clean map screenshot...", flush=True)
            abs_output_dir = os.path.abspath(output_dir)
            screenshot_filename = f"{address.replace(' ', '_')}_map.png"
            screenshot_path = os.path.join(abs_output_dir, screenshot_filename)
            try:
                await page.screenshot(path=screenshot_path)
            except Exception as e:
                print(f"Failed to take map screenshot: {e}", flush=True)
                screenshot_path = None
            # ---------------------------------------

            # 3. Click Pin
            # The pin is usually an image inside an SVG/VML layer
            # ID starts with OpenLayers.Geometry.Point
            # <image id="OpenLayers.Geometry.Point_702" ...>
            pin = page.locator("image[id^='OpenLayers.Geometry.Point']")
            if await pin.count() == 0:
                # Fallback selector
                pin = page.locator("g[id^='OpenLayers.Layer.Vector'] image")
            
            if await pin.count() > 0:
                print("Found pin, clicking...", flush=True)
                await pin.first.click(force=True)
            else:
                # Sometimes the pin might be different or not immediately loaded
                print("Warning: Location pin not found with standard selector.", flush=True)
                # Take screenshot for debug if this happens
                await page.screenshot(path=os.path.join(output_dir, "debug_no_pin.png"))
                raise Exception("Location pin not found on map.")
                
            # 4. Wait for New Modal (#tabsInfo-3)
            print("Waiting for Info Modal (#tabsInfo-3)...", flush=True)
            info_modal = page.locator("#tabsInfo-3")
            await info_modal.wait_for(state="visible", timeout=10000)
            
            # 5. Extract Metadata
            print("Extracting metadata from Info Modal...", flush=True)
            metadata = {}
            
            # Extract from table.featureInfo
            # Get all rows
            rows = info_modal.locator("table.featureInfo tr")
            count = await rows.count()
            
            for i in range(count):
                row = rows.nth(i)
                cells = row.locator("td")
                # We expect key-value pairs
                if await cells.count() == 2:
                    key = await cells.nth(0).inner_text()
                    val = await cells.nth(1).inner_text()
                    key = key.strip().replace(":", "")
                    val = val.strip()
                    if key and val:
                        metadata[key] = val
            
            # Normalize 'Gráfico' to 'lote' for compatibility with extractor
            if "Gráfico" in metadata and "lote" not in metadata:
                metadata["lote"] = metadata["Gráfico"]

            print(f"Extracted Metadata: {metadata}", flush=True)
            
            # 6. Extract PDF Link
            print("Extracting PDF link...", flush=True)
            # Look for "Registro Gráfico" link inside the modal
            # The user snippet shows it in a separate table, but inside #tabsInfo-3
            pdf_link = info_modal.locator("a").filter(has_text="Registro Gráfico")
            
            if await pdf_link.count() > 0:
                href = await pdf_link.first.get_attribute("href")
                print(f"Found PDF href: {href}", flush=True)
                
                if href:
                     if href.startswith("/"):
                        pdf_url = f"https://infomapa.rosario.gov.ar{href}"
                     else:
                        pdf_url = href
                        
                     print(f"Downloading PDF from: {pdf_url}", flush=True)
                     
                     # Download
                     response = await page.request.get(pdf_url)
                     if response.status == 200:
                        pdf_data = await response.body()
                        filename = f"{address.replace(' ', '_')}.pdf"
                        file_path = os.path.join(output_dir, filename)
                        with open(file_path, "wb") as f:
                            f.write(pdf_data)
                        print(f"PDF downloaded to: {file_path}", flush=True)
                        
                        # Screenshot logic removed from here as it's now done earlier (clean map)
                        # We just return the path we captured before

                        return {
                            "pdf_path": file_path,
                            "metadata": metadata,
                            "screenshot_path": screenshot_path
                        }
                     else:
                        raise Exception(f"Download failed with status {response.status}")
                else:
                    raise Exception("PDF link href is empty")
            else:
                 raise Exception("Registro Gráfico link not found in modal")
                
        except Exception as e:
            print(f"Error scraping: {e}")
            # Take screenshot for debug
            await page.screenshot(path=os.path.join(output_dir, "error_screenshot.png"))
            # Dump HTML
            with open(os.path.join(output_dir, "page_dump.html"), "w", encoding="utf-8") as f:
                f.write(await page.content())
            raise e
        finally:
            await browser.close()

if __name__ == "__main__":
    # Test run
    # asyncio.run(scrape_infomapa("Cordoba 1000", "data"))
    pass
