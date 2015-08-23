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
    self.outgoing = Queue.Queue(20)
    self.ircodes = Queue.Queue(100)
    self.lock = threading.Lock()
    self.status = None
    self.clear2send = True
    self.firmware = "unknown"

  def init(self):
    logging.info("Initializing IRDeluxe^2 interface")
    self.port = serial.Serial(self.serialport, baudrate=115200, rtscts=True, timeout=0.1)
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
      self.queueIR('{"receiveMode":1}')
      self.receiving = True
    else:
      self.queueIR('{"receiveMode":0}')
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

      # Triplicate(?) the rawtransmit data
      toSend = cmd["rawTransmit"]
      final = toSend
      #final.extend(toSend)
      #final.extend(toSend)

      str = '{"carrierFreq": %d, "rawTransmit": %s}' % (cmd["carrierFreq"], json.JSONEncoder().encode(final))
    else:
      str = cmd

    if direct:
      self.port.write(str)
      time.sleep(0.150) # Sleep 150ms to avoid collision, this needs to be moved into the multiremote platform instead
      self.lastCommand = data
    else:
      self.outgoing.put(str)
    self.lock.release()

    return direct

  def run(self):
    while True:
      data = self.port.read(1024)

      if len(data) > 0:
        logging.debug('Data received: "' + data + '"')
        self.serialbuffer += data
        self.interpretBuffer()
      if not self.outgoing.empty() and self.clear2send:
        try:
          data = self.outgoing.get(False)
          #logging.debug("Sending: " + repr(data))
          self.clear2send = False
          self.port.write(data)
          time.sleep(0.15)
          self.lastCommand = data
        except:
          pass
          #logging.exception("Queue indicated data but get failed")


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
      resend = False
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
              resend = self.processIncoming(j) ? True : resend
            except:
              logging.exception('Failed to process JSON: "' + self.serialbuffer[s:i+1] + '", i = ' + repr(i) + ', s = ' + repr(s))
            self.serialbuffer = self.serialbuffer[i+2:]
            found = True
            s = 0
            # Remove the JSON
            break
      if resend and self.lastCommand is not None:
        logging.warn("Resending last command due to error on parsing")
        logging.debug("Command being resent is: " + repr(self.lastCommand))
        self.writeIR(self.lastCommand)

  def processIncoming(self, data):
    resend = False
    if "carrierFreq" in data and "rawTransmit" in data:
      logging.debug("Incoming IR sequence")
      self.ircodes.put(data)
    elif "IRDeluxeVersion" in data and data["state"] == "init":
      logging.info("IR Deluxe^2 detected, version %s" % data["IRDeluxeVersion"])
      self.firmware = data["IRDeluxeVersion"]
      self.lock.release()
    elif "firmwareVersion" in data:
      logging.info("Status received")
      self.status = data
      self.lock.release()
    elif "commandResult" in data:
      # This must be last!
      if data["commandResult"] > 0:
        logging.debug("Result from operation: " + repr(data))
        resend = True
      else:
        self.lastCommand = None

      self.clear2send = True
    return resend

class TimeoutException(Exception):
  pass
