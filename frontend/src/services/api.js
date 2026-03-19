/**
 * API Service
 * Automatically switches between mock (demo) and real (PostgreSQL) backend
 * 
 * Usage in components:
 *   import { api } from './services/api';
 *   const queries = await api.getQueries();
 */

import { mockAPI } from './mockApi';

// Configuration
const REAL_API_URL = window.REACT_APP_API_URL || null;
const USE_MOCK = !REAL_API_URL;

console.log(`API Mode: ${USE_MOCK ? 'MOCK (Demo)' : 'REAL (PostgreSQL)'}`);
if (!USE_MOCK) {
  console.log(`Backend URL: ${REAL_API_URL}`);
}

// Real API implementation
class RealAPI {
  constructor(baseURL) {
    this.baseURL = baseURL;
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      }
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.statusText}`);
    }

    return response.json();
  }

  async getQueries() {
    return this.request('/api/queries');
  }

  async getStats() {
    return this.request('/api/stats');
  }

  async getIndexStatus() {
    return this.request('/api/index/status');
  }

  async createIndex() {
    return this.request('/api/index/create', { method: 'POST' });
  }

  async dropIndex() {
    return this.request('/api/index/drop', { method: 'POST' });
  }

  async runBenchmark(queryId, useIndex) {
    return this.request('/api/benchmark', {
      method: 'POST',
      body: JSON.stringify({
        query_id: queryId,
        use_index: useIndex
      })
    });
  }
}

// Export the appropriate API instance
export const api = USE_MOCK 
  ? mockAPI 
  : new RealAPI(REAL_API_URL);

// Export flag for UI to show demo mode indicator
export const IS_DEMO_MODE = USE_MOCK;