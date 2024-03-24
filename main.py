from pydub import AudioSegment
import numpy as np
from flask_api_server import APA102, APA102Control
import pigpio
import logging
from signal import pause

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Main")

def song_to_amplitude_intervals(audio_path, interval_duration_ms=250):
    # Load the song
    song = AudioSegment.from_mp3(audio_path)
    
    # Split the song into chunks of 0.25 seconds
    interval_duration = interval_duration_ms  # in milliseconds
    chunks = [song[i:i+interval_duration] for i in range(0, len(song), interval_duration)]
    
    # Calculate the average amplitude for each chunk
    average_amplitudes = []
    max_amplitude = 0.0
    for chunk in chunks:
        # Get the raw audio data as a numpy array
        samples = np.array(chunk.get_array_of_samples())
        # Calculate the average amplitude for the chunk
        avg_amplitude = np.mean(np.abs(samples))
        if max_amplitude < avg_amplitude:
            max_amplitude = avg_amplitude
        average_amplitudes.append(avg_amplitude)
    
    return average_amplitudes, max_amplitude

def save_amplitudes_to_file(amplitudes, output_file):
    with open(output_file, 'w') as f:
        for amplitude in amplitudes:
            f.write(f"{amplitude}\n")


BUTTON_GPIO = 21

pi = pigpio.pi()

# Example usage
if __name__ == "__main__":
    audio_path = 'test-tube-194556.mp3'
    output_file = 'amplitude_output.txt'
    amplitudes, max_amplitude = song_to_amplitude_intervals(audio_path)
    save_amplitudes_to_file(amplitudes, output_file)

    apa = APA102()

    def button_handler():
        logger.info("Button is pressed")

    musical_lights = APA102Control(apa, gpio=BUTTON_GPIO, pi=pi, amplitude_file=output_file, max_amplitude=max_amplitude, callback=button_handler)
    pause()