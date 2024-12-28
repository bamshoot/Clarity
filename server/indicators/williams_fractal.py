import pandas as pd


def williams_fractal(df, period=2, candle_price_point='close'):
    """
    Calculate Williams Fractal for a given DataFrame.

    Parameters:
    df (pd.DataFrame): DataFrame with columns 'High' and 'Low' or 'Close'.
    period (int): Number of periods before and after the high/low to consider.
    candle_price_point (str): Type of data to use ('high_low' or 'close').

    Returns:
    pd.DataFrame: DataFrame with the original data and columns for upper and
    lower fractals.
    """
    df = df.copy()

    # Initialize the columns for upper and lower fractals with NaN
    df['uf'] = pd.Series([float('nan')] * len(df))
    df['lf'] = pd.Series([float('nan')] * len(df))

    # Loop through the data to identify fractals
    if candle_price_point == 'high_low':
        for i in range(period, len(df) - period):
            high_range = df['high'].iloc[i-period:i+period+1]
            low_range = df['low'].iloc[i-period:i+period+1]

            # Check for upper fractal
            if df['high'].iloc[i] == high_range.max():
                df.iloc[i, df.columns.get_loc(
                    'uf')] = df['high'].iloc[i]

            # Check for lower fractal
            if df['low'].iloc[i] == low_range.min():
                df.iloc[i, df.columns.get_loc(
                    'lf')] = df['low'].iloc[i]
    elif candle_price_point == 'close':
        for i in range(period, len(df) - period):
            close_range = df['close'].iloc[i-period:i+period+1]

            # Check for upper fractal
            if df['close'].iloc[i] == close_range.max():
                df.iloc[i, df.columns.get_loc(
                    'uf')] = df['close'].iloc[i]

            # Check for lower fractal
            if df['close'].iloc[i] == close_range.min():
                df.iloc[i, df.columns.get_loc(
                    'lf')] = df['close'].iloc[i]

    return df
