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
        # pygame.mixer.init(buffer=64)
        pygame.mixer.init(buffer=16)
        pygame.mixer.set_num_channels(128)  # we need to play numerous sound files concurrently so increase # of channels.
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
    def __init__(self, spi_channel, sound_file = "", threshold=100.0, min_interval=0.025, amplify=1.0):
        self.spi_channel = spi_channel
        self.last_value = 0
        self.last_change = 0
        self.noise_level = 0.0
        self.noise_stdev = 0.0
        self.threshold = threshold
        self.min_interval = min_interval # minimum interval between beats
        self.amplify = amplify
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
        self.max_noise = max(self.noise_data)
        self.noise_mean = np.mean(self.noise_data)
        self.noise_stdev = np.std(self.noise_data)
        # Assume the noise has a normal distribution
        # Prob(x<Z)=99%, so we use 2.33 here
        self.threshold = self.noise_mean + self.noise_stdev * 2.33
        print self.spi_channel, "Noise level", self.noise_mean, "+/-", self.noise_stdev, ", max:", self.max_noise
        print "threshold: ", self.spi_channel, self.threshold
        del self.noise_data

    def play(self, volume):
        current_time = time.time()
        # avoid playing the sound file too frequently
        if (current_time - self.last_time) > self.min_interval:
            if self.sound:
                channel = self.sound.play()
                self.last_time = current_time
                if channel:
                    channel.set_volume(volume)
        # else:
        #     print "delay play"

    def process_input(self):
        spi = self.pydrum.spi
        value = read_adc(spi, self.spi_channel)
        if self.calibrating:
            self.noise_data.append(value)
        else:
            change = value - self.last_value
            if value > self.threshold: # noises can cause low values
                # check if we are at the peak of the input wave form
                if self.last_change > 3 and change < -3:
                    volume = self.amplify * float(value) / 1024
                    print "play:", self.spi_channel, volume, value
                    self.play(volume)
            self.last_change = change
            self.last_value = value

    def set_sound(self, sound):
        self.sound = sound

    def set_sound_file(self, sound_file):
        self.sound = pygame.mixer.Sound(sound_file)


# pedal of instruments like hihat.
# linear hall effect sensor-based
class Pedal:
    def __init__(self, spi_channel, threshold=600.0, close_threshold=800.0):
        self.spi_channel = spi_channel
        self.closed = False
        self.threshold = threshold
        self.close_threshold = close_threshold

    def process_input(self):
        spi = self.pydrum.spi
        value = read_adc(spi, self.spi_channel)
        if value > self.threshold:  # ignore low level noise
            if value < self.close_threshold:
                self.closed = False
            else:
                self.closed = True
            # print self.closed


class Hihat(Instrument):
    def __init__(self, spi_channel, pedal=None, sound_files = None, threshold=100.0, min_interval=0.05, amplify=1.0):
        Instrument.__init__(self, spi_channel, "", threshold, min_interval, amplify)
        self.pedal = pedal
        self.set_sound_files(sound_files)

    def set_pedal(self, pedal):
        self.pedal = pedal

    def set_sounds(self, sounds):
        self.sounds = sounds

    def set_sound_files(self, sound_files):
        self.sounds = []
        for sound_file in sound_files:
            sound = pygame.mixer.Sound(sound_file)
            self.sounds.append(sound)

    def play(self, volume):
        current_time = time.time()
        # avoid playing the sound file too frequently
        if (current_time - self.last_time) > self.min_interval:
            if self.sounds:
                # get the sound to play based on the state of the pedal
                if self.pedal:
                    idx = 0 if self.pedal.closed else 1
                    sound = self.sounds[idx]
                else:
                    sound = self.sounds[0]
                channel = sound.play()
                self.last_time = current_time
                if channel:
                    channel.set_volume(volume)


if __name__ == "__main__":
    GPIO.setmode(GPIO.BOARD)
    # GPIO.setup(7, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    pydrum = PyDrum()
    pydrum.add_instrument(Instrument(0, "drumkits/GMkit/cra_Rock_a.ogg", amplify=3.0))
    pydrum.add_instrument(Instrument(1, "drumkits/GMkit/tom_Rock_hi.ogg", amplify=2.0))
    pydrum.add_instrument(Instrument(2, "drumkits/GMkit/cym_Rock_b.ogg", amplify=1.0))
    hihat_pedal=Pedal(7, close_threshold=800.0)
    pydrum.add_instrument(hihat_pedal)
    hihat = Hihat(3, pedal=hihat_pedal, sound_files=["drumkits/GMkit/hhc_Dry_a.ogg", "drumkits/UltraAcousticKit/HH_1_open.ogg"], amplify=2.0)
    # hihat = Hihat(3, pedal=hihat_pedal, sound_files=["drumkits/GMkit/hhc_Dry_a.ogg", "drumkits/GMkit/hhp_Dry_a.ogg"], amplify=1.0)
    pydrum.add_instrument(hihat)
    pydrum.add_instrument(Instrument(4, "drumkits/GMkit/sn_Wet_b.ogg", amplify=1.5))
    pydrum.add_instrument(Instrument(5, "drumkits/GMkit/tom_Rock_lo.ogg", amplify=1.0))
    pydrum.add_instrument(Instrument(6, "drumkits/GMkit/kick_Dry_b.ogg", amplify=3.0, min_interval=0.1))
    try:
        # pydrum.calibrate(duration=5)
        while True:
            # btn_pressed = GPIO.input(7)
            pydrum.process_input()
    except KeyboardInterrupt:
        pass
    pydrum.finalize()
