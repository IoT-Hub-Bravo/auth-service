import base64
import json

from cryptography.hazmat.primitives.serialization import load_pem_public_key
from django.conf import settings
from django.contrib.auth import authenticate
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

from apps.users.services.token_service import TokenService


def healthcheck(request):
    return JsonResponse({"status": "ok", "service": "auth-service"})


@csrf_exempt
def login(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    username = data.get("username")
    password = data.get("password")

    if not username or not isinstance(username, str):
        return JsonResponse({"error": "Username is required"}, status=400)
    if not password or not isinstance(password, str):
        return JsonResponse({"error": "Password is required"}, status=400)

    user = authenticate(request, username=username, password=password)
    if user is None:
        return JsonResponse({"error": "Invalid credentials"}, status=401)

    token, exp = TokenService.issue_access_token(user)
    return JsonResponse({
        "access_token": token,
        "token_type": "bearer",
        "expires_in": exp.isoformat().replace("+00:00", "Z"),
    })


@require_GET
def jwks(request):
    def _b64url(n: int) -> str:
        byte_len = (n.bit_length() + 7) // 8
        return base64.urlsafe_b64encode(n.to_bytes(byte_len, "big")).rstrip(b"=").decode()

    public_key = load_pem_public_key(settings.JWT_PUBLIC_KEY.encode())
    numbers = public_key.public_numbers()

    response = JsonResponse({
        "keys": [{
            "kty": "RSA",
            "use": "sig",
            "alg": "RS256",
            "kid": settings.JWT_KEY_ID,
            "n": _b64url(numbers.n),
            "e": _b64url(numbers.e),
        }]
    })
    response["Cache-Control"] = "public, max-age=3600"
    return response
