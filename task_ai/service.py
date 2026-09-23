"""OpenAI Responses API adapter. Synchronous: use a worker in async backends."""
import json
import math
import os
import socket
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .fallback import local_analysis
from .prompts import SYSTEM_PROMPT
from .schema import ANALYSIS_SCHEMA, ResponseValidationError, validate_analysis, validate_input

API_URL = "https://api.openai.com/v1/responses"
MAX_RESPONSE_BYTES = 256_000


class ProviderFailure(Exception):
    def __init__(self, reason):
        self.reason = reason
        super().__init__(reason)


def _call_openai(description, card, api_key, model, timeout):
    payload = {
        "model": model,
        "instructions": SYSTEM_PROMPT,
        "input": json.dumps({"description": description, "fields": card}, ensure_ascii=False),
        "store": False,
        "max_output_tokens": 1800,
        "text": {"format": {
            "type": "json_schema", "name": "task_clarification",
            "strict": True, "schema": ANALYSIS_SCHEMA,
        }},
    }
    request = Request(API_URL, data=json.dumps(payload).encode("utf-8"), headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }, method="POST")
    # One request only; no automatic retries that multiply latency or spending.
    with urlopen(request, timeout=timeout) as response:
        raw = response.read(MAX_RESPONSE_BYTES + 1)
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ResponseValidationError("Provider response too large")
    envelope = json.loads(raw)
    if not isinstance(envelope, dict):
        raise ResponseValidationError("Invalid response envelope")
    if envelope.get("status") != "completed":
        raise ProviderFailure("incomplete_response")
    output = envelope.get("output")
    if not isinstance(output, list):
        raise ResponseValidationError("Missing output")
    texts = []
    for item in output:
        if not isinstance(item, dict):
            raise ResponseValidationError("Invalid output item")
        if item.get("type") != "message":
            continue
        content = item.get("content")
        if not isinstance(content, list):
            raise ResponseValidationError("Invalid message content")
        for part in content:
            if not isinstance(part, dict):
                raise ResponseValidationError("Invalid content item")
            if part.get("type") == "refusal":
                raise ProviderFailure("refusal")
            if part.get("type") == "output_text":
                if not isinstance(part.get("text"), str):
                    raise ResponseValidationError("Invalid output text")
                texts.append(part["text"])
    if len(texts) != 1:
        raise ResponseValidationError("Expected one JSON output")
    return validate_analysis(json.loads(texts[0]))


def analyze_task(description, fields=None, *, offline=False):
    """Return JSON-compatible data. Bad input raises InputValidationError.

    Provider/config errors return mode='fallback' with a stable reason code.
    User text is never rewritten; card.confirmed is always False.
    """
    card = validate_input(description, fields)
    reason = None
    analysis = None
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if offline:
        reason = "offline_requested"
    elif not api_key:
        reason = "missing_api_key"
    else:
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
        try:
            timeout = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "15"))
            valid_config = bool(model) and math.isfinite(timeout) and 0 < timeout <= 60
        except ValueError:
            valid_config = False
        if not valid_config:
            reason = "invalid_configuration"
        else:
            try:
                analysis = _call_openai(description, card, api_key, model, timeout)
            except HTTPError as exc:
                reason = {401: "authentication_error", 403: "access_denied", 429: "rate_limit"}.get(
                    exc.code, "api_error")
                exc.close()
            except (TimeoutError, socket.timeout):
                reason = "timeout"
            except URLError as exc:
                reason = "timeout" if isinstance(exc.reason, TimeoutError) else "network_error"
            except ProviderFailure as exc:
                reason = exc.reason
            except (ValueError, UnicodeError):
                reason = "invalid_response"
            except (OSError, HTTPException):
                reason = "network_error"
    if analysis is None:
        analysis = validate_analysis(local_analysis(description, card))
    return {
        "schema_version": "1.0",
        "mode": "fallback" if reason else "openai",
        "fallback_reason": reason,
        "requires_confirmation": True,
        "card": card,
        **analysis,
    }
