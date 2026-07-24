from fastapi import FastAPI

from .services.realtime_session import RealtimeSession


def create_app() -> FastAPI:
    app = FastAPI(title="EEG IoT Control Backend")
    app.state.realtime_session = RealtimeSession()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
