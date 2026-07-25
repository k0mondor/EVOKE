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
        self._connection_count = 0
        self._connected_at_ms: int | None = None
        self._disconnected_at_ms: int | None = None
        self._bytes_received_total = 0
        self._pending_frame_bytes = 0
        self._frames_received = 0
        self._last_byte_at_ms: int | None = None
        self._last_frame_at_ms: int | None = None
        self._last_header: dict[str, int] | None = None

    def connect(self) -> None:
        if self._socket is not None:
            return
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.config.timeout_s)
        sock.connect((self.config.host, self.config.port))
        sock.settimeout(None)
        self._socket = sock
        self._connection_count += 1
        self._connected_at_ms = int(time.time() * 1000)
        self._disconnected_at_ms = None

    def close(self) -> None:
        if self._socket is None:
            return
        self._socket.close()
        self._socket = None
        self._disconnected_at_ms = int(time.time() * 1000)

    def receive_frame(self) -> EEGFrameBatch:
        if self._socket is None:
            raise RuntimeError("TCP receiver is not connected")

        payload = self._recv_exact(EXPECTED_FRAME_SIZE)
        batch = self.parse_frame(payload, frame_index=self._frame_index, channel_names=self.config.channel_names)
        self._frames_received += 1
        self._last_frame_at_ms = batch.timestamp_ms
        self._last_header = {
            "num_samples": int(batch.samples.shape[0]),
            "sampling_rate": batch.sampling_rate,
        }
        self._pending_frame_bytes = 0
        self._frame_index += 1
        return batch

    def _recv_exact(self, size: int) -> bytes:
        if self._socket is None:
            raise RuntimeError("TCP receiver is not connected")

        buffer = bytearray()
        self._pending_frame_bytes = 0
        while len(buffer) < size:
            chunk = self._socket.recv(size - len(buffer))
            if not chunk:
                raise ConnectionError("TCP connection closed by peer")
            buffer.extend(chunk)
            self._bytes_received_total += len(chunk)
            self._pending_frame_bytes = len(buffer)
            self._last_byte_at_ms = int(time.time() * 1000)
        return bytes(buffer)

    def diagnostics_snapshot(self) -> dict[str, object]:
        if self._socket is None:
            stream_state = "disconnected"
        elif self._pending_frame_bytes > 0:
            stream_state = "partial_frame"
        elif self._frames_received > 0:
            stream_state = "streaming"
        else:
            stream_state = "waiting_for_bytes"

        return {
            "stream_state": stream_state,
            "tcp_connected": self._socket is not None,
            "tcp_connection_count": self._connection_count,
            "tcp_connected_at_ms": self._connected_at_ms,
            "tcp_disconnected_at_ms": self._disconnected_at_ms,
            "tcp_bytes_received": self._bytes_received_total,
            "tcp_pending_frame_bytes": self._pending_frame_bytes,
            "tcp_expected_frame_bytes": EXPECTED_FRAME_SIZE,
            "tcp_frames_received": self._frames_received,
            "tcp_last_byte_at_ms": self._last_byte_at_ms,
            "tcp_last_frame_at_ms": self._last_frame_at_ms,
            "tcp_last_header": self._last_header,
        }

    @staticmethod
    def parse_frame(
        payload: bytes,
        *,
        frame_index: int | None = None,
        channel_names: tuple[str, ...] | None = None,
    ) -> EEGFrameBatch:
        if len(payload) != EXPECTED_FRAME_SIZE:
            raise ValueError(
                f"Expected {EXPECTED_FRAME_SIZE} bytes per EEG frame, received {len(payload)}."
            )
        num_samples, sampling_rate = struct.unpack("<ii", payload[:HEADER_BYTES])
        if num_samples != SAMPLES_PER_FRAME:
            raise ValueError(
                f"Expected {SAMPLES_PER_FRAME} samples per EEG frame, received {num_samples}."
            )
        if sampling_rate <= 0:
            raise ValueError(f"Sampling rate must be positive, received {sampling_rate}.")
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
