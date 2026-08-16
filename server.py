# Robot Control Server
# This script creates a GUI with directional buttons and a speed slider.
# It runs a TCP server that waits for the ESP32 robot to connect,
# then sends movement commands (forward, backward, left, right, stop, speed)
# over the network whenever a button is pressed or the slider is moved.

import tkinter as tk
import socket
import threading

# The server listens on all network interfaces, port 8080
HOST = '0.0.0.0'
PORT = 8080

class RobotControlPanel:
    def __init__(self, root):
        self.root = root
        self.root.title("Robot Control Panel")
        self.root.geometry("350x400")
        self.root.resizable(False, False)
        
        self.conn = None
        self.is_connected = False
        
        # Status label shows whether the robot is connected or not
        self.status_label = tk.Label(root, text="Waiting for robot connection...", fg="red", font=("Arial", 11, "bold"))
        self.status_label.pack(pady=15)
        
        # Directional buttons arranged in a cross layout
        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=10)
        
        self.btn_fwd = tk.Button(btn_frame, text="Forward", width=10, height=2, bg="#e0e0e0", command=lambda: self.send_command("forward"))
        self.btn_fwd.grid(row=0, column=1, pady=5)
        
        self.btn_left = tk.Button(btn_frame, text="Left", width=10, height=2, bg="#e0e0e0", command=lambda: self.send_command("left"))
        self.btn_left.grid(row=1, column=0, padx=5)
        
        self.btn_stop = tk.Button(btn_frame, text="STOP", width=10, height=2, bg="#ff4c4c", fg="white", font=("Arial", 9, "bold"), command=lambda: self.send_command("stop"))
        self.btn_stop.grid(row=1, column=1, padx=5)
        
        self.btn_right = tk.Button(btn_frame, text="Right", width=10, height=2, bg="#e0e0e0", command=lambda: self.send_command("right"))
        self.btn_right.grid(row=1, column=2, padx=5)
        
        self.btn_bwd = tk.Button(btn_frame, text="Backward", width=10, height=2, bg="#e0e0e0", command=lambda: self.send_command("backward"))
        self.btn_bwd.grid(row=2, column=1, pady=5)
        
        # Speed slider to control how fast the robot moves (0.0 to 1.0)
        self.slider_label = tk.Label(root, text="Global Speed", font=("Arial", 10, "bold"))
        self.slider_label.pack(pady=(20, 0))
        
        self.speed_slider = tk.Scale(root, from_=0.0, to=1.0, resolution=0.1, orient=tk.HORIZONTAL, length=250, command=self.update_speed)
        self.speed_slider.set(1.0)
        self.speed_slider.pack()

        # Start the socket server in a background thread so the GUI stays responsive
        self.server_thread = threading.Thread(target=self.start_server, daemon=True)
        self.server_thread.start()

    # Runs in the background waiting for the ESP32 to connect
    def start_server(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((HOST, PORT))
            s.listen()
            
            while True:
                try:
                    self.conn, addr = s.accept()
                    self.is_connected = True
                    # Update the status label safely from this background thread
                    self.root.after(0, self.update_ui_status, f"Connected to {addr[0]}", "green")
                    print(f"[+] Robot successfully connected from {addr}!")
                    
                    # Keep reading to detect if the robot disconnects
                    while self.is_connected:
                        data = self.conn.recv(1024)
                        if not data:
                            break
                            
                except Exception as e:
                    print(f"Network error: {e}")
                finally:
                    self.is_connected = False
                    self.conn = None
                    self.root.after(0, self.update_ui_status, "Robot disconnected. Waiting...", "red")
                    print("[-] Robot disconnected. Waiting for reconnection...")

    # Sends the command string to the ESP32 over the TCP connection
    def send_command(self, cmd):
        if self.is_connected and self.conn:
            try:
                self.conn.sendall((cmd + "\n").encode('utf-8'))
                print(f"Sent: {cmd}")
            except Exception as e:
                print(f"Failed to send command: {e}")
                self.is_connected = False
        else:
            print(f"Ignored '{cmd}': Robot is not connected!")

    # Called automatically whenever the speed slider is moved
    def update_speed(self, val):
        self.send_command(f"speed {val}")

    # Safely updates the status label from the background thread
    def update_ui_status(self, text, color):
        self.status_label.config(text=text, fg=color)

if __name__ == "__main__":
    # Create and run the Tkinter window
    root = tk.Tk()
    app = RobotControlPanel(root)
    root.mainloop()