#!/bin/bash

while true; do
	# Locate the correct ttyACM for IR Deluxe
  TTY=$(udevadm info -e | grep -oE '/dev/ttyACM[0-9]+' | tail -n 1 | xargs -I {} basename {})
  HID=$(udevadm info -e | grep -oE '/dev/hidraw[0-9]+' | tail -n 1 | xargs -I {} basename {})

	if [ $? -eq 0 -a -e /dev/${TTY} ]; then
		./server.py --tty /dev/${TTY} --debug /dev/${HID}
		echo "Server terminated"
	fi
	echo "No IR Deluxe device detected!"
	echo "Sleeping 1s and retrying"
	sleep 1s
done

