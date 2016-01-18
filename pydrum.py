#!/usr/bin/env python2
import pygame
import time
import spidev
import RPi.GPIO as GPIO
import numpy as np

_spi = None

def init():
	global _spi
	_spi = spidev.SpiDev()  
	_spi.open(0,0)
	pygame.mixer.init(buffer=64)  # small buffer size to decrease latency

def finalize():
	if _spi:
		_spi.close()

# Read SPI data from MCP3008, Channel must be an integer 0-7
def read_adc(spi, ch):
	if ((ch > 7) or (ch < 0)):  
	   return -1  
	adc = spi.xfer2([1,(8+ch)<<4,0])  
	data = ((adc[1]&3)<<8) + adc[2]  
	return data  


class PyDrum:
	def __init__(self, spi_channel, sound_file = ""):
		self.spi_channel = spi_channel
		self.last_value = 0
		self.last_change = 0
		self.noise_level = 0.0
		self.noise_stdev = 0.0
		self.threshold = 10.0
		if sound_file:
			self.set_sound_file(sound_file)

	# detect baseline noise and get a threshold value
	def calibrate(self, duration=3):
		global _spi
		start_time = time.time()
		values = []
		while True:
			value = read_adc(_spi, self.spi_channel)
			values.append(value)
			if (time.time() - start_time) >= duration:
				break
		self.noise_mean = np.mean(values)
		self.noise_stdev = np.std(values)
		# Assume the noise has a normal distribution
		# Prob(x<Z)=99%, so we use 2.33 here
		self.threshold = self.noise_mean + self.noise_stdev * 2.33
		print "Noise level", self.noise_mean, "+/-", self.noise_stdev
		print "threshold", self.threshold

	def process_input(self):
		global _spi
		value = read_adc(_spi, self.spi_channel)
		change = value - self.last_value
		if value > self.threshold: # noises can cause low values
			# if self.spi_channel == 7:
			# 	print value, change
			# check if we are at the peak of the input wave form
			if self.last_change > 3 and change < -3:
				if self.sound:
					volume = 3 * float(value) / 1024
					volume = float(value)/100
					print "---- play ----", volume
					channel = self.sound.play()
					if channel:
						channel.set_volume(volume)
		self.last_change = change
		self.last_value = value

	def set_sound(self, sound):
		self.sound = sound

	def set_sound_file(self, sound_file):
		self.sound = pygame.mixer.Sound(sound_file)


if __name__ == "__main__":
	init()
	
	GPIO.setmode(GPIO.BOARD)
	# GPIO.setup(7, GPIO.IN, pull_up_down=GPIO.PUD_UP)

	drums = [
		PyDrum(7, "drumkits/GMkit/sn_Wet_b.ogg"),
		# PyDrum(0, "drumkits/GMkit/kick_Dry_b.ogg"),
		# PyDrum(0, "drumkits/GMkit/hhp_Dry_a.ogg"),
	]

	try:
		for drum in drums:
			drum.calibrate()

		while True:
			# btn_pressed = GPIO.input(7)
			#print btn_pressed
			for drum in drums:
				drum.process_input()
	except KeyboardInterrupt:
		pass

	finalize()
