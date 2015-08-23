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

# TODO: Issue enabling receive after running status command
ir.enableReceive(True)
#ir.setIndicatorLevel(50)
status = ir.readStatus()
print "Firmware: %s\nBootloader: %s\n" % (status["firmwareVersion"], status["bootloaderVersion"])

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

  input = []
  count = 0
  while True:
    count = count + 1
    sys.stdout.write("Ready for IR command (Attempt #%d, need minimum 2): " % count)
    sys.stdout.flush()
    cmd = {"rawTransmit":[]}
    # Avoid too short
    while cmd != None and len(cmd["rawTransmit"]) < 10:
      ir.clearIR()
      cmd = ir.readIR(True)
    # Throw an error if we get none
    if cmd == None:
      print "Error reading IR command"
      count = count - 1
      continue

    # Continue
    print "OK"
    input.append(cmd)
    if len(input) > 1: 
      # Now we compare
      length = {}
      # Group by size
      for x in input:
        key = "%d" % len(x["rawTransmit"])
        if key in length:
          length[key].append(x)
        else:
          length[key] = [x]
      # Pick the one with highest count
      candidate = None
      for x in length:
        v = length[x]
        if candidate is None or len(candidate) < len(v):
          candidate = v
      if len(candidate) < 2:
        continue
      print "Candidates: %d" % len(candidate)

      # Now, calculate the max delta
      mindelta = 70000 # IRDeluxe is limited at max uint16
      totdelta = 0
      ideal = None
      deltas = []
      # Horrible code, but it will find the entry with least delta
      for z in range(len(candidate)):
        baseline = candidate[z]
        for x in range(z+1, len(candidate)):
          tester = candidate[x]
          maxdelta = 0
          for y in range(len(baseline["rawTransmit"])):
            delta = abs(baseline["rawTransmit"][y] - tester["rawTransmit"][y])
            if delta > maxdelta:
              maxdelta = delta
          deltas.append(maxdelta)
          if totdelta < maxdelta:
            totdelta = maxdelta
          if maxdelta < mindelta:
            mindelta = maxdelta
            ideal = tester
      deltas.sort()
      # Statistics...
      print "Maximum Delta: %d" % totdelta
      print "Minimum Delta: %d" % mindelta
      print "Average Delta: %d" % (sum(deltas) / len(deltas))
      print "Median  Delta: %d" % (deltas[len(deltas)/2])
      #print "Represented by: " + repr(ideal)

      # Ideally, you want less than 5ms, but 25ms is acceptable
      choice = "n"
      if mindelta < 5:
        sys.stdout.write("We have a great candidate (<5ms jitter), do you wish to save? (Y/n/r) ")
        sys.stdout.flush()
        choice = sys.stdin.readline().strip().lower()
        if choice == "":
          choice = "y"
      elif mindelta < 25:
        sys.stdout.write("We have a good candidate (<25ms jitter), do you wish to save? (Y/n/r) ")
        sys.stdout.flush()
        choice = sys.stdin.readline().strip().lower()
        if choice == "":
          choice = "y"
      if choice == "y":
        break
      elif choice == "r":
        print "Restarting collection of IR codes"
        count = 0
        input = []

  print "Saved"    

  data[name] = cmd;

jdata = open(sys.argv[2], "w")
jdata.write(json.dumps(data))
jdata.close()
print "Saved"
