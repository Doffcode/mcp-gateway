import json

import pytest

from gateway.l3 import metadata_text


def test_metadata_serialization_matches_live_tool_and_reconstructed_record():
    from mcp_types import Tool

    record = {"name": "time", "description": "Return the time",
              "inputSchema": {"type": "object", "properties": {"zone": {"type": "string"}}}}
    sibling = {"name": "convert_time"}
    live = Tool.model_validate(record)
    serialized = metadata_text(live, [live, sibling], use_context=True)
    assert serialized == metadata_text(record, [record, sibling], use_context=True)
    assert serialized.startswith('Related tools: ["convert_time"]\n')
    assert "Related tools:" not in metadata_text(live)


def test_operating_point_controls_additional_flags_after_baseline():
    np = pytest.importorskip("numpy")
    pytest.importorskip("sklearn")
    from eval.l3_data import Example
    from eval.train_l3 import operating_point, results

    def example(label, removed=False):
        return Example("server", label, "category", False, removed, "", "")

    rows = [example(0) for _ in range(20)] + [example(0, True), example(1), example(1)]
    scores = np.array([0.9, 0.7] + [0.0] * 18 + [0.95, 0.85, 0.65])
    threshold = operating_point(rows, scores)
    assert threshold == 0.85
    metrics = results(rows, scores, threshold)
    assert metrics["additional_authentic_flagged"] == 1
    assert metrics["combined_authentic_flagged"] == 2
    assert metrics["additional_poisoned_flagged"] == 1


def test_saved_text_scorer_round_trip(tmp_path):
    joblib = pytest.importorskip("joblib")
    pytest.importorskip("sklearn")
    from eval.train_l3 import text_model
    from gateway.l3 import Scorer

    tools = [
        {"name": "clock", "description": description}
        for description in ["current time", "current time", "convert time", "convert time"]
    ]
    classifier = text_model().fit([metadata_text(tool) for tool in tools], [0, 0, 1, 1])
    (tmp_path / "manifest.json").write_text(json.dumps({"model": "tfidf", "threshold": 0.5, "context": False}))
    joblib.dump(classifier, tmp_path / "classifier.joblib")
    results = Scorer(tmp_path).score_listing(tools)
    assert [row["verdict"] for row in results] == ["below_threshold", "below_threshold", "flagged", "flagged"]
