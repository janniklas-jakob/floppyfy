import spotipy
from spotipy.oauth2 import SpotifyOAuth
import logging
import time

logger = logging.getLogger(__name__)

class SpotifyClient:
    def __init__(self, client_id, client_secret, redirect_uri):
        self.sp = None
        if client_id and client_secret:
            self.auth_manager = SpotifyOAuth(
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri,
                scope="user-read-playback-state,user-modify-playback-state"
            )
            self.sp = spotipy.Spotify(auth_manager=self.auth_manager)
        else:
            logger.warning("Spotify credentials not provided.")

    def play(self, uri, device_id=None, shuffle=False):
        if not self.sp:
            return
        
        try:
            # Transfer playback to device if provided (force connection)
            if device_id:
                self.sp.transfer_playback(device_id=device_id, force_play=False)
                time.sleep(1) # Wait for sync

            # Set Shuffle
            self.sp.shuffle(shuffle)

            # Start Context
            # context_uri for albums/playlists, uris=[uri] for tracks
            if "track" in uri:
                self.sp.start_playback(uris=[uri])
            else:
                self.sp.start_playback(context_uri=uri)

        except Exception as e:
            logger.error(f"Spotify Play Error: {e}")

    def pause(self):
        if self.sp:
            try:
                self.sp.pause_playback()
            except Exception:
                pass # Ignore if already paused

    def resume(self):
        if self.sp:
            try:
                self.sp.start_playback()
            except Exception:
                pass

    def get_devices(self):
        if self.sp:
            return self.sp.devices()
        return []
