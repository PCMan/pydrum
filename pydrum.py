#!/usr/bin/env python2
import pygame
import time
import spidev
import RPi.GPIO as GPIO
import numpy as np


# Read SPI data from MCP3008, Channel must be an integer 0-7
def read_adc(spi, ch):
    if ((ch > 7) or (ch < 0)):  
       return -1  
    adc = spi.xfer2([1,(8+ch)<<4,0])  
    data = ((adc[1]&3)<<8) + adc[2]  
    return data  


class PyDrum:
    def __init__(self):
        self.spi = spidev.SpiDev()
        self.spi.open(0,0)
        # set small buffer size to decrease latency
        pygame.mixer.init(buffer=64)
        self.instruments = []

    def finalize(self):
        if self.spi:
            self.spi.close()

    def add_instrument(self, instrument):
        instrument.pydrum = self
        self.instruments.append(instrument)

    def remove_instrument(self, instrument):
        self.instruments.remove(instrument)

    def process_input(self):
        for instrument in self.instruments:
            instrument.process_input()

    # detect baseline noise and get a threshold value
    def calibrate(self, duration=3):
        print("start calibration")
        spi = self.spi
        start_time = time.time()
        for instrument in self.instruments:
            instrument.start_calibration()
        while (time.time() - start_time) < duration:
            self.process_input()
        for instrument in self.instruments:
            instrument.stop_calibration()
        print("calibration finished!")


class Instrument:
    def __init__(self, spi_channel, sound_file = ""):
        self.spi_channel = spi_channel
        self.last_value = 0
        self.last_change = 0
        self.noise_level = 0.0
        self.noise_stdev = 0.0
        self.threshold = 10.0
        self.pydrum = None
        self.calibrating = False
        self.last_time = 0.0
        if sound_file:
            self.set_sound_file(sound_file)

    # detect baseline noise and get a threshold value
    def start_calibration(self):
        self.calibrating = True
        self.noise_data = []

    def stop_calibration(self):
        self.calibrating = False
        self.noise_mean = np.mean(self.noise_data)
        self.noise_stdev = np.std(self.noise_data)
        # Assume the noise has a normal distribution
        # Prob(x<Z)=99%, so we use 2.33 here
        self.threshold = self.noise_mean + self.noise_stdev * 2.33
        print "Noise level", self.noise_mean, "+/-", self.noise_stdev
        print "threshold: ", self.spi_channel, self.threshold
        del self.noise_data

    def process_input(self):
        spi = self.pydrum.spi
        value = read_adc(spi, self.spi_channel)
        if self.calibrating:
            self.noise_data.append(value)
        else:
            change = value - self.last_value
            if value > self.threshold: # noises can cause low values
                # check if we are at the peak of the input wave form
                if self.last_change > 0 and change < 0:
                    current_time = time.time()
                    # avoid playing the sound file too frequently
                    if (current_time - self.last_time) > 0.1:
                        if self.sound:
                            # FIXME: need a way to adjust the volume
                            volume = 2 * float(value) / 1024
                            channel = self.sound.play()
                            print "play:", self.spi_channel, volume
                            if channel:
                                channel.set_volume(volume)
                            self.last_time = current_time
            self.last_change = change
            self.last_value = value

    def set_sound(self, sound):
        self.sound = sound

    def set_sound_file(self, sound_file):
        self.sound = pygame.mixer.Sound(sound_file)


if __name__ == "__main__":
    GPIO.setmode(GPIO.BOARD)
    # GPIO.setup(7, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    pydrum = PyDrum()
    pydrum.add_instrument(Instrument(7, "drumkits/GMkit/sn_Wet_b.ogg"))
    # pydrum.add_instrument(PyDrum(7, "drumkits/GMkit/kick_Dry_b.ogg"))
    # pydrum.add_instrument(PyDrum(7, "drumkits/GMkit/hhp_Dry_a.ogg"))
    try:
        pydrum.calibrate(duration=5)
        while True:
            # btn_pressed = GPIO.input(7)
            pydrum.process_input()
    except KeyboardInterrupt:
        pass
    pydrum.finalize()
