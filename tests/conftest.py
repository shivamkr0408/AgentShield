from __future__ import annotations

import os

# Keep the test suite hermetic and fast: never load a locally trained L2 model (CI has none).
os.environ.setdefault("AGENTSHIELD_LOAD_CLASSIFIER", "0")

from collections.abc import Iterator
from typing import Any

import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from agents.sandbox import Sandbox


class ScriptedChatModel(BaseChatModel):
    """Replays fixed responses so agent tests run without Ollama."""

    responses: list[AIMessage]
    index: int = 0
    bound_tools: list[Any] = []

    @property
    def _llm_type(self) -> str:
        return "scripted"

    def bind_tools(self, tools: Any, **kwargs: Any) -> ScriptedChatModel:
        self.bound_tools = list(tools)
        return self

    def _generate(self, messages: list[BaseMessage], stop: Any = None, run_manager: Any = None, **kwargs: Any) -> ChatResult:
        # A fresh copy each time, as LangGraph merges messages that share an id.
        message = self.responses[min(self.index, len(self.responses) - 1)].model_copy(deep=True)
        self.index += 1
        return ChatResult(generations=[ChatGeneration(message=message)])


def call(name: str, call_id: str = "c1", **args: Any) -> AIMessage:
    return AIMessage("", tool_calls=[{"name": name, "args": args, "id": call_id, "type": "tool_call"}])


def answer(text: str) -> AIMessage:
    return AIMessage(text)


@pytest.fixture
def sandbox() -> Iterator[Sandbox]:
    with Sandbox() as box:
        yield box
