import time

import jwt
import pytest
from django.test import override_settings

from apps.users.services.token_service import TokenService


@pytest.fixture
def jwt_settings(rsa_key_pair):
    private_pem, public_pem = rsa_key_pair
    return {
        "JWT_PRIVATE_KEY": private_pem,
        "JWT_PUBLIC_KEY": public_pem,
        "JWT_ACCESS_TOKEN_TTL": 3600,
        "JWT_KEY_ID": "test-key-1",
    }


@pytest.mark.django_db
class TestIssueAccessToken:
    def test_returns_rs256_token(self, jwt_settings):
        from django.contrib.auth import get_user_model
        user = get_user_model().objects.create_user(
            username="tokenuser", email="token@example.com", password="pass"
        )
        with override_settings(**jwt_settings):
            token, exp = TokenService.issue_access_token(user)

        header = jwt.get_unverified_header(token)
        assert header["alg"] == "RS256"
        assert header["kid"] == "test-key-1"

    def test_payload_contains_required_claims(self, jwt_settings):
        from django.contrib.auth import get_user_model
        user = get_user_model().objects.create_user(
            username="claimuser", email="claim@example.com", password="pass"
        )
        with override_settings(**jwt_settings):
            token, exp = TokenService.issue_access_token(user)
            payload = TokenService.decode_token(token)

        assert payload["sub"] == str(user.id)
        assert payload["role"] == user.role
        assert "iat" in payload
        assert "exp" in payload
        assert "jti" in payload

    def test_token_is_verifiable_with_public_key(self, jwt_settings):
        from django.contrib.auth import get_user_model
        user = get_user_model().objects.create_user(
            username="verifyuser", email="verify@example.com", password="pass"
        )
        with override_settings(**jwt_settings):
            token, _ = TokenService.issue_access_token(user)
            payload = TokenService.decode_token(token)

        assert payload["sub"] == str(user.id)

    def test_expired_token_raises(self, jwt_settings):
        from django.contrib.auth import get_user_model
        user = get_user_model().objects.create_user(
            username="expireduser", email="expired@example.com", password="pass"
        )
        expired_settings = {**jwt_settings, "JWT_ACCESS_TOKEN_TTL": -1}
        with override_settings(**expired_settings):
            token, _ = TokenService.issue_access_token(user)

        with override_settings(**jwt_settings):
            with pytest.raises(jwt.ExpiredSignatureError):
                TokenService.decode_token(token)

    def test_tampered_token_raises(self, jwt_settings):
        from django.contrib.auth import get_user_model
        user = get_user_model().objects.create_user(
            username="tampereduser", email="tampered@example.com", password="pass"
        )
        with override_settings(**jwt_settings):
            token, _ = TokenService.issue_access_token(user)
            tampered = token[:-4] + "XXXX"
            with pytest.raises(jwt.InvalidTokenError):
                TokenService.decode_token(tampered)
