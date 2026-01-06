from playwright.sync_api import sync_playwright
import time

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        print("Navigating to https://infomapa.rosario.gov.ar/ ...")
        page.goto("https://infomapa.rosario.gov.ar/", timeout=60000)
        
        print("Waiting for page to load...")
        page.wait_for_load_state("networkidle")
        
        # Log all WMS requests
        def handle_request(request):
            if "wms" in request.url.lower() or "getmap" in request.url.lower():
                # Check for interesting keywords
                if any(k in request.url.lower() for k in ["semaforos", "normas", "alumbrado", "urbanisticas"]):
                    print(f"[MATCH] {request.url}")
                # else:
                #     print(f"[WMS] {request.url[:100]}...")

        page.on("request", handle_request)
        
        print("Interacting with the map to trigger layer loading...")
        # We might need to open the layer menu and toggle things if they are not default.
        # But maybe they are loaded in the capabilities?
        
        # Let's try to find the layer switcher or menu.
        # Based on previous knowledge, there might be a sidebar.
        
        # Take a screenshot to see what we have
        page.screenshot(path="map_page.png")
        
        # Wait a bit
        time.sleep(10)
        
        browser.close()

if __name__ == "__main__":
    run()
