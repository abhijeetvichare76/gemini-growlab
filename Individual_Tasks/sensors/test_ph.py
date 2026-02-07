import time
import board
import busio
from adafruit_ads1x15.ads1115 import ADS1115
from adafruit_ads1x15.analog_in import AnalogIn

# --- SETUP ---
try:
    i2c = busio.I2C(board.SCL, board.SDA)
    ads = ADS1115(i2c)
    
    # Channel 0 = TDS Sensor
    tds_channel = AnalogIn(ads, 0)
    
    # Channel 1 = pH Sensor
    ph_channel = AnalogIn(ads, 1)
    
    print("✅ Sensors Initialized")
except Exception as e:
    print(f"❌ Initialization Error: {e}")

print("\nStarting Water Monitor... (Press CTRL+C to stop)")
print(f"{'VOLTS (pH)':<12} | {'Est. pH':<10} | {'VOLTS (TDS)':<12} | {'Est. TDS'}")
print("-" * 60)

while True:
    try:
        # --- READ TDS ---
        tds_volt = tds_channel.voltage
        # Generic TDS Formula
        tds_val = (133.42 * tds_volt**3 - 255.86 * tds_volt**2 + 857.39 * tds_volt) * 0.5

        # --- READ pH ---
        ph_volt = ph_channel.voltage
        
        # pH CALIBRATION NOTE:
        # This formula assumes the sensor is perfectly centered (2.5V = pH 7).
        # You will likely need to adjust the 'calibration_value' later.
        # Standard slope is usually around -5.70.
        
        slope = -5.70  # Sensitivity
        calibration_value = 21.34 # Offset (This changes per sensor!)
        
        # Simple Formula: pH = 7 + ((2.5 - Voltage) / 0.18)
        # Let's use a linear map for now:
        ph_val = 7 + ((2.5 - ph_volt) * 3.5) 

        print(f"{ph_volt:.4f} V   | {ph_val:.2f} pH     | {tds_volt:.4f} V   | {tds_val:.0f} ppm")
        
    except Exception as e:
        print(f"Error: {e}")
        
    time.sleep(5)