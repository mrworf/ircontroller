import serial
import threading
import time
import Queue

class IRToy (threading.Thread):
  state = "unknown"
  outgoing = Queue.Queue(10)
  
  def __init__(self, serialport):
    threading.Thread.__init__(self)
    self.serialport = serialport
    self.daemon = True

  def init(self):
    print "Initializing USB IR Toy interface"
    
    self.port = serial.Serial(self.serialport, baudrate=115200)
    self.state = "unknown"
    self.port.flushInput()
    self.port.flushOutput()

    self.port.write("\x00\x00\x00\x00\x00")
    time.sleep(0.5)
    self.port.flushOutput()
    self.port.write("S")
    
    result = self.port.read(3)
    if result != "S01":
      print "Failed to initialize USB IR Toy"
      return False
    # Make sure we get details when we transmit
    self.port.write("\x24\x25\x26")
    
    print "Interface online"
    self.start()
    return True
    
  def readIR(self):
    """Reads a complete IR command from the receiver and returns the buffer"""
    self.port.flushInput()
    
    p = b = 0x00
    cmd = ""
    while not (p == '\xff' and b == '\xff'):
      p = b
      b = self.port.read()
      cmd += b
    return cmd

  def queueIR(self, cmd):
    self.outgoing.put(cmd)
    
  def writeIR(self, cmd):
    """Sends a complete IR command which has previously been received with readIR()"""
    self.port.write("\x03")

    # Deal with any IR commands which haven't been read
    bytes2send = ord(self.port.read(1))
    while bytes2send != 62:
      print "Need to flush old buffer (bytes2send = %d)" % bytes2send
      p = b = bytes2send
      while not (p == '\xff' and b == '\xff'):
        p = b
        b = self.port.read()
      print "Flushed old IR command, lets try again"
      bytes2send = ord(self.port.read(1))

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
      self.port.write(buffer)
      bytes2send = ord(self.port.read(1))
      
    resp = self.port.read(1)
    if resp != "t":
      print "ERROR: Protocol error, aborting"
      return False
      
    high = ord(self.port.read(1))
    low = ord(self.port.read(1))
    sent = high << 8 | low
    if sent != tosend:
      print "ERROR: Wanted to send %d bytes, sent %d" % (tosend, sent)
    result = self.port.read(1)
    return result == "C"

  def run(self):
    while True:
      cmd = self.outgoing.get(True)
      if self.writeIR(cmd):
        print "INFO: IR command sent successfully"
      else:
        print "WARN: IR command failed to send"
        
