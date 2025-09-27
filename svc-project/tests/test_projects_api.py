#!/usr/bin/env python3
"""
Automated pytest tests for NextGen Fusion Project Management API

This module contains comprehensive integration tests for:
- Project CRUD operations
- Task management
- Critical path analysis
- Metrics and monitoring
- Error handling and idempotency
- Database operations

Usage:
    pytest tests/test_projects_api.py -v
    pytest tests/test_projects_api.py::test_project_crud_and_metrics -v
"""

import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

import httpx
import pytest
from httpx import AsyncClient

# Test configuration
BASE_URL = "http://localhost:8003"
TIMEOUT = 30.0
API_PREFIX = "/api/v1"


class APITestClient:
    """Enhanced API test client with built-in error handling and logging"""
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.client: Optional[AsyncClient] = None
        self.project_id: Optional[str] = None
        self.task_id: Optional[str] = None
        self.idempotency_key = str(uuid.uuid4())
    
    async def __aenter__(self):
        self.client = AsyncClient(
            base_url=self.base_url,
            timeout=TIMEOUT,
            headers={"Content-Type": "application/json"}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()
    
    async def request(
        self,
        method: str,
        url: str,
        json_data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        expected_status: int = 200
    ) -> httpx.Response:
        """Make HTTP request with error handling"""
        request_headers = headers or {}
        
        response = await self.client.request(
            method=method,
            url=url,
            json=json_data,
            headers=request_headers
        )
        
        # Log request/response for debugging
        print(f"\n{method} {url} -> {response.status_code}")
        if json_data:
            print(f"Request: {json.dumps(json_data, indent=2)}")
        
        if response.status_code != expected_status:
            print(f"Response: {response.text}")
            response.raise_for_status()
        
        return response
    
    async def get(self, url: str, **kwargs) -> httpx.Response:
        return await self.request("GET", url, **kwargs)
    
    async def post(self, url: str, json_data: Dict[str, Any], **kwargs) -> httpx.Response:
        return await self.request("POST", url, json_data=json_data, **kwargs)
    
    async def patch(self, url: str, json_data: Dict[str, Any], **kwargs) -> httpx.Response:
        return await self.request("PATCH", url, json_data=json_data, **kwargs)
    
    async def delete(self, url: str, **kwargs) -> httpx.Response:
        return await self.request("DELETE", url, **kwargs)


@pytest.fixture
async def api_client():
    """Provide API test client"""
    async with APITestClient() as client:
        yield client


@pytest.mark.asyncio
async def test_health_and_version_endpoints(api_client: APITestClient):
    """Test basic health and version endpoints"""
    # Test health endpoint
    response = await api_client.get("/health")
    health_data = response.json()
    
    assert health_data["status"] == "healthy"
    assert health_data["service"] == "project-management"
    assert "timestamp" in health_data
    assert "database" in health_data
    
    # Test version endpoint
    response = await api_client.get("/version")
    version_data = response.json()
    
    assert version_data["service"] == "project-management"
    assert "version" in version_data
    assert "environment" in version_data
    assert "build_time" in version_data


@pytest.mark.asyncio
async def test_metrics_endpoint(api_client: APITestClient):
    """Test Prometheus metrics endpoint"""
    response = await api_client.get("/metrics")
    metrics_text = response.text
    
    # Check for required metrics
    assert "http_requests_total" in metrics_text
    assert "http_request_duration_seconds" in metrics_text
    assert "db_pool_" in metrics_text
    
    # Check for custom metrics
    expected_metrics = [
        "critical_path_cache_hits_total",
        "critical_path_calc_duration_seconds",
        "tenant_active_projects"
    ]
    
    for metric in expected_metrics:
        assert metric in metrics_text, f"Missing metric: {metric}"


@pytest.mark.asyncio
async def test_admin_runtime_endpoint(api_client: APITestClient):
    """Test admin runtime configuration endpoint"""
    response = await api_client.get("/admin/runtime")
    runtime_data = response.json()
    
    # Check required sections
    assert "service" in runtime_data
    assert "database" in runtime_data
    assert "cache" in runtime_data
    assert "features" in runtime_data
    assert "uptime_seconds" in runtime_data
    
    # Check database pool configuration
    db_config = runtime_data["database"]
    assert "pool_config" in db_config
    assert "connection_status" in db_config
    
    pool_config = db_config["pool_config"]
    required_pool_fields = ["max_size", "min_idle", "max_overflow", "pool_timeout"]
    for field in required_pool_fields:
        assert field in pool_config, f"Missing pool config field: {field}"
    
    # Check features
    features = runtime_data["features"]
    assert "idempotency_keys" in features
    assert "critical_path_caching" in features
    assert "structured_logging" in features


@pytest.mark.asyncio
async def test_project_crud_and_metrics(api_client: APITestClient):
    """Comprehensive test for project CRUD operations with metrics validation"""
    
    # 1. Create project with idempotency key
    project_data = {
        "name": "Alpha Plant - Pytest Integration Test",
        "description": "Test project created via pytest integration test",
        "start_date": datetime.now().strftime("%Y-%m-%d"),
        "end_date": (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d"),
        "status": "planning",
        "priority": "high"
    }
    
    headers = {"Idempotency-Key": api_client.idempotency_key}
    response = await api_client.post(f"{API_PREFIX}/projects", project_data, headers=headers)
    
    project = response.json()
    api_client.project_id = project["id"]
    
    assert project["name"] == project_data["name"]
    assert project["description"] == project_data["description"]
    assert project["status"] == project_data["status"]
    assert project["priority"] == project_data["priority"]
    assert "id" in project
    assert "created_at" in project
    
    # 2. Test idempotency - same request should return same project
    response2 = await api_client.post(f"{API_PREFIX}/projects", project_data, headers=headers)
    project2 = response2.json()
    
    assert project2["id"] == project["id"]
    assert project2["name"] == project["name"]
    
    # 3. Get project by ID
    response = await api_client.get(f"{API_PREFIX}/projects/{api_client.project_id}")
    retrieved_project = response.json()
    
    assert retrieved_project["id"] == api_client.project_id
    assert retrieved_project["name"] == project_data["name"]
    
    # 4. Update project
    update_data = {
        "description": f"Updated description via pytest - {datetime.now().isoformat()}",
        "status": "active"
    }
    
    response = await api_client.patch(f"{API_PREFIX}/projects/{api_client.project_id}", update_data)
    updated_project = response.json()
    
    assert updated_project["description"] == update_data["description"]
    assert updated_project["status"] == update_data["status"]
    assert updated_project["id"] == api_client.project_id
    
    # 5. List projects
    response = await api_client.get(f"{API_PREFIX}/projects?limit=10")
    projects_list = response.json()
    
    # Handle both array and paginated response formats
    if isinstance(projects_list, list):
        projects = projects_list
    else:
        projects = projects_list.get("items", [])
    
    assert len(projects) > 0
    project_ids = [p["id"] for p in projects]
    assert api_client.project_id in project_ids
    
    # 6. Create a task for the project
    task_data = {
        "name": "Solar Array Layout Design",
        "description": "Design optimal solar panel array layout for maximum efficiency",
        "depends_on": [],
        "estimated_hours": 40,
        "priority": "high",
        "status": "todo"
    }
    
    task_headers = {"Idempotency-Key": str(uuid.uuid4())}
    response = await api_client.post(
        f"{API_PREFIX}/projects/{api_client.project_id}/tasks",
        task_data,
        headers=task_headers
    )
    
    task = response.json()
    api_client.task_id = task["id"]
    
    assert task["name"] == task_data["name"]
    assert task["description"] == task_data["description"]
    assert task["estimated_hours"] == task_data["estimated_hours"]
    assert "id" in task
    
    # 7. Test critical path analysis
    response = await api_client.get(f"{API_PREFIX}/projects/{api_client.project_id}/critical-path")
    critical_path = response.json()
    
    assert "critical_path" in critical_path
    assert "total_duration_days" in critical_path
    assert "project_id" in critical_path
    assert isinstance(critical_path["critical_path"], list)
    assert critical_path["project_id"] == api_client.project_id
    
    # 8. Test cache invalidation
    response = await api_client.delete(
        f"{API_PREFIX}/projects/{api_client.project_id}/critical-path/cache",
        expected_status=200
    )
    cache_result = response.json()
    
    assert "message" in cache_result or "status" in cache_result
    
    # 9. Verify metrics were updated
    response = await api_client.get("/metrics")
    metrics_text = response.text
    
    # Check that HTTP request metrics include our endpoints
    assert 'route="/api/v1/projects"' in metrics_text
    assert 'method="POST"' in metrics_text
    assert 'method="GET"' in metrics_text
    assert 'method="PATCH"' in metrics_text


@pytest.mark.asyncio
async def test_error_handling_and_validation(api_client: APITestClient):
    """Test error handling and validation scenarios"""
    
    # 1. Test 404 error for non-existent project
    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await api_client.get(f"{API_PREFIX}/projects/99999", expected_status=404)
    
    assert exc_info.value.response.status_code == 404
    
    # 2. Test validation error for invalid project data
    invalid_data = {
        "name": "",  # Empty name should cause validation error
        "description": "Test"
    }
    
    with pytest.raises(httpx.HTTPStatusError) as exc_info:
        await api_client.post(f"{API_PREFIX}/projects", invalid_data, expected_status=422)
    
    assert exc_info.value.response.status_code in [400, 422]
    
    # 3. Test error response format
    try:
        await api_client.get(f"{API_PREFIX}/projects/invalid-id")
    except httpx.HTTPStatusError as e:
        error_response = e.response.json()
        
        # Check error envelope format
        assert "code" in error_response or "error" in error_response
        assert "message" in error_response
        # Should include trace ID for debugging
        assert "traceId" in error_response or "trace_id" in error_response or "request_id" in error_response


@pytest.mark.asyncio
async def test_database_operations_and_pooling(api_client: APITestClient):
    """Test database operations and connection pooling"""
    
    # 1. Check database health
    response = await api_client.get("/health")
    health_data = response.json()
    
    assert health_data["database"]["status"] == "connected"
    assert "pool_stats" in health_data["database"]
    
    # 2. Check runtime database configuration
    response = await api_client.get("/admin/runtime")
    runtime_data = response.json()
    
    db_config = runtime_data["database"]
    assert db_config["connection_status"] == "healthy"
    
    pool_config = db_config["pool_config"]
    assert pool_config["max_size"] > 0
    assert pool_config["min_idle"] >= 0
    assert pool_config["pool_timeout"] > 0
    
    # 3. Test concurrent database operations
    # Create multiple projects concurrently to test pool handling
    async def create_test_project(index: int) -> Dict[str, Any]:
        project_data = {
            "name": f"Concurrent Test Project {index}",
            "description": f"Project created in concurrent test {index}",
            "start_date": datetime.now().strftime("%Y-%m-%d"),
            "end_date": (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d"),
            "status": "planning",
            "priority": "medium"
        }
        
        headers = {"Idempotency-Key": str(uuid.uuid4())}
        response = await api_client.post(f"{API_PREFIX}/projects", project_data, headers=headers)
        return response.json()
    
    # Create 5 projects concurrently
    tasks = [create_test_project(i) for i in range(5)]
    projects = await asyncio.gather(*tasks)
    
    # Verify all projects were created successfully
    assert len(projects) == 5
    for i, project in enumerate(projects):
        assert project["name"] == f"Concurrent Test Project {i}"
        assert "id" in project
    
    # 4. Check metrics after concurrent operations
    response = await api_client.get("/metrics")
    metrics_text = response.text
    
    # Should have database pool metrics
    assert "db_pool_in_use" in metrics_text
    assert "db_pool_size" in metrics_text
    assert "db_acquire_seconds" in metrics_text


@pytest.mark.asyncio
async def test_caching_and_performance(api_client: APITestClient):
    """Test caching functionality and performance metrics"""
    
    # 1. Create a project with tasks for critical path testing
    project_data = {
        "name": "Cache Performance Test Project",
        "description": "Project for testing critical path caching",
        "start_date": datetime.now().strftime("%Y-%m-%d"),
        "end_date": (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%d"),
        "status": "planning",
        "priority": "high"
    }
    
    headers = {"Idempotency-Key": str(uuid.uuid4())}
    response = await api_client.post(f"{API_PREFIX}/projects", project_data, headers=headers)
    project = response.json()
    project_id = project["id"]
    
    # 2. Create multiple tasks to make critical path calculation meaningful
    tasks_data = [
        {
            "name": "Site Survey",
            "description": "Initial site survey and assessment",
            "depends_on": [],
            "estimated_hours": 16,
            "priority": "high",
            "status": "todo"
        },
        {
            "name": "Design Phase",
            "description": "Solar array design and engineering",
            "depends_on": [],  # Will be updated after first task is created
            "estimated_hours": 40,
            "priority": "high",
            "status": "todo"
        },
        {
            "name": "Permitting",
            "description": "Obtain necessary permits",
            "depends_on": [],
            "estimated_hours": 24,
            "priority": "medium",
            "status": "todo"
        }
    ]
    
    created_tasks = []
    for task_data in tasks_data:
        task_headers = {"Idempotency-Key": str(uuid.uuid4())}
        response = await api_client.post(
            f"{API_PREFIX}/projects/{project_id}/tasks",
            task_data,
            headers=task_headers
        )
        created_tasks.append(response.json())
    
    # 3. Test critical path calculation (first call - should calculate and cache)
    start_time = datetime.now()
    response = await api_client.get(f"{API_PREFIX}/projects/{project_id}/critical-path")
    first_call_duration = (datetime.now() - start_time).total_seconds()
    
    critical_path_1 = response.json()
    assert "critical_path" in critical_path_1
    assert "total_duration_days" in critical_path_1
    
    # 4. Test critical path calculation (second call - should use cache)
    start_time = datetime.now()
    response = await api_client.get(f"{API_PREFIX}/projects/{project_id}/critical-path")
    second_call_duration = (datetime.now() - start_time).total_seconds()
    
    critical_path_2 = response.json()
    
    # Results should be identical
    assert critical_path_1 == critical_path_2
    
    # Second call should be faster (cached)
    # Note: This might not always be true in test environment, so we'll just log it
    print(f"First call: {first_call_duration:.3f}s, Second call: {second_call_duration:.3f}s")
    
    # 5. Test cache invalidation
    response = await api_client.delete(f"{API_PREFIX}/projects/{project_id}/critical-path/cache")
    cache_result = response.json()
    assert "message" in cache_result or "status" in cache_result
    
    # 6. Verify cache metrics
    response = await api_client.get("/metrics")
    metrics_text = response.text
    
    # Should have cache-related metrics
    assert "critical_path_cache_hits_total" in metrics_text
    assert "critical_path_cache_misses_total" in metrics_text
    assert "critical_path_calc_duration_seconds" in metrics_text


if __name__ == "__main__":
    # Run tests directly
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--asyncio-mode=auto"
    ])