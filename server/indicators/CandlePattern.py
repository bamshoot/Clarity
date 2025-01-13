from .DataFoundationBuilder import DataFoundationBuilder
import talib as ta


class CandlePattern(DataFoundationBuilder):
    def __init__(self, db_path: str, candle_patterns: dict):
        super().__init__(db_path)
        self.candle_patterns = candle_patterns

    def reset_candle_pattern_table(self):
        self._create_candle_pattern_table()

    def _create_candle_pattern_table(self):
        self.con.sql(f"""
            CREATE TABLE IF NOT EXISTS {self.working_table_name} AS
            SELECT * FROM {self.source_table_name}
        """)

        self.con.sql(f"""
            ALTER TABLE {self.working_table_name}
            ADD COLUMN IF NOT EXISTS instrument_name VARCHAR
        """)
        self.con.sql(f"""
            ALTER TABLE {self.working_table_name}
            ADD COLUMN IF NOT EXISTS timeframe VARCHAR
        """)

        for pattern in self.candle_patterns:
            self.con.sql(f"""
                ALTER TABLE {self.working_table_name}
                ADD COLUMN IF NOT EXISTS {pattern} INTEGER
            """)

    def _create_temp_table_timestamps_in_source_not_in_candle_pattern(self):
        self.con.execute(f"""
            CREATE TEMP TABLE temp_insert AS
            SELECT s.timestamp,
                   s.gmtoffset,
                   s.datetime,
                   s.date,
                   s.open,
                   s.high,
                   s.low,
                   s.close,
                   s.volume,
                   s.adjusted_close
            FROM {self.source_table_name} AS s
            LEFT JOIN {self.working_table_name} AS w
            ON s.timestamp = w.timestamp
            WHERE w.timestamp IS NULL
        """)

        self.con.sql("""
            ALTER TABLE temp_insert
            ADD COLUMN IF NOT EXISTS instrument_name VARCHAR
        """)
        self.con.sql("""
            ALTER TABLE temp_insert
            ADD COLUMN IF NOT EXISTS timeframe VARCHAR
        """)

        for pattern in self.candle_patterns:
            self.con.sql(f"""
                ALTER TABLE temp_insert
                ADD COLUMN IF NOT EXISTS {pattern} INTEGER
            """)

    def generate_candle_patterns(self):
        self._create_temp_table_timestamps_in_source_not_in_candle_pattern()
        data = self.con.sql("SELECT * FROM temp_insert").fetchnumpy()

        for pattern_name, pattern_info in self.candle_patterns.items():
            func_name = pattern_info['func'].replace('ta.', '')
            func = getattr(ta, func_name)
            print(f"Generating {pattern_name} "
                  f"for {self.instrument_name} "
                  f"{self.timeframe}")

            pattern_result = func(data['open'],
                                  data['high'],
                                  data['low'],
                                  data['close'])

            self.con.execute(f"""
                CREATE TEMP TABLE temp_patterns AS
                SELECT timestamp, pattern_value
                FROM (
                    SELECT UNNEST(?::BIGINT[]) as timestamp,
                           UNNEST(?::INTEGER[]) as pattern_value
                    FROM {self.working_table_name}
                )
            """, [data['timestamp'], pattern_result.tolist()])

            self.con.sql(f"""
                UPDATE temp_insert
                SET {pattern_name} = temp_patterns.pattern_value
                FROM temp_patterns
                WHERE temp_insert.timestamp = temp_patterns.timestamp
            """)

            self.con.execute("DROP TABLE IF EXISTS temp_patterns")

        self.con.execute(f"""
            INSERT INTO {self.working_table_name}
            SELECT * FROM temp_insert
        """)

        self.con.execute("DROP TABLE IF EXISTS temp_insert")
