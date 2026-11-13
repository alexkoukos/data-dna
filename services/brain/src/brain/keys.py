"""Create a personal gateway key for a user (PRD section 8, step 1)."""

import httpx

from brain.config import settings

MODELS = ["gpt-4o-mini", "demo-mock", "demo-echo", "demo-leaky"]


class KeyError_(RuntimeError):
    """The gateway refused or could not be reached. The message is safe to show."""


def default_model() -> str:
    return "gpt-4o-mini" if settings.openai_api_key else "demo-mock"


def create_key(user_id: str, team: str, client: httpx.Client | None = None) -> str:
    admin = {"Authorization": f"Bearer {settings.litellm_master_key}"}
    own = client is None
    http = client or httpx.Client(base_url=settings.gateway_url, timeout=10.0)
    try:
        # The team must exist first. An existing team answers with an error we can ignore.
        http.post("/team/new", headers=admin, json={"team_id": team, "team_alias": team})
        resp = http.post(
            "/key/generate",
            headers=admin,
            json={"user_id": user_id, "team_id": team, "models": MODELS},
        )
        resp.raise_for_status()
        return str(resp.json()["key"])
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        raise KeyError_("The gateway could not create a key. Try again in a minute.") from exc
    finally:
        if own:
            http.close()
