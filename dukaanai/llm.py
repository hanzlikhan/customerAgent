"""Single choke point for all Groq LLM calls (Phase 2).

Authentication, in order of preference:
  1. On the developer's own machine: the GROQ_API_KEY environment variable
     (via .env). Get a free key at https://console.groq.com (no card required).
  2. In the build sandbox: the secure-connector surrogate exchange, used only
     when that mechanism is importable. It is NEVER read from .env there and
     never appears in any file or log.

Quirks (verified 2026-10-14, do not regress):
  - A normal User-Agent header is REQUIRED (Cloudflare 1010 blocks
    Python-urllib's default UA).
  - reasoning_effort="low" is REQUIRED for gpt-oss models, otherwise the
    content field can come back empty.
  - Model: openai/gpt-oss-120b (llama-3.3-70b-versatile is RETIRED).
"""

import json
import sys
import urllib.request
import urllib.error

try:
    sys.path.insert(0, "/opt/muse/skills/custom-connector-setup/bin")
    from dynamic_credentials import add_surrogate_to_request, read_json_response
    _USE_SURROGATE = True
except ImportError:
    _USE_SURROGATE = False

from . import config

_API_URL = "https://api.groq.com/openai/v1/chat/completions"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args):
        raise RuntimeError("redirect refused, verify the endpoint")


def chat(user_prompt: str, system_prompt: str = "",
         max_tokens: int = 800, temperature: float = 0.0) -> str:
    """One chat completion. Returns the assistant's text (stripped).

    temperature defaults to 0.0: a shop receptionist must be
    deterministic, not creative.
    """
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})

    body = json.dumps({
        "model": config.GROQ_MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "reasoning_effort": "low",
    }).encode()

    headers = {
        "User-Agent": "DukaanAI/1.0",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    request = urllib.request.Request(_API_URL, data=body, headers=headers)

    if _USE_SURROGATE:
        add_surrogate_to_request(
            request, "custom.groq", allowed_hosts=["api.groq.com"]
        )
        reader = read_json_response
    else:
        request.add_header(
            "Authorization", f"Bearer {config.require_groq_key()}"
        )

        def reader(response):  # noqa: E306
            return json.loads(response.read().decode())

    try:
        with urllib.request.build_opener(NoRedirect()).open(
            request, timeout=120
        ) as response:
            data = reader(response)
    except urllib.error.HTTPError as e:
        raise RuntimeError(
            f"Groq HTTP {e.code}: {e.read()[:300]!r}"
        ) from e
    return (data["choices"][0]["message"].get("content") or "").strip()
