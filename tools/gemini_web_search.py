"""Minimal Gemini web research tool for IBM watsonx Orchestrate."""
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ibm_watsonx_orchestrate.agent_builder.connections import (
    ConnectionType,
    ExpectedCredentials,
)
from ibm_watsonx_orchestrate.agent_builder.tools import tool, ToolPermission
from ibm_watsonx_orchestrate.run import connections

APP_ID = "gemini_web_search_ibm_184bdbd3"

EXPECTED_CREDS = [
    ExpectedCredentials(app_id=APP_ID, type=ConnectionType.KEY_VALUE),
]

# Default model — override at runtime with the GEMINI_MODEL env var stored in the connection.
DEFAULT_MODEL = "gemini-3.5-flash-lite"


def _get_api_key() -> str:
    """Fetch the Gemini API key from the wxO connection, falling back to env var."""
    try:
        creds = connections.key_value(APP_ID)
        key = (creds.get("api_key") or "").strip()
        if key:
            return key
    except Exception:
        pass
    return os.environ.get("GEMINI_API_KEY", "").strip()


@tool(
    permission=ToolPermission.READ_ONLY,
    expected_credentials=EXPECTED_CREDS,
)
def gemini_web_search(query: str) -> str:
    """Research a question using Gemini (no live web search).

    Use for UK FCA mortgage guidance and regulatory research based on the
    model's training knowledge. Independently verify all legal rules cited.

    Args:
        query (str): The specific research question or search request.

    Returns:
        str: Gemini's answer, or a concise error message.
    """
    api_key = _get_api_key()
    if not api_key:
        return "Configuration error: GEMINI_API_KEY is not set in the tool runtime."
    if not query.strip():
        return "Please provide a research question."

    model = os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)
    # Strip any leading "models/" prefix; the generateContent URL adds it.
    model_id = model.lstrip("models/").strip("/")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent"
    body = json.dumps({
        "contents": [{"parts": [{"text": query[:500]}]}],
    }).encode("utf-8")
    request = Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=45) as response:
            result = json.load(response)
    except HTTPError as exc:
        message = exc.read(1000).decode("utf-8", errors="replace")
        return f"Gemini API error (HTTP {exc.code}): {message}"
    except (URLError, TimeoutError) as exc:
        return f"Gemini connection error: {exc}"

    # Parse the generateContent response (no grounding metadata without google_search tool).
    answer = ""
    for candidate in result.get("candidates", []):
        for part in (candidate.get("content") or {}).get("parts") or []:
            answer += part.get("text") or ""

    return answer.strip() or f"No text returned (raw: {json.dumps(result)[:300]})"
