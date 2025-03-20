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

#define INPUT_SIZE 30

// Motor control language delimeters
const char LINE_DELIM = '\n';
const char COMMAND_DELIM = '$';
const char PARAM_DELIM = ',';
const char PAIR_DELIM = ':';

const int bufferSize = 64;
char buffer[bufferSize];

// Create AccelStepper instances for each axis
AccelStepper stepperX(AccelStepper::DRIVER, STEP_PIN_X, DIR_PIN_X);
AccelStepper stepperY(AccelStepper::DRIVER, STEP_PIN_Y, DIR_PIN_Y);
AccelStepper stepperZ(AccelStepper::DRIVER, STEP_PIN_Z, DIR_PIN_Z);
AccelStepper stepperA(AccelStepper::DRIVER, STEP_PIN_A, DIR_PIN_A);


void setup() {
    Serial.begin(9600);

    // Set speed for each motor
    stepperX.setMaxSpeed(500);
    stepperX.setSpeed(0);

    stepperY.setMaxSpeed(500);
    stepperY.setSpeed(0);

    stepperZ.setMaxSpeed(500);
    stepperZ.setSpeed(0);

    stepperA.setMaxSpeed(500);
    stepperA.setSpeed(0);
}

void loop() {
    stepperX.runSpeed();
    stepperZ.runSpeed();
    stepperY.runSpeed();
    stepperA.runSpeed();

    if (Serial.available()) {
        int bytesRead = Serial.readBytesUntil(
            LINE_DELIM, buffer, bufferSize - 1
        );
        buffer[bytesRead] = '\0';  // Null-terminate

        // Split and assign: command$params
        char* command = strtok(buffer, &COMMAND_DELIM);
        char* params = strtok(NULL, "");

        // Tokenise and progress through params
        char* pair = strtok(params, &PARAM_DELIM);
        while (pair != NULL) {

            // Must use strchr instead of strtok as to not block the token stream
            char* separator = strchr(pair, PAIR_DELIM);
            *separator = '\0';  // Replace delimeter with a null terminator

            char* axis = &pair[0];  // Axis is the first char of the pair's key
            int speed = atoi(separator + 1);  // Convert str after delimeter to an int

            // TODO: handle different commands
            switch (*axis) {
                case 'x':
                    stepperX.setSpeed(speed);
                    break;
                case 'y':
                    stepperY.setSpeed(speed);
                    break;
                case 'z':
                    stepperZ.setSpeed(speed);
                    break;
                case 'a':
                    stepperA.setSpeed(speed);
                    break;
                default:
                    break;
            }

            Serial.print("    Axis: ");
            Serial.print(axis);
            Serial.print(" Speed: ");
            Serial.print(speed);

            // Find the next parameter in input string
            pair = strtok(NULL, &PARAM_DELIM);
        }
    }
}
