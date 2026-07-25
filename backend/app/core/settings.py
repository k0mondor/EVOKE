from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv


REPO_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(REPO_ROOT / ".env")


@dataclass(slots=True)
class SourceSettings:
    mode: str = "demo"
    tcp_host: str = "127.0.0.1"
    tcp_port: int = 12345


@dataclass(slots=True)
class DeviceSettings:
    mode: str = "serial"
    device_id: str = "default-device"
    serial_port: str = "auto"
    serial_baudrate: int = 115200
    serial_timeout_s: float = 0.5
    tcp_host: str = "127.0.0.1"
    tcp_port: int = 19001
    http_url: str = "http://127.0.0.1:19002/device-action"
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
            mode=os.getenv("EEG_DEVICE_MODE", "serial").lower(),
            device_id=os.getenv("EEG_DEVICE_ID", "default-device"),
            serial_port=os.getenv("EEG_DEVICE_SERIAL_PORT", "auto"),
            serial_baudrate=int(os.getenv("EEG_DEVICE_SERIAL_BAUDRATE", "115200")),
            serial_timeout_s=float(os.getenv("EEG_DEVICE_SERIAL_TIMEOUT_S", "0.5")),
            tcp_host=os.getenv("EEG_DEVICE_TCP_HOST", "127.0.0.1"),
            tcp_port=int(os.getenv("EEG_DEVICE_TCP_PORT", "19001")),
            http_url=os.getenv("EEG_DEVICE_HTTP_URL", "http://127.0.0.1:19002/device-action"),
            timeout_s=float(os.getenv("EEG_DEVICE_TIMEOUT_S", "2.0")),
        ),
    )
