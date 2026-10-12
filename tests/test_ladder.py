"""One test per row of the decision ladder in CLAUDE.md."""

from gateway.l1_pins import L1Result
from gateway.ladder import decide

NEW, MATCH, MISMATCH = L1Result("new", None, "h"), L1Result("match", "h", "h"), L1Result("mismatch", "a", "b")


def test_l2_flags_one_tool_removes_only_that_tool():
    d = decide("s", ["a", "b"], {"a": NEW, "b": NEW}, {"a": ["flag"], "b": []}, k=2)
    assert not d.quarantined and d.allowed == ["b"] and d.removed["a"].startswith("L2:")


def test_l2_flags_k_tools_quarantines_server():
    d = decide("s", ["a", "b", "c"], {n: NEW for n in "abc"}, {"a": ["f"], "b": ["f"], "c": []}, k=2)
    assert d.quarantined and d.allowed == [] and set(d.removed) == {"a", "b", "c"}
    assert "K=2" in d.quarantine_reason


def test_l1_mismatch_l2_clean_removes_tool_until_repin():
    d = decide("s", ["a", "b"], {"a": MISMATCH, "b": MATCH}, {}, k=2)
    assert not d.quarantined and d.allowed == ["b"]
    assert d.removed["a"].startswith("L1:") and "gateway pin approve s a" in d.removed["a"]


def test_l1_mismatch_and_l2_flag_quarantines_server():
    d = decide("s", ["a", "b"], {"a": MISMATCH, "b": MATCH}, {"a": ["f"]}, k=2)
    assert d.quarantined and d.quarantine_reason.startswith("L1+L2:")


def test_all_clean_serves_everything():
    d = decide("s", ["a", "b"], {"a": MATCH, "b": NEW}, {}, k=2)
    assert d.allowed == ["a", "b"] and not d.removed
