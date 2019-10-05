#!/usr/bin/env python

import serial
import json
import sys
import base64
import logging

def loadData(file):
	try:
	  jdata = open(file)
	  data = json.load(jdata)
	  jdata.close()
	except:
	  data = {}
	return(data)

cmds = []
#cmds.append(loadData("../ir-devices/displays/jvc-rs1.json"))
#cmds.append(loadData("../ir-devices/accessories/elite_screens-electric100h.json"))
#cmds.append(loadData("../ir-devices/displays/lg-55la7400.json"))
cmds.append(loadData("../ir-devices/accessories/avaccess-4ksw41-h2.json"))

port = serial.Serial("/dev/ttyACM0", baudrate=115200, rtscts=True, timeout=0.1)
if port is None:
  logging.error("Unable to open serial port, abort")
  exit(1)

port.sendBreak()

c = 0
while True:
	for x in cmds:
		for y in x:
			print "Sending " + y
			if 'rawTransmit' in x[y]:
				final = x[y]["rawTransmit"]
				final = final + final + final
				str = '{"carrierFreq": %d, "rawTransmit": %s}' % (x[y]["carrierFreq"], json.JSONEncoder().encode(final))
			else:
				str = '{"%s":%s}' % ('necSend', x[y]['necSend'])
			port.write(str)
			c = c + 1

			if c % 10 == 0:
				dummy = port.read(1024)
				if '"commandResult": 2,' in dummy or '"commandResult": 4,' in dummy:
					print dummy
					exit(255)
