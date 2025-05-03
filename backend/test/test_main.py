import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import os

from app.main import create_application, app


@pytest.fixture
def test_client():
    """Create a test client for the app"""
    return TestClient(app)


class TestMainApplication:
    def test_app_creation(self):
        """Test that the app is created with correct configuration"""
        test_app = create_application()
        assert test_app.title == "🌺Hibiscus Agent Registry API"
        assert test_app.version == "0.1.0"
        
        # Verify routers are included
        router_paths = [route.path for route in test_app.routes]
        assert "/agents/" in router_paths