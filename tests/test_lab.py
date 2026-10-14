"""Gateway Lab: real processes, real frames, and the benchmark recomputed by the same code as results/results.md."""

import random
import shutil

import pytest

from demo_ui import mcptox_lab
from demo_ui.lab import LabSession

pytestmark = pytest.mark.skipif(not mcptox_lab.RAW.exists(), reason="MCPTox data not fetched (scripts/setup.sh)")


def test_replay_server_serves_exactly_the_released_tools():
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(mcptox_lab.ROOT / "fixtures" / "servers")))
    from mcptox_server import tools_for

    for s, d in mcptox_lab.data().items():
        assert [t["name"] for t in tools_for(s, None)] == [t["name"] for t in d["authentic_tools"]]
        assert len(tools_for(s, None)) == len(d["tool_names"])
    case = mcptox_lab.data()["Slack"]["cases"][0]
    assert tools_for("Slack", case["id"])[-1] == case["poisoned_tool"]


async def test_tap_records_both_hops_and_gateway_filters():
    lab = LabSession()
    try:
        r = await lab.connect([{"kind": "weather"}], gateway=True)
    finally:
        await lab.disconnect()
    w = r["servers"]["weather"]
    assert w["served"] == ["get_forecast"] and "get_weather" in w["removed"]
    assert [t["name"] for t in w["upstream"]] == ["get_weather", "get_forecast"]  # what the real server sent
    frames = [x for x in lab._read(lab.wire) if "proc" not in x]
    hops = {(f["hop"], f["dir"]) for f in frames}
    assert {("agent→gw[weather]", "req"), ("agent→gw[weather]", "res"), ("gw→weather", "req"), ("gw→weather", "res")} <= hops
    assert any(isinstance(f["msg"], dict) and f["msg"].get("method") == "tools/list" for f in frames)
    assert len(lab.procs()) == 2


async def test_real_proxy_agrees_with_benchmark_code_path():
    held = [c for s in mcptox_lab.split()["heldout_servers"] for c in mcptox_lab.data()[s]["cases"]]
    for c in random.Random(20261012).sample(held, 12):
        g = await mcptox_lab.case_gateway(c["id"])
        assert g["agree"], c["id"]


def test_sweep_reproduces_results_md():
    done = list(mcptox_lab.sweep())[-1]
    assert (done["detection"]["hits"], done["detection"]["n"]) == (157, 498)
    assert (done["fpr"]["removed"], done["fpr"]["n"]) == (24, 353)
    assert done["quarantined"] == ["Commander"]


@pytest.mark.skipif(shutil.which("uvx") is None, reason="uvx not installed")
async def test_official_servers_pass_through_unflagged():
    lab = LabSession()
    try:
        r = await lab.connect([{"kind": "time"}], gateway=True)
    except Exception as e:  # offline and not cached
        pytest.skip(f"official server unavailable: {e}")
    finally:
        await lab.disconnect()
    t = r["servers"]["time"]
    assert t["removed"] == {} and len(t["served"]) == len(t["upstream"]) >= 1
