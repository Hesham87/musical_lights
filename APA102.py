
from math import ceil
from time import sleep
from collections import deque                                                 
from PIL.ImageColor import getrgb
from luma.core.render import canvas
from luma.led_matrix.device import apa102
from luma.core.interface.serial import spi, bitbang

import logging

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

        self.color = 'black'

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

        # The state of rainbow
        self.rainbow = False

        # Reset device and set it's global contrast level.
        self.device.clear()

        self.device.contrast(contrast_level)   # 0 (off) to 255 (maximum brightness)

        self.rainbow = rainbow


    def set_contrast(self, level):
        """
        Set global LED contrast between 0 (off) to 255 (maximum)
        """

        if level < 0:
            level = 0
        elif level > 255:
            level = 255

        self.device.contrast(level)
    

    def set_rainbow(self, rainbow):
        self.rainbow = rainbow
        logger.info("rainbow is set to {}".format(self.rainbow))

    def get_rainbow(self):
        return self.rainbow

    def is_valid_color(self, color):
        """
        Test if param color is a valid color that is compatible with Pillow getrgb()
        Valid colors include names like red, blue, green that are recognised by getrgb(),
        and hex values like #44FC313.
        For full details on supported color formats, see
        https://pillow.readthedocs.io/en/latest/reference/ImageColor.html#module-PIL.ImageColor
        """

        try:
            getrgb(color)
            return color
        except ValueError:
            return False
        
    
    def set_color(self, color='black', index=-1):                                                # (8)
        """
        Set the color of single LED (index >= 0), or all LEDs (when index == -1)
        """

        if not self.is_valid_color(color):
            logger.info("Ignoring unrecognised color {}".format(color))
            return False
        
        self.color = color

        if index == -1:
            self.color_buffer = deque([color]*self.NUM_LEDS, maxlen=self.NUM_LEDS)
        else:
            self.color_buffer[index] = color
    
    def get_color(self):
        return self.color

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