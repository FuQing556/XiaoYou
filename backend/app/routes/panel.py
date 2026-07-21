from fastapi import APIRouter

from ..brain import brain

router = APIRouter(prefix="/api/panel", tags=["panel"])


@router.get("/state")
async def get_state():
    return brain.get_state()


@router.post("/mode/{mode}")
async def set_mode(mode: str):
    await brain.set_mode(mode)
    return {"ok": True, "mode": mode}


@router.get("/memory/recent")
async def get_recent_memory(limit: int = 20):
    events = brain.memory.recent_events(limit)
    return {"events": events}


@router.get("/memory/search")
async def search_memory(q: str, limit: int = 10):
    results = brain.memory.search_episodic(q, limit)
    return {"results": results}
