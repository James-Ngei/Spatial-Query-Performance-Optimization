"""
Simple loader using GeoPandas (handles osmium format)
Run: python scripts/load_simple.py
"""
import os
import geopandas as gpd
from sqlalchemy import create_engine, text

print("🔄 Loading Nairobi buildings to PostGIS...")

# Connect to PostGIS (use DATABASE_URL if provided)
DATABASE_URL = os.environ["DATABASE_URL"]
engine = create_engine(DATABASE_URL)

try:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("✅ Connected to PostGIS")
except Exception as e:
    print(f"❌ Connection failed: {e}")
    exit(1)

# Read GeoJSON with GeoPandas (handles format automatically)
print("📖 Reading nairobi_buildings.geojson...")
gdf = gpd.read_file('nairobi_buildings.geojson')

print(f"Loaded {len(gdf):,} features")

# Clean data
print("🧹 Cleaning geometries...")
gdf = gdf[gdf.geometry.is_valid & ~gdf.geometry.is_empty]

print(f"After cleaning: {len(gdf):,} valid features")

# Show geometry types
print("\nGeometry types:")
print(gdf.geometry.type.value_counts())

# Select important columns
keep_cols = [col for col in ['osm_id', 'building', 'name', 'amenity', 'addr:street', 'geometry'] 
             if col in gdf.columns]
if 'geometry' not in keep_cols:
    keep_cols.append('geometry')

gdf = gdf[keep_cols]
gdf = gdf.set_geometry("geometry")
gdf = gdf.rename_geometry("geom")


# Load to database
print(f"\n📤 Loading {len(gdf):,} features to PostGIS...")
gdf.to_postgis('buildings', engine, if_exists='append', index=False, chunksize=1000)

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
    
    # Geometry distribution
    result = conn.execute(text("""
        SELECT ST_GeometryType(geom) as type, COUNT(*) as count
        FROM buildings
        GROUP BY type
        ORDER BY count DESC
        LIMIT 5
    """))
    
    print(f"\nTop geometry types:")
    for row in result:
        print(f"   {row[0]}: {row[1]:,}")

print("\n⚠️  No spatial index yet - ready for benchmarking!")
print("\nNext steps:")
print("  1. cd backend")
print("  2. uvicorn main:app --reload")