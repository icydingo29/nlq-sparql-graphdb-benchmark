import re
import requests
import config
import few_shot_prompt as prompt


def ask(question: str) -> tuple:
    """Send question to Ollama and return (sparql_or_None, raw_response_text)."""
    messages = prompt.build_messages(question)
    return _call(messages)


def fix(question: str, bad_sparql: str, error_msg: str) -> tuple:
    """Ask the LLM to fix a SPARQL query that caused a syntax error."""
    messages = prompt.build_messages(question)
    messages.append({"role": "assistant", "content": f"```sparql\n{bad_sparql}\n```"})
    messages.append({
        "role": "user",
        "content": (
            f"That SPARQL query caused a syntax error:\n{error_msg}\n"
            "Please fix the syntax and return only the corrected SPARQL query."
        ),
    })
    return _call(messages)


def _call(messages: list) -> tuple:
    payload = {"model": config.OLLAMA_MODEL, "messages": messages, "stream": False}
    resp = requests.post(f"{config.OLLAMA_BASE_URL}/api/chat", json=payload, timeout=180)
    resp.raise_for_status()
    raw = resp.json()["message"]["content"]
    return _extract_sparql(raw), raw


def _extract_sparql(text: str):
    m = re.search(r"```sparql\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()
    m = re.search(r"```[a-z]*\s*(PREFIX\s+.*?)```", text, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return None
