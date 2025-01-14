from .DataFoundationBuilder import DataFoundationBuilder
import talib as ta


class CandlePattern(DataFoundationBuilder):
    def __init__(self, db_path: str, candle_patterns: dict):
        super().__init__(db_path)
        self.candle_patterns = candle_patterns
        self.candle_pattern_params_table_name = None
        self.last_n_rows_table_name = None
        self.last_n_aggregated_table_name = None

    def set_candle_pattern_params_table_name(
            self, candle_pattern_params_table_name: str):
        self.candle_pattern_params_table_name = candle_pattern_params_table_name

    def set_last_n_rows_table_name(self, last_n_rows_table_name: str):
        self.last_n_rows_table_name = last_n_rows_table_name

    def set_last_n_aggregated_table_name(self, last_n_aggregated_table_name: str):
        self.last_n_aggregated_table_name = last_n_aggregated_table_name

    def reset_candle_pattern_params_table(self):
        self.drop_table(self.candle_pattern_params_table_name)
        self._create_candle_pattern_params_table()

    def reset_last_n_aggregated_table(self):
        self.drop_table(self.last_n_aggregated_table_name)
        self._create_last_n_aggregated_table()

    def reset_candle_pattern_table(self):
        self._create_candle_pattern_table()

    def reset_candle_pattern_last_n_rows(self):
        self.drop_table(self.last_n_rows_table_name)
        self._create_candle_pattern_last_n_rows()

    def _create_candle_pattern_params_table(self):
        self.con.sql(f"""
            CREATE TABLE IF NOT EXISTS {self.candle_pattern_params_table_name} (
                pattern_code VARCHAR,
                name VARCHAR,
                type VARCHAR,
                direction VARCHAR,
                func VARCHAR
            )
        """)

        for pattern_code, pattern_info in self.candle_patterns.items():
            self.con.sql(f"""
                INSERT INTO {self.candle_pattern_params_table_name}
                VALUES (
                    '{pattern_code}',
                    '{pattern_info["name"]}',
                    '{pattern_info["type"]}',
                    '{pattern_info["direction"]}',
                    '{pattern_info["func"]}'
                )
            """)

    def _create_candle_pattern_last_n_rows(self):
        self.con.sql(f"""
            CREATE TABLE IF NOT EXISTS {self.last_n_rows_table_name} (
                pattern_code VARCHAR,
                name VARCHAR,
                type VARCHAR,
                direction VARCHAR,
                func VARCHAR,
                "1" INTEGER,
                "2" INTEGER,
                "3" INTEGER,
                "4" INTEGER,
                "5" INTEGER,
                "6" INTEGER,
                "7" INTEGER,
                "8" INTEGER,
                "9" INTEGER,
                "10" INTEGER,
                "sum" INTEGER
            )
        """)

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

    def _create_last_n_aggregated_table(self):
        self.con.sql(f"""
            CREATE TABLE IF NOT EXISTS {self.last_n_aggregated_table_name} (
                instrument_name VARCHAR,
                timeframe VARCHAR,
                reversal INTEGER,
                indecisive INTEGER,
                continuation INTEGER
            )
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

    def generate_candle_pattern_last_n_rows(self, n: int):
        self.con.sql(f"""
           WITH latest_patterns AS (
                SELECT
                    timestamp,
                    CDL2CROWS
                    , CDL3BLACKCROWS
                    , CDL3INSIDE
                    , CDL3LINESTRIKE
                    , CDL3OUTSIDE
                    , CDL3STARSINSOUTH
                    , CDL3WHITESOLDIERS
                    , CDLABANDONEDBABY
                    , CDLADVANCEBLOCK
                    , CDLBELTHOLD
                    , CDLBREAKAWAY
                    , CDLCLOSINGMARUBOZU
                    , CDLCONCEALBABYSWALL
                    , CDLCOUNTERATTACK
                    , CDLDARKCLOUDCOVER
                    , CDLDOJI
                    , CDLDOJISTAR
                    , CDLDRAGONFLYDOJI
                    , CDLENGULFING
                    , CDLEVENINGDOJISTAR
                    , CDLEVENINGSTAR
                    , CDLGAPSIDESIDEWHITE
                    , CDLGRAVESTONEDOJI
                    , CDLHAMMER
                    , CDLHANGINGMAN
                    , CDLHARAMI
                    , CDLHARAMICROSS
                    , CDLHIGHWAVE
                    , CDLHIKKAKE
                    , CDLHIKKAKEMOD
                    , CDLHOMINGPIGEON
                    , CDLIDENTICAL3CROWS
                    , CDLINNECK
                    , CDLINVERTEDHAMMER
                    , CDLKICKING
                    , CDLKICKINGBYLENGTH
                    , CDLLADDERBOTTOM
                    , CDLLONGLEGGEDDOJI
                    , CDLLONGLINE
                    , CDLMARUBOZU
                    , CDLMATCHINGLOW
                    , CDLMATHOLD
                    , CDLMORNINGDOJISTAR
                    , CDLMORNINGSTAR
                    , CDLONNECK
                    , CDLPIERCING
                    , CDLRICKSHAWMAN
                    , CDLRISEFALL3METHODS
                    , CDLSEPARATINGLINES
                    , CDLSHOOTINGSTAR
                    , CDLSHORTLINE
                    , CDLSPINNINGTOP
                    , CDLSTALLEDPATTERN
                    , CDLSTICKSANDWICH
                    , CDLTAKURI
                    , CDLTASUKIGAP
                    , CDLTHRUSTING
                    , CDLTRISTAR
                    , CDLUNIQUE3RIVER
                    , CDLUPSIDEGAP2CROWS
                    , CDLXSIDEGAP3METHODS
                FROM {self.working_table_name}
                ORDER BY timestamp DESC
                LIMIT {n}
            ),

            numbered_patterns AS (
                SELECT
                    ROW_NUMBER() OVER (ORDER BY timestamp ASC) as idx,
                    CDL2CROWS
                    , CDL3BLACKCROWS
                    , CDL3INSIDE
                    , CDL3LINESTRIKE
                    , CDL3OUTSIDE
                    , CDL3STARSINSOUTH
                    , CDL3WHITESOLDIERS
                    , CDLABANDONEDBABY
                    , CDLADVANCEBLOCK
                    , CDLBELTHOLD
                    , CDLBREAKAWAY
                    , CDLCLOSINGMARUBOZU
                    , CDLCONCEALBABYSWALL
                    , CDLCOUNTERATTACK
                    , CDLDARKCLOUDCOVER
                    , CDLDOJI
                    , CDLDOJISTAR
                    , CDLDRAGONFLYDOJI
                    , CDLENGULFING
                    , CDLEVENINGDOJISTAR
                    , CDLEVENINGSTAR
                    , CDLGAPSIDESIDEWHITE
                    , CDLGRAVESTONEDOJI
                    , CDLHAMMER
                    , CDLHANGINGMAN
                    , CDLHARAMI
                    , CDLHARAMICROSS
                    , CDLHIGHWAVE
                    , CDLHIKKAKE
                    , CDLHIKKAKEMOD
                    , CDLHOMINGPIGEON
                    , CDLIDENTICAL3CROWS
                    , CDLINNECK
                    , CDLINVERTEDHAMMER
                    , CDLKICKING
                    , CDLKICKINGBYLENGTH
                    , CDLLADDERBOTTOM
                    , CDLLONGLEGGEDDOJI
                    , CDLLONGLINE
                    , CDLMARUBOZU
                    , CDLMATCHINGLOW
                    , CDLMATHOLD
                    , CDLMORNINGDOJISTAR
                    , CDLMORNINGSTAR
                    , CDLONNECK
                    , CDLPIERCING
                    , CDLRICKSHAWMAN
                    , CDLRISEFALL3METHODS
                    , CDLSEPARATINGLINES
                    , CDLSHOOTINGSTAR
                    , CDLSHORTLINE
                    , CDLSPINNINGTOP
                    , CDLSTALLEDPATTERN
                    , CDLSTICKSANDWICH
                    , CDLTAKURI
                    , CDLTASUKIGAP
                    , CDLTHRUSTING
                    , CDLTRISTAR
                    , CDLUNIQUE3RIVER
                    , CDLUPSIDEGAP2CROWS
                    , CDLXSIDEGAP3METHODS
                FROM latest_patterns
            ),

            unpivoted AS (
                SELECT idx, 'CDL2CROWS' AS pattern_name, CDL2CROWS AS pattern_value
                FROM numbered_patterns
                UNION ALL SELECT idx, 'CDL3BLACKCROWS', CDL3BLACKCROWS
                FROM numbered_patterns
                UNION ALL SELECT idx, 'CDL3INSIDE', CDL3INSIDE
                FROM numbered_patterns
                UNION ALL SELECT idx, 'CDL3LINESTRIKE', CDL3LINESTRIKE
                FROM numbered_patterns
                UNION ALL SELECT idx, 'CDL3OUTSIDE', CDL3OUTSIDE
                FROM numbered_patterns
                UNION ALL SELECT idx, 'CDL3STARSINSOUTH', CDL3STARSINSOUTH
                FROM numbered_patterns
                UNION ALL SELECT idx, 'CDL3WHITESOLDIERS', CDL3WHITESOLDIERS
                FROM numbered_patterns
                UNION ALL SELECT idx, 'CDLABANDONEDBABY', CDLABANDONEDBABY
                FROM numbered_patterns
                UNION ALL SELECT idx, 'CDLADVANCEBLOCK', CDLADVANCEBLOCK
                FROM numbered_patterns
                UNION ALL SELECT idx, 'CDLBELTHOLD', CDLBELTHOLD
                FROM numbered_patterns
                UNION ALL SELECT idx, 'CDLBREAKAWAY', CDLBREAKAWAY
                FROM numbered_patterns
                UNION ALL SELECT idx, 'CDLCLOSINGMARUBOZU', CDLCLOSINGMARUBOZU
                FROM numbered_patterns
                UNION ALL SELECT idx, 'CDLCONCEALBABYSWALL', CDLCONCEALBABYSWALL
                FROM numbered_patterns
                UNION ALL SELECT idx, 'CDLCOUNTERATTACK', CDLCOUNTERATTACK
                FROM numbered_patterns
                UNION ALL SELECT idx, 'CDLDARKCLOUDCOVER', CDLDARKCLOUDCOVER
                FROM numbered_patterns
                UNION ALL SELECT idx, 'CDLDOJI', CDLDOJI
                FROM numbered_patterns
                UNION ALL SELECT idx, 'CDLDOJISTAR', CDLDOJISTAR
                FROM numbered_patterns
                UNION ALL SELECT idx, 'CDLDRAGONFLYDOJI', CDLDRAGONFLYDOJI
                FROM numbered_patterns
                UNION ALL SELECT idx, 'CDLENGULFING', CDLENGULFING
                FROM numbered_patterns
                UNION ALL SELECT idx, 'CDLEVENINGDOJISTAR', CDLEVENINGDOJISTAR
                FROM numbered_patterns
                UNION ALL SELECT idx, 'CDLEVENINGSTAR', CDLEVENINGSTAR
                FROM numbered_patterns
                UNION ALL SELECT idx, 'CDLGAPSIDESIDEWHITE', CDLGAPSIDESIDEWHITE
                FROM numbered_patterns
                UNION ALL SELECT idx, 'CDLGRAVESTONEDOJI', CDLGRAVESTONEDOJI
                FROM numbered_patterns
                UNION ALL SELECT idx, 'CDLHAMMER', CDLHAMMER
                FROM numbered_patterns
                UNION ALL SELECT idx, 'CDLHANGINGMAN', CDLHANGINGMAN
                FROM numbered_patterns
                UNION ALL SELECT idx, 'CDLHARAMI', CDLHARAMI
                FROM numbered_patterns
                UNION ALL SELECT idx, 'CDLHARAMICROSS', CDLHARAMICROSS
                FROM numbered_patterns
                UNION ALL SELECT idx, 'CDLHIGHWAVE', CDLHIGHWAVE
                FROM numbered_patterns
                UNION ALL SELECT idx, 'CDLHIKKAKE', CDLHIKKAKE
                FROM numbered_patterns
                UNION ALL SELECT idx, 'CDLHIKKAKEMOD', CDLHIKKAKEMOD
                FROM numbered_patterns
                UNION ALL SELECT idx, 'CDLHOMINGPIGEON', CDLHOMINGPIGEON
                FROM numbered_patterns
                UNION ALL SELECT idx, 'CDLIDENTICAL3CROWS', CDLIDENTICAL3CROWS
                FROM numbered_patterns
                UNION ALL SELECT idx, 'CDLINNECK', CDLINNECK FROM numbered_patterns
                UNION ALL SELECT idx, 'CDLINVERTEDHAMMER', CDLINVERTEDHAMMER
                FROM numbered_patterns
                UNION ALL SELECT idx, 'CDLKICKING', CDLKICKING
                FROM numbered_patterns
                UNION ALL SELECT idx, 'CDLKICKINGBYLENGTH', CDLKICKINGBYLENGTH
                FROM numbered_patterns
                UNION ALL SELECT idx, 'CDLLADDERBOTTOM', CDLLADDERBOTTOM
                FROM numbered_patterns
                UNION ALL SELECT idx, 'CDLLONGLEGGEDDOJI', CDLLONGLEGGEDDOJI
                FROM numbered_patterns
                UNION ALL SELECT idx, 'CDLLONGLINE', CDLLONGLINE
                FROM numbered_patterns
                UNION ALL SELECT idx, 'CDLMARUBOZU', CDLMARUBOZU
                FROM numbered_patterns
                UNION ALL SELECT idx, 'CDLMATCHINGLOW', CDLMATCHINGLOW
                FROM numbered_patterns
                UNION ALL SELECT idx, 'CDLMATHOLD', CDLMATHOLD
                FROM numbered_patterns
                UNION ALL SELECT idx, 'CDLMORNINGDOJISTAR', CDLMORNINGDOJISTAR
                FROM numbered_patterns
                UNION ALL SELECT idx, 'CDLMORNINGSTAR', CDLMORNINGSTAR
                FROM numbered_patterns
                UNION ALL SELECT idx, 'CDLONNECK', CDLONNECK
                FROM numbered_patterns
                UNION ALL SELECT idx, 'CDLPIERCING', CDLPIERCING
                FROM numbered_patterns
                UNION ALL SELECT idx, 'CDLRICKSHAWMAN', CDLRICKSHAWMAN
                FROM numbered_patterns
                UNION ALL SELECT idx, 'CDLRISEFALL3METHODS', CDLRISEFALL3METHODS
                FROM numbered_patterns
                UNION ALL SELECT idx, 'CDLSEPARATINGLINES', CDLSEPARATINGLINES
                FROM numbered_patterns
                UNION ALL SELECT idx, 'CDLSHOOTINGSTAR', CDLSHOOTINGSTAR
                FROM numbered_patterns
                UNION ALL SELECT idx, 'CDLSHORTLINE', CDLSHORTLINE
                FROM numbered_patterns
                UNION ALL SELECT idx, 'CDLSPINNINGTOP', CDLSPINNINGTOP
                FROM numbered_patterns
                UNION ALL SELECT idx, 'CDLSTALLEDPATTERN', CDLSTALLEDPATTERN
                FROM numbered_patterns
                UNION ALL SELECT idx, 'CDLSTICKSANDWICH', CDLSTICKSANDWICH
                FROM numbered_patterns
                UNION ALL SELECT idx, 'CDLTAKURI', CDLTAKURI
                FROM numbered_patterns
                UNION ALL SELECT idx, 'CDLTASUKIGAP', CDLTASUKIGAP
                FROM numbered_patterns
                UNION ALL SELECT idx, 'CDLTHRUSTING', CDLTHRUSTING
                FROM numbered_patterns
                UNION ALL SELECT idx, 'CDLTRISTAR', CDLTRISTAR
                FROM numbered_patterns
                UNION ALL SELECT idx, 'CDLUNIQUE3RIVER', CDLUNIQUE3RIVER
                FROM numbered_patterns
                UNION ALL SELECT idx, 'CDLUPSIDEGAP2CROWS', CDLUPSIDEGAP2CROWS
                FROM numbered_patterns
                UNION ALL SELECT idx, 'CDLXSIDEGAP3METHODS', CDLXSIDEGAP3METHODS
                FROM numbered_patterns
            ),

            last_n_rows AS (
                SELECT
                    u.pattern_name AS pattern_code,
                    p.name,
                    p.type,
                    p.direction,
                    p.func,
                    MAX(CASE WHEN u.idx = 1  THEN u.pattern_value END) AS "1",
                    MAX(CASE WHEN u.idx = 2  THEN u.pattern_value END) AS "2",
                    MAX(CASE WHEN u.idx = 3  THEN u.pattern_value END) AS "3",
                    MAX(CASE WHEN u.idx = 4  THEN u.pattern_value END) AS "4",
                    MAX(CASE WHEN u.idx = 5  THEN u.pattern_value END) AS "5",
                    MAX(CASE WHEN u.idx = 6  THEN u.pattern_value END) AS "6",
                    MAX(CASE WHEN u.idx = 7  THEN u.pattern_value END) AS "7",
                    MAX(CASE WHEN u.idx = 8  THEN u.pattern_value END) AS "8",
                    MAX(CASE WHEN u.idx = 9  THEN u.pattern_value END) AS "9",
                    MAX(CASE WHEN u.idx = 10 THEN u.pattern_value END) AS "10",
                    COALESCE(SUM(CASE
                        WHEN u.idx BETWEEN 1 AND 10 THEN u.pattern_value
                    END), 0) AS "sum"
                FROM unpivoted u
                LEFT JOIN tbl_candle_patterns_params p
                ON u.pattern_name = p.pattern_code
                GROUP BY u.pattern_name, p.name, p.type, p.direction, p.func
                ORDER BY u.pattern_name
            )

            INSERT INTO {self.last_n_rows_table_name}
            SELECT * FROM last_n_rows
        """)

    def generate_last_n_aggregated_data(self):
        self.con.sql(f"""
            INSERT INTO {self.last_n_aggregated_table_name}
            SELECT
                '{self.instrument_name}',
                '{self.timeframe}',
                SUM(CASE WHEN type = 'reversal'
                         THEN "sum"
                         ELSE 0 END) as reversal,
                SUM(CASE WHEN type = 'indecisive'
                         THEN "sum"
                         ELSE 0 END) as indecisive,
                SUM(CASE WHEN type = 'continuation'
                         THEN "sum"
                         ELSE 0 END) as continuation
            FROM {self.last_n_rows_table_name}
            """)
