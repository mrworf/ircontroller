#!/usr/bin/env python
"""
Tool to test learned IR commands
"""
from ir_deluxe import IRInterface
import sys
import base64
import json
import argparse

""" Parse it! """
parser = argparse.ArgumentParser(description="IR Deluxe^2 Test Tool", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('--tty', default="/dev/ttyACM0", help="TTY for IR Deluxe^2")
parser.add_argument('--command', help="Which command to send")
parser.add_argument('FILE', help="Location to load IR codes (in JSON format)")
config = parser.parse_args()

jdata = open(config.FILE)
data = json.load(jdata)

def terminated():
  print('Terminate received')

if not config.command:
  print("Available commands in %s:" % config.FILE)
  for cmd in data:
    print("  %s" % cmd)
else:
  if config.command not in data:
    print("ERROR: %s is not a recognized command" % config.command)
    sys.exit(1)

  sys.stdout.write("Initializing IR Deluxe^2...")
  sys.stdout.flush()
  ir = IRInterface(config.tty, terminated)
  if not ir.init():
    print("ERR: Unable to initialize IR interface on %s" % config.tty)
    sys.exit(1)

  ir.writeIR(data[config.command])
  result = ir.readIR(True)
  if result["commandResult"] is "0":
    print("INFO: Command sent successfully")
  else:
    print("ERR: Was unable to send command: " + repr(result))
