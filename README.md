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

3. Link Spotify to Sonos:
   Ensure your Spotify Premium account is linked within the official Sonos app. Floppyfy now uses the Sonos API directly to start playback, so you no longer need to create a Spotify Developer App or manage API keys.

4. Run:
   ```bash
   source ./venv/bin/activate
   python3 src/main.py
   ```

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
