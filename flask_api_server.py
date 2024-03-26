import logging
from flask import Flask, request, render_template
from flask_restful import Api, reqparse, inputs, Resource
from time import sleep

from APA102 import APA102

from pydub import AudioSegment
import numpy as np

import threading

import pigpio
from time import sleep

logger = logging.getLogger('APA102_api_server')

apa102 = None # APA102 HAL Instance

delay_secs=0.5 

color = 'red'

def set_apa102(apa102_instance):
    """
    Set APA102 HAL Instance.
    """

    global apa102

    apa102 = apa102_instance





class LightsControl(Resource):
    def __init__(self):
        """ Constructor """
        global delay_secs
        global color

        self.args_parser = reqparse.RequestParser()

        self.args_parser.add_argument(
            name = "rainbow",
            required = True,
            type = inputs.int_range(low=0, high=1),
            help = 'make rainbow effect {error_msg}',
            default=False)
        
        self.args_parser.add_argument(
            name = "color",
            required = False,
            type = apa102.is_valid_color,
            help = 'make rainbow effect {error_msg}',
            default=False)
        
        self.color = color
        
        

        self.is_polling = False
        self.delay_secs = delay_secs

        self._thread = None


    def set_rainbow(self, rainbow):
        APA102.set_rainbow(apa102, rainbow)

    def get_rainbow(self):
        return APA102.get_rainbow(apa102)
    
    def get(self):
        # return true if rainbow is activated
        data = {"rainbow": self.rainbow, "color": self.color}
        return data
    
    

    def post(self):
        args = self.args_parser.parse_args()

        if args.color:
            self.color = args.color
            APA102.set_color(apa102, color=self.color)
            APA102.update(apa102)

        self.set_rainbow(args.rainbow)
        if self.get_rainbow():
            self._start() # Start polling ADC



    def __str__(self):
        """ To String """
        return "Rainbow value is {}".format(self.rainbow)


    def run(self):
        """ Poll ADC for Voltage Changes """
        while self.get_rainbow():
            APA102.set_color(apa102, 'black') # Start with all LED's "off"
            APA102.update(apa102)

            saturation = 100 # 0 (grayer) to 100 (full color)
            brightness = 100 # 0 (darker) to 100 (brighter)

            #while(self.rainbow):
            for hue in tuple(range(0, 360)) + tuple(range(360, -1, -1)): # 0..360..0
                if self.get_rainbow():
                    color_str = "hsb({}, {}%, {}%)".format(hue, saturation, brightness)
                    APA102.set_color(apa102, color_str)
                    APA102.update(apa102)
                    timer = 0
                    while self.get_rainbow() and timer < self.delay_secs:
                        timer += 0.01
                        sleep(0.01)
            

        # self.is_polling has become False and the Thread ends.
        self._thread = None
        logger.debug("APA102 Polling Thread Finished.")


    def _start(self):
        """ Start Polling ADC """

        if self._thread is not None:
            # Thread already exists.
            logger.warn("Polling Thread Already Started.")
            return

        self._thread = threading.Thread(name='flask_api_rainbow',
                                        target=self.run,
                                        daemon=True)

        self.is_polling = True
        self._thread.start()
        logger.debug("rainbow Polling Thread Started.")

class ButtonControl():


    def __init__(self, gpio, pi, hold_secs=0.5, callback=None):
        """ Constructor """
        
        self.gpio = gpio
        self.pi = pi
        self.hold_secs = hold_secs
        self.callback = callback

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

    def rainbow_toggel():
        APA102.set_rainbow(apa102, not APA102.get_rainbow(apa102))
        logger.info("Toggling rainbow state rainbow:#{}".format(APA102.get_rainbow(apa102)))


class SongControl(Resource):
    def __init__(self):
        """ Constructor """
        


        self.song = None

        self.proccessing_finished = False

        self.amplitude_file = None
        self.max_amplitude = None


        self.is_polling = False
        self.delay_secs = 0.25

        self._thread = None
        
    
    def get(self):
        # return true if rainbow is activated
        data = {'processing_finished': self.proccessing_finished}
        return data
    
    
    def song_to_amplitude_intervals(self, file, interval_duration_ms=250):
        # Load the song
        song = AudioSegment.from_mp3(file)
        
        # Split the song into chunks of 0.25 seconds
        interval_duration = interval_duration_ms  # in milliseconds
        chunks = [song[i:i+interval_duration] for i in range(0, len(song), interval_duration)]
        
        # Calculate the average amplitude for each chunk
        average_amplitudes = []
        max_amplitude = 0
        for chunk in chunks:
            # Get the raw audio data as a numpy array
            samples = np.array(chunk.get_array_of_samples())
            # Calculate the average amplitude for the chunk
            avg_amplitude = np.mean(np.abs(samples))
            average_amplitudes.append(avg_amplitude)
            if max_amplitude < avg_amplitude:
                max_amplitude = avg_amplitude
        
        return average_amplitudes, max_amplitude

    def post(self):

        audio_file = request.files['songFile']
        if audio_file:
            # Process the audio file here, for example:
            interval_duration_ms = 250
            self.average_amplitudes, self.max_amplitude = self.song_to_amplitude_intervals(audio_file, interval_duration_ms)
            self._start() # Start polling ADC
            return True
        return False


    def run(self):
        self.proccessing_finished = True
        for amplitude in self.average_amplitudes:
            APA102.set_contrast(apa102, int((float(amplitude)/self.max_amplitude) * 255))
            # APA102.set_color(apa102,APA102.get_color(apa102))
            # APA102.update(apa102)
            sleep(self.delay_secs)

        # for amplitude in self.average_amplitudes:
        #     if APA102.get_rainbow(apa102):
        #         APA102.set_contrast(apa102, int((float(amplitude)/self.max_amplitude) * 255))
        #         timer = 0
        #         while APA102.get_rainbow(apa102) and timer < self.delay_secs:
        #             timer += 0.01
        #             sleep(0.01)
            
        self.proccessing_finished = False
        # self.is_polling has become False and the Thread ends.
        self._thread = None
        logger.debug("APA102 Polling Thread Finished.")


    def _start(self):
        """ Start Polling ADC """

        if self._thread is not None:
            # Thread already exists.
            logger.warn("Polling Thread Already Started.")
            return

        self._thread = threading.Thread(name='flask_api_song',
                                        target=self.run,
                                        daemon=True)

        self.is_polling = True
        self._thread.start()
        logger.debug("Song Polling Thread Started.")
