import os
from dotenv import load_dotenv

load_dotenv()

# Database Path
DB_PATH = os.path.join(os.path.dirname(__file__), 'db.json')

# Spotify Config
SPOTIPY_CLIENT_ID = os.getenv('SPOTIPY_CLIENT_ID')
SPOTIPY_CLIENT_SECRET = os.getenv('SPOTIPY_CLIENT_SECRET')
SPOTIPY_REDIRECT_URI = 'http://localhost:5000/callback'

# Hardware Config
# I2C PINS for Raspberry Pi Zero 2W
SDA_PIN = 2
SCL_PIN = 3
