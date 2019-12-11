#import signal processing python script - NB this must be first for matplotlib to work
import sys
sys.path.append('../signal_processing')
import sonar_processing as sp
import teensy_interface
from teensy_interface import FormatError

from flask import Flask, render_template, request
from flask import jsonify
from flask import send_file

import io
import random
from flask import Response
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure


app = Flask(__name__)

    
@app.route("/")
def home():
    return render_template("home.html")
    

@app.route("/about")
def about():
	return render_template("about.html")
      
    
@app.route("/refresh")
def refresh():
	return render_template("home.html")
    

@app.route('/sonar_image_2D.png')
def sonar_image_2D_process():

	try:
		#determine if in simulation mode (ie no micro)
		sim_mode = request.args.get('sim_mode')
	
		if(sim_mode=="true"):
			fig = sp.generate_2D_image_sim() # call 2D signal processing routine
		else:
			# will raise format error if micro not connected
			fig = sp.generate_2D_image() # call 2D signal processing routine
	
		output = io.BytesIO()
		FigureCanvas(fig).print_png(output)
		return Response(output.getvalue(), mimetype='image/png')
	
	except FormatError:
		return send_file("static/images/micro_error.png", mimetype='image/gif')

@app.route('/sonar_image_1D.png')
def sonar_image_1D_process():
	
	try:
		#determine if in simulation mode (ie no micro)
		sim_mode = request.args.get('sim_mode')
	
		if(sim_mode=="true"):
			fig = sp.generate_1D_image_sim() # call 1D signal processing routine
		else:
			# will raise format error if micro not connected
			fig = sp.generate_1D_image() # call 1D signal processing routine
	
		output = io.BytesIO()
		FigureCanvas(fig).print_png(output)
	
		return Response(output.getvalue(), mimetype='image/png')
	
	except FormatError:
		return send_file("static/images/micro_error.png", mimetype='image/gif')


@app.route("/micro_status", methods=['POST'])
def micro_status_process():
	if request.method == 'POST':
		reply = teensy_interface.request_info_data();
		return jsonify(reply)

if __name__ == "__main__":
    #app.run(debug=True)
    app.run(host='0.0.0.0')
