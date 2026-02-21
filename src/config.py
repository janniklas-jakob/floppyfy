"""
Application-wide configuration.

Loads environment variables from `.env` and defines constants used
across all modules.
"""

import logging
import os
from enum import Enum
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

logging.basicConfig(level=getattr(logging, LOG_LEVEL, logging.INFO), format=LOG_FORMAT)

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
DB_PATH = os.getenv('DB_PATH', os.path.expanduser('~/floppyfy.json'))

# ---------------------------------------------------------------------------
# NFC polling
# ---------------------------------------------------------------------------
NFC_POLL_INTERVAL_SEC: float = float(os.getenv('NFC_POLL_INTERVAL', '0.2'))
NFC_READ_TIMEOUT_SEC: float = float(os.getenv('NFC_READ_TIMEOUT', '0.1'))
TAG_REMOVAL_DEBOUNCE_SEC: float = float(os.getenv('TAG_REMOVAL_DEBOUNCE', '1.5'))

# ---------------------------------------------------------------------------
# Music server
# ---------------------------------------------------------------------------
MUSIC_SERVER_PORT: int = int(os.getenv('MUSIC_SERVER_PORT', '8080'))
MUSIC_DIRECTORY: str = os.getenv('MUSIC_DIRECTORY', '/home/pi/music')


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class PlaybackSource(str, Enum):
    """Identifies which backend is responsible for current playback."""
    SPOTIFY = 'spotify'
    FILE = 'file'
