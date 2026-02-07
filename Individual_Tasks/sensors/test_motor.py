import time
import board
from adafruit_motorkit import MotorKit

# Initialize the Blue Motor Shield
# It uses the I2C bus (same as your sensors!)
try:
    kit = MotorKit(i2c=board.I2C())
    print("✅ Motor Shield Found!")
except Exception as e:
    print(f"❌ Error finding Motor Shield: {e}")
    print("   (Check SDA/SCL wires and ensure 12V power is plugged in)")
    exit()

print("\nStarting Pump Test (M1)...")

try:
    print(">>> Pump ON (50% Speed)")
    kit.motor1.throttle = 0.5
    time.sleep(2)

    print(">>> Pump ON (Full Speed)")
    kit.motor1.throttle = 1.0
    time.sleep(2)

    print(">>> Pump STOP")
    kit.motor1.throttle = 0
    time.sleep(1)

    # Peristaltic pumps can go backwards too!
    print(">>> Pump REVERSE")
    kit.motor1.throttle = -1.0
    time.sleep(2)

    print(">>> STOP")
    kit.motor1.throttle = 0

except KeyboardInterrupt:
    kit.motor1.throttle = 0
    print("Stopped.")