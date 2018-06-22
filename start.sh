#!/bin/bash

while true; do
	# Locate the correct ttyACM for IR Deluxe
	TTY=$(dmesg | grep ACM | tail -n 1 | egrep -oe 'ttyACM[0-9]')
	HID=$(dmesg | grep hidraw | tail -n 1 | egrep -oe 'hidraw[0-9]')
	if [ $? -eq 0 -a -e /dev/${TTY} ]; then
		./server.py --tty /dev/${TTY} --debug /dev/${HID}
		echo "Server terminated"
	fi
	echo "No IR Deluxe device detected!"
	echo "Sleeping 1s and retrying"
	sleep 1s
done

