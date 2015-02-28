#!/usr/bin/env python
#
# Tool to aid with learning IR commands
#
from ir import IRToy
import sys
import base64

if len(sys.argv) < 3:
  print "Usage: learner.py <serial port> <output file>"
  exit(1)

ir = IRToy(sys.argv[1])
if not ir.init():
  print "Unable to initialize IR Toy"
  exit(1)

f = open(sys.argv[2], "a")

while True:
  sys.stdout.write("Name IR command (or enter to end): ")
  sys.stdout.flush()
  name = sys.stdin.readline().strip()
  if name == "":
    break
  
  while True:
    sys.stdout.write("Ready for IR command: ")
    sys.stdout.flush()
    cmd = ir.readIR()
    if cmd == None:
      print "Error reading IR command"
      continue
    else:
      print "OK"
      break
    
  f.write("{\n");
  f.write("  \"id\" : \"%s\",\n" % name);
  f.write("  \"data\" : \"%s\"\n" % base64.urlsafe_b64encode(cmd));
  f.write("}\n");

print "Saved"
f.close()
