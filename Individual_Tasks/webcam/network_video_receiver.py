import cv2
import socket
import struct
import os
import datetime
import argparse
import sys
import gc

# Global debug flag
DEBUG = False

def log(message):
    if DEBUG:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}")

def handle_client(conn, addr, output_dir):
    log(f"Connection from: {addr}")
    out = None
    display_enabled = True
    
    try:
        data = b""
        payload_size = struct.calcsize(">L")
        
        while True:
            # Retrieve message size
            while len(data) < payload_size:
                packet = conn.recv(4096)
                if not packet: 
                    return # Connection closed
                data += packet
            
            packed_msg_size = data[:payload_size]
            data = data[payload_size:]
            msg_size = struct.unpack(">L", packed_msg_size)[0]
            
            # Retrieve frame data
            while len(data) < msg_size:
                packet = conn.recv(4096)
                if not packet:
                    return # Connection closed mid-frame
                data += packet
                
            frame_data = data[:msg_size]
            data = data[msg_size:]
            
            # Decode frame
            import numpy as np
            frame = cv2.imdecode(np.frombuffer(frame_data, dtype=np.uint8), cv2.IMREAD_COLOR)
            
            if frame is None:
                continue

            # Initialize video writer once we have the frame dimensions
            if out is None:
                height, width, _ = frame.shape
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = os.path.join(output_dir, f"remote_recording_{timestamp}.avi")
                # MJPG is usually safe for Windows/Linux interoperability in OpenCV
                fourcc = cv2.VideoWriter_fourcc(*'MJPG') 
                out = cv2.VideoWriter(filename, fourcc, 20.0, (width, height))
                log(f"Recording started: {filename}")
                if not DEBUG:
                    print(f"Recording to: {filename}")

            out.write(frame)
            
            # Optional: Display the stream
            if display_enabled:
                try:
                    cv2.imshow('Remote Camera', frame)
                    if cv2.waitKey(1) == ord('q'):
                        log("Stop signal received from GUI.")
                        break
                except Exception as e:
                    # Only log this once per connection to avoid spam
                    if display_enabled:
                       log(f"GUI display warning: {e}. Disabling preview.")
                    display_enabled = False
                
    except Exception as e:
        log(f"Error handling client: {e}")
    finally:
        if out is not None:
            out.release()
        conn.close()
        if display_enabled:
            try:
                cv2.destroyAllWindows()
            except:
                pass
        log("Connection closed and resources released.")
        # Force garbage collection to ensure memory is freed between recurring setups
        gc.collect()

def start_server(host, port, output_dir):
    # Create output directory if it doesn't exist
    if not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)
        except OSError as e:
            print(f"Error creating directory {output_dir}: {e}")
            return

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server_socket.bind((host, port))
    except OSError as e:
        print(f"Error binding to port {port}: {e}")
        return

    server_socket.listen(5)
    print(f"Server listening on {host}:{port}")
    print(f"Saving videos to: {output_dir}")
    print("Press Ctrl+C to stop.")

    try:
        while True:
            try:
                conn, addr = server_socket.accept()
                handle_client(conn, addr, output_dir)
            except KeyboardInterrupt:
                raise
            except Exception as e:
                log(f"Error accepting connection: {e}")
                
    except KeyboardInterrupt:
        print("\nServer stopping...")
    finally:
        server_socket.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Receive video stream from Raspberry Pi.")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on")
    parser.add_argument("--dir", type=str, default=r"D:\Videos\hydroponics", help="Directory to save videos")
    parser.add_argument("--debug", action="store_true", help="Enable debug logs")
    
    args = parser.parse_args()
    
    DEBUG = args.debug
    
    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
        if DEBUG:
            print(f"Server Video Receiver IP: {local_ip}")
    except:
        pass
    
    start_server('0.0.0.0', args.port, args.dir)
