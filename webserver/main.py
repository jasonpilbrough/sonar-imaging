""" Web server for sonar imaging

This script provides a web interface to the sonar imaging system. The following URL 
requests are handled by this script:

	* /						- returns web interface
	* /sonar_image_1D.png	- returns 1D sonar image
	* /sonar_image_2D.png	- returns 2D sonar image
	* /debug				- returns specified intermeidate debugging plot
	* /micro_status			- returns the status of microcontroller

The web server can be started from the terminal by running 'python3 main.py'

The IP of the websever can be set to localhost (127.0.0.1), or some other IP on the local
network. This is configured in __main__.
	
This script requires that the following libraries be installed within the Python 
environment you are running this script in:

	sonar_processing, teensy_interface, flask, matplotlib
	
 """


# ===================================== IMPORTS ======================================== #

# add signal processing directory to system path 
import sys
sys.path.append('../signal_processing')

# must import signal processing python script before matplotlib
import sonar_processing as sp

import teensy_interface
from teensy_interface import TeensyError

from flask import Flask, render_template, request
from flask import jsonify
from flask import send_file
from flask import Response

import io
import random
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

app = Flask(__name__)

# ================================= GLOBAL VARIABLES =================================== #

# directory containing the intermediate debugging plots
global DEBUG_DIR; DEBUG_DIR = "../signal_processing/debug/"

# filepath of image to return in case of error
global ERROR_IMAGE_FILEPATH; ERROR_IMAGE_FILEPATH = "static/images/micro_error.png"




# =============================== FUNCTION DEFINITIONS ================================= #
    
@app.route("/")
def home():
	""" Returns the web interface home.html """
	return render_template("home.html")
    

@app.route('/sonar_image_1D.png')
def sonar_image_1D_process():
	""" Returns a 1D sonar png image
	
	Additional arguments can be passed in the URL request using the following format:
		debug_mode=true/false	-	indicates if debug mode is active
		sim_mode=true/false		-	indicates if simulation mode is active
	
	for example, the URL can look as follows:
		/sonar_image_1D.png?sim_mode=false&debug_mode=false
		
	"""


	try:
		#determine if in debug mode
		debug_mode = request.args.get('debug_mode')
		if(debug_mode=="true"):
			sp.set_debug_mode(True)
		else:
			sp.set_debug_mode(False)
		
		
		#determine if in simulation mode (ie no micro)
		sim_mode = request.args.get('sim_mode')
		if(sim_mode=="true"):
			# call 1D signal processing routine - a matplotlib figure will be returned
			fig = sp.generate_1D_image_sim() 
		else:
			# call 1D signal processing routine - a matplotlib figure will be returned or 
			# an error will be raised if there is a problem with the micro  
			fig = sp.generate_1D_image() 
		
		# convert matplotlib figure into png
		output = io.BytesIO()
		FigureCanvas(fig).print_png(output)
		
		# very important to close figure as not closed by automatically
		plt.close()
	
		return Response(output.getvalue(), mimetype='image/png')
	
	except TeensyError:
		# an error will be raised if there is a problem with the micro - send placeholder
		# error image
		return send_file(ERROR_IMAGE_FILEPATH, mimetype='image/gif')



@app.route('/sonar_image_2D.png')
def sonar_image_2D_process():
	""" Returns a 2D sonar png image
	
	Additional arguments can be passed in the URL request using the following format:
		debug_mode=true/false	-	indicates if debug mode is active
		sim_mode=true/false		-	indicates if simulation mode is active
	
	for example, the URL can look as follows:
		/sonar_image_2D.png?sim_mode=false&debug_mode=false
		
	"""
	
	try:
		#determine if in debug mode
		debug_mode = request.args.get('debug_mode')
		if(debug_mode=="true"):
			sp.set_debug_mode(True)
		else:
			sp.set_debug_mode(False)
		
		#determine if in simulation mode (ie no micro)
		sim_mode = request.args.get('sim_mode')
		if(sim_mode=="true"):
			# call 2D signal processing routine - a matplotlib figure will be returned
			fig = sp.generate_2D_image_sim()
		else:
			# call 2D signal processing routine - a matplotlib figure will be returned or 
			# an error will be raised if there is a problem with the micro  
			fig = sp.generate_2D_image() 
		
		# convert matplotlib figure into png
		output = io.BytesIO()
		FigureCanvas(fig).print_png(output)
		
		# very important to close figure as not closed automatically
		plt.close()
		
		return Response(output.getvalue(), mimetype='image/png')
	
	except TeensyError:
		# an error will be raised if there is a problem with the micro - send placeholder
		# error image
		return send_file(ERROR_IMAGE_FILEPATH, mimetype='image/gif')


@app.route('/debug')
def debug_image_process():
	""" Returns specified intermeidate debugging plot
	
	The indermediate plot must be specified as follows:
		plotname=<name of plot>	
	
	The available intermediate plots are:
		x_1_chirp.png
		x_2_receive.png
		x_3_inverse_filter.png
		x_4_analytic.png
		x_5_window.png
		x_6_baseband.png
		x_7_range_comp.png
		x_8_range_profile.png
	
	where x corresponds to the receiver that the intermediate plot belongs to. The first 
	receiver is labeled 0.
	
	for example, the URL can look as follows:
		/debug/plotname=3_1_chirp.png
		
	"""
	
	# extract the name of the intermediate plot
	plotname = request.args.get('plotname')
	
	filepath = DEBUG_DIR+plotname
	
	# send the requested intermediate plot
	return send_file(filepath, mimetype='image/gif')


@app.route("/micro_status", methods=['POST'])
def micro_status_process():
	""" Return the status of microcontroller as a json object """
	if(request.method == 'POST'):
		# request teensy status from teensy interface
		reply = teensy_interface.request_status();
		
		#return json object
		return jsonify(reply)



# ====================================== MAIN ========================================== #

if __name__ == "__main__":
	
	#to run on local machine - uncomment the following line
    app.run(debug=True)
    
    # to run on local network - uncomment the following line
    #app.run(debug=True, host='196.24.184.139')
    
    
    
# ====================================== END =========================================== #
