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


class TestJwksView:
    def test_returns_200(self, client, jwt_settings):
        with override_settings(**jwt_settings):
            response = client.get("/api/auth/.well-known/jwks.json")
        assert response.status_code == 200

    def test_response_contains_keys_array(self, client, jwt_settings):
        with override_settings(**jwt_settings):
            response = client.get("/api/auth/.well-known/jwks.json")
        data = response.json()
        assert "keys" in data
        assert len(data["keys"]) == 1

    def test_jwk_contains_required_fields(self, client, jwt_settings):
        with override_settings(**jwt_settings):
            response = client.get("/api/auth/.well-known/jwks.json")
        key = response.json()["keys"][0]
        assert key["kty"] == "RSA"
        assert key["use"] == "sig"
        assert key["alg"] == "RS256"
        assert key["kid"] == "test-key-1"
        assert "n" in key
        assert "e" in key

    def test_cache_control_header(self, client, jwt_settings):
        with override_settings(**jwt_settings):
            response = client.get("/api/auth/.well-known/jwks.json")
        assert "max-age=3600" in response["Cache-Control"]

    def test_post_method_not_allowed(self, client, jwt_settings):
        with override_settings(**jwt_settings):
            response = client.post("/api/auth/.well-known/jwks.json")
        assert response.status_code == 405
