"""LiteLLM custom guardrail: every request goes through brain /v1/inspect first."""

import os
from typing import Any

import httpx
from fastapi import HTTPException
from litellm.integrations.custom_guardrail import CustomGuardrail

from dna_inspect import GatewayError, apply_decision, finalize_answer

BRAIN_URL = os.environ.get("BRAIN_URL", "http://brain:8001")


class DnaGuardrail(CustomGuardrail):
    def __init__(self, **kwargs: Any) -> None:
        self._client = httpx.AsyncClient()
        super().__init__(**kwargs)

    async def async_pre_call_hook(
        self, user_api_key_dict: Any, cache: Any, data: dict, call_type: str
    ) -> dict:
        if call_type not in ("completion", "acompletion", "text_completion"):
            return data
        headers = (data.get("proxy_server_request") or {}).get("headers") or {}
        try:
            return await apply_decision(
                data,
                user_id=getattr(user_api_key_dict, "user_id", None) or "anonymous",
                team=getattr(user_api_key_dict, "team_id", None) or "unknown",
                headers=headers,
                brain_url=BRAIN_URL,
                client=self._client,
            )
        except GatewayError as err:
            raise HTTPException(status_code=err.status_code, detail=err.body) from err

    async def async_post_call_success_hook(
        self, data: dict, user_api_key_dict: Any, response: Any
    ) -> Any:
        choices = getattr(response, "choices", None)
        if not choices:
            return response
        meta = data.get("metadata") or {}
        try:
            for choice in choices:
                message = getattr(choice, "message", None)
                if message is not None and isinstance(message.content, str):
                    message.content = await finalize_answer(
                        message.content,
                        user_id=getattr(user_api_key_dict, "user_id", None) or "anonymous",
                        team=getattr(user_api_key_dict, "team_id", None) or "unknown",
                        session_id=meta.get("dna_session_id"),
                        brain_url=BRAIN_URL,
                        client=self._client,
                    )
        except GatewayError as err:
            raise HTTPException(status_code=err.status_code, detail=err.body) from err
        return response
