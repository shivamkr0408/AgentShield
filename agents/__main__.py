"""Run the agent once on a free-form request: python -m agents "What's in my inbox?" """

from __future__ import annotations

import argparse
import dataclasses
import sys

from agents.agent import run_agent
from agents.config import Settings
from agents.llm import ModelUnavailable, chat_model, check_ollama
from agents.sandbox import Sandbox
from agents.trace import Trace, console_printer


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the sandboxed test agent on one request.")
    parser.add_argument("request", help="What to ask the agent.")
    parser.add_argument("--model", help="Ollama model name (default from .env).")
    args = parser.parse_args()

    settings = Settings.from_env()
    if args.model:
        settings = dataclasses.replace(settings, model_name=args.model)
    try:
        check_ollama(settings)
    except ModelUnavailable as error:
        sys.exit(str(error))

    with Sandbox() as sandbox:
        run_agent(args.request, sandbox, chat_model(settings), trace=Trace([console_printer]), max_steps=settings.max_steps)
        for mail in sandbox.outbox:
            print(f"OUTBOX  to={mail['to']} subject={mail['subject']!r}")
        for request in sandbox.http_log:
            print(f"HTTP    {request['method']} {request['url']}")


if __name__ == "__main__":
    main()
