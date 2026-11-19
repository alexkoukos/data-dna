"""Create a personal gateway key for a user."""

import httpx

from brain.config import settings

MODELS = ["gpt-4o-mini", "demo-mock", "demo-echo", "demo-leaky", "local-standin"]


class KeyError_(RuntimeError):
    """The gateway refused or could not be reached. The message is safe to show."""


# Only the routes the gate inspects. Assistants, files, batches and the like are not reachable.
ALLOWED_ROUTES = [
    "/chat/completions",
    "/v1/chat/completions",
    "/completions",
    "/v1/completions",
    "/v1/messages",
    "/responses",
    "/v1/responses",
    "/embeddings",
    "/v1/embeddings",
    "/models",
    "/v1/models",
]


def default_model() -> str:
    return "gpt-4o-mini" if settings.openai_api_key else "demo-mock"


def key_request(user_id: str, team: str) -> dict[str, object]:
    """X14: rate and spend limits per key. 0 means no limit, which is the default."""
    body: dict[str, object] = {
        "user_id": user_id,
        "team_id": team,
        "models": MODELS,
        "allowed_routes": ALLOWED_ROUTES,
    }
    if settings.key_rpm_limit > 0:
        body["rpm_limit"] = settings.key_rpm_limit
    if settings.key_max_budget > 0:
        body["max_budget"] = settings.key_max_budget
        body["budget_duration"] = "30d"
    return body


def create_key(user_id: str, team: str, client: httpx.Client | None = None) -> str:
    admin = {"Authorization": f"Bearer {settings.litellm_master_key}"}
    own = client is None
    http = client or httpx.Client(base_url=settings.gateway_url, timeout=10.0)
    try:
        # The team must exist first. An existing team answers with an error we can ignore.
        http.post("/team/new", headers=admin, json={"team_id": team, "team_alias": team})
        resp = http.post("/key/generate", headers=admin, json=key_request(user_id, team))
        resp.raise_for_status()
        return str(resp.json()["key"])
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        raise KeyError_("The gateway could not create a key. Try again in a minute.") from exc
    finally:
        if own:
            http.close()
