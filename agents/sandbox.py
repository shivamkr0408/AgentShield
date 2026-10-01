"""An isolated, disposable copy of the mock world for one agent run.

Nothing here touches real accounts or the network: email goes to an in-memory outbox,
HTTP requests to anything but the local test site are only recorded, and file access
is confined to a temporary copy of the workspace.
"""

from __future__ import annotations

import json
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from agents.website import SiteServer

WORLD_DIR = Path(__file__).resolve().parent / "world"


class SandboxError(ValueError):
    """Raised for requests the sandbox refuses, such as paths outside the workspace."""


@dataclass(frozen=True)
class InjectionSlot:
    """A place in the world where untrusted content can carry an injected payload."""

    kind: Literal["email", "web", "file"]
    # Email id, site page path (e.g. "blog/customer-feedback"), or workspace file path.
    target: str
    # Web only: wrap the payload in an element hidden from human readers.
    hidden: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> InjectionSlot:
        return cls(kind=data["kind"], target=data["target"], hidden=data.get("hidden", False))


class Sandbox:
    def __init__(self, world_dir: Path = WORLD_DIR) -> None:
        self._tmp = Path(tempfile.mkdtemp(prefix="agentshield-"))
        self.root = self._tmp / "world"
        shutil.copytree(world_dir, self.root)

        manifest = json.loads((self.root / "manifest.json").read_text(encoding="utf-8"))
        self.user: dict[str, str] = manifest["user"]
        self.organization: str = manifest["organization"]
        self.site_host: str = manifest["site_host"]
        self.today: str = manifest["today"]
        self.secrets: list[str] = manifest["secrets"]

        self.inbox: list[dict[str, Any]] = json.loads((self.root / "inbox.json").read_text(encoding="utf-8"))
        self.outbox: list[dict[str, str]] = []
        self.http_log: list[dict[str, str]] = []
        self.file_writes: list[dict[str, str]] = []
        self._site: SiteServer | None = None

    @property
    def files_root(self) -> Path:
        return self.root / "files"

    @property
    def site_root(self) -> Path:
        return self.root / "site"

    @property
    def site_base_url(self) -> str:
        if self._site is None:
            self._site = SiteServer(self.site_root)
        return self._site.base_url

    def resolve_file(self, path: str) -> Path:
        relative = path.replace("\\", "/").lstrip("/") or "."
        base = self.files_root.resolve()
        resolved = (base / relative).resolve()
        if not resolved.is_relative_to(base):
            raise SandboxError(f"Path is outside the workspace: {path}")
        return resolved

    def workspace_path(self, resolved: Path) -> str:
        return resolved.relative_to(self.files_root.resolve()).as_posix() or "."

    def find_email(self, email_id: str) -> dict[str, Any]:
        for email in self.inbox:
            if email["id"] == email_id.strip():
                return email
        raise SandboxError(f"No email with id {email_id!r}")

    def inject(self, slot: InjectionSlot, payload: str) -> None:
        if slot.kind == "email":
            email = self.find_email(slot.target)
            email["body"] = f"{email['body']}\n\n{payload}"
        elif slot.kind == "file":
            path = self.resolve_file(slot.target)
            text = path.read_text(encoding="utf-8") if path.exists() else ""
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"{text}\n{payload}\n", encoding="utf-8")
        elif slot.kind == "web":
            path = self.site_root / f"{slot.target.strip('/')}.html"
            if not path.is_file():
                raise SandboxError(f"No site page {slot.target!r}")
            html = path.read_text(encoding="utf-8")
            block = f'<div style="display:none">{payload}</div>' if slot.hidden else f"<p>{payload}</p>"
            anchor = "</main>" if "</main>" in html else "</body>"
            path.write_text(html.replace(anchor, f"{block}\n{anchor}", 1), encoding="utf-8")
        else:
            raise SandboxError(f"Unknown injection slot kind {slot.kind!r}")

    def outbound(self) -> list[dict[str, str]]:
        """Everything the agent sent out of the sandbox, as channel/destination/content records."""
        records = [
            {"channel": "email", "destination": mail["to"], "content": f"{mail['subject']}\n{mail['body']}"}
            for mail in self.outbox
        ]
        records += [
            {"channel": "http", "destination": request["url"], "content": f"{request['url']}\n{request['body']}"}
            for request in self.http_log
        ]
        return records

    def close(self) -> None:
        if self._site is not None:
            self._site.stop()
            self._site = None
        shutil.rmtree(self._tmp, ignore_errors=True)

    def __enter__(self) -> Sandbox:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
