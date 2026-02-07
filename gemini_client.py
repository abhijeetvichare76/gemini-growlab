"""
gemini_client.py - Prompt builder, Gemini API call, and JSON response parsing.

Uses native JSON mode via response_mime_type="application/json" + response schema.
Falls back to safe defaults on API failure.
"""

import json
import logging
import os
from datetime import datetime

from dotenv import load_dotenv
from google import genai
from google.genai import types

import config

logger = logging.getLogger(__name__)

# Response schema enforced via Gemini JSON mode
RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "light": {"type": "string", "enum": ["on", "off"]},
        "air_pump": {"type": "string", "enum": ["on", "off"]},
        "humidifier": {"type": "string", "enum": ["on", "off"]},
        "ph_adjustment": {"type": "string", "enum": ["none", "ph_up", "ph_down"]},
        "reasoning": {
            "type": "object",
            "properties": {
                "overall": {"type": "string"},
                "light_reason": {"type": "string"},
                "air_pump_reason": {"type": "string"},
                "humidifier_reason": {"type": "string"},
                "ph_reason": {"type": "string"},
            },
            "required": ["overall", "light_reason", "air_pump_reason",
                         "humidifier_reason", "ph_reason"],
        },
        "plant_health_score": {"type": "integer"},
        "human_intervention": {
            "type": "object",
            "properties": {
                "needed": {"type": "boolean"},
                "message": {"type": "string"},
            },
            "required": ["needed", "message"],
        },
    },
    "required": ["light", "air_pump", "humidifier", "ph_adjustment",
                  "reasoning", "plant_health_score", "human_intervention"],
}

SAFE_FALLBACK = {
    "light": "on",
    "air_pump": "on",
    "humidifier": "off",
    "ph_adjustment": "none",
    "reasoning": {
        "overall": "FALLBACK: Gemini API unavailable. Using safe defaults.",
        "light_reason": "Lights ON as safe default to maintain photoperiod.",
        "air_pump_reason": "Air pump ON as safe default for oxygenation.",
        "humidifier_reason": "Humidifier OFF as safe default.",
        "ph_reason": "No pH adjustment as safe default to avoid overdosing.",
    },
    "plant_health_score": 5,
    "human_intervention": {
        "needed": True,
        "message": "Gemini API failed. System running on safe defaults. Please check manually.",
    },
}


def _init_client():
    """Initialize the Vertex AI Gemini client."""
    load_dotenv(config.ENV_FILE, override=True)

    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if creds_path and not os.path.isabs(creds_path):
        creds_path = os.path.join(config.PROJECT_ROOT, creds_path)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_path

    project_id = os.getenv("GCP_PROJECT_ID")
    location = os.getenv("GCP_LOCATION", "global")

    if not project_id:
        raise ValueError("GCP_PROJECT_ID not found in .env file")

    return genai.Client(vertexai=True, project=project_id, location=location)


def _format_sensor_value(value, unit=""):
    """Format a sensor value for the prompt, showing N/A if None."""
    if value is None:
        return "N/A (sensor error)"
    return f"{value}{unit}"


def _build_prompt(readings, past_decisions):
    """
    Build the text prompt for Gemini including:
    - Basil DWC context and ideal ranges
    - Current time for light cycle awareness
    - Sensor data
    - Past 3 decisions with per-actuator reasoning
    """
    now = datetime.now()
    current_hour = now.hour

    # Determine if we're in the light period
    in_light_period = config.LIGHTS_ON_HOUR <= current_hour < config.LIGHTS_OFF_HOUR

    prompt = f"""You are an AI hydroponics controller managing a basil plant in a Deep Water Culture (DWC) system inside a grow tent.

## Current Conditions
- **Date/Time**: {now.strftime('%Y-%m-%d %H:%M')}
- **Light Schedule**: {config.LIGHTS_ON_HOUR}:00 - {config.LIGHTS_OFF_HOUR}:00 (16h on / 8h off)
- **Currently**: {'DAYTIME (lights should be ON)' if in_light_period else 'NIGHTTIME (lights should be OFF)'}

## Sensor Readings
- Air Temperature: {_format_sensor_value(readings.air_temp_c, ' C')}
- Humidity: {_format_sensor_value(readings.humidity_pct, '%')}
- Water Temperature: {_format_sensor_value(readings.water_temp_c, ' C')}
- pH: {_format_sensor_value(readings.ph)}
- TDS: {_format_sensor_value(readings.tds_ppm, ' ppm')}

## Ideal Ranges for Basil (DWC)
- Air Temperature: {config.IDEAL_RANGES['air_temp_c']['min']}-{config.IDEAL_RANGES['air_temp_c']['max']} C
- Humidity: {config.IDEAL_RANGES['humidity_pct']['min']}-{config.IDEAL_RANGES['humidity_pct']['max']}%
- Water Temperature: {config.IDEAL_RANGES['water_temp_c']['min']}-{config.IDEAL_RANGES['water_temp_c']['max']} C
- pH: {config.IDEAL_RANGES['ph']['min']}-{config.IDEAL_RANGES['ph']['max']}
- TDS: {config.IDEAL_RANGES['tds_ppm']['min']}-{config.IDEAL_RANGES['tds_ppm']['max']} ppm

## Available Controls
1. **Light** (on/off) - VIPARSPECTRA P1000 LED grow light
2. **Air Pump** (on/off) - Aerates the DWC reservoir
3. **Humidifier** (on/off) - Increases tent humidity
4. **pH Adjustment** (none/ph_up/ph_down) - Peristaltic dosing pumps. ONLY adjust if pH is clearly outside the ideal range. Small deviations are normal and should NOT trigger dosing. Be conservative.

## Decision Guidelines
- Follow the 16h/8h light schedule based on current time
- Air pump should generally stay ON for oxygenation unless there's a specific reason to turn it off
- Only activate humidifier if humidity is significantly below range
- pH adjustment: ONLY dose if pH is more than 0.5 outside the ideal range. Never dose when pH sensor reads N/A
- If any sensor reads N/A, note it in reasoning and be conservative with that parameter
- Explain EACH actuator decision individually in the reasoning fields
"""

    if past_decisions:
        prompt += "\n## Past Decisions (most recent last)\n"
        for i, dec in enumerate(past_decisions, 1):
            ts = dec.get("timestamp", "unknown")
            snapshot = dec.get("sensor_snapshot", {})
            reasoning = dec.get("reasoning", {})
            prompt += f"\n### Decision {i} ({ts})\n"
            prompt += f"- Sensors: pH={snapshot.get('ph', 'N/A')}, TDS={snapshot.get('tds_ppm', 'N/A')}, "
            prompt += f"Air={snapshot.get('air_temp_c', 'N/A')}C, Water={snapshot.get('water_temp_c', 'N/A')}C, "
            prompt += f"Humidity={snapshot.get('humidity_pct', 'N/A')}%\n"
            prompt += f"- Actions: light={dec.get('light')}, air_pump={dec.get('air_pump')}, "
            prompt += f"humidifier={dec.get('humidifier')}, ph_adjustment={dec.get('ph_adjustment')}\n"
            prompt += f"- Overall reasoning: {reasoning.get('overall', 'N/A')}\n"
            prompt += f"- Light reason: {reasoning.get('light_reason', 'N/A')}\n"
            prompt += f"- Air pump reason: {reasoning.get('air_pump_reason', 'N/A')}\n"
            prompt += f"- Humidifier reason: {reasoning.get('humidifier_reason', 'N/A')}\n"
            prompt += f"- pH reason: {reasoning.get('ph_reason', 'N/A')}\n"

    prompt += """
## Photo
A photo of the plant is attached. Consider visible plant health in your assessment.

## Response
Analyze the current conditions and photo, then decide what actions to take. Explain each decision individually.
"""

    return prompt


def get_gemini_decision(readings, photo_path=None, past_decisions=None):
    """
    Query Gemini with sensor data, photo, and history. Returns structured decision dict.

    Args:
        readings: SensorReadings dataclass
        photo_path: Path to current plant photo (optional)
        past_decisions: List of past decision dicts

    Returns:
        dict matching RESPONSE_SCHEMA
    """
    if past_decisions is None:
        past_decisions = []

    try:
        client = _init_client()
        prompt_text = _build_prompt(readings, past_decisions)

        # Build content parts
        contents = []

        # Add photo if available
        if photo_path and os.path.exists(photo_path):
            with open(photo_path, "rb") as f:
                image_bytes = f.read()
            contents.append(
                types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
            )
            logger.info("Attached photo: %s", photo_path)
        else:
            logger.warning("No photo available for Gemini request")

        contents.append(prompt_text)

        # Call Gemini with JSON mode
        response = client.models.generate_content(
            model=config.GEMINI_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=RESPONSE_SCHEMA,
                temperature=config.GEMINI_TEMPERATURE,
            ),
        )

        decision = json.loads(response.text)
        logger.info("Gemini decision received: light=%s, air_pump=%s, humidifier=%s, ph=%s",
                     decision.get("light"), decision.get("air_pump"),
                     decision.get("humidifier"), decision.get("ph_adjustment"))
        return decision

    except Exception as e:
        logger.error("Gemini API failed: %s", e)
        logger.info("Using safe fallback decision")
        return SAFE_FALLBACK.copy()
