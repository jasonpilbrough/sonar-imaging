import matplotlib; 
import random
import matplotlib.pyplot as plt
import numpy as np
import pyfftw
import math
import time



#GLOBAL VARIABLES

global fc; fc = 40000		# center frequency of chirp [Hz]
global T; T = 0.005			# length of chirp [seconds]
global fs; fs = 500000.0	# sample rate [Hz] - NB must be a float for micro to work
global Δt; Δt = 1/fs		# sample spacing in time domain [seconds]
global t; t = np.linspace(0, T, T/Δt)	# time axis

global B; B = 6000			# bandwidth of sonar [Hz]
global K; K = B/T     		# chirp rate [Hz/s]
global f0; f0 = fc-B/2 		# initial freq of chirp [Hz]
global N; N = len(t)

#init frequency axis
global Δω; Δω = 2*np.pi/(N*Δt) # Sample spacing in freq domain [rad]
global Δf; Δf = Δω/(2*np.pi)	# Sample spacing in freq domain [Hz]
global ω; ω = np.linspace(0, (N-1)*Δω, N)  # freq axis [rad]
global f; f = ω/(2*np.pi)		# freq axis [Hz]
global f_axis;
#create array of freq values stored in f_axis. First element maps to 0Hz
if N%2==0:    # case N even
    f_axis =  np.linspace(-N/2, N/2-1, N)*Δf;
else:   # case N odd
    f_axis = np.linspace(-(N-1)/2, (N-1)/2, N)*Δf;  


# Define chirp pulse x(t) and return x(t)
def make_chirp():
	
	
	ct = np.zeros(N) # comparator threshold signal
	ft = np.cos(2*np.pi*(f0*t+0.5*K*t**2)) #cos function
	xt = np.less(ft,ct) # convert to binary signal (0 or 1) by comparing cos to threshold signal
	
	fft = pyfftw.builders.fft(xt) # compute fft
	Xw = fft() 
	
	"""
	#plot x(t) and X(f)
	fig, (tplot, fplot) = plt.subplots(2, 1)
	#plt.title("input chirp signal")
	tplot.plot(t,xt,linewidth=0.7, color="#2da6f7")
	#tplot.plot(t,ft,linewidth=0.7, color="r")
	tplot.set_xlabel("t [s]")
	tplot.set_ylabel("x(t)")
	fplot.plot(f_axis, np.fft.fftshift(abs(Xw)),linewidth=0.7, color="#2da6f7")
	fplot.set_xlabel("f [Hz]")
	fplot.set_ylabel("X(f)")
	plt.show()
	"""
	
	
	return xt
	

def generate_header_file(xt):
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
	


if __name__ == "__main__":
	xt = make_chirp()
	generate_header_file(xt)
	
	
	
	

