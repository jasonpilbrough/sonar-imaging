using FFTW   # Import Fourier library
using Dates
using DSP
using Plots
plt = Plots


starttime = Dates.Time(Dates.now())
gr(legend = true)
gr(reuse=false)

# utility function to initilise plots
function init_plot(xlabel, ylabel, plt_title="")
    plt.plot(xlabel = xlabel, ylabel = ylabel, guidefontsize=10)
    plt.plot!(title = plt_title,titlefontsize=10)
end

# utility function to display plot
function reveal()
    display(plt.plot!())

end

# calc distance between two cordinates
function calc_dist(o1,o2)
    diff = o1 .- o2
    return sqrt((diff[1])^2 + (diff[2])^2)

end

# calc distance between three cordinates
function two_way_dist(t_coord,r_coord, p_coord)
    return calc_dist(t_coord,p_coord) + calc_dist(p_coord,r_coord)
end


# find index of array that contains value - assumes sorted array
function find_closest_index(array, value)
    for x=1:length(array)
        if(array[x]>=value)
            return x
        end
    end
    return 1
end

function generate_noise(t, A)
    N = length(t);
    noise = randn(N);  # Create an array of N zero-mean Gaussian random number of std dev = 1.

    μ = 0.0     # desired mean
    σ = A * 0.02  # desired standard deviation
    noise = noise*σ .+ μ
    return noise;
end


#calculate required shift for basebanding
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


#performs signal processing and returns final range profile
function signal_processing(target_dists)

    # Define a rect(t) function
    rect(t) = ( abs.(t).<0.5 ) * 1.0
    window(w) = ( abs.(w).<0.5 ) * 1.0


    # variables all defined globally before this function is called
    global c, r_max, fc, T, fs, t_max, Δt, t, s, s_max


    B = 2000    # chirp bandwidth
    K = B/T     # chirp rate [Hz/s]
    f0 = fc-B/2 # initial freq of chirp
    λ = c/fc    # wavelength
    N=length(t)


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


    # ---------------------- STEP 1 --------------------------

    # Define chirp pulse
    x = rect((t .- T/2)/T).*cos.(2*pi*(f0*t+0.5*K*t.^2))
    X = fft(x)

    init_plot("t","x(t)","transmitted signal");
    plt.plot!(t,real.(x))
    timeplot1 = plt.plot!()

    init_plot("f [Hz]","X(w)");
    plt.plot!(f_axis[f_axis_0:length(f_axis)], fftshift(abs.(X))[f_axis_0:length(f_axis)]);
    freqplot = plt.plot!()

    plt.plot(timeplot1,freqplot, layout=(2,1))
    global plot1 = plt.plot!()
    #reveal()


    # ---------------------- STEP 2 --------------------------

    # simulate recieved echo based on target distances (passed as arguments)
    v1 = 0
    for i=1:length(target_dists)
        R = target_dists[i]
        td =  2*R/c
        A = 1/R^2
        v = A*rect((t .- (T/2+td) )/T).*cos.(2*pi*(f0*t+0.5*K*(t.-td).^2)) #.+ generate_noise(t,A)
        v1 = v1.+ v
    end

    V1 = fft(v1)

    init_plot("t","v1(t)","recieved signal 1");
    plt.plot!(t,v1)
    timeplot2 = plt.plot!()

    init_plot("f [Hz]","V1(w)");
    plt.plot!(f_axis[f_axis_0:length(f_axis)], fftshift(abs.(V1))[f_axis_0:length(f_axis)]);
    freqplot = plt.plot!()

    plt.plot(timeplot2,freqplot, layout = (2,1))
    global plot2 = plt.plot!()
    #reveal()

    # ---------------------- STEP 3 --------------------------

    #INVERSE FILTER
    wind = window((f .-fc % (N * Δf))/B)

    Y1 = V1./X .* (wind .+ wind[end:-1:1]) # to account for the ='ve and -'ve freq
    Y1[isnan.(Y1)] .= 0 #replace any Nan with 0 (arrises from zero-padding)

    # MATCHED FILTER - alternative
    #H = conj(X) # conjugate of X.
    #Y = H .* V

    #Output of filter
    y1 = ifft( Y1 ) # go back to time domain.

    # ---------------------- STEP 4 --------------------------

    #Create analytic signal

    Y1_an = 2*Y1
    for i = 1:length(Y1)
        if i > length(Y1)/2
            Y1_an[i] =0
        end
    end

    y1_an = ifft(Y1_an)

    init_plot("d","y1(t) - real ","output of inverse filter 1");
    plt.plot!(s,real.(y1))
    timeplot1 = plt.plot!()

    init_plot("d","y1_an(t) - abs");
    plt.plot!(s,abs.(y1_an))
    timeplot2 = plt.plot!()

    init_plot("f [Hz]","Y1(w)");
    plt.plot!(f_axis[f_axis_fc_lb:f_axis_fc_ub], fftshift(abs.(Y1))[f_axis_fc_lb:f_axis_fc_ub]);
    freqplot = plt.plot!()

    plt.plot(timeplot1,timeplot2,freqplot, layout=(3,1))
    global plot4 = plt.plot!()
    #reveal()


    # ---------------------- STEP 10 --------------------------

    #Windowing

    H_window = window((f.-fc)/(1.5*B))  .* cos.(pi*(f.-1200)/(0.7*N)) .^2

    Y1_window = Y1_an .* H_window
    y1_window = ifft(Y1_window)

    init_plot("d","y1(t) - with window","output 1 with windowing");
    plt.plot!(s,abs.(y1_window))
    timeplot1 = plt.plot!()

    init_plot("f [Hz]","Y1_window(w)");
    plt.plot!(f_axis[f_axis_fc_lb:f_axis_fc_ub],fftshift(abs.(Y1_window))[f_axis_fc_lb:f_axis_fc_ub])
    freqplot1 = plt.plot!()

    init_plot("f [Hz]","H_window(w)");
    plt.plot!(f_axis[f_axis_fc_lb:f_axis_fc_ub],fftshift(abs.(H_window))[f_axis_fc_lb:f_axis_fc_ub])
    freqplot2 = plt.plot!()


    plt.plot(timeplot1,freqplot1,freqplot2, layout=(3,1))
    global plot6 = plt.plot!()
    #reveal()


    # ---------------------- STEP 5 --------------------------

    #Basebanding
    shift_to_bb = calc_bb_shift(fc*1.0,fs)
    y1_bb = y1_window .* exp.(-im*2*pi*shift_to_bb*t) #need the % f_highest/2 for the case when sampling = 4B
    Y1_bb = fft(y1_bb)

    bb_zoom_upper = convert(Int,round(length(s)/8))
    bb_zoom_lower = convert(Int,round(length(s)/12))

    init_plot("d","y1_bb(t) - abs","basebanded output 1");
    plt.plot!(s,abs.(y1_bb))
    timeplot1 = plt.plot!()

    init_plot("d","y1_bb(t) - phase");
    plt.plot!(s,angle.(y1_bb))
    timeplot2 = plt.plot!()

    init_plot("f [Hz]","Y1_bb(w)");
    plt.plot!(f_axis[f_axis_bb_lb:f_axis_bb_ub],fftshift(abs.(Y1_bb))[f_axis_bb_lb:f_axis_bb_ub])
    freqplot = plt.plot!()

    plt.plot(timeplot1,timeplot2,freqplot, layout=(3,1))
    global plot8 = plt.plot!()
    #reveal()


    #y1_bb = y1_window
    #Y1_bb = fft(y1_bb)


    # ---------------------- STEP 7 --------------------------

    # range compensation

    range_comp1 = zeros(length(y1_bb))

    for i = 1:length(y1_bb)
        current_time = i * Δt
        current_dist = 0.5 * current_time * c
        range_comp1[i] = current_dist^2
    end

    y1_bb_r = y1_bb .* range_comp1


    # --------------- FINAL PLOT ----------------------

    y1_out = y1_bb_r

    zoom_start = convert(Int,round(N/5))
    zoom_end = convert(Int,round(N/3))

    init_plot("d","y_out(t)-mag","Processed Range Profile");
    plt.plot!(s,abs.(y1_out),xticks = (0:1:s_max))
    timeplot1 = plt.plot!()

    init_plot("d","y_out(t)-mag zoom");
    plt.plot!(s[zoom_start:zoom_end],abs.(y1_out)[zoom_start:zoom_end],xticks = (0:1:s_max))
    timeplot2 = plt.plot!()

    init_plot("d","y_out(t)-angle zoom");
    plt.plot!(s[zoom_start:zoom_end],angle.(y1_out)[zoom_start:zoom_end],xticks = (0:1:s_max), ylim=(-pi, pi))
    timeplot3 = plt.plot!()

    plt.plot(timeplot1,timeplot2,timeplot3, layout=(3,1), legend=false)
    global plot12 = plt.plot!()
    reveal()


    return y1_out

end




print("\n\n______________________________________\n\n")
print("STARTING UP APPLICATION...\n\n")


# GLOBAL VARIABLES FOR 1D RANGE PROFILE

global c = 343          # speed of sound in air
global r_max = 15       # max range in meters

global fc=40000         # center freq of chirp
global T=0.005          # chirp pulse length

global fs = 100000      # sampling rate

global t_max = 2*r_max/c + T   # max range in seconds
global Δt = 1/fs
global t=0:Δt:t_max


global s = 0.5 * t * c  # distance axis
global s_max = 0.5 * t_max * c


# 2D IMAGING

N = 200     # number of grid positions in x direction and y direction - total NxN
xlen = 10   # length in meters of x axis
ylen = 10   # length in meters of y axis

xs = 0:xlen/(N-1):xlen  # x axis
ys = 0:ylen/(N-1):ylen  # y axis

z = complex(zeros(N,N)) # holds value to each grid point

transmit_coord = (0.0,5.0) # (x,y)
#reciever_coords = [(0.0,5-reciever_spacing*3),(0.0,5-reciever_spacing*2),(0.0,5-reciever_spacing*1),(0.0,5.0),(0.0,5+reciever_spacing*1),(0.0,5+reciever_spacing*2),(0.0,5+reciever_spacing*3)]

# create array of recivers, evenly spaced
reciever_coords = []
num_recivers = 10
reciever_spacing = 0.01 # spacing between each of the recievers (in y axis)

for x in (num_recivers-1):-1:1
    val = (x-num_recivers/2)*reciever_spacing
    append!(reciever_coords, [(0.0,5-val)])
end

#target_coords = [(3,5),(4,5),(5,6),(9,5)]
target_coords = [(5,6)]
#target_coords = [(5,5)]

# holds processed range profiles from each reciever
range_profiles = zeros(Complex,length(reciever_coords),length(s))

print("PROCESSING EACH RANGE PROFILE...\n\n")

# determine range profile for each reciever
for x=1:length(reciever_coords)
    dists_to_targets = []
    # calculate the two way distances between the current reciever and each target
    for i=1:length(target_coords)
        append!(dists_to_targets, calc_dist(reciever_coords[x], target_coords[i]))
    end

    # perform range prfile processing
    range_profiles[x,1:end] = signal_processing(dists_to_targets)

end

print("GENERATING 2D IMAGE...\n\n")

field_of_view = 30 # degrees measured from boresight

# use each processed range profile to generate 2D image
for y=1:length(ys)
    for x=1:length(xs)

        #two way distance between transmitter,  focus point, and reference point (0,5)
        dref =  two_way_dist(transmit_coord,(0,5),(xs[x],ys[y]))
        tref = 2* dref / c  # convert distance to time

        if(y==(0.5*N) && x == (0.51*N))
            println("coord=(5,5)")
        elseif(y==(0.6*N) && x == (0.5*N))
            println("coord=(5,6)")
        end

        for n=1:length(reciever_coords)

            #two way distance between transmitter, focus point, and reciever
            dist = two_way_dist(transmit_coord,reciever_coords[n],(xs[x],ys[y]))
            td =  2*dist /c # convert distance into time

            value1 = range_profiles[n,find_closest_index(s,dist*0.5)]
            value = value1 .*exp(2*im*pi*fc*(td-tref))

            if(y==(0.5*N) && x == (0.51*N))

                println(abs.(value1)," ",angle.(value1).*180/pi, " ", abs.(value)," ",angle.(value).*180/pi, " td=",round(td*100000)/100000, " tref=", tref, " td-tref=",td-tref, " dist=",dist)
                #println(transmit_coord," ",reciever_coords[n]," ",(xs[x],ys[y])," ",calc_dist(reciever_coords[n],(xs[y],ys[x])))

                #print("n=",n," x=",xs[x]," y=",ys[y]," dist=",dist," ",abs.(closest)," ",(angle.(closest).*180/pi),"  ")
                correction = exp(2*im*pi*fc*(td-tref))

                #println(abs(closest)," tref=",tref," td=",td, " td-tref=",(td-tref))
                #print(abs(correction)," ",angle(correction).*180/pi,"\n")
            end

            if(y==(0.6*N) && x == (0.5*N))
                println(abs.(value1)," ",angle.(value1).*180/pi, " ", abs.(value)," ",angle.(value).*180/pi, " td=",round(td*100000)/100000 , " tref=", tref, " td-tref=",round((td-tref)*100000)/100000, " dist=",dist)
                #println(transmit_coord," ",reciever_coords[n]," ",(xs[x],ys[y])," ",calc_dist(reciever_coords[n],(xs[y],ys[x])))

                #print("n=",n," x=",xs[x]," y=",ys[y]," dist=",dist," ",abs.(closest)," ",(angle.(closest).*180/pi),"  ")
                correction = exp(2*im*pi*fc*(td-tref))

                #println(abs(closest)," tref=",tref," td=",td, " td-tref=",(td-tref))
                #print(abs(correction)," ",angle(correction).*180/pi,"\n")
            end

            #points outside field of view automatically set to 0
            if (abs(atan((ys[y]-transmit_coord[2])/(xs[x]-transmit_coord[1]))) < field_of_view * pi/180)
                z[y,x] = z[y,x]+value # accumulate values at current focus points from all recievers
            else
                z[y,x]= 0
            end

        end
    end
end


z = z.^0.5

heat = heatmap(ys, xs, abs.(z), aspect_ratio=1, xlabel = "x position", ylabel = "y position",title="2D Sonar Image", titlefontsize=10, guidefontsize=10)
plt.plot(heat, layout=(1,1))
plt.plot!(xlim=(0, 10), ylim=(0, 10),ticks=0:10)

line_upper(t) = t.*tan(field_of_view*pi/180).+5
line_lower(t) = t.*-tan(field_of_view*pi/180).+5
line_x = 0:1:10

plt.plot!(line_x, line_upper(line_x),color=[:grey], legend = false)
plt.plot!(line_x, line_lower(line_x),color=[:grey])
plt.plot!(4.999:0.0001:5.0,line_x , color=[:grey])
reveal()

init_plot("y","magnitude");
plt.plot!(ys,abs.(z[:,100]))
sliceplot1 = plt.plot!()

init_plot("y","phase");
plt.plot!(ys,angle.(z[:,100]))
sliceplot2 = plt.plot!()

plt.plot(sliceplot1,sliceplot2, layout=(2,1), legend=false, xticks=0:10)
reveal()

print("DONE.\n\n")


print("Runtime info: current_time=",Dates.Time(Dates.now())," duration=",Dates.Millisecond(Dates.Time(Dates.now())-starttime))
