#include <math.h>
#include <AccelStepper.h>

// Define the pins for each axis
#define DIR_PIN_X 5
#define STEP_PIN_X 2
#define DIR_PIN_Y 6
#define STEP_PIN_Y 3
#define DIR_PIN_Z 7
#define STEP_PIN_Z 4
#define DIR_PIN_A 13
#define STEP_PIN_A 12

const int STEPS_PER_REV = 200;      // 200 steps per revolution
const int MAX_SPEED = 100;          // Steps/sec
const int ACCEL = 3000;             // Steps/sec^2
const float DEG_PER_STEP = 1.8f;    // Each step is 1.8° (360/200=1.8)
const float GEAR_RATIO = 256.0f / 9.0f;

// MOTCTL language delimeters

const byte bufferSize = 128;
char inputBuffer[bufferSize];
byte bufferIndex = 0;
bool lineComplete = false;

// Should the motors move relative to the last position?
// Usually would want this off
const bool ENABLE_RELATIVE_MOVE = false;

bool hasStarted = false; // Have we started moving yet?

bool xReached = false;
bool yReached = false;
bool zReached = false;
bool aReached = false;

// Create AccelStepper instances for each axis
AccelStepper stepperX(AccelStepper::DRIVER, STEP_PIN_X, DIR_PIN_X);
AccelStepper stepperY(AccelStepper::DRIVER, STEP_PIN_Y, DIR_PIN_Y);
AccelStepper stepperZ(AccelStepper::DRIVER, STEP_PIN_Z, DIR_PIN_Z);
AccelStepper stepperA(AccelStepper::DRIVER, STEP_PIN_A, DIR_PIN_A);

AccelStepper* armSteppers[4] = {&stepperX, &stepperY, &stepperZ, &stepperA};

char** chunkBuffer = nullptr;
int chunkSize = 0;
int currentLineIndex = 0;
bool chunkAllocated = false;
bool chunkFilled = false;

int calculateSteps(float angle) {
    /* Calculates the number of steps required
     * to move by an angle in degrees */
    return round((angle / DEG_PER_STEP) * GEAR_RATIO);
}

void allocateChunkBuffer(int lines) {
    if (chunkBuffer != nullptr) {
        // Clean up existing buffer
        for (int i = 0; i < chunkSize; i++) {
            free(chunkBuffer[i]);
        }
        free(chunkBuffer);
    }

    chunkSize = lines;
    chunkBuffer = (char**)malloc(chunkSize * sizeof(char*));
    for (int i = 0; i < chunkSize; i++) {
        chunkBuffer[i] = (char*)malloc(bufferSize); // assume line <= bufferSize
        chunkBuffer[i][0] = '\0';
    }

    currentLineIndex = 0;
}

void setup() {
    Serial.begin(9600);

    // Set default max and initial speed for each motor
    for (AccelStepper* stepper : armSteppers) {
        stepper->setMaxSpeed(MAX_SPEED);
        stepper->setSpeed(MAX_SPEED);
    }

    stepperX.setMaxSpeed(80);
    stepperX.setAcceleration(ACCEL);

    stepperY.setMaxSpeed(150);
    stepperY.setAcceleration(ACCEL);

    stepperZ.setMaxSpeed(80);
    stepperZ.setAcceleration(ACCEL);

    stepperA.setMaxSpeed(250);
    stepperA.setAcceleration(ACCEL);

    stepperX.moveTo(0);
    stepperY.moveTo(0);
    stepperZ.moveTo(0);
    stepperA.moveTo(0);

    Serial.flush();
}

void checkMotorPositions() {
    // Check is the target positions are reached,
    // if they are, zero (home) the position.
    // Otherwise, run the motors until target position is reached.

    if (abs(stepperX.distanceToGo()) <= 0) {
        if (ENABLE_RELATIVE_MOVE) stepperX.setCurrentPosition(0);
        xReached = true;
    } else {
        stepperX.run();
    }

    if (abs(stepperY.distanceToGo()) <= 0) {
        if (ENABLE_RELATIVE_MOVE) stepperY.setCurrentPosition(0);
        yReached = true;
    } else {
        stepperY.run();
    }

    if (abs(stepperZ.distanceToGo()) <= 0) {
        if (ENABLE_RELATIVE_MOVE) stepperZ.setCurrentPosition(0);
        zReached = true;
    } else {
        stepperZ.run();
    }

    if (abs(stepperA.distanceToGo()) <= 0) {
        if (ENABLE_RELATIVE_MOVE) stepperA.setCurrentPosition(0);
        aReached = true;
    } else {
        stepperA.run();
    }
}

bool handleLine(char* line) {
    line[strcspn(line, "\r\n")] = 0;  // Trim trailing newline

    if (strstr(line, "ASK READY")) {
        Serial.println("ARDUINO IS READY");
    } else if (line[0] == '@') {
        char axis;
        float value; // The angle
        char floatStr[16];

        if (sscanf(line, "@%ld %ld %ld %ld", &target.steps[0], &target.steps[1], &target.steps[2], &target.steps[3]) == 4) {
            value = atof(floatStr);

            int stepValue = calculateSteps(value);
            //float targetTime = 4.0f;
            //float speed = 0.0f;
            hasStarted = true;

            switch (axis) {
                case 'x':
                    stepperX.moveTo(stepValue);
                    break;
                case 'y':
                    stepperY.moveTo(stepValue);
                    break;
                case 'z':
                    stepperZ.moveTo(stepValue);
                    break;
                case 'a':
                    stepperA.moveTo(stepValue);
                    break;
                default:
                    hasStarted = false;
                    break;
            }

            Serial.println(value);

        } else {
        }
    } else if (strstr(line, "STOP")) {
        //Serial.println("EMERGENCY STOP!");
        stepperX.setSpeed(0);
        stepperY.setSpeed(0);
        stepperZ.setSpeed(0);
        stepperA.setSpeed(0);
    } else if (strstr(line, "SET ORIGIN")) {
        //Serial.println("ORIGIN SET");
        stepperX.setCurrentPosition(0);
        stepperY.setCurrentPosition(0);
        stepperZ.setCurrentPosition(0);
        stepperA.setCurrentPosition(0);
    } else if (strstr(line, "IS REACHED")) {
        bool isReached = hasStarted && xReached && yReached && zReached && aReached;
        Serial.print(isReached ? "#TRUE#" : "#FALSE#");
    } else if (strstr(line, "READY TO MOVE")) {
        Serial.println("REQUEST NEXT CHUNK");
    } else if (line[0] == '^') {
        if (chunkAllocated && !chunkFilled) {
            Serial.println("RECEIVED CHUNK DATA");
            fillChunk();
        } else {
            Serial.println("RECEIVED CHUNK DATA BUT NO MEMORY WAS ALLOCATED");
        }
    } else if (line[0] == '&') {
        // Allocate memory request (start of chunk)
        char cmdChar;
        int value;
        if (sscanf(line, "&%d", &value) == 1) {
            allocateChunkBuffer(value);
            chunkAllocated = true;
            // Request the actual data to fill the chunk with
            Serial.println("REQUEST CHUNK DATA");
        }
    } else if (!handleInstructionLine) {
        Serial.print("UNHANDLED CMD: ");
        Serial.println(line);
    } else {
        return false;  // Unhandled
    }
    return true;
}

void handleLine(char* line, bool inChunk = false) {
    // Handle a line from serial
    bool instructionsHandled = handleInstructionLine(line);
    if (inChunk) {
        if (!instructionsHandled) {
            Serial.print("UNHANDLED CMD: ");
            Serial.println(line);
        }
    }

}

void handleSerial() {
    // Non-blocking read while serial is available
    while (Serial.available() > 0) {
        // Read one byte
        char c = Serial.read();

        // If it's the line delimeter character
        if (c == '\n' || c == '\r') {
            if (bufferIndex > 0) {
                // End the input buffer
                inputBuffer[bufferIndex] = '\0';
                bufferIndex = 0;
                lineComplete = true;
            }
        } else if (bufferIndex < bufferSize - 1) {
            // Add char to the input buffer
            inputBuffer[bufferIndex++] = c;
        }

        if (lineComplete) {
            handleLine(inputBuffer);
            lineComplete = false;
        }
    }
}

void fillChunk() {
    char lineBuffer[bufferSize];
    int lineIndex = 0;

    while (Serial.available() > 0) {
        char c = Serial.read();

        // End of chunk marker
        if (c == '$') {
            break;
        }

        // Newline marks end of line
        if (c == '\n' || c == '\r') {
            if (lineIndex > 0) {
                lineBuffer[lineIndex] = '\0';

                // Ensure we havespace
                if (currentLineIndex < chunkSize) {
                    strncpy(chunkBuffer[currentLineIndex], lineBuffer, bufferSize - 1);
                    chunkBuffer[currentLineIndex][bufferSize - 1] = '\0';
                    currentLineIndex++;
                }
                lineIndex = 0; // Reset for next line
            }
        } else if (lineIndex < bufferSize - 1) {
            lineBuffer[lineIndex++] = c;
        }
    }
    chunkFilled = true;
}

void handleChunk() {
    // Reset flags before move
    xReached = false;
    yReached = false;
    zReached = false;
    aReached = false;
    hasStarted = false;

    for (int i = 0; i < chunkSize; ++i) {
        if (chunkBuffer[i][0] != '\0') {
            handleLine(chunkBuffer[i+1], true);
        }
    }

    while (!(xReached && yReached && zReached && aReached)) {
        checkMotorPositions();
    }
    // MAKE IT MOVE ALL MOTORS AT ONCE NOT JUST FIRST LINE
    currentLineIndex = 0;
}

void loop() {
    if (chunkAllocated && chunkFilled) {
        handleChunk();
        chunkFilled = false;
    } else {
        handleSerial();
    }
}
