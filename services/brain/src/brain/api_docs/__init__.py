"""The API docs page (/docs): Swagger UI dressed in the Sentry brand.

FastAPI's stock page is turned off in main.py; this one loads the same Swagger UI bundle and adds
the brand's colours, fonts and logo from files served next to it, so nothing but Swagger itself
comes from outside.
"""

import html
from pathlib import Path

from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_oauth2_redirect_html
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from brain.config import settings

STATIC_DIR = Path(__file__).parent / "static"
STATIC_PATH = "/docs/static"
SWAGGER = "https://cdn.jsdelivr.net/npm/swagger-ui-dist@5"

_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} API · Sentry</title>
<link rel="icon" href="{static}/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="{swagger}/swagger-ui.css">
<link rel="stylesheet" href="{static}/sentry.css">
</head>
<body>
<a class="sd-skip" href="#swagger-ui">Skip to the endpoints</a>
<header class="sd-bar">
  <a class="sd-logo" href="{web}" aria-label="Sentry home">
    <img src="{static}/sentry-mark.svg" alt="" width="26" height="30">
    <span>Sentry</span>
  </a>
  <nav class="sd-nav" aria-label="Main">
    <a href="{web}/how-it-works">How it works</a>
    <a href="{web}/security">Security dashboard</a>
    <a class="sd-cta" href="{web}/app">Open the app</a>
  </nav>
</header>
<main>
  <section class="sd-hero" aria-labelledby="sd-title">
    <p class="sd-eyebrow">Developers</p>
    <h1 id="sd-title">Brain API</h1>
    <p class="sd-lead">Every endpoint the gate, the dashboard and the extension use. Open one and
      press <strong>Try it out</strong>: the request goes to the brain on this machine, nowhere
      else.</p>
    <ul class="sd-meta" aria-label="About this API">
      <li>Version {version}</li>
      <li>OpenAPI {openapi}</li>
      <li><a href="{openapi_url}">openapi.json</a></li>
      <li><a href="/redoc">Read-only view</a></li>
    </ul>
  </section>
  <div id="swagger-ui"></div>
</main>
<script src="{swagger}/swagger-ui-bundle.js"></script>
<script>
window.ui = SwaggerUIBundle({{
  url: "{openapi_url}",
  dom_id: "#swagger-ui",
  layout: "BaseLayout",
  deepLinking: true,
  showExtensions: true,
  showCommonExtensions: true,
  filter: true,
  displayRequestDuration: true,
  defaultModelsExpandDepth: 0,
  syntaxHighlight: {{ theme: "obsidian" }},
  oauth2RedirectUrl: window.location.origin + "/docs/oauth2-redirect",
  presets: [SwaggerUIBundle.presets.apis, SwaggerUIBundle.SwaggerUIStandalonePreset],
}});
</script>
</body>
</html>
"""


def docs_page(app: FastAPI) -> str:
    """The page, with the app's name and version and links back to the web app."""
    e = html.escape
    return _PAGE.format(
        title=e(app.title),
        version=e(app.version),
        openapi=e(app.openapi_version),
        openapi_url=e(app.openapi_url or "/openapi.json"),
        web=e(settings.web_url.rstrip("/")),
        static=STATIC_PATH,
        swagger=SWAGGER,
    )


def install(app: FastAPI) -> None:
    """Serve the branded page at /docs, its files under /docs/static, and Swagger's OAuth hop."""

    @app.get("/docs", response_class=HTMLResponse, include_in_schema=False)
    def docs() -> HTMLResponse:
        return HTMLResponse(docs_page(app))

    @app.get("/docs/oauth2-redirect", response_class=HTMLResponse, include_in_schema=False)
    def oauth2_redirect() -> HTMLResponse:
        return get_swagger_ui_oauth2_redirect_html()

    app.mount(STATIC_PATH, StaticFiles(directory=STATIC_DIR), name="docs-static")
