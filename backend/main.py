"""
FastAPI backend for spatial query performance benchmarking
Run: uvicorn backend.main:app --reload
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import sys
sys.path.append('.')

from backend.queries import list_queries, get_query, format_query
from backend.benchmark import run_query, get_table_stats, check_index_exists, create_index, drop_index

app = FastAPI(
    title="Spatial Query Performance API",
    description="Benchmark PostGIS spatial queries with/without indexes",
    version="1.0.0",
    debug=True,
)

ALLOWED_ORIGINS = [
    "http://spatial-query-perf.s3-website.eu-north-1.amazonaws.com",
    "http://localhost:3000",
    "http://localhost:8000",
    "http://localhost:8001",
    "http://localhost",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_private_network_header(request: Request, call_next):
    response = await call_next(request)
    if request.headers.get("access-control-request-private-network") == "true":
        response.headers["Access-Control-Allow-Private-Network"] = "true"
    return response

class BenchmarkRequest(BaseModel):
    query_id: str
    use_index: bool = False

@app.get("/")
def root():
    return {
        "message": "Spatial Query Performance API",
        "docs": "/docs",
        "endpoints": {
            "queries": "/api/queries",
            "benchmark": "/api/benchmark",
            "stats": "/api/stats",
            "index": "/api/index"
        }
    }

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/api/queries")
def get_queries():
    """List all available benchmark queries"""
    return {"queries": list_queries()}

@app.get("/api/stats")
def get_stats():
    """Get table statistics"""
    try:
        stats = get_table_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/index/status")
def index_status():
    """Check if spatial index exists"""
    return {
        "exists": check_index_exists(),
        "index_name": "idx_buildings_geom"
    }

@app.post("/api/index/create")
def create_spatial_index():
    """Create spatial index"""
    try:
        result = create_index()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/index/drop")
def drop_spatial_index():
    """Drop spatial index"""
    try:
        result = drop_index()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/benchmark")
def run_benchmark(request: BenchmarkRequest):
    """
    Run a benchmark query
    
    Args:
        query_id: ID of the query to run
        use_index: Whether to use spatial index
        
    Returns:
        Benchmark results with timing and query plan
    """
    try:
        # Get query definition
        query = get_query(request.query_id)
        sql = format_query(query)
        
        # Run benchmark
        result = run_query(sql, request.use_index)
        
        # Add query metadata
        result["query_name"] = query.name
        result["query_description"] = query.description
        result["use_case"] = query.use_case
        
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))