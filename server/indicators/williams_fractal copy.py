import pandas as pd


def williams_fractal(ohlc, candle_price_point, period: int = 2):
    """
    Williams Fractal Indicator
    Source: https://www.investopedia.com/terms/f/fractal.asp
    :param DataFrame ohlc: data
    :param int period: how many lower highs/higher lows the extremum value should be
        preceded and followed.
    :return DataFrame: fractals identified by boolean
    """

    def is_bullish_fractal(x):
        if x[period] == max(x):
            return True
        return False

    def is_bearish_fractal(x):
        if x[period] == min(x):
            return True
        return False

    if candle_price_point == "high_low":

        window_size = period * 2 + 1
        bearish_fractals = pd.Series(
            ohlc.low.rolling(window=window_size, center=True).apply(
                is_bearish_fractal, raw=True
            ),
            name="lf",
        )

        bullish_fractals = pd.Series(
            ohlc.high.rolling(window=window_size, center=True).apply(
                is_bullish_fractal, raw=True
            ),
            name="uf",
        )

    elif candle_price_point == "close":

        window_size = period * 2 + 1
        bearish_fractals = pd.Series(
            ohlc.close.rolling(window=window_size, center=True).apply(
                is_bearish_fractal, raw=True
            ),
            name="lf",
        )

        bullish_fractals = pd.Series(
            ohlc.close.rolling(window=window_size, center=True).apply(
                is_bullish_fractal, raw=True
            ),
            name="uf",
        )

    return pd.concat([bearish_fractals, bullish_fractals], axis=1)
