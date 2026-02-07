import cv2
import socket
import struct
import time
import argparse


def stream_video(server_ip, server_port, duration_minutes, width, height, fps, jpeg_quality, hw_fps):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    try:
        print(f"Connecting to {server_ip}:{server_port}...")
        client_socket.connect((server_ip, server_port))
        print("Connected.")
    except Exception as e:
        print(f"Connection failed: {e}")
        return

    cap = cv2.VideoCapture(0)
    
    # Configure video properties
    # IMPORTANT: Must set MJPEG codec FIRST to unlock high resolutions/FPS on USB
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
    
    # Note: The camera might not support the exact requested values, 
    # OpenCv will select the closest supported mode.
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    # Request standard hardware FPS (e.g. 30) to ensure resolution is accepted
    cap.set(cv2.CAP_PROP_FPS, hw_fps)
    
    actual_width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    actual_height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    actual_fps = cap.get(cv2.CAP_PROP_FPS)
    
    print(f"Streaming at {actual_width}x{actual_height} @ {actual_fps} FPS (Requested HW: {width}x{height} @ {hw_fps} FPS)")
    print(f"Transmission rate limited to: {fps} FPS")

    if not cap.isOpened():
        print("Error: Could not open webcam.")
        client_socket.close()
        return

    start_time = time.time()
    duration_seconds = duration_minutes * 60
    
    print(f"Streaming for {duration_minutes} minutes...")

    try:
        while (time.time() - start_time) < duration_seconds:
            # Capture frame (blocking wait for next frame from camera)
            ret, frame = cap.read()
            if not ret:
                print("Error: Failed to capture frame.")
                break
            
            # Encode frame as JPEG
            result, frame_encoded = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_quality])
            data = frame_encoded.tobytes()
            
            # Send message
            client_socket.sendall(struct.pack(">L", len(data)) + data)
            
            # No manual sleep needed if HW FPS matches target FPS.
            # cap.read() will effectively sleep for 1/FPS seconds.

    except KeyboardInterrupt:
        print("Stopping stream...")
    except Exception as e:
        print(f"Error during streaming: {e}")
    finally:
        cap.release()
        client_socket.close()
        print("Stream finished.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stream webcam video to remote PC (Timelapse Mode).")
    parser.add_argument("server_ip", nargs='?', default="10.0.0.239", help="IP address of the receiving PC (default: 10.0.0.239)")
    parser.add_argument("--port", type=int, default=8000, help="Port to connect to")
    parser.add_argument("--duration", type=float, default=5.0, help="Duration in minutes (default: 5.0)")
    parser.add_argument("--width", type=int, default=1920, help="Frame width (default: 1920)")
    parser.add_argument("--height", type=int, default=1080, help="Frame height (default: 1080)")
    parser.add_argument("--fps", type=int, default=5, help="Target Transmission FPS (default: 5)")
    parser.add_argument("--hw-fps", type=int, default=5, help="Hardware Capture FPS (default: 5)")
    parser.add_argument("--quality", type=int, default=95, help="JPEG Quality 0-100 (default: 95)")
    
    args = parser.parse_args()
    
    stream_video(args.server_ip, args.port, args.duration, args.width, args.height, args.fps, args.quality, args.hw_fps)
