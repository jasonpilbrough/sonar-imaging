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
#plotly() #- opens in browser


#initilises plot
function init_plot(xlabel, ylabel, plt_title="")
    plt.plot(xlabel = xlabel, ylabel = ylabel, guidefontsize=10)
    plt.plot!(title = plt_title,titlefontsize=10)
end

#display plot
function reveal()
    display(plt.plot!())

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


#performs signal processing and returns final plot - inits many global vars for intermediate plots
function signal_processing()

    # Define a rect(t) function
    rect(t) = ( abs.(t).<0.5 ) * 1.0
    window(w) = ( abs.(w).<0.5 ) * 1.0


    c = 343 # speed of sound in air
    r_max = 10

    fc=40000;   # center freq of chirp
    T=0.005      # chirp pulse length
    B = 4000    # chirp bandwidth
    K = B/T     # chirp rate [Hz/s]
    f0 = fc-B/2
    #fs = 4*(1.6*B)
    fs = 250000 #100000 400000
    λ = c/fc #waveform

    #list_ports()
    #send chirp command to Teensy
    println("connecting to port")
    sp=open("/dev/cu.usbmodem58714801",9600) # Or whatever in Linux, Windows or Mac. //38400
    #clear buffer
    while(bytesavailable(sp) > 0)
        readline(sp);
    end
    write(sp, "s\n") # Sends chirp (DAC)
    println("chirp sent")
    write(sp, "c\n") # This writes out the ASCII codes for H, e, l, l and o.
    write(sp, "p\n")

    sleep(0.5) # Give time for a response from the micro

    #read in signal from serial port here
    BytesAvailable = bytesavailable(sp) # Number of bytes available in the buffer
    v1=zeros(Int32, 17006) # Create an Uint8 array into which to read the

    n = 1;
    #print("BytesAvailableAtStart: ",bytesavailable(sp))
    println("reading array 1")
    while(bytesavailable(sp) > 0) #divide this by 4?? 4 bytes in a float?
         v1[n] = parse(Int32, (readline(sp)));
         #println(v[n]);
         n = n+1;

    end

    #different symbol for second buffer
    write(sp, "a\n") #ask for second buffer
    sleep(0.5) # Give time for a response from the micro
    # Check if some data is now in the receive buffer:
    BytesAvailable = bytesavailable(sp) # Number of bytes available in the buffer
    #println("Bytes available:",BytesAvailable)
    v2=zeros(Int32, 17006)
    n = 1;
    #print("BytesAvailableAtStart: ",bytesavailable(sp))
    println("reading array 2")
    while(bytesavailable(sp) > 0) #divide this by 4?? 4 bytes in a float?
     #try
        #global n
         v2[n] = parse(Int32, (readline(sp))); #Int16
         n = n+1;

    end


    close(sp) # Close the port.


    #new array is now available as y

    v1 = v1[50:end-10] #ignore the first 50 samples and last sample
    v1 =  (v1 .* 3.3) / 65535

    v2 = v2[50:end-10] #ignore the first 50 samples and last sample
    v2 =  (v2 .* 3.3) / 65535

    numSamples = length(v1)

    Δt = 1/fs
    t_max = Δt*(numSamples-1)
    t = 0:Δt:t_max
    N=length(t)



    #=================================================
    t_max = 2*r_max/c + T
    Δt = 1/fs
    t=0:Δt:t_max
    N=length(t)
    =#

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


    # ---------------------- STEP 1 --------------------------

    # Define chirp pulse
    x = rect((t .- T/2)/T).*cos.(2*pi*(f0*t+0.5*K*t.^2))
    #x = CSV.read("sonar_dump3.csv",header=false)[1]
    #print(x)
    #temp = zeros(N-length(x))
    #x=vcat(x,temp)

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

    #= Simulate recieved signal 1
    R1 = 1.5 + (12-9)/12
    td1 =  2*R1/c
    A1 = 1/R1^2
    v1 = A1*rect((t .- (T/2+td1) )/T).*cos.(2*pi*(f0*t+0.5*K*(t.-td1).^2))

    # Simulate recieved signal 2
    R2 = 1.3 + (12-9)/12
    td2 =  2*R2/c
    A2 = 1/R2^2
    v2 = A2*rect((t .- (T/2+td2) )/T).*cos.(2*pi*(f0*t+0.5*K*(t.-td2).^2))

    =#


    #prepare recieved signal

    HPF =  window((f .- fc)/(2*B)) .+ window((f.- (N*Δf-fc))/(2*B))

    #apply BPF to signal 1
    v1_prefilter = v1;
    V1 = fft(v1)
    V1 = V1.* HPF
    v1 = real(ifft(V1))

    #writedlm( "sonar_dump.csv",  v1 , ',')

    #apply BPF to signal 1
    v2_prefilter = v2;
    V2 = fft(v2)
    V2 = V2.* HPF
    v2 = real(ifft(V2))

    #deadtime comp
    t_deadtime = 0.0065 #0.0055
    s_deadtime = 2.2295


    init_plot("t","v1(t) - prefilter","recieved signal 1");
    plt.plot!(t,v1_prefilter)
    timeplot1 = plt.plot!()

    init_plot("t","v1(t)");
    plt.plot!(t,v1)
    timeplot2 = plt.plot!()

    init_plot("f [Hz]","V1(w)");
    plt.plot!(f_axis[f_axis_0:length(f_axis)], fftshift(abs.(V1))[f_axis_0:length(f_axis)]);
    freqplot = plt.plot!()

    plt.plot(timeplot1, timeplot2,freqplot, layout = (3,1))
    global plot2 = plt.plot!()
    #reveal()

    init_plot("t","v2(t) - prefilter","recieved signal 2");
    plt.plot!(t,v2_prefilter)
    timeplot1 = plt.plot!()

    init_plot("t","v2(t)");
    plt.plot!(t,v2)
    timeplot2 = plt.plot!()

    init_plot("f [Hz]","V2(w)");
    plt.plot!(f_axis[f_axis_0:length(f_axis)], fftshift(abs.(V2))[f_axis_0:length(f_axis)]);
    freqplot = plt.plot!()

    plt.plot(timeplot1, timeplot2,freqplot, layout = (3,1))
    global plot3 = plt.plot!()
    #reveal()

    # ---------------------- STEP 3 --------------------------
    #Matched filter OR inverse filter

    # MATCHED FILTER
    #H = conj(X) # conjugate of X.
    #Y = H .* V

    #INVERSE FILTER
    wind = window((f .-fc % (N * Δf))/B)

    Y1 = V1./X .* (wind .+ wind[end:-1:1]) # to account for the ='ve and -'ve freq
    Y1[isnan.(Y1)] .= 0 #replace any Nan with 0 (arrises from zero-padding)

    Y2 = V2./X .* (wind .+ wind[end:-1:1]) # to account for the ='ve and -'ve freq
    Y2[isnan.(Y2)] .= 0 #replace any Nan with 0 (arrises from zero-padding)

    #Output of filter
    y1 = ifft( Y1 ) # go back to time domain.
    y2 = ifft( Y2 ) # go back to time domain.

    # ---------------------- STEP 4 --------------------------

    #Create analytic signal
    Y1_an = 2*Y1
    Y2_an = 2*Y2
    for i = 1:length(Y1)
        if i > length(Y1)/2
            Y2_an[i] =0
        end
        if i > length(Y2)/2
            Y2_an[i] =0
        end
    end


    y1_an = ifft(Y1_an)
    y2_an = ifft(Y2_an)


    init_plot("d","y1(t) - real ","output of inverse filter 1");
    plt.plot!(s,real.(y1))
    timeplot1 = plt.plot!()

    init_plot("d","y1_an(t) - abs");
    plt.plot!(s,abs.(y1_an))
    #plt.plot!(s[400:500],abs.(y_an)[400:500])
    timeplot2 = plt.plot!()

    init_plot("f [Hz]","Y1(w)");
    plt.plot!(f_axis[f_axis_fc_lb:f_axis_fc_ub], fftshift(abs.(Y1))[f_axis_fc_lb:f_axis_fc_ub]);
    freqplot = plt.plot!()

    plt.plot(timeplot1,timeplot2,freqplot, layout=(3,1))
    global plot4 = plt.plot!()
    #reveal()

    init_plot("d","y2(t) - real ","output of inverse filter 2");
    plt.plot!(s,real.(y2))
    timeplot1 = plt.plot!()

    init_plot("d","y2_an(t) - abs");
    plt.plot!(s,abs.(y2_an))
    #plt.plot!(s[400:500],abs.(y_an)[400:500])
    timeplot2 = plt.plot!()

    init_plot("f [Hz]","Y2(w)");
    plt.plot!(f_axis[f_axis_fc_lb:f_axis_fc_ub], fftshift(abs.(Y2))[f_axis_fc_lb:f_axis_fc_ub]);
    freqplot = plt.plot!()

    plt.plot(timeplot1,timeplot2,freqplot, layout=(3,1))
    global plot5 = plt.plot!()
    #reveal()

    # ---------------------- STEP 10 --------------------------

    H_window = window((f.-fc)/(1.5*B))  .* cos.(pi*(f.+700)/(0.4*N)) .^2

    Y1_window = Y1_an .* H_window
    y1_window = ifft(Y1_window)

    Y2_window = Y2_an .* H_window
    y2_window = ifft(Y2_window)

    init_plot("d","y1(t) - with window","output 1 with windowing");
    plt.plot!(s,abs.(y1_window))
    timeplot1 = plt.plot!()

    init_plot("f [Hz]","Y1_window(w)");
    plt.plot!(f_axis[f_axis_fc_lb:f_axis_fc_ub],fftshift(abs.(Y1_window))[f_axis_fc_lb:f_axis_fc_ub])
    freqplot1 = plt.plot!()

    init_plot("f [Hz]","H_window(w)");
    plt.plot!(f_axis[f_axis_fc_lb:f_axis_fc_ub],fftshift(abs.(H_window))[f_axis_fc_lb:f_axis_fc_ub])
    #plt.plot!(f_axis, fftshift(abs.(H_window)))
    freqplot2 = plt.plot!()


    plt.plot(timeplot1,freqplot1,freqplot2, layout=(3,1))
    global plot6 = plt.plot!()
    #reveal()

    init_plot("d","y2(t) - with window","output 2 with windowing");
    plt.plot!(s,abs.(y2_window))
    timeplot1 = plt.plot!()

    init_plot("f [Hz]","Y2_window(w)");
    plt.plot!(f_axis[f_axis_fc_lb:f_axis_fc_ub],fftshift(abs.(Y2_window))[f_axis_fc_lb:f_axis_fc_ub])
    freqplot1 = plt.plot!()

    init_plot("f [Hz]","H_window(w)");
    plt.plot!(f_axis[f_axis_fc_lb:f_axis_fc_ub],fftshift(abs.(H_window))[f_axis_fc_lb:f_axis_fc_ub])
    #plt.plot!(f_axis, fftshift(abs.(H_window)))
    freqplot2 = plt.plot!()


    plt.plot(timeplot1,freqplot1,freqplot2, layout=(3,1))
    global plot7 = plt.plot!()
    #reveal()

    #init_plot("f","Y(w) - with window","testing");
    #plt.plot!(f_axis[f_axis_fc_lb:f_axis_fc_ub],fftshift(H_window)[f_axis_fc_lb:f_axis_fc_ub])
    #plt.plot!(f_axis[f_axis_fc_lb:f_axis_fc_ub],fftshift(H_window)[f_axis_fc_lb:f_axis_fc_ub])
    #timeplot1 = plt.plot!()
    #plt.plot(timeplot1, layout=(1,1))
    #global plot4 = plt.plot!()
    #reveal()


    # ---------------------- STEP 5 --------------------------

    #Basebanding
    #shift_to_bb = min(-fc + ceil(fc/fs)*fs, fc*1) # to account for when sampled below nyquist rate
    shift_to_bb = calc_bb_shift(fc*1.01,fs) # multiply by 1% for correction
    y1_bb = y1_window .* exp.(-im*2*pi*shift_to_bb*t) #need the % f_highest/2 for the case when sampling = 4B
    Y1_bb = fft(y1_bb)

    y2_bb = y2_window .* exp.(-im*2*pi*shift_to_bb*t) #need the % f_highest/2 for the case when sampling = 4B
    Y2_bb = fft(y2_bb)

    bb_zoom_upper = convert(Int,round(length(s)/8))
    bb_zoom_lower = convert(Int,round(length(s)/12))

    init_plot("d","y1_bb(t) - abs","basebanded output 1");
    plt.plot!(s,abs.(y1_bb))
    timeplot1 = plt.plot!()

    init_plot("d","y1_bb(t) - phase");
    plt.plot!(s,angle.(y1_bb))
    timeplot2 = plt.plot!()

    init_plot("f [Hz]","Y1_bb(w)");
    #plt.plot!(f_axis[f_axis_bb_lb:f_axis_bb_ub],fftshift(abs.(Y_bb))[f_axis_bb_lb:f_axis_bb_ub])
    plt.plot!(f_axis[f_axis_bb_lb:f_axis_bb_ub],fftshift(abs.(Y1_bb))[f_axis_bb_lb:f_axis_bb_ub])
    freqplot = plt.plot!()

    plt.plot(timeplot1,timeplot2,freqplot, layout=(3,1))
    global plot8 = plt.plot!()
    #reveal()

    init_plot("d","y2_bb(t) - abs","basebanded output 2");
    plt.plot!(s,abs.(y2_bb))
    timeplot1 = plt.plot!()

    init_plot("d","y2_bb(t) - phase");
    plt.plot!(s,angle.(y2_bb))
    timeplot2 = plt.plot!()

    init_plot("f [Hz]","Y2_bb(w)");
    #plt.plot!(f_axis[f_axis_bb_lb:f_axis_bb_ub],fftshift(abs.(Y_bb))[f_axis_bb_lb:f_axis_bb_ub])
    plt.plot!(f_axis,fftshift(abs.(Y2_bb)))
    freqplot = plt.plot!()

    plt.plot(timeplot1,timeplot2,freqplot, layout=(3,1))
    global plot9 = plt.plot!()
    #reveal()






    # ---------------------- STEP 11 --------------------------

    #account for dead time by moving the last bit of the array to the beginning
    cut_index = Int(round(N-(t_deadtime/t_max * N)))
    y1_out_comp = vcat(y1_bb[cut_index:end-1],y1_bb[1:cut_index])
    y2_out_comp = vcat(y2_bb[cut_index:end-1],y2_bb[1:cut_index])

    init_plot("d","y1_before_shift(t)","deadtime compensation");
    plt.plot!(s,abs.(y1_bb))
    timeplot1 = plt.plot!()

    init_plot("d","y1_after_shift(t)");
    plt.plot!(s,abs.(y1_out_comp))
    timeplot2 = plt.plot!()

    plt.plot(timeplot1,timeplot2, layout=(2,1))
    global plot10 = plt.plot!()
    #reveal()

    init_plot("d","y2_before_shift(t)","deadtime compensation");
    plt.plot!(s,abs.(y2_bb))
    timeplot1 = plt.plot!()

    init_plot("d","y2_after_shift(t)");
    plt.plot!(s,abs.(y2_out_comp))
    timeplot2 = plt.plot!()

    plt.plot(timeplot1,timeplot2, layout=(2,1))
    global plot11 = plt.plot!()
    #reveal()


    # ---------------------- Step 12 -------------------------

    #Phase calculation

    bb_zoom_upper = convert(Int,round(length(s)/4.5))
    bb_zoom_lower = convert(Int,round(length(s)/5.5))

    init_plot("d","y1_out(t) - abs","phase calc - calibrated for roof target");
    plt.plot!(s[bb_zoom_lower:bb_zoom_upper],abs.(y1_out_comp)[bb_zoom_lower:bb_zoom_upper])
    plt.plot!(s[bb_zoom_lower:bb_zoom_upper],abs.(y2_out_comp)[bb_zoom_lower:bb_zoom_upper])
    timeplot1 = plt.plot!()

    phase = angle.(y2_out_comp.*conj.(y1_out_comp))

    init_plot("d","psi_bb(t)");
    plt.plot!(s[bb_zoom_lower:bb_zoom_upper],angle.(y1_out_comp)[bb_zoom_lower:bb_zoom_upper])
    plt.plot!(s[bb_zoom_lower:bb_zoom_upper],angle.(y2_out_comp)[bb_zoom_lower:bb_zoom_upper])
    plt.plot!(s[bb_zoom_lower:bb_zoom_upper],phase[bb_zoom_lower:bb_zoom_upper])
    timeplot2 = plt.plot!()

    plt.plot(timeplot1,timeplot2, layout=(2,1))
    global plot14 = plt.plot!()
    #reveal()

    init_plot("d","y1_bb(t) - abs","phase calc");
    plt.plot!(s,abs.(y1_out_comp))
    plt.plot!(s,abs.(y2_out_comp))
    timeplot1 = plt.plot!()

    delta_psi = angle.(y2_out_comp.*conj.(y1_out_comp))

    init_plot("d","psi_bb(t)");
    plt.plot!(s,delta_psi)
    timeplot2 = plt.plot!()

    plt.plot(timeplot1,timeplot2, layout=(2,1))
    global plot15 = plt.plot!()
    #reveal()


    # ---------------------- STEP 7 --------------------------
    #y_bb_r = y_bb
    range_comp1 = zeros(length(y1_out_comp))
    range_comp2 = zeros(length(y2_out_comp))

    for i = 1:length(y1_out_comp)
        current_time = i * Δt
        current_dist = 0.5 * current_time * c
        #global range_comp
        range_comp1[i] = current_dist^2
        range_comp2[i] = current_dist^2
    end

    global range_comp_active

    if range_comp_active
        y1_bb_r = y1_out_comp .* range_comp1
        y2_bb_r = y2_out_comp .* range_comp2
    else
        y1_bb_r = y1_out_comp
        y2_bb_r = y2_out_comp
    end


    # ---------------------- STEP 8 --------------------------

    #No error padding



    # --------------- FINAL PLOT ----------------------

    y1_out = y1_bb_r
    y2_out = y2_bb_r


    init_plot("d","y1_out(t) ");
    plt.plot!(s,abs.(y1_out),xticks = (0:1:s_max))
    timeplot1 = plt.plot!()

    plt.plot(timeplot1, layout=(1,1))
    global plot12 = plt.plot!()
    #reveal()

    init_plot("d","y2_out(t) ");
    plt.plot!(s,abs.(y2_out),xticks = (0:1:s_max))
    timeplot1 = plt.plot!()

    plt.plot(timeplot1, layout=(1,1))
    global plot13 = plt.plot!()
    reveal()


    suspected_targets_inds = printTargetDists(abs.(y2_out),Δt,c) # assumes same targets will be present in both y1 and y2
    print("\n")


    # ---------------------- Step 13 -------------------------

    #2D imaging

    theta_k0 = asin.((λ)*delta_psi/(2*pi*0.018)) #seperation distance is 0.018
    theta_minusk = asin.(λ*(delta_psi .- 2 * pi)/(2*pi*0.018))
    theta_plusk = asin.(λ*(delta_psi .+ 2 * pi)/(2*pi*0.018))

    phase_plot_x_k0 = zeros(length(suspected_targets_inds))
    phase_plot_y_k0 = zeros(length(suspected_targets_inds))

    phase_plot_x_kminus1 = zeros(length(suspected_targets_inds))
    phase_plot_y_kminus1 = zeros(length(suspected_targets_inds))

    phase_plot_x_kplus1 = zeros(length(suspected_targets_inds))
    phase_plot_y_kplus1 = zeros(length(suspected_targets_inds))



    for i = 1:length(suspected_targets_inds)
        ang_rad0 = theta_k0[suspected_targets_inds[i]]
        phase_plot_x_k0[i] = s[suspected_targets_inds[i]] .* cos(ang_rad0)
        phase_plot_y_k0[i] = s[suspected_targets_inds[i]] .* sin(ang_rad0)

        ang_rad_minus1 = theta_minusk[suspected_targets_inds[i]]
        phase_plot_x_kminus1[i] = s[suspected_targets_inds[i]] .* cos(ang_rad_minus1)
        phase_plot_y_kminus1[i] = s[suspected_targets_inds[i]] .* sin(ang_rad_minus1)

        ang_rad_plus1 = theta_plusk[suspected_targets_inds[i]]
        phase_plot_x_kplus1[i] = s[suspected_targets_inds[i]] .* cos(ang_rad_plus1)
        phase_plot_y_kplus1[i] = s[suspected_targets_inds[i]] .* sin(ang_rad_plus1)
    end

    init_plot("x","y");
    plt.plot!(phase_plot_x_k0,phase_plot_y_k0, line=(:scatter), xticks = 0:1:10, yticks = -5:1:5, xlims=[0,10],ylims=[-5,5], marker=([:hex :d]))
    plt.plot!(phase_plot_x_kminus1,phase_plot_y_kminus1, line=(:scatter), xticks = 0:1:10, yticks = -5:1:5, xlims=[0,10],ylims=[-5,5], marker=([:hex :d]),color=[:grey])
    plt.plot!(phase_plot_x_kplus1,phase_plot_y_kplus1, line=(:scatter), xticks = 0:1:10, yticks = -5:1:5, xlims=[0,10],ylims=[-5,5], marker=([:hex :d]),color=[:grey])
    plt.plot!(0:1:10,0:2.59/10:2.59,color=[:grey])
    plt.plot!(0:1:10,0:-2.59/10:-2.59,color=[:grey])
    timeplot1 = plt.plot!()
    plt.plot(timeplot1, layout=(1,1))
    global plot16 = plt.plot!()
    reveal()

    return plot12

end



function printTargetDists(signal,Δt,c)
    peak_thresh = maximum(abs.(signal)) * 0.5
    inds = Int[]
    if length(signal)>1
       if signal[1]>signal[2]
           if signal[1] > peak_thresh
               push!(inds,1)
           end
       end
       for i=2:length(signal)-1
           if signal[i-1]<signal[i]>signal[i+1]
               if signal[i] > peak_thresh
                   push!(inds,i)
               end
           end
       end
       if signal[end]>signal[end-1]
            if signal[end] > peak_thresh
                push!(inds,length(signal))
            end
       end
   end
   print("Targets detected at: ")
   print(inds*Δt*0.5*c)
   print("     ")
   return inds
 end



function continuous_mode(temp)
    for i = 1:1
        signal_processing()
        mainplot = Interact.@map (&b1; plot7)
        global plot1
        im_plot1 = Interact.@map (&b1; plot1)
        global plot2
        im_plot2 = Interact.@map (&b1; plot2)
        global plot3
        im_plot3 = Interact.@map (&b1; plot3)
        global plot4
        im_plot4 = Interact.@map (&b1; plot4)
        global plot5
        im_plot5 = Interact.@map (&b1; plot5)
        global plot6
        im_plot6 = Interact.@map (&b1; plot6)

        sleep(3)
        print("\nI AM HEREs\n")
    end
end

function toggle_range_comp()
    global range_comp_active
    range_comp_active = !range_comp_active
end



function generateUI()

    #DO NOT DELETE ANY OF THESE - EVERYTHING BREAKS
    r = slider(0:255, label = "red")
    g = slider(0:255, label = "green")
    b = slider(0:255, label = "blue")
    output = Interact.@map Colors.RGB(&r/255, &g/255, &b/255)
    wdg = Widget(["r" => r, "g" => g, "b" => b], output = output)
    ##

    #default val
    global range_comp_active = true

    println("setup")


    title = HTML(string("<div style='font-size:40px; padding:35px;'> <center>SONAR IMAGING </center></div>"))
    header0 = HTML(string("<div style='font-size:20px; padding:20px;'> FINAL PROCESSED PLOT </div>"))
    header1 = HTML(string("<div style='font-size:20px; padding:20px;'> CONTROL PANEL </div>"))
    header2 = HTML(string("<div style='font-size:20px; padding:20px;'> INTERMEDIATE PLOTS </div>"))
    b1 =button("Single shot", color = Colors.RGB(0.0, 0.5, 0.0))
    b2 =button("Start continuous imaging")
    b3 = button("Stop continuous imaging")

    chkbox = checkbox(label="Range compensation")
    drpdwn = dropdown(["1D","2D","3D"])

    #print(chkbox)
    #set_range_comp(chkbox)

    #toggle_range_comp()
    plot_once = Interact.@map (&chkbox; toggle_range_comp())
    plot_once = Interact.@map (&b1; signal_processing())
    #plot_once = Interact.@map (&b2; continuous_mode(1))


    mainplot = Interact.@map (&b1; plot16)
    global plot1
    im_plot1 = Interact.@map (&b1; plot1)
    global plot2
    im_plot2 = Interact.@map (&b1; plot2)
    global plot3
    im_plot3 = Interact.@map (&b1; plot3)
    global plot4
    im_plot4 = Interact.@map (&b1; plot4)
    global plot5
    im_plot5 = Interact.@map (&b1; plot5)
    global plot6
    im_plot6 = Interact.@map (&b1; plot6)
    global plot7
    im_plot7 = Interact.@map (&b1; plot7)
    global plot8
    im_plot8 = Interact.@map (&b1; plot8)
    global plot9
    im_plot9 = Interact.@map (&b1; plot9)
    global plot10
    im_plot10 = Interact.@map (&b1; plot10)
    global plot11
    im_plot11 = Interact.@map (&b1; plot11)
    global plot12
    im_plot12 = Interact.@map (&b1; plot12)
    global plot13
    im_plot13 = Interact.@map (&b1; plot13)
    global plot14
    im_plot14 = Interact.@map (&b1; plot14)
    global plot15
    im_plot15 = Interact.@map (&b1; plot15)
    global plot16
    im_plot15 = Interact.@map (&b1; plot16)

    """mainplot = Interact.@map (&plot7)
    global plot1
    im_plot1 = Interact.@map (&plot1)
    global plot2
    im_plot2 = Interact.@map (&plot2)
    global plot3
    im_plot3 = Interact.@map (&plot3)
    global plot4
    im_plot4 = Interact.@map (&plot4)
    global plot5
    im_plot5 = Interact.@map (&plot5)"""



    """controlpanel = vbox(hbox(pad(1em, b1),pad(1em, b2),pad(1em, b3)), hbox(pad(1em, chkbox), pad(1em,drpdwn)))
    subplots= vbox(header2,hbox(im_plot1,im_plot2),hbox(im_plot3,im_plot4),hbox(im_plot5))
    mainlayout = vbox(title,mainplot,header1,controlpanel,subplots)"""

    controlpanel = vbox(pad(1em, b1),pad(1em, b2),pad(1em, b3), hbox(pad(1em, chkbox), pad(1em,drpdwn)))
    subplots= vbox(header2,hbox(im_plot12,im_plot13),hbox(im_plot1),hbox(im_plot2,im_plot3),hbox(im_plot4,im_plot5),hbox(im_plot6,im_plot7),hbox(im_plot8,im_plot9),hbox(im_plot10,im_plot11),hbox(im_plot14,im_plot15))
    mainlayout = vbox(title,hbox(pad(4em, vbox(header0, mainplot)),pad(4em, vbox(header1,controlpanel))),pad(4em, subplots))

    @layout! wdg mainlayout ## custom layout: by default things are stacked vertically

end


print("\n\nSTARTING UP APPLICATION...\n\n")

PORT = rand(8000:9000)


#signal_processing();

ui = generateUI()
WebIO.webio_serve(page("/", req -> ui), PORT) # serve on a random port

print("Ready to serve on Port ",PORT)
print("\n\n")




print("Setup info: time=",Dates.Time(Dates.now())," duration=",Dates.Millisecond(Dates.Time(Dates.now())-starttime))
