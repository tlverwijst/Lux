#!/usr/bin/python
import RPi.GPIO as GPIO
import sys

#avoid 'in use' warnings
GPIO.setwarnings(False)

# set pin setup
GPIO.setmode(GPIO.BCM)

# arguments
pin = int(sys.argv[1])
mode = sys.argv[2]
state = sys.argv[3]

# pins allowed to be set by script
available_pins = [2, 3, 4, 17, 27, 22, 10, 9]

def setPinMode(mode):
    if mode == 'out':
        print "setup pin as output"
        GPIO.setup(pin, GPIO.OUT)
        return True
    elif mode == 'in':
        print "setup pin as input"
        GPIO.setup(pin, GPIO.IN)
        return True
    else:
        return False

def setPinState(state):
    if state == 'low':
        print "set pin state to LOW"
        GPIO.output(pin, GPIO.LOW)
        return True
    elif state == 'high':
        print "set pin state to HIGH"
        GPIO.output(pin, GPIO.HIGH)
        return True
    else:
        return False

try:
    if pin in available_pins:
        print "setting pin" + str(pin)
        mode_set = setPinMode(mode)

        if mode_set:
            state_set = setPinState(state)

        else:
            print "WARNING: could not set pin mode";

except:
        GPIO.cleanup()
        print "WARNING: problem while setting GPIO pin"
        print "Quiting..."