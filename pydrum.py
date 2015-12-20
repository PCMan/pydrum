#!/usr/bin/env python2
import pygame
import time
import spidev
import math

# Read SPI data from MCP3008, Channel must be an integer 0-7  
def ReadADC(spi, ch):
    if ((ch > 7) or (ch < 0)):  
       return -1  
    adc = spi.xfer2([1,(8+ch)<<4,0])  
    data = ((adc[1]&3)<<8) + adc[2]  
    return data  


def detect_peak(value, changes):
	if value >= 30 and changes[0] > 0 and changes[1] < 0 and (changes[0] - changes[1]) > 10:
		print value, changes
		return True
	return False


if __name__ == "__main__":
	spi = spidev.SpiDev()  
	spi.open(0,0)

	# load drum sound
	pygame.mixer.init(buffer=64)  # small buffer size to decrease latency
	snd = pygame.mixer.Sound("./sn_Wet_b.ogg")

	last_value = 0
	# store recent 4 changes
	changes = [0] * 2
	try:
		while True:
			value = ReadADC(spi, 0)
			if value > 5:
				change = value - last_value
				if detect_peak(value, changes):
					print "play!!!!"
					volume = 2 * float(value) / 1024
					print volume
					channel = snd.play()
					if channel:
						channel.set_volume(volume)
				last_value = value
			else:
				change = 0

			changes.append(change)
			del changes[0]
	except KeyboardInterrupt:
		pass
	spi.close()
