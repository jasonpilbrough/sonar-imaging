import serial
import time
from serial.tools import list_ports

global TEENSY_DEVICE; TEENSY_DEVICE = '/dev/cu.usbmodem58714801' # '/dev/cu.usbmodem58714801' for Teensy board
global BAUD_RATE; BAUD_RATE = 9600;
global SERIAL;


class FormatError(Exception):
    """Exception raised for errors in format.

    Attributes:
        expression -- input expression in which the error occurred
        message -- explanation of the error
    """

    def __init__(self, expression, message):
        self.expression = expression
        self.message = message
        


def list_serial_devices():
	ports = serial.tools.list_ports.comports()
	print(len(ports), 'ports found:')
	for p in ports:
		print("\t",p.device)
	

def connect_to_Teensy():
	global SERIAL;
	try:
		SERIAL = serial.Serial(TEENSY_DEVICE, BAUD_RATE, timeout = 1)
	except Exception as e:
		print("Cant connect to device")
		print(e);
	
	

def write_to_Teensy():
	SERIAL.write(str("d").encode())
	

def read_from_Teensy():
	#print(SERIAL.read(1000000).decode('ascii'))
	
	samples = SERIAL.read(1000000).decode('ascii').split("\n") # new line means new reading
	
	
	dict = {}
	
	try:
		if("sample_rate" not in samples[0]):
			raise FormatError(samples[0], "input does not contain string 'sample_rate'")
		
		dict["sample_rate"] = float(samples[1].replace("\r",""))
		
		if("start_buffer_transfer" not in samples[2]):
			raise FormatError(samples[2], "input does not contain string 'start_buffer_transfer'")
		
		current_buffer = ""
		counter = 3
		while(True):
			
			if("end_buffer_transfer" in samples[counter]):
				break
			elif("buffer" in samples[counter]):
				current_buffer = samples[counter].replace("\r","") # remove \r
				dict[current_buffer] = []
				#print(current_buffer)
			else:
				#print(samples[counter].replace("\r",""))
				dict[current_buffer].append(float(samples[counter].replace("\r",""))) # remove \r
			counter=counter+1
		
		
			
	
	except FormatError as e:
		print("format from teensy not recongised")
		print(e)
	
	#print(dict)
	
	return dict
	
	


readOut = 0   #chars waiting from laser range finder
connected = False
commandToSend = 1 # get the distance in mm


if __name__ == "__main__":
	print ("Searching for ports...")
	list_serial_devices();
	print ("Connecting to Teensy")
	connect_to_Teensy()
	print ("Writing to Teensy")
	write_to_Teensy()
	print ("Reading from Teensy")
	read_from_Teensy()






