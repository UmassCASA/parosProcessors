import pandas as pd
import numpy as np


def main(datastream):
    window_size = 64
    step_size = 8
    value_col = "value"

    epsilon = 1e-15

    df = datastream

    # calculate fs
    time_delta = df.index[1] - df.index[0]
    fs = 1 / time_delta.total_seconds()

    fft_results = []

    for i in range(0, df.shape[0] - window_size + 1, step_size):
        window_data = df[value_col].iloc[i : i + window_size]
        fft_result = np.fft.fft(window_data)
        fft_mag = np.abs(fft_result)
        fft_mag = 20 * np.log10(fft_mag + epsilon)
        fft_results.append(fft_mag[: window_size // 2])

    # Calculate Frequency Bins
    freq_bins = np.fft.fftfreq(window_size, d=1/fs)
    freq_bins = [f"{freq:.4f} Hz" for freq in freq_bins[: window_size // 2]]

    # Claculate Timestamps
    timestamps = [df.index[i] for i in range(len(df.index)) if i % step_size == 0]
    timestamps = timestamps[:len(fft_results)]

    result_df = pd.DataFrame(fft_results, columns=freq_bins, index=timestamps)

    return result_df
