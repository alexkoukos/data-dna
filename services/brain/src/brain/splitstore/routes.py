"""HTTP access to the split store: POST /v1/vault/store, /reveal, /aggregate.

There is no user login in this app yet, so these routes are for a trusted backend only: every call
needs `Authorization: Bearer $VAULT_API_TOKEN`, and without a token configured they answer 503.
The caller names the actor and role; the store still enforces the role list and writes the audit
log. Values are never logged.
"""

import hmac
from typing import Annotated, Any

import psycopg
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field, StrictInt, StrictStr

from brain.config import settings
from brain.splitstore.integrity import IntegrityError
from brain.splitstore.store import AccessDenied, Actor, KeyMismatchError, get_store

router = APIRouter(prefix="/v1/vault", tags=["split storage"])


def require_token(authorization: Annotated[str, Header()] = "") -> None:
    token = settings.vault_api_token
    if not token:
        raise HTTPException(503, "split storage API is off: set VAULT_API_TOKEN")
    if not hmac.compare_digest(authorization.encode(), f"Bearer {token}".encode()):
        raise HTTPException(401, "missing or wrong bearer token")


class StoreIn(BaseModel):
    record_id: str = Field(min_length=1)
    field: str = Field(min_length=1)
    value: StrictInt | StrictStr  # money as integer cents


class RevealIn(BaseModel):
    record_id: str = Field(min_length=1)
    field: str = Field(min_length=1)
    actor: str = Field(min_length=1)
    role: str


class AggregateIn(BaseModel):
    field: str = Field(min_length=1)
    record_ids: list[str] | None = None
    verify_tags: bool = True


def _call(fn: Any, *args: Any, **kw: Any) -> Any:
    try:
        return fn(*args, **kw)
    except AccessDenied as e:
        raise HTTPException(403, str(e)) from None
    except IntegrityError as e:
        raise HTTPException(409, f"integrity check failed: {e}") from None
    except KeyError as e:
        raise HTTPException(404, str(e.args[0]) if e.args else "not found") from None
    except ValueError as e:
        raise HTTPException(422, str(e)) from None
    except (KeyMismatchError, RuntimeError, psycopg.OperationalError) as e:
        raise HTTPException(503, f"split storage unavailable: {type(e).__name__}") from None


@router.post("/store", status_code=204, dependencies=[Depends(require_token)])
def store_value(body: StoreIn) -> None:
    _call(lambda: get_store().store(body.record_id, body.field, body.value))


@router.post("/reveal", dependencies=[Depends(require_token)])
def reveal_value(body: RevealIn) -> dict[str, Any]:
    value = _call(
        lambda: get_store().reveal(body.record_id, body.field, Actor(body.actor, body.role))
    )
    return {"record_id": body.record_id, "field": body.field, "value": value}


@router.post("/aggregate", dependencies=[Depends(require_token)])
def aggregate(body: AggregateIn) -> dict[str, Any]:
    total = _call(
        lambda: get_store().aggregate_sum(body.field, body.record_ids, verify_tags=body.verify_tags)
    )
    return {"field": body.field, "sum": total}
