var globaltime = new Date();
var continuousMode = false;
var running = false;
var stopInterrupt = false;
var isMicroConnected = false;
var debuggingState = "off"; // options are off, waiting, on
var numReceivers = 8;


//runs once page has loaded - to ensure some UI indicators update straight away
document.addEventListener("DOMContentLoaded", function(){
    //testInternetConnection()
    testMicroStatus()
});


function loadMainplot() {

		globaltime =  new Date();
		
		val = Math.random(); 
		img = document.getElementById("mainplot");
		
		var is_1D_mode = document.getElementById("display_mode_toggle").checked
		
		//var displayRadios = document.getElementsByName("radio_display_mode");
		//var is_1D_mode = displayRadios[0].checked //true if continuous mode at radios[1] is selected
		
		var isSimMode = document.getElementById("simulation_mode_toggle").checked
		var isDebugMode = document.getElementById('debug_mode_toggle').checked

		var urlArguments = "sim_mode="+isSimMode+"&debug_mode="+isDebugMode+"&rand_number="+val // random number forces browser to reload image

		if(is_1D_mode){
			img.src="sonar_image_1D.png?" + urlArguments
		} else{
			img.src="sonar_image_2D.png?" + urlArguments 
		}

		
		var mainplot_image = document.getElementById("mainplot");
		
		//when the mainplot loads
		mainplot_image.onload = function() {
    		var runtime = new Date() - globaltime
    		document.getElementById("label_refresh_rate").innerHTML = runtime/1000.0 + " s";
    		document.getElementById("label_refresh_rate").classList.remove('badge-secondary');
			document.getElementById("label_refresh_rate").classList.add('badge-success');
			
			var isDebugMode = document.getElementById('debug_mode_toggle').checked
			
			//only load debug plots if in debug mode
			if(isDebugMode){
				loadDebugplots()
			}
    		
  			//if in continuous mode keep running
  			if(continuousMode && !stopInterrupt){
  				loadMainplot();
  			} else{
  				running = false;
  				stopInterrupt = false;
  				document.getElementById("label_current_state").innerHTML = "Idle";
    			document.getElementById("label_current_state").classList.remove('badge-success');
    			document.getElementById("label_current_state").classList.remove('badge-danger');
  				document.getElementById("label_current_state").classList.add('badge-secondary');
  			}
			
		};
		
		/* TODO FIX 
		img = document.getElementById("mainplot_zoom"); //zoomed in version
		img.src="plot.png?rand_number=" + val; // same rand number = same image as above
		*/
		  		
}


function loadDebugplots() {
	
	val = Math.random(); 
	
	
	var is_1D_mode = document.getElementById("display_mode_toggle").checked
	var isSimMode = document.getElementById("simulation_mode_toggle").checked
	
	var debugplot_chirp = document.getElementById("debugplot_chirp");
	debugplot_chirp.src = "debug?plotname=_1_chirp.png&rand_number=" + val
	
	for(var i = 0; i< numReceivers; i++){
		
		// stop early if in 1D mode
		if(is_1D_mode && i>0){
			break;
		}
		
		var debugplot_receive = document.getElementById("debugplot_"+i+"_receive");
		var debugplot_filter = document.getElementById("debugplot_"+i+"_filter");
		var debugplot_window = document.getElementById("debugplot_"+i+"_window");
		var debugplot_baseband = document.getElementById("debugplot_"+i+"_baseband");
		var debugplot_comp = document.getElementById("debugplot_"+i+"_comp");
		var debugplot_range_profile = document.getElementById("debugplot_"+i+"_range_profile");
		
		
		debugplot_receive.src = "debug?plotname="+i+"_1_receive.png&rand_number=" + val
		debugplot_filter.src = "debug?plotname="+i+"_2_filter.png&rand_number=" + val
		debugplot_window.src = "debug?plotname="+i+"_3_window.png&rand_number=" + val
		debugplot_baseband.src = "debug?plotname="+i+"_4_baseband.png&rand_number=" + val
		debugplot_comp.src = "debug?plotname="+i+"_5_comp.png&rand_number=" + val
		debugplot_range_profile.src = "debug?plotname="+i+"_6_range_profile.png&rand_number=" + val
	}
	
	if(!isSimMode && !is_1D_mode){
		var debugplot_all_profile_mags = document.getElementById("debugplot_all_profile_mags");
		var debugplot_all_profile_phases = document.getElementById("debugplot_all_profile_phases");
		debugplot_all_profile_mags.src = "debug?plotname=all_profile_mags.png&rand_number=" + val
		debugplot_all_profile_phases.src = "debug?plotname=all_profile_phases.png&rand_number=" + val
	}
	
	//when the first debug plot arrives, show all plots
	document.getElementById("debugplot_chirp").onload = function() {
		var debuggerView = document.getElementById("debuggerView");
		var debuggerWaitingMsg = document.getElementById("debuggerWaitingMsg");
		
		var debuggerOutputRec0 = document.getElementById("debuggerOutput-reciever0");
		var debuggerOutputRemRec = document.getElementById("debuggerOutput-remainingRecievers");
		var debuggerOutputCombinedRec = document.getElementById("debuggerOutput-combinedRecievers");
	
		debuggerView.style.display = "block";
		debuggerWaitingMsg.style.display = "none";
		
		if(is_1D_mode){
			debuggerOutputRec0.style.display = "block";
			debuggerOutputRemRec.style.display = "none";
		}else{
			debuggerOutputRec0.style.display = "block";
			debuggerOutputRemRec.style.display = "block";
			
			//only show if 2D mode and not sim
			if(isSimMode){
				debuggerOutputCombinedRec.style.display = "none";
			}else{
				debuggerOutputCombinedRec.style.display = "block";
			}
		}
		
		
		
	
		debuggingState = "on"
	}
	
	
	

}



$('#debug_mode_toggle').change(function() {
    var debuggerView = document.getElementById("debuggerView");
	var debuggerWaitingMsg = document.getElementById("debuggerWaitingMsg");
	
	var debuggerOutputRec0 = document.getElementById("debuggerOutput-reciever0");
	var debuggerOutputRemRec = document.getElementById("debuggerOutput-remainingRecievers");
	var debuggerOutputCombinedRec = document.getElementById("debuggerOutput-combinedRecievers");
	
	
	if (debuggingState === "off") {
		debuggingState = "waiting"
		debuggerView.style.display = "block";
		debuggerWaitingMsg.style.display = "block";
		
		debuggerOutputRec0.style.display = "none";
		debuggerOutputRemRec.style.display = "none";
		debuggerOutputCombinedRec.style.display = "none";
		
	} else {
		debuggingState = "off"
		debuggerView.style.display = "none";
	}
})
    
    
    
//when Run button is pressed 
document.getElementById("btn_run").addEventListener("click", function(){

	loadMainplot();
	
	continuousMode = !document.getElementById("imaging_mode_toggle").checked
	running = true;
	
	if(continuousMode){
		document.getElementById("label_current_state").innerHTML = "Running (cont.)";
	} else{
		document.getElementById("label_current_state").innerHTML = "Running (single)";
	}
  	document.getElementById("label_current_state").classList.remove('badge-secondary');
  	document.getElementById("label_current_state").classList.add('badge-success');

});

//when Stop button is pressed 
document.getElementById("btn_stop").addEventListener("click", function(){

	//only execute if system is running
	if(running){
		stopInterrupt = true
		document.getElementById("label_current_state").innerHTML = "Stopping...";
  		document.getElementById("label_current_state").classList.remove('badge-success');
  		document.getElementById("label_current_state").classList.add('badge-danger');
	}

});


/*
//check internet connection every 10s and update UI indicator
var intervalInternetID = setInterval(testInternetConnection, 10000);
function testInternetConnection() {
    var internetConnected = navigator.onLine
    if(internetConnected){
    	document.getElementById("label_internet_connection").innerHTML = "Connected";
    	document.getElementById("label_internet_connection").classList.remove('badge-danger');
    	document.getElementById("label_internet_connection").classList.add('badge-success');
    } else {
    	document.getElementById("label_internet_connection").innerHTML = "Not Connected";
    	document.getElementById("label_internet_connection").classList.remove('badge-success');
    	document.getElementById("label_internet_connection").classList.add('badge-danger');
    } 
}
*/


//check micro every 10s and update UI indicator
var intervalMicroID = setInterval(testMicroStatus, 10000);
function testMicroStatus() {

	//dont check micro status if system is running
	if(!running){
		$.ajax({
		type : "POST",
		url : '/micro_status',
		dataType: "json",
		data: JSON.stringify("you can put in a variable in here to send data with the request"),
		contentType: 'application/json;charset=UTF-8',
		success: function (data) {
		
				var micro_connection = data["connection"];
				var sample_rate = data["sample_rate"];
		
				document.getElementById("label_micro_connection").innerHTML = micro_connection; 
				document.getElementById("label_sample_rate").innerHTML = sample_rate;
				
				
				//if this request is successful - server must be connected
				document.getElementById("label_server_connection").innerHTML = "Connected";
    			document.getElementById("label_server_connection").classList.remove('badge-danger');
    			document.getElementById("label_server_connection").classList.add('badge-success');
		
		
				if(micro_connection==="Connected"){
					isMicroConnected = true;
					document.getElementById("label_micro_connection").classList.remove('badge-danger');
					document.getElementById("label_micro_connection").classList.add('badge-success');
				}else{
					isMicroConnected = false;
					document.getElementById("label_micro_connection").classList.remove('badge-success');
					document.getElementById("label_micro_connection").classList.add('badge-danger');
				}
		
				if(sample_rate==="N/A"){
					document.getElementById("label_sample_rate").classList.remove('badge-success');
					document.getElementById("label_sample_rate").classList.add('badge-secondary');
				} else{
					document.getElementById("label_sample_rate").classList.remove('badge-secondary');
					document.getElementById("label_sample_rate").classList.add('badge-success');
				}
		
		
			},
		error: function(XMLHttpRequest, textStatus, errorThrown) { 
		
			//server not connected	
			document.getElementById("label_server_connection").innerHTML = "Not Connected";
    		document.getElementById("label_server_connection").classList.remove('badge-success');
    		document.getElementById("label_server_connection").classList.add('badge-danger');
    		
    		//assume micro isnt connected
			isMicroConnected = false;
			document.getElementById("label_micro_connection").innerHTML = "Not Connected"; 	
			document.getElementById("label_micro_connection").classList.remove('badge-success');
			document.getElementById("label_micro_connection").classList.add('badge-danger');
			document.getElementById("label_sample_rate").innerHTML = "N/A";
			document.getElementById("label_sample_rate").classList.remove('badge-success');
			document.getElementById("label_sample_rate").classList.add('badge-secondary');
			
			running = false;
			document.getElementById("label_current_state").innerHTML = "Idle";
			document.getElementById("label_current_state").classList.remove('badge-success');
			document.getElementById("label_current_state").classList.remove('badge-danger');
			document.getElementById("label_current_state").classList.add('badge-secondary');
		}
		});
	}

}



/*

//when debug checkbox is checked
document.getElementById("debugCheck").addEventListener("click", function(){

	var debuggerView = document.getElementById("debuggerView");
	var debuggerWaitingMsg = document.getElementById("debuggerWaitingMsg");
	
	var debuggerOutputRec0 = document.getElementById("debuggerOutput-reciever0");
	var debuggerOutputRemRec = document.getElementById("debuggerOutput-remainingRecievers");
	
	
	if (debuggingState === "off") {
		debuggingState = "waiting"
		debuggerView.style.display = "block";
		debuggerWaitingMsg.style.display = "block";
		
		debuggerOutputRec0.style.display = "none";
		debuggerOutputRemRec.style.display = "none";
		
	} else {
		debuggingState = "off"
		debuggerView.style.display = "none";
	}
});

*/









