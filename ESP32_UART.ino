#include <ESP32Servo.h>

Servo myServo;
Servo doorServo;

String input = "";

#define IR_PIN 5
#define LED_PIN 19

unsigned long lastDataTime = 0;
bool irDetected = false;
bool timeoutActionDone = false;
unsigned long irStartTime = 0;

void setup() {
  Serial.begin(115200);

  pinMode(IR_PIN, INPUT);
  pinMode(LED_PIN, OUTPUT);

  myServo.attach(18);
  doorServo.attach(19);

  myServo.write(0);
  doorServo.write(180);
}

void loop() {

  int irState = digitalRead(IR_PIN);

  // IR detected
  if (irState == HIGH) {
    if (!irDetected) {
      irStartTime = millis();  // start timer only once
    }

    irDetected = true;


  } else {
    irDetected = false;
    timeoutActionDone = false;  // reset when no object
  }

  // UART read
  while (Serial.available()) {
    char c = Serial.read();

    if (c == '\n') {
      int angle = input.toInt();

      Serial.println(angle);
      Serial.println(irState);

      if (irDetected && angle >= 0 && angle <= 180) {

        myServo.write(angle);
        Serial.println("Moved to: " + String(angle));

        lastDataTime = millis();  // update last received time
        timeoutActionDone = false;

        delay(2000);

        doorServo.write(90);
        Serial.println("Door Open");

        delay(2000);

        doorServo.write(180);
        Serial.println("Door Close");
      }

      input = "";
    } else {
      input += c;
    }
  }

  //  Timeout logic (15 sec no UART data)
  if (irDetected && !timeoutActionDone) {

    if ((millis() - irStartTime > 17000) && (millis() - lastDataTime > 17000)) {

      Serial.println("Timeout - No UART data");

      myServo.write(0);

      delay(2000);

      doorServo.write(90);
      Serial.println("Door Open (Timeout)");

      delay(2000);

      doorServo.write(180);
      Serial.println("Door Close (Timeout)");

      timeoutActionDone = true;
    }
  }
}
