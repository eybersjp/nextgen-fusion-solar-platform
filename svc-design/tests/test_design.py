"""Tests for solar design API endpoints."""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime
from app.models.design import Design


class TestSolarDesignEndpoints:
    """Test solar design API endpoints."""
    
    def test_create_design_success(self, client: TestClient, auth_headers, test_project, test_design_data):
        """Test successful solar design creation."""
        # Update design data with project ID
        design_data = {**test_design_data, "project_id": str(test_project.id)}
        
        response = client.post("/api/v1/designs/", json=design_data, headers=auth_headers)
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == design_data["name"]
        assert data["project_id"] == design_data["project_id"]
        assert data["status"] == "draft"
        assert "id" in data
        assert "created_at" in data
    
    def test_create_design_unauthorized(self, client: TestClient, test_design_data):
        """Test design creation without authentication."""
        response = client.post("/api/v1/designs/", json=test_design_data)
        
        assert response.status_code == 401
    
    def test_create_design_invalid_project(self, client: TestClient, auth_headers, test_design_data):
        """Test design creation with invalid project ID."""
        design_data = {**test_design_data, "project_id": "00000000-0000-0000-0000-000000000000"}
        
        response = client.post("/api/v1/designs/", json=design_data, headers=auth_headers)
        
        assert response.status_code == 400
        assert "project" in response.json()["error"].lower()
    
    def test_create_design_invalid_data(self, client: TestClient, auth_headers, test_project):
        """Test design creation with invalid data."""
        invalid_data = {
            "name": "",  # Empty name should fail validation
            "project_id": str(test_project.id)
        }
        
        response = client.post("/api/v1/designs/", json=invalid_data, headers=auth_headers)
        
        assert response.status_code == 422  # Validation error
    
    def test_list_designs_success(self, client: TestClient, auth_headers, test_solar_design):
        """Test successful design listing."""
        response = client.get("/api/v1/designs/", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert len(data["items"]) >= 1
        
        # Check if our test design is in the list
        design_names = [d["name"] for d in data["items"]]
        assert test_solar_design.name in design_names
    
    def test_list_designs_with_filters(self, client: TestClient, auth_headers, test_solar_design, test_project):
        """Test design listing with filters."""
        # Test project filter
        response = client.get(f"/api/v1/designs/?project_id={test_project.id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        for design in data["items"]:
            assert design["project_id"] == str(test_project.id)
        
        # Test status filter
        response = client.get("/api/v1/designs/?status=draft", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        for design in data["items"]:
            assert design["status"] == "draft"
    
    def test_list_designs_with_pagination(self, client: TestClient, auth_headers):
        """Test design listing with pagination."""
        response = client.get("/api/v1/designs/?page=1&size=5", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["size"] == 5
        assert len(data["items"]) <= 5
    
    def test_list_designs_unauthorized(self, client: TestClient):
        """Test design listing without authentication."""
        response = client.get("/api/v1/designs/")
        
        assert response.status_code == 401
    
    def test_get_design_by_id_success(self, client: TestClient, auth_headers, test_solar_design):
        """Test successful design retrieval by ID."""
        response = client.get(f"/api/v1/designs/{test_solar_design.id}", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_solar_design.id)
        assert data["name"] == test_solar_design.name
        assert data["project_id"] == str(test_solar_design.project_id)
    
    def test_get_design_by_id_not_found(self, client: TestClient, auth_headers):
        """Test design retrieval with non-existent ID."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.get(f"/api/v1/designs/{fake_id}", headers=auth_headers)
        
        assert response.status_code == 404
        assert "not found" in response.json()["error"].lower()
    
    def test_get_design_by_id_invalid_uuid(self, client: TestClient, auth_headers):
        """Test design retrieval with invalid UUID."""
        response = client.get("/api/v1/designs/invalid-uuid", headers=auth_headers)
        
        assert response.status_code == 422  # Validation error
    
    def test_update_design_success(self, client: TestClient, auth_headers, test_solar_design):
        """Test successful design update."""
        update_data = {
            "name": "Updated Design Name",
            "description": "Updated description",
            "system_capacity_kw": 150.0,
            "annual_energy_kwh": 225000.0
        }
        
        response = client.put(f"/api/v1/designs/{test_solar_design.id}", json=update_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == update_data["name"]
        assert data["description"] == update_data["description"]
        assert data["system_capacity_kw"] == update_data["system_capacity_kw"]
        assert data["annual_energy_kwh"] == update_data["annual_energy_kwh"]
    
    def test_update_design_not_found(self, client: TestClient, auth_headers):
        """Test design update with non-existent ID."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        update_data = {"name": "Updated Name"}
        
        response = client.put(f"/api/v1/designs/{fake_id}", json=update_data, headers=auth_headers)
        
        assert response.status_code == 404
        assert "not found" in response.json()["error"].lower()
    
    def test_delete_design_success(self, client: TestClient, auth_headers, test_solar_design):
        """Test successful design deletion (soft delete)."""
        response = client.delete(f"/api/v1/designs/{test_solar_design.id}", headers=auth_headers)
        
        assert response.status_code == 200
        assert "deleted" in response.json()["message"].lower()
        
        # Verify design is soft deleted (should not appear in normal listings)
        list_response = client.get("/api/v1/designs/", headers=auth_headers)
        design_ids = [d["id"] for d in list_response.json()["items"]]
        assert str(test_solar_design.id) not in design_ids
    
    def test_delete_design_not_found(self, client: TestClient, auth_headers):
        """Test design deletion with non-existent ID."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = client.delete(f"/api/v1/designs/{fake_id}", headers=auth_headers)
        
        assert response.status_code == 404
        assert "not found" in response.json()["error"].lower()
    
    def test_duplicate_design_success(self, client: TestClient, auth_headers, test_solar_design):
        """Test successful design duplication."""
        duplicate_data = {"name": "Duplicated Design"}
        
        response = client.post(f"/api/v1/designs/{test_solar_design.id}/duplicate", json=duplicate_data, headers=auth_headers)
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == duplicate_data["name"]
        assert data["project_id"] == str(test_solar_design.project_id)
        assert data["id"] != str(test_solar_design.id)  # Should have different ID
        assert data["status"] == "draft"  # Duplicated design should be draft
    
    def test_duplicate_design_not_found(self, client: TestClient, auth_headers):
        """Test design duplication with non-existent ID."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        duplicate_data = {"name": "Duplicated Design"}
        
        response = client.post(f"/api/v1/designs/{fake_id}/duplicate", json=duplicate_data, headers=auth_headers)
        
        assert response.status_code == 404
        assert "not found" in response.json()["error"].lower()
    
    def test_approve_design_success(self, client: TestClient, auth_headers, test_solar_design):
        """Test successful design approval."""
        approval_data = {"comments": "Design looks good, approved for installation."}
        
        response = client.post(f"/api/v1/designs/{test_solar_design.id}/approve", json=approval_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "approved"
        assert "approved" in data["approval_status"]
    
    def test_approve_design_not_found(self, client: TestClient, auth_headers):
        """Test design approval with non-existent ID."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        approval_data = {"comments": "Approval comments"}
        
        response = client.post(f"/api/v1/designs/{fake_id}/approve", json=approval_data, headers=auth_headers)
        
        assert response.status_code == 404
        assert "not found" in response.json()["error"].lower()
    
    def test_reject_design_success(self, client: TestClient, auth_headers, test_solar_design):
        """Test successful design rejection."""
        rejection_data = {"comments": "Design needs modifications before approval."}
        
        response = client.post(f"/api/v1/designs/{test_solar_design.id}/reject", json=rejection_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "rejected"
        assert "rejected" in data["approval_status"]
    
    def test_validate_design_success(self, client: TestClient, auth_headers, test_solar_design):
        """Test successful design validation."""
        response = client.post(f"/api/v1/designs/{test_solar_design.id}/validate", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "validation_results" in data
        assert "is_valid" in data
        assert "errors" in data
        assert "warnings" in data
    
    def test_validate_design_not_found(self, client: TestClient, auth_headers):
        """Test design validation with non-existent ID."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        
        response = client.post(f"/api/v1/designs/{fake_id}/validate", headers=auth_headers)
        
        assert response.status_code == 404
        assert "not found" in response.json()["error"].lower()
    
    def test_calculate_performance_success(self, client: TestClient, auth_headers, test_solar_design):
        """Test successful design performance calculation."""
        response = client.post(f"/api/v1/designs/{test_solar_design.id}/calculate-performance", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "annual_energy_kwh" in data
        assert "monthly_energy" in data
        assert "performance_ratio" in data
        assert "capacity_factor" in data
        assert isinstance(data["annual_energy_kwh"], (int, float))
        assert isinstance(data["monthly_energy"], list)
        assert len(data["monthly_energy"]) == 12
    
    def test_calculate_performance_not_found(self, client: TestClient, auth_headers):
        """Test performance calculation with non-existent ID."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        
        response = client.post(f"/api/v1/designs/{fake_id}/calculate-performance", headers=auth_headers)
        
        assert response.status_code == 404
        assert "not found" in response.json()["error"].lower()
    
    def test_compare_designs_success(self, client: TestClient, auth_headers, test_solar_design, test_project):
        """Test successful design comparison."""
        # Create a second design for comparison
        design_data = {
            "name": "Comparison Design",
            "project_id": str(test_project.id),
            "system_capacity_kw": 150.0,
            "annual_energy_kwh": 225000.0,
            "system_type": "grid_tied",
            "design_stage": "concept"
        }
        
        create_response = client.post("/api/v1/designs/", json=design_data, headers=auth_headers)
        second_design_id = create_response.json()["id"]
        
        # Compare the two designs
        comparison_data = {
            "design_ids": [str(test_solar_design.id), second_design_id]
        }
        
        response = client.post("/api/v1/designs/compare", json=comparison_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "designs" in data
        assert "comparison_metrics" in data
        assert len(data["designs"]) == 2
        assert "system_size_comparison" in data["comparison_metrics"]
        assert "cost_comparison" in data["comparison_metrics"]
        assert "performance_comparison" in data["comparison_metrics"]
    
    def test_compare_designs_insufficient_designs(self, client: TestClient, auth_headers, test_solar_design):
        """Test design comparison with insufficient designs."""
        comparison_data = {
            "design_ids": [str(test_solar_design.id)]  # Only one design
        }
        
        response = client.post("/api/v1/designs/compare", json=comparison_data, headers=auth_headers)
        
        assert response.status_code == 400
        assert "at least 2 designs" in response.json()["error"].lower()
    
    def test_compare_designs_not_found(self, client: TestClient, auth_headers):
        """Test design comparison with non-existent designs."""
        fake_id1 = "00000000-0000-0000-0000-000000000000"
        fake_id2 = "11111111-1111-1111-1111-111111111111"
        
        comparison_data = {
            "design_ids": [fake_id1, fake_id2]
        }
        
        response = client.post("/api/v1/designs/compare", json=comparison_data, headers=auth_headers)
        
        assert response.status_code == 404
        assert "not found" in response.json()["error"].lower()
    
    def test_design_access_control(self, client: TestClient, test_solar_design):
        """Test design access control for different user roles."""
        # Test unauthorized access
        response = client.get(f"/api/v1/designs/{test_solar_design.id}")
        assert response.status_code == 401