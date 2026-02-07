"""
sensors.py - Unified sensor reading for DHT22, DS18B20, ADS1115 (pH/TDS).

Timing protocol:
  DHT22 -> 5s gap -> DS18B20 -> 5s gap -> pH -> 150ms -> TDS
  Each sensor: 5 reads with 2s gaps, discard first 2, average last 3
  Total wall time: ~65 seconds
"""

import glob
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import config

logger = logging.getLogger(__name__)


@dataclass
class SensorReadings:
    """Container for all sensor readings from a single sweep."""
    timestamp: str
    air_temp_c: Optional[float] = None
    humidity_pct: Optional[float] = None
    water_temp_c: Optional[float] = None
    ph: Optional[float] = None
    tds_ppm: Optional[float] = None


def _validate(value, vmin, vmax):
    """Return value if within range, else None."""
    if value is None:
        return None
    if vmin <= value <= vmax:
        return round(value, 2)
    logger.warning("Value %.2f out of range [%.2f, %.2f], discarding", value, vmin, vmax)
    return None


def _average_valid(values):
    """Average a list of values, ignoring Nones."""
    valid = [v for v in values if v is not None]
    if not valid:
        return None
    return sum(valid) / len(valid)


def _read_dht22():
    """
    Read air temperature and humidity from DHT22.
    Takes 5 readings with 2s gaps, discards first 2, averages last 3.

    Returns:
        (air_temp_c, humidity_pct) tuple, either may be None
    """
    import board
    import adafruit_dht

    pin = getattr(board, f"D{config.DHT22_PIN}")
    dht = adafruit_dht.DHT22(pin)

    temps = []
    humids = []

    try:
        for i in range(config.READINGS_PER_SENSOR):
            try:
                t = dht.temperature
                h = dht.humidity
                temps.append(t)
                humids.append(h)
                logger.debug("DHT22 read %d: temp=%.1f, humidity=%.1f", i, t or 0, h or 0)
            except RuntimeError as e:
                # RuntimeError is expected and common for DHT sensors
                logger.debug("DHT22 read %d: RuntimeError: %s", i, e)
                temps.append(None)
                humids.append(None)

            if i < config.READINGS_PER_SENSOR - 1:
                time.sleep(config.INTRA_SENSOR_DELAY)
    finally:
        dht.exit()

    # Discard first READINGS_TO_DISCARD, average the rest
    kept_temps = temps[config.READINGS_TO_DISCARD:]
    kept_humids = humids[config.READINGS_TO_DISCARD:]

    air_temp = _validate(
        _average_valid(kept_temps),
        config.AIR_TEMP_MIN, config.AIR_TEMP_MAX
    )
    humidity = _validate(
        _average_valid(kept_humids),
        config.HUMIDITY_MIN, config.HUMIDITY_MAX
    )

    return air_temp, humidity


def _read_ds18b20():
    """
    Read water temperature from DS18B20 via 1-Wire.
    Takes 5 readings with 2s gaps, discards first 2, averages last 3.

    Returns:
        water_temp_c or None
    """
    device_folders = glob.glob(config.DS18B20_BASE_DIR + "28*")
    if not device_folders:
        logger.warning("DS18B20 sensor not found")
        return None

    sensor_path = device_folders[0] + "/w1_slave"
    temps = []

    for i in range(config.READINGS_PER_SENSOR):
        try:
            with open(sensor_path, "r") as f:
                lines = f.readlines()

            if lines[0].strip().endswith("YES"):
                equals_pos = lines[1].find("t=")
                if equals_pos != -1:
                    temp_string = lines[1][equals_pos + 2:]
                    temp_c = float(temp_string) / 1000.0
                    temps.append(temp_c)
                    logger.debug("DS18B20 read %d: %.2f C", i, temp_c)
                else:
                    temps.append(None)
            else:
                temps.append(None)
        except Exception as e:
            logger.debug("DS18B20 read %d error: %s", i, e)
            temps.append(None)

        if i < config.READINGS_PER_SENSOR - 1:
            time.sleep(config.INTRA_SENSOR_DELAY)

    kept = temps[config.READINGS_TO_DISCARD:]
    return _validate(
        _average_valid(kept),
        config.WATER_TEMP_MIN, config.WATER_TEMP_MAX
    )


def _read_ph_tds():
    """
    Read pH and TDS from ADS1115 ADC.
    pH on channel 1, TDS on channel 0.
    ADS1115 initialized once, shared between reads.
    Takes 5 readings each with 2s gaps, discards first 2, averages last 3.

    Returns:
        (ph, tds_ppm) tuple, either may be None
    """
    import board
    import busio
    from adafruit_ads1x15.ads1115 import ADS1115
    from adafruit_ads1x15.analog_in import AnalogIn

    i2c = busio.I2C(board.SCL, board.SDA)
    ads = ADS1115(i2c)

    ph_channel = AnalogIn(ads, config.ADS1115_PH_CHANNEL)
    tds_channel = AnalogIn(ads, config.ADS1115_TDS_CHANNEL)

    ph_values = []
    tds_values = []

    for i in range(config.READINGS_PER_SENSOR):
        try:
            # Read pH
            ph_volt = ph_channel.voltage
            ph_val = 7 + ((2.5 - ph_volt) * 3.5)
            ph_values.append(ph_val)
            logger.debug("pH read %d: voltage=%.4f, pH=%.2f", i, ph_volt, ph_val)
        except Exception as e:
            logger.debug("pH read %d error: %s", i, e)
            ph_values.append(None)

        time.sleep(config.PH_TDS_DELAY)

        try:
            # Read TDS
            tds_volt = tds_channel.voltage
            tds_val = (133.42 * tds_volt**3 - 255.86 * tds_volt**2 + 857.39 * tds_volt) * 0.5
            tds_values.append(tds_val)
            logger.debug("TDS read %d: voltage=%.4f, TDS=%.0f ppm", i, tds_volt, tds_val)
        except Exception as e:
            logger.debug("TDS read %d error: %s", i, e)
            tds_values.append(None)

        if i < config.READINGS_PER_SENSOR - 1:
            time.sleep(config.INTRA_SENSOR_DELAY)

    kept_ph = ph_values[config.READINGS_TO_DISCARD:]
    kept_tds = tds_values[config.READINGS_TO_DISCARD:]

    ph = _validate(_average_valid(kept_ph), config.PH_MIN, config.PH_MAX)
    tds = _validate(_average_valid(kept_tds), config.TDS_MIN, config.TDS_MAX)

    return ph, tds


def read_all_sensors():
    """
    Master function: read all sensors following the timing protocol.

    Order: DHT22 -> 5s -> DS18B20 -> 5s -> pH -> 150ms -> TDS
    Each sensor: 5 reads, 2s apart, discard first 2, average last 3.

    Returns:
        SensorReadings dataclass
    """
    readings = SensorReadings(timestamp=datetime.now().isoformat())

    # --- DHT22 (air temp + humidity) ---
    try:
        logger.info("Reading DHT22 (air temp / humidity)...")
        readings.air_temp_c, readings.humidity_pct = _read_dht22()
        logger.info("DHT22: air_temp=%.2f, humidity=%.2f",
                     readings.air_temp_c or 0, readings.humidity_pct or 0)
    except Exception as e:
        logger.error("DHT22 failed: %s", e)

    time.sleep(config.INTER_SENSOR_DELAY)

    # --- DS18B20 (water temp) ---
    try:
        logger.info("Reading DS18B20 (water temp)...")
        readings.water_temp_c = _read_ds18b20()
        logger.info("DS18B20: water_temp=%.2f", readings.water_temp_c or 0)
    except Exception as e:
        logger.error("DS18B20 failed: %s", e)

    time.sleep(config.INTER_SENSOR_DELAY)

    # --- pH + TDS via ADS1115 ---
    try:
        logger.info("Reading pH and TDS via ADS1115...")
        readings.ph, readings.tds_ppm = _read_ph_tds()
        logger.info("ADS1115: pH=%.2f, TDS=%.0f ppm",
                     readings.ph or 0, readings.tds_ppm or 0)
    except Exception as e:
        logger.error("pH/TDS failed: %s", e)

    return readings
