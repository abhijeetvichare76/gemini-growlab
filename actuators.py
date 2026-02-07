"""
actuators.py - Smart plug control + dosing pump control.

Smart plugs via tinytuya (local LAN).
Dosing pumps via Adafruit MotorKit (I2C, lazy-loaded).
"""

import json
import logging
import os
import time

import tinytuya

import config

logger = logging.getLogger(__name__)


def _load_device_info():
    """Load Tuya device ID and local key from devices.json."""
    if not os.path.exists(config.DEVICES_JSON):
        raise FileNotFoundError(f"devices.json not found at {config.DEVICES_JSON}")

    with open(config.DEVICES_JSON, "r") as f:
        devices = json.load(f)

    for dev in devices:
        if dev.get("name") == config.TUYA_DEVICE_NAME or \
           dev.get("product_name", "").strip() == config.TUYA_DEVICE_NAME:
            return dev.get("id"), dev.get("key")

    raise ValueError(f"Device '{config.TUYA_DEVICE_NAME}' not found in devices.json")


def set_light(state):
    """
    Set only the light plug state.

    Args:
        state: "on" or "off"

    Returns:
        True on success, False on failure.
    """
    try:
        device_id, local_key = _load_device_info()

        d = tinytuya.OutletDevice(device_id, config.TUYA_IP, local_key)
        d.set_version(config.TUYA_VERSION)

        d.set_status(state == "on", switch=int(config.DPS_LIGHT))
        logger.info("Set Light (DPS %s) to %s", config.DPS_LIGHT, "ON" if state == "on" else "OFF")
        return True

    except Exception as e:
        logger.error("Failed to set light: %s", e)
        return False


def set_smart_plugs(light, air_pump, humidifier):
    """
    Set smart plug states via tinytuya.

    Args:
        light: "on" or "off"
        air_pump: "on" or "off"
        humidifier: "on" or "off"
    """
    try:
        device_id, local_key = _load_device_info()

        d = tinytuya.OutletDevice(device_id, config.TUYA_IP, local_key)
        d.set_version(config.TUYA_VERSION)

        commands = [
            (config.DPS_LIGHT, light == "on", "Light"),
            (config.DPS_AIR_PUMP, air_pump == "on", "Air Pump"),
            (config.DPS_HUMIDIFIER, humidifier == "on", "Humidifier"),
        ]

        for dps, state, name in commands:
            try:
                d.set_status(state, switch=int(dps))
                logger.info("Set %s (DPS %s) to %s", name, dps, "ON" if state else "OFF")
            except Exception as e:
                logger.error("Failed to set %s: %s", name, e)
            time.sleep(config.TUYA_COMMAND_DELAY)

    except Exception as e:
        logger.error("Smart plug control failed: %s", e)
        logger.warning("Plugs retain their last state")


def run_dosing_pump(adjustment):
    """
    Run a dosing pump based on pH adjustment decision.

    Args:
        adjustment: "none", "ph_up", or "ph_down"

    Motor 1 = pH Down (FloraMicro)
    Motor 2 = pH Up (FloraGrow)
    MotorKit imported lazily to avoid I2C contention during sensor reads.
    """
    if adjustment == "none":
        logger.info("No pH adjustment needed")
        return

    # Lazy import to avoid I2C contention with ADS1115
    import board
    from adafruit_motorkit import MotorKit

    kit = None
    try:
        kit = MotorKit(i2c=board.I2C())

        if adjustment == "ph_down":
            pump = kit.motor1
            name = "pH Down (M1)"
        elif adjustment == "ph_up":
            pump = kit.motor2
            name = "pH Up (M2)"
        else:
            logger.warning("Unknown adjustment: %s, skipping", adjustment)
            return

        logger.info("Dispensing %s for %d seconds...", name, config.DOSING_DURATION)
        pump.throttle = 1.0
        time.sleep(config.DOSING_DURATION)
        pump.throttle = 0
        logger.info("%s dispensing complete", name)

    except Exception as e:
        logger.error("Dosing pump error: %s", e)
        # Emergency stop: zero both motors
        if kit is not None:
            try:
                kit.motor1.throttle = 0
                kit.motor2.throttle = 0
                logger.info("Emergency stop: both motors zeroed")
            except Exception:
                logger.error("Failed to emergency stop motors")
    finally:
        # Always ensure motors are off
        if kit is not None:
            try:
                kit.motor1.throttle = 0
                kit.motor2.throttle = 0
            except Exception:
                pass
