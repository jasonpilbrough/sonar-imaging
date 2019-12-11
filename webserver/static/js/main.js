var globaltime = new Date();
var continuousMode = false;
var running = false;
var stopInterrupt = false;
var isMicroConnected = false;


//runs once page has loaded - to ensure some UI indicators update straight away
document.addEventListener("DOMContentLoaded", function(){
    testInternetConnection()
    testMicroStatus()
});


function loadMainplot() {

		globaltime =  new Date();
		
		val = Math.random(); 
		img = document.getElementById("mainplot");
		
		var displayRadios = document.getElementsByName("radio_display_mode");
		var is_1D_mode = displayRadios[0].checked //true if continuous mode at radios[1] is selected
		
		var isSimMode = document.getElementById('chk_sim_mode').checked
	
		if(is_1D_mode && isSimMode){
			img.src="sonar_image_1D.png?sim_mode=true&rand_number=" + val // random number forces browser to reload image
		} else if(is_1D_mode && !isSimMode){
			img.src="sonar_image_1D.png?sim_mode=false&rand_number=" + val // random number forces browser to reload image
		} else if(!is_1D_mode && isSimMode){
			img.src="sonar_image_2D.png?sim_mode=true&rand_number=" + val // random number forces browser to reload image
		}else{
			img.src="sonar_image_2D.png?sim_mode=false&rand_number=" + val // random number forces browser to reload image
		}

		
		var mainplot_image = document.getElementById("mainplot");
		
		//when the mainplot loads
		mainplot_image.onload = function() {
    		var runtime = new Date() - globaltime
    		document.getElementById("label_refresh_rate").innerHTML = runtime/1000.0 + " s";
    		document.getElementById("label_refresh_rate").classList.remove('badge-secondary');
			document.getElementById("label_refresh_rate").classList.add('badge-info');
    		
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

//when Run button is pressed 
document.getElementById("btn_run").addEventListener("click", function(){

	loadMainplot();
	
	var radios = document.getElementsByName("radio_imaging_mode");
	continuousMode = radios[1].checked //true if continuous mode at radios[1] is selected
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
					document.getElementById("label_sample_rate").classList.remove('badge-info');
    				document.getElementById("label_sample_rate").classList.add('badge-secondary');
				} else{
					document.getElementById("label_sample_rate").classList.remove('badge-secondary');
    				document.getElementById("label_sample_rate").classList.add('badge-info');
				}
			
			
			}	
		});
	}
}












