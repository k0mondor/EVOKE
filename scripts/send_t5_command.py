from __future__ import annotations

import argparse
import sys
from pathlib import Path

import serial


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from models.realtime.device_adapter import resolve_serial_port


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Send one scene code to T5AI through its onboard USB download COM port."
    )
    parser.add_argument("scene", choices=("0", "1", "2"), help="0=left, 1=right, 2=feet")
    parser.add_argument(
        "--port",
        default="auto",
        help="T5AI CH342-A port (default: auto-detect by USB identity)",
    )
    parser.add_argument("--baudrate", type=int, default=115200)
    parser.add_argument("--timeout", type=float, default=1.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    resolved_port = resolve_serial_port(args.port)
    connection = serial.Serial()
    connection.port = resolved_port
    connection.baudrate = args.baudrate
    connection.bytesize = serial.EIGHTBITS
    connection.parity = serial.PARITY_NONE
    connection.stopbits = serial.STOPBITS_ONE
    connection.timeout = args.timeout
    connection.write_timeout = args.timeout
    connection.xonxoff = False
    connection.rtscts = False
    connection.dsrdtr = False
    connection.dtr = False
    connection.rts = False

    try:
        connection.open()
        connection.reset_input_buffer()
        connection.write(f"{args.scene}\n".encode("ascii"))
        connection.flush()
        reply = connection.readline().decode("ascii", errors="replace").strip()
    finally:
        connection.close()

    if reply:
        print(f"T5AI reply from {resolved_port}: {reply}")
    else:
        print(f"Command sent through {resolved_port}, but no acknowledgement was received.")


if __name__ == "__main__":
    main()
