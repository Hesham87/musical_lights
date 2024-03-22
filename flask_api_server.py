import logging
from flask import Flask, request, render_template
from flask_restful import Api, reqparse, inputs, Resource

from math import ceil
from time import sleep
from collections import deque                                                           # (1)
from PIL.ImageColor import getrgb
from luma.core.render import canvas
from luma.led_matrix.device import apa102
from luma.core.interface.serial import spi, bitbang


app = Flask(__name__)
api = Api(app)

# Number of LED's in your APA102 LED Strip.
NUM_LEDS = 150

# Color buffer "array", initialised to all black.
# The color values in this buffer are applied to the APA102 LED Strip
# by the update() function. The value at position 0 = the LED first LED
# in the strip.
color_buffer = deque(['black']*NUM_LEDS, maxlen=NUM_LEDS)

# Initialise serial using Hardware SPI0 (SCLK=BCM 11, MOSI/SDA=BCM 10).
# Default bus_speed_hz=8000000. This value may need to be lowered
# if your Logic Level Converter cannot switch fast enough.
# Allowed values are 500000, 1000000, 2000000, 4000000, 8000000, 16000000, 32000000
# For find the spi class at https://github.com/rm-hull/luma.core/blob/master/luma/core/interface/serial.py
serial = spi(port=0, device=0, bus_speed_hz=2000000)

# Initialise serial using "Big Banging" SPI technique on general GPIO Pins.
# For find the bitbang class at https://github.com/rm-hull/luma.core/blob/master/luma/core/interface/serial.py
# serial = bitbang(SCLK=13, SDA=6)

#Initialise APA102 device instance using serial instance created above.
device = apa102(serial_interface=serial, cascaded=NUM_LEDS)

# Reset device and set it's global contrast level.
device.clear()
contrast_level = 128 # 0 (off) to 255 (maximum brightness)
device.contrast(contrast_level)

rainbow = False


def set_color(color='black', index=-1):                                                # (8)
    """
    Set the color of single LED (index >= 0), or all LEDs (when index == -1)
    """
    if index == -1:
        global color_buffer
        color_buffer = deque([color]*NUM_LEDS, maxlen=NUM_LEDS)
    else:
        color_buffer[index] = color


def update():                                                                           # (12)
    """
    Apply the color buffer to the APA102 strip.
    """
    with canvas(device) as draw:
        for led_pos in range(0, len(color_buffer)):
            color = color_buffer[led_pos]

            ## If your LED strip's colors are are not in the expected
            ## order, uncomment the following lines and adjust the indexes
            ## in the line color = (rgb[0], rgb[1], rgb[2])
            # rgb = getrgb(color)
            # color = (rgb[0], rgb[1], rgb[2])
            # if len(rgb) == 4:
            #     color += (rgb[3],)  # Add in Alpha

            draw.point((led_pos, 0), fill=color)


def push_color(color):                                                                  # (9)
    """
    Push a new color into the color array at index 0. The last value is dropped.
    """
    color_buffer.appendleft(color)


def rainbow_example(rounds=1, delay_secs=0.01):
    """
    Rainbow sequence animation example.
    """
    set_color('black') # Start with all LED's "off"
    update()

    saturation = 100 # 0 (grayer) to 100 (full color)
    brightness = 100 # 0 (darker) to 100 (brighter)

    for i in range(0, rounds):
        for hue in tuple(range(0, 360)) + tuple(range(360, -1, -1)): # 0..360..0
            color_str = "hsb({}, {}%, {}%)".format(hue, saturation, brightness)
            push_color(color_str)
            update()
            sleep(delay_secs)


# @app.route applies to the core Flask instance (app).
# Here we are serving a simple web page.
@app.route('/', methods=['GET'])                                                
def index():
    """Make sure inde.html is in the templates folder
    relative to this Python file."""
    return render_template('index_api_client.html')


# Flask-restful resource definitions.
# A 'resource' is modeled as a Python Class.
class LEDControl(Resource):                
    def __init__(self):
        self.args_parser = reqparse.RequestParser()                                  # (11)

        self.args_parser.add_argument(
            name = "Rainbow",
            required = True,
            type = inputs.boolean(),
            help = 'make rainbow effect {error_msg}',
            default=False)
        
    def get(self):
        global rainbow
        # return true if rainbow is activated
        return rainbow
    
    def post(self):
        global rainbow

        args = self.args_parser.parse_args()

        rainbow = args.Rainbow



# Register Flask-RESTful resource and mount to server end point /led
api.add_resource(LEDControl, '/rainbow')
