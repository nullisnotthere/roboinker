# Arm Motor Control: Language Reference

## Description

Documentation for `.motctl` file format used in this project.

The instructions within `data/output.motctl` are read from by the Raspberry PI
and sent via a serial connection to the Arduino Uno. The Arduino reads and
parses the instructions chunk by chunk, extracting values and moving the motors on the
robotic arm accordingly.

## Syntax

| Syntax   | Function                                            | Example               |
|----------|-----------------------------------------------------|-----------------------|
| @x y z a | Set the angles (in steps) for motors X, Y, Z, and A | @-1798 -280 853 -2651 |
| &n       | Allocate n bytes of memory on the Arduino           | &9000                 |
| ^        | Mark the start of a chunk of movement data          | ^                     |
| $        | Mark the end of a chunk of movement data            | $                     |

### Example

```motctl
&1024
^
@-1798 -280 853 -2651
@-1798 -280 853 -2651
$
&512
^
@-1795 -290 853 -2648
@-1768 -313 859 -2627
$
```