from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from .api import ws_router
from .services.realtime_hub import RealtimeHub


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.realtime_hub = RealtimeHub()
    await app.state.realtime_hub.start()
    yield
    await app.state.realtime_hub.stop()


def create_app() -> FastAPI:
    app = FastAPI(title="EEG IoT Control Backend", lifespan=lifespan)
    app.include_router(ws_router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/realtime/status")
    def realtime_status() -> dict[str, object]:
        return app.state.realtime_hub.status_snapshot()

    return app


app = create_app()
