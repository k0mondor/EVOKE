from __future__ import annotations

from dataclasses import dataclass, field
import json
import logging
import socket
from typing import Any, Protocol
from urllib import request


logger = logging.getLogger(__name__)


class DeviceAdapter(Protocol):
    """Protocol for external device adapters (TCP, HTTP, Serial, etc.)."""

    def connect(self) -> None:
        ...

    def send_action(self, action: str, payload: dict) -> None:
        ...

    def close(self) -> None:
        ...


@dataclass(slots=True)
class NoopDeviceAdapter:
    sent_actions: list[dict] = field(default_factory=list)

    def connect(self) -> None:
        return None

    def send_action(self, action: str, payload: dict) -> None:
        self.sent_actions.append({"action": action, "payload": payload})

    def close(self) -> None:
        return None


@dataclass(slots=True)
class TCPDeviceAdapter:
    host: str
    port: int
    timeout_s: float = 2.0
    _socket: socket.socket | None = field(default=None, init=False)

    def connect(self) -> None:
        if self._socket is not None:
            return
        self._socket = socket.create_connection((self.host, self.port), timeout=self.timeout_s)

    def send_action(self, action: str, payload: dict) -> None:
        if self._socket is None:
            self.connect()
        if self._socket is None:
            raise RuntimeError("TCP device adapter is not connected")
        signal_code = payload.get("signal_code")
        if signal_code is None:
            return
        # TCP device output uses the compact inference code format:
        # 0 -> left, 1 -> right, 2 -> feet
        message = f"{int(signal_code)}\n"
        self._socket.sendall(message.encode("ascii"))

    def close(self) -> None:
        if self._socket is None:
            return
        self._socket.close()
        self._socket = None


@dataclass(slots=True)
class HTTPDeviceAdapter:
    url: str
    timeout_s: float = 2.0

    def connect(self) -> None:
        return None

    def send_action(self, action: str, payload: dict) -> None:
        body = json.dumps({"action": action, "payload": payload}, ensure_ascii=True).encode("utf-8")
        req = request.Request(
            self.url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(req, timeout=self.timeout_s):
            return None

    def close(self) -> None:
        return None


@dataclass(slots=True)
class SerialT5DeviceAdapter:
    """Serial adapter for Tuya T5 development board.

    Sends signal codes as ASCII bytes terminated by newline:
      b"0\\n"  -> left
      b"1\\n"  -> right
      b"2\\n"  -> feet
    """

    port: str = "COM3"
    baudrate: int = 115200
    timeout_s: float = 1.0
    _serial: Any = field(default=None, init=False)

    def connect(self) -> None:
        if self._serial is not None:
            return
        try:
            import serial
        except ImportError:
            raise ImportError(
                "pyserial is required for SerialT5DeviceAdapter. "
                "Install it with: pip install pyserial>=3.5"
            )
        self._serial = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            timeout=self.timeout_s,
            write_timeout=self.timeout_s,
        )
        logger.info(
            "SerialT5DeviceAdapter connected: %s @ %d baud",
            self.port,
            self.baudrate,
        )

    def send_action(self, action: str, payload: dict) -> None:
        signal_code = payload.get("signal_code")
        if signal_code is None:
            return
        if self._serial is None:
            self.connect()
        if self._serial is None:
            raise RuntimeError("Serial device adapter is not connected")

        message = f"{int(signal_code)}\n"
        written = self._serial.write(message.encode("ascii"))
        self._serial.flush()
        logger.debug(
            "SerialT5DeviceAdapter sent: %r (%d bytes to %s)",
            message.strip(),
            written,
            self.port,
        )

    def close(self) -> None:
        if self._serial is None:
            return
        try:
            self._serial.close()
        except Exception:
            pass
        self._serial = None
        logger.info("SerialT5DeviceAdapter disconnected: %s", self.port)

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.close()


def build_device_adapter(settings: Any) -> DeviceAdapter:
    mode = getattr(settings, "mode", "noop")
    if mode == "tcp":
        return TCPDeviceAdapter(
            host=getattr(settings, "tcp_host"),
            port=int(getattr(settings, "tcp_port")),
            timeout_s=float(getattr(settings, "timeout_s", 2.0)),
        )
    if mode == "serial":
        return SerialT5DeviceAdapter(
            port=getattr(settings, "serial_port", "COM3"),
            baudrate=int(getattr(settings, "serial_baudrate", 115200)),
            timeout_s=float(getattr(settings, "timeout_s", 1.0)),
        )
    if mode == "http":
        return HTTPDeviceAdapter(
            url=getattr(settings, "http_url"),
            timeout_s=float(getattr(settings, "timeout_s", 2.0)),
        )
    return NoopDeviceAdapter()
