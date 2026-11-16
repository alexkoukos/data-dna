"""LiteLLM custom guardrail: every request goes through brain /v1/inspect first."""

import os
from typing import Any
from urllib.parse import quote

import httpx
from fastapi import HTTPException
from litellm.integrations.custom_guardrail import CustomGuardrail

from collections.abc import AsyncGenerator

from dna_inspect import GatewayError, apply_decision, finalize_answer, rewrite_stream

BRAIN_URL = os.environ.get("BRAIN_URL", "http://brain:8001")


class DnaGuardrail(CustomGuardrail):
    def __init__(self, **kwargs: Any) -> None:
        self._client = httpx.AsyncClient()
        super().__init__(**kwargs)

    async def async_pre_call_hook(
        self, user_api_key_dict: Any, cache: Any, data: dict, call_type: str
    ) -> dict:
        headers = (data.get("proxy_server_request") or {}).get("headers") or {}
        try:
            return await apply_decision(
                data,
                user_id=getattr(user_api_key_dict, "user_id", None) or "anonymous",
                team=getattr(user_api_key_dict, "team_id", None) or "unknown",
                headers=headers,
                brain_url=BRAIN_URL,
                client=self._client,
                call_type=call_type,
            )
        except GatewayError as err:
            raise HTTPException(status_code=err.status_code, detail=err.body) from err

    async def async_post_call_success_hook(
        self, data: dict, user_api_key_dict: Any, response: Any
    ) -> Any:
        if isinstance(response, dict) and isinstance(response.get("content"), list):
            return await self._clean_blocks(data, user_api_key_dict, response)
        choices = getattr(response, "choices", None)
        if not choices:
            return response
        meta = data.get("metadata") or {}
        # Tell the client what was decided, so the app can show Allowed / Masked / Answered locally.
        hidden = getattr(response, "_hidden_params", None)
        if isinstance(hidden, dict):
            extra = hidden.setdefault("additional_headers", {})
            extra["x-dna-decision"] = str(meta.get("dna_decision", "allow"))
            extra["x-dna-reasons"] = quote("; ".join(meta.get("dna_reasons") or []))
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

    async def _clean_blocks(self, data: dict, user_api_key_dict: Any, response: dict) -> dict:
        """Answers in the Anthropic messages shape: filter each text block."""
        meta = data.get("metadata") or {}
        try:
            for block in response["content"]:
                if isinstance(block, dict) and block.get("type") == "text":
                    block["text"] = await finalize_answer(
                        str(block.get("text", "")),
                        user_id=getattr(user_api_key_dict, "user_id", None) or "anonymous",
                        team=getattr(user_api_key_dict, "team_id", None) or "unknown",
                        session_id=meta.get("dna_session_id"),
                        brain_url=BRAIN_URL,
                        client=self._client,
                    )
        except GatewayError as err:
            raise HTTPException(status_code=err.status_code, detail=err.body) from err
        return response

    async def async_post_call_streaming_iterator_hook(
        self, user_api_key_dict: Any, response: Any, request_data: dict
    ) -> AsyncGenerator[Any, None]:
        meta = request_data.get("metadata") or {}

        async def clean(text: str) -> str:
            return await finalize_answer(
                text,
                user_id=getattr(user_api_key_dict, "user_id", None) or "anonymous",
                team=getattr(user_api_key_dict, "team_id", None) or "unknown",
                session_id=meta.get("dna_session_id"),
                brain_url=BRAIN_URL,
                client=self._client,
            )

        try:
            async for item in rewrite_stream(response, clean):
                yield item
        except GatewayError as err:
            raise HTTPException(status_code=err.status_code, detail=err.body) from err
