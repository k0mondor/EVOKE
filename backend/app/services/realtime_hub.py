from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass, field
import logging
import time

from fastapi import WebSocket

from backend.app.core.settings import AppSettings, load_app_settings
from backend.app.schemas.messages import (
    DeviceControlPayload,
    EEGFramePayload,
    Envelope,
    MIPredictionPayload,
    SignalQualityPayload,
    TopomapSnapshotPayload,
)
from backend.app.services.realtime_session import RealtimeSession, RealtimeSessionOutput
from models.realtime.device_adapter import DeviceAdapter, build_device_adapter
from models.realtime.mock_source import MockEEGSource
from models.realtime.signals import signal_code_for_label
from models.realtime.tcp_receiver import EXPECTED_FRAME_SIZE, TCPReceiver, TCPReceiverConfig


logger = logging.getLogger(__name__)
CLIENT_QUEUE_MAXSIZE = 64


@dataclass(slots=True)
class RealtimeHub:
    settings: AppSettings = field(default_factory=load_app_settings)
    session: RealtimeSession = field(default_factory=RealtimeSession)
    device_adapter: DeviceAdapter | None = field(default=None)
    _clients: set[WebSocket] = field(default_factory=set, init=False)
    _client_queues: dict[WebSocket, asyncio.Queue[dict]] = field(default_factory=dict, init=False)
    _client_sender_tasks: dict[WebSocket, asyncio.Task] = field(default_factory=dict, init=False)
    _source_task: asyncio.Task | None = field(default=None, init=False)
    _source_monitor_task: asyncio.Task | None = field(default=None, init=False)
    _tcp_receiver: TCPReceiver | None = field(default=None, init=False)
    _control_lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False)
    _status: dict[str, object] = field(default_factory=dict, init=False)
    _acquisition_state: str = field(default="idle", init=False)
    _inference_state: str = field(default="idle", init=False)
    _collection_windows_target: int = field(default=5, init=False)
    _collection_windows_seen: int = field(default=0, init=False)
    _inference_windows_target: int = field(default=5, init=False)
    _inference_probabilities: list[dict[str, float]] = field(default_factory=list, init=False)
    _inference_final_result: dict[str, object] | None = field(default=None, init=False)
    _source_error: str | None = field(default=None, init=False)

    async def start(self) -> None:
        if self.device_adapter is None:
            self.device_adapter = build_device_adapter(self.settings.device)
        self._status = {
            "source_mode": self.settings.source.mode,
            "device_mode": self.settings.device.mode,
            "client_count": 0,
            "last_frame_timestamp_ms": None,
            "last_prediction_label": None,
            "last_prediction_confidence": None,
        }
    async def stop(self) -> None:
        await self.stop_acquisition()
        for client in tuple(self._clients):
            self.disconnect(client)
        if self.device_adapter is not None:
            self.device_adapter.close()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._clients.add(websocket)
        queue: asyncio.Queue[dict] = asyncio.Queue(maxsize=CLIENT_QUEUE_MAXSIZE)
        self._client_queues[websocket] = queue
        self._client_sender_tasks[websocket] = asyncio.create_task(
            self._run_client_sender(websocket, queue)
        )
        self._status["client_count"] = len(self._clients)
        queue.put_nowait(self._runtime_state_envelope())

    def disconnect(self, websocket: WebSocket) -> None:
        self._clients.discard(websocket)
        self._client_queues.pop(websocket, None)
        sender_task = self._client_sender_tasks.pop(websocket, None)
        if sender_task is not None and sender_task is not asyncio.current_task():
            sender_task.cancel()
        self._status["client_count"] = len(self._clients)

    def status_snapshot(self) -> dict[str, object]:
        return {**self._status, **self._runtime_state_payload()}

    async def handle_command(self, websocket: WebSocket, message: object) -> None:
        if not isinstance(message, dict):
            await self._send_command_ack(websocket, "unknown", False, "Command must be a JSON object.")
            return

        command = str(message.get("command", "")).strip().lower()
        async with self._control_lock:
            if command == "get_status":
                self._send_to_client(websocket, self._runtime_state_envelope())
                await self._send_command_ack(websocket, command, True, "Runtime state sent.")
                return

            if command == "start_acquisition":
                try:
                    collection_window_count = max(
                        1, min(50, int(message.get("collection_window_count", 5)))
                    )
                    inference_window_count = max(
                        1, min(50, int(message.get("inference_window_count", 5)))
                    )
                except (TypeError, ValueError):
                    await self._send_command_ack(
                        websocket,
                        command,
                        False,
                        "collection_window_count and inference_window_count must be numeric.",
                    )
                    return

                started = await self.start_acquisition(
                    collection_window_count=collection_window_count,
                    inference_window_count=inference_window_count,
                )
                await self._send_command_ack(
                    websocket,
                    command,
                    True,
                    "Acquisition started." if started else "Acquisition is already active.",
                )
                return

            if command == "stop_acquisition":
                await self.stop_acquisition()
                await self._send_command_ack(websocket, command, True, "Acquisition stopped.")
                return

            await self._send_command_ack(websocket, command or "unknown", False, "Unknown command.")

    async def start_acquisition(
        self,
        *,
        collection_window_count: int = 5,
        inference_window_count: int = 5,
    ) -> bool:
        if self._source_task is not None and not self._source_task.done():
            return False

        self.session = RealtimeSession()
        self._source_error = None
        self._reset_inference_state(
            collection_window_count=collection_window_count,
            inference_window_count=inference_window_count,
        )
        if self.settings.source.mode == "tcp":
            self._acquisition_state = "connecting"
            self._source_task = asyncio.create_task(self._run_tcp_loop())
            self._source_monitor_task = asyncio.create_task(self._run_source_monitor())
        else:
            self._acquisition_state = "running"
            self._source_task = asyncio.create_task(self._run_demo_loop())
        await self._broadcast_runtime_state()
        return True

    async def stop_acquisition(self) -> None:
        monitor_task = self._source_monitor_task
        self._source_monitor_task = None
        if monitor_task is not None and not monitor_task.done():
            monitor_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await monitor_task

        task = self._source_task
        self._source_task = None
        if task is not None and not task.done():
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

        if self._inference_state in {"collecting", "inferring"}:
            self._inference_state = "cancelled"
        self._acquisition_state = "stopped"
        await self._broadcast_runtime_state()

    async def ingest_frame(self, frame) -> None:
        output = self.session.push_frame(frame)
        self._status["last_frame_timestamp_ms"] = output.eeg_frame.timestamp_ms
        if output.events:
            event = output.events[-1]
            self._status["last_prediction_label"] = event.prediction.label
            self._status["last_prediction_confidence"] = event.prediction.confidence
        await self._publish_output(output)
        await self._consume_inference_events(output.events)

    async def _publish_output(self, output: RealtimeSessionOutput) -> None:
        eeg_message = Envelope(
            type="eeg_frame",
            timestamp_ms=output.eeg_frame.timestamp_ms,
            payload=EEGFramePayload(
                sampling_rate=output.eeg_frame.sampling_rate,
                channels=output.waveform_channels,
            ).model_dump(),
        )
        await self._broadcast(eeg_message.model_dump())

        for event in output.events:
            prediction_message = Envelope(
                type="mi_probs",
                timestamp_ms=event.window.timestamp_ms,
                payload=MIPredictionPayload(
                    label=event.prediction.label,
                    signal_code=signal_code_for_label(event.prediction.label),
                    probabilities=event.prediction.probabilities,
                    confidence=event.prediction.confidence,
                    usable=event.quality.usable,
                    model_name=event.prediction.model_name,
                ).model_dump(),
            )
            quality_message = Envelope(
                type="signal_quality",
                timestamp_ms=event.window.timestamp_ms,
                payload=SignalQualityPayload(
                    ptp=event.quality.ptp,
                    rms=event.quality.rms,
                    usable=event.quality.usable,
                ).model_dump(),
            )
            topomap_message = Envelope(
                type="topomap",
                timestamp_ms=event.window.timestamp_ms,
                payload=[
                    TopomapSnapshotPayload(
                        id=snapshot.id,
                        channel_names=list(event.window.channel_names),
                        values=snapshot.values,
                        timestamp=snapshot.timestamp,
                    ).model_dump()
                    for snapshot in event.topomaps
                ],
            )
            await self._broadcast(prediction_message.model_dump())
            await self._broadcast(quality_message.model_dump())
            await self._broadcast(topomap_message.model_dump())

    async def _broadcast(self, message: dict) -> None:
        for client in tuple(self._clients):
            self._send_to_client(client, message)
        self._status["client_count"] = len(self._clients)

    def _send_to_client(self, websocket: WebSocket, message: dict) -> None:
        queue = self._client_queues.get(websocket)
        if queue is None:
            return
        try:
            queue.put_nowait(message)
        except asyncio.QueueFull:
            logger.warning(
                "Disconnecting slow realtime client after its %d-message queue filled",
                CLIENT_QUEUE_MAXSIZE,
            )
            self.disconnect(websocket)

    async def _run_client_sender(
        self,
        websocket: WebSocket,
        queue: asyncio.Queue[dict],
    ) -> None:
        try:
            while True:
                message = await queue.get()
                await websocket.send_json(message)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.debug("Realtime websocket sender stopped", exc_info=True)
        finally:
            self._clients.discard(websocket)
            self._client_queues.pop(websocket, None)
            if self._client_sender_tasks.get(websocket) is asyncio.current_task():
                self._client_sender_tasks.pop(websocket, None)
            self._status["client_count"] = len(self._clients)

    async def _send_command_ack(
        self,
        websocket: WebSocket,
        command: str,
        accepted: bool,
        message: str,
    ) -> None:
        self._send_to_client(
            websocket,
            Envelope(
                type="command_ack",
                timestamp_ms=self._now_ms(),
                payload={
                    "command": command,
                    "accepted": accepted,
                    "message": message,
                },
            ).model_dump(),
        )

    async def _broadcast_runtime_state(self) -> None:
        if self._clients:
            await self._broadcast(self._runtime_state_envelope())

    def _runtime_state_envelope(self) -> dict:
        return Envelope(
            type="runtime_state",
            timestamp_ms=self._now_ms(),
            payload=self._runtime_state_payload(),
        ).model_dump()

    def _runtime_state_payload(self) -> dict[str, object]:
        windows_collected = len(self._inference_probabilities)
        progress = (
            windows_collected / self._inference_windows_target
            if self._inference_windows_target > 0
            else 0.0
        )
        tcp_diagnostics = (
            self._tcp_receiver.diagnostics_snapshot()
            if self._tcp_receiver is not None
            else {
                "stream_state": "idle",
                "tcp_connected": False,
                "tcp_connection_count": 0,
                "tcp_connected_at_ms": None,
                "tcp_disconnected_at_ms": None,
                "tcp_bytes_received": 0,
                "tcp_pending_frame_bytes": 0,
                "tcp_expected_frame_bytes": EXPECTED_FRAME_SIZE,
                "tcp_frames_received": 0,
                "tcp_last_byte_at_ms": None,
                "tcp_last_frame_at_ms": None,
                "tcp_last_header": None,
            }
        )
        return {
            "source_mode": self.settings.source.mode,
            "acquisition_state": self._acquisition_state,
            "inference_state": self._inference_state,
            "collection_windows_collected": self._collection_windows_seen,
            "collection_windows_target": self._collection_windows_target,
            "windows_collected": windows_collected,
            "windows_target": self._inference_windows_target,
            "progress": min(1.0, progress),
            "final_result": self._inference_final_result,
            "error": self._source_error,
            **tcp_diagnostics,
        }

    async def _consume_inference_events(self, events: list) -> None:
        if self._inference_state not in {"collecting", "inferring"} or not events:
            return

        for event in events:
            if self._inference_state == "collecting":
                self._collection_windows_seen += 1
                if self._collection_windows_seen >= self._collection_windows_target:
                    self._inference_state = "inferring"
                continue

            if self._inference_state != "inferring":
                break

            self._inference_probabilities.append(dict(event.prediction.probabilities))
            if len(self._inference_probabilities) >= self._inference_windows_target:
                labels = tuple(self._inference_probabilities[0])
                averaged = {
                    label: sum(item.get(label, 0.0) for item in self._inference_probabilities)
                    / len(self._inference_probabilities)
                    for label in labels
                }
                final_label = max(averaged, key=averaged.get)
                completed_at_ms = self._now_ms()
                signal_code = signal_code_for_label(final_label)
                self._inference_final_result = {
                    "label": final_label,
                    "signal_code": signal_code,
                    "confidence": averaged[final_label],
                    "probabilities": averaged,
                    "window_count": len(self._inference_probabilities),
                    "completed_at_ms": completed_at_ms,
                    "device_output": {"status": "pending"},
                }
                self._inference_state = "complete"
                await self._emit_final_device_result()
                break

        await self._broadcast_runtime_state()

    async def _emit_final_device_result(self) -> None:
        result = self._inference_final_result
        if result is None:
            return

        label = str(result["label"])
        signal_code = int(result["signal_code"])
        completed_at_ms = int(result["completed_at_ms"])
        action = f"emit_{label}"
        accepted = True
        reason = "formal_inference_complete"

        try:
            assert self.device_adapter is not None
            await asyncio.to_thread(
                self.device_adapter.send_action,
                action,
                {
                    "label": label,
                    "signal_code": signal_code,
                    "confidence": float(result["confidence"]),
                    "probabilities": result["probabilities"],
                    "window_count": int(result["window_count"]),
                    "timestamp_ms": completed_at_ms,
                },
            )
            result["device_output"] = {"status": "sent"}
        except Exception as error:
            accepted = False
            reason = "device_output_error"
            result["device_output"] = {
                "status": "error",
                "error": str(error),
            }
            logger.exception("Unable to send the final inference result to the device adapter")

        device_message = Envelope(
            type="device_action",
            timestamp_ms=completed_at_ms,
            payload=DeviceControlPayload(
                device_id=self.settings.device.device_id,
                action=action,
                accepted=accepted,
                reason=reason,
                signal_code=signal_code,
            ).model_dump(),
        )
        await self._broadcast(device_message.model_dump())

    def _reset_inference_state(
        self,
        *,
        collection_window_count: int = 5,
        inference_window_count: int = 5,
    ) -> None:
        self._inference_state = "collecting"
        self._collection_windows_target = max(1, min(50, collection_window_count))
        self._collection_windows_seen = 0
        self._inference_windows_target = max(1, min(50, inference_window_count))
        self._inference_probabilities = []
        self._inference_final_result = None

    @staticmethod
    def _now_ms() -> int:
        return int(time.time() * 1000)

    async def _run_demo_loop(self) -> None:
        source = MockEEGSource()
        while True:
            await self.ingest_frame(source.next_frame())
            await asyncio.sleep(source.samples_per_frame / float(source.sampling_rate))

    async def _run_source_monitor(self) -> None:
        while True:
            await self._broadcast_runtime_state()
            await asyncio.sleep(0.5)

    async def _run_tcp_loop(self) -> None:
        config = TCPReceiverConfig(
            host=self.settings.source.tcp_host,
            port=self.settings.source.tcp_port,
        )
        receiver = TCPReceiver(config)
        self._tcp_receiver = receiver

        while True:
            try:
                await asyncio.to_thread(receiver.connect)
                self._acquisition_state = "running"
                self._source_error = None
                await self._broadcast_runtime_state()
                while True:
                    frame = await asyncio.to_thread(receiver.receive_frame)
                    await self.ingest_frame(frame)
            except asyncio.CancelledError:
                receiver.close()
                raise
            except Exception as error:
                receiver.close()
                self._acquisition_state = "connecting"
                self._source_error = str(error)
                await self._broadcast_runtime_state()
                await asyncio.sleep(1.0)
