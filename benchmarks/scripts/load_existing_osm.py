"""
Load existing OSM data (buildings.geojson or buildings.osm.pbf) to PostGIS
Run: python scripts/load_existing_osm.py
"""
import geopandas as gpd
from sqlalchemy import create_engine, text
from pathlib import Path

print("🔄 Loading existing OSM data to PostGIS...")

# Check what files we have
data_files = {
    'geojson': Path('buildings.geojson'),
    'osm_pbf': Path('buildings.osm.pbf'),
    'kenya_pbf': Path('kenya-latest.osm.pbf')
}

available = {k: v for k, v in data_files.items() if v.exists()}

print("Available data files:")
for name, path in available.items():
    size_mb = path.stat().st_size / (1024 * 1024)
    print(f"  ✅ {path.name} ({size_mb:.1f} MB)")

if not available:
    print("❌ No OSM data found. Please run download_data.py first")
    exit(1)

# Load the GeoJSON if available
if 'geojson' in available:
    print(f"\n📖 Reading buildings.geojson...")
    gdf = gpd.read_file('buildings.geojson')
    
elif 'osm_pbf' in available:
    print("❌ buildings.osm.pbf found but need GeoJSON")
    print("Convert with: osmium export buildings.osm.pbf -o buildings.geojson")
    exit(1)
else:
    print("❌ No suitable data file found")
    exit(1)

print(f"Loaded {len(gdf)} features")

# Clean up columns
print("\n🧹 Cleaning data...")

# Drop unnecessary columns, keep important ones
important_cols = ['osm_id', 'building', 'name', 'amenity', 'addr:street', 
                  'addr:city', 'height', 'levels', 'geometry']
cols_to_keep = [col for col in important_cols if col in gdf.columns]

if 'geometry' not in cols_to_keep:
    cols_to_keep.append('geometry')

gdf = gdf[cols_to_keep]

# Ensure valid geometries
gdf = gdf[gdf.geometry.is_valid]
gdf = gdf[~gdf.geometry.is_empty]

print(f"After cleaning: {len(gdf)} valid features")
print(f"\nGeometry types:")
print(gdf.geometry.type.value_counts())

# Sample the data if too large (for faster testing)
if len(gdf) > 100000:
    print(f"\n⚠️  Dataset has {len(gdf)} features")
    print("Options:")
    print("  1. Load all (slower but more realistic)")
    print("  2. Sample 100k random features (faster testing)")
    
    choice = input("Choice [1/2]: ").strip()
    if choice == '2':
        gdf = gdf.sample(n=100000, random_state=42)
        print(f"Using {len(gdf)} sampled features")

# Connect to PostGIS
print("\n📤 Connecting to PostGIS...")
engine = create_engine('postgresql://gisuser:gispass@localhost:5433/spatial_perf')

# Test connection
try:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version()"))
        print(f"✅ Connected to PostgreSQL")
        
        result = conn.execute(text("SELECT PostGIS_Version()"))
        postgis_ver = result.scalar()
        print(f"✅ PostGIS version: {postgis_ver}")
except Exception as e:
    print(f"❌ Connection failed: {e}")
    print("\nMake sure Docker container is running:")
    print("  docker compose up -d")
    exit(1)

# Load to database
print(f"\n📥 Loading {len(gdf)} features to 'buildings' table...")
gdf.to_postgis('buildings', engine, if_exists='replace', index=False)

# Verify
with engine.connect() as conn:
    result = conn.execute(text("SELECT COUNT(*) FROM buildings"))
    count = result.scalar()
    
    result = conn.execute(text("""
        SELECT 
            COUNT(*) as total,
            COUNT(DISTINCT ST_GeometryType(geometry)) as geom_types,
            pg_size_pretty(pg_total_relation_size('buildings')) as table_size
        FROM buildings
    """))
    row = result.fetchone()
    
    print(f"\n✅ Database loaded successfully!")
    print(f"   Rows: {row[0]}")
    print(f"   Geometry types: {row[1]}")
    print(f"   Table size: {row[2]}")

print("\n⚠️  No spatial index created yet")
print("We'll benchmark queries with/without indexes next")
print("\nReady for query benchmarking! 🚀")