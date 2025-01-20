import talib as ta

from .DataFoundationBuilder import DataFoundationBuilder


class MACDPriceCD(DataFoundationBuilder):
    def __init__(self, db_connection):
        super().__init__(db_connection)

    def reset_macd_convergence_divergence_table(self):
        self.drop_table(self.working_table_name)
        self._create_macd_convergence_divergence_table()

    def _create_macd_convergence_divergence_table(self):
        self.con.sql(f"""
            CREATE TABLE {self.working_table_name}
            (
                instrument_name VARCHAR,
                timeframe VARCHAR,
                macd_price_cd DOUBLE,
                status VARCHAR
            )
        """)

    def generate_macd_convergence_divergence(self):
        data = self.get_table_from_db(self.source_table_name).fetchnumpy()

        slope_length = 5

        close = data["close"]
        smoothed_close = ta.EMA(close, 20)
        macd, macd_signal, macd_hist = ta.MACD(close, 12, 26, 9)

        atr = ta.ATR(data["high"], data["low"], data["close"], 14)
        slope_close = (ta.LINEARREG_SLOPE(smoothed_close, slope_length)[-1]/atr[-1])*100
        slope_macd = (ta.LINEARREG_SLOPE(macd, slope_length)[-1]/atr[-1])*100

        macd_price_cd = slope_close - slope_macd

        if macd_price_cd > 5:
            status = "bullish divergence"
        elif macd_price_cd < -5:
            status = "bearish divergence"
        else:
            status = "convergence"

        self.con.sql(f"""
            INSERT INTO {self.working_table_name}
                (instrument_name, timeframe, macd_price_cd, status)
            VALUES ('{self.instrument_name}',
                    '{self.timeframe}',
                     {macd_price_cd},
                    '{status}')
        """)
