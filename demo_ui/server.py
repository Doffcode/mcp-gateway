"""Gateway Studio web server: static UI + JSON/SSE endpoints backed by demo_ui.scenarios.

  uv run --extra agent python -m demo_ui.server        # http://127.0.0.1:8765
"""

import asyncio
import json
import os
from pathlib import Path

import uvicorn
from sse_starlette.sse import EventSourceResponse
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from . import scenarios

STATIC = Path(__file__).resolve().parent / "static"
rugpull = scenarios.RugpullSession()


async def index(request: Request) -> FileResponse:
    return FileResponse(STATIC / "index.html")


async def basics(request: Request) -> JSONResponse:
    return JSONResponse(await scenarios.mcp_basics())


async def l2(request: Request) -> JSONResponse:
    return JSONResponse(await scenarios.l2_scene())


async def rug(request: Request) -> JSONResponse:
    action = request.path_params["action"]
    if action == "reset":
        rugpull.reset()
        return JSONResponse(await rugpull.list())
    if action == "cli":
        out = rugpull.cli((await request.json()).get("command", ""))
        return JSONResponse({**out, "after": await rugpull.list()})
    if action == "approve":
        out = rugpull.approve()
        return JSONResponse({**out, "after": await rugpull.list()})
    if action in ("clean", "bump", "evil", "list"):
        return JSONResponse(await rugpull.list(None if action == "list" else action))
    return JSONResponse({"error": f"unknown action {action}"}, status_code=404)


async def check(request: Request) -> JSONResponse:
    body = await request.json()
    return JSONResponse(scenarios.check_description(body.get("name", ""), body.get("description", ""),
                                                    body.get("params") or {}))


async def results(request: Request) -> JSONResponse:
    return JSONResponse(scenarios.load_results())


async def agent(request: Request) -> EventSourceResponse:
    gateway = request.query_params.get("gateway", "off") == "on"
    seed = int(request.query_params.get("seed", "0"))
    queue: asyncio.Queue = asyncio.Queue()
    if request.query_params.get("mode") == "recorded":
        task = asyncio.create_task(scenarios.agent_replay(gateway, seed, queue))
    else:
        task = asyncio.create_task(scenarios.agent_run(gateway, seed, queue, request.query_params.get("prompt")))

    async def events():
        try:
            while True:
                ev = await queue.get()
                yield {"data": json.dumps(ev, ensure_ascii=False, default=str)}
                if ev["kind"] in ("done", "error"):
                    break
        finally:
            task.cancel()

    return EventSourceResponse(events())


app = Starlette(routes=[
    Route("/", index),
    Route("/api/basics", basics),
    Route("/api/l2", l2),
    Route("/api/rugpull/{action}", rug, methods=["GET", "POST"]),
    Route("/api/check", check, methods=["POST"]),
    Route("/api/results", results),
    Route("/api/agent", agent),
    Mount("/static", StaticFiles(directory=STATIC), name="static"),
])


def main() -> None:
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("STUDIO_PORT", "8765")), log_level="warning")


if __name__ == "__main__":
    main()
