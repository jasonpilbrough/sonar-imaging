#import signal processing python script - NB this must be first for matplotlib to work
import sys
sys.path.append('../signal_processing')
import sonar_processing as sp

from flask import Flask, render_template, request
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
    

@app.route('/plot.png')
def plot_png():
    fig = sp.generate_2D_image() # call signal processing routine
    output = io.BytesIO()
    FigureCanvas(fig).print_png(output)
    return Response(output.getvalue(), mimetype='image/png')

def create_figure():
    fig = Figure()
    axis = fig.add_subplot(1, 1, 1)
    xs = range(100)
    ys = [random.randint(1, 50) for x in xs]
    axis.plot(xs, ys,linewidth=0.7, color="#2da6f7")
    return fig


if __name__ == "__main__":
    app.run(debug=True)
