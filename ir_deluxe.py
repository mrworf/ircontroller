import serial
import threading
import time
import Queue
import logging
import json

class IRInterface (threading.Thread):

  def __init__(self, serialport):
    threading.Thread.__init__(self)
    self.serialport = serialport
    self.daemon = True
    self.port = None
    self.state = "unknown"
    self.receiving = False
    self.state = "unknown"
    self.outgoing = Queue.Queue(10)
    self.ircodes = Queue.Queue(100)
    self.lock = threading.Lock()
    self.status = None

  def init(self):
    logging.info("Initializing IRDeluxe^2 interface")
    self.port = serial.Serial(self.serialport, baudrate=115200, rtscts=False, timeout=0.1)
    if self.port is None:
      logging.error("Unable to open serial port, abort")
      exit(1)

    self.state = "unknown"
    self.start()
    return self.configure()

  def deinit(self):
    logging.info("Closing down interface")
    self.port.close()
    self.port = None
    self.state = "unknown"
    return

  def configure(self):
    try:
      logging.info("Configuring interface")

      self.serialbuffer = ""
      self.state = "configure"

      self.port.flushInput()
      self.port.flushOutput()

      self.lock.acquire()
      self.port.sendBreak()
      return True

    except:
      logging.exception("Error during configure")
      logging.warning("Configure failed, retrying")
      return False

  def readStatus(self):
    self.lock.acquire(True)
    self.outgoing.put('{"requestStatus": 1}')
    # We will get released from the other thread, thus we call it AGAIN
    self.lock.acquire(True)
    self.lock.release()
    return self.status

  def setIndicatorLevel(self, level):
    if level > 100:
      level = 100
    elif level < 0:
      level = 0
    str = '{"indicatorBrightness": %d}' % level
    self.outgoing.put(str)

  def enableReceive(self, enable):
    if self.receiving == enable:
      return
    if enable:
      self.queueIR('{"receiveMode" : 1}')
      self.receiving = True
    else:
      self.queueIR('{"receiveMode" : 0}')
      self.receiving = False

  def clearIR(self):
    while self.readIR() is not None:
      pass

  def readIR(self, blocking=False):
    if blocking:
      return self.ircodes.get()
    else:
      try:
        return self.ircodes.get(False)
      except:
        return None

  def queueIR(self, cmd):
    self.writeIR(cmd, False)

  def writeIR(self, cmd, direct=True):
    """
    We need to make sure that carrierFreq is sent first, so we split it. We also
    need to wait for init, so use the lock.
    """
    self.lock.acquire(True)
    if type(cmd) is dict:
      str = '{"carrierFreq" : %d, "rawTransmit": %s}' % (cmd["carrierFreq"], json.JSONEncoder().encode(cmd["rawTransmit"]))
    else:
      str = cmd

    if direct:
      self.port.write(str)
    else:
      self.outgoing.put(str)
    self.lock.release()
    return direct

  def run(self):
    while True:
      data = self.port.read(1024)

      if len(data) > 0:
        self.serialbuffer += data
        self.interpretBuffer()
      elif not self.outgoing.empty():
        try:
          data = self.outgoing.get(False)
          self.port.write(data)
        except:
          logging.exception("Queue indicated data but get failed")


  def interpretBuffer(self):
    # Find the start
    s = self.serialbuffer.find("{")
    e = self.serialbuffer.find("}")
    if s == -1:
      #logging.warning("No valid data in buffer: " + self.serialbuffer)
      self.serialbuffer = ""
    elif e > -1:
      # Count our way to the end
      b = 0
      found = True
      while found:
        found = False
        section = False
        for i in range(s, len(self.serialbuffer)):
          if self.serialbuffer[i] == '{':
            section = True
            b += 1
          elif self.serialbuffer[i] == '}':
            b -= 1
          if b == 0 and section:
            # Found a section...
            j = json.loads(self.serialbuffer[s:i+1])
            self.processIncoming(j)
            self.serialbuffer = self.serialbuffer[i+2:]
            found = True
            s = 0
            # Remove the JSON
            break

  def processIncoming(self, data):
    if "carrierFreq" in data and "rawTransmit" in data:
      logging.debug("Incoming IR sequence")
      self.ircodes.put(data)
    elif "IRDeluxeVersion" in data and data["state"] == "init":
      logging.info("IR Deluxe^2 detected, version %s" % data["IRDeluxeVersion"])
      self.lock.release()
    elif "firmwareVersion" in data:
      logging.info("Status received")
      self.status = data
      self.lock.release()
    elif "commandResult" in data:
      # This must be last!
      if data["commandResult"] > 0:
        logging.debug("Result from operation: " + repr(data))

class TimeoutException(Exception):
  pass
