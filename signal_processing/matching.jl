using FFTW   # Import Fourier library
using Dates
using DSP
using LibSerialPort
using Interact, Mux
using Plots
using CSV
using DelimitedFiles
plt = Plots

starttime = Dates.Time(Dates.now())
gr(legend = false)
gr(reuse=true)

function init_plot(xlabel, ylabel, plt_title="")
    plt.plot(xlabel = xlabel, ylabel = ylabel, guidefontsize=10)
    plt.plot!(title = plt_title,titlefontsize=10)
    #plt.plot!(tickfontsize=6)
end

function reveal()
    display(plt.plot!())
    #gui()

end

function generate_noise(t, A)
    N = length(t);
    noise = randn(N);  # Create an array of N zero-mean Gaussian random number of std dev = 1.

    μ = 0.0     # desired mean
    σ = A*0.2   # desired standard deviation
    noise = noise*σ .+ μ
    return noise;
end

function calc_bb_shift(f_c,f_s)
    if(f_c < f_s/2)
        return f_c
    end
    if(f_c < f_s)
        return f_s - f_c
    end
    temp = f_c%f_s
    if(temp > fs/2)
        temp = abs(temp-fs)
    end

    return temp

end


# Define a rect(t) function
rect(t) = ( abs.(t).<0.5 ) * 1.0
window(w) = ( abs.(w).<0.5 ) * 1.0


c = 343 # speed of sound in air
r_max = 10

fc=40000;   # center freq of chirp
T=0.005      # chirp pulse length
B = 2000    # chirp bandwidth
K = B/T     # chirp rate [Hz/s]
f0 = fc-B/2
#fs = 4*(1.6*B)
fs = 100000

#list_ports()
#send chirp command to Teensy
sp=open("/dev/cu.usbmodem58714801",9600) # Or whatever in Linux, Windows or Mac. //38400
#clear buffer
while(bytesavailable(sp) > 0)
    readline(sp);
end
write(sp, "s\n") # Sends chirp (DAC)
write(sp, "c\n") # This writes out the ASCII codes for H, e, l, l and o.
write(sp, "p\n")

#sleep(0.5) # Give time for a response from the micro
sleep(0.5)

#read in signal from serial port here
BytesAvailable = bytesavailable(sp) # Number of bytes available in the buffer
v=zeros(UInt16, 10006) # Create an Uint8 array into which to read the

n = 1
#print("BytesAvailableAtStart: ",bytesavailable(sp))
while(bytesavailable(sp) > 0) #divide this by 4?? 4 bytes in a float?
     v[n] = parse(UInt16, (readline(sp)));
     #println(v[n]);
     global n
     n = n+1;

end
close(sp) # Close the port.

v = v[50:end-1] #ignore the first 50 samples and last sample
v =  (v .* 3.3) / 65535

numSamples = length(v)

Δt = 1/fs
t_max = Δt*(numSamples-1)
t = 0:Δt:t_max
N=length(t)

#t_max = 2*r_max/c + T
#Δt = 1/fs
#t=0:Δt:t_max
#N=length(t)

# distance axis
s = 0.5 * t * c
s_max = 0.5 * t_max * c

#init frequency axis
Δω = 2*pi/(N*Δt)   # Sample spacing in freq domain in rad/s
Δf = Δω/(2*pi)
ω = 0:Δω:(N-1)*Δω
f = ω/(2*π)


#create array of freq values stored in f_axis. First element maps to 0Hz
if mod(N,2)==0    # case N even
    f_axis = (-N/2:N/2-1)*Δf;
else   # case N odd
    f_axis = (-(N-1)/2 : (N-1)/2)*Δf;
end

#convinient frequency axis labels
f_axis_0 = convert(Int,floor(N/2))

f_axis_fc = clamp(convert(Int, round(length(t)/2+(fc)/f_axis[length(t)]*length(t)/2)),1,length(t))
f_axis_fc_lb = clamp(convert(Int,f_axis_fc - round((B)/f_axis[length(t)]*length(t))),1,length(t))
f_axis_fc_ub = clamp(convert(Int,f_axis_fc + round((B)/f_axis[length(t)]*length(t))),1,length(t))

f_axis_bb_lb = clamp(convert(Int,f_axis_0 - round((B)/f_axis[length(t)]*length(t))),1,length(t))
f_axis_bb_ub = clamp(convert(Int,f_axis_0 + round((B)/f_axis[length(t)]*length(t))),1,length(t))




# ---------------------- STEP 2 --------------------------


v_prefilter = v;
V = fft(v)
HPF =  window((f .- fc)/(2*B)) .+ window((f.- (N*Δf-fc))/(2*B))
V = V.* HPF
v = real(ifft(V))


init_plot("t","v(t)","recieved signal");
plt.plot!(t,v)
timeplot1 = plt.plot!()

plt.plot(timeplot1, layout = (1,1))
global plot2 = plt.plot!()
reveal()

writedlm( "sonar_dump.csv",  v , ',')
