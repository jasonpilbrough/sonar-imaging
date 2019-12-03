function loadDoc() {
		
  		var xhttp = new XMLHttpRequest();
  		xhttp.onreadystatechange = function() {
    	if (this.readyState == 4 && this.status == 200) {
    		document.getElementById("mainplot").src = "plot.png";
      		//document.getElementById("demo").innerHTML = this.responseText
    	}
  		};
		xhttp.open("GET", "plot.png", true);
  		xhttp.send();
  		
  		
}
