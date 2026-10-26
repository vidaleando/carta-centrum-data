"""API endpoints against the seeded test database (see fixtures/seed.sql)."""
from tests.conftest import requires_db

pytestmark = requires_db


def test_health(db_client):
    r = db_client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "healthy", "database": "connected"}


def test_datacentres(db_client):
    r = db_client.get("/api/datacentres")
    assert r.status_code == 200
    body = r.json()
    assert body["type"] == "FeatureCollection"
    assert [f["properties"]["name"] for f in body["features"]] == ["Alpha DC", "Beta DC", "Gamma DC"]
    assert body["features"][0] == {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [-0.1, 51.5]},
        "properties": {"id": "node/1", "name": "Alpha DC", "operator": "Alpha Ltd", "source": "OpenStreetMap"},
    }


def test_datacentres_limit_is_applied_in_sql(db_client):
    assert len(db_client.get("/api/datacentres?limit=2").json()["features"]) == 2
    assert db_client.get("/api/datacentres?limit=0").status_code == 422


def test_legacy_geojson_endpoint(db_client):
    assert db_client.get("/api/geojson?table_name=osm_data_centers").json() == db_client.get("/api/datacentres").json()
    assert len(db_client.get("/api/geojson?source=sample").json()["features"]) == 4
    assert db_client.get("/api/geojson?table_name=geo_data").status_code == 422


def test_constituency_mp_found_with_case_insensitive_join(db_client):
    r = db_client.get("/api/constituency-mp", params={"lat": 51.50, "lon": -0.10})
    assert r.json() == {
        "found": True,
        "constituency": "Riverside North",
        "mp_name": "Alex Example",
        "party": "Labour",
        "current_position": None,
        "source": "Local DB (ONS 2024 Boundaries)",
    }


def test_constituency_mp_includes_position(db_client):
    body = db_client.get("/api/constituency-mp", params={"lat": 51.55, "lon": -0.10}).json()
    assert body["mp_name"] == "Sam Sample"
    assert body["current_position"] == "Shadow Minister"


def test_constituency_mp_outside_all_constituencies(db_client):
    body = db_client.get("/api/constituency-mp", params={"lat": 48.0, "lon": 2.0}).json()
    assert body["found"] is False
    assert "not within" in body["message"]


def test_constituency_mp_validates_coordinates(db_client):
    assert db_client.get("/api/constituency-mp", params={"lat": "abc", "lon": 1}).status_code == 422


def test_constituency_by_name(db_client):
    features = db_client.get("/api/constituency/RIVERSIDE NORTH").json()["features"]
    assert len(features) == 1
    assert features[0]["properties"] == {"name": "Riverside North", "ons_code": "E14000001"}
    assert db_client.get("/api/constituency/Nowhere").json() == {"type": "FeatureCollection", "features": []}


def test_parliamentary_boundaries(db_client):
    features = db_client.get("/api/parliamentary-boundaries").json()["features"]
    assert [f["properties"] for f in features] == [
        {"name": "Riverside North", "code": "E14000001"},
        {"name": "Hillside South", "code": "E14000002"},
    ]


def test_counties_skip_unnamed_areas(db_client):
    features = db_client.get("/api/counties").json()["features"]
    assert [f["properties"]["name"] for f in features] == ["Westminster", "Berkshire"]
    assert features[0]["properties"]["parent_name"] == "England"


def test_admin_area_lookup(db_client):
    assert db_client.get("/api/constituency", params={"lat": 51.5, "lon": -0.1}).json() == {
        "found": True, "constituency": "Westminster", "type": "London Borough",
    }
    assert db_client.get("/api/constituency", params={"lat": 40, "lon": -70}).json() == {"found": False}


def test_removed_endpoints_are_gone(db_client):
    assert db_client.post("/api/geojson", json={}).status_code == 405
    assert db_client.get("/api/osm/pub").status_code == 404
    assert db_client.get("/api/parliamentary-constituencies").status_code == 404
