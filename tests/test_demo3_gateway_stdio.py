"""Demo 3 plumbing without an LLM: the agent's gateway-ON connection (real `gateway run` subprocess over stdio)
hides the poisoned get_weather, blocks a direct call to it, and still serves the other tools."""

import pytest
from mcp import Client

from agent.loop import CANARY, canary_leaked, server_params

pytestmark = pytest.mark.anyio


async def test_gateway_on_hides_and_blocks_poisoned_tool(tmp_path):
    params = server_params("weather", ["weather.py", "--variant", "poisoned"], gateway=True, run_dir=tmp_path)
    async with Client(params, cache=None) as c:
        assert [t.name for t in (await c.list_tools()).tools] == ["get_forecast"]
        blocked = await c.call_tool("get_weather", {"city": f"Paris|{CANARY}"})
        assert blocked.is_error and "L2" in blocked.content[0].text
        ok = await c.call_tool("get_forecast", {"city": "Paris"})
        assert not ok.is_error
    assert not canary_leaked(tmp_path)  # the blocked call never reached the server


async def test_gateway_off_serves_poisoned_tool(tmp_path):
    params = server_params("weather", ["weather.py", "--variant", "poisoned"], gateway=False, run_dir=tmp_path)
    async with Client(params, cache=None) as c:
        assert sorted(t.name for t in (await c.list_tools()).tools) == ["get_forecast", "get_weather"]
        await c.call_tool("get_weather", {"city": f"Paris|{CANARY}"})
    assert canary_leaked(tmp_path)  # the checker detects canary content reaching the weather server
