""" Generates a TX chirp waveform and saves the waveform as a lookup table in a C header 
file. 

This script was designed be called from inside the signal_processing/ directory. Doing so
will save the resulting C header file in the correct location in the teensy_sonar/ 
directory. 
	
This script requires that the following libraries be installed within the Python 
environment you are running this script in:

	matplotlib, numpy, pyfftw

This file can also be imported to provide the following functions

	* make_chrip
	* generate_header_file
	
"""

# ===================================== IMPORTS ======================================== #

import matplotlib; 
import random
import matplotlib.pyplot as plt
import numpy as np
import pyfftw
import math
import time

# ================================= GLOBAL VARIABLES =================================== #

global fc; fc = 40000						# center frequency of chirp [Hz]
global T; T = 0.005							# length of chirp [seconds]
global fs; fs = 500000.0					# sample rate [Hz] - NB must be a float for micro to work
global Δt; Δt = 1/fs						# sample spacing in time domain [seconds]
global t; t = np.linspace(0, T, T/Δt)		# time axis

global B; B = 6000							# bandwidth of sonar [Hz]
global K; K = B/T     						# chirp rate [Hz/s]
global f0; f0 = fc-B/2 						# initial freq of chirp [Hz]
global N; N = len(t)

#init frequency axis
global Δω; Δω = 2*np.pi/(N*Δt) 				# sample spacing in freq domain [rad]
global Δf; Δf = Δω/(2*np.pi)				# sample spacing in freq domain [Hz
global ω; ω = np.linspace(0, (N-1)*Δω, N) 	# freq axis [rad]
global f; f = ω/(2*np.pi)					# freq axis [Hz]
global f_axis;								# alt freq axis, first element maps to 0 Hz


if N%2==0: 	# case N even
    f_axis =  np.linspace(-N/2, N/2-1, N)*Δf;
else:  		# case N odd
    f_axis = np.linspace(-(N-1)/2, (N-1)/2, N)*Δf;  


# =============================== FUNCTION DEFINITIONS ================================= #


def make_chirp():
	""" Defines a binary chirp signal and returns signal in time domain. 
	
	The properties of the chrip, including its duration, center frequency, and chirp rate
	are defined as global variables.
	
	Returns
	-------
	numpy.ndarray
		chirp signal in time domain x(t)
	"""
	
	ft = np.cos(2*np.pi*(f0*t+0.5*K*t**2))
	
	# comparator threshold signal
	ct = np.zeros(N) 
	
	# convert to binary signal (0 or 1) by comparing cos to threshold signal
	xt = np.less(ft,ct) 
	
	fft = pyfftw.builders.fft(xt) # compute fft
	Xw = fft() 
	
	# uncomment to show plot
	#fig, (tplot, fplot) = plt.subplots(2, 1)
	#tplot.plot(t,xt,linewidth=0.7, color="#2da6f7")
	#tplot.set_xlabel("t [s]")
	#tplot.set_ylabel("x(t)")
	#fplot.plot(f_axis, np.fft.fftshift(abs(Xw)),linewidth=0.7, color="#2da6f7")
	#fplot.set_xlabel("f [Hz]")
	#fplot.set_ylabel("X(f)")
	#plt.show()
	
	return xt
	

def generate_header_file(xt):
	""" Generates a C header file and includes the values of a provided TX signal as a 
	lookup table. 
	
	Additional infomation is included in the header file including the sample rate and the 
	number of samples provided in the table. The script calling this function should be 
	run from inside the signal_processing/ directory. Doing so will save the resulting C 
	header file in the correct location in the teensy_sonar/ directory. 
	
	Parameters
	----------
	xt : numpy.ndarray
		the transmit signal in time domain
	"""
	
	f = open("../teensy_sonar/chirp_signal.h", "w+")
	f.write("#define _chirp_signal_\n")
	f.write("#define CHIRP_SAMPLE_RATE {}\n".format(fs))
	f.write("#define NUM_SAMPLES {}\n".format(N))
	f.write("static float waveformLookup[NUM_SAMPLES] = \n")
	f.write("{\n")
	arr_string = "{}\n".format(np.array2string(np.asarray(xt.astype(int)),threshold=np.inf)).replace("[","").replace("]","").replace(" ",", ").replace("\n","")
	f.write(arr_string)
	f.write("\n};\n")
	
	f.close()
	

# ====================================== MAIN ========================================== #

if __name__ == "__main__":
	xt = make_chirp()
	generate_header_file(xt)
	
	
	
	

