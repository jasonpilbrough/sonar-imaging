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
		print("Cant connect to device", end=" ")
		print(e);
	


def request_info_data():
	
	dict = {}
	
	try:
		connect_to_Teensy()
		# send command to teensy to return info data
		SERIAL.write(str("i").encode())
		# retrieve data
		info = SERIAL.read(100).decode('ascii').split("\n") # new line means new reading
	
		
		
		if("sample_rate" not in info[0]):
			raise FormatError(info[0], "input does not contain string 'sample_rate'")
		
		dict["connection"] = "Connected"
		dict["sample_rate"] = "{} kHz".format(round(float(info[1].replace("\r",""))/1000.0,2))
		
	except (NameError, serial.serialutil.SerialException) as e1:
		print(e1)
		dict["connection"] = "Not Connected"
		dict["sample_rate"] = "N/A"
	except FormatError as e2:
		print("format from teensy not recongised", end=" ")
		print(e2)
		
	#print(dict)
	
	return dict



def request_sonar_data():

	dict = {} # if an error occurs an empty dict is returned
	
	try:
		connect_to_Teensy();
		# send command to teensy to transmit chirp and return sampled echos
		SERIAL.write(str("f").encode())
		# retrieve data
		samples = SERIAL.read(1000000).decode('ascii').split("\n") # new line means new reading

		
		
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
		
	except (NameError,serial.serialutil.SerialException) as e1:
		print(e1)
	except FormatError as e2:
		print("format from teensy not recongised", end=" ")
		print(e2)
	
	#print(dict)
	
	return dict



if __name__ == "__main__":
	print ("Searching for ports...")
	list_serial_devices();
	print ("Requesting info data from Teensy")
	request_info_data()
	print ("Requesting sonar data from Teensy")
	request_sonar_data()






