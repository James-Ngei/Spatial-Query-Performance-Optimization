"""
Optimized spatial query definitions that properly use indexes
"""
from typing import Dict, List
from dataclasses import dataclass

@dataclass
class BenchmarkQuery:
    id: str
    name: str
    description: str
    use_case: str
    sql_template: str
    params: Dict = None

# Queries specifically designed to show index performance
QUERIES: List[BenchmarkQuery] = [
    BenchmarkQuery(
        id="small_bbox",
        name="Small Bounding Box",
        description="Select features in a 0.02° x 0.02° area (~2km²)",
        use_case="Load buildings for a single neighborhood",
        sql_template="""
            SELECT osm_id, building, name
            FROM buildings
            WHERE geom && ST_MakeEnvelope({xmin}, {ymin}, {xmax}, {ymax}, 4326)
        """,
        params={'xmin': 36.82, 'ymin': -1.29, 'xmax': 36.84, 'ymax': -1.27}
    ),
    
    BenchmarkQuery(
        id="point_buffer",
        name="Point Buffer Intersection",
        description="Find features within 0.01° of a point",
        use_case="Buildings near a location",
        sql_template="""
            SELECT osm_id, building, name
            FROM buildings
            WHERE geom && ST_Buffer(ST_SetSRID(ST_MakePoint({lon}, {lat}), 4326), 0.01)
            AND ST_Intersects(geom, ST_Buffer(ST_SetSRID(ST_MakePoint({lon}, {lat}), 4326), 0.01))
        """,
        params={'lon': 36.8219, 'lat': -1.2921}
    ),
    
    BenchmarkQuery(
        id="distance_filter",
        name="Distance Filter (Planar)",
        description="Features within 0.005° distance",
        use_case="Nearby features query",
        sql_template="""
            SELECT osm_id, building, name,
                   ST_Distance(geom, ST_SetSRID(ST_MakePoint({lon}, {lat}), 4326)) as dist
            FROM buildings
            WHERE geom && ST_Expand(ST_SetSRID(ST_MakePoint({lon}, {lat}), 4326), 0.005)
            AND ST_Distance(geom, ST_SetSRID(ST_MakePoint({lon}, {lat}), 4326)) < 0.005
            ORDER BY dist
            LIMIT 100
        """,
        params={'lon': 36.8219, 'lat': -1.2921}
    ),
    
    BenchmarkQuery(
        id="knn_distance",
        name="50 Nearest Neighbors",
        description="Find 50 closest features using KNN",
        use_case="Closest buildings to a point",
        sql_template="""
            SELECT osm_id, building, name,
                   geom <-> ST_SetSRID(ST_MakePoint({lon}, {lat}), 4326) as dist
            FROM buildings
            ORDER BY dist
            LIMIT 50
        """,
        params={'lon': 36.8219, 'lat': -1.2921}
    ),
    
    BenchmarkQuery(
        id="intersects_bbox",
        name="Intersects with Small Area",
        description="Features intersecting a small bounding box",
        use_case="Map tile loading",
        sql_template="""
            SELECT osm_id, building, name
            FROM buildings
            WHERE geom && ST_MakeEnvelope({xmin}, {ymin}, {xmax}, {ymax}, 4326)
            AND ST_Intersects(geom, ST_MakeEnvelope({xmin}, {ymin}, {xmax}, {ymax}, 4326))
        """,
        params={'xmin': 36.815, 'ymin': -1.295, 'xmax': 36.825, 'ymax': -1.285}
    ),
    
    BenchmarkQuery(
        id="count_in_area",
        name="Count Features in Area",
        description="Count all features in a region",
        use_case="Building density analysis",
        sql_template="""
            SELECT COUNT(*) as total
            FROM buildings
            WHERE geom && ST_MakeEnvelope({xmin}, {ymin}, {xmax}, {ymax}, 4326)
        """,
        params={'xmin': 36.80, 'ymin': -1.30, 'xmax': 36.85, 'ymax': -1.28}
    ),
]

def get_query(query_id: str) -> BenchmarkQuery:
    """Get query by ID"""
    for q in QUERIES:
        if q.id == query_id:
            return q
    raise ValueError(f"Query not found: {query_id}")

def list_queries() -> List[Dict]:
    """List all available queries"""
    return [
        {
            "id": q.id,
            "name": q.name,
            "description": q.description,
            "use_case": q.use_case
        }
        for q in QUERIES
    ]

def format_query(query: BenchmarkQuery) -> str:
    """Format query with parameters"""
    if query.params:
        return query.sql_template.format(**query.params)
    return query.sql_template
