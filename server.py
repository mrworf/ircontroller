#!/usr/bin/env python

"""
REST api for sending/receiving IR commands
"""
from ir_deluxe import IRInterface
from flask import Flask, request
from flask import jsonify
from collections import deque
import sys
import base64
import time
import logging
import argparse
import threading
import Queue
import os

from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop


""" Parse it! """
parser = argparse.ArgumentParser(description="IR-2-REST Gateway", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('--logfile', metavar="FILE", help="Log to file instead of stdout")
parser.add_argument('--port', default=5001, type=int, help="Port to listen on")
parser.add_argument('--listen', metavar="ADDRESS", default="0.0.0.0", help="Address to listen on")
parser.add_argument('--tty', default="/dev/ttyACM0", help="TTY for IR Deluxe^2")
parser.add_argument('--debug', default="/dev/hidraw1", help="Enable debugging, usually needs root")
config = parser.parse_args()

""" Setup logging """
logging.basicConfig(filename=config.logfile, level=logging.DEBUG, format='%(filename)s@%(lineno)d - %(levelname)s - %(message)s')

""" Disable some logging by-default """
logging.getLogger("Flask-Cors").setLevel(logging.ERROR)
logging.getLogger("werkzeug").setLevel(logging.ERROR)

app = Flask(__name__)

@app.route("/")
def api_root():
  msg = {
    "hardware-status" : ir.status,
    "pending-write" : ir.outgoing.qsize(),
    "pending-read" : ir.ircodes.qsize(),
  }
  ret = jsonify(msg)
  ret.status_code = 200
  return ret

@app.route("/read")
def api_read():
  """
  Reads an IR command from the IR receiver.
  NOTE! This API call is not protected against someone
        doing /write calls at the same time.
  """
  cmd = ir.readIR()
  msg = {}
  if cmd != None:
    msg["status"] = 200
    msg["data"] = base64.urlsafe_b64encode(cmd)
  else:
    msg["status"] = 404

  ret = jsonify(msg)
  ret.status_code = 200
  return ret

@app.route("/write", methods=['POST'])
def api_write():
  """Queues a IR command for transmission"""
  cmd = request.get_json(force=True)
  msg = {
    "status" : 200
  }
  queue.add(cmd)
  ret = jsonify(msg)
  ret.status_code = 200
  return ret

"""
This class is used to make sure we successfully send the IR, it will
compensate for any errors which occurs during communication with the
IR transmitter.
"""
class SendQueue (threading.Thread):
  def __init__(self):
    threading.Thread.__init__(self)
    self.queue = Queue.Queue(20)
    self.daemon = True
    self.start()

  def add(self, data):
    self.queue.put(data)

  def run(self):
    while (True):
      data = self.queue.get()
      tries = 3
      while tries != 0:
        ir.writeIR(data)
        tries = tries - 1

        result = ir.readIR(True)
        time.sleep(0.15) # This is a bit of a cheat
        tmp = ir.readIR(False)
        if tmp != None:
          result = tmp
        if result["commandResult"] is not 0:
          logging.error("Failed to send, due to: %s" % repr(result))
          logging.error("Command was: " + repr(data))
          logging.error("Tries left: %d" % tries)
          # Dump buffer
          if debugbuf is not None:
            for line in debugbuf.buffer:
              logging.error("DebugBuf: %s" % line)
            debugbuf.buffer.clear()
        else:
          tries = 0

class Debug (threading.Thread):
  def __init__(self):
    threading.Thread.__init__(self)
    self.daemon = True
    self.buffer = deque(20*"", 20)

  def init(self, port):
    try:
      self.input = open(port, "r")
    except:
      logging.exception("Failed to open %s, maybe you need root?" % port)
      return False
    self.start()
    return True

  def run(self):
    while (True):
      line = self.input.readline().rstrip()
      self.buffer.append(line)


def stopServer():
  IOLoop.instance().stop()

if __name__ == "__main__":
  ir = IRInterface(config.tty, stopServer)
  if config.debug is not None:
    debugbuf = Debug()
    if debugbuf.init(config.debug) is False:
      sys.exit(3)
  else:
    debugbuf = None
  if not ir.init():
    logging.error("Unable to start due to serial port failure")
    sys.exit(2)
  queue = SendQueue()
  logging.info("IR-2-REST Gateway running")
  http_server = HTTPServer(WSGIContainer(app))
  http_server.listen(config.port)
  IOLoop.instance().start()
  sys.exit(255)
