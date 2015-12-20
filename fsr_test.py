#!/usr/bin/env python3
import time
import spidev
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
	d = []
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
			d.append((value - last_value))
			last_value = value
			print(i, value)
			i += 1
			if value <= 1:
				print("stop")
				break

	# intensity vs time
	plt.plot(x, y)
	#for i, j in zip(x, y):
	#	plt.annotate(str(j), xy=(i, j))

	# change vs time
	plt.plot(x, d)
	#for i, j in zip(x, d):
	#	plt.annotate(str(j), xy=(i, j))

	plt.show()

	'''
	try:
		while True:
			value = ReadADC(spi, 0)
			print("ADC", value, float(value)*100/1024, "%")
			time.sleep(0.1)
	except KeyboardInterrupt:
		pass
	'''
	spi.close()
