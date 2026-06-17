"""AI Security Analyst — pure logic (no provider/DB calls)."""
import asyncio

from gateway import analyst


def test_summarize_empty_skips_llm():
    # No rows => deterministic message, never touches the provider.
    out = asyncio.run(analyst.summarize("tenant-x", []))
    assert out["generated"] is False
    assert out["model"] is None
    assert "No sessions" in out["summary"]


def test_compact_truncates_prompt_and_picks_fields():
    row = {
        "status": "blocked", "agent": "a1", "model": "gpt-4o",
        "threat_type": "prompt_injection", "risk_score": 0.9,
        "gate_decision": "block", "prompt": "x" * 1000, "response": "y" * 1000,
    }
    c = analyst._compact(row)
    assert c["threat"] == "prompt_injection"
    assert c["status"] == "blocked"
    assert len(c["prompt"]) <= analyst._MAX_PROMPT_CHARS
    assert "response" not in c  # responses excluded from the summary view


def test_tally_counts_status_and_threats():
    rows = [
        {"status": "success"},
        {"status": "blocked", "threat_type": "secret_leak"},
        {"status": "blocked", "threat_type": "secret_leak"},
    ]
    t = analyst._tally(rows)
    assert t["total"] == 3
    assert t["by_status"]["blocked"] == 2
    assert t["by_threat"]["secret_leak"] == 2
