"""
Uploads decision data and plant photos to Supabase.
Called after each Gemini decision cycle in main.py.
"""

import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()
logger = logging.getLogger(__name__)

# Supabase client (initialized lazily)
_client: Optional[Client] = None

SUPABASE_URL = os.getenv("SUPABASE_PROJECT_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SECRET_KEY")
BUCKET_NAME = "plant-photos"


def _get_client() -> Optional[Client]:
    """Get or create the Supabase client. Returns None if not configured."""
    global _client
    if _client is not None:
        return _client

    if not SUPABASE_URL or not SUPABASE_KEY:
        logger.warning("Supabase credentials not configured. Skipping upload.")
        return None

    _client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _client


def _upload_photo(client: Client, photo_path: str) -> Optional[str]:
    """
    Upload a photo to Supabase Storage.

    Args:
        client: Supabase client instance
        photo_path: Local file path to the JPEG photo

    Returns:
        Public URL of the uploaded photo, or None if upload fails
    """
    if not photo_path or not Path(photo_path).exists():
        logger.warning(f"Photo not found at {photo_path}, skipping upload.")
        return None

    # Generate storage path from timestamp: "2026-02-08T14-00-00.jpg"
    timestamp_str = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    storage_path = f"{timestamp_str}.jpg"

    try:
        with open(photo_path, "rb") as f:
            photo_bytes = f.read()

        client.storage.from_(BUCKET_NAME).upload(
            path=storage_path,
            file=photo_bytes,
            file_options={"content-type": "image/jpeg"}
        )

        # Construct the public URL
        public_url = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET_NAME}/{storage_path}"
        logger.info(f"Photo uploaded: {public_url}")
        return public_url

    except Exception as e:
        logger.error(f"Failed to upload photo: {e}")
        return None


def upload_decision(decision: dict, readings, photo_path: Optional[str] = None) -> bool:
    """
    Upload a decision record and its associated photo to Supabase.

    This is the main entry point called from main.py after each cycle.

    Args:
        decision: The Gemini decision dict (light, air_pump, humidifier,
                  ph_adjustment, reasoning, plant_health_score, human_intervention)
        readings: SensorReadings dataclass instance
        photo_path: Optional path to the captured plant photo

    Returns:
        True if upload succeeded, False otherwise
    """
    client = _get_client()
    if client is None:
        return False

    try:
        # Upload photo first (if available)
        photo_url = _upload_photo(client, photo_path) if photo_path else None

        # Validate and clamp plant_health_score to 0-10 range (database constraint)
        health_score = decision["plant_health_score"]
        if health_score < 0 or health_score > 10:
            logger.warning(f"plant_health_score {health_score} out of range, clamping to 0-10")
            health_score = max(0, min(10, health_score))

        # Build the row matching the decisions table schema
        row = {
            "cycle_timestamp": readings.timestamp,
            "air_temp_c": readings.air_temp_c,
            "humidity_pct": readings.humidity_pct,
            "water_temp_c": readings.water_temp_c,
            "ph": readings.ph,
            "tds_ppm": readings.tds_ppm,
            "light": decision["light"],
            "air_pump": decision["air_pump"],
            "humidifier": decision["humidifier"],
            "ph_adjustment": decision["ph_adjustment"],
            "reasoning": decision["reasoning"],
            "plant_health_score": health_score,
            "intervention_needed": decision["human_intervention"]["needed"],
            "intervention_message": decision["human_intervention"].get("message", ""),
            "photo_url": photo_url,
        }

        client.table("decisions").insert(row).execute()
        logger.info("Decision uploaded to Supabase successfully.")
        return True

    except Exception as e:
        logger.error(f"Failed to upload decision to Supabase: {e}")
        return False
