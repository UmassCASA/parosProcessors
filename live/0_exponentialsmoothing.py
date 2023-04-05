import pandas as pd
import numpy as np

# exponential smoothing
def main(datastream):

    value_col = "value"
    df = datastream
    len_df = len(df.index)

    alpha = 0.03

    exp_smooth = [] # empty list for the exponential smoothing algorithm
    exp_smooth.append(df[value_col].loc[0]) # first index value

    a = 0

    for i in range(1,range(len_df)):
        x_t = df[value_col].loc[i]
        predict = str(alpha * float(x_t) + (1 - alpha) *float(exp_smooth[i-1]))
        exp_smooth.append(predict)
    

    result_df = pd.DataFrame(exp_smooth, columns=["value"], index=df.index)

    return result_df