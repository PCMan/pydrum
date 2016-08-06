#!/usr/bin/env python3
import pygame
import time
import spidev
# import RPi.GPIO as GPIO
import numpy as np
import configparser
import os


SAMPLING_RATE = 250  # sampling rate in Hz
DEFAULT_THRESHOLD = 30
DEFAULT_MIN_INTERVAL = 0.075

# Read SPI data from MCP3008, Channel must be an integer 0-7
def read_adc(spi, ch):
    if ((ch > 7) or (ch < 0)):  
       return -1  
    adc = spi.xfer2([1,(8+ch)<<4,0])  
    data = ((adc[1]&3)<<8) + adc[2]  
    return data


class PyDrum:
    def __init__(self, config_file):
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
        self.load_config(config_file)

    def finalize(self):
        if self.spi:
            self.spi.close()

    def load_config(self, config_file):
        config = configparser.ConfigParser()
        config.read(config_file)
        for name in ("crash", "tom1", "ride", "hihat", "snare", "floor_tom", "base_drum"):
            if name not in config:
                continue
            section = config[name]
            channel = section.getint("channel", fallback=-1)
            sound = section.get("sound", None)
            threshold = section.getfloat("threshold", fallback=DEFAULT_THRESHOLD)
            min_interval = section.getfloat("min_interval", fallback=DEFAULT_MIN_INTERVAL)
            amplify = section.getfloat("amplify", fallback=1.0)
            if name == "hihat": # special handling for hihat
                pedal_channel = section.getint("pedal_channel", fallback=-1)
                if pedal_channel == -1:
                    continue
                open_sound=section.get("open_sound", None)
                close_sound=section.get("close_sound", None)
                pedal_close_threshold = section.getfloat("pedal_close_threshold", fallback=800.0)
                hihat_pedal=Pedal(pedal_channel, close_threshold=pedal_close_threshold)
                self.add_instrument(hihat_pedal)
                instrument = Hihat(channel, pedal=hihat_pedal, sound_files=[close_sound, open_sound], amplify=amplify)
            else:
                instrument = Instrument(channel, sound_file=sound, threshold=threshold, min_interval=min_interval, amplify=amplify)
            self.add_instrument(instrument)

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


class Instrument:
    def __init__(self, spi_channel, sound_file = "", threshold=DEFAULT_THRESHOLD, min_interval=DEFAULT_MIN_INTERVAL, amplify=1.0):
        self.spi_channel = spi_channel
        self.last_value = 0
        self.last_change = 0
        self.noise_level = 0.0
        self.noise_stdev = 0.0
        self.threshold = threshold
        self.min_interval = min_interval # minimum interval between beats
        self.amplify = amplify
        self.pydrum = None
        self.last_time = 0.0
        if sound_file:
            self.set_sound_file(sound_file)

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
    def __init__(self, spi_channel, pedal=None, sound_files = None, threshold=DEFAULT_THRESHOLD, min_interval=DEFAULT_MIN_INTERVAL, amplify=1.0):
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
    # GPIO.setmode(GPIO.BOARD)
    config_file = os.path.join(os.path.dirname(__file__), "pydrum.conf")
    pydrum = PyDrum(config_file=config_file)
    try:
        pydrum.main_loop()
    except KeyboardInterrupt:
        pass
    pydrum.finalize()
