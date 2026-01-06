import asyncio
from playwright.async_api import async_playwright

async def sniff_wms():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        print("Monitoring network requests for WMS services...")
        
        unique_urls = set()
        
        page.on("request", lambda request: check_request(request, unique_urls))
        
        try:
            await page.goto("https://infomapa.rosario.gov.ar/emapa/mapa.htm", timeout=60000)
            # Wait a bit for initial layers to load
            await page.wait_for_timeout(10000)
            
            print("\n--- Detected WMS URLs ---")
            for url in unique_urls:
                print(url)
                
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await browser.close()

def check_request(request, unique_urls):
    url = request.url
    # Look for WMS characteristic parameters
    if "GetMap" in url or "wms" in url.lower():
        # Clean up the URL to get the base service
        base_url = url.split("?")[0]
        if base_url not in unique_urls:
            unique_urls.add(base_url)
            print(f"Found WMS candidate: {base_url}")
            # Print full query string for the first match of each base to see layers
            print(f"  Sample Query: {url.split('?')[1]}")

if __name__ == "__main__":
    asyncio.run(sniff_wms())
