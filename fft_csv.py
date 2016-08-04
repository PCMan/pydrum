#!/usr/bin/env python3
import sys
import csv
import numpy as np
# import scipy.signal as signal
import matplotlib.pyplot as plt

if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(1)

    moving_average = 0
    if len(sys.argv) > 2:
        moving_average = int(sys.argv[2])

    with open(sys.argv[1], "r", newline="") as f:
        reader = csv.reader(f)
        reader.__next__()
        if moving_average > 0:
            window = [0.0] * moving_average
        x = []
        y = []
        for row in reader:
            # if 8.5 < float(row[0]) < 10.0:
            x.append(float(row[0]))
            if moving_average:
                window.pop(0)
                window.append(float(row[1]))
                y.append(sum(window) / moving_average)
            else:
                y.append(float(row[1]))

        sampling_rate = len(y) / 15.0
        half = int(np.round(len(y) / 2))
        freq = np.fft.fftfreq(len(y))[1:half] * sampling_rate
        fft = np.fft.fft(y)[1:half]
        amplitude = np.abs(fft)
        valid_freq = freq[amplitude > 0.03 * np.max(amplitude)]
        print("band:", valid_freq[0], valid_freq[-1])
        #plt.plot(freq, fft)
        plt.plot(freq, abs(fft))
        plt.show()
