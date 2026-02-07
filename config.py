"""
config.py - Central configuration for the AI Hydroponics system.
All constants, pins, thresholds, paths, and timing parameters.
"""

import os

# =============================================================================
# PROJECT PATHS
# =============================================================================
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
PHOTOS_DIR = os.path.join(DATA_DIR, "photos")
SENSOR_LOG_CSV = os.path.join(DATA_DIR, "sensor_log.csv")
DECISIONS_JSON = os.path.join(DATA_DIR, "decisions.json")
LOG_FILE = os.path.join(DATA_DIR, "hydroponics.log")
DASHBOARD_HTML = os.path.join(DATA_DIR, "dashboard.html")
DEVICES_JSON = os.path.join(PROJECT_ROOT, "devices.json")
ENV_FILE = os.path.join(PROJECT_ROOT, ".env")

# =============================================================================
# GPIO PINS
# =============================================================================
DHT22_PIN = 17          # board.D17
DS18B20_BASE_DIR = "/sys/bus/w1/devices/"
ADS1115_TDS_CHANNEL = 0
ADS1115_PH_CHANNEL = 1

# =============================================================================
# SENSOR TIMING (seconds)
# =============================================================================
READINGS_PER_SENSOR = 5         # Total reads per sensor
READINGS_TO_DISCARD = 2         # Discard first N reads
INTRA_SENSOR_DELAY = 2.0        # Seconds between reads of the same sensor
INTER_SENSOR_DELAY = 5.0        # Seconds between different sensors
PH_TDS_DELAY = 0.15             # 150ms between pH and TDS reads

# =============================================================================
# SENSOR VALIDATION RANGES
# =============================================================================
PH_MIN = 3.0
PH_MAX = 9.0
TDS_MIN = 0
TDS_MAX = 3000          # ppm
AIR_TEMP_MIN = 5.0      # Celsius
AIR_TEMP_MAX = 50.0
WATER_TEMP_MIN = 5.0
WATER_TEMP_MAX = 50.0
HUMIDITY_MIN = 5.0
HUMIDITY_MAX = 100.0

# =============================================================================
# TUYA SMART PLUG
# =============================================================================
TUYA_DEVICE_NAME = "Smart Power Strip"
TUYA_IP = "10.0.0.224"
TUYA_VERSION = 3.3
# DPS mapping (update after physical test)
DPS_LIGHT = "1"
DPS_AIR_PUMP = "2"
DPS_HUMIDIFIER = "3"
TUYA_COMMAND_DELAY = 0.5  # Seconds between plug commands

# =============================================================================
# DOSING PUMPS
# =============================================================================
DOSING_DURATION = 5      # Seconds per pump activation
# Motor 1 = pH Down (FloraMicro), Motor 2 = pH Up (FloraGrow)

# =============================================================================
# GEMINI AI
# =============================================================================
GEMINI_MODEL = "gemini-3-flash-preview"
GEMINI_TEMPERATURE = 0.2
PAST_DECISIONS_COUNT = 3  # Number of past decisions to include in prompt

# =============================================================================
# CAMERA
# =============================================================================
CAMERA_INDEX = 0
CAMERA_WARMUP_FRAMES = 10

# =============================================================================
# VIDEO STREAMING
# =============================================================================
VIDEO_STREAM_ENABLED = True           # Master toggle for video streaming
VIDEO_SERVER_IP = "10.0.0.239"        # IP of receiving PC
VIDEO_SERVER_PORT = 8000              # Port for video streaming
VIDEO_DURATION_MINUTES = 5.0          # Minutes per recording session
VIDEO_WIDTH = 1920                    # Frame width (pixels)
VIDEO_HEIGHT = 1080                   # Frame height (pixels)
VIDEO_FPS = 5                         # Target transmission FPS
VIDEO_HW_FPS = 5                      # Hardware capture FPS
VIDEO_JPEG_QUALITY = 95               # JPEG compression quality (0-100)

# =============================================================================
# LIGHT SCHEDULE (24-hour format)
# =============================================================================
LIGHTS_ON_HOUR = 6       # 6 AM
LIGHTS_OFF_HOUR = 22     # 10 PM (16h on / 8h off)

# =============================================================================
# IDEAL RANGES (for Gemini prompt context)
# =============================================================================
IDEAL_RANGES = {
    "air_temp_c": {"min": 20, "max": 28, "unit": "C"},
    "humidity_pct": {"min": 40, "max": 70, "unit": "%"},
    "water_temp_c": {"min": 18, "max": 24, "unit": "C"},
    "ph": {"min": 5.5, "max": 6.5, "unit": ""},
    "tds_ppm": {"min": 560, "max": 840, "unit": "ppm"},
}
