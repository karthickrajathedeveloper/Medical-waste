#include <ESP32Servo.h>

Servo myServo;
Servo doorServo;

String input = "";

// Pins
#define IR_PIN 5
#define LED_PIN 2
#define BTN_90 13
#define BTN_180 14
#define BTN_0 27

// States
bool irDetected = false;
bool lastIrState = HIGH;

unsigned long irStartTime = 0;
unsigned long lastDataTime = 0;
unsigned long doorTimer = 0;

bool doorOpen = false;
bool timeoutDone = false;

void setup() {
  Serial.begin(115200);

  pinMode(IR_PIN, INPUT);
  pinMode(LED_PIN, OUTPUT);

  pinMode(BTN_90, INPUT_PULLUP);
  pinMode(BTN_180, INPUT_PULLUP);
  pinMode(BTN_0, INPUT_PULLUP);

  myServo.attach(18);
  doorServo.attach(19);

  myServo.write(0);
  doorServo.write(180);

  Serial.println("System Ready");
}

void loop() {

  // ================= IR SENSOR =================
  int irState = digitalRead(IR_PIN);

  if (irState == LOW && lastIrState == HIGH) {
    Serial.println("IR Detected");
    irDetected = true;
    irStartTime = millis();
    timeoutDone = false;
  }

  if (irState == HIGH && lastIrState == LOW) {
    Serial.println("IR Cleared");
    irDetected = false;
    doorClose();
  }

  lastIrState = irState;

  // ================= BUTTON CONTROL =================
  if (digitalRead(BTN_90) == LOW) {
    Serial.println("Button 90");
    moveServo(90);
  }

  if (digitalRead(BTN_180) == LOW) {
    Serial.println("Button 180");
    moveServo(180);
  }

  if (digitalRead(BTN_0) == LOW) {
    Serial.println("Button 0");
    moveServo(0);
  }

  // ================= UART READ =================
  while (Serial.available()) {
    char c = Serial.read();

    if (c == '\n') {
      Serial.print("Received: ");
      Serial.println(input);

      int angle = input.toInt();

      if (angle >= 0 && angle <= 180) {
        moveServo(angle);
      }

      input = "";
    } else {
      input += c;
    }
  }

  // ================= AUTO TIMEOUT =================
  if (irDetected && !timeoutDone) {
    if (millis() - irStartTime > 10000 && millis() - lastDataTime > 10000) {
      Serial.println("Timeout → Reset");
      moveServo(0);
      timeoutDone = true;
    }
  }

  // ================= AUTO DOOR CLOSE =================
  if (doorOpen && millis() - doorTimer > 3000) {
    doorClose();
  }
}

// ================= FUNCTIONS =================

void moveServo(int angle) {
  myServo.write(angle);
  Serial.println("Servo → " + String(angle));

  lastDataTime = millis();

  doorOpenNow();
}

void doorOpenNow() {
  doorServo.write(90);
  Serial.println("Door Open");

  digitalWrite(LED_PIN, HIGH);

  doorOpen = true;
  doorTimer = millis();
}

void doorClose() {
  doorServo.write(180);
  Serial.println("Door Close");

  digitalWrite(LED_PIN, LOW);

  doorOpen = false;
}
