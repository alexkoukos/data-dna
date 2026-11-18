"""LiteLLM custom guardrail: every request goes through brain /v1/inspect first."""

import os
from typing import Any
from urllib.parse import quote

import httpx
from fastapi import HTTPException
from litellm.integrations.custom_guardrail import CustomGuardrail

from collections.abc import AsyncGenerator

from dna_inspect import (
    GatewayError,
    acceptance_scope,
    apply_decision,
    finalize_answer,
    rewrite_output,
    rewrite_stream,
)

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
                accept_scope=acceptance_scope(
                    getattr(user_api_key_dict, "user_id", None),
                    getattr(user_api_key_dict, "api_key", None),
                    getattr(user_api_key_dict, "user_role", None),
                ),
            )
        except GatewayError as err:
            raise HTTPException(status_code=err.status_code, detail=err.body) from err

    async def async_post_call_success_hook(
        self, data: dict, user_api_key_dict: Any, response: Any
    ) -> Any:
        if isinstance(response, dict) and isinstance(response.get("content"), list):
            return await self._clean_blocks(data, user_api_key_dict, response)
        choices = getattr(response, "choices", None)
        output = (
            response.get("output")
            if isinstance(response, dict)
            else getattr(response, "output", None)
        )
        if not choices and not isinstance(output, list):
            return response
        meta = data.get("metadata") or {}
        # Tell the client what was decided, so the app can show Allowed / Masked / Answered locally.
        hidden = getattr(response, "_hidden_params", None)
        if isinstance(hidden, dict):
            extra = hidden.setdefault("additional_headers", {})
            extra["x-dna-decision"] = str(meta.get("dna_decision", "allow"))
            extra["x-dna-reasons"] = quote("; ".join(meta.get("dna_reasons") or []))
        try:
            if isinstance(output, list):
                # Responses API answers keep their text in output[].content[].text.
                await rewrite_output(
                    output, lambda text: self._finalize(text, user_api_key_dict, meta)
                )
            for choice in choices or []:
                message = getattr(choice, "message", None)
                if message is not None and isinstance(message.content, str):
                    message.content = await self._finalize(message.content, user_api_key_dict, meta)
                if message is not None:
                    await self._clean_message_extras(message, user_api_key_dict, meta)
                # Text completions answer in `choices[].text`, not in a message.
                if isinstance(getattr(choice, "text", None), str):
                    choice.text = await self._finalize(choice.text, user_api_key_dict, meta)
        except GatewayError as err:
            raise HTTPException(status_code=err.status_code, detail=err.body) from err
        return response

    async def _clean_message_extras(self, message: Any, user_api_key_dict: Any, meta: dict) -> None:
        """Refusal, reasoning and tool-call arguments are answer text too."""
        for name in ("refusal", "reasoning_content"):
            value = getattr(message, name, None)
            if isinstance(value, str) and value:
                setattr(message, name, await self._finalize(value, user_api_key_dict, meta))
        for block in getattr(message, "thinking_blocks", None) or []:
            text = block.get("thinking") if isinstance(block, dict) else getattr(block, "thinking", None)
            if isinstance(text, str) and text:
                cleaned = await self._finalize(
                    text, user_api_key_dict, {**meta, "dna_session_id": None}
                )
                if isinstance(block, dict):
                    block["thinking"] = cleaned
                else:
                    block.thinking = cleaned
        calls = list(getattr(message, "tool_calls", None) or [])
        legacy = getattr(message, "function_call", None)
        if legacy is not None:
            calls.append(type("Legacy", (), {"function": legacy})())
        for call in calls:
            fn = getattr(call, "function", None)
            args = getattr(fn, "arguments", None)
            if isinstance(args, str) and args:
                fn.arguments = await self._finalize(args, user_api_key_dict, meta)

    async def _finalize(self, text: str, user_api_key_dict: Any, meta: dict) -> str:
        return await finalize_answer(
            text,
            user_id=getattr(user_api_key_dict, "user_id", None) or "anonymous",
            team=getattr(user_api_key_dict, "team_id", None) or "unknown",
            session_id=meta.get("dna_session_id"),
            brain_url=BRAIN_URL,
            client=self._client,
        )

    async def _clean_blocks(self, data: dict, user_api_key_dict: Any, response: dict) -> dict:
        """Answers in the Anthropic messages shape: text, tool input and thinking blocks."""
        meta = data.get("metadata") or {}
        hidden = response.setdefault("_hidden_params", {})
        if isinstance(hidden, dict):
            extra = hidden.setdefault("additional_headers", {})
            extra["x-dna-decision"] = str(meta.get("dna_decision", "allow"))
            extra["x-dna-reasons"] = quote("; ".join(meta.get("dna_reasons") or []))
        try:
            for block in response["content"]:
                if not isinstance(block, dict):
                    continue
                kind = block.get("type")
                if kind == "text":
                    block["text"] = await self._finalize(
                        str(block.get("text", "")), user_api_key_dict, meta
                    )
                elif kind == "tool_use":
                    block["input"] = await self._walk(block.get("input"), user_api_key_dict, meta)
                elif kind == "thinking" and isinstance(block.get("thinking"), str):
                    block["thinking"] = await self._finalize(
                        block["thinking"], user_api_key_dict, {**meta, "dna_session_id": None}
                    )
        except GatewayError as err:
            raise HTTPException(status_code=err.status_code, detail=err.body) from err
        return response

    async def _walk(self, node: Any, user_api_key_dict: Any, meta: dict) -> Any:
        if isinstance(node, str):
            return await self._finalize(node, user_api_key_dict, meta) if node else node
        if isinstance(node, dict):
            return {
                (await self._walk(k, user_api_key_dict, meta)): await self._walk(
                    v, user_api_key_dict, meta
                )
                for k, v in node.items()
            }
        if isinstance(node, list):
            return [await self._walk(v, user_api_key_dict, meta) for v in node]
        return node

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

        async def filter_only(text: str) -> str:
            return await finalize_answer(
                text,
                user_id=getattr(user_api_key_dict, "user_id", None) or "anonymous",
                team=getattr(user_api_key_dict, "team_id", None) or "unknown",
                session_id=None,
                brain_url=BRAIN_URL,
                client=self._client,
            )

        try:
            async for item in rewrite_stream(response, clean, filter_only):
                yield item
        except GatewayError as err:
            raise HTTPException(status_code=err.status_code, detail=err.body) from err
