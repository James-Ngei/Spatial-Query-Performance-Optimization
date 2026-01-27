"""
Load OSM data in chunks to avoid memory issues
Run: python scripts/load_chunked.py
"""
import json
import geopandas as gpd
from sqlalchemy import create_engine, text
from shapely.geometry import shape
import sys

print("🔄 Loading OSM data in chunks...")

# Connect to PostGIS first
engine = create_engine('postgresql://gisuser:gispass@localhost:5432/spatial_perf')

# Test connection
try:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("✅ Connected to PostGIS")
except Exception as e:
    print(f"❌ Connection failed: {e}")
    print("Make sure: docker compose up -d")
    exit(1)

# Drop table if exists
with engine.connect() as conn:
    conn.execute(text("DROP TABLE IF EXISTS buildings"))
    conn.commit()
    print("🗑️  Cleared existing table")

print("\n📖 Reading buildings.geojson in chunks...")

chunk_size = 10000  # Load 10k features at a time
features_loaded = 0
chunk_num = 0

try:
    with open('nairobi_buildings.geojson', 'r') as f:
        # Read header
        line = f.readline()
        if not line.strip().startswith('{"type"'):
            print("❌ Invalid GeoJSON format")
            exit(1)
        
        # Parse the file incrementally
        geojson_data = json.load(f)
        total_features = len(geojson_data.get('features', []))
        
        print(f"Total features in file: {total_features:,}")
        print(f"\n⏳ Loading in chunks of {chunk_size:,}...")
        
        # Process in chunks
        for i in range(0, total_features, chunk_size):
            chunk = geojson_data['features'][i:i+chunk_size]
            
            # Convert to GeoDataFrame
            gdf = gpd.GeoDataFrame.from_features(chunk, crs='EPSG:4326')
            
            # Clean
            gdf = gdf[gdf.geometry.is_valid & ~gdf.geometry.is_empty]
            
            # Select columns
            keep_cols = [col for col in ['osm_id', 'building', 'name', 'amenity', 'geometry'] 
                        if col in gdf.columns]
            if 'geometry' not in keep_cols:
                keep_cols.append('geometry')
            gdf = gdf[keep_cols]
            
            # Load to database
            if chunk_num == 0:
                gdf.to_postgis('buildings', engine, if_exists='replace', index=False)
            else:
                gdf.to_postgis('buildings', engine, if_exists='append', index=False)
            
            features_loaded += len(gdf)
            chunk_num += 1
            
            progress = (i + len(chunk)) / total_features * 100
            print(f"  Chunk {chunk_num}: {features_loaded:,} features ({progress:.1f}%)")
            
            # Stop after 500k for testing
            if features_loaded >= 500000:
                print(f"\n⚠️  Reached 500k features - stopping (good for benchmarking)")
                break

except MemoryError:
    print(f"❌ Out of memory at {features_loaded:,} features")
    print("Try with smaller chunk_size")
    exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)

# Verify
with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT 
            COUNT(*) as total,
            pg_size_pretty(pg_total_relation_size('buildings')) as size
        FROM buildings
    """))
    row = result.fetchone()
    
    print(f"\n✅ Successfully loaded!")
    print(f"   Features: {row[0]:,}")
    print(f"   Table size: {row[1]}")
    
    # Geometry type distribution
    result = conn.execute(text("""
        SELECT ST_GeometryType(geometry) as type, COUNT(*) as count
        FROM buildings
        GROUP BY type
        ORDER BY count DESC
    """))
    
    print(f"\nGeometry types:")
    for row in result:
        print(f"   {row[0]}: {row[1]:,}")

print("\n⚠️  No spatial index yet - ready for benchmarking!")
print("Next: python scripts/benchmark_runner.py")