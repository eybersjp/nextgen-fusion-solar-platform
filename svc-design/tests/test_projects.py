"""Tests for project management API endpoints."""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime


class TestProjectEndpoints:
    """Test project management API endpoints."""
    
    def test_create_project_success(self, client: TestClient, auth_headers, test_project_data):
        """Test successful project creation."""
        response = client.post("/api/v1/projects/", json=test_project_data, headers=auth_headers)
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == test_project_data["name"]
        assert data["description"] == test_project_data["description"]
        assert data["status"] == "planning"
        assert "id" in data
        assert "created_at" in data
    
    def test_create_project_unauthorized(self, client: TestClient, test_project_data):
        """Test project creation without authentication."""
        response = client.post("/api/v1/projects/", json=test_project_data)
        
        assert response.status_code == 401
    
    def test_create_project_invalid_data(self, client: TestClient, auth_headers):
        """Test project creation with invalid data."""
        invalid_data = {
            "name": "",  # Empty name should fail validation
            "description": "Test description"
        }
        
        response = client.post("/api/v1/projects/", json=invalid_data, headers=auth_headers)
        
        assert response.status_code == 422  # Validation error
    
    def test_list_projects_success(self, client: TestClient, auth_headers, test_project):
        """Test successful project listing."""
        response = client.get("/api/v1/projects/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert len(data["items"]) >= 1
        
        # Check if our test project is in the list
        project_names = [p["name"] for p in data["items"]]
        assert test_project.name in project_names
    
    def test_list_projects_with_filters(self, client: TestClient, auth_headers, test_project):
        """Test project listing with filters."""
        # Test status filter
        response = client.get("/api/v1/projects/?status=planning", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        for project in data["items"]:
            assert project["status"] == "planning"
    
    def test_list_projects_with_pagination(self, client: TestClient, auth_headers):
        """Test project listing with pagination."""
        response = client.get("/api/v1/projects/?page=1&size=5", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["size"] == 5
        assert len(data["items"]) <= 5
    
    def test_list_projects_unauthorized(self, client: TestClient):
        """Test project listing without authentication."""
        response = client.get("/api/v1/projects/")
        
        assert response.status_code == 401
    
    def test_get_project_statistics(self, client: TestClient, auth_headers, test_project):
        """Test project statistics retrieval."""
        response = client.get("/api/v1/projects/statistics", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "total_projects" in data
        assert "projects_by_status" in data
        assert "recent_activity" in data
        assert data["total_projects"] >= 1
    
    def test_get_project_by_id_success(self, client: TestClient, auth_headers, test_project):
        """Test successful project retrieval by ID."""
        response = client.get(f"/api/v1/projects/{test_project.id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_project.id)
        assert data["name"] == test_project.name
        assert data["description"] == test_project.description
    
    def test_get_project_by_id_not_found(self, client: TestClient, auth_headers):
        """Test project retrieval with non-existent ID."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.get(f"/api/v1/projects/{fake_id}", headers=auth_headers)
        
        assert response.status_code == 404
        assert "not found" in response.json()["error"].lower()
    
    def test_get_project_by_id_invalid_uuid(self, client: TestClient, auth_headers):
        """Test project retrieval with invalid UUID."""
        response = client.get("/api/v1/projects/invalid-uuid", headers=auth_headers)
        
        assert response.status_code == 422  # Validation error
    
    def test_update_project_success(self, client: TestClient, auth_headers, test_project):
        """Test successful project update."""
        update_data = {
            "name": "Updated Project Name",
            "description": "Updated description",
            "status": "in_progress"
        }
        
        response = client.put(f"/api/v1/projects/{test_project.id}", json=update_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == update_data["name"]
        assert data["description"] == update_data["description"]
        assert data["status"] == update_data["status"]
    
    def test_update_project_not_found(self, client: TestClient, auth_headers):
        """Test project update with non-existent ID."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        update_data = {"name": "Updated Name"}
        
        response = client.put(f"/api/v1/projects/{fake_id}", json=update_data, headers=auth_headers)
        
        assert response.status_code == 404
        assert "not found" in response.json()["error"].lower()
    
    def test_update_project_status_success(self, client: TestClient, auth_headers, test_project):
        """Test successful project status update."""
        status_data = {"status": "completed"}
        
        response = client.patch(f"/api/v1/projects/{test_project.id}/status", json=status_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
    
    def test_update_project_status_invalid(self, client: TestClient, auth_headers, test_project):
        """Test project status update with invalid status."""
        status_data = {"status": "invalid_status"}
        
        response = client.patch(f"/api/v1/projects/{test_project.id}/status", json=status_data, headers=auth_headers)
        
        assert response.status_code == 422  # Validation error
    
    def test_update_project_location_success(self, client: TestClient, auth_headers, test_project):
        """Test successful project location update."""
        location_data = {
            "address": "123 Updated Street",
            "city": "Updated City",
            "state": "Updated State",
            "country": "Updated Country",
            "postal_code": "12345",
            "latitude": -25.7479,
            "longitude": 28.2293
        }
        
        response = client.patch(f"/api/v1/projects/{test_project.id}/location", json=location_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["location"]["address"] == location_data["address"]
        assert data["location"]["city"] == location_data["city"]
    
    def test_update_project_tags_success(self, client: TestClient, auth_headers, test_project):
        """Test successful project tags update."""
        tags_data = {"tags": ["solar", "commercial", "rooftop"]}
        
        response = client.patch(f"/api/v1/projects/{test_project.id}/tags", json=tags_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert set(data["tags"]) == set(tags_data["tags"])
    
    def test_update_project_custom_fields_success(self, client: TestClient, auth_headers, test_project):
        """Test successful project custom fields update."""
        custom_fields_data = {
            "custom_fields": {
                "priority": "high",
                "budget": "100000",
                "deadline": "2024-12-31"
            }
        }
        
        response = client.patch(f"/api/v1/projects/{test_project.id}/custom-fields", json=custom_fields_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["custom_fields"]["priority"] == "high"
        assert data["custom_fields"]["budget"] == "100000"
    
    def test_delete_project_success(self, client: TestClient, auth_headers, test_project):
        """Test successful project deletion (soft delete)."""
        response = client.delete(f"/api/v1/projects/{test_project.id}", headers=auth_headers)
        
        assert response.status_code == 200
        assert "deleted" in response.json()["message"].lower()
        
        # Verify project is soft deleted (should not appear in normal listings)
        list_response = client.get("/api/v1/projects/", headers=auth_headers)
        project_ids = [p["id"] for p in list_response.json()["items"]]
        assert str(test_project.id) not in project_ids
    
    def test_delete_project_not_found(self, client: TestClient, auth_headers):
        """Test project deletion with non-existent ID."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.delete(f"/api/v1/projects/{fake_id}", headers=auth_headers)
        
        assert response.status_code == 404
        assert "not found" in response.json()["error"].lower()
    
    def test_duplicate_project_success(self, client: TestClient, auth_headers, test_project):
        """Test successful project duplication."""
        duplicate_data = {"name": "Duplicated Project"}
        
        response = client.post(f"/api/v1/projects/{test_project.id}/duplicate", json=duplicate_data, headers=auth_headers)
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == duplicate_data["name"]
        assert data["description"] == test_project.description
        assert data["id"] != str(test_project.id)  # Should have different ID
    
    def test_duplicate_project_not_found(self, client: TestClient, auth_headers):
        """Test project duplication with non-existent ID."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        duplicate_data = {"name": "Duplicated Project"}
        
        response = client.post(f"/api/v1/projects/{fake_id}/duplicate", json=duplicate_data, headers=auth_headers)
        
        assert response.status_code == 404
        assert "not found" in response.json()["error"].lower()
    
    def test_project_access_control(self, client: TestClient, test_project):
        """Test project access control for different user roles."""
        # Test with admin user should have full access
        # This would require creating admin user fixture and testing different permissions
        # For now, we'll test basic unauthorized access
        response = client.get(f"/api/v1/projects/{test_project.id}")
        assert response.status_code == 401