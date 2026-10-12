import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from mcp import Client
from mcp.client.stdio import StdioServerParameters

from gateway.l1_pins import PinStore
from gateway.logjson import JsonLog
from gateway.proxy import Gateway

ROOT = Path(__file__).resolve().parents[1]
SERVERS = ROOT / "fixtures" / "servers"


def fixture_params(script: str, *args: str, env: dict | None = None) -> StdioServerParameters:
    full_env = {**os.environ, **(env or {})}
    return StdioServerParameters(command=sys.executable, args=[str(SERVERS / script), *args], env=full_env)


@asynccontextmanager
async def gateway_for(name: str, params: StdioServerParameters, pin_path: Path, k: int = 2, l2=None):
    """Upstream over real stdio; agent side connects to the gateway in-process."""
    log = JsonLog(None, stream=None)
    async with Client(params, cache=None) as upstream:
        gw = Gateway(name, upstream, PinStore(pin_path), log, k, **({"l2": l2} if l2 else {}))
        async with Client(gw.build_server(), cache=None) as agent:
            yield gw, agent, log


@pytest.fixture
def anyio_backend():
    return "asyncio"
