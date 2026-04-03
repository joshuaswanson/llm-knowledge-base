import httpx

from kb.config import (
    ANTHROPIC_MODEL,
    MAX_TOKENS,
    OLLAMA_BASE_URL,
    OLLAMA_MODEL,
    PROVIDER,
)


def _ask_ollama(prompt: str, system: str, model: str) -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    response = httpx.post(
        f"{OLLAMA_BASE_URL}/api/chat",
        json={"model": model, "messages": messages, "stream": False},
        timeout=300,
    )
    response.raise_for_status()
    return response.json()["message"]["content"]


def _ask_anthropic(prompt: str, system: str, model: str) -> str:
    import anthropic

    client = anthropic.Anthropic()
    messages = [{"role": "user", "content": prompt}]
    kwargs: dict = {"model": model, "max_tokens": MAX_TOKENS, "messages": messages}
    if system:
        kwargs["system"] = system
    response = client.messages.create(**kwargs)
    return response.content[0].text


def ask(prompt: str, *, system: str = "") -> str:
    if PROVIDER == "anthropic":
        return _ask_anthropic(prompt, system, ANTHROPIC_MODEL)
    return _ask_ollama(prompt, system, OLLAMA_MODEL)
