#!/usr/bin/env python2
import pygame
import time
import spidev

# Read SPI data from MCP3008, Channel must be an integer 0-7  
def ReadADC(spi, ch):
    if ((ch > 7) or (ch < 0)):  
       return -1  
    adc = spi.xfer2([1,(8+ch)<<4,0])  
    data = ((adc[1]&3)<<8) + adc[2]  
    return data  
  
# Convert data to voltage level  
def ReadVolts(spi, data,deci):
    volts = (data * 3.3) / float(1023)  
    volts = round(volts,deci)  
    return volts  


if __name__ == "__main__":
	spi = spidev.SpiDev()  
	spi.open(0,0)

	# load drum sound
	pygame.mixer.init(buffer=64)  # small buffer size to decrease latency
	snd = pygame.mixer.Sound("./sn_Wet_b.ogg")

	last_value = 0
	last_change = 0
	try:
		while True:
			value = ReadADC(spi, 0)
			if value > 5:
				change = value - last_value
				print value, ", change",change
				if last_change > 0 and change < last_change and last_change > 20 and change > 0:
					print "play!!!!"
					volume = 2 * float(value) / 1024
					channel = snd.play()
					if channel:
						channel.set_volume(volume)
				last_value = value
				last_change = change
	except KeyboardInterrupt:
		pass
	spi.close()
