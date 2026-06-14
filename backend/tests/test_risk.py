from scoring import risk


def _hist(lt=0, ltb=0, rt=0, rtb=0):
    return {"lifetime_total": lt, "lifetime_blocked": ltb,
            "recent_total": rt, "recent_blocked": rtb}


def test_clean_request_released():
    a = risk.assess(
        adversary_summary={"tests_run": 4, "failed": 0, "partial": 0, "max_severity": 0.0},
        controls_in_scope=4,
        agent_history=_hist(10, 0, 5, 0),
        hold_threshold=0.6,
    )
    assert a.decision == "release"
    assert a.score < 0.6


def test_high_severity_request_held():
    a = risk.assess(
        adversary_summary={"tests_run": 4, "failed": 3, "partial": 1, "max_severity": 0.95},
        controls_in_scope=4,
        agent_history=_hist(10, 5, 5, 3),
        hold_threshold=0.6,
    )
    assert a.decision == "hold"
    assert a.score >= 0.6
    assert a.reasons


def test_score_bounded():
    a = risk.assess(
        adversary_summary={"tests_run": 1, "failed": 1, "partial": 0, "max_severity": 1.0},
        controls_in_scope=1,
        agent_history=_hist(1, 1, 1, 1),
        hold_threshold=0.6,
    )
    assert 0.0 <= a.score <= 1.0
