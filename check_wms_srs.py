import requests
import xml.etree.ElementTree as ET

url = "https://www.rosario.gob.ar/wms/planobase?SERVICE=WMS&VERSION=1.1.0&REQUEST=GetCapabilities"

try:
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    
    root = ET.fromstring(response.content)
    
    print("Checking supported SRS/CRS...")
    
    # Check root capability layer for inherited SRS
    capability = root.find('Capability')
    if capability:
        layer = capability.find('Layer')
        if layer:
            srs_list = layer.findall('SRS')
            for srs in srs_list:
                print(f"Root Layer SRS: {srs.text}")
                
            # Check a child layer just in case
            child = layer.find('Layer')
            if child:
                srs_list = child.findall('SRS')
                for srs in srs_list:
                    print(f"Child Layer SRS: {srs.text}")

except Exception as e:
    print(f"Error: {e}")
