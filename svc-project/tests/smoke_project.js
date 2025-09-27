/**
 * k6 Smoke Test for NextGen Fusion Project Management API
 * 
 * This script performs load testing on critical API endpoints to ensure
 * the service can handle concurrent requests and maintain performance SLOs.
 * 
 * Performance Targets:
 * - API p95 latency: < 300ms
 * - UI TTI: < 2.5s
 * - Availability: 99.9%
 * 
 * Usage:
 *   k6 run tests/smoke_project.js
 *   k6 run --vus 10 --duration 5m tests/smoke_project.js
 *   k6 run --env BASE_URL=http://localhost:8003 tests/smoke_project.js
 */

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';
import { randomString, randomIntBetween } from 'https://jslib.k6.io/k6-utils/1.2.0/index.js';

// Configuration
const BASE_URL = __ENV.BASE_URL || 'http://localhost:8003';
const API_PREFIX = '/api/v1';

// Custom metrics
const errorRate = new Rate('errors');
const apiLatency = new Trend('api_latency');
const dbOperationLatency = new Trend('db_operation_latency');
const cacheHitRate = new Rate('cache_hits');
const projectCreationCounter = new Counter('projects_created');
const criticalPathCalculations = new Counter('critical_path_calculations');

// Test options
export const options = {
  stages: [
    { duration: '30s', target: 5 },   // Ramp up to 5 users
    { duration: '2m', target: 5 },    // Stay at 5 users for 2 minutes
    { duration: '30s', target: 10 },  // Ramp up to 10 users
    { duration: '2m', target: 10 },   // Stay at 10 users for 2 minutes
    { duration: '30s', target: 0 },   // Ramp down to 0 users
  ],
  thresholds: {
    http_req_duration: ['p(95)<300'], // 95% of requests must be below 300ms
    http_req_failed: ['rate<0.1'],    // Error rate must be below 10%
    errors: ['rate<0.05'],            // Custom error rate below 5%
    api_latency: ['p(95)<300'],       // API latency p95 < 300ms
    checks: ['rate>0.95'],            // 95% of checks must pass
  },
};

// Test data generators
function generateProjectData() {
  const projectTypes = ['Solar Farm', 'Wind Farm', 'Battery Storage', 'Hybrid Plant'];
  const priorities = ['low', 'medium', 'high', 'critical'];
  const statuses = ['planning', 'design', 'permitting', 'construction'];
  
  return {
    name: `${projectTypes[randomIntBetween(0, projectTypes.length - 1)]} - ${randomString(8)}`,
    description: `Load test project created at ${new Date().toISOString()}`,
    start_date: new Date().toISOString().split('T')[0],
    end_date: new Date(Date.now() + 90 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    status: statuses[randomIntBetween(0, statuses.length - 1)],
    priority: priorities[randomIntBetween(0, priorities.length - 1)],
    budget: randomIntBetween(100000, 10000000),
    location: `Test Site ${randomString(4)}`,
  };
}

function generateTaskData() {
  const taskTypes = [
    'Site Survey', 'Environmental Assessment', 'Grid Connection Study',
    'Equipment Procurement', 'Foundation Work', 'Installation',
    'Commissioning', 'Testing', 'Documentation'
  ];
  
  return {
    name: `${taskTypes[randomIntBetween(0, taskTypes.length - 1)]} - ${randomString(6)}`,
    description: `Load test task created at ${new Date().toISOString()}`,
    depends_on: [],
    estimated_hours: randomIntBetween(8, 160),
    priority: ['low', 'medium', 'high'][randomIntBetween(0, 2)],
    status: ['todo', 'in_progress', 'review', 'done'][randomIntBetween(0, 3)],
  };
}

function generateIdempotencyKey() {
  return `k6-test-${Date.now()}-${randomString(16)}`;
}

// Helper functions
function makeRequest(method, url, payload = null, headers = {}) {
  const defaultHeaders = {
    'Content-Type': 'application/json',
    'User-Agent': 'k6-load-test/1.0',
  };
  
  const requestHeaders = { ...defaultHeaders, ...headers };
  const startTime = Date.now();
  
  let response;
  if (payload) {
    response = http.request(method, url, JSON.stringify(payload), { headers: requestHeaders });
  } else {
    response = http.request(method, url, null, { headers: requestHeaders });
  }
  
  const latency = Date.now() - startTime;
  apiLatency.add(latency);
  
  // Track errors
  const isError = response.status >= 400;
  errorRate.add(isError);
  
  return response;
}

function checkResponse(response, expectedStatus = 200, description = 'Request') {
  const checks = {
    [`${description} - Status is ${expectedStatus}`]: (r) => r.status === expectedStatus,
    [`${description} - Response time < 1000ms`]: (r) => r.timings.duration < 1000,
    [`${description} - Has valid JSON response`]: (r) => {
      try {
        JSON.parse(r.body);
        return true;
      } catch (e) {
        return false;
      }
    },
  };
  
  return check(response, checks);
}

// Test scenarios
export function setup() {
  console.log('🚀 Starting k6 smoke test for NextGen Fusion Project Management API');
  console.log(`Base URL: ${BASE_URL}`);
  console.log(`Test duration: ${JSON.stringify(options.stages)}`);
  
  // Verify API is accessible
  const healthResponse = makeRequest('GET', `${BASE_URL}/health`);
  if (!check(healthResponse, { 'Setup - API is accessible': (r) => r.status === 200 })) {
    throw new Error('API is not accessible. Aborting test.');
  }
  
  console.log('✅ API accessibility verified');
  return { baseUrl: BASE_URL };
}

export default function (data) {
  const baseUrl = data.baseUrl;
  
  group('Health and Monitoring Endpoints', () => {
    // Health check
    const healthResponse = makeRequest('GET', `${baseUrl}/health`);
    checkResponse(healthResponse, 200, 'Health check');
    
    if (healthResponse.status === 200) {
      const healthData = JSON.parse(healthResponse.body);
      check(healthData, {
        'Health - Service is healthy': (data) => data.status === 'healthy',
        'Health - Database is connected': (data) => data.database && data.database.status === 'connected',
      });
    }
    
    // Version info
    const versionResponse = makeRequest('GET', `${baseUrl}/version`);
    checkResponse(versionResponse, 200, 'Version info');
    
    // Metrics (sample every 10th iteration to avoid overwhelming)
    if (__ITER % 10 === 0) {
      const metricsResponse = makeRequest('GET', `${baseUrl}/metrics`);
      check(metricsResponse, {
        'Metrics - Available': (r) => r.status === 200,
        'Metrics - Contains HTTP metrics': (r) => r.body.includes('http_requests_total'),
        'Metrics - Contains DB metrics': (r) => r.body.includes('db_pool_'),
      });
    }
  });
  
  group('Project CRUD Operations', () => {
    let projectId;
    
    // Create project
    const projectData = generateProjectData();
    const idempotencyKey = generateIdempotencyKey();
    
    const createResponse = makeRequest(
      'POST',
      `${baseUrl}${API_PREFIX}/projects`,
      projectData,
      { 'Idempotency-Key': idempotencyKey }
    );
    
    if (checkResponse(createResponse, 200, 'Create project')) {
      const project = JSON.parse(createResponse.body);
      projectId = project.id;
      projectCreationCounter.add(1);
      
      check(project, {
        'Create - Project has ID': (p) => p.id !== undefined,
        'Create - Project name matches': (p) => p.name === projectData.name,
        'Create - Project has timestamps': (p) => p.created_at !== undefined,
      });
    }
    
    // Test idempotency (repeat same request)
    if (projectId) {
      const idempotentResponse = makeRequest(
        'POST',
        `${baseUrl}${API_PREFIX}/projects`,
        projectData,
        { 'Idempotency-Key': idempotencyKey }
      );
      
      if (checkResponse(idempotentResponse, 200, 'Idempotent create')) {
        const idempotentProject = JSON.parse(idempotentResponse.body);
        check(idempotentProject, {
          'Idempotency - Same project ID': (p) => p.id === projectId,
        });
      }
    }
    
    // Get project
    if (projectId) {
      const getResponse = makeRequest('GET', `${baseUrl}${API_PREFIX}/projects/${projectId}`);
      checkResponse(getResponse, 200, 'Get project');
      
      if (getResponse.status === 200) {
        const retrievedProject = JSON.parse(getResponse.body);
        check(retrievedProject, {
          'Get - Project ID matches': (p) => p.id === projectId,
          'Get - Project has required fields': (p) => p.name && p.description && p.status,
        });
      }
    }
    
    // Update project
    if (projectId) {
      const updateData = {
        description: `Updated by k6 test at ${new Date().toISOString()}`,
        status: 'active'
      };
      
      const updateResponse = makeRequest(
        'PATCH',
        `${baseUrl}${API_PREFIX}/projects/${projectId}`,
        updateData
      );
      
      checkResponse(updateResponse, 200, 'Update project');
      
      if (updateResponse.status === 200) {
        const updatedProject = JSON.parse(updateResponse.body);
        check(updatedProject, {
          'Update - Description updated': (p) => p.description === updateData.description,
          'Update - Status updated': (p) => p.status === updateData.status,
        });
      }
    }
    
    // List projects
    const listResponse = makeRequest('GET', `${baseUrl}${API_PREFIX}/projects?limit=10`);
    checkResponse(listResponse, 200, 'List projects');
    
    if (listResponse.status === 200) {
      const projectsList = JSON.parse(listResponse.body);
      const projects = Array.isArray(projectsList) ? projectsList : projectsList.items || [];
      
      check(projects, {
        'List - Returns array': (p) => Array.isArray(p),
        'List - Contains projects': (p) => p.length > 0,
      });
    }
  });
  
  group('Task Management and Critical Path', () => {
    // Use a project ID from previous group or create a minimal one
    let projectId;
    
    // Create a simple project for task testing
    const simpleProject = {
      name: `Task Test Project ${randomString(6)}`,
      description: 'Project for task testing',
      start_date: new Date().toISOString().split('T')[0],
      end_date: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
      status: 'planning',
      priority: 'medium'
    };
    
    const projectResponse = makeRequest(
      'POST',
      `${baseUrl}${API_PREFIX}/projects`,
      simpleProject,
      { 'Idempotency-Key': generateIdempotencyKey() }
    );
    
    if (projectResponse.status === 200) {
      projectId = JSON.parse(projectResponse.body).id;
      
      // Create tasks
      const taskData = generateTaskData();
      const taskResponse = makeRequest(
        'POST',
        `${baseUrl}${API_PREFIX}/projects/${projectId}/tasks`,
        taskData,
        { 'Idempotency-Key': generateIdempotencyKey() }
      );
      
      checkResponse(taskResponse, 200, 'Create task');
      
      // Test critical path calculation
      const criticalPathResponse = makeRequest(
        'GET',
        `${baseUrl}${API_PREFIX}/projects/${projectId}/critical-path`
      );
      
      if (checkResponse(criticalPathResponse, 200, 'Critical path calculation')) {
        criticalPathCalculations.add(1);
        
        const criticalPath = JSON.parse(criticalPathResponse.body);
        check(criticalPath, {
          'Critical Path - Has path array': (cp) => Array.isArray(cp.critical_path),
          'Critical Path - Has duration': (cp) => cp.total_duration_days !== undefined,
          'Critical Path - Has project ID': (cp) => cp.project_id === projectId,
        });
        
        // Test cache by making the same request again
        const cachedResponse = makeRequest(
          'GET',
          `${baseUrl}${API_PREFIX}/projects/${projectId}/critical-path`
        );
        
        if (cachedResponse.status === 200) {
          const cachedPath = JSON.parse(cachedResponse.body);
          const isCacheHit = JSON.stringify(cachedPath) === JSON.stringify(criticalPath);
          cacheHitRate.add(isCacheHit);
          
          check(cachedPath, {
            'Cache - Consistent results': (cp) => cp.project_id === projectId,
          });
        }
      }
      
      // Test cache invalidation
      const invalidateResponse = makeRequest(
        'DELETE',
        `${baseUrl}${API_PREFIX}/projects/${projectId}/critical-path/cache`
      );
      
      check(invalidateResponse, {
        'Cache Invalidation - Success': (r) => r.status === 200,
      });
    }
  });
  
  group('Error Handling', () => {
    // Test 404 error
    const notFoundResponse = makeRequest('GET', `${baseUrl}${API_PREFIX}/projects/99999`);
    check(notFoundResponse, {
      'Error - 404 for non-existent project': (r) => r.status === 404,
      'Error - Has error response': (r) => {
        try {
          const error = JSON.parse(r.body);
          return error.message || error.error || error.detail;
        } catch (e) {
          return false;
        }
      },
    });
    
    // Test validation error
    const invalidProject = { name: '' }; // Invalid data
    const validationResponse = makeRequest(
      'POST',
      `${baseUrl}${API_PREFIX}/projects`,
      invalidProject,
      { 'Idempotency-Key': generateIdempotencyKey() }
    );
    
    check(validationResponse, {
      'Error - Validation error status': (r) => r.status === 400 || r.status === 422,
      'Error - Has validation message': (r) => {
        try {
          const error = JSON.parse(r.body);
          return error.message || error.detail;
        } catch (e) {
          return false;
        }
      },
    });
  });
  
  // Random sleep between 0.1 and 1 second to simulate realistic user behavior
  sleep(Math.random() * 0.9 + 0.1);
}

export function teardown(data) {
  console.log('🏁 k6 smoke test completed');
  console.log('📊 Check the summary below for performance metrics');
}

// Handle test interruption gracefully
export function handleSummary(data) {
  const summary = {
    'smoke-test-results.json': JSON.stringify(data, null, 2),
  };
  
  // Log key metrics
  console.log('\n📈 Key Performance Metrics:');
  console.log(`- Total Requests: ${data.metrics.http_reqs.values.count}`);
  console.log(`- Failed Requests: ${data.metrics.http_req_failed.values.rate * 100}%`);
  console.log(`- Average Response Time: ${data.metrics.http_req_duration.values.avg.toFixed(2)}ms`);
  console.log(`- 95th Percentile: ${data.metrics.http_req_duration.values['p(95)'].toFixed(2)}ms`);
  console.log(`- Projects Created: ${data.metrics.projects_created ? data.metrics.projects_created.values.count : 0}`);
  console.log(`- Critical Path Calculations: ${data.metrics.critical_path_calculations ? data.metrics.critical_path_calculations.values.count : 0}`);
  
  return summary;
}