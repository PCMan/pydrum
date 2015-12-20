#!/usr/bin/env python3
import time
import spidev
import sys
import matplotlib.pyplot as plt

# Read SPI data from MCP3008, Channel must be an integer 0-7  
def ReadADC(spi, ch):
    if ((ch > 7) or (ch < 0)):  
       return -1  
    adc = spi.xfer2([1,(8+ch)<<4,0])  
    data = ((adc[1]&3)<<8) + adc[2]  
    return data  
  
# Convert data to voltage level  
def ReadVolts(spi, data,deci):
    volts = (data * 5.0) / float(1023)  
    volts = round(volts,deci)  
    return volts


if __name__ == "__main__":
	spi = spidev.SpiDev()  
	spi.open(0,0)

	print("start")
	x = []
	y = []
	changes = []
	i = 0
	record = False
	last_value = 0
	while True:
		value = ReadADC(spi, 0)
		if value > 2:
			record = True
		if record:
			x.append(i)
			y.append(value)
			changes.append((value - last_value))
			last_value = value
			print(i, value)
			i += 1
			if value <= 1:
				print("stop")
				break

	annote_interval = int(len(x) / 15)
	if annote_interval == 0:
		annote_interval = 1

	# intensity vs time
	plt.plot(x, y)
	for i, j in zip(x, y):
		if i % annote_interval == 0:
			plt.annotate(str(j), xy=(i, j))

	# change vs time
	plt.plot(x, changes)
	for i, j in zip(x, changes):
		if i % annote_interval == 0:
			plt.annotate(str(j), xy=(i, j))

	if len(sys.argv) > 1:
		filename = sys.argv[1]
		plt.savefig(filename)
	else:
		plt.show()

	spi.close()
