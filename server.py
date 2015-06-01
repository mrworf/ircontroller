#!/usr/bin/env python

"""
REST api for sending/receiving IR commands
"""
from ir import IRToy
from flask import Flask
from flask import jsonify
import base64
import time
import logging
import argparse

""" Parse it! """
parser = argparse.ArgumentParser(description="IR-2-REST Gateway", formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('--logfile', metavar="FILE", help="Log to file instead of stdout")
parser.add_argument('--port', default=5001, type=int, help="Port to listen on")
parser.add_argument('--listen', metavar="ADDRESS", default="0.0.0.0", help="Address to listen on")
parser.add_argument('--tty', default="/dev/ttyACM0", help="TTY for USB IR Toy")
config = parser.parse_args()

""" Setup logging """
logging.basicConfig(filename=config.logfile, level=logging.DEBUG, format='%(asctime)s - %(filename)s@%(lineno)d - %(levelname)s - %(message)s')

""" Disable some logging by-default """
logging.getLogger("Flask-Cors").setLevel(logging.ERROR)
logging.getLogger("werkzeug").setLevel(logging.ERROR)

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
  logging.info("Queueing command for transmission")
  ir.queueIR(cmd)
  ret = jsonify(msg)
  ret.status_code = 200
  return ret

if __name__ == "__main__":
  ir = IRToy(config.tty)
  app.debug = True
  logging.info("IR-2-REST Gateway running")
  app.run(host=config.listen, port=config.port, use_debugger=False, use_reloader=False)
