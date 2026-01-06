import requests
import xml.etree.ElementTree as ET

url = "https://infomapa.rosario.gov.ar/wms/planobase?SERVICE=WMS&VERSION=1.1.0&REQUEST=GetCapabilities"

try:
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    
    root = ET.fromstring(response.content)
    
    # Namespace handling might be needed, but usually simple tags work if we ignore ns
    # WMS 1.1.0 doesn't strictly use namespaces in all tags, but let's see.
    
    print("Fetching layers...")
    
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

    recursive_print(root.find('Capability'))

except Exception as e:
    print(f"Error: {e}")
