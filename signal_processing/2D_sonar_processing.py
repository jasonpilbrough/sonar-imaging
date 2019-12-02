import random
import matplotlib.pyplot as plt
import numpy as np
import pyfftw
import math
import time


#GLOBAL VARIABLES

global c; c = 343			# speed of sound [meters/sec]
global r_max; r_max = 15	# max range [meters]

global fc; fc = 40000		# center frequency of sonar [Hz]
global T; T = 0.005			# length of chirp [seconds]
global fs; fs = 100000		# sample rate [Hz]

global t_max; t_max = 2*r_max/c + T   # max range [seconds]
global Δt; Δt = 1/fs		# sample spacing in time domain [seconds]
global t; t = np.linspace(0, t_max, t_max/Δt)	# time axis

global s; s = 0.5 * t * c  	# distance axis
global s_max; s_max = 0.5 * t_max * c	# max range [meters]

global B; B = 2000			# bandwidth of sonar [Hz]
global K; K = B/T     		# chirp rate [Hz/s]
global f0; f0 = fc-B/2 		# initial freq of chirp [Hz]
global λ; λ = c/fc    		# wavelength [m]
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


# 2D GLOBAL VARIABLES
global transmit_coord; transmit_coord = (0.0,0.0) # (x,y)
global reciever_spacing; reciever_spacing = 0.01 # spacing between each of the recievers (in y axis)
global reciever_coords; reciever_coords = [(0.0,-reciever_spacing*3),(0.0,-reciever_spacing*2),(0.0,-reciever_spacing*1),(0.0,0.0),(0.0,reciever_spacing*1),(0.0,reciever_spacing*2),(0.0,reciever_spacing*3)]
global target_coords; target_coords = [(5,0)]
#global target_coords; target_coords = [(10, np.pi/12)]

global rad; rad = np.linspace(0, 10, 100)
global azm; azm = np.linspace(-np.pi/4, np.pi/4, 100)




# define rect function
def rect(t):
	return abs(t) < 0.5  * 1.0


# Define chirp pulse x(t) and return x(t)
def make_chirp():
	xt = 10*rect((t - T/2)/T)*np.cos(2*np.pi*(f0*t+0.5*K*t**2))
	fft = pyfftw.builders.fft(xt) # compute fft
	Xw = fft() 
	
	"""
	#plot x(t) and X(f)
	fig, (tplot, fplot) = plt.subplots(2, 1)
	#plt.title("input chirp signal")
	tplot.plot(t,xt,linewidth=0.7, color="#2da6f7")
	tplot.set_xlabel("t [s]")
	tplot.set_ylabel("x(t)")
	fplot.plot(f_axis, np.fft.fftshift(abs(Xw)),linewidth=0.7, color="#2da6f7")
	fplot.set_xlabel("f [Hz]")
	fplot.set_ylabel("X(f)")
	plt.show()
	"""
	
	return xt , Xw


# Simulate recieved echo from targets at distances that are passed as arguments
def simulate_recieve_signal(target_dists):
	vt = 0
	for i in range(0,len(target_dists)):
		R = target_dists[i]
		td = 2*R/c
		A = 1/R**2
		v = A*10*rect((t - (T/2+td) )/T)*np.cos(2*np.pi*(f0*t+0.5*K*(t-td)**2)) #.+ generate_noise(t,A)
		vt = vt + v

	fft = pyfftw.builders.fft(vt) # compute fft
	Vw = fft() 
	
	"""
	#plot v(t) and V(f)
	fig, (tplot, fplot) = plt.subplots(2, 1)
	#plt.title("recieved signal")
	tplot.plot(t,vt,linewidth=0.7, color="#2da6f7")
	tplot.set_xlabel("t [s]")
	tplot.set_ylabel("v(t)")
	fplot.plot(f_axis, np.fft.fftshift(abs(Vw)),linewidth=0.7, color="#2da6f7")
	fplot.set_xlabel("f [Hz]")
	fplot.set_ylabel("V(f)")
	plt.show()
	"""
	
	return vt, Vw


# Perform pulse compression by passing signal through inverse filter
def pulse_compression(Xw,Vw): #Xw input signal, Vw output signal

	window = rect((f -fc % (N * Δf))/B)
	Yw = Vw/Xw * (window + window[::-1]) # to account for the ='ve and -'ve freq
	Yw = np.nan_to_num(Yw) #replace any Nan with 0
	
	#Hw = np.conj(Xw) # conjugate of X.
	#Yw = Hw * Vw
	
	fft = pyfftw.builders.ifft(Yw) # compute inverse fft to return to time domain
	yt = fft() 
	
	"""
	#plot y(t) and Y(f)
	fig, (tplot, fplot) = plt.subplots(2, 1)
	#plt.title("output of inverse filter")
	tplot.plot(t,abs(yt),linewidth=0.7, color="#2da6f7")
	tplot.set_xlabel("t [s]")
	tplot.set_ylabel("y(t)")
	fplot.plot(f_axis, np.fft.fftshift(abs(Yw)),linewidth=0.7, color="#2da6f7")
	fplot.set_xlabel("f [Hz]")
	fplot.set_ylabel("Y(f)")
	plt.show()
	"""
	
	return yt, Yw
	
# make signal analytic by zero-ing out negative frequency components 
def to_analytic_signal(Xw):
	Yw = 2*Xw
	for i in range(0,len(Yw)):
		if (i > len(Yw)/2):
			Yw[i] = 0

	fft = pyfftw.builders.ifft(Yw) # compute inverse fft to return to time domain
	yt = fft() 
	
	"""
	#plot y(t) and Y(f)
	fig, (tplot, fplot) = plt.subplots(2, 1)
	#plt.title("analytic output signal")
	tplot.plot(t,abs(yt),linewidth=0.7, color="#2da6f7")
	tplot.set_xlabel("t [s]")
	tplot.set_ylabel("y(t)")
	fplot.plot(f_axis, np.fft.fftshift(abs(Yw)),linewidth=0.7, color="#2da6f7")
	fplot.set_xlabel("f [Hz]")
	fplot.set_ylabel("Y(f)")
	plt.show()
	"""
	
	return yt, Yw
	

# apply Blackman window function to provided signal
def apply_window_function(Xw, window_B, window_fc):
	
	#co-efficients for Blackman window 
	a0 = 0.42
	a1 = 0.5
	a2 = 0.08
	
	B_window = B * 1
	Hw = a0 - a1*np.cos((2 * np.pi * (f+fc+B/2))/(B_window)) + a2*np.cos((4 * np.pi * (f+fc+B/2))/(B_window))
	Hw = Hw * rect((f-fc)/B)

	Yw = Xw * Hw 
	
	fft = pyfftw.builders.ifft(Yw) # compute inverse fft to return to time domain
	yt = fft() 
	
	"""
	#plot y(t) and Y(f)
	fig, (tplot, fplot) = plt.subplots(2, 1)
	#plt.title("analytic output signal")
	tplot.plot(t,abs(yt),linewidth=0.7, color="#2da6f7")
	tplot.set_xlabel("t [s]")
	tplot.set_ylabel("y(t)")
	fplot.plot(f, abs(Yw),linewidth=0.7, color="#2da6f7")
	fplot.set_xlabel("f [Hz]")
	fplot.set_ylabel("Y(f)")
	plt.show()
	"""
	
	return yt, Yw

# translate signal to baseband (centered around 0Hz)
def to_baseband(xt):

	yt = xt * np.exp(-2*1j*np.pi*fc*t) 
	fft = pyfftw.builders.fft(yt) # compute fft
	Yw = fft() 
	
	"""
	#plot y(t) and Y(f)
	fig, (tplot, fplot) = plt.subplots(2, 1)
	#plt.title("analytic output signal")
	tplot.plot(t,abs(yt),linewidth=0.7, color="#2da6f7")
	tplot.set_xlabel("t [s]")
	tplot.set_ylabel("y(t)")
	fplot.plot(f_axis, np.fft.fftshift(abs(Yw)),linewidth=0.7, color="#2da6f7")
	fplot.set_xlabel("f [Hz]")
	fplot.set_ylabel("Y(f)")
	plt.show()
	"""
	
	return yt, Yw


# compensate for reduction of echo strength due to range
def range_compensation(xt):
	
	comp_factors = 0.5 * t * c
	yt = xt * comp_factors**2
	
	fft = pyfftw.builders.fft(yt) # compute fft
	Yw = fft() 
	
	"""
	#plot y(t) and Y(f)
	fig, (tplot1, tplot2) = plt.subplots(2, 1)
	#plt.title("analytic output signal")
	tplot1.plot(t,abs(xt),linewidth=0.7, color="#2da6f7")
	tplot1.set_xlabel("t [s]")
	tplot1.set_ylabel("x(t)")
	tplot2.plot(t,abs(yt),linewidth=0.7, color="#2da6f7")
	tplot2.set_xlabel("t [s]")
	tplot2.set_ylabel("y(t)")
	plt.show(block = False)
	"""
	
	return yt, Yw


def generate_range_profile(dists_to_targets):
	xt, Xw = make_chirp()
	vt, Vw = simulate_recieve_signal(dists_to_targets)
	yt, Yw = pulse_compression(Xw, Vw)
	yt, Yw = to_analytic_signal(Yw)
	yt, Yw = apply_window_function(Yw,2000,40000)
	yt, Yw = to_baseband(yt)
	yt, Yw = range_compensation(yt)
	
	
	"""
	#plot y(t) and Y(f)
	fig, (tplot, fplot) = plt.subplots(2, 1)
	#plt.title("analytic output signal")
	tplot.plot(t,abs(yt),linewidth=0.7, color="#2da6f7")
	tplot.set_xlabel("d [m]")
	tplot.set_ylabel("{}".format("|y(t)|"))
	#fplot.plot(f_axis, np.fft.fftshift(abs(Yw)),linewidth=0.7, color="#2da6f7")
	fplot.plot(t, np.angle(yt),linewidth=0.7, color="#2da6f7")
	fplot.set_xlabel("d [m]")
	fplot.set_ylabel("<y(t)")
	plt.show(block = False)
	"""
	
	
	return yt
	

# calculate distance between two points c1 and c2 - assumes rectangular coordinates
def calc_dist(c1, c2):
	diff = np.subtract(c1, c2)
	return math.sqrt(diff[0]**2+diff[1]**2)


def generate_all_range_profiles():
	# holds processed range profiles from each reciever
	range_profiles = [] # np.zeros((len(reciever_coords),N))
	for reciever in reciever_coords:
		dists_to_targets = []
		for target in target_coords:
			#temp = (target[0]*np.cos(target[1]), target[0]*np.sin(target[1]))
			temp = target
			dists_to_targets.append(calc_dist(reciever, target))
		range_profiles.append(generate_range_profile(dists_to_targets))
	
	return range_profiles


def coherent_summing(range_profiles):
	z = np.zeros((len(rad),len(azm))) # tuple (range,angle)
	z = np.array(z, dtype=complex)
	
	for i in range(0, len(rad)):
		for j in range(0, len(azm)):
			focus_point = (rad[i]*np.cos(azm[j]), rad[i]*np.sin(azm[j]))
			
			#distance between transmitter,  focus point, and reference point (0,0)
			dref = calc_dist(transmit_coord, focus_point) + calc_dist(focus_point, (0,0))
			tref = 2 * dref / c  # convert distance to time
			
			for n in range(0, len(reciever_coords)):
				dist = calc_dist(transmit_coord, focus_point) + calc_dist(focus_point, reciever_coords[n])
				td = 2 * dist / c
				
				index = int(round(td * 0.5 / Δt))
				value = range_profiles[n][index] * np.exp(2*1j*np.pi*fc*(td-tref))
				
				z[j][i] = z[j][i] + value #NB must be [j][i] as later plot expects [angle, magnitude]
	
	return z


def plot_2D_image(z):
	fig = plt.figure()
	r, th = np.meshgrid(rad, azm)
	ax = plt.subplot(projection="polar")
	
	ax.set_thetamin(45)
	ax.set_thetamax(-45)
	
	plt.pcolormesh(th, r, abs(z), cmap="inferno")
	plt.plot(azm, r, color='k', ls='none') 
	plt.colorbar()
	#plt.grid()
	plt.show(block=False)
	
	
	# plot cross-section of z at fixed range
	slice = [row[50] for row in z]
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
	

if __name__ == "__main__":
	
	start_time_millis = time.time()
	start_time_fmt = time.strftime("%H:%M:%S", time.localtime())
	
	range_profiles = generate_all_range_profiles()
	z = coherent_summing(range_profiles)
	
	end_time_millis = time.time()
	runtime = end_time_millis - start_time_millis
	print("Runtime info: starttime={}, runtime={}s".format(start_time_fmt,round(runtime,2)))
	
	plot_2D_image(z)

