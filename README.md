# Floppyfy Setup Guide

## Hardware
- Raspberry Pi Zero 2W
- PN532 NFC Module (I2C Mode)

## Wiring (I2C)
| PN532 | Pi Zero 2W |
|-------|------------|
| VCC   | 5V (Pin 2) |
| GND   | GND (Pin 6)|
| SDA   | SDA (Pin 3)|
| SCL   | SCL (Pin 5)|

## Software Setup (On Raspberry Pi)
1. Enable I2C Interface:
   `sudo raspi-config` -> Interface Options -> I2C -> Enable

2. Install Dependencies:
   ```bash
   sudo apt-get update
   sudo apt-get install python3-pip libopenjp2-7 python3-venv
   python3 -m venv .venv
   source .venv/bin/activate
   pip3 install -r requirements.txt
   ```

3. Configure Spotify:
   Create a `.env` file in the root directory:
   ```env
   SPOTIPY_CLIENT_ID=your_id_here
   SPOTIPY_CLIENT_SECRET=your_secret_here
   ```

4. Run:
   ```bash
   source ./venv/bin/activate
   python3 src/main.py
   ```

5. Authenticate Spotify (Headless via SSH):
   When running the application on a headless system for the first time, you need to authenticate Spotipy:
   - Scan a tag associated with a Spotify URI (or trigger playback).
   - The terminal will print an authorization link starting with `https://accounts.spotify.com/authorize?...`.
   - Copy that entire link and open it in a browser on your computer.
   - Log in to Spotify and grant permissions.
   - Your browser will then be redirected to a localhost URL (e.g., `http://127.0.0.1:5000/callback?...`) and likely show a "Site cannot be reached" error. This is expected.
   - Copy the **entire redirect URL** from your browser's address bar.
   - Go back to your SSH terminal, paste the copied URL into the prompt (`Enter the URL you were redirected to:`), and press `Enter`.
   
   *Alternative:* Connect via SSH with port forwarding: `ssh -L 5000:127.0.0.1:5000 pi@<raspberry-pi-ip>`. This forwards the callback directly to your machine so the browser redirect completes seamlessly.

6. Wake Up Sonos / Cache Spotify Device ID:
   Sonos speakers frequently disappear from the active Spotify Connect device list (e.g., when they go into TV mode or standby). To fix this, Floppyfy caches the active `device_id` to reliably wake up the speaker later.
   - For the first time (or if the device wasn't found), open the Spotify app on your phone or computer.
   - Select your Sonos speaker (e.g., `Wohnzimmer TV`) and play *any* song for a second so Spotify makes it "active".
   - While it's active, scan a tag on the Floppyfy reader.
   - Floppyfy will discover the speaker and immediately cache its unique `device_id` into your `settings.json`. From then on, it can wake the speaker seamlessly without your phone.

## Local Music Server
Top lay local files, ensure they are in `/home/pi/music` (or edit `src/music_server.py`).
The service runs on port 8080.
- **URI Format**: `http://<raspberry-pi-ip>:8080/filename.mp3`

## System Services
To enable auto-start:
```bash
sudo cp *.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now floppyfy.service
sudo systemctl enable --now floppyfy-web.service
sudo systemctl enable --now floppyfy-music.service
```
