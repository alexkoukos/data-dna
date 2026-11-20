from fastapi.testclient import TestClient

from brain.api_docs import STATIC_PATH
from brain.config import settings
from brain.main import app

client = TestClient(app)


def test_docs_is_the_branded_page() -> None:
    r = client.get("/docs")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    page = r.text
    assert f"{STATIC_PATH}/sentry.css" in page
    assert "swagger-ui-bundle.js" in page
    assert 'url: "/openapi.json"' in page
    assert "Brain API" in page
    assert f"Version {app.version}" in page
    assert f'href="{settings.web_url.rstrip("/")}/app"' in page


def test_docs_files_are_served() -> None:
    css = client.get(f"{STATIC_PATH}/sentry.css")
    assert css.status_code == 200
    assert "text/css" in css.headers["content-type"]
    for path in (
        "favicon.svg",
        "sentry-mark.svg",
        "fonts/GeistPixel-Square.woff2",
        "fonts/poppins-latin-400-normal.woff2",
        "fonts/poppins-latin-600-normal.woff2",
        "fonts/jetbrains-mono-latin-wght-normal.woff2",
    ):
        assert client.get(f"{STATIC_PATH}/{path}").status_code == 200, path
    # Every font the stylesheet asks for exists.
    for name in ("GeistPixel-Square", "poppins-latin-400", "poppins-latin-600", "jetbrains-mono"):
        assert f"fonts/{name}" in css.text


def test_docs_pages_stay_out_of_the_api_schema() -> None:
    paths = client.get("/openapi.json").json()["paths"]
    assert not any(p.startswith("/docs") for p in paths)


def test_swagger_oauth_redirect_still_works() -> None:
    r = client.get("/docs/oauth2-redirect")
    assert r.status_code == 200
    assert "oauth2" in r.text.lower()


def test_a_missing_docs_file_is_404_not_a_directory_listing() -> None:
    assert client.get(f"{STATIC_PATH}/").status_code == 404
    assert client.get(f"{STATIC_PATH}/../__init__.py").status_code == 404
