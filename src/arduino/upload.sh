#!/usr/bin/env sh

# Load .env file
set -a          # Automatically export all variables
source ./.env     # Source the env file
set +a

DEFAULT_SKETCH_DIR=./src/arduino/firmware/motor_controller/
board=arduino:renesas_uno:unor4wifi

if [ $1 ]
then
    sketch_dir=$1
else
    sketch_dir=$DEFAULT_SKETCH_DIR
fi

rm -rf ~/.cache/arduino/
#arduino-cli compile --fqbn arduino:avr:uno $sketch_dir
arduino-cli compile --fqbn $board $sketch_dir
echo $ARDUINO_PORT
arduino-cli upload -p $ARDUINO_PORT --fqbn $board $sketch_dir
