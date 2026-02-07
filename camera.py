"""
camera.py - Webcam capture wrapper.
Saves timestamped photos to data/photos/.
"""

import logging
import os
import time
from datetime import datetime

import cv2

import config
import data_store

logger = logging.getLogger(__name__)


def capture_photo():
    """
    Capture a single photo from the USB webcam.
    Warms up 10 frames, captures final frame.

    Returns:
        str filepath of saved photo, or None on failure.
        Falls back to latest existing photo if capture fails.
    """
    data_store.ensure_data_dirs()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"webcam_{timestamp}.jpg"
    filepath = os.path.join(config.PHOTOS_DIR, filename)

    logger.info("Initializing camera (index %d)...", config.CAMERA_INDEX)
    cap = cv2.VideoCapture(config.CAMERA_INDEX)

    if not cap.isOpened():
        logger.warning("Could not open webcam, falling back to latest photo")
        return data_store.get_latest_photo()

    try:
        # Warm up for auto-exposure adjustment
        logger.debug("Warming up camera (%d frames)...", config.CAMERA_WARMUP_FRAMES)
        for _ in range(config.CAMERA_WARMUP_FRAMES):
            cap.read()
            time.sleep(0.1)

        ret, frame = cap.read()
        if ret:
            cv2.imwrite(filepath, frame)
            logger.info("Photo saved: %s", filepath)
            return filepath
        else:
            logger.warning("Failed to capture frame, falling back to latest photo")
            return data_store.get_latest_photo()
    finally:
        cap.release()
