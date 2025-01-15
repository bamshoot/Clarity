from .DataFoundationBuilder import DataFoundationBuilder
import talib as ta


class RSI(DataFoundationBuilder):
    def __init__(self, db_path: str):
        super().__init__(db_path)
        self.source_table_name = None
        self.pair_table_name = None
        self.currency_table_name = None
        self.currency_rsi_values = {
            'AUD': {'1h': [], 'd': [], 'w': [], 'm': []},
            'NZD': {'1h': [], 'd': [], 'w': [], 'm': []},
            'CAD': {'1h': [], 'd': [], 'w': [], 'm': []},
            'CHF': {'1h': [], 'd': [], 'w': [], 'm': []},
            'JPY': {'1h': [], 'd': [], 'w': [], 'm': []},
            'GBP': {'1h': [], 'd': [], 'w': [], 'm': []},
            'EUR': {'1h': [], 'd': [], 'w': [], 'm': []},
            'USD': {'1h': [], 'd': [], 'w': [], 'm': []}
        }
        self.currency_rsi_avg = {
            'AUD': {'1h': None, 'd': None, 'w': None, 'm': None},
            'NZD': {'1h': None, 'd': None, 'w': None, 'm': None},
            'CAD': {'1h': None, 'd': None, 'w': None, 'm': None},
            'CHF': {'1h': None, 'd': None, 'w': None, 'm': None},
            'JPY': {'1h': None, 'd': None, 'w': None, 'm': None},
            'GBP': {'1h': None, 'd': None, 'w': None, 'm': None},
            'EUR': {'1h': None, 'd': None, 'w': None, 'm': None},
            'USD': {'1h': None, 'd': None, 'w': None, 'm': None}
        }

    def set_pair_table_name(self, pair_table_name: str):
        self.pair_table_name = pair_table_name

    def set_currency_table_name(self, currency_table_name: str):
        self.currency_table_name = currency_table_name

    def reset_rsi_ranks_table(self):
        self.drop_table(self.pair_table_name)
        self.drop_table(self.currency_table_name)
        self._create_pair_rsi_ranks_table()
        self._create_currency_rsi_ranks_table()

    def set_instrument_name(self, instrument_name: str):
        self.instrument_name = instrument_name

    def set_timeframe(self, timeframe: str):
        self.timeframe = timeframe

    def _create_pair_rsi_ranks_table(self):
        self.con.sql(f"""
            CREATE TABLE {self.pair_table_name}
            (
                instrument_name VARCHAR,
                base_currency VARCHAR,
                quote_currency VARCHAR,
                timeframe VARCHAR,
                lst_price_datetime DATETIME,
                pair_rsi DOUBLE,
                base_rsi DOUBLE,
                quote_rsi DOUBLE,
                pair_rsi_diff DOUBLE,
                base_rsi_diff DOUBLE,
                quote_rsi_diff DOUBLE,
                pair_timeframe_rank INTEGER,
                base_timeframe_rank INTEGER,
                quote_timeframe_rank INTEGER,
                pair_status VARCHAR,
                base_status VARCHAR,
                quote_status VARCHAR
            )
        """)

    def _create_currency_rsi_ranks_table(self):
        self.con.sql(f"""
            CREATE TABLE {self.currency_table_name}
            (
                currency VARCHAR,
                timeframe VARCHAR,
                rsi DOUBLE,
                rsi_diff DOUBLE,
                rank INTEGER,
                status VARCHAR
            )
        """)

    def generate_rsi(self):
        data = self.get_table_from_db(self.source_table_name).fetchnumpy()
        rsi = ta.RSI(data["close"], 14)
        lst_price_datetime = data["datetime"][-1]

        base_currency = self.instrument_name[:3]
        quote_currency = self.instrument_name[3:]

        if base_currency in self.currency_rsi_values:
            if self.timeframe in self.currency_rsi_values[base_currency]:
                self.currency_rsi_values[base_currency][self.timeframe].append(rsi[-1])

        if quote_currency in self.currency_rsi_values:
            if self.timeframe in self.currency_rsi_values[quote_currency]:
                self.currency_rsi_values[quote_currency][self.timeframe].append(rsi[-1])

        self.con.sql(f"""
            INSERT INTO {self.pair_table_name}
            (instrument_name, base_currency, quote_currency, timeframe,
             lst_price_datetime, pair_rsi)
            VALUES
            ('{self.instrument_name}', '{base_currency}', '{quote_currency}',
             '{self.timeframe}', '{lst_price_datetime}', {rsi[-1]})
        """)

    def generate_pair_timeframe_rank(self):
        self.con.sql(f"""
            UPDATE {self.pair_table_name} t1
            SET pair_rsi_diff = (
                SELECT ABS(pair_rsi - 50)
                FROM {self.pair_table_name}
                WHERE instrument_name = t1.instrument_name
                    AND timeframe = t1.timeframe
            )
        """)

        self.con.sql(f"""
            UPDATE {self.pair_table_name} t1
            SET pair_timeframe_rank = (
                SELECT rank
                FROM (
                    SELECT
                        instrument_name,
                        timeframe,
                        DENSE_RANK() OVER (
                            PARTITION BY timeframe
                            ORDER BY pair_rsi_diff DESC
                        ) as rank
                    FROM {self.pair_table_name}
                ) rankings
                WHERE rankings.instrument_name = t1.instrument_name
                AND rankings.timeframe = t1.timeframe
            )
        """)

        self.con.sql(f"""
            UPDATE {self.pair_table_name} t1
            SET pair_status = (
                SELECT CASE
                    WHEN pair_rsi_diff >= 10 AND pair_rsi < 50 THEN 'buy'
                    WHEN pair_rsi_diff >= 10 AND pair_rsi > 50 THEN 'sell'
                    ELSE 'neutral'
                END
                FROM {self.pair_table_name}
                WHERE instrument_name = t1.instrument_name
                    AND timeframe = t1.timeframe
            )
        """)

    def generate_currency_rsi(self):
        for currency in self.currency_rsi_values:
            for timeframe in self.currency_rsi_values[currency]:
                try:
                    self.currency_rsi_avg[currency][timeframe] = (
                        sum(self.currency_rsi_values[currency][timeframe]) /
                        len(self.currency_rsi_values[currency][timeframe]))
                    self.con.sql(f"""
                        INSERT INTO {self.currency_table_name}
                        (currency, timeframe, rsi)
                        VALUES
                        ('{currency}',
                        '{timeframe}',
                        {self.currency_rsi_avg[currency][timeframe]})
                    """)
                except ZeroDivisionError:
                    self.currency_rsi_avg[currency][timeframe] = None

        self.con.sql(f"""
            UPDATE {self.currency_table_name} t1
            SET rsi_diff = (
                SELECT ABS(rsi - 50)
                FROM {self.currency_table_name}
                WHERE currency = t1.currency
                    AND timeframe = t1.timeframe
            )
        """)

        self.con.sql(f"""
            UPDATE {self.currency_table_name} t1
            SET rank = (
                SELECT rank
                FROM (
                    SELECT currency,
                           timeframe,
                           DENSE_RANK() OVER (
                               PARTITION BY timeframe ORDER BY rsi_diff DESC) as rank
                    FROM {self.currency_table_name}
                ) rankings
                WHERE rankings.currency = t1.currency
                    AND rankings.timeframe = t1.timeframe
            )
        """)

        self.con.sql(f"""
            UPDATE {self.currency_table_name} t1
            SET status = (
                SELECT CASE
                    WHEN rsi_diff >= 5 AND rsi < 50 THEN 'buy'
                    WHEN rsi_diff >= 5 AND rsi > 50 THEN 'sell'
                    ELSE 'neutral'
                END
            )
        """)

    def generate_base_quote_timeframe_rank(self):
        self.con.sql(f"""
            UPDATE {self.pair_table_name} t1
            SET base_rsi = (
                SELECT rsi
                FROM {self.currency_table_name}
                WHERE currency = t1.base_currency AND timeframe = t1.timeframe
            )
        """)
        self.con.sql(f"""
            UPDATE {self.pair_table_name} t1
            SET quote_rsi = (
                SELECT rsi
                FROM {self.currency_table_name}
                WHERE currency = t1.quote_currency AND timeframe = t1.timeframe
            )
        """)
        self.con.sql(f"""
            UPDATE {self.pair_table_name} t1
            SET base_rsi_diff = (
                SELECT rsi_diff
                FROM {self.currency_table_name}
                WHERE currency = t1.base_currency AND timeframe = t1.timeframe
            )
        """)
        self.con.sql(f"""
            UPDATE {self.pair_table_name} t1
            SET quote_rsi_diff = (
                SELECT rsi_diff
                FROM {self.currency_table_name}
                WHERE currency = t1.quote_currency AND timeframe = t1.timeframe
            )
        """)
        self.con.sql(f"""
            UPDATE {self.pair_table_name} t1
            SET base_timeframe_rank = (
                SELECT rank
                FROM {self.currency_table_name}
                WHERE currency = t1.base_currency AND timeframe = t1.timeframe
            )
        """)
        self.con.sql(f"""
            UPDATE {self.pair_table_name} t1
            SET quote_timeframe_rank = (
                SELECT rank
                FROM {self.currency_table_name}
                WHERE currency = t1.quote_currency AND timeframe = t1.timeframe
            )
        """)
        self.con.sql(f"""
            UPDATE {self.pair_table_name} t1
            SET quote_status = (
                SELECT status
                FROM {self.currency_table_name}
                WHERE currency = t1.quote_currency AND timeframe = t1.timeframe
            )
        """)
        self.con.sql(f"""
            UPDATE {self.pair_table_name} t1
            SET base_status = (
                SELECT status
                FROM {self.currency_table_name}
                WHERE currency = t1.base_currency AND timeframe = t1.timeframe
            )
        """)
