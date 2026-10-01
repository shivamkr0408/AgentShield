import re

from agents.sandbox import Sandbox
from agents.tools import Toolbox
from eval.scenarios import load_tasks


def test_there_are_20_to_30_unique_tasks() -> None:
    tasks = load_tasks()
    assert 20 <= len(tasks) <= 30
    assert len({task.prompt for task in tasks.values()}) == len(tasks)


def test_every_task_constrains_side_effects() -> None:
    for task in load_tasks().values():
        types = {check["type"] for check in task.checks}
        assert types & {"no_outbound", "outbound_only_to"}, task.id


def test_files_and_pages_named_in_prompts_exist() -> None:
    with Sandbox() as sandbox:
        tools = Toolbox(sandbox)
        for task in load_tasks().values():
            for url in re.findall(r"http://acme\.test/\S+", task.prompt):
                assert not tools.browse_web(url.rstrip(".")).content.startswith("HTTP 404"), task.id
            for path in re.findall(r"\b(?:docs|reports)/[\w./-]+\.\w+", task.prompt):
                assert sandbox.resolve_file(path).is_file(), (task.id, path)


def test_planted_secrets_exist_in_private_files() -> None:
    with Sandbox() as sandbox:
        private = "".join(
            path.read_text(encoding="utf-8") for path in (sandbox.files_root / "private").iterdir()
        )
        assert sandbox.secrets and all(secret in private for secret in sandbox.secrets)
