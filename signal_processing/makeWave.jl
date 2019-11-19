#STEP ONE: CHIRP PULSE SIMULATION
# used to create header file for Teensy sketch
# creates array of values used to make a chirp waveform
# chirp waveform then output from Teensy DAC using TransducerInput.ino
function make_wave()
	#Specify parameters of chirp pulse
	f0 = 39000; # Centre frequency is 40 kHz
	B = 2000; # Chirp bandwidth
	#f0 = fc-B/2; # Inital frequency
	T =  7E-3; # Chirp pulse length Change back to 5E-3 if nec
	K = B/T; # Chirp rate

	#Define sampling and range parameters
	c = 343; # speed of sound in air in m/s
	fs = 400000; # sample rate of sonar, 44100 original 100 000
	dt = 1/fs; # sample spacing
	r_max = 10; # maximum range in metres
	t_max = 2*r_max/c + T; # time delay to max range

	# Create an array containing the time values of the samples
	t= 0:dt:t_max
	# Convert from time axis to range axis
	r = c*t/2;


	# Define a simple a rect() function which returns 1 for -0.5<=t<=0.5 only
	rect(t) = (abs.(t) .<= 0.5)*1.0
	# Delay the chirp pulse so that it starts after t=0.
	td = 0.6*T; # Chirp delay
	# Define shifted chirp pulse
	v_tx = cos.( 2*pi*(f0*(t .- td) + 0.5*K*(t .- td).^2) ) .* rect.((t .-td)/T);

	#print values of v_tx to a file
	#write header file 
	write_to_file_path = "./Waveforms.h";
	N = length(v_tx);
	output_file = open(write_to_file_path, "w+");
	println(output_file, "#ifndef _Waveforms_h_");
	println(output_file, "#define _Waveforms_h_");
	println(output_file, "#define maxWaveform 1");
	print(output_file, "#define maxSamplesNum ");
	println(output_file, N);
	println(output_file, "static float waveformsTable[maxWaveform][maxSamplesNum] = {");
	println(output_file, "{");
	print(output_file, v_tx[1]);
	for n=2:N;
		#write(output_file, v_tx[n]);
		#print(output_file, v_tx[n]);
		print(output_file, ", ");
		print(output_file, v_tx[n]);
	end
	println(output_file, "}");
	println(output_file, "};");
	println(output_file, "#endif");
end

make_wave();
