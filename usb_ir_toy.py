import serial
import threading
import time
import Queue
import logging

class IRInterface (threading.Thread):
  state = "unknown"
  outgoing = Queue.Queue(10)

  def __init__(self, serialport):
    threading.Thread.__init__(self)
    self.serialport = serialport
    self.daemon = True
    self.port = None
    self.state = "unknown"
    self.start()

  def init(self):
    logging.info("Initializing USB IR Toy interface")
    if self.port is None:
      self.port = serial.Serial(self.serialport, baudrate=115200, rtscts=False, timeout=10)
      self.state = "unknown"
      return self.configure()
    return True

  def deinit(self):
    logging.info("Closing down USB IR Toy interface")
    if self.port is None:
      return
    self.port.close()
    self.port = None
    self.state = "unknown"
    return

  def configure(self):
    while True:
      try:
        logging.info("Configuring USB IR Toy")

        self.port.flushInput()
        self.port.flushOutput()

        self.write("\x00\x00\x00\x00\x00")
        time.sleep(0.1)
        self.write("S")

        result = self.read(3)
        if result != "S01":
          logging.error("Failed to initialize USB IR Toy")
          return False
        # Make sure we get details when we transmit
        self.write("\x24\x25\x26")

        logging.info("Interface online")
        return True
      except:
        logging.warning("Configure failed, retrying")
        time.sleep(1)


  def readIR(self):
    """Reads a complete IR command from the receiver and returns the buffer"""
    self.port.flushInput()

    p = b = 0x00
    cmd = ""
    while not (p == '\xff' and b == '\xff'):
      p = b
      b = self.read()
      cmd += b
    return cmd

  def queueIR(self, cmd):
    self.outgoing.put(cmd)

  def writeIR(self, cmd):
    """Sends a complete IR command which has previously been received with readIR()"""
    while True:
      try:
        self.write("\x03")

        # Deal with any IR commands which haven't been read
        bytes2send = ord(self.read(1))
        while bytes2send <> 62:
          logging.debug("Need to flush old buffer (bytes2send = %d)" % bytes2send)
          p = b = bytes2send
          while not (p == '\xff' and b == '\xff'):
            p = b
            b = self.read()
          logging.debug("Flushed old IR command, lets try again")
          bytes2send = ord(self.read(1))

        tosend = len(cmd)
        while True:
          if len(cmd) == 0:
            break
          elif bytes2send < len(cmd):
            buffer = cmd[:bytes2send]
            cmd = cmd[bytes2send:]
          else:
            buffer = cmd
            cmd = ""
          self.write(buffer)
          bytes2send = ord(self.read(1))

        resp = self.read(1)
        if resp != "t":
          logging.error("Protocol error, aborting")
          return False

        high = ord(self.read(1))
        low = ord(self.read(1))
        sent = high << 8 | low
        if sent != tosend:
          logging.error("Wanted to send %d bytes, sent %d" % (tosend, sent))
        result = self.read(1)
        return result == "C"
      except:
        logging.warning("Timeout sending IR, retrying.")
        self.configure()

  def run(self):
    while True:
      cmd = self.outgoing.get(True)
      self.init() # Safe to call multiple times
      if self.writeIR(cmd):
        logging.info("IR command sent successfully")
        time.sleep(0.150) # Avoid conflict with other devices
      else:
        logging.warning("IR command failed to send")
      if self.outgoing.empty():
        logging.info("No more pending commands, shutting down IR")
        self.deinit()

  def read(self, count = 1):
    data = self.port.read(count)
    if len(data) <> count:
      logging.error("Requested %d bytes, got %d" % (count, len(data)))
      raise TimeoutException("Read Timeout")
    return data

  def write(self, data):
    count = 0
    #for byte in data:
    #  count += self.port.write(byte)
    count = self.port.write(data)
    time.sleep(0.01)
    if len(data) <> count:
      logging.error("Wanted to write %d bytes, wrote %d" % (len(data), count))
      raise TimeoutException("Write Timeout")
    return count

class TimeoutException(Exception):
  pass
