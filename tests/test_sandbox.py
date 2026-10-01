import pytest

from agents.sandbox import WORLD_DIR, InjectionSlot, Sandbox, SandboxError
from agents.tools import Toolbox
from agents.website import WORLD_SITE, create_site

MARKER = "SLOT-MARKER-7731"


def test_sandboxes_are_isolated_from_the_world_and_each_other() -> None:
    with Sandbox() as first, Sandbox() as second:
        Toolbox(first).write_file("notes/scratch.md", "hello")
        first.inbox[0]["unread"] = True

        assert first.resolve_file("notes/scratch.md").exists()
        assert not second.resolve_file("notes/scratch.md").exists()
        assert not (WORLD_DIR / "files" / "notes" / "scratch.md").exists()
        assert second.inbox[0]["unread"] is False


def test_sandbox_directory_is_removed_on_close() -> None:
    box = Sandbox()
    root = box.root
    box.close()
    assert not root.exists()


@pytest.mark.parametrize("path", ["../manifest.json", "../../inbox.json", "docs/../../site/index.html", "C:/Windows/win.ini"])
def test_file_access_is_confined_to_the_workspace(sandbox: Sandbox, path: str) -> None:
    with pytest.raises(SandboxError):
        sandbox.resolve_file(path)


def test_leading_slash_is_treated_as_workspace_relative(sandbox: Sandbox) -> None:
    assert sandbox.resolve_file("/docs/onboarding-checklist.md").is_file()


def test_email_slot_appends_to_body(sandbox: Sandbox) -> None:
    sandbox.inject(InjectionSlot("email", "e-104"), MARKER)
    assert Toolbox(sandbox).read_email("e-104").content.endswith(MARKER)


def test_file_slot_appends_to_file(sandbox: Sandbox) -> None:
    sandbox.inject(InjectionSlot("file", "docs/projects/atlas-status.md"), MARKER)
    output = Toolbox(sandbox).read_file("docs/projects/atlas-status.md")
    assert "Completion: 70%" in output.content and MARKER in output.content


def test_hidden_web_slot_is_invisible_in_html_but_reaches_the_agent(sandbox: Sandbox) -> None:
    sandbox.inject(InjectionSlot("web", "reviews", hidden=True), MARKER)
    html = (sandbox.site_root / "reviews.html").read_text(encoding="utf-8")
    assert f'<div style="display:none">{MARKER}</div>' in html

    output = Toolbox(sandbox).browse_web("http://acme.test/reviews")
    assert MARKER in output.content
    assert output.source == "web:http://acme.test/reviews"


def test_unknown_slot_targets_are_rejected(sandbox: Sandbox) -> None:
    with pytest.raises(SandboxError):
        sandbox.inject(InjectionSlot("email", "e-999"), MARKER)
    with pytest.raises(SandboxError):
        sandbox.inject(InjectionSlot("web", "no-such-page"), MARKER)


def test_site_serves_pages_and_404s() -> None:
    client = create_site(WORLD_SITE).test_client()
    assert b"per diem is $75" in client.get("/policies/travel").data
    assert b"Acme Intranet" in client.get("/").data
    assert client.get("/missing").status_code == 404
    assert client.get("/../manifest").status_code == 404
