"""Tool registry unit tests — run handlers directly without HTTP."""
import datetime as dt

import pytest

from app.database import SessionLocal
from app.tools import TOOL_REGISTRY, get_tool_names, run_tool, tool_schemas


@pytest.fixture()
def db():
    session = SessionLocal()
    yield session
    session.close()


def test_registry_entries_have_required_fields(db):
    for _name, spec in TOOL_REGISTRY.items():
        assert "description" in spec
        assert "parameters" in spec
        assert "handler" in spec


def test_get_time_returns_iso(db):
    result = run_tool("get_time", "user-1", db, {})
    assert result.text.startswith("Current UTC time:")
    assert "T" in result.text


def test_email_validates_recipient(db):
    result = run_tool("send_email", "user-1", db, {"to": "not-an-email", "subject": "Hi", "body": "x"})
    assert "Invalid email" in result.text
    good = run_tool("send_email", "user-1", db, {"to": "a@b.com", "subject": "Hi", "body": "x"})
    assert "queued" in good.text


def test_slack_channel_normalized(db):
    result = run_tool("send_slack", "user-1", db, {"channel": "general", "message": "hello"})
    assert "#general" in result.text


def test_github_action_whitelist(db):
    result = run_tool("github_action", "user-1", db, {"action": "delete_everything", "repo": "x"})
    assert "Unsupported GitHub action" in result.text
    ok = run_tool("github_action", "user-1", db, {"action": "create_issue", "repo": "a/b"})
    assert "executed" in ok.text


def test_code_exec_arithmetic(db):
    result = run_tool("code_exec", "user-1", db, {"code": "(2 + 3) * 4"})
    assert "20" in result.text


def test_code_exec_blocks_imports(db):
    result = run_tool("code_exec", "user-1", db, {"code": "__import__('os').system('ls')"})
    assert "rejected" in result.text


def test_code_exec_blocks_io(db):
    result = run_tool("code_exec", "user-1", db, {"code": "open('/etc/passwd').read()"})
    assert "rejected" in result.text


def test_code_exec_blocks_dunders(db):
    result = run_tool("code_exec", "user-1", db, {"code": "(1).__class__.__mro__"})
    assert "rejected" in result.text


def test_code_exec_syntax_error(db):
    result = run_tool("code_exec", "user-1", db, {"code": "1 +"})
    assert "syntax error" in result.text


def test_code_exec_blocks_comprehensions(db):
    result = run_tool("code_exec", "user-1", db, {"code": "[x for x in range(10)]"})
    assert "rejected" in result.text


def test_unknown_tool_returns_error(db):
    result = run_tool("nope", "user-1", db, {})
    assert "Unknown tool" in result.text


def test_tool_schemas_filters_by_enabled(db):
    schemas = tool_schemas(["get_time"])
    assert len(schemas) == 1
    assert schemas[0]["function"]["name"] == "get_time"


def test_web_search_demo_mode(db):
    result = run_tool("web_search", "user-1", db, {"query": "python"})
    assert "demo mode" in result.text
