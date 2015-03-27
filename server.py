#!/usr/bin/env python
#
# REST api for sending/receiving IR commands
#
from ir import IRToy
from flask import Flask
from flask import jsonify
import base64
import time

cfg_SerialPort = "/dev/ttyACM0"
cfg_ServerAddr = "0.0.0.0"
cfg_ServerPort = 5001

app = Flask(__name__)

@app.route("/")
def api_root():
  return "Hi there"

@app.route("/read")
def api_read():
  """
  Reads an IR command from the IR receiver.
  NOTE! This API call is not protected against someone
        doing /write calls at the same time.
  """
  cmd = ir.readIR()
  msg = {
    "data" : base64.urlsafe_b64encode(cmd)
  }
  if cmd != None:
    msg["status"] = 200
  else:
    msg["status"] = 404
    
  ret = jsonify(msg)
  ret.status_code = 200
  return ret

@app.route("/write/<data>")
def api_write(data):
  """Queues a IR command for transmission"""
  data = data.encode("utf-8")
  cmd = base64.urlsafe_b64decode(data)
  msg = {
    "status" : 200
  }
  print "INFO: Queueing command for transmission"
  ir.queueIR(cmd)
  ret = jsonify(msg)
  ret.status_code = 200
  return ret

if __name__ == "__main__":
  ir = IRToy(cfg_SerialPort)
  if not ir.init():
    print "ERROR: Unable to initialize IR module"
    exit(1)
  app.debug = True
  app.run(host=cfg_ServerAddr, port=cfg_ServerPort, use_debugger=False, use_reloader=False)
  #while True:
  #  time.sleep(5)