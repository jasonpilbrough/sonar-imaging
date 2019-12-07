var globaltime = new Date();

function loadDoc() {

		var time =  new Date();
		console.log(time-globaltime)
		globaltime = time
		
		val = Math.random(); 
		img = document.getElementById("mainplot");
		img.src="plot.png?rand_number=" + val// random number forces browser to reload image
		
		/* TODO FIX 
		img = document.getElementById("mainplot_zoom"); //zoomed in version
		img.src="plot.png?rand_number=" + val; // same rand number = same image as above
		*/
		
		
		
		/*
		var time =  new Date();
		console.log(time-globaltime)
		globaltime = time
  		var xhttp = new XMLHttpRequest();
  		xhttp.onreadystatechange = function() {
    	if (this.readyState == 4 && this.status == 200) {
    		var blob = this.response;
    		//console.log(blob)
    		document.getElementById("mainplot").src = "plot.png";
      		//document.getElementById("mainplot") = blob
      		//var d2 = new Date();
      		//console.log(d2-d1)
    	}
  		};
		xhttp.open("GET", "plot.png", true);
  		xhttp.send();
  		*/
  		
  		
  		
}
