#!/usr/bin/env python3
import time
import spidev
import sys

# Read SPI data from MCP3008, Channel must be an integer 0-7  
def ReadADC(spi, ch):
    if ((ch > 7) or (ch < 0)):  
       return -1  
    adc = spi.xfer2([1,(8+ch)<<4,0])  
    data = ((adc[1]&3)<<8) + adc[2]  
    return data  

if __name__ == "__main__":
	spi = spidev.SpiDev()  
	spi.open(0,0)

	channel = 0
	if len(sys.argv) > 1:
		channel = int(sys.argv[1])
	print("start")
	x = []
	y = []
	start_time = time.time()
	while True:
		current_time = time.time()
		elapsed = current_time - start_time
		value = ReadADC(spi, channel)
		x.append(elapsed)
		y.append(value)
		if elapsed > 30.0:
			break
		print("%.4f" % elapsed, value)
		delta = time.time() - current_time
		#if delta < 0.001:
		#	time.sleep(0.001 - delta)

	if len(sys.argv) > 2:
		filename = sys.argv[2]
		#plt.savefig(filename + ".png")

		with open(filename + ".csv", "w") as f:
			f.write('"time","intensity"\n')
			for row in zip(x, y):
				f.write("%f,%d\n" % row)
	else:
		import matplotlib.pyplot as plt
		# intensity vs time
		plt.plot(x, y)
		plt.show()

	spi.close()
