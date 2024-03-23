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

import threading

import pigpio
from time import sleep

app = Flask(__name__)
api = Api(app)

logger = logging.getLogger('APA102')
class APA102():
    def __init__(self, NUM_LEDS = 150, rainbow = False, contrast_level = 128):

        # Number of LED's in your APA102 LED Strip.
        self.NUM_LEDS = NUM_LEDS

        # Color buffer "array", initialised to all black.
        # The color values in this buffer are applied to the APA102 LED Strip
        # by the update() function. The value at position 0 = the LED first LED
        # in the strip.
        self.color_buffer = deque(['black']*NUM_LEDS, maxlen=NUM_LEDS)

        # Initialise serial using Hardware SPI0 (SCLK=BCM 11, MOSI/SDA=BCM 10).
        # Default bus_speed_hz=8000000. This value may need to be lowered
        # if your Logic Level Converter cannot switch fast enough.
        # Allowed values are 500000, 1000000, 2000000, 4000000, 8000000, 16000000, 32000000
        # For find the spi class at https://github.com/rm-hull/luma.core/blob/master/luma/core/interface/serial.py
        self.serial = spi(port=0, device=0, bus_speed_hz=2000000)

        # Initialise serial using "Big Banging" SPI technique on general GPIO Pins.
        # For find the bitbang class at https://github.com/rm-hull/luma.core/blob/master/luma/core/interface/serial.py
        # serial = bitbang(SCLK=13, SDA=6)

        #Initialise APA102 device instance using serial instance created above.
        self.device = apa102(serial_interface=self.serial, cascaded=NUM_LEDS)

        # Reset device and set it's global contrast level.
        self.device.clear()

        self.device.contrast(contrast_level)   # 0 (off) to 255 (maximum brightness)

        self.rainbow = rainbow


    def set_contrast(self, contrast):
        self.device.contrast(contrast)


    def set_color(self, color='black', index=-1):                                                # (8)
        """
        Set the color of single LED (index >= 0), or all LEDs (when index == -1)
        """
        if index == -1:
            self.color_buffer = deque([color]*self.NUM_LEDS, maxlen=self.NUM_LEDS)
        else:
            self.color_buffer[index] = color

    def update(self):                                                            
        """
        Apply the color buffer to the APA102 strip.
        """
        with canvas(self.device) as draw:
            for led_pos in range(0, len(self.color_buffer)):
                color = self.color_buffer[led_pos]

                ## If your LED strip's colors are are not in the expected
                ## order, uncomment the following lines and adjust the indexes
                ## in the line color = (rgb[0], rgb[1], rgb[2])
                # rgb = getrgb(color)
                # color = (rgb[0], rgb[1], rgb[2])
                # if len(rgb) == 4:
                #     color += (rgb[3],)  # Add in Alpha

                draw.point((led_pos, 0), fill=color)


    def push_color(self, color):                                                                  # (9)
        """
        Push a new color into the color array at index 0. The last value is dropped.
        """
        self.color_buffer.appendleft(color)





class APA102Control(Resource):
    PRESSED  = "PRESSED"
    RELEASED = "RELEASED"
    HOLD     = "HOLD"
    def __init__(self, apa, gpio, pi, amplitude_file, max_amplitude, hold_secs=0.5, delay_secs=0.25, callback=None, color = 'red'):
        """ Constructor """

        self.args_parser = reqparse.RequestParser()

        self.args_parser.add_argument(
            name = "Rainbow",
            required = True,
            type = inputs.boolean(),
            help = 'make rainbow effect {error_msg}',
            default=False)
        
        self.gpio = gpio
        self.pi = pi
        self.hold_secs = hold_secs
        self.callback = callback

        self.rainbow = False
        
        self.color = color
        # Setup Button GPIO as INPUT and enable internal Pull-Up Resistor.
        # Our button is therefore Active LOW.
        self.pi.set_mode(gpio, pigpio.INPUT)
        self.pi.set_pull_up_down(gpio, pigpio.PUD_UP)
        self.pi.set_glitch_filter(gpio, 10000) # microseconds debounce

        self._hold_timer = 0  # For detecting hold events.
        self.pressed = False  # True when button pressed, false when released.
        self.hold = False     # Hold has been detected.

        # Register internal PiGPIO callback (as an alternative to polling the button in a while loop)
        self._pigpio_callback = self.pi.callback(self.gpio, pigpio.EITHER_EDGE, self.rainbow_toggel)

        self.amplitude_file = amplitude_file
        self.max_amplitude = max_amplitude


        self.apa = apa
        APA102.set_color(self.apa, color=self.color)
        APA102.update(self.apa)


        self.is_polling = False
        self.delay_secs = delay_secs

        self._thread = None
        self._start() # Start polling ADC


    def rainbow_toggel(self):
        self.rainbow = not self.rainbow
        logger.info("rainbow is set to {}".format(self.rainbow))
        self.rainbow_lights()

    def get_rainbow(self):
        # return true if rainbow is activated
        return self.rainbow
    
    def rainbow_lights(self, delay_secs=0.01):
        """
        Rainbow sequence animation example.
        """
        APA102.set_color(self.apa, 'black') # Start with all LED's "off"
        APA102.update(self.apa)

        saturation = 100 # 0 (grayer) to 100 (full color)
        brightness = 100 # 0 (darker) to 100 (brighter)

        while(self.rainbow):
            for hue in tuple(range(0, 360)) + tuple(range(360, -1, -1)): # 0..360..0
                color_str = "hsb({}, {}%, {}%)".format(hue, saturation, brightness)
                APA102.set_color(self.apa, color_str)
                APA102.update(self.apa)
                sleep(delay_secs)

    def post(self):
        args = self.args_parser.parse_args()

        self.rainbow = args.Rainbow


    def __str__(self):
        """ To String """
        return "Rainbow value is {}".format(self.rainbow)


    def run(self):
        """ Poll ADC for Voltage Changes """
        while self.is_polling:                                                           # (1)
            with open(self.amplitude_file, 'r') as f:
                amplitudes = f.readlines()
                for amplitude in amplitudes:
                    APA102.set_contrast((float(amplitude)/self.max_amplitude) * 255)
                    sleep(self.delay_secs)
            

        # self.is_polling has become False and the Thread ends.
        self._thread = None
        logger.debug("Potentiometer Polling Thread Finished.")


    def _start(self):
        """ Start Polling ADC """

        if self._thread is not None:
            # Thread already exists.
            logger.warn("Polling Thread Already Started.")
            return

        self._thread = threading.Thread(name='Potentiometer',
                                        target=self.run,
                                        daemon=True)

        self.is_polling = True
        self._thread.start()
        logger.debug("Potentiometer Polling Thread Started.")

# Register Flask-RESTful resource and mount to server end point /led
api.add_resource(APA102Control, '/APA102')


# @app.route applies to the core Flask instance (app).
# Here we are serving a simple web page.
@app.route('/', methods=['GET'])                                                
def index():
    """Make sure inde.html is in the templates folder
    relative to this Python file."""
    return render_template('index_api_client.html')
