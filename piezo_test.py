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
	start_time = time.time()
	while True:
		current_time = time.time()
		elapsed = current_time - start_time
		value = ReadADC(spi, 7)
		x.append(elapsed)
		y.append(value)
		if elapsed > 15.0:
			break
		print("%.4f" % elapsed, value)
		delta = time.time() - current_time
		#if delta < 0.001:
		#	time.sleep(0.001 - delta)

	annote_interval = int(len(x) / 10)
	if annote_interval == 0:
		annote_interval = 1

	# intensity vs time
	plt.plot(x, y)
	'''
	for i, j in zip(x, y):
		if i % annote_interval == 0:
			plt.annotate(str(j), xy=(i, j))
	'''

	if len(sys.argv) > 1:
		filename = sys.argv[1]
		plt.savefig(filename + ".png")
		
		with open(filename + ".csv", "w") as f:
			f.write('"time","intensity","change"\n')
			for row in zip(x, y, changes):
				f.write("%d,%d,%d\n" % row)
	else:
		plt.show()

	spi.close()
