"""X15: Slack or Teams webhook alert for critical incidents. Off unless ALERT_WEBHOOK_URL is set.

The message carries the decision, the categories and the pseudonym, never the prompt. Sending is
best effort and runs after the answer, so a dead webhook never slows or breaks a user's request.
"""

import logging

import httpx

from brain.config import settings

log = logging.getLogger(__name__)
CRITICAL_CATEGORIES = {"honeytoken", "secret"}


def is_critical(decision: str, categories: list[str]) -> bool:
    return decision == "block" or bool(CRITICAL_CATEGORIES & set(categories))


def message(decision: str, categories: list[str], user: str, team: str) -> dict[str, str]:
    what = ", ".join(c.replace("_", " ") for c in sorted(set(categories))) or "policy"
    # "text" works for Slack incoming webhooks and for Teams workflow webhooks.
    return {"text": f"Hive alert: {decision} for {user} ({team}). Detected: {what}."}


def notify(
    decision: str,
    categories: list[str],
    user: str,
    team: str,
    url: str | None = None,
    client: httpx.Client | None = None,
) -> bool:
    target = settings.alert_webhook_url if url is None else url
    if not target or not is_critical(decision, categories):
        return False
    own = client is None
    http = client or httpx.Client(timeout=5.0)
    try:
        http.post(target, json=message(decision, categories, user, team)).raise_for_status()
        return True
    except httpx.HTTPError:
        log.warning("The alert webhook could not be reached")
        return False
    finally:
        if own:
            http.close()
