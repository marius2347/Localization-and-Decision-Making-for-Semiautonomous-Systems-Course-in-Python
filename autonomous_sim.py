# Autonomous Navigation Server (Simulation Mode)
# This script reads pre-recorded Marvelmind position data from a CSV file
# and uses it to navigate the robot towards a target coordinate.
# It connects to the ESP32 over TCP and sends movement commands
# (forward, left, right, stop) based on angle and distance calculations.

import socket
import re
import time
import math

# Network settings for the TCP server
HOST = '0.0.0.0'
PORT = 8080

# Target coordinates where the robot should navigate to (in meters)
TARGET_X = 0.000
TARGET_Y = 2.000

# Calculates the straight-line distance between two points
def calculate_distance(x1, y1, x2, y2):
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)

# Calculates the angle (in degrees) from point 1 to point 2
def calculate_angle(x1, y1, x2, y2):
    angle_rad = math.atan2(y2 - y1, x2 - x1)
    return math.degrees(angle_rad)

def run_autonomous_server(log_filepath):
    print("Autonomous Navigation Server (Simulation Mode)")
    print(f"Destination set to X: {TARGET_X}m, Y: {TARGET_Y}m")
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, PORT))
        s.listen()
        
        print(f"Waiting for ESP32 to connect on port {PORT}...")
        conn, addr = s.accept()
        
        with conn:
            print(f"ESP32 joined from {addr}!")
            
            # Remember previous position to calculate which direction the robot is facing
            prev_x, prev_y = None, None
            
            try:
                with open(log_filepath, mode='r') as file:
                    for line in file:
                        # Parse the Marvelmind log format to extract X and Y coordinates
                        match = re.search(r'X:\s*([-\d.]+)\s*m,\s*Y:\s*([-\d.]+)\s*m', line)
                        
                        if not match:
                            continue 
                            
                        current_x = float(match.group(1))
                        current_y = float(match.group(2))
                        
                        # Calculate how far we are from the target
                        dist_to_target = calculate_distance(current_x, current_y, TARGET_X, TARGET_Y)
                        print(f"\nCurrent Pos: ({current_x:.2f}, {current_y:.2f}) | Distance remaining: {dist_to_target:.2f}m")
                        
                        # If we are within 20 cm of the target, stop
                        if dist_to_target <= 0.2:
                            print("Target reached! Stopping motors.")
                            conn.sendall(b"stop\n")
                            break
                            
                        # Navigation logic: decide whether to turn or go straight
                        if prev_x is not None and prev_y is not None:
                            # Figure out which direction the robot is currently heading
                            robot_heading = calculate_angle(prev_x, prev_y, current_x, current_y)
                            
                            # Figure out which direction the target is
                            target_angle = calculate_angle(current_x, current_y, TARGET_X, TARGET_Y)
                            
                            # Calculate how far off we are from the ideal direction
                            angle_diff = target_angle - robot_heading
                            
                            # Normalize the angle to be between -180 and 180
                            angle_diff = (angle_diff + 180) % 360 - 180
                            
                            print(f"Heading: {robot_heading:.0f} deg | Target Angle: {target_angle:.0f} deg | Diff: {angle_diff:.0f}")
                            
                            # If the target is more than 15 degrees to the left, turn left
                            if angle_diff > 15:
                                print("Turning LEFT")
                                conn.sendall(b"left\n")
                            # If the target is more than 15 degrees to the right, turn right
                            elif angle_diff < -15:
                                print("Turning RIGHT")
                                conn.sendall(b"right\n")
                            # Otherwise we are pointing roughly at the target, go forward
                            else:
                                print("Moving FORWARD")
                                conn.sendall(b"forward\n")
                        else:
                            # First reading, just move forward to establish a heading
                            print("Initializing movement (FORWARD)")
                            conn.sendall(b"forward\n")
                            
                        # Save current position for next iteration
                        prev_x = current_x
                        prev_y = current_y
                        
                        # Simulate real-time delay between position readings
                        time.sleep(0.5) 
                        
            except FileNotFoundError:
                print(f"Could not find the file: {log_filepath}")
            except Exception as e:
                print(f"Network or Logic Error: {e}")

if __name__ == "__main__":
    # Run the simulation using pre-recorded data from traseu.csv
    run_autonomous_server('test_left_right_forward.csv')