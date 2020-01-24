""" Provides all the required signal processing and plotting for sonar imaging

This script provides the user with all the signal processing steps to generate sonar
images. Two different types of sonar images can be generated using this script, and are
discussed briefly below:

	1) 1D range profiling - generates a 1D range profile of a scene from a single recieve
	signal. Two modes of operation are provided:
		
		a) simulated data - fictional scene is generated using simulated recieve signals.
		No microcontroller needs to be connected for operation in this mode. The following 
		function can be called to generate a 1D range profile using simulated data:
			
			* generate_1D_image_sim
		
		b) real data - real scene is imaged using actual recieve signals obtained from a 
		connected microcontroller. The following function can be called to generate a 1D 
		range profile using real data:
		
			* generate_1D_image
		
	2) 2D imaging - generates 2D image of a scene using multiple recieve signals. Two 
	modes of operation are provided:
	
		a) simulated data - The following function can be called to generate a 2D image 
		using simulated data:
			
			* generate_2D_image_sim
		
		a) real data - The following function can be called to generate a 2D image using 
		real data:
		
			* generate_2D_image


This script was designed be run directly from the terminal, or run indirectly by a web 
server.	
	
This script requires that the following libraries be installed  within the Python 
environment you are running this script in:

	matplotlib, numpy, pyfftw, teensy_interface

This file can also be imported to provide the following individual signal processing 
steps:

	* make_chrip
	* generate_noise
	* simulate_recieve_signal
	* prepare_recieve_signal
	* pulse_compression
	* to_analytic_signal
	* apply_window_function
	* to_baseband
	* non_ideal_compensation
	* range_compensation
	* coherent_summing
	
 """


# ===================================== IMPORTS ======================================== #

import matplotlib; 

# NB 'agg' backend is required to plot in browser. This statement must run before pyplot 
# is imported. To plot in a window, the backend must be changed to "MacOSX in __main__". 
matplotlib.use('agg')

import matplotlib.pyplot as plt
import random
import numpy as np
import pyfftw
import math
import time
import teensy_interface


# ================================= GLOBAL VARIABLES =================================== #

global c; c = 343							# speed of sound in air [meters/sec]
global r_max; r_max = 10					# max range [meters]

global fc; fc = 40000						# center frequency of sonar [Hz]
global T; T = 0.005							# length of chirp [seconds]
global fs; fs = 105000						# default sample rate [Hz]

global t_max; t_max = 2*r_max/c + T   		# max range [seconds]
global Δt; Δt = 1/fs						# sample spacing in time domain [seconds]
global t; t = np.linspace(0,t_max,t_max/Δt)	# time axis

global s; s = 0.5 * t * c  					# distance axis
global s_max; s_max = 0.5 * t_max * c		# max range [meters]

global B; B = 2000							# bandwidth of sonar [Hz]
global K; K = B/T     						# chirp rate [Hz/s]
global f0; f0 = fc-B/2 						# initial freq of chirp [Hz]
global λ; λ = c/fc    						# wavelength [m]
global N; N = len(t)						# number of elements in time axis

global Δω; Δω = 2*np.pi/(N*Δt) 				# sample spacing in freq domain [rad]
global Δf; Δf = Δω/(2*np.pi)				# sample spacing in freq domain [Hz]
global ω; ω = np.linspace(0, (N-1)*Δω, N)  	# freq axis [rad]
global f; f = ω/(2*np.pi)					# freq axis [Hz]
global f_axis; 								# alt freq axis, first element maps to 0 Hz

if N%2==0:    # case N even
    f_axis =  np.linspace(-N/2, N/2-1, N)*Δf;
else:   # case N odd
    f_axis = np.linspace(-(N-1)/2, (N-1)/2, N)*Δf;  


# 2D COORDINATE SYSTEM

# All coords defined in following lines are in form (radius in m, angle in rads). The 
# transmitter is located at the origin (0,0). The receivers are spaced evenly appart 
# forming a linear array centered on the origin, with a north-south orientation.


# max field of view (in azimuth) measured from bore-sight in degrees
global FIELD_OF_VIEW; FIELD_OF_VIEW = 30

# define radial axis, and azimuth axis  
global rad; rad = np.linspace(0, r_max, 150)
global azm; azm = np.linspace(-FIELD_OF_VIEW*np.pi/180, FIELD_OF_VIEW*np.pi/180, 150)

# the origin (0,0) is defined as the location of the transmitter 
global transmit_coord; transmit_coord = (0.0,0.0)

# spacing between each of the recievers in meters
global reciever_spacing; reciever_spacing = 0.01 

global reciever_coords; reciever_coords = [(reciever_spacing*3.5, 3*np.pi/2),(reciever_spacing*2.5, 3*np.pi/2),(reciever_spacing*1.5, 3*np.pi/2),(reciever_spacing*0.5, 3*np.pi/2),(reciever_spacing*0.5, np.pi/2),(reciever_spacing*1.5, np.pi/2),(reciever_spacing*2.5, np.pi/2),(reciever_spacing*3.5, np.pi/2)]
global target_coords; target_coords = [(5 , 10*np.pi/180),(8.5 , 0*np.pi/180)] 						# global target_coords; target_coords = [(4,10*np.pi/180),(5,10*np.pi/180),(6,10*np.pi/180),(7,10*np.pi/180),(5.5,10*np.pi/180)] 


# DEBUGGING 

# if debug mode is active, each intermediate figure will be saved for later inspection
# and can help with debugging
global DEBUG_MODE_ACTIVE; DEBUG_MODE_ACTIVE = False

# this is the path that debugging figures are saved to. Note that if this script is called
# by a webserver, then the debug/ folder will not be in the webserver/ dir, but in the 
# signal_processing/ dir. If this the script is called from the terminal, the path should
# be changed to debug/ in __main__.
global DEBUG_DIR; DEBUG_DIR = "../signal_processing/debug"

# this variable keeps track of the current receiver being processed, and is used to
# label each of the intermediate plots generated by debug mode. In the case of 1D mode,
# where only one receiver is used, this variable is fixed to 0
global DEBUG_ACTIVE_RECIEVER; DEBUG_ACTIVE_RECIEVER = 0


# RECORDING RECEIVE SIGNAL

# trying to detect the presence of the simulated chirp signal in the receive signal will
# often lead to poor results - thus it is preferable to calibrate the system by recording
# the receive echo off a strong target, and using that as the waveform to match with all
# future receive signals. Note that the receive signal must be formatted correctly before
# it can be used again - can use Microsoft Excel. NB only record RX when in 1D mode, else
# each receiver will overwrite the previous one  

# if record Rx mode is active, the received waveform will be saved in a text file. 
global RECORD_RX; RECORD_RX = True

# if true, the recorded waveform will be read in and used for matching
global USE_RECORDED_RX; USE_RECORDED_RX = True

# the file paths used to save and load the recorded signals - note save and load use
# different files to prevent acidental overwriting
global RX_SAVE_FILEPATH; RX_SAVE_FILEPATH = "../signal_processing/receive_signal/recorded_RX_signal.txt"
global RX_LOAD_FILEPATH; RX_LOAD_FILEPATH = "../signal_processing/receive_signal/formatted_RX_signal3.txt"


# =============================== FUNCTION DEFINITIONS ================================= #


# 1D SIGNAL PROCESSING ALGORITHMS

def make_chirp():
	""" Defines a chirp signal and returns signal in time and frequency domains. 
	
	The properties of the chrip, including its duration, center frequency, and chirp rate
	are defined as global variables.
	
	Returns
	-------
	numpy.ndarray
		chirp signal in time domain x(t)
	numpy.ndarray
		chirp signal in frequency domain X(w)
	"""
	
	# either read in a file containing the "transmitted" chirp, or create simulated one
	if(USE_RECORDED_RX):
		xt = np.loadtxt(RX_LOAD_FILEPATH)
	else:
		xt = rect((t - T/2)/T)*np.cos(2*np.pi*(f0*t+0.5*K*t**2))
	
	fft = pyfftw.builders.fft(xt) # compute fft
	Xw = fft() 
	
	
	# if debug mode is active, save this intermediate figure for later inspection. This is
	# only done if for the first receiver and TX signal will be the same 
	# to plot this figure in a window (i.e not the browser), uncomment the plt.show()
	# command below
	if(DEBUG_MODE_ACTIVE and DEBUG_ACTIVE_RECIEVER==0):
		fig, (tplot, fplot) = plt.subplots(2, 1, figsize=(8,6))
		fig.suptitle("Transmitted chirp x(t)", y=0.94)
		plt.subplots_adjust(top=0.89,hspace=0.3)
		
		tplot.plot(t,xt,linewidth=0.7, color="#2da6f7")
		tplot.set_xlabel("t [s]")
		tplot.set_ylabel("x(t)")
		
		fplot.plot(f_axis, np.fft.fftshift(abs(Xw)),linewidth=0.7, color="#2da6f7")
		fplot.set_xlabel("f [Hz]")
		fplot.set_ylabel("X(f)")
		
		#plt.show(block=False)
		save_figure(fig, "_1_chirp.png".format(DEBUG_ACTIVE_RECIEVER))
		plt.close()
	
	
	return xt , Xw



def simulate_recieve_signal(td_targets):
	"""Simulates what the recieve signal would look like for given targets in a scene.
	
	This function is called when in simulation mode.  
	
	Parameters
	----------
	td_targets : list
		array containing the time delay (td) between transmitting the pulse, and recieving 
		an echo for each of the targets. A longer td means the target is further away.
	
	Returns
	-------
	numpy.ndarray
		recieved signal in time domain v(t)
	numpy.ndarray
		recieved signal in frequency domain V(w)
	"""
	
	vt = 0
	for i in range(0,len(td_targets)):
		td = td_targets[i] 
		R = 0.5 * td * c
		A = 1/R**2
		v = A*rect((t - (T/2+td) )/T)*np.cos(2*np.pi*(f0*(t-td)+0.5*K*(t-td)**2))
		vt = vt + v

	vt = vt + generate_noise()
	
	fft = pyfftw.builders.fft(vt) # compute fft
	Vw = fft() 
	
	
	# if debug mode is active, save this intermediate figure for later inspection
	# to plot this figure in a window (i.e not the browser), uncomment the plt.show()
	# command below
	if(DEBUG_MODE_ACTIVE):
		fig, (tplot, fplot) = plt.subplots(2, 1, figsize=(8,6))
		fig.suptitle("Recieved signal v(t)", y=0.94)
		plt.subplots_adjust(top=0.89,hspace=0.3)
		
		tplot.plot(s,vt,linewidth=0.7, color="#2da6f7")
		tplot.set_xlabel("t [s]")
		tplot.set_ylabel("v(t)")
		
		fplot.plot(f_axis, np.fft.fftshift(abs(Vw)),linewidth=0.7, color="#2da6f7")
		fplot.set_xlabel("f [Hz]")
		fplot.set_ylabel("V(f)")
		
		#plt.show(block=False)
		save_figure(fig, "{}_1_receive.png".format(DEBUG_ACTIVE_RECIEVER))
		plt.close()
	
	
	return vt, Vw


def prepare_recieve_signal(samples):
	"""Prepares the recieved signal for further processing by applying BPF centered on fc.
	Also saves recieved waveform is RECORD_RX==true
	
	This function is used when recieving actual sonar data, as opposed to using simulated
	data.
	
	TODO - high pass filtering
	
	Parameters
	----------
	samples : numpy.ndarray
		array containing all samples of the recieved signal. It is important that this is
		a numpy array.
	
	Returns
	-------
	numpy.ndarray
		processed signal in time domain v(t)
	numpy.ndarray
		processed signal in frequency domain V(w)
	"""
	
	vt = samples
	
	# save receive signal as text file if in record mode (i.e. RECORD_RX == True)
	if(RECORD_RX):
		np.savetxt(RX_SAVE_FILEPATH, vt, delimiter=',')
	
	fft = pyfftw.builders.fft(vt) # compute fft
	Vw = fft() 
	
	# BPF
	window = rect((f -fc % (N * Δf))/B)
	Vw = Vw * (window + window[::-1]) # to account for the +'ve and -'ve freq
	fft = pyfftw.builders.ifft(Vw) # compute inverse fft
	vt = fft() 
	
	
	# if debug mode is active, save this intermediate figure for later inspection
	# to plot this figure in a window (i.e not the browser), uncomment the plt.show()
	# command below
	if(DEBUG_MODE_ACTIVE):
		fig, (tplot, fplot) = plt.subplots(2, 1, figsize=(8,6))
		fig.suptitle("Recieved signal v(t)", y=0.94)
		plt.subplots_adjust(top=0.89,hspace=0.4)

		tplot.plot(t,vt,linewidth=0.7, color="#2da6f7")
		tplot.set_xlabel("t [s]")
		tplot.set_ylabel("v(t)")
		
		fplot.plot(f_axis, np.fft.fftshift(abs(Vw)),linewidth=0.7, color="#2da6f7")
		fplot.set_xlabel("f [Hz]")
		fplot.set_ylabel("V(f)")
		
		#plt.show()
		save_figure(fig, "{}_1_receive.png".format(DEBUG_ACTIVE_RECIEVER))
		plt.close()
	
	
	
	return vt, Vw
	


def pulse_compression(Xw,Vw): 
	"""Performs pulse compression on the recieved signal using an inverse filter.
	
	Inverse filter designed to detect the presence of a waveform of known structure (in 
	this case a chirp signal) buried in the presence of additive noise. The output will
	typically exhibit a sharp peak in response to the presence of the desired waveform.
	
	Parameters
	----------
	Xw : numpy.ndarray
		the transmit signal in frequency domain
	Vw: numpy.ndarray
		the recieved signal in frequency domain after being prepared
	
	Returns
	-------
	numpy.ndarray
		processed signal in time domain y(t)
	numpy.ndarray
		processed signal in frequency domain Y(w)
	"""
	
	# defines a window over the bandwidth of the transmitted chirp
	window = rect((f -fc % (N * Δf))/B)
		
	# applies inverse filter to received signal 
	Yw = Vw/Xw * (window + window[::-1]) # to account for the +'ve and -'ve freq
	
	# replaces any Nan with 0
	Yw = np.nan_to_num(Yw) 
	
	# MATCHED FILTER 
	#Hw = np.conj(Xw) # conjugate of X.
	#Yw = Hw * Vw
		
	fft = pyfftw.builders.ifft(Yw) # compute inverse fft
	yt = fft() 
	

	# if debug mode is active, save this intermediate figure for later inspection
	# to plot this figure in a window (i.e not the browser), uncomment the plt.show()
	# command below - NB NOT USED CURRENTLY
	
	#if(DEBUG_MODE_ACTIVE):
	if(False):
		fig, (tplot, fplot) = plt.subplots(2, 1, figsize=(8,6))
		fig.suptitle("Output of inverse filter y(t)", y=0.94)
		plt.subplots_adjust(top=0.89,hspace=0.3)
		
		tplot.plot(t,abs(yt),linewidth=0.7, color="#2da6f7")
		tplot.set_xlabel("t [s]")
		tplot.set_ylabel("y(t)")
		
		fplot.plot(f_axis, np.fft.fftshift(abs(Yw)),linewidth=0.7, color="#2da6f7")
		fplot.set_xlabel("f [Hz]")
		fplot.set_ylabel("Y(f)")
		
		#plt.show()
		save_figure(fig, "{}_2_inverse_filter.png".format(DEBUG_ACTIVE_RECIEVER))
		plt.close()
	
	
	return yt, Yw


def to_analytic_signal(Xw):
	"""Converts signal to analytic form by zero-ing out negative frequency components. 
	
	Parameters
	----------
	Xw: numpy.ndarray
		signal, in frequency domain, to convert to analytic form
	
	Returns
	-------
	numpy.ndarray
		processed signal in time domain y(t)
	numpy.ndarray
		processed signal in frequency domain Y(w)
	"""
	
	# analytic signal must be multiple by 2 to compensate for losing its -'ve frequencies
	Yw = 2*Xw 
	
	for i in range(0,len(Yw)):
		if (i > len(Yw)/2):
			Yw[i] = 0

	fft = pyfftw.builders.ifft(Yw) # compute inverse fft
	yt = fft() 
	
	
	# if debug mode is active, save this intermediate figure for later inspection
	# to plot this figure in a window (i.e not the browser), uncomment the plt.show()
	# command below
	if(DEBUG_MODE_ACTIVE):
		fig, (tplot, fplot) = plt.subplots(2, 1, figsize=(8,6))
		fig.suptitle("Output of inverse filter y(t) - analytic", y=0.94)
		plt.subplots_adjust(top=0.89,hspace=0.3)
		
		tplot.plot(t,abs(yt),linewidth=0.7, color="#2da6f7")
		tplot.set_xlabel("t [s]")
		tplot.set_ylabel("y(t)")
		
		fplot.plot(f_axis, np.fft.fftshift(abs(Yw)),linewidth=0.7, color="#2da6f7")
		fplot.set_xlabel("f [Hz]")
		fplot.set_ylabel("Y(f)")
		
		#plt.show(block=True)
		save_figure(fig, "{}_2_filter.png".format(DEBUG_ACTIVE_RECIEVER))
		plt.close()
	
	
	
	return yt, Yw
	

def apply_window_function(Xw):
	"""Apply window function to signal to reduce sidelobes.
	
	Multipying a signal by a window function after having undergone pulse compression will 
	reduce the magnitude of the sidelobes in the response. A Blackman window function is 
	used in this case.
	
	Parameters
	----------
	Xw: numpy.ndarray
		signal, in frequency domain, to convert to analytic form
	
	Returns
	-------
	numpy.ndarray
		processed signal in time domain y(t)
	numpy.ndarray
		processed signal in frequency domain Y(w)
	"""
	
	#co-efficients for Blackman window 
	a0 = 0.42
	a1 = 0.5
	a2 = 0.08
	
	# if the desired bandwidth of the window function is different to the bandwidth of the
	# chirp signal, then change the 1 in the following expression
	B_window = B * 1
	
	# define window transfer function
	Hw = a0 - a1*np.cos((2 * np.pi * (f+fc+B/2))/(B_window)) + a2*np.cos((4 * np.pi * (f+fc+B/2))/(B_window))
	Hw = Hw * rect((f-fc)/B)

	Yw = Xw * Hw 
	
	fft = pyfftw.builders.ifft(Yw) # compute inverse fft
	yt = fft() 
	
	
	# if debug mode is active, save this intermediate figure for later inspection
	# to plot this figure in a window (i.e not the browser), uncomment the plt.show()
	# command below 
	
	if(DEBUG_MODE_ACTIVE):
		fig, (tplot, fplot, hplot) = plt.subplots(3, 1, figsize=(8,6))
		fig.suptitle("Output after window function y(t)", y=0.94)
		plt.subplots_adjust(top=0.89,hspace=0.4)
		
		tplot.plot(t,abs(yt),linewidth=0.7, color="#2da6f7")
		tplot.set_xlabel("t [s]")
		tplot.set_ylabel("y(t)")
		
		fplot.plot(f, abs(Yw),linewidth=0.7, color="#2da6f7")
		fplot.set_xlabel("f [Hz]")
		fplot.set_ylabel("Y(f)")
		
		hplot.plot(f, abs(Hw),linewidth=0.7, color="#2da6f7")
		hplot.set_xlabel("f [Hz]")
		hplot.set_ylabel("H(f)")
		
		#plt.show(block=True)
		save_figure(fig, "{}_3_window.png".format(DEBUG_ACTIVE_RECIEVER))
		plt.close()
	
	
	return yt, Yw


def to_baseband(xt):
	"""Translate the provided signal to baseband (i.e. centered around 0Hz).
	
	Parameters
	----------
	xt: numpy.ndarray
		signal, in time domain, to convert to baseband form
	
	Returns
	-------
	numpy.ndarray
		basebanded signal in time domain y(t)
	numpy.ndarray
		basebanded signal in frequency domain Y(w)
	"""
	
	# multiplying signal by exponential function in time domain is equivalent to 
	# translation in frequency domain
	yt = xt * np.exp(-2*1j*np.pi*fc*t) 
	
	fft = pyfftw.builders.fft(yt) # compute fft
	Yw = fft() 
	

	# if debug mode is active, save this intermediate figure for later inspection
	# to plot this figure in a window (i.e not the browser), uncomment the plt.show()
	# command below
	if(DEBUG_MODE_ACTIVE):
		fig, (tplot, fplot) = plt.subplots(2, 1, figsize=(8,6))
		fig.suptitle("Output after basebanding y(t)", y=0.94)
		plt.subplots_adjust(top=0.89,hspace=0.4)
		
		tplot.plot(t,abs(yt),linewidth=0.7, color="#2da6f7")
		tplot.set_xlabel("t [s]")
		tplot.set_ylabel("|y(t)|")
		
		fplot.plot(f_axis, np.fft.fftshift(abs(Yw)),linewidth=0.7, color="#2da6f7")
		fplot.set_xlabel("f [Hz]")
		fplot.set_ylabel("Y(f)")
		
		#plt.show()
		save_figure(fig, "{}_4_baseband.png".format(DEBUG_ACTIVE_RECIEVER))
		plt.close()
	
	
	return yt, Yw

def non_ideal_compensation(xt):
	"""Compensates for phase offset due to no ideal effects in the system. This includes
	compensating for deadtime, phase, and gain.
	
	This step is not required for simulated data. The compensation factors for gain and 
	phase were determined by placing a corner reflector 2m away from the sonar directly on
	boresight. The gain and phase at the location of the target should be approximately
	the same. If not, then the appropriate compensation factor was calculated to cause 
	this to be true. 
	
	
	Parameters
	----------
	xt: numpy.ndarray
		time domain signal to perform compensation
	
	Returns
	-------
	numpy.ndarray
		phase compensated signal in time domain y(t)
	numpy.ndarray
		phase compensated signal in frequency domain Y(w)
	"""
	
	# DEAD-TIME COMPENSATION
	
	# move end portion of RX array to start to compensate for deadtime
	xt = np.concatenate((xt[(len(xt)-410):len(xt)], xt[0:(len(xt)-410)]))
	fft = pyfftw.builders.fft(xt) # compute fft
	Xw = fft() 
	
	
	# PHASE COMPENSATION

	# phase compensation factors for each receiver in radians, assumes 8 receivers
	phase_comp_factors = [-0.856, -1.329, 1.693, 1.054, 3.171, -2.967, 2.302, -1.429] #comp_factors = [1.3451, -2.479, 2.368, 2.429, -2.940, -2.639, 2.510, -0.977] #comp_factors = [2.0, -2.1, 2.6, 2.7, -2.1, -2.2, 3.0, -0.7] #comp_factors = [-0.1707, 0.5777, -0.9882,-0.9321, -2.5832, 0.4118, -0.5452, 1.9282] #comp_factors = [1.3451, 0.3382, 2.368, 2.429, -2.940, -2.639, 2.510, -0.977]
	
	# apply compensation factor to current receiver
	yt = xt * np.exp(1j*phase_comp_factors[DEBUG_ACTIVE_RECIEVER]) 	
	fft = pyfftw.builders.fft(yt) # compute fft
	Yw = fft() 
	
	# GAIN COMPENSATION
	
	# gain compensation factors for each receiver in radians, assumes 8 receivers
	gain_comp_factors = [1/0.0866,1/0.1009,1/0.07615,1/0.0839,1/0.06921,1/0.06902,1/0.0906,1/0.08533]
	
	#apply compensation factor to current receiver
	yt = yt * gain_comp_factors[DEBUG_ACTIVE_RECIEVER] 	
	fft = pyfftw.builders.fft(yt) # compute fft
	Yw = fft() 
	
	
	return yt, Yw


def range_compensation(xt):
	"""Compensates for R^2 reduction in echo strength.
	
	Two targets of equal size will produce echos of different strengths if they are at 
	different distances away from the sonar. The reduction in signal strength is 
	proportional to this distance squared (R^2). To compensate for this loss, the recieve
	signal can be multiplied by R^2.  
	
	Parameters
	----------
	xt: numpy.ndarray
		time domain signal to perform range compensation
	
	Returns
	-------
	numpy.ndarray
		range compensated signal in time domain y(t)
	numpy.ndarray
		range compensated signal in frequency domain Y(w)
	"""
	
	#array of compensation factors
	comp_factors = 0.5 * t * c
	
	yt = xt * comp_factors**2
	
	fft = pyfftw.builders.fft(yt) # compute fft
	Yw = fft() 
	
	
	# if debug mode is active, save this intermediate figure for later inspection
	# to plot this figure in a window (i.e not the browser), uncomment the plt.show()
	# command below
	if(DEBUG_MODE_ACTIVE):
		fig, (tplot1, tplot2) = plt.subplots(2, 1, figsize=(8,6))
		fig.suptitle("Output before and after compensation", y=0.94)
		plt.subplots_adjust(top=0.89,hspace=0.4)
		
		tplot1.plot(t,abs(xt),linewidth=0.7, color="#2da6f7")
		tplot1.set_xlabel("t [s]")
		tplot1.set_ylabel("x(t)")
		
		tplot2.plot(t,abs(yt),linewidth=0.7, color="#2da6f7")
		tplot2.set_xlabel("t [s]")
		tplot2.set_ylabel("y(t)")
		
		#plt.show(block = True)
		save_figure(fig, "{}_5_comp.png".format(DEBUG_ACTIVE_RECIEVER))
		plt.close()
	
	# if debug mode is active, produce a single  plot with all range profiles super 
	# imposed for both magnitude and phase
	if(DEBUG_MODE_ACTIVE):
		# plot magnitude curve for each receiver on same figure
		plt.figure(num="mag")
		plt.plot(s,abs(yt),linewidth=0.7)
		plt.legend(('r0', 'r1', 'r2', 'r3', 'r4', 'r5', 'r6', 'r7'))
		plt.title("Combined Range Profiles - magnitude")
		plt.xlabel("d [m]")
		plt.ylabel("|y(t)|")
		
		# plot phase curve for each receiver on same figure
		plt.figure(num="phase")
		plt.plot(s,np.angle(yt),linewidth=0.7)
		plt.legend(('r0', 'r1', 'r2', 'r3', 'r4', 'r5', 'r6', 'r7'))
		plt.title("Combined Range Profiles - phase")
		plt.xlabel("d [m]")
		plt.ylabel("<y(t)")
		plt.show(block=False)
		
		# save each plot if this is the last receiver
		if(DEBUG_ACTIVE_RECIEVER==7):
			plt.figure(num="mag")
			save_figure(plt.gcf(), "all_profile_mags.png")
			plt.close()
			plt.figure(num="phase")
			save_figure(plt.gcf(), "all_profile_phases.png")
			plt.close()
	
	return yt, Yw


def produce_range_profile_sim(td_targets):
	"""Performs all signal processing steps to produce 1D range profile from simulated 
	data.
	
	This function is called when in simulation mode.  This function only produces the 
	range profile and is not responsible for generating the simulation data. 
	
	Parameters
	----------
	td_targets : list
		array containing the time delay (td) between transmitting the pulse, and recieving 
		an echo for each of the targets. A longer td means the target is further away.
	
	Returns
	-------
	numpy.ndarray
		range profile y(t)
	"""
	
	# dont use recorded RX when in sim mode
	global USE_RECORDED_RX; USE_RECORDED_RX = False
	
	xt, Xw = make_chirp()
	vt, Vw = simulate_recieve_signal(td_targets)
	yt, Yw = pulse_compression(Xw, Vw)
	yt, Yw = to_analytic_signal(Yw)
	yt, Yw = apply_window_function(Yw)
	yt, Yw = to_baseband(yt)
	yt, Yw = range_compensation(yt)
	
	
	# if debug mode is active, save this intermediate figure for later inspection
	# to plot this figure in a window (i.e not the browser), uncomment the plt.show()
	# command below
	if(DEBUG_MODE_ACTIVE):
		fig, (tplot1, tplot2) = plt.subplots(2, 1, figsize=(8,6))
		fig.suptitle("Processed Range Profile", y=0.94)
		plt.subplots_adjust(top=0.89,hspace=0.4)
		
		tplot1.plot(s,abs(yt),linewidth=0.7, color="#2da6f7")
		tplot1.set_xlabel("d [m]")
		tplot1.set_ylabel("{}".format("|y(t)|"))
		
		tplot2.plot(s, np.angle(yt),linewidth=0.7, color="#2da6f7")
		tplot2.set_xlabel("d [m]")
		tplot2.set_ylabel("<y(t)")
		
		#plt.show(block = True)
		save_figure(fig, "{}_6_range_profile.png".format(DEBUG_ACTIVE_RECIEVER))
		plt.close()
	
	
	
	return yt

	
def produce_range_profile(samples):
	"""Performs all signal processing steps to produce 1D range profile from real data.
	
	Real data refers to data that is captured from a scene using an actual sonar, as 
	opposed to using simulated data. This function only produces the range profile and is 
	not responsible for aquiring sonar data. 
	
	Parameters
	----------
	samples: numpy.ndarray
		array of digital samples collected by a microcontroller from the sonar.
	
	Returns
	-------
	numpy.ndarray
		range profile y(t)
	"""
	
	# use recorded RX when in sim mode
	global USE_RECORDED_RX; USE_RECORDED_RX = True
	
	xt, Xw = make_chirp()
	vt, Vw = prepare_recieve_signal(np.asarray(samples)) #NB must convert to numpy array
	yt, Yw = pulse_compression(Xw, Vw)
	yt, Yw = to_analytic_signal(Yw)
	yt, Yw = apply_window_function(Yw)
	yt, Yw = to_baseband(yt)
	yt, Yw = non_ideal_compensation(yt)
	yt, Yw = range_compensation(yt)
	
	
	# if debug mode is active, save this intermediate figure for later inspection
	# to plot this figure in a window (i.e not the browser), uncomment the plt.show()
	# command below
	if(DEBUG_MODE_ACTIVE):
		fig, (tplot1, tplot2) = plt.subplots(2, 1, figsize=(8,6))
		fig.suptitle("Processed Range Profile", y=0.94)
		plt.subplots_adjust(top=0.89,hspace=0.4)
		
		tplot1.plot(t,abs(yt),linewidth=0.7, color="#2da6f7")
		tplot1.set_xlabel("d [m]")
		tplot1.set_ylabel("{}".format("|y(t)|"))
		
		tplot2.plot(t, np.angle(yt),linewidth=0.7, color="#2da6f7")
		tplot2.set_xlabel("d [m]")
		tplot2.set_ylabel("<y(t)")
		
		#plt.show(block=False)
		save_figure(fig, "{}_8_range_profile.png".format(DEBUG_ACTIVE_RECIEVER))
		plt.close()
	
	
	return yt



def generate_1D_image_sim():
	"""Generates complete 1D range profile image using simulated data.
	
	This function is called when in simulation mode.  This function first generates the
	simulation data, then uses this data to obtain a processed range profile to display.  
	
	Returns
	-------
	matplotlib.figure.Figure
		1D range profile image
	"""
	
	# this variable keeps track of the current receiver being processed, and is used to
	# label some of the intermediate plots generated by debug mode. In the case of 1D mode
	# where only one receiver is used, this variable is fixed to 0
	global DEBUG_ACTIVE_RECIEVER; DEBUG_ACTIVE_RECIEVER =0
	
	two_way_delay_to_targets = []
	
	for target in target_coords:
		two_way_dist = calc_dist_polar(transmit_coord, target)+calc_dist_polar(target, reciever_coords[0])			
		two_way_delay = two_way_dist/c
		two_way_delay_to_targets.append(two_way_delay)
		
	yt = produce_range_profile_sim(two_way_delay_to_targets)
		

	fig, (splot) = plt.subplots(1, 1, figsize=(8,6))
	plt.subplots_adjust(top=0.97,right = 0.95, left = 0.15)

	splot.plot(s,abs(yt),linewidth=0.7, color="#2da6f7")
	splot.set_xlabel("d [m]")
	splot.set_ylabel("{}".format("|y(t)|"))
	#plt.show()

	return fig

	

def generate_1D_image():
	"""Generates complete 1D range profile image using actual sonar data.
	
	This function is used when recieving actual sonar data, as opposed to using simulated
	data. This function first obtains the sonar data using the teensy_interface, then 
	uses this data to obtain a processed range profile to display. Note that multiple
	recievers can be provided by the sonar. However, for 1D range profiling only a single 
	reciever is required. Reciever 0 is used by default. The sampling rate is also 
	obtained from the microcontroller in this function, and used to update the sampling 
	rate used in signal processing.
	
	Returns
	-------
	matplotlib.figure.Figure
		1D range profile image
	"""
	
	# this variable keeps track of the current receiver being processed, and is used to
	# label some of the intermediate plots generated by debug mode. In the case of 1D mode
	# where only one receiver is used, this variable is fixed to 0
	global DEBUG_ACTIVE_RECIEVER; DEBUG_ACTIVE_RECIEVER =0
	
	# dictionary stores all sonar data - use short_timeout=True for 1D sonar
	dict = teensy_interface.request_sonar_data(short_timeout=True)
	
	# could not connect to teensy - return empty figure
	if(len(dict)==0):
		raise teensy_interface.SerialFormatError("","error from microcontroller")
		
	# the sample rate is also included in the sonar data, and must be removes from the
	# dict before signal processing. The sample rate used is this script is updated to
	# the sample rate from the sonar data
	change_sample_rate(dict.pop("sample_rate"),len(dict["buffer0"]))
	
	# uses reciever0 of the sonar by default
	yt = produce_range_profile(dict["buffer0"])


	fig, (splot) = plt.subplots(1, 1, figsize=(8,6))
	plt.subplots_adjust(top=0.97, right = 0.95, left = 0.15)
	splot.plot(s,abs(yt),linewidth=0.7, color="#2da6f7")
	splot.set_xlabel("d [m]")
	splot.set_ylabel("{}".format("|y(t)|"))
	plt.show()

	return fig



# -------------------------------------------------------------------------------------- #
# 2D SIGNAL PROCESSING ALGORITHMS


def coherent_summing(range_profiles):
	"""Constructs a 2D image from the processed signals from each reciever.
	
	This algorithms works as follows: the scene is first divided into a polar grid. Then 
	moving through the grid, the two-way delay between the transmitter, current grid 
	position, and receiver is calculated. This delay is then used to extract a single 
	value from each of the processed received signals that would represent the echo from 
	a target if it occupied that particular position in the grid. Each of these values 
	are then summed using the appropriate phase compensation and aperture taping to 
	reduce sidelobes. This process is repeated for every point in the grid to construct 
	an image.
	
	Parameters
	----------
	range_profiles: numpy.ndarray
		2D array containing processed range profile from each reciever.
	
	Returns
	-------
	numpy.ndarray
		2D sonar image array z. This array will be used to plot a polar 2D image at a 
		later stage. The plot will need to access the array as follows:
				
				z[angle][magnitude]
		
		Thus, the azimuth angle must be stored as the first dimension in the array, and 
		magnitude/range must be stored in the second dimension.
	"""
	
	# NB must be [angle][magnitude] - see doc string
	z = np.zeros((len(azm),len(rad)))
	
	# declare array stores complex numbers
	z = np.array(z, dtype=complex)
	
	
	for i in range(0, len(rad)): # for every range bin
		for j in range(0, len(azm)): # for every azimuth angle
		
	
			# polar coordinate given as (r, theta)
			#focus_point = (rad[i],azm[j]) 
			focus_point = (rad[i],azm[j])

			#distance between transmitter,  focus point, and reference point (0,0)
			dref = calc_dist_polar(transmit_coord, focus_point) + calc_dist_polar(focus_point, (0,0))

			# convert distance to time
			tref = dref / c  

			for n in range(0, len(reciever_coords)): # for every receiver	

				# distance between transmitter,  focus point, and receiver	
				two_way_dist = calc_dist_polar(transmit_coord, focus_point) + calc_dist_polar(focus_point, reciever_coords[n])

				# convert distance to time delay
				two_way_td = two_way_dist / c 

				# find index in range profile corresponding to time delay two_way_td
				index = int(round(two_way_td / Δt))

				# extract value from range profile at index and apply phase compensation
				value = range_profiles[n][index] * np.exp(2*1j*np.pi*fc*(two_way_td)) #* np.exp(2*1j*np.pi*fc*(two_way_td-tref)) 



				# NB must be [j][i] as later plot expects [angle, magnitude]
				z[j][i] = z[j][i] + value 
	
	z = z**0.5
	
	return z


def plot_2D_image(z):
	"""Plots polar 2D sonar image.
	
	Real data refers to data that is captured from a scene using an actual sonar, as 
	opposed to using simulated data. This function only produces the range profile and is 
	not responsible for aquiring sonar data. 
	
	Parameters
	----------
	z: numpy.ndarray
		2D array of values to plot. Must be in polar coordinates.
	
	Returns
	-------
	matplotlib.figure.Figure
		2D sonar image
	"""
	
	fig = plt.figure(figsize=(12,8))
	r, th = np.meshgrid(rad, azm)
	ax = plt.subplot(projection="polar")
	
	ax.set_thetamin(FIELD_OF_VIEW) # in degrees
	ax.set_thetamax(-FIELD_OF_VIEW) # in degrees
	#ax.set_theta_offset(np.pi/2)
	
	plt.pcolormesh(th, r, abs(z), cmap="inferno")
	plt.plot(azm, r, color='k', ls='none') 
	plt.colorbar()
	#plt.colorbar(orientation='horizontal')
	#plt.grid()
	plt.subplots_adjust(left=0.0, right=1.0, top=0.95, bottom=0.05)
	plt.show(block=True)
	
		
	return fig
	
	

def generate_2D_image_sim():
	"""Generates complete 2D sonar image using simulated data.
	
	This function is called when in simulation mode.  This function first generates the
	simulation data for each reciever, then uses this data to obtain processed range 
	profiles for each reciever, before finally using these range profiles to build a 2D 
	sonar image using a technique called coherrent summing.
	
	Returns
	-------
	matplotlib.figure.Figure
		2D sonar image
	"""
	
	# this variable keeps track of the current receiver being processed, and is used to
	# label some of the intermediate plots generated by debug mode
	global DEBUG_ACTIVE_RECIEVER; DEBUG_ACTIVE_RECIEVER = 0
	
	# holds processed range profiles from each reciever
	range_profiles = [] 
	
	# generate simulation data for each receiver and then range profile
	for reciever in reciever_coords:
		two_way_delay_to_targets = []
		for target in target_coords:
			two_way_dist = calc_dist_polar(transmit_coord, target) + calc_dist_polar(target, reciever)
			two_way_delay = two_way_dist/c
			two_way_delay_to_targets.append(two_way_delay)
			
			
		range_profiles.append(produce_range_profile_sim(two_way_delay_to_targets))
		
		# increment after each receiver has been processed
		DEBUG_ACTIVE_RECIEVER+=1
	
	

	
	
	# form 2D array from range_profiles for 2D image
	z = coherent_summing(range_profiles)
	
	# return the 2D sonar image
	return plot_2D_image(z)


def generate_2D_image():
	"""Generates complete 2D sonar image using actual sonar data.
	
	This function is used when recieving actual sonar data, as opposed to using simulated
	data. This function first obtains the sonar data for each reciever using the 
	teensy_interface, then uses this data to obtain processed range profiles for each 
	reciever, before finally using these range profiles to build a 2D sonar image using a 
	technique called coherrent summing. The sampling rate is also obtained from the 
	microcontroller in this function, and used to update the sampling rate used in signal 
	processing.
	
	Returns
	-------
	matplotlib.figure.Figure
		2D sonar image
	"""
	
	# this variable keeps track of the current receiver being processed, and is used to
	# label some of the intermediate plots generated by debug mode
	global DEBUG_ACTIVE_RECIEVER; DEBUG_ACTIVE_RECIEVER =0
	
	# dictionary stores all sonar data - use short_timeout=False for 2D sonar
	dict = teensy_interface.request_sonar_data(short_timeout=False)
	
	# could not connect to teensy - return empty figure
	if(len(dict)==0):
		raise teensy_interface.SerialFormatError("","error from microcontroller")
	
	
	# the sample rate is also included in the sonar data, and must be removes from the
	# dict before signal processing. The sample rate used is this script is updated to
	# the sample rate from the sonar data
	change_sample_rate(dict.pop("sample_rate"),len(dict["buffer0"])) #NB must pop sample rate
	
	
	# holds processed range profiles from each reciever
	range_profiles = []
	
	# generate range profile for each receiver using sonar data
	for reciever in dict:
		range_profiles.append(produce_range_profile(dict[reciever]))
		
		# increment after each receiver has been processed
		DEBUG_ACTIVE_RECIEVER+=1
	
	# form 2D array from range_profiles for 2D image
	z = coherent_summing(range_profiles)
	
	# return the 2D sonar image
	return plot_2D_image(z)


# -------------------------------------------------------------------------------------- #
# HELPER FUNCTIONS


def rect(t):
	"""Defines a rect function."""
	
	return abs(t) < 0.5  * 1.0
	

def generate_noise():
	"""Generates noise with fixed mean μ and standard deviation σ."""
	
	noise = np.random.normal(size=N)
	μ = 0.0 
	σ = 0.01
	noise = noise * σ + μ
	return noise


def calc_dist_rect(c1, c2):
	"""Calculates distance between two points given in rectangular coordinates (x,y)."""
	
	diff = np.subtract(c1, c2)
	return math.sqrt(diff[0]**2+diff[1]**2)
	

def calc_dist_polar(c1, c2):
	"""Calculates distance between two points given in polar coordinates (r,theta)."""
	
	return math.sqrt(c1[0]**2 + c2[0]**2 - 2*c1[0]*c2[0]*np.cos(c1[1] -  c2[1]))
	

def change_sample_rate(new_sample_rate, num_samples):
	"""Changes all relevent global variables that are dependent on sample rate.
	
	It is extremely important to call this function if the sample rate of the 
	microcontroller changes, else the signal processing will produce erroneous results.
	
	Parameters
	----------
	new_sample_rate: float
		the new sample rate in Hz
	num_samples: int
		the number of sample to be used in signal processing (i.e. length of all the 
		arrays)
		
	"""
	
	global fs; fs = new_sample_rate				# sample rate [Hz]
	global N; N = num_samples
	
	global Δt; Δt = 1/fs						# sample spacing in time domain [seconds]
	global t_max;t_max = N*Δt   				# max range [seconds]
	global t; t = np.linspace(0, t_max,N)		# time axis

	global s; s = 0.5 * t * c  					# distance axis
	global s_max; s_max = 0.5 * t_max * c		# max range [meters]	

	global Δω; Δω = 2*np.pi/(N*Δt) 				# sample spacing in freq domain [rad]
	global Δf; Δf = Δω/(2*np.pi)				# sample spacing in freq domain [Hz]
	global ω; ω = np.linspace(0, (N-1)*Δω, N)  	# freq axis [rad]
	global f; f = ω/(2*np.pi)					# freq axis [Hz]
	global f_axis;								# alt freq axis, first element maps to 0 Hz
	
	if N%2==0:    # case N even
		f_axis =  np.linspace(-N/2, N/2-1, N)*Δf;
	else:   # case N odd
		f_axis = np.linspace(-(N-1)/2, (N-1)/2, N)*Δf;  



def set_debug_mode(value):
	"""Sets whether debug mode is active or not. 
	
	The sets the global variable DEBUG_MODE_ACTIVE. Debug mode is used to temporarily 
	store the intermediate plots generated by each of the signal processing steps. These 
	can be shown to the user to aid debugging. 
	
	Parameters
	----------
	value : bool
		If true, debug mode is set to active, else set to not active
	
	"""
	global DEBUG_MODE_ACTIVE;
	DEBUG_MODE_ACTIVE = value;



def save_figure(fig, filename):
	"""Save a pyplot figure using the filename provided.
	
	The path to the file is determined by the gloabl variable DEBUG_DIR. If this directory
	does not exist, it will be created. 
	
	Parameters
	----------
	filename : string
		The filename and extension, excluding the file path, to save the figure to.
		
	"""
	
	from errno import EEXIST
	from os import makedirs,path
	
	# create new directory if it doesn't already exist
	try:
		makedirs(DEBUG_DIR)
	except OSError as exc: # Python >2.5
		if (exc.errno == EEXIST and path.isdir(DEBUG_DIR)):
			pass
		else: raise
		
	fullpath = '{}/{}'.format(DEBUG_DIR, filename)
	fig.savefig(fullpath, dpi=150, bbox_inches="tight")





# ====================================== MAIN ========================================== #

if __name__ == "__main__":
	
	# if running this script from the terminal, it is import to switch the backend
	plt.switch_backend("MacOSX")
	
	# change filepath if run from terminal - assuming this script is run from signal_processing/
	DEBUG_DIR = "debug"
	RX_SAVE_FILEPATH = "receive_signal/recorded_RX_signal.txt"
	RX_LOAD_FILEPATH = "receive_signal/formatted_RX_signal3.txt"
	
	# set debug mode to active by default in order to view any plots
	DEBUG_MODE_ACTIVE = True
	
	
	# TEST CODE
	
	
	
	start_time_millis = time.time()
	start_time_fmt = time.strftime("%H:%M:%S", time.localtime())
	
	generate_2D_image()
	#generate_1D_image();
	
	end_time_millis = time.time()
	runtime = end_time_millis - start_time_millis
	print("Runtime info: starttime={}, runtime={}s".format(start_time_fmt,round(runtime,2)))
	
	
	"""
	start_time_millis = time.time()
	start_time_fmt = time.strftime("%H:%M:%S", time.localtime())
	
	
	# holds processed range profiles from each reciever
	range_profiles = [] 
	
	# generate simulation data for each receiver and then range profile
	for reciever in reciever_coords:
		two_way_delay_to_targets = []
		for target in target_coords:
			two_way_dist = calc_dist_polar(transmit_coord, target) + calc_dist_polar(target, reciever)
			two_way_delay = two_way_dist/c
			two_way_delay_to_targets.append(two_way_delay)
			
		range_profiles.append(produce_range_profile_sim(two_way_delay_to_targets))
		DEBUG_ACTIVE_RECIEVER+=1
	
	
	#fig, (splot) = plt.subplots(1, 1, figsize=(8,6))
	#splot.plot((np.asarray(temp)),linewidth=0.7, color="#2da6f7")
	#plt.show(block=False)
	
	
	# form 2D array from range_profiles for 2D image
	z = coherent_summing(range_profiles)

	end_time_millis = time.time()
	runtime = end_time_millis - start_time_millis
	print("Runtime info: starttime={}, runtime={}s".format(start_time_fmt,round(runtime,2)))
	
	plot_2D_image(z)
	"""
	
	
	



	
	


# ====================================== END =========================================== #









# ====================================================================================== #
# OTHER CODE WORTH KEEPING JUST IN CASE


"""
global transmit_coord; transmit_coord = (0.0,0.0) # (x,y)
global reciever_spacing; reciever_spacing = 0.01 # spacing between each of the recievers (in y axis)
global reciever_coords; reciever_coords = [(0.0,-reciever_spacing*4),(0.0,-reciever_spacing*3),(0.0,0.0-reciever_spacing*2),(0.0,-reciever_spacing*1),(0.0,0.0),(0.0,reciever_spacing*1),(0.0,reciever_spacing*2),(0.0,reciever_spacing*3)]
global target_coords; target_coords = [(5,0),(5,3),(5,-4),(7,0),(8,0.1)]
#global target_coords; target_coords = [(5,2)]
#global target_coords; target_coords = [(10, np.pi/12)]

global rad; rad = np.linspace(0, r_max, 150)
global azm; azm = np.linspace(-np.pi/4, np.pi/4, 150)
"""




"""
Plot cross sections of 2D image

# plot cross-section of z at fixed range
slice = [row[81] for row in z]
slice = np.array(slice, dtype=complex)

#plot |z(theta)| and <z(theta)
fig, (sliceplot1, sliceplot2) = plt.subplots(2, 1)
sliceplot1.plot(azm, abs(slice), linewidth=0.7, color="#2da6f7")
sliceplot1.set_xlabel("azimuth angle [rad]")
sliceplot1.set_ylabel("{}".format("|z(theta)|"))
sliceplot2.plot(azm, np.angle(slice), linewidth=0.7, color="#2da6f7")
sliceplot2.set_xlabel("azimuth angle [rad]")
sliceplot2.set_ylabel("<z(theta)")
plt.show()


# plot cross-section of z at fixed angle 
slice = z[75]
slice = np.array(slice, dtype=complex)

#plot |z(theta)| and <z(theta)
fig, (sliceplot1, sliceplot2) = plt.subplots(2, 1)
sliceplot1.plot(rad, abs(slice), linewidth=0.7, color="#2da6f7")
sliceplot1.set_xlabel("d [m]")
sliceplot1.set_ylabel("{}".format("|z(theta)|"))
sliceplot2.plot(rad, np.angle(slice), linewidth=0.7, color="#2da6f7")
sliceplot2.set_xlabel("d [m]")
sliceplot2.set_ylabel("<z(theta)")
plt.show()

"""



"""
def coherent_summing(range_profiles):
	
	z = np.zeros((len(rad),len(azm)))
	z = np.array(z, dtype=complex)
	
	
	for i in range(0, len(rad)): # for every range bin
		for j in range(0, len(azm)): # for every azimuth angle
		
			# polar coordinate given as (r, theta)
			focus_point = (rad[i],azm[j]) 
			
			#distance between transmitter,  focus point, and reference point (0,0)
			dref = calc_dist_polar(transmit_coord, focus_point) + calc_dist_polar(focus_point, (0,0))
			
			# convert distance to time
			tref = dref / c  
			
			for n in range(0, len(reciever_coords)):				
				
				
				#dist = calc_dist_rect(transmit_coord, focus_point) + calc_dist_rect(focus_point, reciever_coords[n])
				dist = calc_dist_polar(transmit_coord, focus_point) + calc_dist_polar(focus_point, reciever_coords[n])
				td = 2 * dist / c
				index = int(round(td * 0.5 / Δt))
				value = range_profiles[n][index] * np.exp(2*1j*np.pi*fc*(td-tref))
				
				
				
				two_way_dist = calc_dist_polar(transmit_coord, focus_point) + calc_dist_polar(focus_point, reciever_coords[n])
				two_way_td = two_way_dist / c 
				index = int(round(two_way_td / Δt))
				value = range_profiles[n][index] * np.exp(2*1j*np.pi*fc*(two_way_td-tref)) 
			
				
				
				two_way_dist = calc_dist_polar(transmit_coord, focus_point) + calc_dist_polar(focus_point, reciever_coords[n])
				two_way_td = two_way_dist / c 
				index = int(round(two_way_td / Δt))
				value = range_profiles[n][index] *  np.exp(2*1j*np.pi/λ * 0 * (n-4) * reciever_spacing*np.sin(azm[i])) *  np.exp(2*1j*np.pi*fc*(two_way_td-tref)) 
				
				
				
				
				tdelay = 2*np.pi/λ * (n)*reciever_spacing*np.sin(azm[i])
				tn = tref + tdelay
				print(tn, tref, 2*np.pi/λ)
				
				#two_way_dist = calc_dist_polar(transmit_coord, focus_point) + calc_dist_polar(focus_point, reciever_coords[n])
				#two_way_td = two_way_dist / c 
				index = int(round(tn / Δt))
				value = range_profiles[n][index] *  np.exp(2*1j*np.pi/λ * (n) * reciever_spacing*np.sin(azm[i])) *  np.exp(2*1j*np.pi*fc*(tn)) 
				
				
				#two_way_dist = calc_dist_polar((0,0), focus_point)
				#two_way_td = 2*(two_way_dist + reciever_spacing*(n)*np.sin(azm[i])) / c 
				#index = int(round(two_way_td/Δt))
				#value = range_profiles[n][index]* np.exp((1j*2*np.pi*reciever_spacing*(n)*np.sin(azm[i]))/λ) * np.exp(2*1j*np.pi*fc*(two_way_td-tref))
                       
                                	
				
				#print(rad[i],azm[j])
				#print(rad[i], azm[j], rad[i]>=5.0 , rad[i]<=5.05 , azm[j] >= 0 , azm[j] <= 0.01)
				if(rad[i]>=5.0 and rad[i]<=5.05 and azm[j] >= 0 and azm[j] <= 0.01):
					print("5r","0deg",abs(value), np.angle(value)*180/np.pi)
					
				if(rad[i]>=5.0 and rad[i]<=5.05 and azm[j] >= 0.201 and azm[j] <= 0.211):
					print("5r","11deg",abs(value), np.angle(value)*180/np.pi)
					z[j][i] = z[j][i] + 0.02
				
				
				z[j][i] = z[j][i] + value #NB must be [j][i] as later plot expects [angle, magnitude]
				
	#z = z**0.5
	#z = 20*np.log(z/0.001)
	
	
	
	#Beam Pattern
	
	num = np.sin(np.pi*8*reciever_spacing*np.sin(azm-0)/λ)
	denom = (np.sin(np.pi*reciever_spacing*np.sin(azm-0)/λ))
	func = 10*np.log(abs(num/denom))
	#plot y(t) and Y(f)
	fig, (tplot) = plt.subplots(1, 1)
	#plt.title("analytic output signal")
	tplot.plot(azm,func,linewidth=0.7, color="#2da6f7")
	tplot.set_xlabel("angle [rad]")
	tplot.set_ylabel("{}".format("|Beam Power|"))
	plt.show(block = False)
	
	
	
	return z
	"""
	
	
"""
	- If this script is called from the command line, the sonar images will be plot in a 
	new window on the desktop. In this case, it is important to ensure that the line in 
	the IMPORTS section that says "matplotlib.use('agg')" is commented out or removed. If 
	it is not removed then, plot will not be shown.
	
	- If this script is called from a web server that is serving the plots to the browser,
	the following line must be included in the IMPORTS section, directly under the 
	matplotlib import:
		matplotlib.use('agg')
	If this command is not included, then an error will be thrown.
	
"""


"""
	def column(matrix, i):
    	return [row[i] for row in matrix]
    
	fig, ax = plt.subplots(figsize=(6,6))	
	ax.imshow(abs(np.asarray(range_profiles)), aspect="auto")
	plt.show()
	
	fig, ax = plt.subplots(figsize=(6,6))	
	
	ax.plot(np.angle(np.asarray(column(range_profiles, 3060))))
	plt.show()
"""

"""
	
		range_profiles_old = range_profiles
	temp = []
	vbb = []
	for n in range(0, len(reciever_coords)): # for every receiver
		two_way_dist = calc_dist_polar(transmit_coord, target_coords[0]) + calc_dist_polar(target_coords[0], reciever_coords[n])	
		two_way_td = two_way_dist / c 
		vbbn = np.sin((np.pi*B*(t-two_way_td)))/(np.pi*B*(t-two_way_td)) * np.exp(-2*1j*np.pi*fc*(two_way_td))
		vbb.append(vbbn)
		temp.append(two_way_td)
	
	range_profiles = vbb
	
	fig, (splot) = plt.subplots(1, 1, figsize=(8,6))
	splot.plot((np.asarray(temp)),linewidth=0.7, color="#2da6f7")
	plt.show()

	fig, ax = plt.subplots(figsize=(6,6))	
	ax.imshow(np.angle(np.asarray(range_profiles)), aspect="auto")
	plt.show()
	
	
	fig, ax = plt.subplots(figsize=(6,6))	
	ax.plot(np.angle(np.asarray(column(range_profiles, int(target_coords[0][0]/10 * len(range_profiles)) ))))
	ax.plot(np.angle(np.asarray(column(range_profiles_old, int(target_coords[0][0]/10 * len(range_profiles))))))
	plt.show()
	
	
	#i = int(target_coords[0][0]/10 * len(rad))
	#j = int(target_coords[0][1]/(np.pi/2) * len(azm))
	#j = int(len(azm)*45/90) #65 
	
	#fig, (splot) = plt.subplots(1, 1, figsize=(8,6))
	#splot.plot(np.angle(np.asarray(temp)),linewidth=0.7, color="#2da6f7")
	#plt.show(block=False)
"""

"""
def place_receivers(num, spacing):

	global reciever_coords; 
	reciever_coords = []
	
	for i in range(int(-num/2), int(num/2)):
		angle = 0
		if(i < 0):
			angle = 3*np.pi/2
		else:
			angle = np.pi/2
		
		reciever_coords.append((abs(spacing*i), angle))

"""