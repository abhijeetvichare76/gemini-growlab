#!/usr/bin/env python3
import cv2
import os
import time
import datetime
import argparse

# Constants
# Most USB webcams default to index 0. If you have multiple, try 1, 2, etc.
CAMERA_INDEX = 0
# Directory to save snapshots
SNAPSHOT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "snapshots")

def log(message):
    """Print with timestamp for monitoring."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def capture_photo(filename=None):
    """Capture a single photo from the USB webcam."""
    if not os.path.exists(SNAPSHOT_DIR):
        os.makedirs(SNAPSHOT_DIR)
        log(f"Created directory: {SNAPSHOT_DIR}")

    if filename is None:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"webcam_{timestamp}.jpg"
    
    filepath = os.path.join(SNAPSHOT_DIR, filename)

    log(f"Initializing camera (index {CAMERA_INDEX})...")
    cap = cv2.VideoCapture(CAMERA_INDEX)

    if not cap.isOpened():
        log("Error: Could not open webcam. Is it plugged in?")
        return None

    try:
        # USB Webcams often need a "warm up" period for auto-exposure to adjust.
        # We capture a few frames and discard them.
        log("Warming up sensor...")
        for i in range(10):
            cap.read()
            time.sleep(0.1)

        # Capture the actual frame
        ret, frame = cap.read()
        if ret:
            # Save the frame
            cv2.imwrite(filepath, frame)
            log(f"Photo saved successfully: {filepath}")
            return filepath
        else:
            log("Error: Failed to capture frame.")
            return None
    finally:
        # Always release the camera resource
        cap.release()

def main():
    parser = argparse.ArgumentParser(description="Capture photo from USB webcam.")
    parser.add_argument("--name", help="Custom name for the output file.")
    args = parser.parse_args()

    capture_photo(args.name)

if __name__ == "__main__":
    main()
