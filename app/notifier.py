"""Notification adapters for download queue lifecycle events.

This module keeps queue-notification transport logic outside of the web
bootstrap. ``SocketIONotifier`` implements the ``DownloadQueueNotifier``
interface and translates queue callbacks into Socket.IO events for browser
clients.

The notifier is intentionally small:
- ``ytdl.py`` owns the callback interface;
- the notifier owns serialization, logging, and event emission;
- ``main.py`` only wires dependencies together.

This separation makes it easier to extend notifications later with additional
destinations, payload shaping, or per-event routing rules without growing the
application bootstrap.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import socketio

from ytdl import DownloadQueueNotifier

DEFAULT_LOGGER = logging.getLogger("notifier")


class SocketIONotifier(DownloadQueueNotifier):
    """Emit download queue lifecycle updates through Socket.IO.

    The class preserves the existing ``DownloadQueueNotifier`` contract while
    moving transport-specific concerns out of ``main.py``. A single helper
    method centralizes event lookup, logging, serialization, and emission so
    future extensions can be added in one place.
    """

    _EVENTS = {
        "added": ("added", logging.INFO, "Notifier: Download added - %s"),
        "updated": ("updated", logging.DEBUG, "Notifier: Download updated - %s"),
        "completed": ("completed", logging.INFO, "Notifier: Download completed - %s"),
        "canceled": ("canceled", logging.INFO, "Notifier: Download canceled - %s"),
        "cleared": ("cleared", logging.INFO, "Notifier: Download cleared - %s"),
    }

    def __init__(
        self,
        sio: socketio.AsyncServer,
        serializer: json.JSONEncoder,
        logger: logging.Logger | None = None,
    ) -> None:
        """Store the explicit dependencies needed to publish notifier events."""
        self.sio = sio
        self.serializer = serializer
        self.logger = logger or DEFAULT_LOGGER

    async def _emit(self, event_key: str, payload: Any, log_arg: Any) -> None:
        """Serialize the payload, log the transition, and emit a Socket.IO event."""
        event_name, level, log_message = self._EVENTS[event_key]
        self.logger.log(level, log_message, log_arg)
        await self.sio.emit(event_name, self.serializer.encode(payload))

    async def added(self, dl):
        """Publish the ``added`` queue event for a newly enqueued download."""
        await self._emit("added", dl, dl.title)

    async def updated(self, dl):
        """Publish the ``updated`` queue event for progress or state changes."""
        await self._emit("updated", dl, dl.title)

    async def completed(self, dl):
        """Publish the ``completed`` queue event when a download finishes."""
        await self._emit("completed", dl, dl.title)

    async def canceled(self, identifier):
        """Publish the ``canceled`` queue event for a removed in-flight item."""
        await self._emit("canceled", identifier, identifier)

    async def cleared(self, identifier):
        """Publish the ``cleared`` queue event for a removed completed item."""
        await self._emit("cleared", identifier, identifier)
