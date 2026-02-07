import tinytuya
import json
import os

# Configuration from JSON files
DEVICES_FILE = 'devices.json'
# We still need the IP as it's not in the JSON yet, but we'll try to find ID/Key
IP_ADDRESS = '10.0.0.224'

def load_device_info(target_name="Smart Power Strip"):
    if not os.path.exists(DEVICES_FILE):
        print(f"Error: {DEVICES_FILE} not found.")
        return None, None

    with open(DEVICES_FILE, 'r') as f:
        devices = json.load(f)
    
    for dev in devices:
        if dev.get('name') == target_name or dev.get('product_name') == target_name:
            return dev.get('id'), dev.get('key')
    
    return None, None

def main():
    print(f"--- Gosund Smart Power Strip Connection Test ---")
    
    device_id, local_key = load_device_info()
    
    if not device_id or not local_key:
        print("Error: Could not find device info in devices.json")
        return

    print(f"Loaded from JSON: ID={device_id}, Key=****")
    print(f"Using IP Address: {IP_ADDRESS}")
    
    # Set up the connection
    d = tinytuya.OutletDevice(device_id, IP_ADDRESS, local_key)
    d.set_version(3.3)

    # Get status
    print(f"\nFetching device status...")
    data = d.status()
    
    if 'Error' in data:
        print(f"Error connecting to device: {data['Error']}")
        print("Note: If you get 'Connection reset', try running the script again.")
        return
        
    print("Device Status:", json.dumps(data, indent=4))

    # 4. Toggle Test (Optional - let's toggle Switch 1 as a test)
    print("\n--- Toggle Test (Switch 1) ---")
    current_state = data['dps']['2']
    new_state = not current_state
    print(f"Current State of Switch 1: {'ON' if current_state else 'OFF'}")
    print(f"Toggling Switch 1 to: {'ON' if new_state else 'OFF'}...")
    
    d.set_status(new_state, 2)
    
    # 5. Verify
    print("Verifying new status...")
    new_data = d.status()
    if 'dps' in new_data:
        print(f"Confirmed! Switch 1 is now: {'ON' if new_data['dps']['1'] else 'OFF'}")
    else:
        print("Could not verify status change.")

    print("\nSuccessfully connected and controlled the Smart Power Strip!")

if __name__ == "__main__":
    main()
