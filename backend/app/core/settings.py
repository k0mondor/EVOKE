from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(slots=True)
class SourceSettings:
    mode: str = "demo"
    tcp_host: str = "127.0.0.1"
    tcp_port: int = 12345


@dataclass(slots=True)
class DeviceSettings:
    mode: str = "noop"
    device_id: str = "default-device"
    tcp_host: str = "127.0.0.1"
    tcp_port: int = 19001
    http_url: str = "http://127.0.0.1:19002/device-action"
    serial_port: str = "COM3"
    serial_baudrate: int = 115200
    timeout_s: float = 2.0


@dataclass(slots=True)
class AppSettings:
    source: SourceSettings
    device: DeviceSettings


def load_app_settings() -> AppSettings:
    return AppSettings(
        source=SourceSettings(
            mode=os.getenv("EEG_REALTIME_SOURCE", "demo").lower(),
            tcp_host=os.getenv("EEG_TCP_HOST", "127.0.0.1"),
            tcp_port=int(os.getenv("EEG_TCP_PORT", "12345")),
        ),
        device=DeviceSettings(
            mode=os.getenv("EEG_DEVICE_MODE", "noop").lower(),
            device_id=os.getenv("EEG_DEVICE_ID", "default-device"),
            tcp_host=os.getenv("EEG_DEVICE_TCP_HOST", "127.0.0.1"),
            tcp_port=int(os.getenv("EEG_DEVICE_TCP_PORT", "19001")),
            http_url=os.getenv("EEG_DEVICE_HTTP_URL", "http://127.0.0.1:19002/device-action"),
            serial_port=os.getenv("EEG_DEVICE_SERIAL_PORT", "COM3"),
            serial_baudrate=int(os.getenv("EEG_DEVICE_SERIAL_BAUDRATE", "115200")),
            timeout_s=float(os.getenv("EEG_DEVICE_TIMEOUT_S", "2.0")),
        ),
    )
