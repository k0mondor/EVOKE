#!/usr/bin/env python
"""
Serial T5 Device Adapter — Standalone Verification Script

Tests serial communication with the Tuya T5 development board
independently of the realtime EEG pipeline.

Usage:
    # List available COM ports first
    py scripts/test_t5_serial.py --list

    # Send a specific signal code (0=left, 1=right, 2=feet)
    py scripts/test_t5_serial.py --port COM3 --baud 115200 --code 0

    # Interactive mode: send codes by typing 0/1/2
    py scripts/test_t5_serial.py --port COM3 --baud 115200 --interactive
"""

from __future__ import annotations

import argparse
import logging
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("test_t5_serial")


def list_ports() -> None:
    """List available serial ports."""
    try:
        import serial.tools.list_ports
    except ImportError:
        logger.error("pyserial not installed. Run: pip install pyserial>=3.5")
        sys.exit(1)

    ports = serial.tools.list_ports.comports()
    if not ports:
        logger.info("No serial ports found.")
        return

    logger.info("Available serial ports:")
    for port in sorted(ports, key=lambda p: p.device):
        logger.info("  %s  —  %s", port.device, port.description or "(no description)")


def send_code(port: str, baud: int, code: int, count: int = 1) -> None:
    """Open serial port and send signal code(s)."""
    try:
        import serial
    except ImportError:
        logger.error("pyserial not installed. Run: pip install pyserial>=3.5")
        sys.exit(1)

    LABELS = {0: "left", 1: "right", 2: "feet"}
    if code not in LABELS:
        logger.error("Invalid code: %d. Use 0 (left), 1 (right), or 2 (feet).", code)
        sys.exit(1)

    message = f"{code}\n"
    label = LABELS[code]

    logger.info("Opening %s @ %d baud ...", port, baud)
    with serial.Serial(port=port, baudrate=baud, timeout=1, write_timeout=1) as ser:
        logger.info("Connected: %s", ser.name)
        for i in range(count):
            written = ser.write(message.encode("ascii"))
            ser.flush()
            logger.info(
                "[%d/%d] Sent code %d (%s): %r (%d bytes)",
                i + 1,
                count,
                code,
                label,
                message.strip(),
                written,
            )
            time.sleep(0.5)
    logger.info("Closed %s", port)


def interactive_mode(port: str, baud: int) -> None:
    """Interactive mode: type 0/1/2 to send codes, q to quit."""
    try:
        import serial
    except ImportError:
        logger.error("pyserial not installed. Run: pip install pyserial>=3.5")
        sys.exit(1)

    LABELS = {0: "left", 1: "right", 2: "feet"}
    REVERSE = {v: k for k, v in LABELS.items()}

    logger.info("Opening %s @ %d baud (interactive mode) ...", port, baud)
    with serial.Serial(port=port, baudrate=baud, timeout=1, write_timeout=1) as ser:
        logger.info("Connected: %s", ser.name)
        print()
        print("Interactive serial test — type a command and press Enter:")
        print("  0  -> left")
        print("  1  -> right")
        print("  2  -> feet")
        print("  q  -> quit")
        print()

        while True:
            try:
                line = input(">> ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print()
                break

            if line in ("q", "quit", "exit"):
                break

            if line in ("0", "1", "2"):
                code = int(line)
                label = LABELS[code]
                message = f"{code}\n"
                written = ser.write(message.encode("ascii"))
                ser.flush()
                logger.info("Sent code %d (%s): %r (%d bytes)", code, label, message.strip(), written)
            elif line in ("left", "right", "feet"):
                code = REVERSE[line]
                message = f"{code}\n"
                written = ser.write(message.encode("ascii"))
                ser.flush()
                logger.info("Sent code %d (%s): %r (%d bytes)", code, line, message.strip(), written)
            else:
                print("Unknown command. Enter 0, 1, 2, or q.")

    logger.info("Closed %s", port)


def main() -> None:
    parser = argparse.ArgumentParser(description="Tuya T5 Serial Test Tool")
    parser.add_argument("--list", action="store_true", help="List available serial ports")
    parser.add_argument("--port", default="COM3", help="Serial port (default: COM3)")
    parser.add_argument("--baud", type=int, default=115200, help="Baud rate (default: 115200)")
    parser.add_argument("--code", type=int, choices=[0, 1, 2], help="Signal code to send: 0=left, 1=right, 2=feet")
    parser.add_argument("--count", type=int, default=1, help="Number of times to send the code (default: 1)")
    parser.add_argument("--interactive", action="store_true", help="Interactive mode")

    args = parser.parse_args()

    if args.list:
        list_ports()
        return

    if args.interactive:
        interactive_mode(args.port, args.baud)
    elif args.code is not None:
        send_code(args.port, args.baud, args.code, args.count)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
