## 40kHz sonar imaging in air

Design project that uses ultrasound to accurately image the surrounding environment. 
This repository contains all code that was developed for the project including: 

* **C++ for Teensy 3.6 microcontroller**: code to interface with A/D and D/A converters.

* **Python digital signal processing**: all required signal processing algorithms including digital filtering, 
pulse compression, base-banding, windowing, beam-forming via coherent summing etc.

* **HTML, CSS, and Javascript frontend**: uses the Bootstrap library.

* **Web interface served with a Flask backend**


### How to start the web server

Navigate to the webserver directory and run the following command:

#### `python3 main.py`

Open [http://localhost:5000](http://localhost:5000) in the browser to view the web interface.


