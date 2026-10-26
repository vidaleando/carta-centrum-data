"""Serving the built frontend."""
import pytest

from tests.conftest import client_for


@pytest.fixture
def build_dir(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<!doctype html><title>app</title>")
    (tmp_path / "sw.js").write_text("self.addEventListener('fetch', () => {});")
    (tmp_path / "manifest.json").write_text("{}")
    (tmp_path / "assets" / "index-abc123.js").write_text("console.log(1);")
    (tmp_path.parent / "secret.txt").write_text("outside the build dir")
    return tmp_path


@pytest.fixture
def client(build_dir):
    with client_for(demo_mode=True, frontend_build_dir=build_dir) as client:
        yield client


def test_root_serves_index_without_caching(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "<title>app</title>" in r.text
    assert r.headers["cache-control"] == "no-cache"


def test_client_side_routes_fall_back_to_index(client):
    assert "<title>app</title>" in client.get("/map/some/view").text


@pytest.mark.parametrize("path, content_type", [
    ("/sw.js", "javascript"),
    ("/manifest.json", "application/json"),
    ("/assets/index-abc123.js", "javascript"),
])
def test_real_files_are_served_with_their_own_type(client, path, content_type):
    r = client.get(path)
    assert r.status_code == 200
    assert content_type in r.headers["content-type"]
    assert "<title>" not in r.text


def test_service_worker_is_not_cached(client):
    assert client.get("/sw.js").headers["cache-control"] == "no-cache"


@pytest.mark.parametrize("path", ["/assets/missing.js", "/api/unknown"])
def test_reserved_paths_404_instead_of_returning_index(client, path):
    assert client.get(path).status_code == 404


@pytest.mark.parametrize("path", ["/../secret.txt", "/%2e%2e/secret.txt", "/assets/../../secret.txt"])
def test_paths_outside_the_build_dir_are_not_served(client, path):
    assert "outside the build dir" not in client.get(path).text


def test_api_docs_are_not_shadowed(client):
    assert client.get("/openapi.json").status_code == 200


def test_missing_build_reports_api_only_mode(tmp_path):
    with client_for(demo_mode=True, frontend_build_dir=tmp_path / "nope") as client:
        assert client.get("/").json() == {"message": "API is running. Frontend not built."}
