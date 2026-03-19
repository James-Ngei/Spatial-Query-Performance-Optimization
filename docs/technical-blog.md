# How Spatial Indexes Made My Queries 292x Faster: A PostGIS Performance Deep Dive

## TL;DR
I benchmarked spatial queries on 625,951 building features in Nairobi, Kenya. Adding a GiST spatial index reduced query times from 566ms to 1.94ms—a **292x speedup**. Here's how spatial indexes work and when they help most.

## The Problem: Slow Spatial Queries

Working with geospatial data in PostGIS, I faced a common problem: queries were painfully slow. A simple "find buildings near this point" query took over 500 milliseconds. For a map application serving tiles or running spatial analytics, this is unacceptable.

The issue? Without spatial indexes, PostgreSQL must scan every single row and calculate spatial relationships one by one. With 625,951 features, that's a lot of geometry operations.

## The Dataset

- **Location:** Nairobi, Kenya
- **Features:** 625,951 buildings (from OpenStreetMap)
- **Geometry Types:** Polygons, LineStrings, Points
- **Table Size:** 159 MB
- **Database:** PostgreSQL 15 + PostGIS 3.4

## Benchmark Results

I tested five common spatial query patterns with and without a GiST spatial index:

| Query Type | Without Index | With Index | Speedup |
|------------|---------------|------------|---------|
| Small Bounding Box | 108.38 ms | 7.72 ms | **14x** |
| Count in Area | 138.06 ms | 11.45 ms | **12x** |
| Distance Filter | 667.33 ms | 3.75 ms | **178x** |
| 50 Nearest Neighbors | 566.27 ms | 1.94 ms | **292x** |

## Understanding Spatial Indexes

### What is a GiST Index?

GiST (Generalized Search Tree) is PostgreSQL's index type for spatial data. It organizes geometries into a hierarchical R-tree structure based on their bounding boxes.

```sql
CREATE INDEX idx_buildings_geom 
ON buildings USING GIST(geometry);
```

### How It Works

1. **Hierarchical Bounding Boxes:** The index builds a tree where each node represents a bounding box containing child geometries
2. **Quick Elimination:** When querying "features near point X", the index immediately eliminates entire branches that can't possibly contain matches
3. **Candidate Set:** Returns a small set of potential matches
4. **Exact Check:** PostgreSQL then performs precise spatial calculations only on candidates

Without an index, PostgreSQL must check all 625k rows. With an index, it might check only 100 candidates.

## Query Pattern Analysis

### Pattern 1: Bounding Box Pre-Filter (14x speedup)

```sql
SELECT osm_id, building, name
FROM buildings
WHERE geometry && ST_MakeEnvelope(36.82, -1.29, 36.84, -1.27, 4326)
```

**Without index:** Parallel sequential scan (Gather node)  
**With index:** Bitmap heap scan using GiST index  
**Result:** 108ms → 7.72ms

The `&&` operator checks if bounding boxes overlap—perfect for spatial indexes. This is the foundation of efficient spatial queries.

### Pattern 2: Distance Filter (178x speedup)

```sql
SELECT osm_id, building, name
FROM buildings
WHERE geometry && ST_Expand(ST_MakePoint(36.82, -1.29), 0.005)
AND ST_Distance(geometry, ST_MakePoint(36.82, -1.29)) < 0.005
ORDER BY ST_Distance(geometry, ST_MakePoint(36.82, -1.29))
LIMIT 100
```

**Without index:** 667ms calculating distance to every feature  
**With index:** 3.75ms using bounding box pre-filter  
**Result:** 178x faster

The two-stage approach is crucial:
1. `&&` operator uses index for bounding box filter
2. `ST_Distance` performs exact calculation only on candidates

### Pattern 3: K-Nearest Neighbors (292x speedup!)

```sql
SELECT osm_id, building, name,
       geometry <-> ST_MakePoint(36.82, -1.29) as dist
FROM buildings
ORDER BY dist
LIMIT 50
```

**Without index:** 566ms sorting all features by distance  
**With index:** 1.94ms using KNN-GiST optimization  
**Result:** 292x faster

The `<->` operator (distance operator) is specially optimized for GiST indexes. It doesn't need to calculate distance to every row—it traverses the R-tree intelligently.

## Reading Query Plans

Here's how to interpret `EXPLAIN ANALYZE` output:

### Without Index
```
Gather (actual time=620.382..627.235)
  Workers Planned: 2
  -> Parallel Seq Scan on buildings
       Filter: (geometry && ...)
       Rows Removed by Filter: 312,950
```

**Red flags:**
- "Seq Scan" = scanning every row
- High "Rows Removed by Filter" = wasted work
- "Gather" = parallel workers all doing sequential scans

### With Index
```
Bitmap Heap Scan (actual time=3.532..3.551)
  Recheck Cond: (geometry && ...)
  -> Bitmap Index Scan on idx_buildings_geom
       Index Cond: (geometry && ...)
```

**Good signs:**
- "Index Scan" = using the index
- Low actual time
- Small candidate set

## When Indexes Help Most

✅ **Excellent speedup:**
- Small area queries (< 10% of data)
- Distance-based searches
- K-nearest neighbor queries
- Map tile loading (viewport queries)

⚠️ **Marginal benefit:**
- Queries returning 40%+ of rows
- Full-table aggregations
- Analytical queries needing most/all data

❌ **No benefit:**
- `SELECT *` with no spatial filter
- Tables under 10,000 rows (overhead not worth it)

## Production Best Practices

### 1. Always Index Geometry Columns
```sql
CREATE INDEX idx_table_geom ON table_name USING GIST(geometry);
```

For tables over 10k rows, the speedup justifies the storage cost.

### 2. Run ANALYZE After Index Creation
```sql
ANALYZE table_name;
```

This updates PostgreSQL's query planner statistics, ensuring it knows about and uses the index.

### 3. Use Bounding Box Pre-Filters
```sql
-- Bad: No index usage
WHERE ST_Intersects(geom, polygon)

-- Good: Index-friendly
WHERE geom && polygon
AND ST_Intersects(geom, polygon)
```

### 4. Monitor Index Usage
```sql
SELECT 
    schemaname, tablename, indexname,
    idx_scan, idx_tup_read, idx_tup_fetch
FROM pg_stat_user_indexes
WHERE tablename = 'buildings';
```

Check `idx_scan` to confirm your index is being used.

### 5. Consider Index Size vs Benefit
My index added 51 MB (32% of table size) but provided 14-292x speedup. That's an excellent tradeoff. If your index is larger than your table, investigate why.

## Common Pitfalls

### Pitfall 1: Geography vs Geometry
```sql
-- Slow: geography casting disables index
WHERE ST_DWithin(geom::geography, point::geography, 500)

-- Fast: use planar distance with index
WHERE geom && ST_Expand(point, 0.005)
AND ST_Distance(geom, point) < 0.005
```

### Pitfall 2: Forcing Sequential Scans
If PostgreSQL ignores your index, it might think a seq scan is faster. Check:
```sql
SET enable_seqscan = off;  -- Test only
```

If this speeds up queries, increase `random_page_cost` or run `ANALYZE`.

### Pitfall 3: Outdated Statistics
After bulk inserts, always:
```sql
VACUUM ANALYZE table_name;
```

## The Architecture

I built an interactive benchmarking API to test this:

```
┌─────────────────┐
│  React Frontend │  (Benchmark UI)
│   Tailwind CSS  │
└────────┬────────┘
         │ HTTP
         ▼
┌─────────────────┐
│  FastAPI Backend│  (Benchmark runner)
│   /api/queries  │
│   /api/benchmark│
└────────┬────────┘
         │ psycopg2
         ▼
┌─────────────────┐
│ PostgreSQL 15   │
│   + PostGIS 3.4 │
│   625k features │
└─────────────────┘
```

The backend:
- Drops/creates indexes on demand
- Runs `EXPLAIN ANALYZE` to capture query plans
- Forces sequential scans for true comparison
- Returns timing metrics and scan types

## Key Takeaways

1. **Spatial indexes are non-negotiable** for production geospatial applications
2. **292x speedup** is possible with proper indexing
3. **Bounding box operators** (`&&`) are key to index usage
4. **Query patterns matter**—always pre-filter with bounding boxes
5. **Monitor and measure**—use `EXPLAIN ANALYZE` to verify index usage

## Try It Yourself

Full code with interactive dashboard: [GitHub Repo]

```bash
# Clone and run
git clone [your-repo]
cd spatial-query-perf
docker compose up -d
python scripts/load_simple.py
uvicorn backend.main:app --reload
# Open frontend/index.html
```

## Conclusion

Spatial indexes transform PostGIS from painfully slow to lightning fast. A one-line `CREATE INDEX` statement turned 566ms queries into 1.94ms queries—enabling real-time spatial applications that would otherwise be impossible.

If you're working with geospatial data and haven't indexed your geometry columns, do it now. Your users will thank you.

---

**Questions? Issues?** Drop a comment or open an issue on GitHub.

**Want to learn more?** Check out the [PostGIS documentation on indexing](http://postgis.net/workshops/postgis-intro/indexing.html).