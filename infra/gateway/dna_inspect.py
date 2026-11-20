"""Gateway-side glue between LiteLLM and the brain.

Pure logic, no LiteLLM imports, so it can be unit tested without the gateway image.
`dna_guardrail.py` is the thin LiteLLM wrapper around it.
"""

from __future__ import annotations

import base64
import copy
import hashlib
import json
import re
import threading
import time
from collections import OrderedDict
from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import unquote_to_bytes

import httpx

ACK_HEADER = "x-dna-ack"
REROUTE_HEADER = "x-dna-reroute"  # X31: "send it to Company AI instead"
LOCAL_MODEL = "local"


@dataclass
class GatewayError(Exception):
    """An answer the gateway returns instead of forwarding the request."""

    status_code: int
    body: dict[str, Any] = field(default_factory=dict)


# Every way into the gateway that carries text we understand. Anything else (images, audio,
# pass-through routes) is refused: an unchecked door would let people around the safety check.
CHAT_CALLS = {"completion", "acompletion"}
TEXT_CALLS = {"text_completion", "atext_completion"}
ANTHROPIC_CALLS = {"anthropic_messages", "aanthropic_messages"}
RESPONSES_CALLS = {"responses", "aresponses"}
EMBEDDING_CALLS = {"embeddings", "aembedding"}
SUPPORTED_CALLS = CHAT_CALLS | TEXT_CALLS | ANTHROPIC_CALLS | RESPONSES_CALLS | EMBEDDING_CALLS

_TEXT_PARTS = {"text", "input_text", "output_text", "summary_text"}
DEFINITION = "definition"  # request text that is not a message and not a tool description
TOOL_DEFINITION = "tool_definition"  # tool and function descriptions: injection wording warns


@dataclass
class Slot:
    """One piece of text the brain checks, and how to put a masked version back.

    `write` is None when the text cannot be rewritten (a signed thinking block). `risky` means
    the same message also carries an image, file or audio part: rewriting its text is refused
    because the brain never saw the other part.
    """

    role: str
    text: str
    write: Callable[[str], None] | None
    risky: bool = False
    where: tuple[int, Any] | None = None
    path: str = ""


class _Writer:
    """Puts a new string back where the old one was, and remembers where that is."""

    def __init__(self, container: Any, key: Any) -> None:
        self.container = container
        self.key = key

    def __call__(self, value: str) -> None:
        self.container[self.key] = value


def _setter(container: Any, key: Any) -> Callable[[str], None]:
    return _Writer(container, key)


def _no_token_ids() -> GatewayError:
    return GatewayError(
        403,
        {
            "type": "block",
            "message": "Send text, not token ids, through the company gateway.",
            "reasons": ["The request carries token ids, which cannot be checked"],
            "approved_alternative": "Send the text itself.",
        },
    )


def _unreadable_document() -> GatewayError:
    return GatewayError(
        403,
        {
            "type": "block",
            "message": "A text document in this request is not valid base64, so it cannot be "
            "checked.",
            "reasons": ["A text document could not be decoded exactly"],
            "approved_alternative": "Send the document as plain text, or re-encode it as "
            "standard base64.",
        },
    )


def _too_large_document() -> GatewayError:
    return GatewayError(
        403,
        {
            "type": "block",
            "message": "A text file in this request is too large for the company gateway to "
            "check in full.",
            "reasons": ["A text file over about 150 KB cannot be checked"],
            "approved_alternative": "Shorten the file or split it into smaller parts.",
        },
    )


_CLIENT_ROLES = {"system", "developer", "user", "assistant", "tool"}


def _client_role(raw: Any) -> str:
    """The role a client claimed, if the brain knows it. Anything else (including the gateway's
    own "definition" and "tool_definition" roles) is checked as the person's own text."""
    role = str(raw if raw is not None else "user").strip().lower()
    return role if role in _CLIENT_ROLES else "user"


def _describe(node: Any, out: list[Slot]) -> None:
    """Every description and title string in a tool definition or its JSON schema."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key in ("description", "title") and isinstance(value, str):
                if value:
                    out.append(Slot(TOOL_DEFINITION, value, _setter(node, key)))
            else:
                _describe(value, out)
    elif isinstance(node, list):
        for item in node:
            _describe(item, out)


def _tool_definitions(data: dict[str, Any]) -> list[Slot]:
    out: list[Slot] = []
    for key in ("tools", "functions"):
        for tool in data.get(key) or []:
            if isinstance(tool, dict):
                _describe(tool, out)
    return out


def _message_slots(role: str, content: Any, out: list[Slot]) -> bool:
    """Slots for a message body that is a string or a list of parts. True if it has parts that
    are not text (images, files, audio)."""
    if isinstance(content, str):
        return False
    other = False
    for part in content if isinstance(content, list) else []:
        if not isinstance(part, dict):
            other = True
        elif part.get("type") in _TEXT_PARTS and isinstance(part.get("text"), str):
            out.append(Slot(role, part["text"], _setter(part, "text")))
        elif part.get("type") == "refusal" and isinstance(part.get("refusal"), str):
            out.append(Slot(role, part["refusal"], _setter(part, "refusal")))
        else:
            other = True
    return other


def _chat_slots(data: dict[str, Any]) -> list[Slot]:
    out = _tool_definitions(data)
    for m in data.get("messages") or []:
        if not isinstance(m, dict):
            continue
        role = _client_role(m.get("role"))
        mine: list[Slot] = []
        content = m.get("content")
        if isinstance(content, str):
            mine.append(Slot(role, content, _setter(m, "content")))
        other = _message_slots(role, content, mine)
        for key in ("refusal", "reasoning_content"):
            if isinstance(m.get(key), str):
                mine.append(Slot(role, m[key], _setter(m, key)))
        legacy = m.get("function_call")
        if isinstance(legacy, dict) and isinstance(legacy.get("arguments"), str):
            mine.append(Slot("assistant", legacy["arguments"], _setter(legacy, "arguments")))
        for call in m.get("tool_calls") or []:
            fn = call.get("function") if isinstance(call, dict) else None
            if isinstance(fn, dict) and isinstance(fn.get("arguments"), str):
                mine.append(Slot("assistant", fn["arguments"], _setter(fn, "arguments")))
        for slot in mine:
            slot.risky = other
        out.extend(mine)
    return out


def _text_slots(data: dict[str, Any]) -> list[Slot]:
    out: list[Slot] = []
    prompt = data.get("prompt")
    if isinstance(prompt, str):
        out.append(Slot("user", prompt, _setter(data, "prompt")))
    elif isinstance(prompt, list):
        for i, item in enumerate(prompt):
            if not isinstance(item, str):
                raise _no_token_ids()
            out.append(Slot("user", item, _setter(prompt, i)))
    elif prompt is not None:
        raise _no_token_ids()
    if isinstance(data.get("suffix"), str):
        out.append(Slot("user", data["suffix"], _setter(data, "suffix")))
    return out


def _anthropic_slots(data: dict[str, Any]) -> list[Slot]:
    out: list[Slot] = []
    system = data.get("system")
    if isinstance(system, str):
        out.append(Slot("system", system, _setter(data, "system")))
    elif isinstance(system, list):
        for block in system:
            if isinstance(block, dict) and isinstance(block.get("text"), str):
                out.append(Slot("system", block["text"], _setter(block, "text")))
    out.extend(_tool_definitions(data))
    for index, m in enumerate(data.get("messages") or []):
        if not isinstance(m, dict):
            continue
        role = _client_role(m.get("role"))
        content = m.get("content")
        mine: list[Slot] = []
        other = False
        if isinstance(content, str):
            mine.append(Slot(role, content, _setter(m, "content")))
        for n, block in enumerate(content if isinstance(content, list) else []):
            if not isinstance(block, dict):
                other = True
                continue
            kind = block.get("type")
            if kind == "text" and isinstance(block.get("text"), str):
                mine.append(Slot(role, block["text"], _setter(block, "text")))
            elif kind == "tool_result":
                inner = block.get("content")
                if isinstance(inner, str):
                    mine.append(Slot("tool", inner, _setter(block, "content")))
                else:
                    other = _message_slots("tool", inner, mine) or other
            elif kind == "thinking" and isinstance(block.get("thinking"), str):
                mine.append(Slot(role, block["thinking"], None, where=(id(block), "thinking")))
            elif kind == "document":
                source = block.get("source")
                if isinstance(source, dict) and source.get("type") == "text":
                    if isinstance(source.get("data"), str):
                        mine.append(Slot(role, source["data"], _setter(source, "data")))
                elif isinstance(source, dict) and source.get("type") == "content":
                    inner = source.get("content")
                    if isinstance(inner, str):
                        mine.append(Slot(role, inner, _setter(source, "content")))
                    else:
                        other = _message_slots(role, inner, mine) or other
                elif isinstance(source, dict) and source.get("type") == "base64":
                    decoded = _base64_document_text(source)
                    if decoded is None:
                        other = True
                    else:
                        field_path = f"messages[{index}].content[{n}].source.data"
                        mine.append(
                            Slot(role, decoded, None, where=(id(source), "data"), path=field_path)
                        )
                else:
                    other = True
            elif kind == "search_result":
                other = _message_slots(role, block.get("content"), mine) or other
            elif kind in ("tool_use", "redacted_thinking"):
                continue
            else:
                other = True
        for slot in mine:
            slot.risky = other
        out.extend(mine)
    return out


def _responses_slots(data: dict[str, Any]) -> list[Slot]:
    out: list[Slot] = []
    if isinstance(data.get("instructions"), str):
        out.append(Slot("system", data["instructions"], _setter(data, "instructions")))
    out.extend(_tool_definitions(data))
    raw = data.get("input")
    if isinstance(raw, str):
        out.append(Slot("user", raw, _setter(data, "input")))
        return out
    for item in raw if isinstance(raw, list) else []:
        if not isinstance(item, dict):
            continue
        kind = item.get("type")
        if kind in ("function_call_output", "custom_tool_call_output"):
            if isinstance(item.get("output"), str):
                out.append(Slot("tool", item["output"], _setter(item, "output")))
            else:
                mine_out: list[Slot] = []
                other_out = _message_slots("tool", item.get("output"), mine_out)
                for slot in mine_out:
                    slot.risky = other_out
                out.extend(mine_out)
            continue
        if kind in ("function_call", "custom_tool_call"):
            key = "arguments" if kind == "function_call" else "input"
            if isinstance(item.get(key), str):
                out.append(Slot("assistant", item[key], _setter(item, key)))
            continue
        role = _client_role(item.get("role"))
        content = item.get("content")
        mine: list[Slot] = []
        if isinstance(content, str):
            mine.append(Slot(role, content, _setter(item, "content")))
        other = _message_slots(role, content, mine)
        for slot in mine:
            slot.risky = other
        out.extend(mine)
    return out


def _embedding_slots(data: dict[str, Any]) -> list[Slot]:
    raw = data.get("input")
    if isinstance(raw, str):
        return [Slot("user", raw, _setter(data, "input"))]
    out: list[Slot] = []
    for i, item in enumerate(raw if isinstance(raw, list) else []):
        if not isinstance(item, str):
            raise _no_token_ids()
        out.append(Slot("user", item, _setter(raw, i)))
    return out


# Top-level fields the gateway adds itself. They are not what the person sent and are not read.
_OWN_KEYS = {
    "model",
    "metadata",
    "litellm_metadata",
    "proxy_server_request",
    "secret_fields",
    "provider_specific_header",
}
_OWN_LITELLM_KEYS = {
    "litellm_call_id",
    "litellm_logging_obj",
    "litellm_metadata",
    "litellm_trace_id",
    "litellm_session_id",
}
# Settings a client could send to change where or how the gateway calls the model. LiteLLM
# keeps them in the request it forwards, so they are refused instead of read.
_CONNECTION_KEYS = (
    "headers",
    "extra_headers",
    "api_key",
    "api_base",
    "base_url",
    "api_version",
    "cache",
)
# Per-request router settings. A client that sets fallbacks or a router override could steer the
# call to another model after the gate chose "local", so these are refused when merely present.
# disable_fallbacks and client_side_timeout are LiteLLM's own key settings and are not listed.
_ROUTER_KEYS = (
    "fallbacks",
    "context_window_fallbacks",
    "content_policy_fallbacks",
    "router_settings_override",
    "model_group_retry_policy",
    "routing_strategy",
    "routing_strategy_args",
    "num_retries",
    "timeout",
    "request_timeout",
    "stream_timeout",
    "model_list",
    "specific_deployment",
    "allowed_model_region",
    "fallback_depth",
    "attempted_targets",
    "include_fallback_errors",
    "passthrough_on_no_deployment",
    "silent_model",
    "_target_order",
    "_retry_skipped_deployment_ids",
    "max_retries",
    "mock_testing_fallbacks",
    "model_group_alias",
)
_DECISIONS = {"allow", "mask", "warn", "local", "block"}
# Fields LiteLLM adds to `metadata` next to what the person sent.
_LITELLM_METADATA = {"headers", "used_client_oauth_token"}
_SPOOFED_METADATA_PREFIXES = ("user_api_key", "dna_", "litellm_")
_SHORT_LABELS = {"type", "role", "detail", "media_type", "mime_type"}
_LABEL_VALUE = re.compile(r"[A-Za-z0-9_./+\-]+")
_BASE64 = re.compile(r"[A-Za-z0-9+/]+={0,2}|[A-Za-z0-9_\-]+={0,2}")
_DATA_URL = re.compile(r"data:([^,;]*)((?:;[^,;]*)*),(.*)", re.DOTALL | re.IGNORECASE)
_MIN_BINARY_CHARS = 256  # shorter strings are checked: API keys and phrases look like base64
_MAX_DATA_URL_CHARS = 200_000
_MAX_DEPTH = 24


def _connection_error(key: str) -> GatewayError:
    return GatewayError(
        403,
        {
            "type": "block",
            "message": "This request sets connection settings the company gateway does not "
            f"allow. Remove {key} and try again.",
            "reasons": [f"The request sets {key}"],
            "approved_alternative": "Send only the model, the messages and the usual options.",
        },
    )


def _several_answers(n: Any) -> bool:
    try:
        return int(n or 1) > 1
    except (TypeError, ValueError):
        return True


def refuse_connection_settings(data: dict[str, Any], call_type: str) -> None:
    """Refuse a request that sets connection settings or forges the gateway's own fields.

    LiteLLM overwrites some of these itself, but not all, and a client must never decide how the
    gateway talks to the model or which session an answer is unmasked with.
    """
    for key in _CONNECTION_KEYS:
        if data.get(key):
            raise _connection_error(key)
    if data.get("provider_specific_header") and call_type not in ANTHROPIC_CALLS:
        raise _connection_error("provider_specific_header")
    extra_body = data.get("extra_body")
    for key in _ROUTER_KEYS:
        if key in data or (isinstance(extra_body, dict) and key in extra_body):
            raise _connection_error(key)
    for key in data:
        if isinstance(key, str) and (
            key.startswith("user_api_key")
            or (key.startswith("litellm_") and key not in _OWN_LITELLM_KEYS)
        ):
            raise _connection_error(key)
    for name in ("metadata", "litellm_metadata"):
        meta = data.get(name)
        if not isinstance(meta, dict):
            continue
        snapshot = meta.get("requester_metadata")
        if name == "litellm_metadata" and snapshot is not None and "metadata" not in data:
            raise _connection_error("metadata.requester_metadata")
        # `headers` and `used_client_oauth_token` are written by LiteLLM over anything the client
        # sent, so they cannot be told apart from its own and are not refused.
        # On some routes `metadata` is LiteLLM's own dict, full of its user_api_key_* fields, so
        # only our own dna_* keys are refused there; the snapshot of what the client sent is
        # held to the full list.
        mine = snapshot if isinstance(snapshot, dict) else meta
        banned = _SPOOFED_METADATA_PREFIXES if isinstance(snapshot, dict) else ("dna_",)
        for key in mine:
            if (isinstance(snapshot, dict) and key == "requester_metadata") or str(key).startswith(
                banned
            ):
                raise _connection_error(f"metadata.{key}")


def _is_binary(text: str) -> bool:
    """A long base64 blob that is not text (a signature, a file). Anything else is checked,
    including a string that only looks like base64 but does not decode."""
    if len(text) < _MIN_BINARY_CHARS or _BASE64.fullmatch(text) is None:
        return False
    try:
        raw = base64.b64decode(
            text.replace("-", "+").replace("_", "/") + "=" * (-len(text) % 4), validate=True
        )
        decoded = raw.decode("utf-8")
    except UnicodeDecodeError:
        return True
    except ValueError:
        return False
    return sum(c.isprintable() or c in "\n\r\t" for c in decoded) / max(len(decoded), 1) < 0.85


_PART = re.compile(r"(?:messages|input)\[\d+\]\.content\[\d+\](?:\.content\[\d+\])?")
# Where each kind of content part keeps its media, as providers read it.
_MEDIA_FIELDS = {
    "image_url": ("image_url", "image_url.url"),
    "input_audio": ("input_audio.data",),
    "file": ("file.file_data",),
    "input_image": ("image_url",),
    "input_file": ("file_data",),
    "image": ("source.data",),
    "document": ("source.data",),
}


def _in_media_position(part_type: Any, path: str) -> bool:
    """True only at the exact place a provider reads an image, file or audio from: the part's own
    type decides, so the same field name anywhere else is ordinary text."""
    if not isinstance(part_type, str):
        return False
    m = _PART.match(path)
    if m is None or path[m.end() : m.end() + 1] != ".":
        return False
    return path[m.end() + 1 :] in _MEDIA_FIELDS.get(part_type, ())


def _textual_media(media: str) -> bool:
    media = media.split(";", 1)[0].strip().lower()
    return (
        media.startswith("text/")
        or media in ("application/json", "application/xml")
        or media.endswith(("+json", "+xml"))
    )


def _strict_b64decode(data: str) -> bytes | None:
    """Decode standard base64 exactly, or None.

    Only whitespace is ignored. Characters outside the alphabet or data after padding make it
    fail, so the gateway never checks a different text from the one a stricter or looser
    decoder at the provider would read.
    """
    compact = re.sub(r"\s+", "", data)
    try:
        return base64.b64decode(compact + "=" * (-len(compact) % 4), validate=True)
    except ValueError:
        return None


def _base64_document_text(source: dict[str, Any]) -> str | None:
    """The text inside a base64 document whose media type is text, JSON or XML, else None.

    Raises a 403 when the media type is textual but the data is not exact base64.
    """
    data = source.get("data")
    media = source.get("media_type")
    if not isinstance(data, str) or not isinstance(media, str) or not _textual_media(media):
        return None
    raw = _strict_b64decode(data)
    if raw is None:
        raise _unreadable_document()
    return raw.decode("utf-8", errors="replace")


def _data_url_texts(value: str, media_position: bool) -> list[str] | None:
    """What to check in a data URL: None if the string is not one (check it as text).

    In a media position a binary type is skipped. Anywhere else the string itself is checked,
    plus its payload when that decodes to something that is not a real binary file.
    """
    if not value[:5].lower() == "data:":
        return None
    m = _DATA_URL.fullmatch(value)
    if m is None:
        return None
    media = m.group(1).strip().lower()
    textual = media == "" or _textual_media(media)
    if media_position and not textual:
        return []
    full = m.group(3)
    is_base64 = ";base64" in m.group(2).lower()
    if media_position and textual and is_base64 and len(full) > _MAX_DATA_URL_CHARS:
        # A text file the provider reads in full must not be checked only in part.
        raise _too_large_document()
    payload = full[:_MAX_DATA_URL_CHARS]
    out = [value]
    try:
        if is_base64:
            decoded_bytes = _strict_b64decode(payload)
            if decoded_bytes is None:
                if media_position and textual:
                    raise _unreadable_document()
                return out
            raw = decoded_bytes
            if len(raw) >= _MIN_BINARY_CHARS and not _mostly_text(raw):
                return out
        else:
            raw = unquote_to_bytes(payload)
    except ValueError:
        return out
    decoded = raw.decode("utf-8", errors="replace")
    if decoded and decoded != value:
        out.append(decoded)
    return out


def _mostly_text(raw: bytes) -> bool:
    try:
        decoded = raw.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return sum(c.isprintable() or c in "\n\r\t" for c in decoded) / max(len(decoded), 1) >= 0.85


def _short_label(key: Any, value: str) -> bool:
    return (
        isinstance(key, str)
        and key in _SHORT_LABELS
        and len(value) <= 40
        and _LABEL_VALUE.fullmatch(value) is not None
    )


def _sweep(
    node: Any,
    covered: set[tuple[int, Any]],
    out: list[Slot],
    depth: int = 0,
    path: str = "",
    part_type: Any = None,
) -> None:
    """Every string not already in a slot becomes a read-only slot, so no field is skipped by
    accident. Anything here can be checked but not rewritten."""
    if depth > _MAX_DEPTH:
        return
    pairs: Any = None
    if isinstance(node, dict):
        if _PART.fullmatch(path):
            part_type = node.get("type")
        pairs = node.items()
    elif isinstance(node, (list, tuple)):
        pairs = enumerate(node)
    for key, value in pairs or ():
        if depth == 0 and isinstance(key, str) and (key in _OWN_KEYS or key.startswith("litellm_")):
            continue
        here = f"{path}[{key}]" if isinstance(node, (list, tuple)) else f"{path}.{key}".lstrip(".")
        if isinstance(value, str):
            if not value or (id(node), key) in covered or _short_label(key, value):
                continue
            texts = _data_url_texts(value, _in_media_position(part_type, here))
            if texts is None:
                texts = [] if _is_binary(value) else [value]
            out.extend(Slot(DEFINITION, t, None, path=here) for t in texts)
        elif isinstance(value, (dict, list, tuple)):
            _sweep(value, covered, out, depth + 1, here, part_type)


# Inline files (PDF, Word, images, audio) the provider reads at a media position. They go to the
# brain as attachments, so their text is checked too; what the brain cannot read is refused.
MAX_ATTACHMENTS = 10  # the brain's own limit per request
MAX_ATTACHMENT_CHARS = 13_000_000  # base64 in total, under the brain's 15 MB request limit
_MEDIA_SUFFIX = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/bmp": ".bmp",
}
_SAFE_NAME = re.compile(r"[^A-Za-z0-9 ._()\-]+")


def _too_many_files() -> GatewayError:
    return GatewayError(
        403,
        {
            "type": "block",
            "message": "This request carries more files than the company gateway can check at "
            f"once (at most {MAX_ATTACHMENTS}, about 10 MB in total).",
            "reasons": ["Too many or too large files to check"],
            "approved_alternative": "Send fewer or smaller files in each request.",
        },
    )


def _attachment_name(node: dict[str, Any], media: str) -> str:
    """A display name for the file. The brain reads the content, so a wrong name hides nothing."""
    raw = node.get("filename") if isinstance(node.get("filename"), str) else ""
    name = _SAFE_NAME.sub("_", raw.replace("\\", "/").rsplit("/", 1)[-1]).strip()[:100]
    suffix = _MEDIA_SUFFIX.get(media, "")
    if not name:
        return f"attachment{suffix or '.bin'}"
    return name if "." in name[1:] or not suffix else name + suffix


def _media_blob(node: dict[str, Any], value: str) -> dict[str, str] | None:
    """The inline file at a media position as an attachment, or None when there is no inline file
    to read (a web address, or text that is already checked as text)."""
    m = _DATA_URL.fullmatch(value) if value[:5].lower() == "data:" else None
    if m is not None:
        media = m.group(1).strip().lower()
        if media == "" or _textual_media(media):
            return None  # decoded and checked as text by _data_url_texts
        if ";base64" in m.group(2).lower():
            raw = _strict_b64decode(m.group(3))
            if raw is None:
                raise _unreadable_document()
        else:
            raw = unquote_to_bytes(m.group(3))
    else:
        if re.match(r"[a-z][a-z0-9+.\-]*://", value[:16], re.IGNORECASE):
            return None  # a web address: the provider fetches it, there is nothing inline
        media = str(node.get("media_type") or node.get("mime_type") or "").strip().lower()
        if not media and isinstance(node.get("format"), str):
            media = f"audio/{node['format'].lower()}"
        if _textual_media(media):
            return None  # an Anthropic text document, decoded into its own slot
        raw = _strict_b64decode(value)
        if raw is None:
            raise _unreadable_document()
    return {
        "filename": _attachment_name(node, media),
        "content_base64": base64.b64encode(raw).decode(),
    }


def media_attachments(data: dict[str, Any], call_type: str) -> list[dict[str, str]]:
    """Every inline file a provider would read from this request, ready for the brain.

    Only the exact places a provider reads media from count (see `_MEDIA_FIELDS`), in messages,
    Responses input and tool results. Raises GatewayError when there are too many to check.
    """
    if call_type in EMBEDDING_CALLS or call_type in TEXT_CALLS:
        return []
    found: list[dict[str, str]] = []

    def walk(node: Any, path: str, part_type: Any, depth: int) -> None:
        if depth > _MAX_DEPTH:
            return
        if isinstance(node, dict):
            if _PART.fullmatch(path):
                part_type = node.get("type")
            items: Any = node.items()
        elif isinstance(node, list):
            items = enumerate(node)
        else:
            return
        for key, value in items:
            if depth == 0 and isinstance(key, str) and key not in ("messages", "input"):
                continue
            here = f"{path}[{key}]" if isinstance(node, list) else f"{path}.{key}".lstrip(".")
            if isinstance(value, str) and isinstance(node, dict):
                if value and _in_media_position(part_type, here):
                    blob = _media_blob(node, value)
                    if blob is not None:
                        found.append(blob)
            elif isinstance(value, (dict, list)):
                walk(value, here, part_type, depth + 1)

    walk(data, "", None, 0)
    if len(found) > MAX_ATTACHMENTS or (
        sum(len(f["content_base64"]) for f in found) > MAX_ATTACHMENT_CHARS
    ):
        raise _too_many_files()
    return found


def _requester_metadata(data: dict[str, Any]) -> list[tuple[str, Any]]:
    """What the person put in `metadata`, without the fields the gateway adds to it."""
    found: list[tuple[str, Any]] = []
    for name in ("metadata", "litellm_metadata"):
        meta = data.get(name)
        if not isinstance(meta, dict):
            continue
        if isinstance(meta.get("requester_metadata"), dict):
            meta = meta["requester_metadata"]
        elif name == "litellm_metadata":
            continue
        mine = {k: v for k, v in meta.items() if k not in _LITELLM_METADATA}
        if mine not in [m for _, m in found]:
            found.append(("metadata", mine))
    return found


def _covered(slots: list[Slot]) -> set[tuple[int, Any]]:
    out: set[tuple[int, Any]] = set()
    for s in slots:
        if isinstance(s.write, _Writer):
            out.add((id(s.write.container), s.write.key))
        if s.where is not None:
            out.add(s.where)
    return out


def inspection_view(data: dict[str, Any], call_type: str) -> list[Slot]:
    """Every piece of text in the request that reaches the model.

    Strings found anywhere else in the request come first as read-only definition slots, then
    the named parts: definitions, system text and messages in order. Raises GatewayError when
    the request carries something that cannot be read as text.
    """
    if call_type in EMBEDDING_CALLS:
        named = _embedding_slots(data)
    elif call_type in RESPONSES_CALLS:
        named = _responses_slots(data)
    elif call_type in ANTHROPIC_CALLS:
        named = _anthropic_slots(data)
    elif call_type in TEXT_CALLS:
        named = _text_slots(data)
    else:
        named = _chat_slots(data)
    covered = _covered(named)
    rest: list[Slot] = []
    _sweep(data, covered, rest)
    for where, meta in _requester_metadata(data):
        _sweep(meta, covered, rest, 1, where)
    return rest + named


def _changes(slots: list[Slot], masked: Any) -> list[tuple[Slot, str]] | None:
    """The slots the brain rewrote, with their new text. None if the answer does not line up."""
    if not isinstance(masked, list) or len(masked) != len(slots):
        return None
    out: list[tuple[Slot, str]] = []
    for slot, m in zip(slots, masked, strict=True):
        content = m.get("content") if isinstance(m, dict) else None
        if not isinstance(content, str):
            return None
        if content != slot.text:
            out.append((slot, content))
    return out


def _reroute_asked(headers: dict[str, str] | None) -> bool:
    lowered = {k.lower(): v for k, v in (headers or {}).items()}
    return lowered.get(REROUTE_HEADER, "").strip() == "1"


def _ack_given(headers: dict[str, str] | None) -> bool:
    lowered = {k.lower(): v for k, v in (headers or {}).items()}
    return bool(lowered.get(ACK_HEADER, "").strip())


ACCEPTED_TTL_SECONDS = 3600
ACCEPTED_MAX_ENTRIES = 20_000


_SHARED_IDENTITIES = {"", "anonymous", "default_user_id"}
_HASHED_TOKEN = re.compile(r"[0-9a-f]{64}")


def acceptance_scope(user_id: str | None, token: str | None, role: Any = None) -> str | None:
    """Who a remembered acknowledgement belongs to, or None when nothing may be remembered.

    LiteLLM gives the master key the user `default_user_id`, the role proxy_admin and a fixed alias
    instead of a hashed token; a key made without a user has no user at all. Those identities are
    shared by many people, so acknowledging once would hide warnings from everyone else. A real
    personal key has its own user and a hashed token (64 hex characters), and the scope uses both,
    so two keys of the same user do not share what they acknowledged.
    """
    role_name = str(getattr(role, "value", role) or "")
    if (
        not user_id
        or user_id in _SHARED_IDENTITIES
        or role_name.startswith("proxy_admin")
        or not isinstance(token, str)
        or not _HASHED_TOKEN.fullmatch(token)
    ):
        return None
    return f"{user_id}\0{token}"


class _AcceptedMemory:
    """Texts a person already sent on purpose (with X-DNA-Ack), so a client that resends the whole
    history is not warned about the same text again on every call.

    The gateway holds it, keyed by the scope of the virtual key (see `acceptance_scope`): a client
    cannot name someone else's memory. Only a hash is kept, never the text. Shared identities have
    no scope and are never remembered. Everything is lost on restart, and a second gateway process
    has its own memory; both only mean an extra warning.
    """

    def __init__(self, ttl: float = ACCEPTED_TTL_SECONDS, size: int = ACCEPTED_MAX_ENTRIES) -> None:
        self._items: OrderedDict[str, float] = OrderedDict()
        self._ttl = ttl
        self._size = size
        self._lock = threading.Lock()

    @staticmethod
    def _key(scope: str, slot: Slot) -> str:
        raw = f"{scope}\0{slot.role}\0{slot.text}"
        return hashlib.sha256(raw.encode("utf-8", "surrogatepass")).hexdigest()

    def has(self, scope: str | None, slot: Slot) -> bool:
        if not scope:
            return False
        key = self._key(scope, slot)
        with self._lock:
            added = self._items.get(key)
            if added is None:
                return False
            if time.monotonic() - added >= self._ttl:
                del self._items[key]
                return False
            return True

    def add(self, scope: str | None, slots: list[Slot]) -> None:
        if not scope:
            return
        now = time.monotonic()
        with self._lock:
            for slot in slots:
                key = self._key(scope, slot)
                self._items[key] = now
                self._items.move_to_end(key)
            while len(self._items) > self._size:
                self._items.popitem(last=False)


ACCEPTED = _AcceptedMemory()


def _brain_detail(resp: httpx.Response) -> str:
    try:
        detail = resp.json().get("detail")
    except (ValueError, AttributeError):
        return "invalid request."
    if isinstance(detail, list):
        detail = "; ".join(str(d.get("msg", "")) for d in detail if isinstance(d, dict))
    return str(detail or "invalid request.")[:300]


async def apply_decision(
    data: dict[str, Any],
    *,
    user_id: str,
    team: str,
    headers: dict[str, str] | None,
    brain_url: str,
    client: httpx.AsyncClient,
    call_type: str = "completion",
    accept_scope: str | None = None,
) -> dict[str, Any]:
    """Ask the brain about this request and return the (possibly changed) request.

    Raises GatewayError for warn, block and brain failures. Fails closed: if the brain
    cannot be reached the request is not forwarded. Works for chat, Anthropic messages,
    responses and embeddings; other kinds of request are refused.
    """
    if call_type not in SUPPORTED_CALLS:
        raise GatewayError(
            403,
            {
                "type": "block",
                "message": "This kind of request is not available through the company gateway.",
                "reasons": [f"Unsupported request type: {call_type}"],
                "approved_alternative": "Use the chat or messages interface of the gateway.",
            },
        )
    refuse_connection_settings(data, call_type)
    if data.get("stream") and _several_answers(data.get("n")):
        raise GatewayError(
            403,
            {
                "type": "block",
                "message": "Several streamed answers at once are not supported. Send n=1 or "
                "turn streaming off.",
                "reasons": ["The request asks for several streamed answers"],
                "approved_alternative": "Send n=1, or turn streaming off.",
            },
        )
    # `organization` is not refused: clients such as the OpenAI SDK send it as a header, and LiteLLM
    # forwards neither that header nor this key unless forward_openai_org_id is set (it is not).
    # Dropping it keeps the key out of the request the model provider receives.
    data.pop("organization", None)
    slots = inspection_view(data, call_type)
    attachments = media_attachments(data, call_type)
    payload: dict[str, Any] = {
        "user_id": user_id,
        "team": team,
        "model": str(data.get("model", "default")),
        "messages": [{"role": s.role, "content": s.text} for s in slots],
    }
    if attachments:
        # The files themselves: the brain reads their text (OCR for images and scans) and checks
        # it with the messages. A file it cannot read is refused below, never let through unread.
        payload["attachments"] = attachments
    accepted = [i for i, s in enumerate(slots) if ACCEPTED.has(accept_scope, s)]
    accepted_ids = {id(slots[i]) for i in accepted}
    if accepted:
        payload["accepted_indexes"] = accepted
    if _reroute_asked(headers):
        payload["reroute"] = True
    try:
        # A long chat is worked out once and remembered, so only its first request is slow.
        size = sum(len(m["content"]) for m in payload["messages"])
        wait = 120.0 if attachments else min(120.0, 10.0 + size / 5000)
        resp = await client.post(f"{brain_url}/v1/inspect", json=payload, timeout=wait)
        if resp.status_code == 413:
            raise GatewayError(
                413,
                {
                    "type": "block",
                    "message": "This request is too large to check, so it was not sent.",
                    "next": "Shorten it or split it.",
                },
            )
        if resp.status_code == 422 and attachments:
            raise GatewayError(
                403,
                {
                    "type": "block",
                    "message": "A file in this request could not be checked, so nothing was "
                    f"sent: {_brain_detail(resp)}",
                    "reasons": ["An attached file could not be read by the safety check"],
                    "approved_alternative": "Send the file as PDF, Word, plain text or an image "
                    "(PNG, JPG), or paste the text you need.",
                },
            )
        if resp.status_code == 422:
            raise GatewayError(
                503,
                {
                    "type": "unavailable",
                    "message": "The safety check could not read this request, so it was not "
                    f"sent: {_brain_detail(resp)}",
                    "next": "Fix the request and send it again.",
                },
            )
        resp.raise_for_status()
        verdict = resp.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise GatewayError(
            503,
            {
                "type": "unavailable",
                "message": "The safety check is not available, so your message was not sent.",
                "next": "Try again in a minute. If it keeps happening, tell your IT contact.",
                "detail": type(exc).__name__,
            },
        ) from exc

    decision = verdict.get("decision") if isinstance(verdict, dict) else None
    if decision not in _DECISIONS:
        raise GatewayError(
            503,
            {
                "type": "unavailable",
                "message": "The safety check is not available, so your message was not sent.",
                "next": "Try again in a minute. If it keeps happening, tell your IT contact.",
                "detail": "unexpected answer from the safety check",
            },
        )
    reasons = verdict.get("reasons", [])

    rerouted = bool(verdict.get("rerouted"))
    if rerouted:
        # X31: the person chose Company AI. Masked text, the local model, never the original
        # destination, so a blocked tool is not called.
        changes = _changes(slots, verdict.get("masked_messages"))
        if (
            call_type not in CHAT_CALLS
            or changes is None
            or any(s.write is None or s.risky for s, _ in changes)
        ):
            raise GatewayError(
                403,
                {
                    "type": "block",
                    "message": "This kind of request cannot be rerouted. It was not sent.",
                    "reasons": reasons,
                    "approved_alternative": "Use the company chat, which keeps data inside.",
                },
            )
        for slot, new_text in changes:
            if slot.write is not None:
                slot.write(new_text)
        data["model"] = LOCAL_MODEL
        for k in _ROUTER_KEYS:
            data.pop(k, None)
        data.setdefault("metadata", {})["dna_session_id"] = verdict.get("session_id")
        decision = "rerouted"
    elif decision == "mask":
        changes = _changes(slots, verdict.get("masked_messages"))
        if changes:
            # Text the person already accepted that cannot be rewritten (a file, a signed block)
            # is sent as it is instead of asking again.
            # Only text the brain treated as earlier, accepted history counts: the same text sent
            # as the new message is checked in full.
            applied = {i for i in verdict.get("accepted_applied") or [] if isinstance(i, int)}
            accepted_ids = {id(slots[i]) for i in applied if 0 <= i < len(slots)} & accepted_ids
            kept = [
                (s, new)
                for s, new in changes
                if not (id(s) in accepted_ids and (s.write is None or s.risky))
            ]
            nothing_left = not kept
            changes = kept
        else:
            nothing_left = False
        if nothing_left:
            decision = "allow"
        elif changes is None:
            decision = "warn"
            reasons = [*reasons, "Sensitive data could not be masked safely"]
        elif not changes or any(s.write is None or s.risky for s, _ in changes):
            # A file, image or signed block cannot be rewritten in place: ask first instead.
            decision = "warn"
            named = next((s.path for s, _ in changes if s.write is None and s.path), "")
            reasons = [
                *reasons,
                f"Sensitive data in `{named}` cannot be masked automatically. Remove it or "
                "send with the X-DNA-Ack header."
                if named
                else "Sensitive data in a file or tool output cannot be masked automatically",
            ]
        else:
            for slot, new_text in changes:
                if slot.write is not None:
                    slot.write(new_text)
            data.setdefault("metadata", {})["dna_session_id"] = verdict.get("session_id")
    if decision == "local" and call_type in EMBEDDING_CALLS:
        raise GatewayError(
            403,
            {
                "type": "block",
                "message": "This text is confidential and cannot be sent to an embedding service.",
                "reasons": reasons,
                "approved_alternative": "Use the company chat, which keeps data inside.",
            },
        )
    elif decision == "local":
        data["model"] = LOCAL_MODEL
        for k in _ROUTER_KEYS:
            data.pop(k, None)
    elif decision == "warn" and not _ack_given(headers):
        raise GatewayError(
            409,
            {
                "type": "warn",
                "message": "This message may contain sensitive data.",
                "reasons": reasons,
                "suggested_rewrite": verdict.get("suggested_rewrite"),
                "options": ["Send anyway (add the X-DNA-Ack header with your reason)", "Edit it"],
            },
        )
    elif decision == "block":
        raise GatewayError(
            403,
            {
                "type": "block",
                "message": "This message was not sent because it contains protected data.",
                "reasons": reasons,
                "approved_alternative": "Use the company chat, which keeps data inside.",
            },
        )

    if decision == "warn":
        # Only a warning the person answered with the ack header is remembered.
        warned = verdict.get("warned_indexes")
        if verdict.get("decision") == "warn" and isinstance(warned, list):
            only = [slots[i] for i in warned if isinstance(i, int) and 0 <= i < len(slots)]
            ACCEPTED.add(accept_scope, only)
        else:
            ACCEPTED.add(accept_scope, slots)
    metadata = data.setdefault("metadata", {})
    metadata["dna_decision"] = decision
    metadata["dna_reasons"] = reasons
    return data


async def finalize_answer(
    text: str,
    *,
    user_id: str,
    team: str,
    session_id: str | None,
    brain_url: str,
    client: httpx.AsyncClient,
) -> str:
    """Filter a model answer, then restore the user's own masked values.

    Order matters: filter first, so only values the model invented or echoed are masked,
    then unmask, so the user's own values come back. If the brain cannot be reached the
    answer is withheld rather than returned unfiltered.
    """
    try:
        out = await client.post(
            f"{brain_url}/v1/inspect-output",
            json={"user_id": user_id, "team": team, "text": text},
            timeout=10.0,
        )
        out.raise_for_status()
        text = out.json()["text"]
        if session_id:
            back = await client.post(
                f"{brain_url}/v1/unmask",
                json={"session_id": session_id, "user_id": user_id, "text": text},
                timeout=10.0,
            )
            back.raise_for_status()
            text = back.json()["text"]
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        raise GatewayError(
            503,
            {
                "type": "unavailable",
                "message": "The answer could not be checked, so it was not shown.",
                "next": "Try again in a minute. If it keeps happening, tell your IT contact.",
                "detail": type(exc).__name__,
            },
        ) from exc
    return text


def _get(obj: Any, key: str) -> Any:
    return obj.get(key) if isinstance(obj, dict) else getattr(obj, key, None)


def _set(obj: Any, key: str, value: Any) -> None:
    if isinstance(obj, dict):
        obj[key] = value
    else:
        setattr(obj, key, value)


async def rewrite_output(output: Any, transform: Callable[[str], Awaitable[str]]) -> None:
    """Clean the text of a Responses API answer (`output[].content[].text`) in place."""
    for item in output if isinstance(output, list) else []:
        content = _get(item, "content")
        for part in content if isinstance(content, list) else []:
            text = _get(part, "text")
            if _get(part, "type") == "output_text" and isinstance(text, str):
                _set(part, "text", await transform(text))


def _text_holder(chunk: Any) -> tuple[Any, str] | None:
    """Where a streamed chunk keeps its text: `delta.content` for chat, `text` for completions."""
    choices = getattr(chunk, "choices", None)
    if not choices:
        return None
    delta = getattr(choices[0], "delta", None)
    if delta is not None and isinstance(getattr(delta, "content", None), str):
        return delta, "content"
    if isinstance(getattr(choices[0], "text", None), str):
        return choices[0], "text"
    return None


_FIELD = {"output_text": "text", "refusal": "refusal"}
_DELTA_KIND = {"response.output_text.delta": "output_text", "response.refusal.delta": "refusal"}
_DONE_KIND = {"response.output_text.done": "output_text", "response.refusal.done": "refusal"}
_FINAL_EVENTS = {
    "response.created",
    "response.in_progress",
    "response.completed",
    "response.incomplete",
    "response.failed",
}
_Key = tuple[str, int, int]


def _event_type(event: Any) -> str:
    kind = _get(event, "type")
    return str(getattr(kind, "value", kind)) if kind is not None else ""


def _is_response_event(chunk: Any) -> bool:
    return _event_type(chunk).startswith("response.")


def _index(event: Any, name: str) -> int:
    value = _get(event, name)
    return value if isinstance(value, int) else 0


def _text_parts(content: Any) -> list[tuple[int, Any, str]]:
    """(content index, part, text field) for every output_text and refusal part in a list."""
    out: list[tuple[int, Any, str]] = []
    for ci, part in enumerate(content if isinstance(content, list) else []):
        kind = _get(part, "type")
        kind = getattr(kind, "value", kind)
        if kind in _FIELD:
            out.append((ci, part, _FIELD[kind]))
    return out


def _event_text_slots(event: Any) -> list[tuple[_Key, Any, str]]:
    """Every place a non-delta event keeps answer text: (key, holder, field)."""
    kind = _event_type(event)
    slots: list[tuple[_Key, Any, str]] = []
    if kind in _DONE_KIND:
        field_ = _FIELD[_DONE_KIND[kind]]
        slots.append(
            ((_DONE_KIND[kind], _index(event, "output_index"), _index(event, "content_index")),
             event, field_)
        )
    elif kind in ("response.content_part.added", "response.content_part.done"):
        for _, part, field_ in _text_parts([_get(event, "part")]):
            key = (
                "output_text" if field_ == "text" else "refusal",
                _index(event, "output_index"),
                _index(event, "content_index"),
            )
            slots.append((key, part, field_))
    elif kind in ("response.output_item.added", "response.output_item.done"):
        oi = _index(event, "output_index")
        for ci, part, field_ in _text_parts(_get(_get(event, "item"), "content")):
            slots.append((("output_text" if field_ == "text" else "refusal", oi, ci), part, field_))
    elif kind in _FINAL_EVENTS:
        output = _get(_get(event, "response"), "output")
        for oi, item in enumerate(output if isinstance(output, list) else []):
            for ci, part, field_ in _text_parts(_get(item, "content")):
                slots.append(
                    (("output_text" if field_ == "text" else "refusal", oi, ci), part, field_)
                )
    return slots


def _clear_logprobs(holder: Any) -> None:
    if _get(holder, "logprobs"):
        _set(holder, "logprobs", [])


async def _rewrite_responses_events(
    events: list[Any], transform: Callable[[str], Awaitable[str]]
) -> list[Any]:
    """Clean the text of a streamed Responses API answer.

    Like chat, the whole answer is collected first. For each text block (kind, output index,
    content index) the deltas are joined and checked once; the first delta then carries all of
    the cleaned text and later deltas are empty, so the client still gets every event in order.
    The done, part, item and final-response events carry the same text, so they get the cleaned
    version too. A copy that does not match what was streamed is checked on its own. Reasoning,
    function-call arguments and annotations are not text answers and pass through.
    """
    deltas: dict[_Key, list[str]] = {}
    for event in events:
        kind = _DELTA_KIND.get(_event_type(event))
        delta = _get(event, "delta")
        if kind and isinstance(delta, str):
            key = (kind, _index(event, "output_index"), _index(event, "content_index"))
            deltas.setdefault(key, []).append(delta)
    cleaned: dict[str, str] = {}

    async def clean(raw: str) -> str:
        if raw not in cleaned:
            cleaned[raw] = await transform(raw)
        return cleaned[raw]

    # Checked before the first event leaves, so a brain failure withholds the whole answer.
    for parts in deltas.values():
        if any(parts):
            await clean("".join(parts))
    for event in events:
        for _, holder, field_ in _event_text_slots(event):
            value = _get(holder, field_)
            if isinstance(value, str) and value:
                await clean(value)
    first_seen: set[_Key] = set()
    done: set[tuple[int, str]] = set()  # one response object can sit in several events
    for event in events:
        kind = _DELTA_KIND.get(_event_type(event))
        delta = _get(event, "delta")
        if kind and isinstance(delta, str):
            key = (kind, _index(event, "output_index"), _index(event, "content_index"))
            if key not in first_seen:
                first_seen.add(key)
                joined = "".join(deltas[key])
                _set(event, "delta", cleaned[joined] if joined else "")
            else:
                _set(event, "delta", "")
            _clear_logprobs(event)
        for _, holder, field_ in _event_text_slots(event):
            value = _get(holder, field_)
            if (id(holder), field_) not in done and isinstance(value, str) and value:
                done.add((id(holder), field_))
                _set(holder, field_, cleaned[value])
            _clear_logprobs(holder)
    return events


def _unreadable_stream() -> GatewayError:
    return GatewayError(
        503,
        {
            "type": "unavailable",
            "message": "The answer could not be checked, so it was not shown.",
            "next": "Try again in a minute. If it keeps happening, tell your IT contact.",
            "detail": "UnreadableStream",
        },
    )


@dataclass
class _Frame:
    """One server-sent event: its raw text, and its JSON body when it has one."""

    raw: str
    name: str = ""
    body: dict[str, Any] | None = None
    changed: bool = False

    def text(self) -> str:
        if not self.changed or self.body is None:
            return self.raw
        head = f"event: {self.name}\n" if self.name else ""
        return f"{head}data: {json.dumps(self.body, ensure_ascii=False)}"


def _parse_frame(raw: str) -> _Frame:
    name = ""
    data: list[str] = []
    for line in raw.split("\n"):
        if line.startswith("event:"):
            name = line[6:].strip()
        elif line.startswith("data:"):
            data.append(line[5:].removeprefix(" "))
    frame = _Frame(raw, name)
    if data:
        try:
            body = json.loads("\n".join(data))
        except ValueError:
            body = None
        if body is not None and not isinstance(body, dict):
            raise _unreadable_stream()
        if isinstance(body, dict):
            frame.body = body
            frame.name = name or str(body.get("type", ""))
        elif "\n".join(data).strip() != "[DONE]":
            raise _unreadable_stream()
    return frame


_ANTHROPIC_EVENTS = {
    "message_start",
    "ping",
    "content_block_start",
    "content_block_delta",
    "content_block_stop",
    "message_delta",
    "message_stop",
    "error",
}
_TEXT_KEYS = {"text", "content", "delta", "message", "partial_json", "thinking", "arguments"}


def _has_text(node: Any) -> bool:
    if isinstance(node, dict):
        return any(
            (k in _TEXT_KEYS and isinstance(v, str) and v) or _has_text(v) for k, v in node.items()
        )
    if isinstance(node, list):
        return any(_has_text(v) for v in node)
    return False


def _block_index(body: dict[str, Any]) -> int:
    index = body.get("index")
    return index if isinstance(index, int) else 0


_START_FIELDS = {"text": "text", "thinking": "thinking"}
_DELTA_FIELDS = {
    "text_delta": "text",
    "input_json_delta": "partial_json",
    "thinking_delta": "thinking",
}


async def _rewrite_anthropic_sse(
    chunks: list[Any],
    transform: Callable[[str], Awaitable[str]],
    filter_only: Callable[[str], Awaitable[str]] | None = None,
) -> list[Any]:
    """Clean the text blocks of a streamed Anthropic `/v1/messages` answer.

    LiteLLM hands the stream over as raw server-sent-event bytes. The frames are put together
    first, since a frame or a placeholder can be split across chunks. For each text block the
    `text_delta`, `input_json_delta` (tool input) and `thinking_delta` pieces are joined and checked once (thinking is filtered but never unmasked); the first delta then holds the cleaned text
    and later ones are empty, so every frame keeps its place (if the opening frame already holds
    text, that frame gets it). Other frames (pings, message start and stop) pass through as received.
    """
    as_text = isinstance(chunks[0], str)
    try:
        # Join the bytes first: a multibyte character can be split between two chunks.
        joined = b"".join(c.encode("utf-8") if isinstance(c, str) else c for c in chunks).decode(
            "utf-8"
        )
    except UnicodeDecodeError as exc:
        raise _unreadable_stream() from exc
    lines = joined.replace("\r\n", "\n").replace("\r", "\n")  # every line ending a client accepts
    raws = [r for r in re.split(r"\n\n", lines) if r.strip()]
    frames = [_parse_frame(r) for r in raws]
    for f in frames:
        if f.body is not None and f.body.get("type") not in _ANTHROPIC_EVENTS and _has_text(f.body):
            # Text in a shape we cannot clean (for example chat-style chunks): withhold it.
            raise _unreadable_stream()
    parts: dict[tuple[int, str], list[str]] = {}
    for f in frames:
        body = f.body
        if body is None:
            continue
        if body.get("type") == "content_block_start":
            block = body.get("content_block")
            field = _START_FIELDS.get(str(block.get("type"))) if isinstance(block, dict) else None
            if field and isinstance(block, dict):
                parts.setdefault((_block_index(body), field), []).append(
                    str(block.get(field) or "")
                )
        elif body.get("type") == "content_block_delta":
            delta = body.get("delta")
            field = _DELTA_FIELDS.get(str(delta.get("type"))) if isinstance(delta, dict) else None
            if field and isinstance(delta, dict):
                parts.setdefault((_block_index(body), field), []).append(
                    str(delta.get(field) or "")
                )
    cleaned = {
        k: await (filter_only if k[1] == "thinking" and filter_only else transform)("".join(p))
        for k, p in parts.items()
        if any(p)
    }
    placed: set[tuple[int, str]] = set()
    for f in frames:
        body = f.body
        if body is None:
            continue
        index = _block_index(body)
        if body.get("type") == "content_block_start":
            block = body.get("content_block")
            if isinstance(block, dict) and block.get("type") == "tool_use" and block.get("input"):
                # A tool call can open with input already filled in.
                try:
                    block["input"] = json.loads(
                        await transform(json.dumps(block["input"], ensure_ascii=False))
                    )
                except ValueError as exc:
                    raise _unreadable_stream() from exc
                f.changed = True
            field = _START_FIELDS.get(str(block.get("type"))) if isinstance(block, dict) else None
            if field and isinstance(block, dict) and (index, field) in parts and block.get(field):
                block[field] = cleaned[(index, field)] if (index, field) not in placed else ""
                placed.add((index, field))
                f.changed = True
        elif body.get("type") == "content_block_delta":
            delta = body.get("delta")
            field = _DELTA_FIELDS.get(str(delta.get("type"))) if isinstance(delta, dict) else None
            if field and isinstance(delta, dict) and (index, field) in parts:
                if (index, field) in cleaned and (index, field) not in placed:
                    placed.add((index, field))
                    delta[field] = cleaned[(index, field)]
                else:
                    delta[field] = ""
                f.changed = True
    out = [f.text() + "\n\n" for f in frames]
    return out if as_text else [x.encode("utf-8") for x in out]


WITHHELD_MARK = "[Removed"


WITHHELD_ARGUMENTS = "[Removed: a tool call was withheld because its arguments held sensitive data.]"


async def clean_arguments(
    text: str,
    transform: Callable[[str], Awaitable[str]],
    whole_check: Callable[[str], Awaitable[str]] | None = None,
) -> tuple[str, str | None]:
    """Clean tool-call arguments. Valid JSON is cleaned string by string (values and keys), so a
    value that holds a quote, a backslash or a newline stays valid JSON; numbers are checked as
    text too (a card number can be a JSON number); anything else is cleaned as plain text.

    `whole_check` (the answer filter without unmasking) also looks at the arguments as one text, so
    a value split across several fields is not missed: if it finds something that no single
    field accounts for, the call is withheld. Returns the arguments and, if something had to be
    withheld, a notice (the arguments are then `{}` and the caller shows the notice instead)."""
    seen: dict[str, str] = {}
    notice: list[str] = []

    async def leaf(value: str) -> str:
        if not value.strip():
            return value
        if value not in seen:
            seen[value] = await transform(value)
            if seen[value].startswith(WITHHELD_MARK):
                notice.append(seen[value])
        return seen[value]

    async def walk(node: Any) -> Any:
        if isinstance(node, bool) or node is None:
            return node
        if isinstance(node, (int, float)):
            out = await leaf(json.dumps(node))
            return node if out == json.dumps(node) else out
        if isinstance(node, str):
            return await leaf(node)
        if isinstance(node, dict):
            return {(await leaf(k)): await walk(v) for k, v in node.items()}
        if isinstance(node, list):
            return [await walk(v) for v in node]
        return node

    try:
        parsed = json.loads(text)
    except ValueError:
        out = await leaf(text)
        return ("{}", notice[0]) if notice else (out, None)
    walked = await walk(parsed)
    cleaned = json.dumps(walked, ensure_ascii=False)
    if notice:
        return "{}", notice[0]
    if whole_check is not None:
        # The cleaned result is looked at as one text: anything still found or changed in it
        # (a value split across fields) withholds the call, even if single fields were masked.
        whole = await whole_check(cleaned)
        if whole.startswith(WITHHELD_MARK):
            return "{}", whole
        if whole != cleaned:
            return "{}", WITHHELD_ARGUMENTS
    return cleaned, None


async def _clean_side_channels(
    chunks: list[Any],
    transform: Callable[[str], Awaitable[str]],
    filter_only: Callable[[str], Awaitable[str]] | None = None,
) -> list[str]:
    """Streamed tool-call arguments, reasoning and refusal text: each is joined, checked once and
    put in the first chunk that carried it; the later chunks keep their place without text.
    Returns the notices of any tool call whose arguments had to be withheld."""
    notices: list[str] = []
    slots: dict[tuple[str, int], list[tuple[Any, str]]] = {}
    for chunk in chunks:
        choices = getattr(chunk, "choices", None)
        delta = getattr(choices[0], "delta", None) if choices else None
        if delta is None:
            continue
        for name in ("reasoning_content", "refusal"):
            if isinstance(getattr(delta, name, None), str) and getattr(delta, name):
                slots.setdefault((name, 0), []).append((delta, name))
        for n, block in enumerate(getattr(delta, "thinking_blocks", None) or []):
            if isinstance(_get(block, "thinking"), str) and _get(block, "thinking"):
                slots.setdefault(("thinking", n), []).append((block, "thinking"))
        for n, call in enumerate(getattr(delta, "tool_calls", None) or []):
            fn = getattr(call, "function", None)
            args = getattr(fn, "arguments", None)
            if isinstance(args, str) and args:
                index = getattr(call, "index", None)
                slots.setdefault(("tool", index if isinstance(index, int) else n), []).append(
                    (fn, "arguments")
                )
    for (kind, _), holders in slots.items():
        joined = "".join(str(_get(h, a)) for h, a in holders)
        if kind == "tool":
            cleaned, notice = await clean_arguments(joined, transform, filter_only)
            if notice:
                notices.append(notice)
        else:
            # Thinking is filtered but never unmasked, as for Anthropic blocks.
            run = filter_only if kind == "thinking" and filter_only else transform
            cleaned = await run(joined)
        for n, (holder, attr) in enumerate(holders):
            _set(holder, attr, cleaned if n == 0 else "")
    return notices


async def rewrite_stream(
    chunks: AsyncIterator[Any],
    transform: Callable[[str], Awaitable[str]],
    filter_only: Callable[[str], Awaitable[str]] | None = None,
) -> AsyncIterator[Any]:
    """Check a streamed answer before the client sees any of it.

    The whole answer is collected first, because a secret or a placeholder can be split across
    chunks and a half-seen value cannot be filtered. The cleaned text is then sent in the first
    content chunk; chunks without text (role, finish reason, usage) pass through in order. The
    client still gets a normal stream, only the text arrives together.
    """
    buffered: list[Any] = []
    parts: list[str] = []
    async for chunk in chunks:
        buffered.append(chunk)
        holder = _text_holder(chunk)
        if holder is not None:
            parts.append(getattr(holder[0], holder[1]))
    if buffered and all(isinstance(c, (bytes, str)) for c in buffered):
        for frame in await _rewrite_anthropic_sse(buffered, transform, filter_only):
            yield frame
        return
    if any(_is_response_event(c) for c in buffered):
        for event in await _rewrite_responses_events(buffered, transform):
            yield event
        return
    notices = await _clean_side_channels(buffered, transform, filter_only)
    cleaned = await transform("".join(parts)) if parts else ""
    if notices:
        cleaned = "\n".join(x for x in (cleaned, *notices) if x)
        if not parts:
            # No chunk carried text: let the first one with a delta carry the notice.
            for chunk in buffered:
                choices = getattr(chunk, "choices", None)
                delta = getattr(choices[0], "delta", None) if choices else None
                if delta is not None:
                    delta.content = ""
                    break
    placed = False
    for chunk in buffered:
        holder = _text_holder(chunk)
        if holder is None:
            yield chunk
        elif not placed:
            setattr(holder[0], holder[1], cleaned)
            placed = True
            yield chunk
        elif getattr(chunk.choices[0], "finish_reason", None):
            # A later chunk that ends the answer keeps its place, without text.
            setattr(holder[0], holder[1], "")
            yield chunk


# Streaming the local model's answer as it is written. The last characters stay back until a later
# check has seen what follows them, so a value split across chunks is never shown half-checked.
STREAM_HOLD_CHARS = 64
STREAM_CHECK_EVERY = 40


def _has_side_channel(chunk: Any) -> bool:
    """Reasoning, refusal, thinking or tool-call text: checked once at the end, never streamed."""
    choices = getattr(chunk, "choices", None)
    delta = getattr(choices[0], "delta", None) if choices else None
    if delta is None:
        return False
    names = ("reasoning_content", "refusal", "thinking_blocks", "tool_calls", "function_call")
    return any(getattr(delta, name, None) for name in names)


async def stream_progressively(
    chunks: AsyncIterator[Any],
    transform: Callable[[str], Awaitable[str]],
    filter_only: Callable[[str], Awaitable[str]] | None = None,
    *,
    hold: int = STREAM_HOLD_CHARS,
    every: int = STREAM_CHECK_EVERY,
) -> AsyncIterator[Any]:
    """Stream a chat answer from the company's own model while it is being written.

    Used only when the gate chose "local": the text never leaves the company. Every check runs on
    the whole answer so far and only checked text is sent, minus the last `hold` characters. The
    full answer is checked once more at the end. If that last check changes text already sent
    (an answer that turned into a protected document is withheld whole), the checked version
    follows after a blank line, so what the person ends with is always the checked answer.
    """
    raw = ""
    shown = ""
    checked = 0
    seen_text = False
    spare: tuple[Any, tuple[Any, str]] | None = None  # a text chunk not sent yet, to carry text
    last_text: Any = None  # the shape to copy if no chunk is left to carry the rest
    ending: list[Any] = []  # chunks that must come after the last text, in their order
    async for chunk in chunks:
        holder = _text_holder(chunk)
        choices = getattr(chunk, "choices", None)
        finish = getattr(choices[0], "finish_reason", None) if choices else None
        if _has_side_channel(chunk) or finish:
            if holder is not None:
                raw += getattr(holder[0], holder[1])
                setattr(holder[0], holder[1], "")
            ending.append(chunk)
            continue
        if holder is None:
            if seen_text:
                ending.append(chunk)
            else:
                yield chunk  # the role chunk opens the stream at once
            continue
        seen_text = True
        raw += getattr(holder[0], holder[1])
        spare = (chunk, holder)
        last_text = chunk
        if len(raw) - checked < every:
            continue
        checked = len(raw)
        cleaned = await transform(raw)
        safe = cleaned[: max(0, len(cleaned) - hold)]
        if len(safe) > len(shown) and safe.startswith(shown):
            setattr(holder[0], holder[1], safe[len(shown) :])
            shown = safe
            spare = None
            yield chunk
    cleaned = await transform(raw) if raw else ""
    rest = cleaned[len(shown) :] if cleaned.startswith(shown) else "\n\n" + cleaned
    notices = await _clean_side_channels(ending, transform, filter_only)
    if notices:
        rest = "\n".join(x for x in (rest, *notices) if x)
    if rest:
        if spare is not None:
            setattr(spare[1][0], spare[1][1], rest)
            yield spare[0]
        else:
            carrier = next((c for c in ending if _text_holder(c) is not None), None)
            if carrier is not None:
                holder = _text_holder(carrier)
                assert holder is not None
                setattr(holder[0], holder[1], rest)
            else:
                ending.insert(0, _text_chunk_like([last_text, *ending], rest))
    for chunk in ending:
        yield chunk


def _text_chunk_like(chunks: list[Any], text: str) -> Any:
    """A text chunk for the rest of the answer when no chunk is left to carry it.

    A chunk the client already reads is copied, so the new one has the same shape."""
    for chunk in chunks:
        choices = getattr(chunk, "choices", None)
        delta = getattr(choices[0], "delta", None) if choices else None
        if delta is not None:
            twin = copy.deepcopy(chunk)
            twin_delta = twin.choices[0].delta
            twin_delta.content = text
            for name in ("reasoning_content", "refusal", "thinking_blocks", "tool_calls"):
                if hasattr(twin_delta, name):
                    setattr(twin_delta, name, None)
            if hasattr(twin.choices[0], "finish_reason"):
                twin.choices[0].finish_reason = None
            return twin
    raise GatewayError(
        503,
        {
            "type": "unavailable",
            "message": "The answer could not be checked, so it was not shown.",
            "next": "Try again in a minute. If it keeps happening, tell your IT contact.",
        },
    )
