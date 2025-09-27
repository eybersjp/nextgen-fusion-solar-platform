"""Tests for authentication API endpoints."""

import pytest
from fastapi.testclient import TestClient
from app.core.auth import AuthService


class TestAuthEndpoints:
    """Test authentication API endpoints."""
    
    def test_register_user_success(self, client: TestClient):
        """Test successful user registration."""
        user_data = {
            "email": "newuser@example.com",
            "password": "newpassword123",
            "full_name": "New User",
            "company": "New Company",
            "role": "engineer"
        }
        
        response = client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == user_data["email"]
        assert data["full_name"] == user_data["full_name"]
        assert "id" in data
        assert "password" not in data  # Password should not be returned
    
    def test_register_user_duplicate_email(self, client: TestClient, test_user):
        """Test registration with duplicate email."""
        user_data = {
            "email": test_user.email,
            "password": "newpassword123",
            "full_name": "Another User",
            "company": "Another Company",
            "role": "engineer"
        }
        
        response = client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == 400
        assert "already registered" in response.json()["error"].lower()
    
    def test_register_user_invalid_email(self, client: TestClient):
        """Test registration with invalid email."""
        user_data = {
            "email": "invalid-email",
            "password": "password123",
            "full_name": "Test User",
            "company": "Test Company",
            "role": "engineer"
        }
        
        response = client.post("/api/v1/auth/register", json=user_data)
        
        assert response.status_code == 422  # Validation error
    
    def test_login_success(self, client: TestClient, test_user, test_user_data):
        """Test successful user login."""
        login_data = {
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        }
        
        response = client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
        assert "user" in data
        assert data["user"]["email"] == test_user.email
    
    def test_login_invalid_credentials(self, client: TestClient, test_user):
        """Test login with invalid credentials."""
        login_data = {
            "email": test_user.email,
            "password": "wrongpassword"
        }
        
        response = client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 401
        assert "invalid credentials" in response.json()["error"].lower()
    
    def test_login_nonexistent_user(self, client: TestClient):
        """Test login with nonexistent user."""
        login_data = {
            "email": "nonexistent@example.com",
            "password": "password123"
        }
        
        response = client.post("/api/v1/auth/login", json=login_data)
        
        assert response.status_code == 401
        assert "invalid credentials" in response.json()["error"].lower()
    
    def test_refresh_token_success(self, client: TestClient, test_user, test_user_data):
        """Test successful token refresh."""
        # First login to get refresh token
        login_data = {
            "email": test_user_data["email"],
            "password": test_user_data["password"]
        }
        
        login_response = client.post("/api/v1/auth/login", json=login_data)
        refresh_token = login_response.json()["refresh_token"]
        
        # Use refresh token to get new access token
        refresh_data = {"refresh_token": refresh_token}
        response = client.post("/api/v1/auth/refresh", json=refresh_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
    
    def test_refresh_token_invalid(self, client: TestClient):
        """Test refresh with invalid token."""
        refresh_data = {"refresh_token": "invalid_token"}
        response = client.post("/api/v1/auth/refresh", json=refresh_data)
        
        assert response.status_code == 401
        assert "invalid" in response.json()["error"].lower()
    
    def test_get_profile_success(self, client: TestClient, auth_headers, test_user):
        """Test successful profile retrieval."""
        response = client.get("/api/v1/auth/profile", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
        assert data["full_name"] == test_user.full_name
        assert "id" in data
        assert "password" not in data
    
    def test_get_profile_unauthorized(self, client: TestClient):
        """Test profile retrieval without authentication."""
        response = client.get("/api/v1/auth/profile")
        
        assert response.status_code == 401
    
    def test_get_profile_invalid_token(self, client: TestClient):
        """Test profile retrieval with invalid token."""
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/api/v1/auth/profile", headers=headers)
        
        assert response.status_code == 401
    
    def test_update_profile_success(self, client: TestClient, auth_headers, test_user):
        """Test successful profile update."""
        update_data = {
            "full_name": "Updated Name",
            "company": "Updated Company"
        }
        
        response = client.put("/api/v1/auth/profile", json=update_data, headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == update_data["full_name"]
        assert data["company"] == update_data["company"]
        assert data["email"] == test_user.email  # Email should remain unchanged
    
    def test_change_password_success(self, client: TestClient, auth_headers, test_user_data):
        """Test successful password change."""
        password_data = {
            "current_password": test_user_data["password"],
            "new_password": "newpassword123"
        }
        
        response = client.post("/api/v1/auth/change-password", json=password_data, headers=auth_headers)
        
        assert response.status_code == 200
        assert "success" in response.json()["message"].lower()
    
    def test_change_password_wrong_current(self, client: TestClient, auth_headers):
        """Test password change with wrong current password."""
        password_data = {
            "current_password": "wrongpassword",
            "new_password": "newpassword123"
        }
        
        response = client.post("/api/v1/auth/change-password", json=password_data, headers=auth_headers)
        
        assert response.status_code == 400
        assert "current password" in response.json()["error"].lower()
    
    def test_logout_success(self, client: TestClient, auth_headers):
        """Test successful logout."""
        response = client.post("/api/v1/auth/logout", headers=auth_headers)
        
        assert response.status_code == 200
        assert "success" in response.json()["message"].lower()
    
    def test_logout_unauthorized(self, client: TestClient):
        """Test logout without authentication."""
        response = client.post("/api/v1/auth/logout")
        
        assert response.status_code == 401
    
    def test_request_password_reset(self, client: TestClient, test_user):
        """Test password reset request."""
        reset_data = {"email": test_user.email}
        
        response = client.post("/api/v1/auth/request-password-reset", json=reset_data)
        
        assert response.status_code == 200
        assert "sent" in response.json()["message"].lower()
    
    def test_request_password_reset_nonexistent_email(self, client: TestClient):
        """Test password reset request for nonexistent email."""
        reset_data = {"email": "nonexistent@example.com"}
        
        response = client.post("/api/v1/auth/request-password-reset", json=reset_data)
        
        # Should still return success for security reasons
        assert response.status_code == 200
        assert "sent" in response.json()["message"].lower()
    
    def test_verify_email_placeholder(self, client: TestClient):
        """Test email verification endpoint (placeholder)."""
        verify_data = {"token": "verification_token"}
        
        response = client.post("/api/v1/auth/verify-email", json=verify_data)
        
        # This is a placeholder implementation
        assert response.status_code == 200
        assert "verified" in response.json()["message"].lower()