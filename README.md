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
   sudo apt-get install python3-pip libopenjp2-7
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
