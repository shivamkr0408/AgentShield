"""Mock tools and the gateway that routes every call through a single ``ToolHook``."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlsplit

import httpx
from langchain_core.utils.function_calling import convert_to_openai_tool
from pydantic import ValidationError, validate_call

from agents.hooks import Kind, PassThroughHook, Risk, ToolCall, ToolHook, ToolResult
from agents.sandbox import Sandbox, SandboxError
from agents.trace import Trace


@dataclass(frozen=True)
class ToolOutput:
    content: str
    source: str


@dataclass(frozen=True)
class ToolSpec:
    name: str
    func: Callable[..., ToolOutput]
    kind: Kind
    risk: Risk

    @property
    def schema(self) -> dict[str, Any]:
        return convert_to_openai_tool(self.func)


class _TextExtractor(HTMLParser):
    """Rough HTML-to-text conversion, like a typical agent web reader.

    Text hidden with CSS is kept, because simple readers do not evaluate styles.
    """

    _BLOCKS = {"p", "div", "li", "tr", "h1", "h2", "h3", "h4", "article", "section", "nav", "br", "table", "ul", "ol"}
    _SKIP = {"script", "style", "head"}

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self._skip_depth = 0
        self._href: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self._SKIP:
            self._skip_depth += 1
        elif tag in self._BLOCKS:
            self.parts.append("\n")
        elif tag in {"td", "th"}:
            self.parts.append(" | ")
        elif tag == "a":
            self._href = dict(attrs).get("href")

    def handle_endtag(self, tag: str) -> None:
        if tag in self._SKIP:
            self._skip_depth = max(0, self._skip_depth - 1)
        elif tag == "a" and self._href:
            self.parts.append(f" ({self._href})")
            self._href = None

    def handle_data(self, data: str) -> None:
        if not self._skip_depth:
            self.parts.append(data)

    def text(self) -> str:
        lines = (" ".join(line.split()) for line in "".join(self.parts).splitlines())
        return "\n".join(line for line in lines if line)


def html_to_text(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    return parser.text()


class Toolbox:
    """Tool implementations bound to one sandbox. Docstrings become the tool descriptions."""

    def __init__(self, sandbox: Sandbox) -> None:
        self.sandbox = sandbox

    def list_emails(self, unread_only: bool = False) -> ToolOutput:
        """List emails in the inbox, newest first, showing id, sender, date and subject.

        Args:
            unread_only: Only list unread emails.
        """
        emails = sorted(self.sandbox.inbox, key=lambda email: email["date"], reverse=True)
        rows = [
            f"{email['id']} | {email['from']} | {email['date']} | {email['subject']}"
            + (" | UNREAD" if email["unread"] else "")
            for email in emails
            if email["unread"] or not unread_only
        ]
        return ToolOutput("\n".join(rows) or "No emails.", "inbox")

    def read_email(self, email_id: str) -> ToolOutput:
        """Read one email in full and mark it as read.

        Args:
            email_id: The email id shown by list_emails, for example "e-104".
        """
        email = self.sandbox.find_email(email_id)
        email["unread"] = False
        content = (
            f"From: {email['from']}\nTo: {email['to']}\nDate: {email['date']}\n"
            f"Subject: {email['subject']}\n\n{email['body']}"
        )
        return ToolOutput(content, f"inbox:{email['id']}")

    def search_emails(self, query: str) -> ToolOutput:
        """Search emails by sender, subject or body text.

        Args:
            query: Case-insensitive text to look for.
        """
        needle = query.lower()
        rows = [
            f"{email['id']} | {email['from']} | {email['date']} | {email['subject']}"
            for email in self.sandbox.inbox
            if needle in f"{email['from']} {email['subject']} {email['body']}".lower()
        ]
        return ToolOutput("\n".join(rows) or f"No emails match {query!r}.", "inbox:search")

    def send_email(self, to: str, subject: str, body: str) -> ToolOutput:
        """Send an email on the user's behalf.

        Args:
            to: Recipient email address.
            subject: Subject line.
            body: Plain-text message body.
        """
        if "@" not in to:
            raise SandboxError(f"Invalid recipient address: {to!r}")
        message_id = f"out-{len(self.sandbox.outbox) + 1}"
        self.sandbox.outbox.append({"id": message_id, "to": to.strip(), "subject": subject, "body": body})
        return ToolOutput(f"Email sent to {to} (message id {message_id}).", "outbox")

    def browse_web(self, url: str) -> ToolOutput:
        """Open a web page and return its text. The company intranet is at http://acme.test.

        Args:
            url: Full URL of the page, for example "http://acme.test/policies/travel".
        """
        if "://" not in url:
            url = f"http://{url}"
        parts = urlsplit(url)
        host = (parts.hostname or "").lower()
        if host in {self.sandbox.site_host, f"www.{self.sandbox.site_host}"}:
            target = f"{self.sandbox.site_base_url}{parts.path or '/'}"
            response = httpx.get(target, params=parts.query or None, timeout=10)
            if response.status_code != 200:
                return ToolOutput(f"HTTP {response.status_code}: page not found.", f"web:{url}")
            return ToolOutput(html_to_text(response.text), f"web:{url}")
        # Every other host is a mock: the request is recorded and never leaves the machine.
        self.sandbox.http_log.append({"method": "GET", "url": url, "body": ""})
        return ToolOutput("HTTP 200 OK (empty response)", f"web:{url}")

    def http_post(self, url: str, body: str) -> ToolOutput:
        """Send an HTTP POST request, for example to a webhook or an internal API.

        Args:
            url: Destination URL.
            body: Request body, usually text or JSON.
        """
        self.sandbox.http_log.append({"method": "POST", "url": url, "body": body})
        return ToolOutput('HTTP 200 OK {"received": true}', f"http:{url}")

    def list_files(self, directory: str = ".") -> ToolOutput:
        """List files in the user's workspace, recursively.

        Args:
            directory: Workspace-relative directory to list, for example "docs".
        """
        root = self.sandbox.resolve_file(directory)
        if not root.is_dir():
            raise SandboxError(f"Not a directory: {directory}")
        paths = sorted(
            self.sandbox.workspace_path(path) for path in root.rglob("*") if path.is_file() and path.name != ".keep"
        )
        return ToolOutput("\n".join(paths) or "No files.", f"file:{directory}")

    def read_file(self, path: str) -> ToolOutput:
        """Read a text file from the user's workspace.

        Args:
            path: Workspace-relative file path, for example "docs/onboarding-checklist.md".
        """
        resolved = self.sandbox.resolve_file(path)
        if not resolved.is_file():
            raise SandboxError(f"No such file: {path}")
        return ToolOutput(resolved.read_text(encoding="utf-8"), f"file:{self.sandbox.workspace_path(resolved)}")

    def write_file(self, path: str, content: str) -> ToolOutput:
        """Create or overwrite a text file in the user's workspace.

        Args:
            path: Workspace-relative file path, for example "notes/summary.md".
            content: Full text to write.
        """
        resolved = self.sandbox.resolve_file(path)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding="utf-8")
        relative = self.sandbox.workspace_path(resolved)
        self.sandbox.file_writes.append({"path": relative, "content": content})
        return ToolOutput(f"Wrote {len(content)} characters to {relative}.", f"file:{relative}")

    def specs(self) -> list[ToolSpec]:
        return [
            ToolSpec("list_emails", self.list_emails, Kind.READ, Risk.LOW),
            ToolSpec("read_email", self.read_email, Kind.READ, Risk.LOW),
            ToolSpec("search_emails", self.search_emails, Kind.READ, Risk.LOW),
            # The URL itself can carry data out, so browsing is not risk-free.
            ToolSpec("browse_web", self.browse_web, Kind.READ, Risk.MEDIUM),
            ToolSpec("list_files", self.list_files, Kind.READ, Risk.LOW),
            ToolSpec("read_file", self.read_file, Kind.READ, Risk.LOW),
            ToolSpec("write_file", self.write_file, Kind.ACTION, Risk.MEDIUM),
            ToolSpec("send_email", self.send_email, Kind.ACTION, Risk.HIGH),
            ToolSpec("http_post", self.http_post, Kind.ACTION, Risk.HIGH),
        ]


class ToolGateway:
    """Executes tool calls. This is the only path from the model to a tool."""

    def __init__(self, specs: list[ToolSpec], hook: ToolHook | None = None, trace: Trace | None = None) -> None:
        self.specs = {spec.name: spec for spec in specs}
        self.hook = hook or PassThroughHook()
        self.trace = trace or Trace()
        self._validated = {spec.name: validate_call(spec.func) for spec in specs}

    @property
    def schemas(self) -> list[dict[str, Any]]:
        return [spec.schema for spec in self.specs.values()]

    def execute(self, name: str, args: dict[str, Any], call_id: str) -> str:
        spec = self.specs.get(name)
        if spec is None:
            self.trace.emit("tool_error", call_id=call_id, tool=name, error="unknown tool")
            return f"Error: unknown tool {name!r}. Available tools: {', '.join(self.specs)}."

        call = ToolCall(call_id=call_id, tool=name, args=dict(args), kind=spec.kind, risk=spec.risk)
        self.trace.emit("tool_call", call_id=call_id, tool=name, args=call.args, kind=call.kind, risk=call.risk)

        decision = self.hook.before_call(call)
        self.trace.emit("decision", call_id=call_id, allowed=decision.allowed, reason=decision.reason)
        if not decision.allowed:
            return f"Blocked by security policy: {decision.reason}"

        try:
            output = self._validated[name](**args)
        except ValidationError as error:
            details = "; ".join(f"{'.'.join(map(str, item['loc']))}: {item['msg']}" for item in error.errors())
            message = f"invalid arguments for {name}: {details}"
            self.trace.emit("tool_error", call_id=call_id, tool=name, error=message)
            return f"Error: {message}"
        except (SandboxError, httpx.HTTPError) as error:
            message = str(error) or type(error).__name__
            self.trace.emit("tool_error", call_id=call_id, tool=name, error=message)
            return f"Error: {message}"

        result = self.hook.after_result(ToolResult(call=call, content=output.content, source=output.source))
        self.trace.emit(
            "tool_result",
            call_id=call_id,
            tool=name,
            source=result.source,
            trusted=result.trusted,
            content=result.content,
            annotations=json.loads(json.dumps(result.annotations, default=str)),
        )
        return result.content
