# Autonomous Navigation Server (Live USB Mode)
# This script reads real-time position data from a Marvelmind indoor GPS
# connected via USB, and navigates the robot towards a target coordinate.
# It connects to the ESP32 over TCP and sends movement commands
# (forward, left, right, stop) based on angle and distance calculations.

import socket
import time
import math
import sys
# Marvelmind library for reading position from the USB modem
from marvelmind import MarvelmindHedge 

# Network settings for the TCP server
HOST = '0.0.0.0'
PORT = 8080

# Target coordinates where the robot should navigate to (in meters)
TARGET_X = 5.0
TARGET_Y = 5.0  

# Calculates the straight-line distance between two points
def calculate_distance(x1, y1, x2, y2):
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

# Calculates the angle (in degrees) from point 1 to point 2
def calculate_angle(x1, y1, x2, y2):
    angle_rad = math.atan2(y2 - y1, x2 - x1)
    return math.degrees(angle_rad)

def run_live_server():
    print("Autonomous Navigation Server (LIVE USB Mode)")
    print(f"Destination set to X: {TARGET_X}m, Y: {TARGET_Y}m")
    
    # Connect to the Marvelmind modem via USB
    # If there is a port error, change /dev/ttyACM0 to /dev/ttyUSB0
    try:
        hedge = MarvelmindHedge(tty="/dev/ttyACM0", adr=None, debug=False)
        hedge.start()
        print("Marvelmind Modem has started!")
    except Exception as e:
        print(f"Cannot read the USB modem: {e}")
        print("Did you run: 'sudo usermod -a -G dialout $USER' and restart?")
        sys.exit()
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen()
        
        print(f"Waiting for ESP32 to connect on port {PORT}...")
        conn, addr = s.accept()
        
        with conn:
            print(f"ESP32 joined from {addr}!")
            prev_x, prev_y = None, None
            
            try:
                while True:
                    # Wait for fresh position data from the USB modem
                    hedge.dataEvent.wait(1)
                    hedge.dataEvent.clear()
                    
                    # Read the live position (format: [address, X, Y, Z, timestamp])
                    position = hedge.position()
                    current_x = position[1]
                    current_y = position[2]
                    
                    # Calculate how far we are from the target
                    dist_to_target = calculate_distance(current_x, current_y, TARGET_X, TARGET_Y)
                    print(f"\nLIVE Pos: ({current_x:.2f}, {current_y:.2f}) | Distance: {dist_to_target:.2f}m")
                    
                    # If we are within 20 cm of the target, stop
                    if dist_to_target <= 0.2:
                        print("Target reached! Stopping motors.")
                        conn.sendall(b"stop\n")
                        break
                        
                    # Navigation logic: decide whether to turn or go straight
                    if prev_x is not None and prev_y is not None:
                        robot_heading = calculate_angle(prev_x, prev_y, current_x, current_y)
                        target_angle = calculate_angle(current_x, current_y, TARGET_X, TARGET_Y)
                        angle_diff = target_angle - robot_heading
                        angle_diff = (angle_diff + 180) % 360 - 180
                        
                        if angle_diff > 15:
                            conn.sendall(b"left\n")
                        elif angle_diff < -15:
                            conn.sendall(b"right\n")
                        else:
                            conn.sendall(b"forward\n")
                    else:
                        # First reading, just move forward to establish a heading
                        conn.sendall(b"forward\n")
                        
                    # Save current position for next iteration
                    prev_x = current_x
                    prev_y = current_y
                    
                    # Small delay to avoid flooding the network
                    time.sleep(0.2) 
                    
            except KeyboardInterrupt:
                print("Server stopped manually.")
            finally:
                # Close the USB communication cleanly
                hedge.stop()

if __name__ == "__main__":
    run_live_server()