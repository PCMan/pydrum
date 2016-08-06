#!/usr/bin/env python3
import pygame
import time
import spidev
import RPi.GPIO as GPIO
import numpy as np
from scipy import signal


SAMPLING_RATE = 250  # sampling rate in Hz

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
        # estimate the max number of concurrently played sound files:
        # assume that one beat lasts for 3 second, and the max BPM we support is 400, then
        # when playing the sound for one beat, the maximum number of concurrently played sound files is roughly
        # 3 sec * (400 BPM / 60 sec) * 8 channels = 160
        pygame.mixer.set_num_channels(160)  # we need to play numerous sound files concurrently so increase # of channels.
        self.instruments = []
        self.begin_time = time.time()

    def finalize(self):
        if self.spi:
            self.spi.close()

    def add_instrument(self, instrument):
        instrument.pydrum = self
        self.instruments.append(instrument)

    def remove_instrument(self, instrument):
        self.instruments.remove(instrument)

    def main_loop(self):
        sampling_period = 1.0 / SAMPLING_RATE
        wait_adjust = 0.0
        next_read_time = time.time()
        while True:
            read_time = time.time()
            for instrument in self.instruments:
                instrument.process_input()
            wait_adjust =  next_read_time - read_time  # adjust for the difference from expected time
            next_read_time = read_time + sampling_period + wait_adjust
            wait_time = next_read_time - time.time()
            if wait_time > 0:
                time.sleep(wait_time)


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
        print(self.spi_channel, "Noise level", self.noise_mean, "+/-", self.noise_stdev, ", max:", self.max_noise)
        print("threshold: ", self.spi_channel, self.threshold)
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
                    print("play:", self.spi_channel, volume, value)
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

    pydrum = PyDrum()
    pydrum.add_instrument(Instrument(1, "drumkits/GMkit/cra_Rock_a.ogg", amplify=3.0))
    pydrum.add_instrument(Instrument(2, "drumkits/GMkit/tom_Rock_hi.ogg", amplify=2.0))
    pydrum.add_instrument(Instrument(3, "drumkits/GMkit/cym_Rock_b.ogg", amplify=1.0))
    hihat_pedal=Pedal(0, close_threshold=800.0)
    pydrum.add_instrument(hihat_pedal)
    hihat = Hihat(4, pedal=hihat_pedal, sound_files=["drumkits/GMkit/hhc_Dry_a.ogg", "drumkits/UltraAcousticKit/HH_1_open.ogg"], amplify=2.0)
    # hihat = Hihat(3, pedal=hihat_pedal, sound_files=["drumkits/GMkit/hhc_Dry_a.ogg", "drumkits/GMkit/hhp_Dry_a.ogg"], amplify=1.0)
    pydrum.add_instrument(hihat)
    pydrum.add_instrument(Instrument(5, "drumkits/GMkit/sn_Wet_b.ogg", amplify=1.5))
    pydrum.add_instrument(Instrument(6, "drumkits/GMkit/tom_Rock_lo.ogg", amplify=1.0))
    pydrum.add_instrument(Instrument(7, "drumkits/GMkit/kick_Dry_b.ogg", amplify=3.0, min_interval=0.1))
    try:
        # pydrum.calibrate(duration=5)
        pydrum.main_loop()
    except KeyboardInterrupt:
        pass
    pydrum.finalize()
