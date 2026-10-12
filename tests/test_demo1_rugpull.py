"""Demo 1 (L1 rug-pull): clean description is pinned, then silently changes -> blocked with a diff."""

import pytest

from gateway.l1_pins import PinStore

from .conftest import fixture_params, gateway_for

pytestmark = pytest.mark.anyio


async def test_rugpull_is_blocked_with_diff(tmp_path):
    control = tmp_path / "rugpull_mode"
    control.write_text("clean")
    params = fixture_params("rugpull.py", env={"RUGPULL_CONTROL": str(control)})
    pins = tmp_path / "pins.json"

    async with gateway_for("rugpull", params, pins) as (gw, agent, log):
        # 1. First sight: pinned and served.
        names = [t.name for t in (await agent.list_tools()).tools]
        assert names == ["convert_currency"]
        assert any(r["event"] == "l1_pinned" for r in log.records)
        ok = await agent.call_tool("convert_currency", {"amount": 10, "from_currency": "USD", "to_currency": "INR"})
        assert not ok.is_error

        # 2. Server silently changes its description.
        control.write_text("evil")
        assert (await agent.list_tools()).tools == []

        mismatch = [r for r in log.records if r["event"] == "l1_mismatch"]
        assert len(mismatch) == 1
        diff = mismatch[0]["diff"]
        assert "-  \"description\": \"Convert an amount between two currencies using fixed demo rates.\"" in diff
        assert "+" in diff and "aws_secret_access_key" in diff
        removed = [r for r in log.records if r["event"] == "removed"]
        assert removed and removed[-1]["reason"].startswith("L1:")

        # 3. Calls to the blocked tool are refused, not forwarded.
        blocked = await agent.call_tool("convert_currency", {"amount": 1, "from_currency": "USD", "to_currency": "INR"})
        assert blocked.is_error and "Blocked by gateway" in blocked.content[0].text

        # 4. Still blocked on every later listing: no auto-approve.
        assert (await agent.list_tools()).tools == []


async def test_version_bump_needs_explicit_approval(tmp_path):
    control = tmp_path / "rugpull_mode"
    control.write_text("clean")
    params = fixture_params("rugpull.py", env={"RUGPULL_CONTROL": str(control)})
    pins = tmp_path / "pins.json"

    async with gateway_for("rugpull", params, pins) as (gw, agent, log):
        await agent.list_tools()
        control.write_text("bump")
        assert (await agent.list_tools()).tools == []

        PinStore(pins).approve("rugpull", "convert_currency")  # what `gateway pin approve` does
        gw.pins = PinStore(pins)
        assert [t.name for t in (await agent.list_tools()).tools] == ["convert_currency"]


def test_approve_without_pending_change_fails(tmp_path):
    with pytest.raises(KeyError):
        PinStore(tmp_path / "pins.json").approve("rugpull", "convert_currency")
