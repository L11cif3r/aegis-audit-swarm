"""OpenAI-compatible surface: message handling, response shaping, auth bearer."""
import asyncio

from llm.providers import flatten_messages, _split_system, _to_gemini_contents
from gateway.openai_compat import _coerce_content, _completion
from gateway import auth
from config import settings


def test_flatten_messages_marks_roles():
    msgs = [
        {"role": "system", "content": "be terse"},
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
        {"role": "user", "content": "bye"},
    ]
    flat = flatten_messages(msgs)
    assert "system: be terse" in flat
    assert "assistant: hello" in flat
    assert "hi" in flat and "bye" in flat


def test_split_system_extracts_system():
    msgs = [
        {"role": "system", "content": "S1"},
        {"role": "system", "content": "S2"},
        {"role": "user", "content": "U"},
    ]
    system, rest = _split_system(msgs)
    assert system == "S1\nS2"
    assert rest == [{"role": "user", "content": "U"}]


def test_gemini_role_mapping():
    contents = _to_gemini_contents([
        {"role": "user", "content": "a"},
        {"role": "assistant", "content": "b"},
        {"role": "system", "content": "c"},
    ])
    assert [c["role"] for c in contents] == ["user", "model", "user"]
    assert contents[0]["parts"][0]["text"] == "a"


def test_coerce_content_handles_parts_and_none():
    assert _coerce_content("plain") == "plain"
    assert _coerce_content([{"type": "text", "text": "a"}, {"type": "text", "text": "b"}]) == "ab"
    assert _coerce_content(None) == ""


def test_completion_shape_and_usage_totals():
    result = {
        "response": "hello world", "model": "gpt-4o-mini",
        "input_tokens": 10, "output_tokens": 5, "status": "success",
        "risk_score": 0.1, "cost_usd": 0.0001,
    }
    comp = _completion(result, "gpt-4o-mini")
    assert comp["object"] == "chat.completion"
    assert comp["choices"][0]["message"]["content"] == "hello world"
    assert comp["usage"] == {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}
    assert comp["x_aegis"]["risk_score"] == 0.1


def test_bearer_operator_api_key_resolves(monkeypatch):
    monkeypatch.setattr(settings, "api_keys", "op-secret")
    principal = asyncio.run(auth._principal_from_api_key("op-secret", None))
    assert principal is not None
    assert principal.roles == ("operator",)
    assert principal.scheme == "api_key"
