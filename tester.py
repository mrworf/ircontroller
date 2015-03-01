#!/usr/bin/env python
#
# Tool to test learned IR commands
#
from ir import IRToy
import sys
import base64
import json

if len(sys.argv) < 4:
  print "Usage: tester.py <serial port> <input file> <command>"
  exit(1)

ir = IRToy(sys.argv[1])
if not ir.init():
  print "Unable to initialize IR Toy"
  exit(1)

jdata = open(sys.argv[2])
data = json.load(jdata)

if ir.writeIR(base64.urlsafe_b64decode(data[sys.argv[3]].encode("utf-8"))):
  print "Command sent successfully"
else:
  print "Was unable to send command"
