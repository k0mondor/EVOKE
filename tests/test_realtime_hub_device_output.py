from __future__ import annotations

import asyncio
from types import SimpleNamespace

from backend.app.core.settings import AppSettings, DeviceSettings, SourceSettings
from backend.app.services.realtime_hub import RealtimeHub
from models.realtime.device_adapter import NoopDeviceAdapter


def _event(left: float, right: float, feet: float) -> SimpleNamespace:
    return SimpleNamespace(
        prediction=SimpleNamespace(
            probabilities={
                "left": left,
                "right": right,
                "feet": feet,
            }
        )
    )


def _hub(adapter) -> RealtimeHub:
    return RealtimeHub(
        settings=AppSettings(
            source=SourceSettings(mode="demo"),
            device=DeviceSettings(mode="noop", device_id="test-device"),
        ),
        session=object(),
        device_adapter=adapter,
    )


def test_device_output_is_emitted_once_after_formal_inference_completes() -> None:
    async def scenario() -> None:
        adapter = NoopDeviceAdapter()
        hub = _hub(adapter)

        await hub._consume_inference_events([_event(0.1, 0.8, 0.1)])
        assert adapter.sent_actions == []

        hub._inference_state = "inferring"
        hub._inference_windows_target = 3
        await hub._consume_inference_events([_event(0.1, 0.8, 0.1)])
        await hub._consume_inference_events([_event(0.2, 0.7, 0.1)])
        assert adapter.sent_actions == []

        await hub._consume_inference_events([_event(0.1, 0.6, 0.3)])
        assert hub._inference_state == "complete"
        assert hub._inference_final_result is not None
        assert hub._inference_final_result["label"] == "right"
        assert hub._inference_final_result["signal_code"] == 1
        assert hub._inference_final_result["device_output"] == {"status": "sent"}
        assert len(adapter.sent_actions) == 1
        assert adapter.sent_actions[0]["payload"]["signal_code"] == 1

        await hub._consume_inference_events([_event(0.9, 0.05, 0.05)])
        assert len(adapter.sent_actions) == 1

    asyncio.run(scenario())


def test_device_output_failure_does_not_cancel_the_final_result() -> None:
    class FailingAdapter:
        def send_action(self, action: str, payload: dict) -> None:
            raise OSError("device offline")

        def close(self) -> None:
            return None

    async def scenario() -> None:
        hub = _hub(FailingAdapter())
        hub._inference_state = "inferring"
        hub._inference_windows_target = 1

        await hub._consume_inference_events([_event(0.7, 0.2, 0.1)])

        assert hub._inference_state == "complete"
        assert hub._inference_final_result is not None
        assert hub._inference_final_result["label"] == "left"
        assert hub._inference_final_result["signal_code"] == 0
        assert hub._inference_final_result["device_output"] == {
            "status": "error",
            "error": "device offline",
        }

    asyncio.run(scenario())


def test_auto_inference_skips_collection_windows_and_uses_following_windows() -> None:
    async def scenario() -> None:
        adapter = NoopDeviceAdapter()
        hub = _hub(adapter)
        hub._reset_inference_state(
            collection_window_count=2,
            inference_window_count=2,
        )

        await hub._consume_inference_events(
            [
                _event(0.95, 0.03, 0.02),
                _event(0.90, 0.05, 0.05),
            ]
        )
        assert hub._inference_state == "inferring"
        assert hub._collection_windows_seen == 2
        assert hub._inference_probabilities == []

        await hub._consume_inference_events(
            [
                _event(0.10, 0.80, 0.10),
                _event(0.20, 0.70, 0.10),
            ]
        )

        assert hub._inference_state == "complete"
        assert hub._inference_final_result is not None
        assert hub._inference_final_result["label"] == "right"
        assert hub._inference_final_result["window_count"] == 2
        assert hub._inference_final_result["probabilities"] == {
            "left": 0.15000000000000002,
            "right": 0.75,
            "feet": 0.1,
        }
        assert len(adapter.sent_actions) == 1

    asyncio.run(scenario())
