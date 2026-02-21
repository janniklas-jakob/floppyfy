import os
import sys
from dotenv import load_dotenv

# Add src to path so we can import modules
sys.path.append(os.path.join(os.getcwd(), 'src'))

from spotify_client import SpotifyClient

def list_spotify_devices():
    load_dotenv()
    client = SpotifyClient()
    
    print("\n--- FETCHING SPOTIFY DEVICES ---")
    devices = client.get_devices()
    
    if not devices.get('devices'):
        print("No active Spotify devices found.")
        print("Make sure you are playing music on one of your devices (phone, PC, Sonos) right now!")
        return

    print(f"{'DEVICE NAME':<30} | {'TYPE':<12} | {'ID'}")
    print("-" * 80)
    for dev in devices['devices']:
        name = dev['name']
        dtype = dev['type']
        did = dev['id']
        is_active = "[ACTIVE]" if dev['is_active'] else ""
        print(f"{name:<30} | {dtype:<12} | {did} {is_active}")
    print("\nPRO TIP: If you see your Sonos speaker above, copy its ID.")
    print("You can manually set it in settings.json as 'spotify_device_id'.\n")

if __name__ == "__main__":
    list_spotify_devices()
