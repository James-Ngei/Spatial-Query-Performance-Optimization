/**
 * Mock API Service
 * Simulates realistic PostGIS query performance for client-side demo
 * Based on actual benchmark data from 625k OpenStreetMap features
 */

// Database statistics
const DB_STATS = {
  total_rows: 625951,
  table_size: "133 MB",
  index_size: "42 MB"
};

// Query definitions with actual benchmark ranges
const QUERY_DATA = {
  small_bbox: {
    id: "small_bbox",
    name: "Small Bounding Box",
    description: "Select features in a 0.02° x 0.02° area (~2km²)",
    use_case: "Load buildings for a single neighborhood",
    without_index: {
      execution_time_range: [55.00, 200.00],
      planning_time_range: [4.71, 13.13],
      scan_type: "Gather",
      rows: 8596
    },
    with_index: {
      execution_time_range: [2.50, 7.68],
      planning_time_range: [4.71, 13.13],
      scan_type: "Bitmap Heap Scan",
      rows: 8596
    }
  },
  
  point_buffer: {
    id: "point_buffer",
    name: "Point Buffer Intersection",
    description: "Find features within 0.01° of a point",
    use_case: "Buildings near a location",
    without_index: {
      execution_time_range: [295.78, 800.56],
      planning_time_range: [5.10, 11.50],
      scan_type: "Gather",
      rows: 3413
    },
    with_index: {
      execution_time_range: [7.76, 17.36],
      planning_time_range: [5.10, 11.50],
      scan_type: "Index Scan",
      rows: 3413
    }
  },
  
  distance_filter: {
    id: "distance_filter",
    name: "Distance Filter (Planar)",
    description: "Features within 0.005° distance",
    use_case: "Nearby features query",
    without_index: {
      execution_time_range: [457.73, 680.44],
      planning_time_range: [5.10, 11.50],
      scan_type: "Limit",
      rows: 100
    },
    with_index: {
      execution_time_range: [1.77, 3.91],
      planning_time_range: [5.10, 11.50],
      scan_type: "Limit",
      rows: 100
    }
  },
  
  knn_distance: {
    id: "knn_distance",
    name: "50 Nearest Neighbors",
    description: "Find 50 closest features using KNN",
    use_case: "Closest buildings to a point",
    without_index: {
      execution_time_range: [288.28, 460.29],
      planning_time_range: [3.12, 6.68],
      scan_type: "Limit",
      rows: 50
    },
    with_index: {
      execution_time_range: [0.51, 1.33],
      planning_time_range: [3.12, 6.68],
      scan_type: "Limit",
      rows: 50
    }
  },
  
  intersects_bbox: {
    id: "intersects_bbox",
    name: "Intersects with Small Area",
    description: "Features intersecting a small bounding box",
    use_case: "Map tile loading",
    without_index: {
      execution_time_range: [294.77, 459.61],
      planning_time_range: [5.03, 11.63],
      scan_type: "Gather",
      rows: 1039
    },
    with_index: {
      execution_time_range: [1.69, 4.32],
      planning_time_range: [5.03, 11.63],
      scan_type: "Index Scan",
      rows: 1039
    }
  },
  
  count_in_area: {
    id: "count_in_area",
    name: "Count Features in Area",
    description: "Count all features in a region",
    use_case: "Building density analysis",
    without_index: {
      execution_time_range: [61.70, 157.39],
      planning_time_range: [4.50, 11.68],
      scan_type: "Aggregate",
      rows: 1
    },
    with_index: {
      execution_time_range: [6.97, 17.18],
      planning_time_range: [4.50, 11.68],
      scan_type: "Aggregate",
      rows: 1
    }
  }
};

// Utility: Random number in range
function randomInRange(min, max) {
  return min + Math.random() * (max - min);
}

// Simulate network delay
function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// Generate realistic query plan
function generateQueryPlan(scanType, executionTime, rows) {
  return {
    "Plan": {
      "Node Type": scanType,
      "Parallel Aware": scanType === "Gather",
      "Startup Cost": 0.00,
      "Total Cost": executionTime * 1.2,
      "Plan Rows": rows,
      "Plan Width": 32,
      "Actual Startup Time": executionTime * 0.1,
      "Actual Total Time": executionTime,
      "Actual Rows": rows,
      "Actual Loops": 1
    },
    "Planning Time": randomInRange(3, 12),
    "Execution Time": executionTime
  };
}

// Mock API implementation
class MockAPI {
  constructor() {
    this.indexExists = false;
  }

  async getQueries() {
    await delay(100);
    return {
      queries: Object.values(QUERY_DATA).map(q => ({
        id: q.id,
        name: q.name,
        description: q.description,
        use_case: q.use_case
      }))
    };
  }

  async getStats() {
    await delay(100);
    return DB_STATS;
  }

  async getIndexStatus() {
    await delay(50);
    return {
      exists: this.indexExists,
      index_name: "idx_buildings_geom"
    };
  }

  async createIndex() {
    await delay(2000); // Simulate index creation time
    this.indexExists = true;
    return {
      success: true,
      message: "Index created successfully",
      index_name: "idx_buildings_geom"
    };
  }

  async dropIndex() {
    await delay(500);
    this.indexExists = false;
    return {
      success: true,
      message: "Index dropped successfully"
    };
  }

  async runBenchmark(queryId, useIndex) {
    await delay(200); // Simulate network latency

    const queryData = QUERY_DATA[queryId];
    if (!queryData) {
      throw new Error(`Query not found: ${queryId}`);
    }

    // Mirror real backend behavior: runBenchmark creates/drops the index
    // before executing, so index state reflects useIndex after the call.
    this.indexExists = useIndex;

    const config = useIndex ? queryData.with_index : queryData.without_index;
    
    // Generate random execution time within range
    const executionTime = randomInRange(
      config.execution_time_range[0],
      config.execution_time_range[1]
    );
    
    const planningTime = randomInRange(
      config.planning_time_range[0],
      config.planning_time_range[1]
    );

    // Simulate actual query execution time
    await delay(Math.min(executionTime, 500)); // Cap UI delay at 500ms

    return {
      query_id: queryId,
      query_name: queryData.name,
      query_description: queryData.description,
      use_case: queryData.use_case,
      execution_time_ms: parseFloat(executionTime.toFixed(2)),
      planning_time_ms: parseFloat(planningTime.toFixed(2)),
      row_count: config.rows,
      index_used: useIndex,
      index_exists: useIndex, // mirrors real backend response
      query_plan: generateQueryPlan(config.scan_type, executionTime, config.rows)
    };
  }
}

// Export singleton instance
export const mockAPI = new MockAPI();