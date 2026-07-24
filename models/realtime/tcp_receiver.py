from __future__ import annotations

from dataclasses import dataclass
import socket
import struct
import time

import numpy as np

from models.realtime.types import EEGFrameBatch

HEADER_BYTES = 8
NUM_CHANNELS = 8
SAMPLES_PER_FRAME = 10
EXPECTED_FRAME_SIZE = HEADER_BYTES + SAMPLES_PER_FRAME * NUM_CHANNELS * 4


@dataclass(slots=True)
class TCPReceiverConfig:
    host: str
    port: int
    timeout_s: float = 10.0
    channel_names: tuple[str, ...] = tuple(f"CH{i}" for i in range(1, NUM_CHANNELS + 1))


class TCPReceiver:
    def __init__(self, config: TCPReceiverConfig) -> None:
        self.config = config
        self._socket: socket.socket | None = None
        self._frame_index = 0

    def connect(self) -> None:
        if self._socket is not None:
            return
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.config.timeout_s)
        sock.connect((self.config.host, self.config.port))
        sock.settimeout(None)
        self._socket = sock

    def close(self) -> None:
        if self._socket is None:
            return
        self._socket.close()
        self._socket = None

    def receive_frame(self) -> EEGFrameBatch:
        if self._socket is None:
            raise RuntimeError("TCP receiver is not connected")

        payload = self._recv_exact(EXPECTED_FRAME_SIZE)
        batch = self.parse_frame(payload, frame_index=self._frame_index, channel_names=self.config.channel_names)
        self._frame_index += 1
        return batch

    def _recv_exact(self, size: int) -> bytes:
        if self._socket is None:
            raise RuntimeError("TCP receiver is not connected")

        buffer = b""
        while len(buffer) < size:
            chunk = self._socket.recv(size - len(buffer))
            if not chunk:
                raise ConnectionError("TCP connection closed by peer")
            buffer += chunk
        return buffer

    @staticmethod
    def parse_frame(
        payload: bytes,
        *,
        frame_index: int | None = None,
        channel_names: tuple[str, ...] | None = None,
    ) -> EEGFrameBatch:
        num_samples, sampling_rate = struct.unpack("<ii", payload[:HEADER_BYTES])
        raw = struct.unpack(f"<{num_samples * NUM_CHANNELS}f", payload[HEADER_BYTES:])
        samples = np.asarray(raw, dtype=np.float32).reshape(num_samples, NUM_CHANNELS)
        return EEGFrameBatch(
            sampling_rate=int(sampling_rate),
            channel_names=channel_names or tuple(f"CH{i}" for i in range(1, NUM_CHANNELS + 1)),
            samples=samples,
            timestamp_ms=int(time.time() * 1000),
            frame_index=frame_index,
            source="tcp",
        )
