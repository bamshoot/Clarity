from server.indicators.DataFoundationBuilder import DataFoundationBuilder


class CandlePattern(DataFoundationBuilder):
    def __init__(self, db_path: str, candle_patterns: dict):
        super().__init__(db_path)
        self.candle_patterns = candle_patterns

    def reset_candle_pattern_table(self):
        self.drop_table(self.working_table_name)
        self._create_candle_pattern_table()

    def _create_candle_pattern_table(self):
        self.con.sql(f"""
            CREATE TABLE {self.working_table_name} AS
            SELECT * FROM {self.source_table_name}
        """)

        self.con.sql(f"""
            ALTER TABLE {self.working_table_name}
            ADD COLUMN instrument_name VARCHAR
        """)
        self.con.sql(f"""
            ALTER TABLE {self.working_table_name}
            ADD COLUMN timeframe VARCHAR
        """)

        for pattern in self.candle_patterns:
            self.con.sql(f"""
                ALTER TABLE {self.working_table_name}
                ADD COLUMN {pattern} INTEGER
            """)

    def generate_candle_patterns(self):
        data = self.get_table_from_db(self.working_table_name).fetchnumpy()

        for pattern_name, (_, func) in self.candle_patterns.items():
            print(f"Generating {pattern_name} "
                  f"for {self.instrument_name} "
                  f"{self.timeframe}")
            pattern_result = func(data['open'],
                                  data['high'],
                                  data['low'],
                                  data['close'])

            self.con.execute(f"""
                CREATE TEMP TABLE temp_patterns AS
                SELECT datetime,
                       UNNEST(?) as pattern_value
                FROM {self.working_table_name}
            """, [pattern_result.tolist()])

            self.con.execute(f"""
                UPDATE {self.working_table_name} t
                SET {pattern_name} = tp.pattern_value,
                    instrument_name = '{self.instrument_name}',
                    timeframe = '{self.timeframe}'
                FROM temp_patterns tp
                WHERE t.datetime = tp.datetime
            """)

            self.con.execute("DROP TABLE IF EXISTS temp_patterns")
