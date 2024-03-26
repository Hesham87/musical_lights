from pydub import AudioSegment
import numpy as np
from flask_api_server import APA102
from flask_restful import Api
from flask import Flask, request, render_template
import pigpio
import logging
from signal import pause
import flask_api_server

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Main")

# Flask & Flask-RESTful instance variables
app = Flask(__name__, static_url_path='/static', static_folder='static')
api = Api(app) # Flask-RESTful extension wrapper

@app.route('/', methods=['GET'])
def index():
    return render_template('index_api_client.html')

apa102 = APA102()

# APA102 Flask-RESTFul Resource setup and registration.
flask_api_server.set_apa102(apa102)
api.add_resource(flask_api_server.LightsControl, "/lights")
api.add_resource(flask_api_server.SongControl, "/song")


BUTTON_GPIO = 21

pi = pigpio.pi()

button = flask_api_server.ButtonControl(gpio=BUTTON_GPIO, pi=pi)
# Example usage
if __name__ == '__main__':

    # If you have debug=True and receive the error "OSError: [Errno 8] Exec format error", then:
    # remove the execuition bit on this file from a Terminal, ie:
    # chmod -x flask_api_server.py
    #
    # Flask GitHub Issue: https://github.com/pallets/flask/issues/3189

    app.run(host="0.0.0.0", debug=True)