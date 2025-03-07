#include <AccelStepper.h>

#define STEPS 200 // 200 total steps, each step is 1.8°

// Define the pins for each axis
#define DIR_PIN_X 5
#define STEP_PIN_X 2

#define DIR_PIN_Y 6
#define STEP_PIN_Y 3

#define DIR_PIN_Z 7
#define STEP_PIN_Z 4

#define DIR_PIN_A 8
#define STEP_PIN_A 5

// Create AccelStepper instances for each axis
AccelStepper stepperX(AccelStepper::DRIVER, STEP_PIN_X, DIR_PIN_X);
AccelStepper stepperY(AccelStepper::DRIVER, STEP_PIN_Y, DIR_PIN_Y);
AccelStepper stepperZ(AccelStepper::DRIVER, STEP_PIN_Z, DIR_PIN_Z);
AccelStepper stepperA(AccelStepper::DRIVER, STEP_PIN_A, DIR_PIN_A);

void setup() {
    Serial.begin(9600);

    // Set speed for each motor
    stepperX.setMaxSpeed(1000);
    stepperX.setSpeed(50);

    stepperY.setMaxSpeed(1000);
    stepperY.setSpeed(50);

    stepperZ.setMaxSpeed(1000);
    stepperZ.setSpeed(50);

    stepperA.setMaxSpeed(1000);
    stepperA.setSpeed(50);
}

void loop() {
    stepperX.runSpeed();
    stepperY.runSpeed();

    // Optional: Print the current position for debugging
    Serial.print("X: ");
    Serial.print(stepperX.currentPosition());
    Serial.print(" Y: ");
    Serial.print(stepperY.currentPosition());
    Serial.print(" Z: ");
    Serial.println(stepperZ.currentPosition())

    /*
    stepperX.step(1 * dir);
    stepCount += 1 * dir;

    if (stepCount >= 1500) {
        dir = -1;
    } else if (stepCount <= 0) {
        dir = 1;
    }
    */
}
