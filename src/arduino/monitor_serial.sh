#!/usr/bin/env sh

# Load .env file
set -a          # Automatically export all variables
source ./.env     # Source the env file
set +a

arduino-cli monitor -p $ARDUINO_PORT -c baudrate=9600
