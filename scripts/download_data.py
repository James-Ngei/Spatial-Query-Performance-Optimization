"""
Download OSM data for Nairobi County
Run: python scripts/download_data.py
"""
import requests
import json
from pathlib import Path

# Create data directory
Path("data").mkdir(exist_ok=True)

print("📥 Downloading Nairobi OSM data...")

# Nairobi County bounding box
bbox = "-1.444,36.650,-1.163,37.103"  # south,west,north,east

# Overpass query for buildings, roads, and POIs
query = f"""
[out:json][timeout:180];
(
  way["building"]({bbox});
  way["highway"]({bbox});
  way["landuse"]({bbox});
  node["amenity"]({bbox});
  node["shop"]({bbox});
);
out body;
>;
out skel qt;
"""

url = "https://overpass-api.de/api/interpreter"

try:
    print("Querying Overpass API (this may take 1-2 minutes)...")
    response = requests.post(url, data={"data": query}, timeout=300)
    
    if response.status_code == 200:
        data = response.json()
        elements = data.get('elements', [])
        
        with open('data/nairobi_raw.json', 'w') as f:
            json.dump(data, f)
        
        print(f"✅ Downloaded {len(elements)} OSM elements")
        print(f"💾 Saved to data/nairobi_raw.json")
        
        # Quick stats
        node_count = sum(1 for el in elements if el['type'] == 'node')
        way_count = sum(1 for el in elements if el['type'] == 'way')
        
        print(f"\nStats:")
        print(f"  Nodes: {node_count}")
        print(f"  Ways: {way_count}")
        print(f"  Total: {len(elements)}")
        
    else:
        print(f"❌ Error: HTTP {response.status_code}")
        print(response.text)
        
except Exception as e:
    print(f"❌ Error downloading data: {e}")
    print("\nAlternative: Download manually from:")
    print("https://download.geofabrik.de/africa/kenya-latest.osm.pbf")
    print("Then use osmium tools to extract Nairobi region")