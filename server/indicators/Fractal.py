from .DataFoundationBuilder import DataFoundationBuilder


class Fractal(DataFoundationBuilder):
    def __init__(self,
                 db_connection,
                 max_bars: int,
                 candle_price_point: str):
        super().__init__(db_connection)
        self.fractal_period = None
        self.max_bars = max_bars
        self.candle_price_point = candle_price_point

    def create_fractal_table(self):
        self.con.sql(f"""
            CREATE TABLE {self.working_table_name} AS
            SELECT *
            FROM {self.source_table_name}
            ORDER BY datetime DESC
            LIMIT {self.max_bars}
        """)

        self.con.sql(f"""
            ALTER TABLE {self.working_table_name}
            ADD COLUMN f INTEGER
        """)
        self.con.sql(f"""
            ALTER TABLE {self.working_table_name}
            ADD COLUMN lstCandlePrice DOUBLE
        """)
        self.con.sql(f"""
            ALTER TABLE {self.working_table_name}
            ADD COLUMN distLstCandle DOUBLE
        """)
        self.con.sql(f"""
            ALTER TABLE {self.working_table_name}
            ADD COLUMN idx INTEGER
        """)
        self.con.sql(f"""
            ALTER TABLE {self.working_table_name}
            ADD COLUMN uf BOOLEAN
        """)
        self.con.sql(f"""
            ALTER TABLE {self.working_table_name}
            ADD COLUMN lf BOOLEAN
        """)

    def reset_table(self):
        self.drop_table(self.working_table_name)
        self.create_fractal_table()

    def set_fractal_period(self, fractal_period: int):
        self.fractal_period = fractal_period

    def generate_input_data(self):
        self.con.sql(f"""
            UPDATE {self.working_table_name}
            SET f = {self.fractal_period}
        """)

    def generate_last_candle_price(self):
        if self.candle_price_point == "close":
            self.con.sql(f"""
                UPDATE {self.working_table_name}
                SET lstCandlePrice = (SELECT close FROM {self.working_table_name}
                                         ORDER BY date DESC LIMIT 1),
                    distLstCandle = abs((SELECT close FROM {self.working_table_name}
                                            ORDER BY date DESC LIMIT 1) - close)
            """)
        elif self.candle_price_point == "high_low":
            self.con.sql(f"""
                UPDATE {self.working_table_name}
                SET lstCandlePrice = (SELECT (high + low) / 2
                                      FROM {self.working_table_name}
                                      ORDER BY date DESC LIMIT 1),
                    distLstCandle = abs((SELECT (high + low) / 2
                                         FROM {self.working_table_name}
                                         ORDER BY date DESC LIMIT 1) -
                                         (high + low) / 2)
            """)

    def generate_index_data(self):

        self.con.sql(f"""
            CREATE TABLE {self.working_table_name}_temp AS
            SELECT *,
                   row_number() OVER (ORDER BY date) - 1 AS idx_temp
            FROM {self.working_table_name}
        """)

        self.con.sql(f"""
            UPDATE {self.working_table_name}
            SET idx = {self.working_table_name}_temp.idx_temp,
            FROM {self.working_table_name}_temp
            WHERE {self.working_table_name}.date = {self.working_table_name}_temp.date
        """)

        self.drop_table(f"{self.working_table_name}_temp")

    def generate_fractal_data(self):

        self.con.sql(f"""
            CREATE TABLE {self.working_table_name}_temp AS
            WITH fractals AS (
                SELECT
                    datetime,
                    CASE
                        WHEN current_high = window_max THEN true
                        ELSE false
                    END as uf,
                    CASE
                        WHEN current_low = window_min THEN true
                        ELSE false
                    END as lf
                FROM (
                    SELECT
                        *,
                        MAX(CASE
                            WHEN '{self.candle_price_point}' =
                                'high_low' THEN high
                            ELSE close
                        END) OVER (
                            ORDER BY date
                            ROWS BETWEEN {self.fractal_period}
                                PRECEDING AND {self.fractal_period}
                                FOLLOWING
                        ) as window_max,
                        MIN(CASE
                            WHEN '{self.candle_price_point}' =
                                'high_low' THEN low
                            ELSE close
                        END) OVER (
                            ORDER BY date
                            ROWS BETWEEN {self.fractal_period}
                                PRECEDING AND {self.fractal_period}
                                FOLLOWING
                        ) as window_min,
                        CASE
                            WHEN '{self.candle_price_point}' =
                                'high_low' THEN high
                            ELSE close
                        END as current_high,
                        CASE
                            WHEN '{self.candle_price_point}' =
                                'high_low' THEN low
                            ELSE close
                        END as current_low
                    FROM {self.working_table_name}
                ) AS subq
            )
            SELECT
                t.*,
                f.uf AS uf_temp,
                f.lf AS lf_temp
            FROM {self.working_table_name} t
            LEFT JOIN fractals f ON t.datetime = f.datetime
            ORDER BY t.datetime;
        """)

        # print(self.con.sql(f"""
        #     SELECT COUNT(*) FROM {self.working_table_name}_temp
        # """).fetchone()[0])

        self.con.sql(f"""
            UPDATE {self.working_table_name} t
            SET uf = temp.uf_temp,
                lf = temp.lf_temp
            FROM {self.working_table_name}_temp temp
            WHERE t.datetime = temp.datetime
        """)

        self.drop_table(f"{self.working_table_name}_temp")

        self.con.sql(f"""
            CREATE TABLE {self.working_table_name}_temp AS
            SELECT * FROM {self.working_table_name}
            WHERE uf = true OR lf = true
            ORDER BY idx
        """)

        self.drop_table(f"{self.working_table_name}")

        self.con.sql(f"""
            CREATE TABLE {self.working_table_name} AS
            SELECT * FROM {self.working_table_name}_temp
        """)

        self.drop_table(f"{self.working_table_name}_temp")
