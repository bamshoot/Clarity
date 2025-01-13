from .DataFoundationBuilder import DataFoundationBuilder
import talib as ta


class PatternCD(DataFoundationBuilder):

    def __init__(self, db_path: str):
        super().__init__(db_path)
        self.fractal_period = None
        self.cluster_count = None
        self.atr_threshold = None

    def reset_pattern_convergence_divergence_table(self):
        self.drop_table(self.working_table_name)
        self._create_pattern_convergence_divergence_table()

    def set_fractal_period(self, fractal_period: int):
        self.fractal_period = fractal_period

    def set_cluster_count(self, cluster_count: int):
        self.cluster_count = cluster_count

    def set_atr_threshold(self, atr_threshold: float):
        self.atr_threshold = atr_threshold

    def _create_pattern_convergence_divergence_table(self):
        self.con.sql(f"""
            CREATE TABLE {self.working_table_name}
            (
                instrument_name VARCHAR,
                timeframe VARCHAR,
                f INTEGER,
                atr DOUBLE,
                atr_threshold DOUBLE,
                first_upper_x BIGINT,
                first_upper_y DOUBLE,
                second_upper_x BIGINT,
                second_upper_y DOUBLE,
                third_upper_x BIGINT,
                third_upper_y DOUBLE,
                first_lower_x BIGINT,
                first_lower_y DOUBLE,
                second_lower_x BIGINT,
                second_lower_y DOUBLE,
                third_lower_x BIGINT,
                third_lower_y DOUBLE,
                max_first_x BIGINT,
                max_first_y DOUBLE,
                min_third_x BIGINT,
                min_third_y DOUBLE,
                upper_slope DOUBLE,
                upper_intercept DOUBLE,
                lower_slope DOUBLE,
                lower_intercept DOUBLE,
                y_at_max_first_x DOUBLE,
                y_at_min_third_x DOUBLE,
                y_at_upper_second_x DOUBLE,
                y_at_lower_second_x DOUBLE,
                dist_first DOUBLE,
                dist_third DOUBLE,
                dist_upper_second DOUBLE,
                dist_lower_second DOUBLE,
                upper_second_atr DOUBLE,
                lower_second_atr DOUBLE,
                dist_third_lt_first BOOLEAN,
                upper_second_within_atr BOOLEAN,
                lower_second_within_atr BOOLEAN,
                status VARCHAR
            )
        """)

    def generate_pattern_convergence_divergence(self):

        data = self.get_table_from_db(self.source_table_name).fetchnumpy()
        atr = ta.ATR(data["high"], data["low"], data["close"], 14)[-1]

        last_timestamp = self.con.sql(f"""
            SELECT timestamp
            FROM {self.source_table_name}
            ORDER BY TIMESTAMP DESC
            LIMIT 1
        """).fetchone()[0]

        self.con.sql(f"""
            CREATE TEMP TABLE temp_uf AS
            SELECT timestamp, open, close, f, uf, lf,
                GREATEST(open, close) as max_price, 0 as min_price
            FROM (
                SELECT *
                FROM {self.source_table_name}
                WHERE uf = TRUE and timestamp < {last_timestamp}
                ORDER BY TIMESTAMP DESC
                LIMIT 3
            ) sub
            ORDER BY TIMESTAMP ASC
        """)

        self.con.sql(f"""
            CREATE TEMP TABLE temp_lf AS
            SELECT timestamp, open, close, f, uf, lf, 0 as max_price,
                LEAST(open, close) as min_price
            FROM (
                SELECT *
                FROM {self.source_table_name}
                WHERE lf = TRUE and timestamp < {last_timestamp}
                ORDER BY TIMESTAMP DESC
                LIMIT 3
            ) sub
            ORDER BY TIMESTAMP ASC
        """)

        self.con.sql("""
            CREATE TEMP TABLE temp_uf_transposed AS
            SELECT
                timestamp[1] as first_upper_x,
                max_price[1] as first_upper_y,
                timestamp[2] as second_upper_x,
                max_price[2] as second_upper_y,
                timestamp[3] as third_upper_x,
                max_price[3] as third_upper_y
            FROM (
                SELECT
                    LIST(timestamp) as timestamp,
                    LIST(max_price) as max_price
                FROM temp_uf
            )
        """)

        self.con.sql("""
            CREATE TEMP TABLE temp_lf_transposed AS
            SELECT
                timestamp[1] as first_lower_x,
                min_price[1] as first_lower_y,
                timestamp[2] as second_lower_x,
                min_price[2] as second_lower_y,
                timestamp[3] as third_lower_x,
                min_price[3] as third_lower_y
            FROM (
                SELECT
                    LIST(timestamp) as timestamp,
                    LIST(min_price) as min_price
                FROM temp_lf
            )
        """)

        # First INSERT statement
        self.con.sql(f"""
            INSERT INTO {self.working_table_name}
            (instrument_name,
            timeframe,
            f,
            atr,
            atr_threshold,
            first_upper_x,
            first_upper_y,
            second_upper_x,
            second_upper_y,
            third_upper_x,
            third_upper_y)
            SELECT
                '{self.instrument_name}',
                '{self.timeframe}',
                {self.fractal_period},
                {atr},
                {self.atr_threshold},
                first_upper_x,
                first_upper_y,
                second_upper_x,
                second_upper_y,
                third_upper_x,
                third_upper_y
            FROM temp_uf_transposed
        """)

        self.con.sql(f"""
            UPDATE {self.working_table_name}
            SET
                first_lower_x = temp.first_lower_x,
                first_lower_y = temp.first_lower_y,
                second_lower_x = temp.second_lower_x,
                second_lower_y = temp.second_lower_y,
                third_lower_x = temp.third_lower_x,
                third_lower_y = temp.third_lower_y
            FROM temp_lf_transposed temp
            WHERE {self.working_table_name}.instrument_name = '{self.instrument_name}'
            AND {self.working_table_name}.timeframe = '{self.timeframe}'
            AND {self.working_table_name}.f = {self.fractal_period}
        """)

        self.con.sql(f"""
            UPDATE {self.working_table_name}
            SET max_first_x = GREATEST(first_upper_x, first_lower_x),
                min_third_x = LEAST(third_upper_x, third_lower_x)
            WHERE instrument_name = '{self.instrument_name}'
            AND timeframe = '{self.timeframe}'
            AND f = {self.fractal_period}
        """)

        self.con.sql(f"""
            UPDATE {self.working_table_name}
            SET
                upper_slope = (third_upper_y - first_upper_y) /
                    (third_upper_x - first_upper_x),
                upper_intercept = first_upper_y - (first_upper_x *
                    (third_upper_y - first_upper_y) /
                    (third_upper_x - first_upper_x))
            WHERE instrument_name = '{self.instrument_name}'
            AND timeframe = '{self.timeframe}'
            AND f = {self.fractal_period}
        """)

        self.con.sql(f"""
            UPDATE {self.working_table_name}
            SET
                lower_slope = (third_lower_y - first_lower_y) /
                    (third_lower_x - first_lower_x),
                lower_intercept = first_lower_y - (first_lower_x *
                    (third_lower_y - first_lower_y) /
                    (third_lower_x - first_lower_x))
            WHERE instrument_name = '{self.instrument_name}'
            AND timeframe = '{self.timeframe}'
            AND f = {self.fractal_period}
        """)

        self.con.sql(f"""
            UPDATE {self.working_table_name}
            SET
                y_at_max_first_x = upper_slope * max_first_x + upper_intercept,
                y_at_min_third_x = lower_slope * min_third_x + lower_intercept,
                y_at_upper_second_x = upper_slope * second_upper_x + upper_intercept,
                y_at_lower_second_x = lower_slope * second_lower_x + lower_intercept,
            WHERE instrument_name = '{self.instrument_name}'
            AND timeframe = '{self.timeframe}'
            AND f = {self.fractal_period}
        """)

        # union temp_uf and temp_lf
        self.con.sql("""
            CREATE TEMP TABLE temp_union AS
            SELECT * FROM temp_uf
            UNION ALL
            SELECT * FROM temp_lf
        """)

        self.con.sql(f"""
            UPDATE {self.working_table_name}
            SET
               max_first_y = GREATEST(max_price, min_price),
            FROM temp_union
            WHERE timestamp = max_first_x
        """)

        self.con.sql(f"""
            UPDATE {self.working_table_name}
            SET
               min_third_y = GREATEST(max_price, min_price),
            FROM temp_union
            WHERE timestamp = min_third_x
        """)

        self.con.sql(f"""
            UPDATE {self.working_table_name}
            SET
                dist_first = ABS(y_at_max_first_x - max_first_y),
                dist_third = ABS(y_at_min_third_x - min_third_y),
            WHERE instrument_name = '{self.instrument_name}'
            AND timeframe = '{self.timeframe}'
            AND f = {self.fractal_period}
        """)

        self.con.sql(f"""
            UPDATE {self.working_table_name}
            SET
                dist_upper_second = ABS(y_at_upper_second_x - second_upper_y),
                dist_lower_second = ABS(y_at_lower_second_x - second_lower_y),
            WHERE instrument_name = '{self.instrument_name}'
            AND timeframe = '{self.timeframe}'
            AND f = {self.fractal_period}
        """)

        self.con.sql(f"""
            UPDATE {self.working_table_name}
            SET
                upper_second_atr = dist_upper_second / atr *100,
                lower_second_atr = dist_lower_second / atr *100,
            WHERE instrument_name = '{self.instrument_name}'
            AND timeframe = '{self.timeframe}'
            AND f = {self.fractal_period}
        """)

        self.con.sql(f"""
            UPDATE {self.working_table_name}
            SET
                dist_third_lt_first = dist_third < dist_first,
                upper_second_within_atr = upper_second_atr < {self.atr_threshold},
                lower_second_within_atr = lower_second_atr < {self.atr_threshold}
            WHERE instrument_name = '{self.instrument_name}'
            AND timeframe = '{self.timeframe}'
            AND f = {self.fractal_period}
        """)

        self.con.sql(f"""
            UPDATE {self.working_table_name}
            SET
                status = CASE
                    WHEN dist_third_lt_first = TRUE
                        AND upper_second_within_atr = TRUE
                        AND lower_second_within_atr = TRUE
                        THEN 'Valid Convergence'
                    WHEN dist_third_lt_first = TRUE
                        AND lower_second_within_atr = TRUE
                        AND upper_second_within_atr = FALSE
                        THEN 'Invalid Upper Convergence'
                    WHEN dist_third_lt_first = TRUE
                        AND upper_second_within_atr = TRUE
                        AND lower_second_within_atr = FALSE
                        THEN 'Invalid Lower Convergence'
                    WHEN dist_third_lt_first = TRUE
                        AND upper_second_within_atr = FALSE
                        AND lower_second_within_atr = FALSE
                        THEN 'Invalid Upper and Lower Convergence'
                    WHEN dist_third_lt_first = FALSE
                        AND upper_second_within_atr = FALSE
                        AND lower_second_within_atr = FALSE
                        THEN 'Invalid Upper and Lower Divergence'
                    WHEN dist_third_lt_first = FALSE
                        AND upper_second_within_atr = TRUE
                        AND lower_second_within_atr = TRUE
                        THEN 'Valid Divergence'
                    WHEN dist_third_lt_first = FALSE
                        AND upper_second_within_atr = TRUE
                        AND lower_second_within_atr = FALSE
                        THEN 'Invalid Upper Divergence'
                    WHEN dist_third_lt_first = FALSE
                        AND upper_second_within_atr = FALSE
                        AND lower_second_within_atr = TRUE
                        THEN 'Invalid Lower Divergence'
                    ELSE 'Invalid'
                END
            WHERE instrument_name = '{self.instrument_name}'
            AND timeframe = '{self.timeframe}'
            AND f = {self.fractal_period}
        """)

        self.con.sql("""
            DROP TABLE IF EXISTS temp_uf
        """)
        self.con.sql("""
            DROP TABLE IF EXISTS temp_lf
        """)
        self.con.sql("""
            DROP TABLE IF EXISTS temp_uf_transposed
        """)
        self.con.sql("""
            DROP TABLE IF EXISTS temp_lf_transposed
        """)
        self.con.sql("""
            DROP TABLE IF EXISTS temp_union
        """)
