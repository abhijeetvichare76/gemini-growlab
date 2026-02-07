import time
import board
import busio
from adafruit_ads1x15.ads1115 import ADS1115
from adafruit_ads1x15.analog_in import AnalogIn

# Initialize I2C bus
try:
    i2c = busio.I2C(board.SCL, board.SDA)
    print("✅ I2C Bus initialized")
except Exception as e:
    print(f"❌ I2C Error: {e}")

# Initialize the ADS1115
try:
    ads = ADS1115(i2c)
    print("✅ ADS1115 Board Object Created")
    
    # We use channel 0 (P0) for the TDS sensor
    # We use the number 0 directly to avoid library version errors
    tds_channel = AnalogIn(ads, 0)
    print("✅ Sensor Channel Set")

except Exception as e:
    print(f"❌ Setup Error: {e}")
    print("   (If this fails, check your soldering on the SDA/SCL pins)")

print("\nReading TDS Sensor... (Press CTRL+C to stop)")
print("-" * 30)

while True:
    try:
        # Read voltage
        voltage = tds_channel.voltage
        
        # Calculate TDS (Generic estimation)
        tds_value = (133.42 * voltage**3 - 255.86 * voltage**2 + 857.39 * voltage) * 0.5
        
        print(f"Voltage: {voltage:.4f} V  |  Est. TDS: {tds_value:.0f} ppm")
    except OSError:
        print("❌ Read Error: Check Soldering!")
    except Exception as e:
        print(f"Error: {e}")
        
    time.sleep(1)