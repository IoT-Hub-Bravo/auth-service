import json

import pytest
from django.test import Client, override_settings


@pytest.fixture
def client():
    return Client()


@pytest.fixture
def jwt_settings(rsa_key_pair):
    private_pem, public_pem = rsa_key_pair
    return {
        "JWT_PRIVATE_KEY": private_pem,
        "JWT_PUBLIC_KEY": public_pem,
        "JWT_ACCESS_TOKEN_TTL": 3600,
        "JWT_KEY_ID": "test-key-1",
    }


@pytest.fixture
def user(db):
    from django.contrib.auth import get_user_model
    return get_user_model().objects.create_user(
        username="loginuser", email="login@example.com", password="correctpass"
    )


def post_login(client, body, content_type="application/json"):
    return client.post(
        "/api/auth/login/",
        data=json.dumps(body),
        content_type=content_type,
    )


@pytest.mark.django_db
class TestLoginView:
    def test_valid_credentials_returns_200_with_token(self, client, user, jwt_settings):
        with override_settings(**jwt_settings):
            response = post_login(client, {"username": "loginuser", "password": "correctpass"})

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data

    def test_wrong_password_returns_401(self, client, user, jwt_settings):
        with override_settings(**jwt_settings):
            response = post_login(client, {"username": "loginuser", "password": "wrongpass"})

        assert response.status_code == 401
        assert response.json()["error"] == "Invalid credentials"

    def test_unknown_user_returns_401(self, client, jwt_settings):
        with override_settings(**jwt_settings):
            response = post_login(client, {"username": "nobody", "password": "pass"})

        assert response.status_code == 401

    def test_missing_username_returns_400(self, client, jwt_settings):
        with override_settings(**jwt_settings):
            response = post_login(client, {"password": "pass"})

        assert response.status_code == 400
        assert "Username" in response.json()["error"]

    def test_missing_password_returns_400(self, client, jwt_settings):
        with override_settings(**jwt_settings):
            response = post_login(client, {"username": "loginuser"})

        assert response.status_code == 400
        assert "Password" in response.json()["error"]

    def test_invalid_json_returns_400(self, client):
        response = client.post(
            "/api/auth/login/",
            data="not-json",
            content_type="application/json",
        )
        assert response.status_code == 400
        assert "Invalid JSON" in response.json()["error"]

    def test_get_method_returns_405(self, client):
        response = client.get("/api/auth/login/")
        assert response.status_code == 405
