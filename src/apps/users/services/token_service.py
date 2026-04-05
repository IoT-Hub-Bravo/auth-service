import uuid
from datetime import datetime, timedelta, timezone

import jwt
from django.conf import settings


class TokenService:
    @staticmethod
    def issue_access_token(user) -> str:
        """
        Sign and return an RS256 JWT for the given user.
        Payload: sub, role, iat, exp, jti, kid (in header).
        """
        now = datetime.now(timezone.utc)
        exp = now + timedelta(seconds=settings.JWT_ACCESS_TOKEN_TTL)

        payload = {
            "sub": str(user.id),
            "role": user.role,
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
            "jti": str(uuid.uuid4()),
        }

        token = jwt.encode(
            payload,
            settings.JWT_PRIVATE_KEY,
            algorithm="RS256",
            headers={"kid": settings.JWT_KEY_ID},
        )
        return token, exp

    @staticmethod
    def decode_token(token: str) -> dict:
        """
        Decode and verify an RS256 JWT using the local public key.
        Raises jwt.ExpiredSignatureError or jwt.InvalidTokenError on failure.
        """
        return jwt.decode(
            token,
            settings.JWT_PUBLIC_KEY,
            algorithms=["RS256"],
        )
