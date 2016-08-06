#!/usr/bin/env python3
import time
import spidev
import sys
from array import array

# Read SPI data from MCP3008, Channel must be an integer 0-7  
def ReadADC(spi, ch):
    if ((ch > 7) or (ch < 0)):  
       return -1  
    adc = spi.xfer2([1,(8+ch)<<4,0])  
    data = ((adc[1]&3)<<8) + adc[2]  
    return data  

def main():
    if len(sys.argv) > 3:
        sampling_rate = int(sys.argv[3])
    else:
        sampling_rate = 100
    sampling_period = 1.0 / sampling_rate

    spi = spidev.SpiDev()  
    spi.open(0,0)

    channel = 0
    if len(sys.argv) > 1:
        channel = int(sys.argv[1])
    print("start")
    x = array('d')
    y = array('i')
    wait_adjust = 0.0
    next_read_time = start_time = time.time()
    while True:
        read_time = time.time()
        value = ReadADC(spi, channel)
        elapsed = read_time - start_time
        if elapsed > 5.0:
            break
        x.append(elapsed)
        y.append(value)
        print("%.4f" % elapsed, value)
        wait_adjust =  next_read_time - read_time  # adjust for the difference from expected time
        next_read_time = read_time + sampling_period + wait_adjust
        wait_time = next_read_time - time.time()
        if wait_time > 0:
            time.sleep(wait_time)

    print("average sampling rate:", len(y) / elapsed)
    if len(sys.argv) > 2:
        filename = sys.argv[2]
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

if __name__ == "__main__":
    main()
