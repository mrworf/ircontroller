#!/usr/bin/env python
"""
Tool to aid with learning IR commands
"""
from ir_deluxe import IRInterface
import json
import sys
import base64
import logging

logging.basicConfig(level=logging.WARN, format='%(asctime)s - %(filename)s@%(lineno)d - %(levelname)s - %(message)s')

if len(sys.argv) < 3:
  print "Usage: learner.py <serial port> <output file>"
  exit(1)

ir = IRInterface(sys.argv[1])
if not ir.init():
  print "Unable to initialize IR Toy"
  exit(1)

ir.setIndicatorLevel(50)
status = ir.readStatus()
print repr(status)
ir.enableReceive(True)

try:
  jdata = open(sys.argv[2])
  data = json.load(jdata)
  jdata.close()
except:
  data = {}

while True:
  sys.stdout.write("Name IR command (or enter to end): ")
  sys.stdout.flush()
  name = sys.stdin.readline().strip()
  if name == "":
    break

  while True:
    sys.stdout.write("Ready for IR command: ")
    sys.stdout.flush()
    ir.clearIR()
    cmd = ir.readIR(True)
    if cmd == None:
      print "Error reading IR command"
      continue
    else:
      print "OK"
      break

  data[name] = cmd;

jdata = open(sys.argv[2], "w")
jdata.write(json.dumps(data))
jdata.close()
print "Saved"
