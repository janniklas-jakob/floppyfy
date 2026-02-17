import board
import busio
from digitalio import DigitalInOut
from adafruit_pn532.i2c import PN532_I2C
import logging
import time

logger = logging.getLogger(__name__)

class NFCService:
    def __init__(self):
        self.pn532 = None
        try:
            # I2C connection:
            # On Raspberry Pi, board.SCL and board.SDA are the main I2C pins.
            i2c = busio.I2C(board.SCL, board.SDA)
            
            # Reset pin is usually not needed for I2C if wired correctly, 
            # but sometimes helpful. For now, we assume standard wiring.
            self.pn532 = PN532_I2C(i2c, debug=False)
            
            ic, ver, rev, support = self.pn532.firmware_version
            logger.info(f"Found PN532 with firmware version: {ver}.{rev}")
            
            self.pn532.SAM_configuration()
        except Exception as e:
            logger.error(f"Failed to initialize PN532: {e}")

    def get_uid(self):
        """
        Check for a card. Returns UID string (hex) if found, else None.
        This is non-blocking (mostly) but timeouts can occur.
        """
        if not self.pn532:
            return None
        
        try:
            # timeout=0.5 makes it relatively quick to return None if empty
            uid = self.pn532.read_passive_target(timeout=0.1)
            if uid:
                return ':'.join([hex(i)[2:].zfill(2) for i in uid])
            return None
        except Exception as e:
            logger.error(f"Error reading NFC: {e}")
            return None
