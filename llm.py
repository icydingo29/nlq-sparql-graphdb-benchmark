import re
import requests
import config
import prompt


def ask(question: str) -> tuple:
    """Send question to Ollama and return (sparql_or_None, raw_response_text)."""
    messages = prompt.build_messages(question)
    payload = {
        "model": config.OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
    }
    resp = requests.post(
        f"{config.OLLAMA_BASE_URL}/api/chat",
        json=payload,
        timeout=180,
    )
    resp.raise_for_status()
    raw = resp.json()["message"]["content"]
    sparql = _extract_sparql(raw)
    return sparql, raw


def _extract_sparql(text: str):
    # Prefer explicit ```sparql ... ``` block
    m = re.search(r"```sparql\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()
    # Fall back to any ``` block that starts with PREFIX
    m = re.search(r"```[a-z]*\s*(PREFIX\s+.*?)```", text, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return None
