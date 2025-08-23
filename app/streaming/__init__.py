"""Simple streaming manager using aiortc.

This module provides a minimal interface to start and stop a WebRTC
stream.  The actual media handling is intentionally minimal so the
module can be extended or replaced with a different backend such as an
RTMP pipeline.
"""

from __future__ import annotations

import asyncio
from typing import Optional

try:  # pragma: no cover - optional dependency
    from aiortc import RTCPeerConnection
except Exception:  # pragma: no cover
    RTCPeerConnection = None  # type: ignore


class StreamManager:
    """Manage a single outgoing stream.

    The manager lazily creates an :class:`RTCPeerConnection` instance
    when :func:`start` is called.  The URL returned is a placeholder
    that frontends can use to establish a WebRTC connection.
    """

    def __init__(self) -> None:
        self._pc: Optional[RTCPeerConnection] = None
        self._url: Optional[str] = None

    def start(self) -> str:
        """Start the stream and return the playback URL.

        Raises:
            RuntimeError: if ``aiortc`` is not installed.
        """

        if self._pc is not None:
            return self._url or ""
        if RTCPeerConnection is None:
            raise RuntimeError("aiortc is required to start WebRTC streaming")
        self._pc = RTCPeerConnection()
        # In a real implementation we would negotiate SDP here.
        self._url = "webrtc://localhost/stream"
        return self._url

    def stop(self) -> None:
        """Stop the active stream if running."""

        if self._pc is not None:
            try:
                asyncio.run(self._pc.close())
            except Exception:
                pass
        self._pc = None
        self._url = None

    def get_url(self) -> Optional[str]:
        """Return the current stream URL, if any."""

        return self._url


# Shared singleton used by routes and Socket.IO events
stream_manager = StreamManager()
