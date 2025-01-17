""" Interface to the serial port used by Teensy microcontroller.

This script allows the user to retrieve data from a Teensy microcontroller using a serial 
port. Two types of requests can be made: 

	1) status request - the data returned from this request will contain info about the 
	status of the microcontroller, including whether it is currently connected, and the 
	current sampling rate of the ADC. Note that to achieve maximum performace the sampling 
	rate of the ADC is not fixed and is set as high as possible by the microcontroller.
	
	2) sonar request - the data returned from this request is the sampled recieve signal 
	captured by the Teensy. The sampling rate of the ADC is also included. This is vital 
	important for any subsequent signal processing, as the sampling rate is not fixed. 

This script requires that 'serial' be installed within the Python environment you are 
running this script in.

This file can also be imported as a module and contains the following
functions:

    * list_serial_devices - prints all the available serial ports to the console
    * request_status - retrieves the current status of the Teensy.
    * request_sonar_data - sends transmit command to Teensy and retrieves the captured 
      recieve signals. 


Note that some attributes used in this script are set be default and cannot be provided 
from outside this script, including TEENSY_DEVICE, BAUD_RATE, and SERIAL_TIMEOUT.
 """


# ===================================== IMPORTS ======================================== #

import serial
import time
from serial.tools import list_ports


# ================================= GLOBAL VARIABLES =================================== #

# the device name for the Teensy board is '/dev/cu.usbmodem58714801' on my pc
global TEENSY_DEVICE; TEENSY_DEVICE = '/dev/cu.usbmodem58714801' 

# baud rate of the serial coms -> may be overwritten if using USB to default USB baud rate 
global BAUD_RATE; BAUD_RATE = 9600;

# Seconds that serial port waits after last byte before closing connection. Two different
# timeout values are defined: Use SERIAL_TIMEOUT_SHORT when receiving sonar data from
# a single receiver (1D mode), and SERIAL_TIMEOUT_LONG when receiving sonar data 
# from multiple receivers. 
global SERIAL_TIMEOUT_LONG; SERIAL_TIMEOUT_LONG = 0.8; 
global SERIAL_TIMEOUT_SHORT; SERIAL_TIMEOUT_SHORT = 0.2; 



# ================================= CLASS DEFINITIONS ================================== #


class TeensyError(Exception):
	"""Exception raised for errors in communication with Teensy
	
	This error can be raised if no Teensy device is connected, or if the bytes recieved 
	during serial comms with the Teensy are not in the expected format.
	
	Attributes
	----------
	message : str
		explanation of the error
	"""
	def __init__(self, message):
		"""
		Parameters
		----------
		message : str
			explanation of the error	
		"""
		
		self.message = message
		self.expression = ""


	def __str__(self):
		""" returns string containing explaination of error """
		
		return self.message



# =============================== FUNCTION DEFINITIONS ================================= #

def list_serial_devices():
	"""prints all the available serial ports to the console. """
	
	ports = serial.tools.list_ports.comports()
	print(len(ports), 'ports found:') # print the number of ports found
	for p in ports:
		print("\t",p.device)
	

def request_status():
	""" Retrieves the current status of the Teensy and returns it as a dictionary.
	
	The status of the Teensy microcontroller includes: 1) whether the Teensy is currently 
	connected and 2) the current sampling rate of the internal ADC of the Teensy (Note 
	that to achieve maximum performace the sampling rate of the ADC is not fixed and is 
	set as high as possible by the microcontroller).
	
	To request status from the Teensy, the Teensy expects the char 'i' to be written to
	the serial port.
	
	The format of the status data returned from the Teensy is expected to be in the 
	following format:
	
	"sample_rate"
	<sample_rate_in_Hz>
	
	Note that a maximum of 100 bytes are read from the serial port. If less than 100 bytes
	are written by the Teensy, then the serial port will automatically close after timeout 
	period (SERIAL_TIMEOUT_SHORT is used by default).
	
	Returns
	-------
	A dictionary mapping each of the status indicators to their value. The dictionary will
	look as follows:
	
		{"connection"  : "Connected",
		 "sample_rate" : "104.12 kHz"}
	
	Note that the only values that are valid for the 'connection' indicator are 
	"Connected" and "Not Connected". If Teensy is not connected, the value associated
	with 'sample_rate' is set to "N/A".
		
	Raises
	------
	Teensy Error
		If any errors occure during Teensy comms, including no Teensy connection or 
		invalid format 
	"""
	
	dict = {}
	
	try:
		# establish serial connection with teensy 
		teensy = serial.Serial(TEENSY_DEVICE, BAUD_RATE, timeout = SERIAL_TIMEOUT_SHORT)
		
		# send command to teensy to return status data
		teensy.write(str("i").encode())
		
		# retrieve data from Teensy
		info = teensy.read(100).decode('ascii').split("\n") # new line means new value
	
		if("sample_rate" not in info[0]):
			raise TeensyError("Format from Teensy not recognised: input does not contain string 'sample_rate' at index 0")
		
		# if no error has been thrown by this point, it means that the Teensy is connected
		dict["connection"] = "Connected"
		
		# provided sample rate in kHz rounded to 2 decimal places
		dict["sample_rate"] = "{} kHz".format(round(float(info[1].replace("\r",""))/1000.0,2))
		
	except (serial.serialutil.SerialException) as e1:
		print("\tCould not connect to Teensy")
		dict["connection"] = "Not Connected"
		dict["sample_rate"] = "N/A"
		
	except TeensyError as e2:
		print("\t", e2)
		dict["connection"] = "Not Connected"
		dict["sample_rate"] = "N/A"
		
	
	return dict


def request_sonar_data(short_timeout=False):
	"""Sends transmit command to Teensy and retrieves the captured recieve signals.
	
	The sonar data includes the recieve signal captured from each of the channels on the
	sonar. The sampling rate of the ADC is included. This is vital important for any 
	subsequent signal processing, as the sampling rate is not fixed. Also, the maximum
	ADC code is provided. This is determined by the resolution of the ADC and is required
	to convert each adc code into avoltage
	
	To request sonar data from the Teensy, the Teensy expects the char 'f' to be written 
	to the serial port.
	
	The format of the sonar data returned from the Teensy is expected to be in the 
	following format ('...' represents data that is not shown):
	
	"sample_rate"
	<sample_rate_in_Hz>
	"max_adc_code"
	<max_adc_code>
	"start_buffer_transfer"
	"buffer0"
	123
	122
	345
	...
	"buffer1"
	...
	"buffer<n>"
	...
	"end_buffer_transfer"
	
	Note that each of the sampled values is provided as an adc_code. These will be in the
	range from 0 -> max_adc_code. A maximum of 1000000 bytes are read from the serial 
	port. If less than 1000000 bytes are written by the Teensy, then the serial port will 
	automatically close after timeout period.
	
	Parameters
	----------
	short_timeout : bool, optional
		if true sets serial timeout to SERIAL_TIMEOUT_SHORT, if false sets serial timeout 
		to SERIAL_TIMEOUT_LONG. Use SERIAL_TIMEOUT_SHORT when receiving sonar data from
		a single receiver (1D mode), and SERIAL_TIMEOUT_LONG when receiving sonar data 
		from multiple receivers.
		
	Returns
	-------
	A dictionary containing the recived signal buffer for each sonar channel, as well as 
	the sample rate. The dictionary might look as follows:
	
		{"sample_rate" : "104.12 kHz",
		 "buffer0"     : [1.2, 1.1, 1.1,...],    
		 "buffer1"     : [...],
		 	...
		 "buffer<n>"   : [...]}
	
	Note that each sample has been converted from its adc code to the voltage it 
	represents. If Teensy is not connected, then an empty dictionary {} is returned.
		
	Raises
	------
	Teensy Error
		If any errors occure during Teensy comms, including no Teensy connection or 
		invalid format 
	"""

	dict = {}
	
	try:
		
		# establish serial connection with teensy and send command to transmit chirp and 
		# return sampled echos
		if(short_timeout):
			teensy = serial.Serial(TEENSY_DEVICE, BAUD_RATE, timeout = SERIAL_TIMEOUT_SHORT)
			# command 'g' is send for short mode
			teensy.write(str("g").encode())
		else:
			teensy = serial.Serial(TEENSY_DEVICE, BAUD_RATE, timeout = SERIAL_TIMEOUT_LONG)
			# command 'f' is send for short mode
			teensy.write(str("f").encode())
		
		
		# retrieve data from Teensy
		samples = teensy.read(10000000).decode('ascii').split("\n") # new line means new value
		
		
		if("sample_rate" not in samples[0]):
			raise TeensyError("Format from Teensy not recognised: input does not contain string 'sample_rate' at index 0")
		
		dict["sample_rate"] = float(samples[1].replace("\r",""))
		
		if("max_adc_code" not in samples[2]):
			raise TeensyError("Format from Teensy not recognised: input does not contain string 'max_adc_code' at index 2")
		
		# maximum adc code - e.g. if 10bit ADC is used, max code is 2**10 = 1024. Used to 
		# convert adc code into a voltage. 
		max_adc_code = float(samples[3].replace("\r",""))
		
		if("start_buffer_transfer" not in samples[4]):
			raise TeensyError("Format from Teensy not recognised: input does not contain string 'start_buffer_transfer' at index 4")
		
		current_buffer = ""
		counter = 5 # start iterations after 'start_buffer_transfer' at index 5
		
		while(True):		
			
			
			# if end is reached without receiving 'end_buffer_transfer' string, raise an error
			if(counter>=len(samples)):
				raise TeensyError("Format from Teensy not recognised: input does not end with string 'end_buffer_transfer'")
			
			# indicates end of sonar data	
			elif("end_buffer_transfer" in samples[counter]):
				break
			
			# indicates start of new buffer/channel 
			elif("buffer" in samples[counter]):
				# create key for current buffer for dict
				current_buffer = samples[counter].replace("\r","") # remove \r
				
				dict[current_buffer] = []
			else:
				adc_code = int(samples[counter].replace("\r","")) # remove \r
				
				# convert adc code into voltage - assumes teensy has 3.3V reference
				voltage = adc_code * 3.3 / (max_adc_code - 1)
				
				# append next sample to appropriate key in dict
				dict[current_buffer].append(voltage) 
			
			counter=counter+1
		

	except (serial.serialutil.SerialException) as e1:
		print("\tCould not connect to Teensy")
		
		# re-raise as TeensyError so it can be handled correctly above
		raise TeensyError("Could not connect to Teensy")
	
	except TeensyError as e2:
		print("\t",e2)
		
		# re-raise as TeensyError so it can be handled correctly above
		raise TeensyError(e2.message)

	
	return dict


# ====================================== MAIN ========================================== #

if __name__ == "__main__":

	# runs test that all functionality in this module is working as expected
	
	print ("Searching for ports...")
	list_serial_devices();
	print ("Requesting info data from Teensy")
	request_info_data()
	print ("Requesting sonar data from Teensy")
	
	start_time_millis = time.time()
	start_time_fmt = time.strftime("%H:%M:%S", time.localtime())
	
	request_sonar_data()
	
	end_time_millis = time.time()
	runtime = end_time_millis - start_time_millis
	print("Runtime info: starttime={}, runtime={}s".format(start_time_fmt,round(runtime,2)))





# ====================================== END =========================================== #

