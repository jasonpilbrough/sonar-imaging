var globaltime = new Date();

function loadDoc() {
		var time =  new Date();
		console.log(time-globaltime)
		globaltime = time
  		var xhttp = new XMLHttpRequest();
  		xhttp.onreadystatechange = function() {
    	if (this.readyState == 4 && this.status == 200) {
    		document.getElementById("mainplot").src = "plot.png";
      		//document.getElementById("demo").innerHTML = this.responseText
      		//var d2 = new Date();
      		//console.log(d2-d1)
    	}
  		};
		xhttp.open("GET", "plot.png", true);
  		xhttp.send();
  		
  		
  		
}
