#include <ESP32Servo.h>

Servo myServo;
Servo doorServo;

String input = "";

#define IR_PIN 5
#define LED_PIN 2
#define degree_90 35
#define degree_180 34
#define degree_0 39

unsigned long lastDataTime = 0;
bool irDetected = false;
bool timeoutActionDone = false;
unsigned long irStartTime = 0;
unsigned long dataSendTime = 0;
bool lastIrState = HIGH;  //  for edge detection

void setup() {
  Serial.begin(115200);

  pinMode(IR_PIN, INPUT);
  pinMode(degree_90, INPUT);
  pinMode(degree_180, INPUT);
  pinMode(degree_0, INPUT);
  pinMode(LED_PIN, OUTPUT);

  myServo.attach(18);
  doorServo.attach(19);

  myServo.write(0);
  doorServo.write(180);
}

void loop() {

  int irState = digitalRead(IR_PIN);
  int dg_90 = digitalRead(degree_90);
  int dg_180 = digitalRead(degree_180);
  int dg_0 = digitalRead(degree_0);

  // IR Edge Detection (ONLY ONCE)
  if (irState == LOW && lastIrState == HIGH) {
    if (millis() - dataSendTime > 5000) {
      Serial.println("Detected");

      irDetected = true;
      irStartTime = millis();
      dataSendTime = millis();
    }
  }

  if (irState == HIGH && lastIrState == LOW) {
    irDetected = false;
    timeoutActionDone = false;
  }

  lastIrState = irState;

  //  Button Control
  if (dg_90 == LOW) {
    Serial.println("90");
    moveAndOpen(90);
  } else if (dg_180 == LOW) {
    Serial.println("180");
    moveAndOpen(180);
  } else if (dg_0 == HIGH) {
    Serial.println("0");
    moveAndOpen(0);
  }

  //  Default close
  if (!irDetected && dg_90 && dg_180 && dg_0) {
    doorServo.write(180);
  }

  //  UART Read
  while (Serial.available()) {
    char c = Serial.read();

    if (c == '\n') {
      int angle = input.toInt();

      lastDataTime = millis();  //  important fix

      if (irDetected && angle >= 0 && angle <= 180) {
        moveAndOpen(angle);
      }

      input = "";
    } else {
      input += c;
    }
  }

  // Timeout Logic
  if (irDetected && !timeoutActionDone) {
    if ((millis() - irStartTime > 17000) && (millis() - lastDataTime > 17000)) {

      Serial.println("Timeout - No UART data");

      moveAndOpen(0);

      timeoutActionDone = true;
    }
  }
}

// Common Function
void moveAndOpen(int angle) {
  myServo.write(angle);
  Serial.println("Moved to: " + String(angle));

  lastDataTime = millis();
  timeoutActionDone = false;

  delay(2000);

  doorServo.write(90);
  Serial.println("Door Open");

  delay(2000);

  doorServo.write(180);
  Serial.println("Door Close");
}
