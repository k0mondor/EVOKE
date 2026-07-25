from __future__ import annotations

import os
import sys
from pathlib import Path

import uvicorn
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

load_dotenv(REPO_ROOT / ".env")


def main() -> None:
    host = os.getenv("EEG_BACKEND_HOST", "127.0.0.1")
    port = int(os.getenv("EEG_BACKEND_PORT", "8000"))
    uvicorn.run(
        "backend.app.main:app",
        host=host,
        port=port,
        reload=False,
        factory=False,
    )


if __name__ == "__main__":
    main()
