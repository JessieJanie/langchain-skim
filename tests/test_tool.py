"""Unit tests for SkimReader.

These tests inject a fake payment-aware session (via the cached ``_session``
private attribute), so they never touch the network or sign a real payment.
"""

import pytest

from langchain_skim import SkimReader
from langchain_core.tools import ToolException

VALID_KEY = "0x" + "ab" * 32


class _FakeResp:
    def __init__(self, status=200, payload=None, text="", reason="OK"):
        self.status_code = status
        self._payload = payload or {}
        self.text = text
        self.reason = reason
        self.ok = 200 <= status < 300

    def json(self):
        return self._payload


class _FakeSession:
    def __init__(self, resp):
        self._resp = resp
        self.calls = []

    def post(self, url, json=None, timeout=None):
        self.calls.append({"url": url, "json": json, "timeout": timeout})
        return self._resp


def test_read_assembles_markdown_with_metadata_frontmatter():
    tool = SkimReader(private_key=VALID_KEY)
    fake = _FakeSession(
        _FakeResp(
            payload={
                "markdown": "# Title\n\nBody text.",
                "metadata": {
                    "title": "Title",
                    "byline": "Jane Doe",
                    "lang": "en",
                    "excerpt": "",  # empty values are filtered out
                    "siteName": None,  # None values are filtered out
                },
            }
        )
    )
    tool._session = fake

    out = tool.invoke({"url": "https://example.com/a"})

    assert out.startswith("---\n")
    assert "title: Title" in out
    assert "byline: Jane Doe" in out
    assert "lang: en" in out
    assert "excerpt:" not in out
    assert "siteName:" not in out
    assert out.endswith("# Title\n\nBody text.")

    call = fake.calls[0]
    assert call["url"].endswith("/api/v1/read")
    assert call["json"] == {"url": "https://example.com/a", "mode": "basic"}


def test_include_metadata_false_returns_plain_markdown():
    tool = SkimReader(private_key=VALID_KEY, include_metadata=False)
    tool._session = _FakeSession(
        _FakeResp(payload={"markdown": "# Title", "metadata": {"title": "Title"}})
    )

    out = tool.invoke({"url": "https://example.com/a"})

    assert out == "# Title"


def test_falls_back_to_text_when_no_markdown():
    tool = SkimReader(private_key=VALID_KEY, include_metadata=False)
    tool._session = _FakeSession(_FakeResp(payload={"text": "plain text"}))

    assert tool.invoke({"url": "https://example.com/a"}) == "plain text"


def test_custom_base_url_is_used():
    tool = SkimReader(private_key=VALID_KEY, base_url="https://example.test/")
    fake = _FakeSession(_FakeResp(payload={"markdown": "x"}))
    tool._session = fake

    tool.invoke({"url": "https://example.com/a"})

    assert fake.calls[0]["url"] == "https://example.test/api/v1/read"


def test_metadata_values_are_yaml_safe():
    tool = SkimReader(private_key=VALID_KEY)
    tool._session = _FakeSession(
        _FakeResp(
            payload={
                "markdown": "body",
                "metadata": {
                    "title": "Breaking: it works\nline two",
                    "excerpt": "a: b",
                    "lang": "en",
                },
            }
        )
    )

    out = tool.invoke({"url": "https://example.com/a"})

    assert 'title: "Breaking: it works line two"' in out
    assert 'excerpt: "a: b"' in out
    assert "lang: en" in out
    # No raw newline should leak into the frontmatter block.
    frontmatter = out.split("---\n\n", 1)[0]
    assert "\nline two" not in frontmatter


def test_non_json_response_raises_tool_exception():
    tool = SkimReader(private_key=VALID_KEY)

    class _BadJsonResp(_FakeResp):
        def json(self):
            raise ValueError("Expecting value")

    tool._session = _FakeSession(_BadJsonResp(text="<html>oops</html>"))

    with pytest.raises(ToolException):
        tool._run("https://example.com/a")


def test_http_error_raises_tool_exception():
    tool = SkimReader(private_key=VALID_KEY)
    tool._session = _FakeSession(
        _FakeResp(status=502, text="upstream boom", reason="Bad Gateway")
    )

    with pytest.raises(ToolException) as exc:
        tool._run("https://example.com/a")

    assert "502" in str(exc.value)


def test_missing_key_raises_value_error(monkeypatch):
    monkeypatch.delenv("SKIM_WALLET_PRIVATE_KEY", raising=False)
    tool = SkimReader()

    with pytest.raises(ValueError):
        tool._get_session()


def test_malformed_key_raises_value_error(monkeypatch):
    monkeypatch.delenv("SKIM_WALLET_PRIVATE_KEY", raising=False)
    tool = SkimReader(private_key="not-a-hex-key")

    with pytest.raises(ValueError):
        tool._get_session()
