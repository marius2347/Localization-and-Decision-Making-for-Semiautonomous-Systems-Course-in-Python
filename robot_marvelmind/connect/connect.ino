// Robot WiFi Remote Control using ESP32
// This program turns an ESP32 into a WiFi-controlled robot car.
// It connects to a local WiFi network, then listens for movement commands
// from a Python server (forward, backward, left, right, stop, speed).
// The robot uses two DC motors (left and right) driven by an H-bridge (L298N).

#include <WiFi.h>

// WiFi credentials
const char* ssid = "marius";
const char* password = "marius23";

// The robot connects to a Python server that sends driving commands
const char* serverAddress = "10.161.233.90"; 
const int serverPort = 8080;

// Motor pin mapping
// These pins connect the ESP32 to the L298N motor driver board.
// Two input pins per motor control direction, one enable pin controls speed via PWM.
int motorRightPin1 = 26; // Right motor direction pin A
int motorRightPin2 = 13; // Right motor direction pin B
int enableRight = 32;    // Right motor speed (PWM)

int motorLeftPin1 = 14;  // Left motor direction pin A
int motorLeftPin2 = 27;  // Left motor direction pin B
int enableLeft = 33;     // Left motor speed (PWM)

// Master speed multiplier (0.0 = stopped, 1.0 = full speed)
float globalSpeed = 1.0; 

// Turning calibration
// These timing values control how the robot executes a 90-degree turn.
// Tweak them depending on your surface (carpet, tile, etc.)
int timpInFataInainteDeCurba = 300; // Milliseconds to drive straight before starting the turn
int timpRotire90Grade = 350;        // Milliseconds to spin in place to complete a 90 degree turn

// WiFi client used to maintain a persistent TCP connection to the server
WiFiClient client;

// Sets the actual motor speeds using PWM
// Takes a multiplier for each side (0.0 to 1.0) and combines it with globalSpeed
void applySpeed(float leftMultiplier, float rightMultiplier) {
  int pwmLeft = (int)(255.0 * globalSpeed * leftMultiplier);
  int pwmRight = (int)(255.0 * globalSpeed * rightMultiplier);
  
  // Clamp values to the maximum PWM range
  if(pwmLeft > 255) pwmLeft = 255;
  if(pwmRight > 255) pwmRight = 255;

  analogWrite(enableLeft, pwmLeft);
  analogWrite(enableRight, pwmRight);
}

// Both motors spin so the robot drives straight ahead
void moveForward() {
  digitalWrite(motorLeftPin1, LOW); digitalWrite(motorLeftPin2, HIGH);
  digitalWrite(motorRightPin1, HIGH); digitalWrite(motorRightPin2, LOW);
  applySpeed(1.0, 1.0); 
  Serial.println("Command: Moving Forward");
}

// Both motors spin in reverse so the robot goes backwards
void moveBackward() {
  digitalWrite(motorLeftPin1, HIGH); digitalWrite(motorLeftPin2, LOW);
  digitalWrite(motorRightPin1, LOW); digitalWrite(motorRightPin2, HIGH);
  applySpeed(1.0, 1.0); 
  Serial.println("Command: Moving Backward");
}

// Cuts power to both motors, robot stops immediately
void stopMotors() {
  digitalWrite(motorLeftPin1, LOW); digitalWrite(motorLeftPin2, LOW);
  digitalWrite(motorRightPin1, LOW); digitalWrite(motorRightPin2, LOW);
  applySpeed(0.0, 0.0); 
  Serial.println("Command: Stopped");
}

// Executes a 90 degree left turn in 3 steps:
// 1. Drive forward briefly
// 2. Spin left in place (left wheel backward, right wheel forward)
// 3. Resume driving forward
void turnLeft() {
  Serial.println("Command: Sequence Left");
  
  // Step 1: Drive forward a little to build momentum
  digitalWrite(motorLeftPin1, LOW); digitalWrite(motorLeftPin2, HIGH);
  digitalWrite(motorRightPin1, HIGH); digitalWrite(motorRightPin2, LOW);
  applySpeed(1.0, 1.0);
  delay(timpInFataInainteDeCurba);

  // Step 2: Spin left, left motor goes backward, right motor goes forward
  digitalWrite(motorLeftPin1, HIGH); digitalWrite(motorLeftPin2, LOW);
  digitalWrite(motorRightPin1, HIGH); digitalWrite(motorRightPin2, LOW);
  applySpeed(1.0, 1.0);
  delay(timpRotire90Grade);

  // Step 3: Go straight again (robot is now facing the new direction)
  digitalWrite(motorLeftPin1, LOW); digitalWrite(motorLeftPin2, HIGH);
  digitalWrite(motorRightPin1, HIGH); digitalWrite(motorRightPin2, LOW);
  applySpeed(1.0, 1.0);
}

// Executes a 90 degree right turn in 3 steps:
// 1. Drive forward briefly
// 2. Spin right in place (left wheel forward, right wheel backward)
// 3. Resume driving forward
void turnRight() {
  Serial.println("Command: Sequence Right");
  
  // Step 1: Drive forward a little to build momentum
  digitalWrite(motorLeftPin1, LOW); digitalWrite(motorLeftPin2, HIGH);
  digitalWrite(motorRightPin1, HIGH); digitalWrite(motorRightPin2, LOW);
  applySpeed(1.0, 1.0);
  delay(timpInFataInainteDeCurba);

  // Step 2: Spin right, left motor goes forward, right motor goes backward
  digitalWrite(motorLeftPin1, LOW); digitalWrite(motorLeftPin2, HIGH);
  digitalWrite(motorRightPin1, LOW); digitalWrite(motorRightPin2, HIGH);
  applySpeed(1.0, 1.0);
  delay(timpRotire90Grade);

  // Step 3: Go straight again (robot is now facing the new direction)
  digitalWrite(motorLeftPin1, LOW); digitalWrite(motorLeftPin2, HIGH);
  digitalWrite(motorRightPin1, HIGH); digitalWrite(motorRightPin2, LOW);
  applySpeed(1.0, 1.0);
}

// Runs once when the ESP32 powers on
// Configures motor pins, stops motors, and connects to WiFi
void setup() {
  Serial.begin(115200);
  
  // Configure all motor-related pins as outputs
  pinMode(motorLeftPin1, OUTPUT); pinMode(motorLeftPin2, OUTPUT);
  pinMode(motorRightPin1, OUTPUT); pinMode(motorRightPin2, OUTPUT);
  pinMode(enableLeft, OUTPUT); pinMode(enableRight, OUTPUT);

  // Make sure the robot doesn't move on startup
  stopMotors();

  // Connect to WiFi, will keep trying until successful
  Serial.print("Connecting to Wi-Fi");
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected!");
}

// Runs continuously after setup
// Maintains a TCP connection to the server and listens for commands
// Supported commands: forward, backward, left, right, stop, speed X
void loop() {
  // If we lost the connection (or never had one), try to reconnect
  if (!client.connected()) {
    if (client.connect(serverAddress, serverPort)) {
      Serial.println("Connected to Python Server!");
    } else {
      delay(1000); // Wait a second before retrying
    }
  } else {
    // We're connected, check if the server sent us a command
    if (client.available()) {
      String request = client.readStringUntil('\n');
      request.trim(); // Remove any trailing whitespace or carriage returns

      // Match the command and execute the corresponding action
      if (request == "forward") moveForward();
      else if (request == "backward") moveBackward();
      else if (request == "left") turnLeft();
      else if (request == "right") turnRight();
      else if (request == "stop") stopMotors();
      else if (request.startsWith("speed ")) {
        // Update the global speed dynamically (useful for fine-tuning on the fly)
        globalSpeed = request.substring(6).toFloat();
        if (globalSpeed < 0.0) globalSpeed = 0.0;
        if (globalSpeed > 1.0) globalSpeed = 1.0;
        Serial.print("Global Speed updated to: ");
        Serial.println(globalSpeed); 
      }
    }
  }
}