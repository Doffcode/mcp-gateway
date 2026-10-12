"""Demo 2 (L2 capability mismatch): get_weather(city) whose description implies filesystem access
is removed with a reason; the other tools keep working."""

import pytest

from gateway.config import ROOT
from gateway.l2_capability import L2Analyzer

from .conftest import fixture_params, gateway_for

pytestmark = pytest.mark.anyio
L2 = L2Analyzer.from_dir(ROOT / "taxonomy")


async def test_poisoned_weather_tool_removed_others_served(tmp_path):
    params = fixture_params("weather.py", "--variant", "poisoned", env={"GATEWAY_VAR": str(tmp_path)})
    async with gateway_for("weather", params, tmp_path / "pins.json", l2=L2) as (gw, agent, log):
        names = [t.name for t in (await agent.list_tools()).tools]
        assert names == ["get_forecast"]

        removed = [r for r in log.records if r["event"] == "removed"]
        assert [r["tool"] for r in removed] == ["get_weather"]
        reason = removed[0]["reason"]
        assert reason.startswith("L2:") and "filesystem" in reason and "params: city" in reason
        flag = [r for r in log.records if r["event"] == "l2_flag"][0]["flags"][0]
        assert flag["category"] == "filesystem" and flag["target_source"]

        ok = await agent.call_tool("get_forecast", {"city": "Paris", "days": 2})
        assert not ok.is_error and "Paris" in ok.content[0].text
        blocked = await agent.call_tool("get_weather", {"city": "Paris"})
        assert blocked.is_error


async def test_clean_weather_fully_served(tmp_path):
    params = fixture_params("weather.py", "--variant", "clean", env={"GATEWAY_VAR": str(tmp_path)})
    async with gateway_for("weather", params, tmp_path / "pins.json", l2=L2) as (gw, agent, log):
        assert sorted(t.name for t in (await agent.list_tools()).tools) == ["get_forecast", "get_weather"]


async def test_benign_trigger_word_tools_not_flagged(tmp_path):
    async with gateway_for("benign", fixture_params("benign.py"), tmp_path / "pins.json", l2=L2) as (gw, agent, log):
        names = sorted(t.name for t in (await agent.list_tools()).tools)
        assert names == ["fetch_url", "read_config", "run_tests", "send_email"]


async def test_rugpull_to_flagged_version_quarantines_server(tmp_path):
    control = tmp_path / "rugpull_mode"
    control.write_text("clean")
    params = fixture_params("rugpull.py", env={"RUGPULL_CONTROL": str(control)})
    async with gateway_for("rugpull", params, tmp_path / "pins.json", l2=L2) as (gw, agent, log):
        assert len((await agent.list_tools()).tools) == 1
        control.write_text("evil")
        assert (await agent.list_tools()).tools == []
        q = [r for r in log.records if r["event"] == "quarantine"]
        assert q and q[0]["reason"].startswith("L1+L2:")
