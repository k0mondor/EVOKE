from __future__ import annotations

from dataclasses import dataclass, field
import json
import socket
from typing import Any, Protocol
from urllib import request


class DeviceAdapter(Protocol):
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
        message = json.dumps({"action": action, "payload": payload}, ensure_ascii=True) + "\n"
        self._socket.sendall(message.encode("utf-8"))

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


def build_device_adapter(settings: Any) -> DeviceAdapter:
    if getattr(settings, "mode", "noop") == "tcp":
        return TCPDeviceAdapter(
            host=getattr(settings, "tcp_host"),
            port=int(getattr(settings, "tcp_port")),
            timeout_s=float(getattr(settings, "timeout_s", 2.0)),
        )
    if getattr(settings, "mode", "noop") == "http":
        return HTTPDeviceAdapter(
            url=getattr(settings, "http_url"),
            timeout_s=float(getattr(settings, "timeout_s", 2.0)),
        )
    return NoopDeviceAdapter()
