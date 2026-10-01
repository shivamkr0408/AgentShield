from agents.hooks import Decision, Kind, Risk, ToolCall, ToolResult
from agents.sandbox import Sandbox
from agents.tools import ToolGateway, Toolbox, html_to_text


class RecordingHook:
    def __init__(self, block: set[str] | None = None) -> None:
        self.calls: list[ToolCall] = []
        self.results: list[ToolResult] = []
        self.block = block or set()

    def before_call(self, call: ToolCall) -> Decision:
        self.calls.append(call)
        return Decision.block("test policy") if call.tool in self.block else Decision.allow()

    def after_result(self, result: ToolResult) -> ToolResult:
        self.results.append(result)
        result.content = f"[seen] {result.content}"
        return result


def test_every_tool_is_declared_with_kind_risk_and_schema(sandbox: Sandbox) -> None:
    specs = {spec.name: spec for spec in Toolbox(sandbox).specs()}
    assert set(specs) == {
        "list_emails", "read_email", "search_emails", "browse_web",
        "list_files", "read_file", "write_file", "send_email", "http_post",
    }
    assert specs["send_email"].kind is Kind.ACTION and specs["send_email"].risk is Risk.HIGH
    assert specs["read_email"].kind is Kind.READ
    schema = specs["send_email"].schema["function"]
    assert schema["name"] == "send_email"
    assert set(schema["parameters"]["required"]) == {"to", "subject", "body"}


def test_reads_and_actions_all_pass_through_the_hook(sandbox: Sandbox) -> None:
    hook = RecordingHook()
    gateway = ToolGateway(Toolbox(sandbox).specs(), hook=hook)

    content = gateway.execute("read_email", {"email_id": "e-109"}, "c1")
    gateway.execute("send_email", {"to": "maria.gomez@acme.test", "subject": "Hi", "body": "Thanks"}, "c2")

    assert [call.tool for call in hook.calls] == ["read_email", "send_email"]
    assert [result.source for result in hook.results] == ["inbox:e-109", "outbox"]
    assert content.startswith("[seen] ")
    assert all(result.trusted is False for result in hook.results)


def test_blocked_action_never_executes(sandbox: Sandbox) -> None:
    gateway = ToolGateway(Toolbox(sandbox).specs(), hook=RecordingHook(block={"send_email", "http_post"}))

    reply = gateway.execute("send_email", {"to": "a@b.test", "subject": "s", "body": "b"}, "c1")
    gateway.execute("http_post", {"url": "http://hooks.acme.test/x", "body": "b"}, "c2")

    assert reply.startswith("Blocked by security policy")
    assert sandbox.outbox == [] and sandbox.http_log == []
    decisions = gateway.trace.of_type("decision")
    assert [decision["allowed"] for decision in decisions] == [False, False]


def test_bad_calls_return_errors_to_the_model(sandbox: Sandbox) -> None:
    gateway = ToolGateway(Toolbox(sandbox).specs())
    assert "unknown tool" in gateway.execute("delete_everything", {}, "c1")
    assert "email_id: Missing required argument" in gateway.execute("read_email", {}, "c2")
    assert "No email with id" in gateway.execute("read_email", {"email_id": "e-999"}, "c3")
    assert "outside the workspace" in gateway.execute("read_file", {"path": "../manifest.json"}, "c4")
    assert len(gateway.trace.of_type("tool_error")) == 4


def test_string_booleans_are_coerced(sandbox: Sandbox) -> None:
    gateway = ToolGateway(Toolbox(sandbox).specs())
    unread = gateway.execute("list_emails", {"unread_only": "true"}, "c1")
    assert unread.count("UNREAD") == 6 and len(unread.splitlines()) == 6


def test_non_intranet_requests_are_recorded_not_sent(sandbox: Sandbox) -> None:
    tools = Toolbox(sandbox)
    assert tools.browse_web("https://example.test/page?q=1").content == "HTTP 200 OK (empty response)"
    tools.http_post("http://hooks.acme.test/standup", "update")
    assert [(r["method"], r["url"]) for r in sandbox.http_log] == [
        ("GET", "https://example.test/page?q=1"),
        ("POST", "http://hooks.acme.test/standup"),
    ]


def test_intranet_pages_are_fetched_over_http(sandbox: Sandbox) -> None:
    tools = Toolbox(sandbox)
    assert "Omar Haddad | Security Lead" in tools.browse_web("acme.test/team").content
    assert tools.browse_web("http://acme.test/nope").content.startswith("HTTP 404")
    assert sandbox.http_log == []


def test_list_files_is_recursive_and_hides_placeholders(sandbox: Sandbox) -> None:
    listing = Toolbox(sandbox).list_files().content.splitlines()
    assert "docs/projects/atlas-status.md" in listing
    assert "private/credentials.env" in listing
    assert not any(path.endswith(".keep") for path in listing)


def test_html_to_text_keeps_links_and_drops_scripts() -> None:
    text = html_to_text('<p>See <a href="/team">team</a></p><script>var x = 1;</script><style>p{}</style>')
    assert text == "See team (/team)"
