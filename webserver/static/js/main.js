/* ============================== GLOBAL VARIABLES ============================== */

//indicates is system is currently running
var RUNNING = false;					

//indicates if stop btn has been pressed and system is waiting for last plot to arrive before it can stop
var STOP_INTERRUPT = false;		
		
//options for debugging state are off, waiting, or on
var DEBUGGING_STATE = "off"; 

//number of sonar receivers 
var NUM_RECIEVERS = 8;


/* ========================= REGISTER EVENT LISTENSERS  ========================= */


//runs once page has loaded and ensures that UI micro indicator updates straight away
document.addEventListener("DOMContentLoaded", function(){
    testMicroStatus()
});


//handles when Run button is pressed 
document.getElementById("btn_run").addEventListener("click", function(){
	
	loadMainplot();
	
	//update UI indicators as required
	var continuousMode = !document.getElementById("imaging_mode_toggle").checked
	if(continuousMode){
		document.getElementById("label_current_state").innerHTML = "Running (cont.)";
	} else{
		document.getElementById("label_current_state").innerHTML = "Running (single)";
	}
	
  	document.getElementById("label_current_state").classList.remove('badge-secondary');
  	document.getElementById("label_current_state").classList.add('badge-success');
  	
  	RUNNING = true;

});

//handles when Stop button is pressed 
document.getElementById("btn_stop").addEventListener("click", function(){

	//only execute if sonar is currently running
	if(RUNNING){
		STOP_INTERRUPT = true
		document.getElementById("label_current_state").innerHTML = "Stopping...";
  		document.getElementById("label_current_state").classList.remove('badge-success');
  		document.getElementById("label_current_state").classList.add('badge-danger');
	}

});


//handles when position of debug toggle is changed
$('#debug_mode_toggle').change(function() {

    var debuggerView = document.getElementById("debuggerView");
	var debuggerWaitingMsg = document.getElementById("debuggerWaitingMsg");
	
	//div containing the debug info for the first receiver 
	var debuggerOutputRec0 = document.getElementById("debuggerOutput-reciever0");
	
	//div containing the debug info for all the other receivers (excl. receiver 0)
	var debuggerOutputRemRec = document.getElementById("debuggerOutput-remainingRecievers");
	
	//div containing the debug info for all receivers combined together
	var debuggerOutputCombinedRec = document.getElementById("debuggerOutput-combinedRecievers");
	
	if (DEBUGGING_STATE === "off") {
		//if debug toggle is turned from off to on, set DEBUGGING_STATE to 'waiting' until
		//debug plots arrive - displays waiting msg. 
		DEBUGGING_STATE = "waiting"
		debuggerView.style.display = "block";
		debuggerWaitingMsg.style.display = "block";
		
		debuggerOutputRec0.style.display = "none";
		debuggerOutputRemRec.style.display = "none";
		debuggerOutputCombinedRec.style.display = "none";
		
	} else {
		DEBUGGING_STATE = "off"
		debuggerView.style.display = "none";
	}
})


/* ============================ FUNCTION DEFINITIONS ============================ */


/**
 * Loads the main plot that is displayed to user from the web server. 
 */
function loadMainplot() {

		var globaltime =  new Date();
		
		var img = document.getElementById("mainplot");

		var is1DMode = document.getElementById("display_mode_toggle").checked
		var isSimMode = document.getElementById("simulation_mode_toggle").checked
		var isDebugMode = document.getElementById('debug_mode_toggle').checked

		//a random value will be appending to URL to ensure that a new plot is retrieved 
		//and not an old cached plot
		var val = Math.random(); 
		
		var urlArguments = "sim_mode="+isSimMode+"&debug_mode="+isDebugMode+"&rand_number="+val // random number forces browser to reload image

		if(is1DMode){
			img.src="sonar_image_1D.png?" + urlArguments
		} else{
			img.src="sonar_image_2D.png?" + urlArguments 
		}

		//when the mainplot arrives from the web server
		img.onload = function() {
			
			//time between request for image being made and image arriving
    		var runtime = new Date() - globaltime
    		
    		document.getElementById("label_refresh_rate").innerHTML = runtime/1000.0 + " s";
    		document.getElementById("label_refresh_rate").classList.remove('badge-secondary');
			document.getElementById("label_refresh_rate").classList.add('badge-success');
			
			var isDebugMode = document.getElementById('debug_mode_toggle').checked
			var continuousMode = !document.getElementById("imaging_mode_toggle").checked
			
			//update label as run mode may have changed
			if(continuousMode){
				document.getElementById("label_current_state").innerHTML = "Running (cont.)";
			} else{
				document.getElementById("label_current_state").innerHTML = "Running (single)";
			}		
			
			//only load debug plots if in debug mode
			if(isDebugMode){
				loadDebugplots()
			}
    		
  			//if in continuous mode and stop has not been pressed, then keep running
  			if(continuousMode && !STOP_INTERRUPT){
  				loadMainplot();
  			} else{
  				RUNNING = false;
  				STOP_INTERRUPT = false;
  				document.getElementById("label_current_state").innerHTML = "Idle";
    			document.getElementById("label_current_state").classList.remove('badge-success');
    			document.getElementById("label_current_state").classList.remove('badge-danger');
  				document.getElementById("label_current_state").classList.add('badge-secondary');
  			}
			
		};
		
		  		
}


/**
 * Loads all intermediate plots that are displayed when in debugging mode.
 */
function loadDebugplots() {
	
	var is1DMode = document.getElementById("display_mode_toggle").checked
	var isSimMode = document.getElementById("simulation_mode_toggle").checked
	
	//a random value will be appending to URL to ensure that new plots are retrieved 
	//and not an old cached plot
	var val = Math.random(); 
		
	var debugplot_chirp = document.getElementById("debugplot_chirp");
	debugplot_chirp.src = "debug?plotname=_1_chirp.png&rand_number=" + val
	
	//load debug plots for all receivers. If in 1D mode loop only run once.
	for(var i = 0; i< NUM_RECIEVERS; i++){
		
		// stop early if in 1D mode
		if(is1DMode && i>0){
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
	
	//load combined receiver plots if in 2D and real mode.
	if(!isSimMode && !is1DMode){
		var debugplot_all_profile_mags = document.getElementById("debugplot_all_profile_mags");
		var debugplot_all_profile_phases = document.getElementById("debugplot_all_profile_phases");
		debugplot_all_profile_mags.src = "debug?plotname=all_profile_mags.png&rand_number=" + val
		debugplot_all_profile_phases.src = "debug?plotname=all_profile_phases.png&rand_number=" + val
	}
	
	
	//when the first debug plot arrives, show all plots
	document.getElementById("debugplot_chirp").onload = function() {
		var debuggerView = document.getElementById("debuggerView");
		var debuggerWaitingMsg = document.getElementById("debuggerWaitingMsg");
		
		//div containing the debug info for the first receiver 
		var debuggerOutputRec0 = document.getElementById("debuggerOutput-reciever0");
		
		//div containing the debug info for all the other receivers (excl. receiver 0)
		var debuggerOutputRemRec = document.getElementById("debuggerOutput-remainingRecievers");
		
		//div containing the debug info for all receivers combined together
		var debuggerOutputCombinedRec = document.getElementById("debuggerOutput-combinedRecievers");
	
		debuggerView.style.display = "block";
		debuggerWaitingMsg.style.display = "none";
		
		if(is1DMode){
			debuggerOutputRec0.style.display = "block";
			debuggerOutputRemRec.style.display = "none";
		}else{
			debuggerOutputRec0.style.display = "block";
			debuggerOutputRemRec.style.display = "block";
			
			//only show combined receiver plots if 2D mode and not sim
			if(isSimMode){
				debuggerOutputCombinedRec.style.display = "none";
			}else{
				debuggerOutputCombinedRec.style.display = "block";
			}
		}
		DEBUGGING_STATE = "on"
	}
}



//check micro status every 10s
var intervalMicroID = setInterval(testMicroStatus, 10000);

/**
 * Retrieves microcontroller status from web server and updates UI indicators.
 */
function testMicroStatus() {

	//dont check micro status if system is currently running
	if(!RUNNING){
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
					
				//if this request is successful - it is assumed web server must be connected
				document.getElementById("label_server_connection").innerHTML = "Connected";
    			document.getElementById("label_server_connection").classList.remove('badge-danger');
    			document.getElementById("label_server_connection").classList.add('badge-success');
		
				if(micro_connection==="Connected"){
					document.getElementById("label_micro_connection").classList.remove('badge-danger');
					document.getElementById("label_micro_connection").classList.add('badge-success');
				}else{
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
    		
    		//assume micro isnt connected either
			document.getElementById("label_micro_connection").innerHTML = "Not Connected"; 	
			document.getElementById("label_micro_connection").classList.remove('badge-success');
			document.getElementById("label_micro_connection").classList.add('badge-danger');
			document.getElementById("label_sample_rate").innerHTML = "N/A";
			document.getElementById("label_sample_rate").classList.remove('badge-success');
			document.getElementById("label_sample_rate").classList.add('badge-secondary');
			
			RUNNING = false;
			document.getElementById("label_current_state").innerHTML = "Idle";
			document.getElementById("label_current_state").classList.remove('badge-success');
			document.getElementById("label_current_state").classList.remove('badge-danger');
			document.getElementById("label_current_state").classList.add('badge-secondary');
		}
		});
	}

}

