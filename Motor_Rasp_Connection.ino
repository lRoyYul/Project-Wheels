#include <SoftwareSerial.h>

// ===== Motor Pins =====
int In1 = 7;
int In2 = 8;
int ENA = 5;
int SPEED = 210;

// ===== Bluetooth (HC-05) Pins =====
#define rxPin 2
#define txPin 3
#define baudrate 38400

SoftwareSerial hc05(rxPin, txPin);
String msg = "";

void setup() {
  // Motor setup
  pinMode(In1, OUTPUT);
  pinMode(In2, OUTPUT);
  pinMode(ENA, OUTPUT);

  // Bluetooth setup
  pinMode(rxPin, INPUT);
  pinMode(txPin, OUTPUT);

  Serial.begin(9600);     // Serial monitor
  hc05.begin(baudrate);   // HC-05 Bluetooth
  Serial.println("Bluetooth motor controller ready.");
  stopMotor();
}

// ===== Motor Control Functions =====
void forward(int speed) {
  digitalWrite(In1, HIGH);
  digitalWrite(In2, LOW);
  analogWrite(ENA, constrain(speed, 0, 255));
  Serial.println("Motor ON (forward)");
}

void stopMotor() {
  digitalWrite(In1, LOW);
  digitalWrite(In2, LOW);
  analogWrite(ENA, 0);
  Serial.println("Motor OFF");
}

// ===== Bluetooth Communication =====
void loop() {
  // Read from Bluetooth
  if (hc05.available() > 0) {
    char c = hc05.read();
    if (c == '\n') {
      processCommand(msg);
      msg = "";
    } else {
      msg += c;
    }
  }

  // Optional: read from Serial Monitor (for testing)
  if (Serial.available() > 0) {
    String s = Serial.readStringUntil('\n');
    processCommand(s);
  }
}

// ===== Command Parser =====
void processCommand(String command) {
  command.trim();
  command.toLowerCase();

  if (command == "on") {
    forward(SPEED);
    hc05.println("Motor ON");
  } else if (command == "off") {
    stopMotor();
    hc05.println("Motor OFF");
  } else if (command.startsWith("speed")) {
    int val = command.substring(5).toInt();
    SPEED = constrain(val, 0, 255);
    forward(SPEED);
    hc05.println("Speed set to " + String(SPEED));
  } else {
    hc05.println("Unknown command: " + command);
  }
}
