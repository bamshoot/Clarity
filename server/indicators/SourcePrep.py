import talib as ta
from .DataFoundationBuilder import DataFoundationBuilder


class SourcePrep(DataFoundationBuilder):
    def __init__(self, db_connection):
        super().__init__(db_connection)
        self.candle_price_point = None

    def get_table_from_db(self, table_name: str):
        return self.con.sql(f"SELECT * FROM {table_name} ORDER BY datetime")

    def set_candle_price_point(self, candle_price_point: str):
        self.candle_price_point = candle_price_point

    def add_columns(self):
        self.con.sql(f"""
            ALTER TABLE {self.source_table_name}
            ADD COLUMN IF NOT EXISTS lstCandlePrice DOUBLE
        """)
        self.con.sql(f"""
            ALTER TABLE {self.source_table_name}
            ADD COLUMN IF NOT EXISTS distLstCandle DOUBLE
        """)
        self.con.sql(f"""
            ALTER TABLE {self.source_table_name}
            ADD COLUMN IF NOT EXISTS idx INTEGER
        """)

    def generate_last_candle_price(self):
        if self.candle_price_point == "close":
            self.con.sql(f"""
                UPDATE {self.source_table_name}
                SET lstCandlePrice = (SELECT close FROM {self.source_table_name}
                                 ORDER BY datetime DESC LIMIT 1),
                distLstCandle = abs((SELECT close FROM {self.source_table_name}
                                 ORDER BY datetime DESC LIMIT 1) - close)
            """)
        elif self.candle_price_point == "high_low":
            self.con.sql(f"""
                UPDATE {self.source_table_name}
                SET lstCandlePrice = (SELECT (high + low) / 2
                                 FROM {self.source_table_name}
                                 ORDER BY datetime DESC LIMIT 1),
                distLstCandle = abs((SELECT (high + low) / 2
                                 FROM {self.source_table_name}
                                 ORDER BY datetime DESC LIMIT 1) -
                                 (high + low) / 2)
            """)

    def generate_index_data(self):
        self.con.sql(f"""
            CREATE TABLE {self.source_table_name}_temp AS
            SELECT *,
                   row_number() OVER (ORDER BY datetime) - 1 AS idx_temp
            FROM {self.source_table_name}
        """)
        self.con.sql(f"""
            UPDATE {self.source_table_name}
            SET idx = {self.source_table_name}_temp.idx_temp
            FROM {self.source_table_name}_temp
            WHERE {self.source_table_name}.datetime =
                {self.source_table_name}_temp.datetime
        """)
        self.drop_table(f"{self.source_table_name}_temp")

    def generate_sma(self, period: int):
        data = self.con.sql(f"SELECT * FROM {self.source_table_name}").fetchnumpy()
        sma = ta.SMA(data["close"], period)
        data[f"sma{period}"] = sma

        self.con.sql(f"""
            CREATE TABLE {self.source_table_name}_temp AS
            SELECT * FROM data
        """)

        self.con.sql(f"""
            DROP TABLE IF EXISTS {self.source_table_name}
        """)

        self.con.sql(f"""
            ALTER TABLE {self.source_table_name}_temp
            RENAME TO {self.source_table_name}
        """)

    def generate_ema(self, period: int):
        data = self.con.sql(f"SELECT * FROM {self.source_table_name}").fetchnumpy()
        ema = ta.EMA(data["close"], period)
        data[f"ema{period}"] = ema

        self.con.sql(f"""
            CREATE TABLE {self.source_table_name}_temp AS
            SELECT * FROM data
        """)

        self.con.sql(f"""
            DROP TABLE IF EXISTS {self.source_table_name}
        """)

        self.con.sql(f"""
            ALTER TABLE {self.source_table_name}_temp
            RENAME TO {self.source_table_name}
        """)

    def generate_atr(self, period: int):
        data = self.con.sql(f"SELECT * FROM {self.source_table_name}").fetchnumpy()
        atr = ta.ATR(data["high"], data["low"], data["close"], period)
        data[f"atr{period}"] = atr

        self.con.sql(f"""
            CREATE TABLE {self.source_table_name}_temp AS
            SELECT * FROM data
        """)

        self.con.sql(f"""
            DROP TABLE IF EXISTS {self.source_table_name}
        """)

        self.con.sql(f"""
            ALTER TABLE {self.source_table_name}_temp
            RENAME TO {self.source_table_name}
        """)

    def generate_rsi(self, period: int):
        data = self.con.sql(f"SELECT * FROM {self.source_table_name}").fetchnumpy()
        rsi = ta.RSI(data["close"], period)
        data[f"rsi{period}"] = rsi

        self.con.sql(f"""
            CREATE TABLE {self.source_table_name}_temp AS
            SELECT * FROM data
        """)

        self.con.sql(f"""
            DROP TABLE IF EXISTS {self.source_table_name}
        """)

        self.con.sql(f"""
            ALTER TABLE {self.source_table_name}_temp
            RENAME TO {self.source_table_name}
        """)

    def generate_macd(self, fast_period: int, slow_period: int, signal_period: int):
        data = self.con.sql(f"SELECT * FROM {self.source_table_name}").fetchnumpy()
        macd, macd_signal, macd_hist = ta.MACD(
            data["close"], fast_period, slow_period, signal_period)
        data[f"macd_{fast_period}_{slow_period}_{signal_period}"] = macd

        self.con.sql(f"""
            CREATE TABLE {self.source_table_name}_temp AS
            SELECT * FROM data
        """)

        self.con.sql(f"""
            DROP TABLE IF EXISTS {self.source_table_name}
        """)

        self.con.sql(f"""
            ALTER TABLE {self.source_table_name}_temp
            RENAME TO {self.source_table_name}
        """)
