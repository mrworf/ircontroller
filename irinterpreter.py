import copy

"""
 * Takes an array of on/off pulses in us format
 * and merges any pulses lower than a certain duration
 *
 * @param seq IR Sequence
 * @param cutoff Min signal length, anything below this is merged 
 *               with previous cycle
 *
 * @return cleaned Sequence
 *
 * @todo Only deals with on pulses
"""
def dejitter(seq, cutoff):
	result = []

	i = 0
	o = 0
	while i != (len(seq) - len(seq) % 2):
		high = seq[i]
		low  = seq[i+1]
		i += 2

		if (high < cutoff or low < cutoff) and len(result) > 0:
			result[len(result)-1] += (high + low)
		else:
			result.append(high)
			result.append(low)
	return result

"""
 * Compare A with B where B may deviate up to a certain
 * amount.
 *
 * @param a Value to test
 * @param b Value to test
 *
 * @return true if a match, false if not
"""
def dcmp(a, b):
	devitation = round(b * 0.18)
	return (b + devitation) >= a and (b - devitation) <= a

"""
 * Consumes X amount of bits
 *
 * @param input Array of time in us
 * @param bits Number of bits to read
 * @param on_h Time for high (logical 1)
 * @param on_l Time for low  (logical 1)
 * @param off_h Time for high (logical 0)
 * @param off_l Time for low  (logical 0)
 * @param allowTrail If true, allow last low to be equal or larger than required
 *
 * @return an array consisting of value, time and trail (always zero unless allowTrail)
 *
 * value is the bits combined into a number
 * time is the amount of time consumed from the array
 * trail is the amount of time the last off value had (or zero if allowTrail is false)
"""
def readbits(input, bits, on_h, on_l, off_h, off_l, allowTrail=False):
	result = 0
	time = 0
	trail = 0
	i = 0
	while i != bits and len(input) > 0:
		h = input.pop(0)
		l = input.pop(0)

		if dcmp(h, on_h) and dcmp(l, on_l):
			result |= 1 << (bits - i - 1)
		elif allowTrail and (l > on_l or l > off_l) and i == (bits-1):
			trail = l
		elif not dcmp(h, off_h) or (not dcmp(l, off_l) and l != 65535):
			return None
		time += (h + l)
		i += 1
	return {"value": result, "time": time, "trail": trail}

"""
Counts the number of bits which conform to the on/off pattern
provided. Will return upon first non-confirming bit.

 @param input Array of time in us
 @param bits Number of bits to read
 @param on_h Time for high (logical 1)
 @param on_l Time for low  (logical 1)
 @param off_h Time for high (logical 0)
 @param off_l Time for low  (logical 0)
 @param allowTrail If true, allow last low to be equal or larger than required

 @return bits found
"""
def countbits(input, on_h, on_l, off_h, off_l, allowTrail=False):
	result = 0
	time = 0
	trail = 0
	i = 0
	for i in range(0, len(input), 2):
		h = input[i]
		l = input[i+1]

		if dcmp(h, on_h) and dcmp(l, on_l):
			pass
		elif allowTrail and (l > on_l or l > off_l):
			return i/2+1
		elif not dcmp(h, off_h) or (not dcmp(l, off_l) and l != 65535):
			return i/2
		i += 1
	return len(input)/2

"""
Interprets JVC IR signals
"""
def jvc(sequence):
	h = sequence.pop(0)
	l = sequence.pop(0)

	if not (dcmp(h, 8400) and dcmp(l, 4200)):
		return None

	address = readbits(sequence, 8, 526, 526*3, 526, 526)
	command = readbits(sequence, 8, 526, 526*3, 526, 526)
	if address is None or command is None:
		return None

	end = readbits(sequence, 1, 526, 60000 - (address["time"] + command["time"] + h + l), 1, 1);
	if end is None:
		return None

	return {"address" : address, "command" : command}

"""
Interprets Sony IR signals. 12, 15 and 20 bit versions supported.
"""
def sony(sequence):
	h = sequence.pop(0)
	l = sequence.pop(0)

	if not (dcmp(h, 2400) and dcmp(l, 600)):
		return None

	bits = countbits(sequence, 1200, 600, 600, 600, True)
	command = None
	address = None
	extend = None
	if bits is 12:
		command = readbits(sequence, 7, 1200, 600, 600, 600)
		address = readbits(sequence, 5, 1200, 600, 600, 600)
	elif bits is 15:
		command = readbits(sequence, 7, 1200, 600, 600, 600)
		address = readbits(sequence, 8, 1200, 600, 600, 600)
	elif bits is 20:
		command = readbits(sequence, 7, 1200, 600, 600, 600)
		address = readbits(sequence, 5, 1200, 600, 600, 600)
		extend  = readbits(sequence, 8, 1200, 600, 600, 600, True)
	else:
		print "Unknown sony, %d bits" % bits
		return None

	if command is None or address is None:
		return None
	return {"address": address, "command": command, "extend": extend}

"""
Interprets NEC IR signals, regular and extended.
"""
def nec(sequence):
	h = sequence.pop(0)
	l = sequence.pop(0)

	if not (dcmp(h, 9000) and dcmp(l, 4500)):
		return None

	extend  = False
	address  = readbits(sequence, 8, 562, 1687, 562, 562)
	iaddress = readbits(sequence, 8, 562, 1687, 562, 562)
	command  = readbits(sequence, 8, 562, 1687, 562, 562)
	icommand = readbits(sequence, 8, 562, 1687, 562, 562)

	# Find end indicator
	if not dcmp(sequence.pop(0), 562):
		return None

	if iaddress["value"] ^ address["value"] is not 255:
		extend = True
		address["value"] |= (iaddress["value"] << 8)
	if icommand["value"] ^ command["value"] is not 255:
		return None

	return {"address" : address, "command" : command}

"""
Declare the name of the interpreter and which function to call
to interpret it. An interpreter must return None if it is unable
to decode the signal.
"""
mapping = [
	{
		"name": "jvc",
		"func": jvc
	},
	{
		"name": "sony",
		"func": sony
	},
	{
		"name": "nec",
		"func": nec
	},
]

"""
Takes a sequence of IR pulses in on/off format (us) and tries to convert them
into their native format.

@param input Array of paired on/off pulses
@return array containing name and results
"""
def recognize(input):
	clean = dejitter(input, 100)
	for interpreter in mapping:
		sequence = copy.copy(clean)
		result = interpreter["func"](sequence)
		if result is not None:
			ret = {"name": interpreter["name"]}
			for item in result:
				ret[item] = result[item]["value"]
			return ret

	return None