"""
video_streamer.py - Video streaming module for the AI Hydroponics system.

Streams video from USB webcam to a remote PC for timelapse recording.
Designed to be called from main.py as Step 9 of the control loop.
"""

import logging
import socket
import struct
import time

import config

logger = logging.getLogger("video_streamer")

# Connection timeout in seconds
CONNECTION_TIMEOUT = 10


def stream_video() -> bool:
    """
    Stream video to the configured remote server.

    Returns:
        True if streaming completed successfully, False otherwise.
    """
    # Check if streaming is enabled
    if not config.VIDEO_STREAM_ENABLED:
        logger.info("Video streaming disabled (VIDEO_STREAM_ENABLED=False)")
        return True

    # Lazy import cv2 to avoid startup cost when streaming is disabled
    try:
        import cv2
    except ImportError:
        logger.warning("OpenCV (cv2) not installed, cannot stream video")
        return False

    server_ip = config.VIDEO_SERVER_IP
    server_port = config.VIDEO_SERVER_PORT
    duration_minutes = config.VIDEO_DURATION_MINUTES
    width = config.VIDEO_WIDTH
    height = config.VIDEO_HEIGHT
    hw_fps = config.VIDEO_HW_FPS
    jpeg_quality = config.VIDEO_JPEG_QUALITY

    # Create socket and connect
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.settimeout(CONNECTION_TIMEOUT)

    try:
        logger.info("Connecting to video server %s:%d...", server_ip, server_port)
        client_socket.connect((server_ip, server_port))
        logger.info("Connected to video server")
    except socket.timeout:
        logger.warning("Connection to video server timed out after %ds", CONNECTION_TIMEOUT)
        client_socket.close()
        return False
    except ConnectionRefusedError:
        logger.warning("Connection refused by video server %s:%d", server_ip, server_port)
        client_socket.close()
        return False
    except OSError as e:
        logger.warning("Failed to connect to video server: %s", e)
        client_socket.close()
        return False

    # Clear socket timeout for streaming
    client_socket.settimeout(None)

    # Open camera
    cap = cv2.VideoCapture(config.CAMERA_INDEX)

    if not cap.isOpened():
        logger.warning("Could not open webcam (index %d)", config.CAMERA_INDEX)
        client_socket.close()
        return False

    # Configure camera - MJPEG codec first to unlock high resolutions
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap.set(cv2.CAP_PROP_FPS, hw_fps)

    actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    actual_fps = cap.get(cv2.CAP_PROP_FPS)

    logger.info("Camera configured: %dx%d @ %.1f FPS (requested %dx%d @ %d FPS)",
                actual_width, actual_height, actual_fps, width, height, hw_fps)

    # Stream video
    start_time = time.time()
    duration_seconds = duration_minutes * 60
    frame_count = 0

    logger.info("Streaming for %.1f minutes...", duration_minutes)

    try:
        while (time.time() - start_time) < duration_seconds:
            ret, frame = cap.read()
            if not ret:
                logger.warning("Failed to capture frame, ending stream")
                break

            # Encode frame as JPEG
            result, frame_encoded = cv2.imencode(
                '.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_quality]
            )
            if not result:
                logger.warning("Failed to encode frame")
                continue

            data = frame_encoded.tobytes()

            # Send frame: 4-byte length prefix + data
            try:
                client_socket.sendall(struct.pack(">L", len(data)) + data)
                frame_count += 1
            except (BrokenPipeError, ConnectionResetError) as e:
                logger.warning("Connection lost during streaming: %s", e)
                break
            except OSError as e:
                logger.warning("Socket error during streaming: %s", e)
                break

    except KeyboardInterrupt:
        logger.info("Stream interrupted by user")
    except Exception as e:
        logger.error("Unexpected error during streaming: %s", e)
    finally:
        cap.release()
        client_socket.close()

    # Calculate stats
    elapsed = time.time() - start_time
    avg_fps = frame_count / elapsed if elapsed > 0 else 0

    logger.info("Stream finished: %d frames in %.1f seconds (avg %.2f FPS)",
                frame_count, elapsed, avg_fps)

    return frame_count > 0
