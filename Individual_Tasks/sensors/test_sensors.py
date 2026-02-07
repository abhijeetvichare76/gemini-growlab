import time
import board
import adafruit_dht
import glob
import os

# ==========================================
# CONFIGURATION
# ==========================================
# AIR SENSOR (DHT22) connected to GPIO 17 (Pin 11)
AIR_PIN = board.D17

# WATER SENSOR (DS18B20) uses 1-Wire protocol on GPIO 4
# No pin setup needed here, the system handles it via the file system.
BASE_DIR = '/sys/bus/w1/devices/'

# ==========================================
# SETUP
# ==========================================
print("Initializing sensors...")

# Setup Air Sensor
try:
    dht_device = adafruit_dht.DHT22(AIR_PIN)
    print("✅ Air Sensor (DHT22) initialized.")
except Exception as e:
    print(f"❌ Error initializing Air Sensor: {e}")

# Setup Water Sensor
device_folder = glob.glob(BASE_DIR + '28*')
water_sensor_path = None

if device_folder:
    water_sensor_path = device_folder[0] + '/w1_slave'
    print(f"✅ Water Sensor (DS18B20) found at: {device_folder[0]}")
else:
    print("❌ Water Sensor NOT found.")
    print("   -> Check if the Red/Black/Yellow wires are tight in the adapter.")
    print("   -> Check if 'dtoverlay=w1-gpio' is in /boot/firmware/config.txt")

print("\nStarting readings (Press CTRL+C to stop)...\n")
print(f"{'TIMESTAMP':<10} | {'AIR TEMP':<12} | {'HUMIDITY':<10} | {'WATER TEMP':<12}")
print("-" * 55)

# ==========================================
# MAIN LOOP
# ==========================================
while True:
    try:
        # --- READ AIR SENSOR ---
        try:
            # DHT22 requires a catch for frequent read errors
            air_temp_c = dht_device.temperature
            air_humid = dht_device.humidity
            
            if air_temp_c is not None:
                air_str = f"{air_temp_c:.1f}°C"
                hum_str = f"{air_humid:.1f}%"
            else:
                air_str = "Error"
                hum_str = "Error"
        except RuntimeError:
            # This is normal for DHT sensors, just ignore and retry next loop
            air_str = "Retrying..."
            hum_str = "..."

        # --- READ WATER SENSOR ---
        water_str = "No Sensor"
        if water_sensor_path:
            try:
                with open(water_sensor_path, 'r') as f:
                    lines = f.readlines()
                # The sensor returns "YES" if the read was good
                if lines[0].strip()[-3:] == 'YES':
                    equals_pos = lines[1].find('t=')
                    if equals_pos != -1:
                        temp_string = lines[1][equals_pos+2:]
                        water_temp_c = float(temp_string) / 1000.0
                        water_str = f"{water_temp_c:.1f}°C"
            except Exception:
                water_str = "Error"

        # --- PRINT RESULT ---
        curr_time = time.strftime("%H:%M:%S")
        print(f"{curr_time:<10} | {air_str:<12} | {hum_str:<10} | {water_str:<12}")

    except KeyboardInterrupt:
        print("\nExiting...")
        dht_device.exit()
        break
    except Exception as e:
        print(f"Unexpected error: {e}")

    # DHT22 requires at least 2 seconds between reads
    time.sleep(5.0)