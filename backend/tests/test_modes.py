"""Behaviour without a working database: explicit demo mode vs. an unreachable database."""
from tests.conftest import client_for

UNREACHABLE_DB = "postgresql://postgres:x@127.0.0.1:1/none"


def test_demo_mode_serves_fixture_data_without_a_database():
    with client_for(demo_mode=True) as client:
        assert client.get("/health").json() == {"status": "demo_mode", "database": "not_connected"}
        assert len(client.get("/api/datacentres").json()["features"]) == 4
        assert len(client.get("/api/geojson?source=sample").json()["features"]) == 4
        assert client.get("/api/constituency-mp?lat=51.5&lon=-0.1").json()["found"] is False
        for path in ("/api/parliamentary-boundaries", "/api/counties", "/api/constituency/Anywhere"):
            assert client.get(path).json() == {"type": "FeatureCollection", "features": []}
        assert client.get("/api/constituency?lat=51.5&lon=-0.1").json() == {"found": False}


def test_unreachable_database_returns_503_not_empty_data():
    with client_for(database_url=UNREACHABLE_DB) as client:
        health = client.get("/health")
        assert health.status_code == 503
        assert health.json() == {"status": "unhealthy", "database": "unavailable"}
        for path in (
            "/api/datacentres",
            "/api/counties",
            "/api/parliamentary-boundaries",
            "/api/constituency-mp?lat=51.5&lon=-0.1",
        ):
            r = client.get(path)
            assert r.status_code == 503, path
            assert r.json() == {"detail": "Database unavailable"}


def test_sample_data_does_not_need_the_database():
    # The frontend loads this on startup, so the page must render even when the DB is down.
    with client_for(database_url=UNREACHABLE_DB) as client:
        assert client.get("/api/geojson?source=sample").status_code == 200


def test_error_responses_do_not_leak_connection_details():
    with client_for(database_url=UNREACHABLE_DB) as client:
        assert "127.0.0.1" not in client.get("/api/datacentres").text
