import re

import httpx

from kb.config import (
    MAX_TOKENS,
    OLLAMA_BASE_URL,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    PROVIDER,
    get_model,
)


def _ask_ollama(prompt: str, system: str, model: str) -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    response = httpx.post(
        f"{OLLAMA_BASE_URL}/api/chat",
        json={"model": model, "messages": messages, "stream": False},
        timeout=1800,
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


def _ask_openai(prompt: str, system: str, model: str) -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    response = httpx.post(
        f"{OPENAI_BASE_URL}/chat/completions",
        headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
        json={"model": model, "messages": messages, "max_tokens": MAX_TOKENS},
        timeout=300,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def _strip_think_tags(text: str) -> str:
    return re.sub(r"<think>.*?</think>\s*", "", text, flags=re.DOTALL)


def ask(prompt: str, *, system: str = "") -> str:
    model = get_model()
    if PROVIDER == "anthropic":
        return _ask_anthropic(prompt, system, model)
    if PROVIDER == "openai":
        return _ask_openai(prompt, system, model)
    result = _ask_ollama(prompt, system, model)
    return _strip_think_tags(result)
