"""
Simple HTTP file server for local music playback via Sonos.

Serves files from :data:`config.MUSIC_DIRECTORY` at the port
configured in :data:`config.MUSIC_SERVER_PORT`.
"""

import http.server
import logging
import os
import socketserver

from config import MUSIC_DIRECTORY, MUSIC_SERVER_PORT

logger = logging.getLogger(__name__)


class _MusicHandler(http.server.SimpleHTTPRequestHandler):
    """Serve files from the configured music directory."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=MUSIC_DIRECTORY, **kwargs)

    def log_message(self, fmt, *args):  # noqa: D102
        logger.info(fmt, *args)


def run() -> None:
    """Start the music file server (blocking)."""
    os.makedirs(MUSIC_DIRECTORY, exist_ok=True)

    with socketserver.TCPServer(('', MUSIC_SERVER_PORT), _MusicHandler) as httpd:
        logger.info("Serving music on port %d from %s", MUSIC_SERVER_PORT, MUSIC_DIRECTORY)
        httpd.serve_forever()


if __name__ == '__main__':
    run()
