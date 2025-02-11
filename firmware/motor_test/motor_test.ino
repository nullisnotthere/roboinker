#include <AccelStepper.h>

// Define the pins for each axis
#define DIR_PIN_X 5    // X-DIR on CNC Shield
#define STEP_PIN_X 2   // X-STEP on CNC Shield

#define DIR_PIN_Y 6    // Y-DIR on CNC Shield
#define STEP_PIN_Y 3   // Y-STEP on CNC Shield

#define DIR_PIN_Z 7    // Z-DIR on CNC Shield
#define STEP_PIN_Z 4   // Z-STEP on CNC Shield

// Create AccelStepper instances for each axis
AccelStepper stepperX(AccelStepper::DRIVER, STEP_PIN_X, DIR_PIN_X);
AccelStepper stepperY(AccelStepper::DRIVER, STEP_PIN_Y, DIR_PIN_Y);
AccelStepper stepperZ(AccelStepper::DRIVER, STEP_PIN_Z, DIR_PIN_Z);

void setup() {
    Serial.begin(9600);

    // Set max speed and speed for each motor
    stepperX.setMaxSpeed(1000);
    stepperX.setSpeed(1000);

    stepperY.setMaxSpeed(1000);
    stepperY.setSpeed(1000);

    stepperZ.setMaxSpeed(1000);
    stepperZ.setSpeed(57);
}

void loop() {
    // Run each stepper motor at the set speed
    stepperX.runSpeed();
    stepperY.runSpeed();
    stepperZ.runSpeed();

    // Optional: Print the current position for debugging
    Serial.print("X: ");
    Serial.print(stepperX.currentPosition());
    Serial.print(" Y: ");
    Serial.print(stepperY.currentPosition());
    Serial.print(" Z: ");
    Serial.println(stepperZ.currentPosition());
}

