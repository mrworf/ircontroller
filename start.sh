#!/bin/bash

# Locate the correct ttyACM for IR Deluxe
ACM=$(dmesg | grep -A1 "IR Deluxe" | grep ACM | tail -n 1 | egrep -oe 'ttyACM[0-9]')
if [ $? -eq 0 ]; then
	./server.py --tty /dev/${ACM}
	exit $?
fi
echo "No IR Deluxe device detected!"
exit 255

