#include <math.h>
#include <AccelStepper.h>

// Pin Definitions
#define DIR_PIN_X 5
#define STEP_PIN_X 2
#define DIR_PIN_Y 6
#define STEP_PIN_Y 3
#define DIR_PIN_Z 7
#define STEP_PIN_Z 4
#define DIR_PIN_A 13
#define STEP_PIN_A 12

// Motion Parameters
const int STEPS_PER_REV = 200;
const int MAX_SPEED = 100;
const int ACCEL = 3000;
const float DEG_PER_STEP = 1.8f;
const float GEAR_RATIO = 256.0f / 9.0f;

// Movement Flags
const bool ENABLE_RELATIVE_MOVE = false;
bool xReached = false, yReached = false, zReached = false, aReached = false;

// Stepper Motors
AccelStepper stepperX(AccelStepper::DRIVER, STEP_PIN_X, DIR_PIN_X);
AccelStepper stepperY(AccelStepper::DRIVER, STEP_PIN_Y, DIR_PIN_Y);
AccelStepper stepperZ(AccelStepper::DRIVER, STEP_PIN_Z, DIR_PIN_Z);
AccelStepper stepperA(AccelStepper::DRIVER, STEP_PIN_A, DIR_PIN_A);
AccelStepper* armSteppers[4] = { &stepperX, &stepperY, &stepperZ, &stepperA };

// Serial Buffer
const byte bufferSize = 128;
char inputBuffer[bufferSize];
byte bufferIndex = 0;
bool lineComplete = false;

// Chunk Buffer
char* chunkBuffer = nullptr;
int chunkBufferSize = 0;   // total allocated size
int chunkBufferUsed = 0;   // how many chars currently filled
bool inChunk = false;
bool chunkAllocated = false;
bool chunkFilled = false;


void setup() {
    Serial.begin(9600);

    for (AccelStepper* stepper : armSteppers) {
        stepper->setMaxSpeed(MAX_SPEED);
        stepper->setSpeed(MAX_SPEED);
        stepper->setAcceleration(ACCEL);
        stepper->moveTo(0);
    }

    stepperX.setMaxSpeed(80);
    stepperY.setMaxSpeed(150);
    stepperZ.setMaxSpeed(80);
    stepperA.setMaxSpeed(250);

    Serial.flush();
}

// Memory Management
void allocateChunkBuffer(int memSize) {
    if (chunkBuffer != nullptr) {
        free(chunkBuffer);
    }

    chunkBuffer = (char*)malloc(memSize);
    if (chunkBuffer) {
        chunkBuffer[0] = '\0';   // empty string
        chunkBufferSize = memSize;
        chunkBufferUsed = 0;
        chunkAllocated = true;
        chunkFilled = false;
    } else {
        chunkAllocated = false;
        Serial.println("ERROR: Allocation failed");
    }
}

void fillChunk(const char* line) {
    if (!chunkAllocated || !chunkBuffer) return;

    int len = strlen(line);

    // +2 = 1 for '\n', 1 for '\0'
    if (chunkBufferUsed + len + 2 >= chunkBufferSize) {
        Serial.println("ERROR: Chunk buffer overflow");
        return;
    }

    // Copy line into buffer
    memcpy(chunkBuffer + chunkBufferUsed, line, len);
    chunkBufferUsed += len;

    // Append '\n'
    chunkBuffer[chunkBufferUsed++] = '\n';
    chunkBuffer[chunkBufferUsed] = '\0';

    chunkFilled = true;  // mark as having data
}

void freeChunkBuffer() {
    if (chunkBuffer != nullptr) {
        free(chunkBuffer);
        chunkBuffer = nullptr;
    }

    chunkBufferSize = 0;
    chunkBufferUsed = 0;
    chunkAllocated = false;
    chunkFilled = false;
}

// Stepper Update
void updateMotorPositions() {
    if (abs(stepperX.distanceToGo()) <= 0) {
        if (ENABLE_RELATIVE_MOVE) {
            stepperX.setCurrentPosition(0);
        }
        xReached = true;
    } else stepperX.run();
    if (abs(stepperY.distanceToGo()) <= 0) {
        if (ENABLE_RELATIVE_MOVE) {
            stepperY.setCurrentPosition(0);
        }
        yReached = true;
    } else stepperY.run();
    if (abs(stepperZ.distanceToGo()) <= 0) {
        if (ENABLE_RELATIVE_MOVE) {
            stepperZ.setCurrentPosition(0);
        }
        zReached = true;
    } else stepperZ.run();
    if (abs(stepperA.distanceToGo()) <= 0) {
        if (ENABLE_RELATIVE_MOVE) {
            stepperA.setCurrentPosition(0);
        }
        aReached = true;
    } else stepperA.run();
}

// Chunk Line Handler
void handleChunkLine(char* line) {
    line[strcspn(line, "\r\n")] = 0;

    if (strcmp(line, "DONE") == 0) {
        Serial.println("ALL CHUNKS DONE");
        freeChunkBuffer();
    }
    else if (strncmp(line, "@", 1) == 0) {
        int xValue, yValue, zValue, aValue;
        if (sscanf(line, "@%d %d %d %d", &xValue, &yValue, &zValue, &aValue) == 4) {
            xReached = yReached = zReached = aReached = false;
            stepperX.moveTo(xValue);
            stepperY.moveTo(yValue);
            stepperZ.moveTo(zValue);
            stepperA.moveTo(aValue);

            // Update until they reach positions
            while (!(xReached && yReached && zReached && aReached)) {
                updateMotorPositions();
            }
            Serial.println("Finished moving");
        } else {
            Serial.println("ERROR ANGLES OF WRONG FORMAT");
        }
    }
    else if (strstr(line, "SET ORIGIN")) {
        // Mark current point for all steppers as zero point
        for (AccelStepper* stepper : armSteppers) {
            stepper->setCurrentPosition(0);
        }
        Serial.println("Origin set");
    }
    else if (strstr(line, "END CHUNK$")) {
        inChunk = false;
        Serial.println("NEXT CHUNK");
    }
    else {
        // Unhandled
        Serial.print("UNKNOWN IN-CHUNK CMD: ");
        Serial.println(line);
    }
}

// Non-chunk Commands
void handleNonChunkLine(char* line) {
    // Receiving chunk data as input
    if (strncmp("START CHUNK", line, 11) == 0) {
        if (chunkAllocated) {
            inChunk = true;
            fillChunk(line);
        } else {
            Serial.println("RECEIVED CHUNK DATA BUT NO MEMORY WAS ALLOCATED");
        }
        return;
    }

    // Strip line if its not chunk data, because chunk data is newline delimited
    line[strcspn(line, "\r\n")] = 0;

    if (strstr(line, "ASK READY")) {
        Serial.println("READY");
    }
    else if (strstr(line, "STOP")) {
        for (AccelStepper* stepper : armSteppers)
            stepper->setSpeed(0);
    }
    else if (line[0] == '&') {
        int value;
        if (sscanf(line, "&%d", &value) == 1) {
            allocateChunkBuffer(value);
            Serial.println("MEMORY ALLOCATED");
        } else {
            Serial.println("MEMORY COULD NOT BE ALLOCATED INVALID FORMAT");
        }
    }
    else {
        // Unhandled
        Serial.print("UNHANDLED NON-CHUNK LINE: ");
        Serial.println(line);
    }
}

// Serial Input Handler
// Check if the first 11 characters read are START CHUNK, that means we're in a
// chunk so we'll keep reading until '$' character and send it all to
// handleNonChunkLine as one line (where it gets allocated and parsed).
// BUT!!! if the line starts with ^ handle that line with handleChunkLine!!!
// This is so that we can send individual commands too without needing to
// allocate new memory every time.
void handleSerial() {
    static bool readingChunk = false; // Track if we're inside START CHUNK
    static int charCount = 0;         // Track how many chars read so far

    while (Serial.available() > 0) {
        char c = Serial.read();

        // Always append unless buffer is full
        if (bufferIndex < bufferSize - 1) {
            inputBuffer[bufferIndex++] = c;
        }

        // Count characters until 11 so we can check START CHUNK prefix
        if (charCount < 11) {
            charCount++;
            if (charCount == 11 && strncmp(inputBuffer, "START CHUNK", 11) == 0) {
                readingChunk = true; // We now know we're reading a chunk
            }
        }

        if (readingChunk) {
            // If we see '$', the chunk ends
            if (c == '$') {
                inputBuffer[bufferIndex] = '\0';
                handleNonChunkLine(inputBuffer); // includes the $
                bufferIndex = 0;
                charCount = 0;
                readingChunk = false;
            }
        } else {
            // Normal mode: newline ends the command
            if (c == '\n' || c == '\r') {
                if (bufferIndex > 1) { // Ignore empty lines
                    inputBuffer[bufferIndex - 1] = '\0'; // Remove newline

                    // Case 1: standalone chunk-style line starting with ^
                    if (inputBuffer[0] == '^') {
                        handleChunkLine(&inputBuffer[1]); // exclude '^'
                    }
                    // Case 2: normal non-chunk line
                    else {
                        handleNonChunkLine(inputBuffer);
                    }
                }
                bufferIndex = 0;
                charCount = 0;
            }
        }
    }
}

// Chunk Executor
void parseCurrentChunk() {
    if (!chunkFilled || !chunkBuffer) return;

    char line[bufferSize];
    int linePos = 0;
    int lineCounter = 0;

    for (int i = 0; chunkBuffer[i] != '\0'; i++) {
        if (chunkBuffer[i] == '\n') {
            line[linePos] = '\0'; // terminate string
            if (linePos > 0) {
                handleChunkLine(line);
                lineCounter++;
            }
            linePos = 0; // reset for next line
        } else {
            if (linePos < bufferSize - 1) {
                line[linePos++] = chunkBuffer[i];
            }
        }
    }
    Serial.println(lineCounter);

    // If last line doesn’t end with \n
    if (linePos > 0) {
        line[linePos] = '\0';
        handleChunkLine(line);
    }

    chunkFilled = false; // done parsing
}

// Main Loop
void loop() {
    if (chunkAllocated && chunkFilled) {
        parseCurrentChunk();
    } else {
        handleSerial();
    }
}

