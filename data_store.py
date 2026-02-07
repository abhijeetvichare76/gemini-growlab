"""
data_store.py - CSV logging, decision JSON persistence, photo lookup.
"""

import csv
import json
import os
import glob
from datetime import datetime

import config


def ensure_data_dirs():
    """Create data directories if they don't exist."""
    os.makedirs(config.DATA_DIR, exist_ok=True)
    os.makedirs(config.PHOTOS_DIR, exist_ok=True)


def append_sensor_reading(readings):
    """
    Append a sensor reading row to the CSV log.
    Creates the file with headers if it doesn't exist.

    Args:
        readings: SensorReadings dataclass instance
    """
    ensure_data_dirs()
    headers = ["timestamp", "air_temp_c", "humidity_pct", "water_temp_c", "ph", "tds_ppm"]
    file_exists = os.path.exists(config.SENSOR_LOG_CSV)

    with open(config.SENSOR_LOG_CSV, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(headers)

        # None values become empty strings (pandas-friendly)
        row = [
            readings.timestamp,
            readings.air_temp_c if readings.air_temp_c is not None else "",
            readings.humidity_pct if readings.humidity_pct is not None else "",
            readings.water_temp_c if readings.water_temp_c is not None else "",
            readings.ph if readings.ph is not None else "",
            readings.tds_ppm if readings.tds_ppm is not None else "",
        ]
        writer.writerow(row)


def load_past_decisions(n=3):
    """
    Load the last N decisions from the decisions JSON file.

    Args:
        n: Number of past decisions to load

    Returns:
        List of decision dicts, most recent last
    """
    if not os.path.exists(config.DECISIONS_JSON):
        return []

    try:
        with open(config.DECISIONS_JSON, "r") as f:
            decisions = json.load(f)
        return decisions[-n:]
    except (json.JSONDecodeError, IOError):
        return []


def save_decision(decision, readings):
    """
    Append a decision to the decisions JSON file.
    Adds timestamp and sensor_snapshot fields.

    Args:
        decision: Dict from Gemini response
        readings: SensorReadings dataclass instance
    """
    ensure_data_dirs()

    decision["timestamp"] = datetime.now().isoformat()
    decision["sensor_snapshot"] = {
        "air_temp_c": readings.air_temp_c,
        "humidity_pct": readings.humidity_pct,
        "water_temp_c": readings.water_temp_c,
        "ph": readings.ph,
        "tds_ppm": readings.tds_ppm,
    }

    # Load existing decisions
    decisions = []
    if os.path.exists(config.DECISIONS_JSON):
        try:
            with open(config.DECISIONS_JSON, "r") as f:
                decisions = json.load(f)
        except (json.JSONDecodeError, IOError):
            decisions = []

    decisions.append(decision)

    with open(config.DECISIONS_JSON, "w") as f:
        json.dump(decisions, f, indent=2)


def get_latest_photo():
    """
    Return the path to the most recent photo in the photos directory.

    Returns:
        str path or None
    """
    photos = glob.glob(os.path.join(config.PHOTOS_DIR, "*.jpg"))
    if not photos:
        return None
    return max(photos, key=os.path.getmtime)
