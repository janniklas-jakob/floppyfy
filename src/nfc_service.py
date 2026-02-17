"""
PN532 NFC reader service.

Provides a simple polling interface: call :meth:`get_uid` in a loop
to detect tag presence. Returns the tag's UID as a colon-separated
hex string (e.g. ``04:a3:4b:d2``) or ``None`` when no tag is present.
"""

import logging
from typing import Optional

from config import NFC_READ_TIMEOUT_SEC

logger = logging.getLogger(__name__)


def _format_uid(raw: bytearray) -> str:
    """Convert a raw UID bytearray to a human-readable hex string."""
    return ':'.join(f'{byte:02x}' for byte in raw)


class NFCService:
    """Thin wrapper around an Adafruit PN532 I2C driver."""

    def __init__(self) -> None:
        self.pn532 = None
        try:
            import board          # type: ignore[import-untyped]
            import busio           # type: ignore[import-untyped]
            from adafruit_pn532.i2c import PN532_I2C  # type: ignore[import-untyped]

            i2c = busio.I2C(board.SCL, board.SDA)
            self.pn532 = PN532_I2C(i2c, debug=False)

            ic, ver, rev, support = self.pn532.firmware_version
            logger.info("Found PN532 with firmware version: %d.%d", ver, rev)

            self.pn532.SAM_configuration()
        except Exception as exc:
            logger.error("Failed to initialise PN532: %s", exc)

    def get_uid(self) -> Optional[str]:
        """Return the UID of the tag currently on the reader, or ``None``."""
        if not self.pn532:
            return None

        try:
            uid = self.pn532.read_passive_target(timeout=NFC_READ_TIMEOUT_SEC)
            if uid is not None:
                return _format_uid(uid)
            return None
        except Exception as exc:
            logger.error("Error reading NFC: %s", exc)
            return None
