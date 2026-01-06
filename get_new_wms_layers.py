import requests
import xml.etree.ElementTree as ET

urls = [
    "https://infomapa.rosario.gov.ar/wms/codigourbano?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetCapabilities",
    "https://infomapa.rosario.gov.ar/wms/infraestructura?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetCapabilities"
]

def recursive_print(element, depth=0):
    if element.tag.endswith('Layer'):
        name_elem = element.find('Name')
        title_elem = element.find('Title')
        
        name = name_elem.text if name_elem is not None else "No Name"
        title = title_elem.text if title_elem is not None else "No Title"
        
        print(f"{'  ' * depth}- Title: {title} | Name: {name}")
        
        # Recurse
        for child in element:
            recursive_print(child, depth + 1)
    elif element.tag.endswith('Capability'):
            for child in element:
                recursive_print(child, depth)

for url in urls:
    print(f"\n--- Fetching capabilities from: {url} ---")
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # Remove namespace prefixes for easier parsing if present, or just ignore them
        # simple parsing:
        root = ET.fromstring(response.content)
        recursive_print(root.find('Capability'))
        
    except Exception as e:
        print(f"Error fetching {url}: {e}")
