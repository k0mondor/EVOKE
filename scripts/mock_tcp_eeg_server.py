from __future__ import annotations

import socket
import struct
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from models.realtime.mock_source import MockEEGSource


def encode_frame(samples, sampling_rate: int) -> bytes:
    flat = [float(value) for row in samples for value in row]
    return struct.pack("<ii", len(samples), sampling_rate) + struct.pack(f"<{len(flat)}f", *flat)


def main() -> None:
    host = "127.0.0.1"
    port = 12345
    source = MockEEGSource()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((host, port))
        server.listen(1)
        print(f"[mock-tcp] listening on {host}:{port}")

        while True:
            conn, addr = server.accept()
            print(f"[mock-tcp] client connected from {addr[0]}:{addr[1]}")
            with conn:
                try:
                    while True:
                        frame = source.next_frame()
                        conn.sendall(encode_frame(frame.samples.tolist(), frame.sampling_rate))
                        time.sleep(source.samples_per_frame / float(source.sampling_rate))
                except (BrokenPipeError, ConnectionResetError):
                    print("[mock-tcp] client disconnected")


if __name__ == "__main__":
    main()
