import pandas as pd
import numpy as np

# FFT of residual(raw - exponential smoothing)
def main(datastream):

    # self-defined value
    alpha = 0.03
    A, B = 6, 2  # Fast Fourier transform (FFT) Window size: (2^A) and Shift size: (2^B)
    dB = True

    value_col = "value"
    df = datastream
    len_df = len(df.index)


    exp_smooth = [] # empty list for the exponential smoothing algorithm
    exp_smooth.append(df[value_col].loc[0]) # first index value

    for i in range(1,range(len_df)):
        x_t = df[value_col].loc[i]
        predict = str(alpha * float(x_t) + (1 - alpha) *float(exp_smooth[i-1]))
        exp_smooth.append(predict)
    
    residual = [float(x) - float(y) for x, y in zip(df[value_col], exp_smooth)]

    window_size = 2**A
    step_size = 2**B

    # Calculate the number of windows
    n_windows = int((len(residual) - window_size) / step_size) + 1
    
    # Create an empty list to store the squared sums
    fft_results = []
    # Loop through each window

    for i in range(n_windows):
        # Extract the current window from the signal
        window = residual[i*step_size:i*step_size+window_size]
        
        # Apply FFT to the window
        fft = np.fft.fft(window)
        
        # Extract the positive frequencies
        positive_freqs = fft[:window_size//2]
        
        # Take the absolute values
        abs_values = np.abs(positive_freqs)

        # Calculate the squared sum
        squared_sums = np.sum(abs_values)**2

        # covert to dB
        if dB == True:
            squared_sums = 10*np.log10(squared_sums)
        
        fft_results.append(squared_sums)

    # Claculate Timestamps
    timestamps = [df.index[i] for i in range(len(df.index)) if i % step_size == 0]
    timestamps = timestamps[:len(fft_results)]

    result_df = pd.DataFrame(fft_results, columns=["value"], index=timestamps)

    return result_df