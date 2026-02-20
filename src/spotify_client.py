"""
Spotify Web API client.

Wraps *spotipy* to provide play / pause / resume / device-listing
methods.  All operations are no-ops if credentials are not configured.
"""

import logging
import time
from typing import Optional

import spotipy
from spotipy.oauth2 import SpotifyOAuth

from config import SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI

logger = logging.getLogger(__name__)

# Silence expected HTTP 404 errors from spotipy when pausing without an active device
logging.getLogger("spotipy.client").setLevel(logging.CRITICAL)

_REQUIRED_SCOPES = 'user-read-playback-state,user-modify-playback-state'
_DEVICE_SYNC_DELAY_SEC = 1.0


class SpotifyClient:
    """Thin facade over the Spotify Web API for playback control."""

    def __init__(
        self,
        client_id: Optional[str] = SPOTIPY_CLIENT_ID,
        client_secret: Optional[str] = SPOTIPY_CLIENT_SECRET,
        redirect_uri: str = SPOTIPY_REDIRECT_URI,
    ) -> None:
        self.sp: Optional[spotipy.Spotify] = None

        if client_id and client_secret:
            auth = SpotifyOAuth(
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri,
                scope=_REQUIRED_SCOPES,
                open_browser=False,
            )
            self.sp = spotipy.Spotify(auth_manager=auth)
        else:
            logger.warning("Spotify credentials not provided — Spotify playback disabled.")

    @property
    def is_configured(self) -> bool:
        """Return ``True`` if a Spotify session is available."""
        return self.sp is not None

    def play(self, uri: str, *, device_id: Optional[str] = None, shuffle: bool = False) -> None:
        """Start playback of *uri* (album, playlist, or track)."""
        if not self.sp:
            return

        try:
            if device_id:
                self.sp.transfer_playback(device_id=device_id, force_play=False)
                time.sleep(_DEVICE_SYNC_DELAY_SEC)

            self.sp.shuffle(shuffle)

            if ':track:' in uri:
                self.sp.start_playback(uris=[uri])
            else:
                self.sp.start_playback(context_uri=uri)
        except Exception as exc:
            logger.error("Spotify play error: %s", exc)

    def pause(self) -> None:
        """Pause playback. Silently ignores errors (e.g. already paused)."""
        if not self.sp:
            return
        try:
            self.sp.pause_playback()
        except Exception:
            pass  # already paused

    def resume(self) -> None:
        """Resume playback."""
        if not self.sp:
            return
        try:
            self.sp.start_playback()
        except Exception:
            pass  # nothing to resume

    def get_devices(self) -> dict:
        """Return the Spotify Connect device list."""
        if not self.sp:
            return {}
        try:
            return self.sp.devices()
        except Exception as exc:
            logger.error("Error fetching Spotify devices: %s", exc)
            return {}
