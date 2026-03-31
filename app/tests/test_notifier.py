"""Tests for ``SocketIONotifier`` event emission behavior."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

from notifier import SocketIONotifier


class _FakeSerializer:
    def __init__(self) -> None:
        self.encode = MagicMock(side_effect=lambda payload: f"encoded:{payload}")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method_name", "payload", "event_name"),
    [
        ("added", MagicMock(title="Video A"), "added"),
        ("updated", MagicMock(title="Video B"), "updated"),
        ("completed", MagicMock(title="Video C"), "completed"),
        ("canceled", "download-id", "canceled"),
        ("cleared", "download-id", "cleared"),
    ],
)
async def test_notifier_emits_expected_socket_event(method_name, payload, event_name):
    sio = MagicMock()
    sio.emit = AsyncMock()
    serializer = _FakeSerializer()
    logger = MagicMock(spec=logging.Logger)
    notifier = SocketIONotifier(sio=sio, serializer=serializer, logger=logger)

    await getattr(notifier, method_name)(payload)

    serializer.encode.assert_called_once_with(payload)
    sio.emit.assert_awaited_once_with(event_name, f"encoded:{payload}")
    logger.log.assert_called_once()
