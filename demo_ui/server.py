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

from starlette.concurrency import iterate_in_threadpool, run_in_threadpool

from . import lab as lab_mod
from . import mcptox_lab, scenarios

STATIC = Path(__file__).resolve().parent / "static"
rugpull = scenarios.RugpullSession()
LAB = lab_mod.LabSession()


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


async def lab_page(request: Request) -> FileResponse:
    return FileResponse(STATIC / "lab.html")


async def lab_connect(request: Request) -> JSONResponse:
    body = await request.json()
    try:
        return JSONResponse(await LAB.connect(body.get("servers", []), bool(body.get("gateway", True))))
    except Exception as e:
        return JSONResponse({"error": f"{type(e).__name__}: {e}"}, status_code=500)


async def lab_list(request: Request) -> JSONResponse:
    return JSONResponse(await LAB.list_all())


async def lab_call(request: Request) -> JSONResponse:
    b = await request.json()
    return JSONResponse(await LAB.call(b["server"], b["tool"], b.get("args") or {}))


async def lab_disconnect(request: Request) -> JSONResponse:
    await LAB.disconnect()
    return JSONResponse({"ok": True})


async def lab_stream(request: Request) -> EventSourceResponse:
    """Tail the tap log (every JSON-RPC frame) and the gateway log of the current lab session."""
    async def events():
        pos = {"wire": 0, "gw": 0}
        work = None
        while not await request.is_disconnected():
            if work is not LAB.work:
                work, pos = LAB.work, {"wire": 0, "gw": 0}
                yield {"data": json.dumps({"src": "reset"})}
            for src, path in (("wire", LAB.wire), ("gw", LAB.gwlog)):
                if path.exists():
                    lines = path.read_text().splitlines()
                    for line in lines[pos[src]:]:
                        yield {"data": json.dumps({"src": src, "rec": json.loads(line)}, ensure_ascii=False)}
                    pos[src] = len(lines)
            await asyncio.sleep(0.15)
    return EventSourceResponse(events())


async def lab_chat(request: Request) -> EventSourceResponse:
    prompt = request.query_params.get("q", "")
    seed = int(request.query_params.get("seed", "0"))

    async def events():
        try:
            async for ev in lab_mod.chat(LAB, prompt, seed):
                yield {"data": json.dumps(ev, ensure_ascii=False, default=str)}
        except Exception as e:
            yield {"data": json.dumps({"kind": "error", "text": f"{type(e).__name__}: {e}"})}
        yield {"data": json.dumps({"kind": "done"})}
    return EventSourceResponse(events())


async def mx_servers(request: Request) -> JSONResponse:
    return JSONResponse(mcptox_lab.servers_index())


async def mx_case(request: Request) -> JSONResponse:
    return JSONResponse(mcptox_lab.case_info(request.path_params["cid"]))


async def mx_case_gateway(request: Request) -> JSONResponse:
    return JSONResponse(await mcptox_lab.case_gateway(request.path_params["cid"]))


async def mx_case_run(request: Request) -> JSONResponse:
    q = request.query_params
    try:
        return JSONResponse(await run_in_threadpool(mcptox_lab.case_run, request.path_params["cid"],
                                                    q.get("cond", "no_defense"), q.get("think", "on") == "on"))
    except Exception as e:
        return JSONResponse({"error": f"{type(e).__name__}: {e}"}, status_code=503)


async def mx_asr(request: Request) -> JSONResponse:
    return JSONResponse(mcptox_lab.asr_from_file())


async def model_status(request: Request) -> JSONResponse:
    return JSONResponse(await run_in_threadpool(mcptox_lab.model_status))


async def sweep(request: Request) -> EventSourceResponse:
    async def events():
        async for ev in iterate_in_threadpool(mcptox_lab.sweep()):
            yield {"data": json.dumps(ev, ensure_ascii=False)}
    return EventSourceResponse(events())


app = Starlette(routes=[
    Route("/lab", lab_page),
    Route("/api/lab/connect", lab_connect, methods=["POST"]),
    Route("/api/lab/list", lab_list),
    Route("/api/lab/call", lab_call, methods=["POST"]),
    Route("/api/lab/disconnect", lab_disconnect, methods=["POST"]),
    Route("/api/lab/stream", lab_stream),
    Route("/api/lab/chat", lab_chat),
    Route("/api/mcptox/servers", mx_servers),
    Route("/api/mcptox/case/{cid}", mx_case),
    Route("/api/mcptox/case/{cid}/gateway", mx_case_gateway, methods=["POST"]),
    Route("/api/mcptox/case/{cid}/run", mx_case_run, methods=["POST"]),
    Route("/api/mcptox/asr", mx_asr),
    Route("/api/model/status", model_status),
    Route("/api/sweep", sweep),
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
