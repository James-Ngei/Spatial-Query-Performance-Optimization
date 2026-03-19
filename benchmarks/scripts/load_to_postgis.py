"""
Load OSM data into PostGIS
Run: python scripts/load_to_postgis.py
"""
import json
import geopandas as gpd
from sqlalchemy import create_engine, text
from shapely.geometry import Point, LineString, Polygon
import pandas as pd

print("🔄 Loading OSM data to PostGIS...")

# Read downloaded data
with open('data/nairobi_raw.json', 'r') as f:
    data = json.load(f)

elements = data.get('elements', [])
print(f"Processing {len(elements)} OSM elements...")

# Build node lookup for way reconstruction
nodes = {el['id']: (el['lon'], el['lat']) 
         for el in elements if el['type'] == 'node'}

# Convert to GeoDataFrame
features = []

for el in elements:
    if el['type'] == 'node' and 'tags' in el:
        # Point features (POIs)
        features.append({
            'osm_id': el['id'],
            'osm_type': 'node',
            'geometry': Point(el['lon'], el['lat']),
            **el.get('tags', {})
        })
    
    elif el['type'] == 'way' and 'nodes' in el:
        # Reconstruct way geometry from node references
        coords = [nodes[nid] for nid in el['nodes'] if nid in nodes]
        
        if len(coords) < 2:
            continue
            
        # Closed way = polygon, open way = linestring
        if coords[0] == coords[-1] and len(coords) > 3:
            geom = Polygon(coords)
        else:
            geom = LineString(coords)
        
        features.append({
            'osm_id': el['id'],
            'osm_type': 'way',
            'geometry': geom,
            **el.get('tags', {})
        })

print(f"Created {len(features)} valid features")

# Create GeoDataFrame
gdf = gpd.GeoDataFrame(features, crs='EPSG:4326')

# Select important columns
important_cols = ['osm_id', 'osm_type', 'name', 'building', 'highway', 
                  'amenity', 'shop', 'landuse', 'geometry']
cols_to_keep = [col for col in important_cols if col in gdf.columns]
gdf = gdf[cols_to_keep]

print(f"\nDataset info:")
print(f"  Total features: {len(gdf)}")
print(f"  Points: {sum(gdf.geometry.type == 'Point')}")
print(f"  LineStrings: {sum(gdf.geometry.type == 'LineString')}")
print(f"  Polygons: {sum(gdf.geometry.type == 'Polygon')}")

# Connect to PostGIS
print("\n📤 Uploading to PostGIS...")
engine = create_engine('postgresql://gisuser:gispass@localhost:5433/spatial_perf')

# Load to database (no index yet - we'll benchmark that)
gdf.to_postgis('osm_features', engine, if_exists='replace', index=False)
print(f"✅ Loaded {len(gdf)} features to table 'osm_features'")

# Verify
with engine.connect() as conn:
    result = conn.execute(text("SELECT COUNT(*) FROM osm_features"))
    count = result.scalar()
    print(f"✅ Verified {count} rows in database")
    
print("\n⚠️  No spatial index created yet (we'll benchmark with/without)")
print("Ready for benchmarking!")