#!/usr/bin/env python3
"""
main.py - Cron entry point / orchestrator for the AI Hydroponics system.

Designed to run every 60 minutes via cron:
  */60 * * * * cd /path/to/Gemini-hydroponics && venv/bin/python main.py

Flow:
  1. Read sensors       -> SensorReadings
  2. Store in CSV       -> data_store
  3. Capture photo      -> filepath
  4. Load history       -> past decisions
  5. Query Gemini       -> decision dict
  6. Store decision     -> data_store
  7. Execute actions    -> smart plugs + dosing pump
  8. Log reasoning      -> per-actuator reasoning + human_intervention flag
  9. Stream video       -> remote PC timelapse (5 min)
"""

import logging
import os
import sys
from datetime import datetime
import time

import config
import data_store
from supabase_uploader import upload_decision

# ---- Logging setup ----
data_store.ensure_data_dirs()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(config.LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("main")


def run():
    """Execute one full cycle of the hydroponics control loop."""
    logger.info("=" * 60)
    logger.info("HYDROPONICS CYCLE START - %s", datetime.now().isoformat())
    logger.info("=" * 60)

    # --- Step 1: Read sensors ---
    logger.info("Step 1: Reading sensors...")
    try:
        from sensors import read_all_sensors
        readings = read_all_sensors()

        # Sanitize pH for Gemini / Safety
        # If pH is None (sensor error/out of hardware range) or extreme, default to 6.0
        # so Gemini sees a "perfect" value and takes no action.
        if readings.ph is None or not (config.PH_MIN <= readings.ph <= config.PH_MAX):
            logger.warning("pH value %s out of normal range. Defaulting to 6.0.", readings.ph)
            readings.ph = 6.0

        logger.info("Sensors: air=%.2f C, humidity=%.2f%%, water=%.2f C, pH=%.2f, TDS=%.0f ppm",
                     readings.air_temp_c or 0, readings.humidity_pct or 0,
                     readings.water_temp_c or 0, readings.ph or 0, readings.tds_ppm or 0)
    except Exception as e:
        logger.error("Sensor reading failed: %s", e)
        # Create a minimal readings object with Nones
        from sensors import SensorReadings
        readings = SensorReadings(timestamp=datetime.now().isoformat())
        # Also default pH here just in case
        readings.ph = 6.0

    # --- Step 2: Store sensor data in CSV ---
    logger.info("Step 2: Storing sensor data...")
    try:
        data_store.append_sensor_reading(readings)
        logger.info("Sensor data appended to %s", config.SENSOR_LOG_CSV)
    except Exception as e:
        logger.error("CSV storage failed: %s", e)

    # --- Step 3: Capture photo ---
    logger.info("Step 3: Capturing photo...")
    # Turn light ON for photo capture
    try:
        from actuators import set_light
        set_light("on")
    except Exception as e:
        logger.warning("Could not turn light on for photo: %s", e)

    photo_path = None
    try:
        from camera import capture_photo
        photo_path = capture_photo()
        if photo_path:
            logger.info("Photo captured: %s", photo_path)
        else:
            logger.warning("No photo available")
    except Exception as e:
        logger.error("Photo capture failed: %s", e)
        # Try fallback to latest photo
        try:
            photo_path = data_store.get_latest_photo()
            if photo_path:
                logger.info("Using fallback photo: %s", photo_path)
        except Exception:
            pass

    # --- Step 4: Load past decisions ---
    logger.info("Step 4: Loading past decisions...")
    try:
        past_decisions = data_store.load_past_decisions(config.PAST_DECISIONS_COUNT)
        logger.info("Loaded %d past decisions", len(past_decisions))
    except Exception as e:
        logger.error("Failed to load past decisions: %s", e)
        past_decisions = []

    # --- Step 5: Query Gemini ---
    logger.info("Step 5: Querying Gemini AI...")
    try:
        from gemini_client import get_gemini_decision
        decision = get_gemini_decision(readings, photo_path, past_decisions)
    except Exception as e:
        logger.error("Gemini query failed: %s", e)
        from gemini_client import SAFE_FALLBACK
        decision = SAFE_FALLBACK.copy()

    # --- Step 6: Store decision ---
    logger.info("Step 6: Storing decision...")
    try:
        data_store.save_decision(decision, readings)
        logger.info("Decision saved to %s", config.DECISIONS_JSON)
    except Exception as e:
        logger.error("Decision storage failed: %s", e)

    # --- Step 6b: Upload to Supabase ---
    logger.info("Step 6b: Uploading to Supabase...")
    try:
        upload_decision(decision, readings, photo_path)
    except Exception as e:
        logger.error("Supabase upload failed: %s", e)

    # --- Step 7: Execute actions ---
    logger.info("Step 7: Executing actions...")

    # Smart plugs
    try:
        from actuators import set_smart_plugs
        humidifier_state = decision.get("humidifier", "off")

        set_smart_plugs(
            light=decision.get("light", "on"),
            air_pump=decision.get("air_pump", "on"),
            humidifier=humidifier_state,
        )

        # If humidifier is ON, run it for 5 minutes then turn off
        if humidifier_state == "on":
            duration = config.HUMIDIFIER_DURATION_SECONDS
            logger.info("Humidifier is ON. Keeping it ON for %d seconds...", duration)
            time.sleep(duration)

            # Turn humidifier OFF, keep others in their decided state
            logger.info("Humidifier timer finished. Turning Humidifier OFF.")
            set_smart_plugs(
                light=decision.get("light", "on"),
                air_pump=decision.get("air_pump", "on"),
                humidifier="off",
            )
    except Exception as e:
        logger.error("Smart plug control failed: %s", e)

    # Dosing pump
    try:
        from actuators import run_dosing_pump
        run_dosing_pump(decision.get("ph_adjustment", "none"))
    except Exception as e:
        logger.error("Dosing pump failed: %s", e)

    # --- Step 8: Log reasoning ---
    logger.info("Step 8: Logging reasoning...")
    reasoning = decision.get("reasoning", {})

    logger.info("----- GEMINI DECISION SUMMARY -----")
    logger.info("Overall: %s", reasoning.get("overall", "N/A"))
    logger.info("Light (%s): %s", decision.get("light"), reasoning.get("light_reason", "N/A"))
    logger.info("Air Pump (%s): %s", decision.get("air_pump"), reasoning.get("air_pump_reason", "N/A"))
    logger.info("Humidifier (%s): %s", decision.get("humidifier"), reasoning.get("humidifier_reason", "N/A"))
    logger.info("pH Adjustment (%s): %s", decision.get("ph_adjustment"), reasoning.get("ph_reason", "N/A"))
    logger.info("Plant Health Score: %s/10", decision.get("plant_health_score", "N/A"))

    # Human intervention flag
    intervention = decision.get("human_intervention", {})
    if intervention.get("needed"):
        logger.warning("HUMAN INTERVENTION NEEDED: %s", intervention.get("message", ""))
        # Write alert file
        try:
            alert_path = os.path.join(config.DATA_DIR, "ALERT.txt")
            with open(alert_path, "w") as f:
                f.write(f"ALERT - {datetime.now().isoformat()}\n")
                f.write(f"{intervention.get('message', 'Check system manually.')}\n")
            logger.info("Alert written to %s", alert_path)
        except Exception as e:
            logger.error("Failed to write alert file: %s", e)

    # --- Step 9: Stream video to remote server ---
    logger.info("Step 9: Streaming video...")
    # Turn light ON for video streaming
    light_decision = decision.get("light", "on")
    try:
        from actuators import set_light
        set_light("on")
    except Exception as e:
        logger.warning("Could not turn light on for video: %s", e)

    try:
        from video_streamer import stream_video
        if stream_video():
            logger.info("Video streaming completed successfully")
        else:
            logger.warning("Video streaming did not complete (see warnings above)")
    except Exception as e:
        logger.error("Video streaming failed: %s", e)

    # Restore light to AI decision
    try:
        set_light(light_decision)
        logger.info("Light restored to AI decision: %s", light_decision)
    except Exception as e:
        logger.warning("Could not restore light state: %s", e)

    logger.info("=" * 60)
    logger.info("HYDROPONICS CYCLE COMPLETE")
    logger.info("=" * 60)


if __name__ == "__main__":
    run()
