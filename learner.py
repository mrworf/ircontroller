#!/usr/bin/env python
"""
Tool to aid with learning IR commands
"""
from ir_deluxe import IRInterface
from irinterpreter import recognize
import json
import sys
import base64
import logging
import argparse

""" Parse it! """
parser = argparse.ArgumentParser(description="IR Deluxe^2 Learn Tool", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('--tty', default="/dev/ttyACM0", help="TTY for IR Deluxe^2")
parser.add_argument('--file', help="Location to load/save IR codes (in JSON format)")
parser.add_argument('--raw', action="store_true", default=False, help="Store all IR codes as raw format, do not interpret")
parser.add_argument('--convert', action="store_true", default=False, help="Interpret existing codes")
parser.add_argument('--remove', action="store_true", default=False, help="Remove any IR code which cannot be interpreted")
parser.add_argument('--learn', action="store_true", default=False, help="Start learning mode")
config = parser.parse_args()

logging.basicConfig(level=logging.WARN, format='%(asctime)s - %(filename)s@%(lineno)d - %(levelname)s - %(message)s')

changed = False
ir = IRInterface(config.tty)
if config.learn:
  sys.stdout.write("Initializing IR Deluxe^2...")
  sys.stdout.flush()

  if not ir.init():
    print "Error"
    logging.error("Unable to initialize IR Toy (%s)" % config.tty)
    sys.exit(1)

  ir.enableReceive(True)
  status = ir.readStatus()
  print "OK\nFirmware: %s\nBootloader: %s\n" % (status["firmwareVersion"], status["bootloaderVersion"])

if config.file is None:
  sys.exit(0)

if config.file:
  try:
    jdata = open(config.file)
    data = json.load(jdata)
    jdata.close()
  except:
    data = {}

  if len(data):
    if config.convert:
      print "Converting commands in %s:" % config.file
    else:
      print "Commands in %s:" % config.file
    removed = []
    for x in data:
      t = data[x]
      if "rawTransmit" in t:
        t = "Raw IR pulse-train"
      elif "necSend" in t:
        t = "NEC, address = %d, command = %d" % (t["necSend"][0], t["necSend"][1])
      elif "sircSend" in t:
        t = "Sony IR, address = %d, command = %d" % (t["sircSend"][0], t["sircSend"][1])
      elif "jvcSend" in t:
        t = "JVC, address = %d, command = %d" % (t["jvcSend"][0], t["jvcSend"][1])
      else:
        t = "Unknown format, are you running the latest version of ircontroller?"
      if config.convert and "rawTransmit" in data[x]:
        rec = recognize(data[x]["rawTransmit"])
        if rec is None and config.remove:
          r = None
          removed.append(x)
        elif rec is None:
          r = "Unknown (unchanged)"
        else:
          data[x] = {rec["name"] + "Send": [rec["address"],rec["command"]]}
          r = rec["name"].upper()
          changed = True
        if r is not None:
          print "%12s : %s > %s" % (x, t, r)
      else:
        print "%12s : %s" % (x, t)
    if len(removed):
      changed = True
      print "\nThe following commands were removed:"
      for x in removed:
        del data[x]
        print "  " + x

if config.learn and config.file:
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
      sys.stdout.write("Ready to receive IR sequence")
      if count > 1 or config.raw:
        sys.stdout.write(" (Attempt #%d, need minimum 2)" % count)
      sys.stdout.write(": ")
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

      # See if we can interpret this, if so, skip cumbersome filtering
      rec = recognize(cmd["rawTransmit"])
      if rec is not None:
        print "Detected %s code." % rec["name"].upper()
        cmd = {rec["name"] + "Send": [rec["address"],rec["command"]]}
        break

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
    changed = True
    data[name] = cmd;

if config.file:
  print ""
  if changed:
    sys.stdout.write("Saving commands...")
    sys.stdout.flush()
    jdata = open(config.file, "w")
    jdata.write(json.dumps(data))
    jdata.close()
    print "OK"
  else:
    print "No changes made."
