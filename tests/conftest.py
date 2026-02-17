"""
Shared test fixtures.

Adds ``src/`` to the Python path and provides helper utilities
used across test modules.
"""

import json
import os
import sys
import tempfile

# Ensure ``src/`` is importable without installing the package.
_SRC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src')
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)


def create_test_db(content: dict | None = None) -> str:
    """Write *content* to a temporary JSON file and return its path.

    Caller is responsible for cleanup.
    """
    if content is None:
        content = {
            "tags": {
                "aa:bb:cc:dd": {
                    "name": "Test Album",
                    "type": "spotify",
                    "uri": "spotify:album:test123",
                    "shuffle": False,
                },
                "11:22:33:44": {
                    "name": "Test Playlist",
                    "type": "spotify",
                    "uri": "spotify:playlist:test456",
                    "shuffle": True,
                },
                "ff:ee:dd:cc": {
                    "name": "Local File",
                    "type": "file",
                    "uri": "http://192.168.1.10:8080/song.mp3",
                    "shuffle": False,
                },
            },
            "settings": {
                "speakers": {
                    "coordinator": "Living Room",
                    "join": ["Kitchen"],
                }
            },
        }
    fd, path = tempfile.mkstemp(suffix='.json')
    with os.fdopen(fd, 'w') as fh:
        json.dump(content, fh)
    return path
