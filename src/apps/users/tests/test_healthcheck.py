import pytest
from django.test import Client


@pytest.fixture
def client():
    return Client()


def test_healthcheck_returns_200(client):
    response = client.get("/api/health/")
    assert response.status_code == 200


def test_healthcheck_response_body(client):
    response = client.get("/api/health/")
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "auth-service"
