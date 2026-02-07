import time
import board
from adafruit_motorkit import MotorKit

# Initialize the Board
try:
    kit = MotorKit(i2c=board.I2C())
    print("✅ Motor Shield Connected")
except ValueError:
    print("❌ Connection Error: Check your SDA/SCL wires!")
    exit()

# --- CONFIGURATION ---
# Define which pump is which
pump_flora_micro = kit.motor1
pump_flora_grow  = kit.motor2

def dispense_liquid(pump, name, duration_seconds):
    print(f" -> Dispensing {name} for {duration_seconds} seconds...")
    
    # Turn Pump ON (Full Speed)
    pump.throttle = 1.0
    
    # Wait for the specific time
    time.sleep(duration_seconds)
    
    # Turn Pump OFF
    pump.throttle = 0
    print(f" -> {name} DONE.")

# --- MAIN TEST ---
print("\n--- HYDROPONICS DOSING TEST ---")
print("Make sure your OUTLET tubes are in a measuring cup!")
print("Starting in 3 seconds...")
time.sleep(3)

try:
    # Test Pump 1 (e.g., FloraMicro)
    dispense_liquid(pump_flora_micro, "FloraMicro (M1)", 2.0)
    
    time.sleep(2) # Pause between pumps
    
    # Test Pump 2 (e.g., FloraGrow)
    # dispense_liquid(pump_flora_grow, "FloraGrow (M2)", 5.0)

    print("\n✅ Test Complete. All pumps OFF.")

except KeyboardInterrupt:
    print("\nSTOPPING!")
    kit.motor1.throttle = 0
    kit.motor2.throttle = 0