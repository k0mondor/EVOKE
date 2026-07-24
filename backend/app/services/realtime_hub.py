from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass, field

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
from models.realtime.tcp_receiver import TCPReceiver, TCPReceiverConfig


@dataclass(slots=True)
class RealtimeHub:
    settings: AppSettings = field(default_factory=load_app_settings)
    session: RealtimeSession = field(default_factory=RealtimeSession)
    device_adapter: DeviceAdapter | None = field(default=None)
    _clients: set[WebSocket] = field(default_factory=set, init=False)
    _source_task: asyncio.Task | None = field(default=None, init=False)
    _status: dict[str, object] = field(default_factory=dict, init=False)

    async def start(self) -> None:
        if self.device_adapter is None:
            self.device_adapter = build_device_adapter(self.settings.device)
        self.device_adapter.connect()
        source_mode = self.settings.source.mode
        self._status = {
            "source_mode": source_mode,
            "device_mode": self.settings.device.mode,
            "client_count": 0,
            "last_frame_timestamp_ms": None,
            "last_prediction_label": None,
            "last_prediction_confidence": None,
        }
        if source_mode == "tcp":
            self._source_task = asyncio.create_task(self._run_tcp_loop())
        else:
            self._source_task = asyncio.create_task(self._run_demo_loop())

    async def stop(self) -> None:
        if self._source_task is not None:
            self._source_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._source_task
        self.device_adapter.close()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._clients.add(websocket)
        self._status["client_count"] = len(self._clients)

    def disconnect(self, websocket: WebSocket) -> None:
        self._clients.discard(websocket)
        self._status["client_count"] = len(self._clients)

    def status_snapshot(self) -> dict[str, object]:
        return dict(self._status)

    async def ingest_frame(self, frame) -> None:
        output = self.session.push_frame(frame)
        self._status["last_frame_timestamp_ms"] = output.eeg_frame.timestamp_ms
        if output.events:
            event = output.events[-1]
            self._status["last_prediction_label"] = event.prediction.label
            self._status["last_prediction_confidence"] = event.prediction.confidence
        await self._publish_output(output)

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
                        values=snapshot.values,
                        timestamp=snapshot.timestamp,
                    ).model_dump()
                    for snapshot in event.topomaps
                ],
            )
            device_message = Envelope(
                type="device_action",
                timestamp_ms=event.window.timestamp_ms,
                payload=DeviceControlPayload(
                    device_id="default-device",
                    action=event.device_action.action,
                    accepted=event.device_action.accepted,
                    reason=event.device_action.reason,
                    signal_code=event.device_action.signal_code,
                ).model_dump(),
            )

            if event.device_action.accepted:
                assert self.device_adapter is not None
                self.device_adapter.send_action(
                    event.device_action.action,
                    {
                        "label": event.prediction.label,
                        "signal_code": event.device_action.signal_code,
                        "confidence": event.prediction.confidence,
                        "timestamp_ms": event.window.timestamp_ms,
                    },
                )

            await self._broadcast(prediction_message.model_dump())
            await self._broadcast(quality_message.model_dump())
            await self._broadcast(topomap_message.model_dump())
            await self._broadcast(device_message.model_dump())

    async def _broadcast(self, message: dict) -> None:
        stale: list[WebSocket] = []
        for client in self._clients:
            try:
                await client.send_json(message)
            except Exception:
                stale.append(client)

        for client in stale:
            self._clients.discard(client)

    async def _run_demo_loop(self) -> None:
        source = MockEEGSource()
        while True:
            await self.ingest_frame(source.next_frame())
            await asyncio.sleep(source.samples_per_frame / float(source.sampling_rate))

    async def _run_tcp_loop(self) -> None:
        config = TCPReceiverConfig(
            host=self.settings.source.tcp_host,
            port=self.settings.source.tcp_port,
        )
        receiver = TCPReceiver(config)

        while True:
            try:
                await asyncio.to_thread(receiver.connect)
                while True:
                    frame = await asyncio.to_thread(receiver.receive_frame)
                    await self.ingest_frame(frame)
            except asyncio.CancelledError:
                receiver.close()
                raise
            except Exception:
                receiver.close()
                await asyncio.sleep(1.0)
