#!/bin/bash

# Locate the correct ttyACM for IR Deluxe
TTY=$(dmesg | grep ACM | tail -n 1 | egrep -oe 'ttyACM[0-9]')
if [ $? -eq 0 -a -e /dev/${TTY} ]; then
	./server.py --tty /dev/${TTY}
	exit $?
fi
echo "No IR Deluxe device detected!"
exit 255

