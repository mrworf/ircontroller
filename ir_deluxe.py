import sys
import serial
import threading
import Queue
import time
import logging
import json

class IRInterface (threading.Thread):

  def __init__(self, serialport, cbTerminate):
    threading.Thread.__init__(self)
    self.serialport = serialport
    self.daemon = True
    self.port = None
    self.state = "unknown"
    self.receiving = False
    self.state = "unknown"
    self.outgoing = Queue.Queue(20)
    self.ircodes = Queue.Queue(100)
    self.status = None
    self.firmware = "unknown"
    self.cbTerminate = cbTerminate

  def init(self):
    logging.info("Initializing IRDeluxe^2 interface")
    try:
      self.port = serial.Serial(self.serialport, baudrate=115200, rtscts=False, timeout=0.1, writeTimeout=0.1)
    except:
      logging.exception("Unable to open port")
      return False
    self.state = "unknown"
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
      self.start()

      self.serialbuffer = ""
      self.state = "configure"

      self.port.flushInput()
      self.port.flushOutput()
      self.port.sendBreak()
      msg = self.readIR(True)

      self.status = self.readStatus()
      logging.debug("Configuration: " + repr(self.status))
      return True

    except:
      logging.exception("Error during configure")
      logging.warning("Configure failed")
      return False

  def getResult(self, field):
    result = {}
    while field not in result:
      result = self.readIR(True)
    return result

  def readStatus(self):
    self.writeIR('{"requestStatus": 1}')
    return self.getResult("firmwareVersion")

  def setIndicatorLevel(self, level):
    level = max(0, min(100, level))
    str = '{"indicatorBrightness": %d}' % level
    self.writeIR(str)
    return self.getResult("commandResult")

  def enableReceive(self, enable):
    if self.receiving == enable:
      return

    if enable:
      self.writeIR('{"receiveMode":1}')
      self.receiving = True
    else:
      self.writeIR('{"receiveMode":0}')
      self.receiving = False
    return self.getResult("commandResult")

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

  def writeIR(self, cmd):
    """
    We need to make sure that carrierFreq is sent first, so we split it.
    """
    if type(cmd) is dict:
      if "carrierFreq" in cmd and "rawTransmit" in cmd:
        str = '{"carrierFreq": %d, "rawTransmit": %s}' % (cmd["carrierFreq"], json.JSONEncoder().encode(cmd["rawTransmit"]))
      else:
        str = json.JSONEncoder().encode(cmd)
    else:
      str = cmd
    logging.debug('Sending: %s', str)
    self.outgoing.put(str)

  def run(self):
    while True:
      data = ''
      try:
        data = self.port.read(1024)
      except:
        logging.error('Serial port exception, maybe device low voltage or disconnected.')
        self.cbTerminate()

      if len(data) > 0:
        self.serialbuffer += data
        self.interpretBuffer()
      try:
        data = self.outgoing.get(False)
        self.port.write(data)
        time.sleep(0.15)
      except:
        pass

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
            try:
              j = json.loads(self.serialbuffer[s:i+1])
              self.processIncoming(j)
            except:
              logging.exception('Failed to process JSON: "' + self.serialbuffer[s:i+1] + '", i = ' + repr(i) + ', s = ' + repr(s))
            self.serialbuffer = self.serialbuffer[i+2:]
            found = True
            s = 0
            # Remove the JSON
            break

  def processIncoming(self, data):
    self.ircodes.put(data)

class TimeoutException(Exception):
  pass
