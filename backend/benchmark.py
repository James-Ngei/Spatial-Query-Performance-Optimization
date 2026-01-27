"""
Benchmark runner for spatial queries
"""
import time
from typing import Dict, Any
from sqlalchemy import create_engine, text
from contextlib import contextmanager
import json

DATABASE_URL = "postgresql://gisuser:gispass@localhost:5432/spatial_perf"

@contextmanager
def get_connection():
    """Get database connection"""
    engine = create_engine(DATABASE_URL)
    conn = engine.connect()
    try:
        yield conn
    finally:
        conn.close()

def check_index_exists() -> bool:
    """Check if spatial index exists on buildings table"""
    with get_connection() as conn:
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT 1 
                FROM pg_indexes 
                WHERE tablename = 'buildings' 
                AND indexname = 'idx_buildings_geom'
            )
        """))
        return result.scalar()

def create_index():
    """Create spatial index"""
    with get_connection() as conn:
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_buildings_geom ON buildings USING GIST(geometry)"))
        conn.commit()
    return {"status": "created", "index": "idx_buildings_geom"}

def drop_index():
    """Drop spatial index"""
    with get_connection() as conn:
        conn.execute(text("DROP INDEX IF EXISTS idx_buildings_geom"))
        conn.commit()
    return {"status": "dropped", "index": "idx_buildings_geom"}

def run_query(sql: str, use_index: bool) -> Dict[str, Any]:
    """
    Run a query and return timing + results
    
    Args:
        sql: SQL query to execute
        use_index: Whether to ensure index exists
        
    Returns:
        Dict with execution_time_ms, row_count, query_plan, etc.
    """
    # Ensure index state matches requirement
    index_exists = check_index_exists()
    if use_index and not index_exists:
        create_index()
        with get_connection() as conn:
            conn.execute(text("ANALYZE buildings"))
            conn.commit()
    elif not use_index and index_exists:
        drop_index()
        with get_connection() as conn:
            conn.execute(text("ANALYZE buildings"))
            conn.commit()
    
    with get_connection() as conn:
        # Disable bitmap scan for no-index case to force seq scan
        if not use_index:
            conn.execute(text("SET enable_bitmapscan = off"))
            conn.execute(text("SET enable_indexscan = off"))
        else:
            conn.execute(text("SET enable_bitmapscan = on"))
            conn.execute(text("SET enable_indexscan = on"))
        
        # Get query plan with EXPLAIN ANALYZE
        explain_sql = f"EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) {sql}"
        
        start_time = time.time()
        result = conn.execute(text(explain_sql))
        execution_time = (time.time() - start_time) * 1000
        
        plan_data = result.fetchone()[0]
        plan = plan_data[0]
        
        # Reset settings
        conn.execute(text("SET enable_bitmapscan = on"))
        conn.execute(text("SET enable_indexscan = on"))
        conn.commit()
        
        execution_time_from_plan = plan.get('Execution Time', 0)
        planning_time = plan.get('Planning Time', 0)
        
        # Get actual row count
        rows = plan.get('Plan', {}).get('Actual Rows', 0)
        
        # Check if index was used
        plan_str = json.dumps(plan)
        index_used = 'Index Scan' in plan_str or 'Bitmap Index Scan' in plan_str
        
        return {
            "execution_time_ms": round(execution_time_from_plan, 2),
            "planning_time_ms": round(planning_time, 2),
            "total_time_ms": round(execution_time_from_plan + planning_time, 2),
            "row_count": rows,
            "index_used": index_used,
            "index_exists": check_index_exists(),
            "query_plan": plan,
            "query": sql
        }

def get_table_stats() -> Dict[str, Any]:
    """Get statistics about the buildings table"""
    with get_connection() as conn:
        result = conn.execute(text("""
            SELECT 
                COUNT(*) as total_rows,
                pg_size_pretty(pg_total_relation_size('buildings')) as table_size,
                pg_size_pretty(pg_indexes_size('buildings')) as index_size,
                (SELECT COUNT(*) FROM pg_indexes WHERE tablename = 'buildings') as index_count
            FROM buildings
        """))
        row = result.fetchone()
        
        return {
            "total_rows": row[0],
            "table_size": row[1],
            "index_size": row[2],
            "index_count": row[3],
            "has_spatial_index": check_index_exists()
        }