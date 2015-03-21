#!/usr/bin/env python
#
# Tool to test learned IR commands
#
from ir import IRToy
import sys
import base64
import json

if len(sys.argv) != 2 and len(sys.argv) != 4:
  print "Usage: tester.py <input file> [<command> <serial port>]"
  exit(1)

jdata = open(sys.argv[1])
data = json.load(jdata)


if len(sys.argv) == 2:
	print "Available commands for device:"
	for cmd in data:
		print "  %s" % cmd
else:
	if sys.argv[2] not in data:
		print "ERROR: %s is not a recognized command" % sys.argv[2]
		exit(1)

	ir = IRToy(sys.argv[3])
	if not ir.init():
	  print "ERR: Unable to initialize IR Toy on %s" % sys.argv[3]
	  exit(1)

	if ir.writeIR(base64.urlsafe_b64decode(data[sys.argv[2]].encode("utf-8"))):
		print "INFO: Command sent successfully"
	else:
		print "ERR: Was unable to send command"
