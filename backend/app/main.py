"""小悠 v2 FastAPI 应用"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from .brain import brain
from .config import PORT


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[Main] starting brain...")
    await brain.start()
    yield
    print("[Main] stopping brain...")
    await brain.stop()


app = FastAPI(title="小悠 v2", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 导入路由 ──
from .routes.chat import router as chat_router
from .routes.panel import router as panel_router

app.include_router(chat_router)
app.include_router(panel_router)


# ── 音频端点 ──
@app.get("/audio/{audio_id}")
async def serve_audio(audio_id: str):
    data = brain.get_audio(audio_id)
    if data:
        return Response(content=data, media_type="audio/mpeg")
    return Response(status_code=404)


@app.get("/health")
async def health():
    return {"status": "ok", "mode": brain._mode}
