""" Provides all the required signal processing and plotting for sonar imaging

This script provides the user with all the signal processing steps to generate a sonar
image. Two different types of sonar images can be generated using this script, and are
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


This script can be run directly from the terminal, or run indirectly by a web server:	
	
	- If this script is called from the command line, the sonar images will be plot in a 
	new window on the desktop. In this case, it is important to ensure that the line in 
	the IMPORTS section that says "matplotlib.use('agg')" is commented out or removed. If 
	it is not removed then, plot will not be shown.
	
	- If this script is called from a web server that is serving the plots to the browser,
	the following line must be included in the IMPORTS section, directly under the 
	matplotlib import:
		matplotlib.use('agg')
	If this command is not included, then an error will be thrown.

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
	* range_compensation
	* coherent_summing
	
 """


# ===================================== IMPORTS ======================================== #

import matplotlib; 

# NB to plot in window comment out the following line, to plot in browser dont comment out
matplotlib.use('agg')

import random
import matplotlib.pyplot as plt
import numpy as np
import pyfftw
import math
import time
import teensy_interface


# ================================= GLOBAL VARIABLES =================================== #

global DEBUG_MODE_ACTIVE; DEBUG_MODE_ACTIVE = True
global DEBUG_ACTIVE_RECIEVER; DEBUG_ACTIVE_RECIEVER = 0

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


# the origin (0,0) is defined as the location of the transmitter 
global transmit_coord; transmit_coord = (0.0,0.0)

# spacing between each of the recievers in meters
global reciever_spacing; reciever_spacing = 0.01 

global reciever_coords; reciever_coords = [(reciever_spacing*3.5, 3*np.pi/2),(reciever_spacing*2.5, 3*np.pi/2),(reciever_spacing*1.5, 3*np.pi/2),(reciever_spacing*0.5, 3*np.pi/2),(reciever_spacing*0.5, np.pi/2),(reciever_spacing*1.5, np.pi/2),(reciever_spacing*2.5, np.pi/2),(reciever_spacing*3.5, np.pi/2)]
global target_coords; target_coords = [(4,10*np.pi/180),(5,10*np.pi/180),(6,10*np.pi/180),(7,10*np.pi/180),(5.5,10*np.pi/180)]  #global target_coords; target_coords = [(5, -60*np.pi/180),(8.2,60*np.pi/180)]

# define radial axis, and azimuth axis  
global rad; rad = np.linspace(0, r_max, 150)
global azm; azm = np.linspace(-np.pi/4, np.pi/4, 160)


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

	xt = rect((t - T/2)/T)*np.cos(2*np.pi*(f0*t+0.5*K*t**2))
	fft = pyfftw.builders.fft(xt) # compute fft
	Xw = fft() 
	
	
	
	if(DEBUG_MODE_ACTIVE):
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
		save_figure(fig, "{}_1_chirp.png".format(DEBUG_ACTIVE_RECIEVER))
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
		v = A*rect((t - (T/2+td) )/T)*np.cos(2*np.pi*(f0*t+0.5*K*(t-td)**2))
		vt = vt + v

	vt = vt + generate_noise()
	
	fft = pyfftw.builders.fft(vt) # compute fft
	Vw = fft() 
	
	
	#plot v(t) and V(f)
	
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
		
		#plt.show(block=True)
		save_figure(fig, "{}_2_receive.png".format(DEBUG_ACTIVE_RECIEVER))
		plt.close()
	
	
	return vt, Vw


def prepare_recieve_signal(samples):
	"""Prepares the recieved signal for further processing.
	
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
	fft = pyfftw.builders.fft(vt) # compute fft
	Vw = fft() 
	
	
	
	
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
		
		#plt.show(block=True)
		save_figure(fig, "{}_2_receive.png".format(DEBUG_ACTIVE_RECIEVER))
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
		
	fft = pyfftw.builders.ifft(Yw) # compute inverse fft
	yt = fft() 
	

	
	if(DEBUG_MODE_ACTIVE):
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
		save_figure(fig, "{}_3_inverse_filter.png".format(DEBUG_ACTIVE_RECIEVER))
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
	
	

	if(DEBUG_MODE_ACTIVE):
		fig, (tplot, fplot) = plt.subplots(2, 1, figsize=(8,6))
		fig.suptitle("Analytic signal y(t)", y=0.94)
		plt.subplots_adjust(top=0.89,hspace=0.3)
		
		tplot.plot(t,abs(yt),linewidth=0.7, color="#2da6f7")
		tplot.set_xlabel("t [s]")
		tplot.set_ylabel("y(t)")
		
		fplot.plot(f_axis, np.fft.fftshift(abs(Yw)),linewidth=0.7, color="#2da6f7")
		fplot.set_xlabel("f [Hz]")
		fplot.set_ylabel("Y(f)")
		
		#plt.show(block=True)
		save_figure(fig, "{}_4_analytic.png".format(DEBUG_ACTIVE_RECIEVER))
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
		save_figure(fig, "{}_5_window.png".format(DEBUG_ACTIVE_RECIEVER))
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
	

	if(DEBUG_MODE_ACTIVE):
		fig, (tplot, fplot) = plt.subplots(2, 1, figsize=(8,6))
		fig.suptitle("Output after basbanding y(t)", y=0.94)
		plt.subplots_adjust(top=0.89,hspace=0.4)
		
		tplot.plot(t,abs(yt),linewidth=0.7, color="#2da6f7")
		tplot.set_xlabel("t [s]")
		tplot.set_ylabel("y(t)")
		
		fplot.plot(f_axis, np.fft.fftshift(abs(Yw)),linewidth=0.7, color="#2da6f7")
		fplot.set_xlabel("f [Hz]")
		fplot.set_ylabel("Y(f)")
		
		#plt.show()
		save_figure(fig, "{}_6_baseband.png".format(DEBUG_ACTIVE_RECIEVER))
		plt.close()
	
	
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
	
	
	if(DEBUG_MODE_ACTIVE):
		fig, (tplot1, tplot2) = plt.subplots(2, 1, figsize=(8,6))
		fig.suptitle("Output before and after range compensation", y=0.94)
		plt.subplots_adjust(top=0.89,hspace=0.4)
		
		tplot1.plot(t,abs(xt),linewidth=0.7, color="#2da6f7")
		tplot1.set_xlabel("t [s]")
		tplot1.set_ylabel("x(t)")
		
		tplot2.plot(t,abs(yt),linewidth=0.7, color="#2da6f7")
		tplot2.set_xlabel("t [s]")
		tplot2.set_ylabel("y(t)")
		
		#plt.show(block = True)
		save_figure(fig, "{}_7_range_comp.png".format(DEBUG_ACTIVE_RECIEVER))
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
	
	xt, Xw = make_chirp()
	vt, Vw = simulate_recieve_signal(td_targets)
	yt, Yw = pulse_compression(Xw, Vw)
	yt, Yw = to_analytic_signal(Yw)
	yt, Yw = apply_window_function(Yw)
	yt, Yw = to_baseband(yt)
	yt, Yw = range_compensation(yt)
	
	

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
		
		#plt.show(block = True)
		save_figure(fig, "{}_8_range_profile.png".format(DEBUG_ACTIVE_RECIEVER))
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
	
	xt, Xw = make_chirp()
	vt, Vw = prepare_recieve_signal(np.asarray(samples)) #NB must convert to numpy array
	yt, Yw = pulse_compression(Xw, Vw)
	yt, Yw = to_analytic_signal(Yw)
	yt, Yw = apply_window_function(Yw)
	yt, Yw = to_baseband(yt)
	yt, Yw = range_compensation(yt)
	
	
	
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
		
		#plt.show(block = False)
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
	
	global DEBUG_ACTIVE_RECIEVER; DEBUG_ACTIVE_RECIEVER =0
	
	two_way_delay_to_targets = []
	
	for target in target_coords:
		two_way_dist = calc_dist_polar(transmit_coord, target)+calc_dist_polar(target, reciever_coords[0])			
		two_way_delay = two_way_dist/c
		two_way_delay_to_targets.append(two_way_delay)
		
	yt = produce_range_profile_sim(two_way_delay_to_targets)
		
	#plot y(t) 
	fig, (splot) = plt.subplots(1, 1)
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

	#plot y(t) 
	fig, (splot) = plt.subplots(1, 1)
	splot.plot(s,abs(yt),linewidth=0.7, color="#2da6f7")
	splot.set_xlabel("d [m]")
	splot.set_ylabel("{}".format("|y(t)|"))
	#plt.show()

	return fig



# -------------------------------------------------------------------------------------- #
# 2D SIGNAL PROCESSING ALGORITHMS


def coherent_summing(range_profiles):
	"""Constructs a 2D image from the processed signals from each reciever.
	
	This algorithms works as follows: the scene is first divided into a polar grid. The 
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
				
				# find index in range profile corresponding to time delay td
				index = int(round(two_way_td / Δt))
				
				# extract value from range profile at index and apply phase compensation
				value = range_profiles[n][index] * np.exp(2*1j*np.pi*fc*(two_way_td-tref)) 
				
				# NB must be [j][i] as later plot expects [angle, magnitude]
				z[j][i] = z[j][i] + value 
				
	
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
	
	ax.set_thetamin(45) # in degrees
	ax.set_thetamax(-45) # in degrees
	#ax.set_theta_offset(np.pi/2)
	
	plt.pcolormesh(th, r, abs(z), cmap="inferno")
	plt.plot(azm, r, color='k', ls='none') 
	plt.colorbar()
	#plt.colorbar(orientation='horizontal')
	plt.grid()
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
	σ = 0.02
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
	global DEBUG_MODE_ACTIVE;
	DEBUG_MODE_ACTIVE = value;



def save_figure(fig, filename):
	"""Save a figure from pyplot.
	
	Parameters
	----------
	path : string
		The path (and filename, with the extension) to save the figure to.
		
	"""
	
	# Create new directory
	output_dir = "debug"
	mkdir_p(output_dir)
	fullpath = '{}/{}'.format(output_dir, filename)
	fig.savefig(fullpath, dpi=150, bbox_inches="tight")


def mkdir_p(mypath):
	"""Creates a directory. equivalent to using mkdir -p on the command line"""
	
	from errno import EEXIST
	from os import makedirs,path
	
	try:
		makedirs(mypath)
	except OSError as exc: # Python >2.5
		if (exc.errno == EEXIST and path.isdir(mypath)):
			pass
		else: raise

# ====================================== MAIN ========================================== #

if __name__ == "__main__":
	
	
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
	
	# form 2D array from range_profiles for 2D image
	z = coherent_summing(range_profiles)
	
	end_time_millis = time.time()
	runtime = end_time_millis - start_time_millis
	print("Runtime info: starttime={}, runtime={}s".format(start_time_fmt,round(runtime,2)))
	
	plot_2D_image(z)
	"""
	
	
	"""
	start_time_millis = time.time()
	start_time_fmt = time.strftime("%H:%M:%S", time.localtime())
	
	dict = teensy_interface.request_sonar_data()
	
	change_sample_rate(dict.pop("sample_rate"),len(dict["buffer0"])) #NB must pop sample rate
	
	range_profiles = generate_all_range_profiles(dict)
	z = coherent_summing(range_profiles)
	
	end_time_millis = time.time()
	runtime = end_time_millis - start_time_millis
	print("Runtime info: starttime={}, runtime={}s".format(start_time_fmt,round(runtime,2)))
	
	plot_2D_image(z)
	"""
	
	
	generate_1D_image_sim();
	


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

