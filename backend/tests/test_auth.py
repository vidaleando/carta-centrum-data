"""Invite-only access: Supabase access tokens on the API, and the invite tool."""
import json
import time
from types import SimpleNamespace

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from tests.conftest import client_for
from tools.invite import InviteFailed, invite_link, send_invite

SUPABASE_URL = "https://example.supabase.co"
UNREACHABLE_DB = "postgresql://postgres:x@127.0.0.1:1/none"
SIGNING_KEY = ec.generate_private_key(ec.SECP256R1())


class FakeJWKS:
    """Stands in for PyJWKClient: always returns our test public key."""

    def __init__(self, private_key):
        self._key = SimpleNamespace(key=private_key.public_key())

    def get_signing_key_from_jwt(self, token):
        return self._key


def make_token(private_key=SIGNING_KEY, **overrides):
    claims = {
        "sub": "user-1",
        "email": "ada@example.com",
        "aud": "authenticated",
        "iss": f"{SUPABASE_URL}/auth/v1",
        "exp": int(time.time()) + 600,
        **overrides,
    }
    return jwt.encode(claims, private_key, algorithm="ES256")


@pytest.fixture
def auth_client():
    # An unreachable database: requests that pass auth get 503, not 401.
    with client_for(auth_enabled=True, supabase_url=SUPABASE_URL, database_url=UNREACHABLE_DB) as client:
        client.app.state.jwks = FakeJWKS(SIGNING_KEY)
        yield client


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def test_api_requires_a_token(auth_client):
    for path in ("/api/datacentres", "/api/geojson?source=sample", "/api/counties", "/api/constituency-mp?lat=51&lon=0"):
        r = auth_client.get(path)
        assert r.status_code == 401, path
        assert r.headers["www-authenticate"] == "Bearer"


def test_valid_token_is_accepted(auth_client):
    assert auth_client.get("/api/geojson?source=sample", headers=bearer(make_token())).status_code == 200
    # Past auth, on to the (unreachable) database.
    assert auth_client.get("/api/datacentres", headers=bearer(make_token())).status_code == 503


@pytest.mark.parametrize(
    "token",
    [
        make_token(exp=int(time.time()) - 60),
        make_token(aud="anon"),
        make_token(iss="https://other.supabase.co/auth/v1"),
        make_token(private_key=ec.generate_private_key(ec.SECP256R1())),
        "not-a-jwt",
    ],
    ids=["expired", "wrong-audience", "wrong-issuer", "wrong-key", "garbage"],
)
def test_bad_tokens_are_rejected(auth_client, token):
    r = auth_client.get("/api/datacentres", headers=bearer(token))
    assert r.status_code == 401
    assert r.json() == {"detail": "Invalid or expired session"}


def test_health_and_frontend_stay_open(auth_client):
    assert auth_client.get("/health").status_code == 503  # open, reporting the database
    assert auth_client.get("/api/nope").status_code == 404


def test_auth_is_off_by_default():
    with client_for(demo_mode=True) as client:
        assert client.get("/api/datacentres").status_code == 200


def test_auth_needs_a_supabase_url():
    with pytest.raises(ValueError, match="SUPABASE_URL"):
        with client_for(auth_enabled=True):
            pass


def _admin_client(handler):
    return httpx.Client(base_url=f"{SUPABASE_URL}/auth/v1", transport=httpx.MockTransport(handler))


def test_invite_link_falls_back_to_sign_in_link_for_existing_users():
    requested = []

    def handler(request):
        link_type = json.loads(request.content)["type"]
        requested.append(link_type)
        if link_type == "invite":
            return httpx.Response(422, json={"msg": "A user with this email address has already been registered"})
        return httpx.Response(200, json={"action_link": "https://example.supabase.co/auth/v1/verify?token=abc"})

    with _admin_client(handler) as client:
        assert invite_link(client, "ada@example.com", "https://site").endswith("token=abc")
    assert requested == ["invite", "magiclink"]


def test_send_invite_reports_supabase_errors():
    def handler(request):
        assert request.url.params["redirect_to"] == "https://site"
        return httpx.Response(429, json={"msg": "Email rate limit exceeded"})

    with _admin_client(handler) as client, pytest.raises(InviteFailed, match="rate limit"):
        send_invite(client, "ada@example.com", "https://site")
