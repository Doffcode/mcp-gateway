import json

from gateway import l4
from demo_ui import lab as lab_mod


def make_review(score=0.2, categories=()):
    return l4.Review("time", "Return the current time.", "{}", (), categories, score, 0.54)


def test_suggested_for_disagreement_and_near_threshold():
    assert make_review(0.79).suggested()
    assert make_review(0.2, ("network",)).suggested()
    assert make_review(0.55, ("network",)).suggested()
    assert not make_review().suggested()
    assert not make_review(None, ("network",)).suggested()


def test_model_evidence_has_bounded_fields():
    item = l4.Review("test", "x" * 5000, "y" * 6000, ("z" * 200,) * 20, (), None, None)
    evidence = json.loads(item.evidence())
    assert evidence["truncated"]
    assert len(evidence["description"]) == 2400
    assert len(evidence["input_schema_json"]) == 3000
    assert len(evidence["sibling_names"]) == 12


async def test_review_returns_validated_finding_or_unavailable(monkeypatch):
    async def ask(item):
        return json.dumps({"verdict": "low_risk", "evidence_field": "description", "reason": "Matches the tool."})

    monkeypatch.setattr(l4, "ask_ollama", ask)
    finding = await l4.review_metadata(make_review())
    assert finding["verdict"] == "low_risk" and finding["model"] == l4.MODEL

    async def invalid(item):
        return json.dumps({"verdict": "allow", "tool_call": "time"})

    monkeypatch.setattr(l4, "ask_ollama", invalid)
    assert (await l4.review_metadata(make_review()))["verdict"] == "unavailable"


async def test_lab_uses_real_listing_and_keeps_decision(monkeypatch):
    async def review(item):
        assert item.name == "get_weather"
        assert item.l2_categories
        return {"verdict": "low_risk"}

    monkeypatch.setattr(lab_mod, "review_metadata", review)
    lab = lab_mod.LabSession()
    try:
        result = await lab.connect([{"kind": "weather"}], gateway=True)
        weather = result["servers"]["weather"]
        review_id = next(tool["l4"]["id"] for tool in weather["upstream"] if tool["name"] == "get_weather")
        assert (await lab.review_tool(review_id))["verdict"] == "low_risk"
        assert (await lab.call("weather", "get_weather", {"city": "Paris"}))["is_error"]
        assert weather["served"] == ["get_forecast"]
    finally:
        await lab.disconnect()
    assert review_id not in lab.reviews
