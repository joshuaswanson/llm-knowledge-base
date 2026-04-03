import anthropic

from kb.config import MAX_TOKENS, MODEL

_client: anthropic.Anthropic | None = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def ask(prompt: str, *, system: str = "", model: str = MODEL, max_tokens: int = MAX_TOKENS) -> str:
    messages = [{"role": "user", "content": prompt}]
    kwargs: dict = {"model": model, "max_tokens": max_tokens, "messages": messages}
    if system:
        kwargs["system"] = system
    response = get_client().messages.create(**kwargs)
    return response.content[0].text
