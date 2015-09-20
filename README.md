# ircontroller
REST interface to IR Deluxe², allowing easy use of IR receive/send from the network

# Requirements
- python-flask
- python-serial
- python-tornado

And of course, a IR Deluxe² dongle.

# server.py
This is the REST interface daemon. It creates a web server on port 5001 which listens for incoming requests which will be queued and sent over the IR Deluxe² hardware.

## Options
- --tty Alows you to override the default /dev/ttyACM0 for accessing the hardware
- --logfile Redirect output to a logfile instead of stdout
- --port Override the default port of 5001
- --listen Override the default interface to listen on (default is 0.0.0.0, that is, any)
- --debug Saves extra logging from the debug port of the hardware when an error occurs. _(Requires root)_

## REST endpoints

### GET /read
Returns an IR sequence as understood by the hardware.

**This is a BLOCKING endpoint and not really intended for much use.** It was added more for completeness rather than as a way of reacting to IR. The IR Deluxe² hardware is primarily designed for blasting IR, not receiving.

### POST /write
Queues an IR sequence to be sent. This sequence was obtained from either /read endpoint or by using the learner.py tool.

Sending of IR is entirely fire-and-forget(tm) and you will always get a 200 success back. However, should the hardware fail due to some issue, the server will try up to two more times. It will also log any pertinent data to help with debugging, so please submit this information (preferably with --debug enabled) when reporting issues.

_Note, sending raw IR sequence requires the presence of the carrierFreq field in the JSON data, or it will fail_

# learner.py
The learning tool which allows you to record IR sequences from remotes, input pronto HEX codes and also convert previously raw IR sequences into native IR formats if supported.

## Options
- --tty Alows you to override the default /dev/ttyACM0 for accessing the hardware
- --file Points out the JSON file to write (and if it exists, load before continuing)
- --raw Forces the tool to record all learned IR as raw data instead of trying to detect and use native replay
- --convert Converts existing raw recordings to native replay
- --remove Removes any non-native items during conversion
- --learn Uses the hardware to learn IR codes
- --pronto Allows you to input HEX codes (from http://files.remotecentral.com/library/3-1/index.html for example) and convert them into the format understood by IR Deluxe². If --raw is specified, no detection is runned.

## Examples

Show existing codes in json:\
`learner.py --file ircodes.json`

Try and convert old raw recordings into native replay:\
`learner.py --file ircodes.json --convert`

Record new IR:\
`learner.py --file newir.json --learn`

Convert Pronto HEX codes:\
`learner.py --file newir.json --learn --pronto`


# tester.py
Takes any JSON file generated by learner.py and allows you to replay it using the IR Deluxe² hardware.

## Options
You must always provide a JSON file, without parameters it will show existing commands.

- --tty Alows you to override the default /dev/ttyACM0 for accessing the hardware
- --command Which command to transmit