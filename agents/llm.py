"""Local model access through Ollama."""

from __future__ import annotations

import httpx
from langchain_core.language_models import BaseChatModel

from agents.config import Settings


class ModelUnavailable(RuntimeError):
    pass


def check_ollama(settings: Settings) -> None:
    """Fail early with setup instructions if Ollama or the model is missing."""
    try:
        response = httpx.get(f"{settings.model_url}/api/tags", timeout=5)
        response.raise_for_status()
    except httpx.HTTPError as error:
        raise ModelUnavailable(
            f"Ollama is not reachable at {settings.model_url} ({error}). "
            "Install it from https://ollama.com/download and make sure it is running."
        ) from error
    names = {model["name"] for model in response.json().get("models", [])}
    if settings.model_name not in names and f"{settings.model_name}:latest" not in names:
        raise ModelUnavailable(
            f"Model {settings.model_name!r} is not pulled. Run: ollama pull {settings.model_name}"
        )


def chat_model(settings: Settings) -> BaseChatModel:
    from langchain_ollama import ChatOllama

    return ChatOllama(
        model=settings.model_name,
        base_url=settings.model_url,
        temperature=0,
        seed=settings.seed,
        num_ctx=settings.num_ctx,
    )
