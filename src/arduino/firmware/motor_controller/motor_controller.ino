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

// Serial line buffer
const byte lineBufferSize = 128;
char lineBuffer[lineBufferSize];
byte bufferIndex = 0;

// Chunk buffer
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
        chunkBuffer[0] = '\0';   // Empty the string
        chunkBufferSize = memSize;
        chunkBufferUsed = 0;
        chunkAllocated = true;
        chunkFilled = false;
        inChunk = false;
        Serial.print("Allocated: ");
        Serial.print(memSize);
        Serial.println(" bytes");
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
    inChunk = true;
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

    Serial.print("line: ");
    Serial.println(line);

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

            Serial.print("dx to go: ");
            Serial.println(stepperX.distanceToGo());

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
    else if (strstr(line, "$")) {
        inChunk = false;
        Serial.println("NEXT CHUNK");
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
    else if (strstr(line, "ASK READY")) {
        Serial.println("READY");
    }
    else if (strstr(line, "STOP")) {
        for (AccelStepper* stepper : armSteppers)
            stepper->setSpeed(0);
    }
    else {
        // Unhandled
        Serial.print("UNKNOWN CMD: ");
        Serial.println(line);
    }
}

void handleSerial() {
    // Non-blocking serial parser with three modes:
    // 1) writingChunk: between '^' and '$' -> append to chunkBuffer (inclusive) if allocated.
    // 2) readingStarLine: line starting with '*' -> collect into 128B temp, pass to handleChunkLine (without '*').
    // 3) default line: collect into 128B temp, pass to handleChunkLine on EOL.
    static bool writingChunk = false;
    static bool readingStarLine = false;
    static char lineBuf[128];
    static int  lineLen = 0;

    while (Serial.available() > 0) {
        char c = (char)Serial.read();

        // Mode 1: inside a ^...$ chunk
        if (writingChunk) {
            if (chunkAllocated && chunkBuffer != nullptr && chunkBufferSize > 0) {
                if (chunkBufferUsed < (chunkBufferSize - 1)) {
                    chunkBuffer[chunkBufferUsed++] = c;   // store every byte (incl. newlines, '$')
                    chunkBuffer[chunkBufferUsed] = '\0';  // keep null-terminated
                }
                // else: drop overflow but keep scanning until '$'
            }
            if (c == '$') {
                writingChunk = false;
                if (chunkAllocated && chunkBuffer != nullptr) {
                    chunkFilled = true; // ready for parseCurrentChunk()
                }
            }
            continue; // do not treat chunk bytes as command lines
        }

        // Not inside chunk yet: check for '^' to start
        if (c == '^') {
            writingChunk = true;
            if (chunkAllocated && chunkBuffer != nullptr && chunkBufferSize > 0) {
                // start fresh and include '^'
                chunkBufferUsed = 0;
                chunkBuffer[chunkBufferUsed++] = '^';
                chunkBuffer[chunkBufferUsed] = '\0';
            }
            continue; // keep reading following bytes as chunk content
        }

        // Star-led single-line command (exclude '*' itself)
        if (c == '*') {
            readingStarLine = true;
            lineLen = 0;
            continue;
        }

        // End-of-line => flush whichever line we're building
        if (c == '\n' || c == '\r') {
            if (lineLen > 0) {
                lineBuf[lineLen] = '\0';
                handleChunkLine(lineBuf); // for star lines, '*' was excluded above
                lineLen = 0;
                readingStarLine = false;
            }
            // Swallow CRLF pair non-blockingly
            if (c == '\r' && Serial.peek() == '\n') (void)Serial.read();
            continue;
        }

        // Regular character for current line (star or default)
        if (lineLen < (int)sizeof(lineBuf) - 1) {
            lineBuf[lineLen++] = c;
        }
        // else: truncate until EOL to remain safe and non-blocking
    }
}

void parseCurrentChunk() {
    // Consume chunkBuffer line-by-line using a rotating 128-byte temp buffer.
    if (!chunkAllocated || !chunkFilled || chunkBuffer == nullptr) return;

    const char* p = chunkBuffer;

    while (*p != '\0') {
        // Allocate 128B temporary buffer for this line
        char* tmp = (char*)malloc(128);
        if (!tmp) {
            // Allocation failed — abort parsing to avoid UB
            return;
        }
        int idx = 0;

        // Copy until EOL or NUL, truncating safely at 127 chars
        while (*p != '\0' && *p != '\n' && *p != '\r') {
            if (idx < 127) tmp[idx++] = *p;
            ++p;
        }
        tmp[idx] = '\0';

        if (idx > 0) {
            handleChunkLine(tmp);
        }

        free(tmp);

        // Skip EOL chars (CRLF/CR/LF)
        if (*p == '\r') {
            ++p;
            if (*p == '\n') ++p;
        } else if (*p == '\n') {
            ++p;
        }
    }

    // Mark chunk as consumed / ready for next write
    chunkFilled = false;
    chunkBufferUsed = 0;
    if (chunkBuffer) chunkBuffer[0] = '\0';
}

// Main Loop
void loop() {
    if (chunkAllocated && chunkFilled) {
        parseCurrentChunk();
    } else {
        handleSerial();
    }
}

