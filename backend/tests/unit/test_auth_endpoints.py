"""
Unit tests for authentication API endpoints.
Tests login, token management, and user authentication flows.
"""
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import status
from datetime import datetime, timedelta
import jwt

from routers.auth import router
from fastapi import FastAPI

# Create test app with auth router
app = FastAPI()
app.include_router(router)
client = TestClient(app)


class TestAuthToken:
    """Test /token endpoint (OAuth2 compatible)."""
    
    @patch('routers.auth.authenticate_user')
    @patch('routers.auth.create_access_token')
    @patch('routers.auth.get_db')
    def test_successful_login(self, mock_db, mock_create_token, mock_auth_user):
        """Should return token on successful authentication."""
        # Mock successful authentication
        mock_auth_user.return_value = {
            "username": "thomas",
            "email": "thomas@example.com",
            "full_name": "Thomas Test"
        }
        mock_create_token.return_value = "fake-jwt-token"
        mock_db.return_value = MagicMock()
        
        response = client.post(
            "/api/v1/auth/token",
            data={"username": "thomas", "password": "password123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["access_token"] == "fake-jwt-token"
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
    
    @patch('routers.auth.authenticate_user')
    @patch('routers.auth.get_db')
    def test_failed_login_wrong_credentials(self, mock_db, mock_auth_user):
        """Should return 401 for invalid credentials."""
        mock_auth_user.return_value = None  # Authentication failed
        mock_db.return_value = MagicMock()
        
        response = client.post(
            "/api/v1/auth/token",
            data={"username": "thomas", "password": "wrongpassword"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Incorrect username or password" in response.json()["detail"]
    
    def test_login_missing_credentials(self):
        """Should return 422 for missing credentials."""
        response = client.post("/api/v1/auth/token")
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestAuthLogin:
    """Test /login endpoint (JSON payload)."""
    
    @patch('routers.auth.authenticate_user')
    @patch('routers.auth.create_access_token')
    @patch('routers.auth.get_db')
    def test_successful_json_login(self, mock_db, mock_create_token, mock_auth_user):
        """Should return token on successful JSON login."""
        mock_auth_user.return_value = {
            "username": "katia",
            "email": "katia@example.com"
        }
        mock_create_token.return_value = "fake-jwt-token-json"
        mock_db.return_value = MagicMock()
        
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "katia", "password": "password456"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["access_token"] == "fake-jwt-token-json"
        assert data["token_type"] == "bearer"
    
    @patch('routers.auth.authenticate_user')
    @patch('routers.auth.get_db')
    def test_failed_json_login(self, mock_db, mock_auth_user):
        """Should return 401 for invalid JSON credentials."""
        mock_auth_user.return_value = None
        mock_db.return_value = MagicMock()
        
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "katia", "password": "wrongpassword"}
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_login_invalid_json(self):
        """Should return 422 for invalid JSON payload."""
        response = client.post(
            "/api/v1/auth/login",
            json={"invalid": "payload"}
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestCurrentUser:
    """Test /me endpoint."""
    
    @patch('routers.auth.get_current_user')
    def test_get_current_user_info(self, mock_get_user):
        """Should return current user information."""
        mock_get_user.return_value = {
            "username": "thomas",
            "email": "thomas@example.com",
            "full_name": "Thomas Test User",
            "disabled": False
        }
        
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer fake-token"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["username"] == "thomas"
        assert data["email"] == "thomas@example.com"
        assert data["full_name"] == "Thomas Test User"
        assert data["disabled"] == False
    
    def test_get_current_user_unauthorized(self):
        """Should return 401 without valid token."""
        response = client.get("/api/v1/auth/me")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestTokenRefresh:
    """Test /refresh endpoint."""
    
    @patch('routers.auth.get_current_user')
    @patch('routers.auth.create_access_token')
    def test_successful_token_refresh(self, mock_create_token, mock_get_user):
        """Should return new token on successful refresh."""
        mock_get_user.return_value = {"username": "thomas"}
        mock_create_token.return_value = "new-refreshed-token"
        
        response = client.post(
            "/api/v1/auth/refresh",
            headers={"Authorization": "Bearer old-token"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["access_token"] == "new-refreshed-token"
        assert data["token_type"] == "bearer"
        mock_create_token.assert_called_once()
    
    def test_token_refresh_unauthorized(self):
        """Should return 401 without valid token."""
        response = client.post("/api/v1/auth/refresh")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestLogout:
    """Test /logout endpoint."""
    
    @patch('routers.auth.get_current_user')
    def test_successful_logout(self, mock_get_user):
        """Should return success message on logout."""
        mock_get_user.return_value = {"username": "thomas"}
        
        response = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": "Bearer valid-token"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "Successfully logged out" in data["message"]
        assert "JWT tokens are stateless" in data["note"]
    
    def test_logout_unauthorized(self):
        """Should return 401 without valid token."""
        response = client.post("/api/v1/auth/logout")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestTokenValidation:
    """Test /validate endpoint."""
    
    @patch('routers.auth.get_current_user')
    def test_valid_token_validation(self, mock_get_user):
        """Should confirm valid token."""
        mock_get_user.return_value = {
            "username": "thomas",
            "email": "thomas@example.com",
            "full_name": "Thomas Test"
        }
        
        response = client.get(
            "/api/v1/auth/validate",
            headers={"Authorization": "Bearer valid-token"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["valid"] == True
        assert data["user"]["username"] == "thomas"
        assert data["message"] == "Token is valid"
    
    def test_invalid_token_validation(self):
        """Should return 401 for invalid token."""
        response = client.get("/api/v1/auth/validate")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestAuthHealth:
    """Test /health endpoint."""
    
    @patch('routers.auth.validate_jwt_key_consistency')
    def test_healthy_auth_service(self, mock_validate_jwt):
        """Should return healthy status."""
        mock_validate_jwt.return_value = True
        
        response = client.get("/api/v1/auth/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "authentication"
        assert data["jwt_key_valid"] == True
        assert "timestamp" in data
    
    @patch('routers.auth.validate_jwt_key_consistency')
    def test_auth_service_jwt_warning(self, mock_validate_jwt):
        """Should return warning status for JWT issues."""
        mock_validate_jwt.return_value = False
        
        response = client.get("/api/v1/auth/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "warning"
        assert data["jwt_key_valid"] == False
    
    @patch('routers.auth.validate_jwt_key_consistency')
    def test_auth_service_error(self, mock_validate_jwt):
        """Should handle errors gracefully."""
        mock_validate_jwt.side_effect = Exception("JWT validation failed")
        
        response = client.get("/api/v1/auth/health")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "error"
        assert "JWT validation failed" in data["error"]


class TestDebugEndpoint:
    """Test /debug endpoint (development only)."""
    
    @patch('routers.auth.settings')
    @patch('routers.auth.get_current_user')
    def test_debug_in_development(self, mock_get_user, mock_settings):
        """Should return debug info in development."""
        mock_settings.environment = "development"
        mock_get_user.return_value = {"username": "thomas"}
        
        with patch('routers.auth.debug_jwt_validation') as mock_debug:
            mock_debug.return_value = {"token_info": "debug_data"}
            
            response = client.post(
                "/api/v1/auth/debug",
                json={"test_mode": True},
                headers={"Authorization": "Bearer valid-token"}
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "debug_info" in data
            assert "current_user" in data
            assert "jwt_settings" in data
    
    @patch('routers.auth.settings')
    def test_debug_disabled_in_production(self, mock_settings):
        """Should return 404 in production."""
        mock_settings.environment = "production"
        
        response = client.post(
            "/api/v1/auth/debug",
            json={"test_mode": True},
            headers={"Authorization": "Bearer valid-token"}
        )
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not available in production" in response.json()["detail"]


class TestAuthErrorHandling:
    """Test error handling in authentication endpoints."""
    
    @patch('routers.auth.authenticate_user')
    @patch('routers.auth.get_db')
    def test_login_internal_error(self, mock_db, mock_auth_user):
        """Should handle internal errors gracefully."""
        mock_auth_user.side_effect = Exception("Database connection failed")
        mock_db.return_value = MagicMock()
        
        response = client.post(
            "/api/v1/auth/token",
            data={"username": "thomas", "password": "password123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Internal authentication error" in response.json()["detail"]
    
    @patch('routers.auth.get_current_user')
    @patch('routers.auth.create_access_token')
    def test_refresh_token_error(self, mock_create_token, mock_get_user):
        """Should handle token refresh errors."""
        mock_get_user.return_value = {"username": "thomas"}
        mock_create_token.side_effect = Exception("Token creation failed")
        
        response = client.post(
            "/api/v1/auth/refresh",
            headers={"Authorization": "Bearer valid-token"}
        )
        
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Token refresh failed" in response.json()["detail"]


class TestAuthSecurityHeaders:
    """Test security-related headers and responses."""
    
    @patch('routers.auth.authenticate_user')
    @patch('routers.auth.get_db')
    def test_unauthorized_response_headers(self, mock_db, mock_auth_user):
        """Should include WWW-Authenticate header on 401."""
        mock_auth_user.return_value = None
        mock_db.return_value = MagicMock()
        
        response = client.post(
            "/api/v1/auth/token",
            data={"username": "invalid", "password": "invalid"},
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "WWW-Authenticate" in response.headers
        assert response.headers["WWW-Authenticate"] == "Bearer"
    
    def test_token_response_structure(self):
        """Should return properly structured token response."""
        with patch('routers.auth.authenticate_user') as mock_auth, \
             patch('routers.auth.create_access_token') as mock_token, \
             patch('routers.auth.get_db'):
            
            mock_auth.return_value = {"username": "thomas"}
            mock_token.return_value = "test-jwt-token"
            
            response = client.post(
                "/api/v1/auth/token",
                data={"username": "thomas", "password": "password123"},
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            
            # Verify OAuth2 compliance
            required_fields = ["access_token", "token_type", "expires_in"]
            for field in required_fields:
                assert field in data
            
            assert data["token_type"] == "bearer"
            assert isinstance(data["expires_in"], int)
            assert data["expires_in"] > 0