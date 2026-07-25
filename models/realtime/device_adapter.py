from __future__ import annotations

from dataclasses import dataclass, field
import json
import logging
import socket
from typing import Any, Protocol
from urllib import request

import serial
from serial.tools import list_ports as serial_list_ports

LOGGER = logging.getLogger(__name__)


T5AI_USB_VID = 0x1A86
T5AI_USB_PID = 0x55D2


def _port_identity(port_info: Any) -> str:
    fields = (
        getattr(port_info, "description", None),
        getattr(port_info, "interface", None),
        getattr(port_info, "product", None),
        getattr(port_info, "hwid", None),
        getattr(port_info, "location", None),
    )
    return " ".join(str(value) for value in fields if value).upper()


def _is_ch342_channel_a(port_info: Any) -> bool:
    identity = _port_identity(port_info)
    return any(
        marker in identity
        for marker in ("SERIAL-A", "CH342-A", "INTERFACE A", "INTERFACE=A", "MI_00")
    ) or identity.endswith((":X.0", ":1.0"))


def _is_ch342_channel_b(port_info: Any) -> bool:
    identity = _port_identity(port_info)
    return any(
        marker in identity
        for marker in ("SERIAL-B", "CH342-B", "INTERFACE B", "INTERFACE=B", "MI_02")
    ) or identity.endswith((":X.2", ":1.2"))


def find_t5ai_ch342_ports() -> list[Any]:
    return [
        port_info
        for port_info in serial_list_ports.comports()
        if getattr(port_info, "vid", None) == T5AI_USB_VID
        and getattr(port_info, "pid", None) == T5AI_USB_PID
    ]


def resolve_serial_port(configured_port: str | None = "auto") -> str:
    port = (configured_port or "auto").strip() or "auto"
    if port.lower() != "auto":
        return port

    candidates = find_t5ai_ch342_ports()
    channel_a = [port_info for port_info in candidates if _is_ch342_channel_a(port_info)]
    if len(channel_a) == 1:
        resolved = str(channel_a[0].device)
        LOGGER.info("Automatically detected T5AI CH342-A command port: %s", resolved)
        return resolved

    if len(channel_a) > 1:
        ports = ", ".join(str(port_info.device) for port_info in channel_a)
        raise serial.SerialException(
            f"Multiple T5AI CH342-A ports were found ({ports}); set EEG_DEVICE_SERIAL_PORT "
            "to the target port explicitly"
        )

    non_log_candidates = [
        port_info for port_info in candidates if not _is_ch342_channel_b(port_info)
    ]
    if len(non_log_candidates) == 1:
        resolved = str(non_log_candidates[0].device)
        LOGGER.info("Automatically detected T5AI command port: %s", resolved)
        return resolved

    if not candidates:
        LOGGER.warning("No CH342 chip found (VID:PID 1A86:55D2); falling back to serial port scan")
        return _fallback_auto_detect()

    ports = ", ".join(str(port_info.device) for port_info in candidates)
    raise serial.SerialException(
        f"T5AI CH342 was found, but channel A is ambiguous ({ports}); set "
        "EEG_DEVICE_SERIAL_PORT to the command port explicitly"
    )


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
class SerialDeviceAdapter:
    port: str
    baudrate: int = 115200
    timeout_s: float = 0.5
    _serial: serial.Serial | None = field(default=None, init=False)
    _resolved_port: str | None = field(default=None, init=False)
    _last_signal_code: int | None = field(default=None, init=False)

    def connect(self) -> None:
        self._connect_once()

    def _connect_once(self) -> bool:
        if self._serial is not None and self._serial.is_open:
            return True

        try:
            resolved_port = resolve_serial_port(self.port)
        except serial.SerialException as exc:
            LOGGER.warning("T5AI serial port resolution failed: %s", exc)
            return False

        connection = serial.Serial()
        connection.port = resolved_port
        connection.baudrate = self.baudrate
        connection.bytesize = serial.EIGHTBITS
        connection.parity = serial.PARITY_NONE
        connection.stopbits = serial.STOPBITS_ONE
        connection.timeout = self.timeout_s
        connection.write_timeout = self.timeout_s
        connection.xonxoff = False
        connection.rtscts = False
        connection.dsrdtr = False

        # Do not request a board reset when opening the onboard USB download port.
        connection.dtr = False
        connection.rts = False

        try:
            connection.open()
        except (OSError, serial.SerialException) as exc:
            connection.close()
            LOGGER.warning("T5AI serial port %s is unavailable: %s", self.port, exc)
            return False

        self._serial = connection
        self._resolved_port = resolved_port
        self._last_signal_code = None
        connection.reset_input_buffer()
        LOGGER.info("T5AI serial output connected: %s at %d 8N1", resolved_port, self.baudrate)
        return True

    def send_action(self, action: str, payload: dict) -> None:
        del action

        signal_code = payload.get("signal_code")
        if signal_code is None:
            return

        code = int(signal_code)
        if code not in (0, 1, 2):
            raise ValueError(f"Unsupported T5AI scene code: {code}")

        if self._serial is not None and self._serial.is_open and code == self._last_signal_code:
            return

        message = f"{code}\n".encode("ascii")
        for _ in range(2):
            if not self._connect_once():
                continue
            assert self._serial is not None
            try:
                self._serial.write(message)
                self._serial.flush()
            except (OSError, serial.SerialException, serial.SerialTimeoutException) as exc:
                LOGGER.warning("T5AI serial write failed; reconnecting: %s", exc)
                self.close()
                continue

            self._last_signal_code = code
            LOGGER.info("T5AI scene command sent: %d", code)
            return

        LOGGER.error("T5AI scene command %d was not sent; port %s is unavailable", code, self.port)

    def close(self) -> None:
        if self._serial is None:
            return
        try:
            self._serial.close()
        finally:
            self._serial = None
            self._resolved_port = None
            self._last_signal_code = None


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
      b"0\n"  -> left
      b"1\n"  -> right
      b"2\n"  -> feet
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
        LOGGER.info(
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
        LOGGER.debug(
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
        LOGGER.info("SerialT5DeviceAdapter disconnected: %s", self.port)

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.close()


def _fallback_auto_detect() -> str:
    """Fallback when CH342 is not found: scan all serial ports."""
    all_ports = list(serial_list_ports.comports())
    if len(all_ports) == 0:
        raise serial.SerialException(
            "No serial port was found at all. Ensure the T5AI board is connected via USB "
            "and check Device Manager for the COM port."
        )
    if len(all_ports) == 1:
        resolved = str(all_ports[0].device)
        LOGGER.info("Fallback auto-detected serial port: %s (%s)", resolved, all_ports[0].description)
        return resolved
    lines = ["EEG_DEVICE_SERIAL_PORT=auto could not determine the correct port."]
    lines.append("Set EEG_DEVICE_SERIAL_PORT explicitly in .env. Available ports:")
    desc = lambda p: p.description or "(no description)"
    lines += [f"  {p.device}  -  {desc(p)}" for p in sorted(all_ports, key=lambda x: x.device)]
    raise serial.SerialException("\n".join(lines))


def build_device_adapter(settings: Any) -> DeviceAdapter:
    if getattr(settings, "mode", "noop") == "serial":
        return SerialDeviceAdapter(
            port=str(getattr(settings, "serial_port")),
            baudrate=int(getattr(settings, "serial_baudrate", 115200)),
            timeout_s=float(getattr(settings, "serial_timeout_s", 0.5)),
        )
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
