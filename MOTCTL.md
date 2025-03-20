# Arm Motor Control: Language Reference

## Description

Documentation for `.motctl` file format used in this project.

The instructions within `data/output.motctl` are read from by the Raspberry PI
and sent via a serial connection to the Arduino Uno. The Arduino reads and
parses the instructions, extracting values and moving the motors on the
robotic arm accordingly.

## Syntax

`COMMAND$AXISNAME:VALUE,AXISNAME2:VALUE,AXISNAME3:VALUE,AXISNAME4:VALUE`

### Example

`SET ANGLES$x:45.00,y:60.00,z:-30.00,a:90.00`
`SET SPEEDS$x:50,y:-100,z:0,a:0`

## Commands

- `SET ANGLES`
- `SET SPEEDS`
- `PEN UP`
- `PEN DOWN`
- `NO ANGLES`
