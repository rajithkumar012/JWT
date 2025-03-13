from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
import jwt  # Import JWT for token manipulation
from datetime import datetime, timedelta
from django.conf import settings
from django.core.cache import cache  # Added for rate limit reset
from rest_framework_simplejwt.tokens import AccessToken

class AuthRateLimitTestCase(TestCase):
    def setUp(self):
        """Setup API client and register a test user"""
        self.client = APIClient()
        cache.clear()  # Reset rate limits before each test
        self.client.post("/api/register/", {"username": "testuser", "password": "testpass"})

    def test_valid_login(self):
        """Test successful login and token retrieval"""
        response = self.client.post("/api/login/", {"username": "testuser", "password": "testpass"})
        self.assertEqual(response.status_code, status.HTTP_200_OK, f"Login failed: {response.json()}")
        self.assertIn("access", response.json())
        self.assertIn("refresh", response.json())

    def test_protected_route_with_valid_token(self):
        """Test accessing protected route with a valid token"""
        login_response = self.client.post("/api/login/", {"username": "testuser", "password": "testpass"})
        self.assertEqual(login_response.status_code, status.HTTP_200_OK, f"Login failed: {login_response.json()}")

        access_token = login_response.json().get("access")
        response = self.client.get("/api/protected/", HTTP_AUTHORIZATION=f"Bearer {access_token}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

   

    def test_protected_route_with_expired_token(self):
        """Test accessing protected route with an expired token"""
        login_response = self.client.post("/api/login/", {"username": "testuser", "password": "testpass"}, format="json")
        self.assertEqual(login_response.status_code, status.HTTP_200_OK, f"Login failed: {login_response.json()}")

        # Generate an expired access token properly
        expired_token = AccessToken()
        expired_token.set_exp(from_time=datetime.utcnow() - timedelta(hours=2))  # Set expiration 2 hours ago

        response = self.client.get("/api/protected/", HTTP_AUTHORIZATION=f"Bearer {str(expired_token)}")
        print("EXPIRED TOKEN RESPONSE:", response.status_code, response.json())  # Debugging

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


    def test_rate_limit_within_limit(self):
        """Test making requests within the rate limit (should pass)"""
        login_response = self.client.post("/api/login/", {"username": "testuser", "password": "testpass"})
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)

        access_token = login_response.json().get("access")

        for _ in range(10):  # Reduce to 10 requests for testing
            response = self.client.get("/api/protected/", HTTP_AUTHORIZATION=f"Bearer {access_token}")
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_rate_limit_exceeded(self):
        """Test exceeding rate limit (should return 429)"""
        login_response = self.client.post("/api/login/", {"username": "testuser", "password": "testpass"})
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)

        access_token = login_response.json().get("access")

        for _ in range(100):  # Send 100 requests (allowed)
            self.client.get("/api/protected/", HTTP_AUTHORIZATION=f"Bearer {access_token}")

        response = self.client.get("/api/protected/", HTTP_AUTHORIZATION=f"Bearer {access_token}")
        self.assertEqual(response.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertIn("Rate limit exceeded", response.json().get("error", ""))
