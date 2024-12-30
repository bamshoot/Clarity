# import pandas as pd
# import kmeans1d
import duckdb
# import numpy as np
import math


class DataFoundationBuilder:
    def __init__(self, db_path: str, params: dict):
        self.db_path = db_path
        self.con = duckdb.connect(self.db_path)
        self.params = params
        self.table_name = (f"tbl_{self.params['data_source']}"
                           f"_{self.params['instrument_name']}"
                           f"_{self.params['timeframe']}")
        self.fractal_table_name = f"{self.table_name}_fractals"
        self._reset_table(self.table_name, self.fractal_table_name)

    def __del__(self):
        if hasattr(self, 'con'):
            self.con.close()

    def _get_table_from_db(self, table_name: str):
        return self.con.sql(f"SELECT * FROM {table_name}")

    def _drop_fractal_table(self, table_name: str):
        self.con.sql(f"DROP TABLE IF EXISTS {table_name}")

    def _create_fractal_table(self, table_name: str, fractal_table_name: str):
        self.con.sql(
            f"CREATE TABLE {fractal_table_name} AS SELECT * FROM {table_name}")

    def _add_columns_to_fractal_table(self, fractal_table_name: str):
        self.con.sql(f"""
            ALTER TABLE {fractal_table_name}
            ADD COLUMN last_candle_price DOUBLE
        """)
        self.con.sql(f"""
            ALTER TABLE {fractal_table_name}
            ADD COLUMN dist_last_candle DOUBLE
        """)
        self.con.sql(f"""
            ALTER TABLE {fractal_table_name}
            ADD COLUMN idx INTEGER
        """)
        self.con.sql(f"""
            ALTER TABLE {fractal_table_name}
            ADD COLUMN idxExp DOUBLE
        """)
        self.con.sql(f"""
            ALTER TABLE {fractal_table_name}
            ADD COLUMN uf BOOLEAN
        """)
        self.con.sql(f"""
            ALTER TABLE {fractal_table_name}
            ADD COLUMN lf BOOLEAN
        """)

    def _reset_table(self, table_name: str, fractal_table_name: str):
        self._drop_fractal_table(fractal_table_name)
        self._create_fractal_table(table_name, fractal_table_name)
        self._add_columns_to_fractal_table(fractal_table_name)

    def get_table(self, table_name: str):
        return self.con.sql(f"SELECT * FROM {table_name}")

    def create_fractal_cluster_data(self, table_name: str):

        if self.params.get("candle_price_point") == "close":
            self.con.sql(f"""
                UPDATE {table_name}
                SET last_candle_price = (SELECT close FROM {table_name}
                                         ORDER BY date DESC LIMIT 1),
                    dist_last_candle = abs((SELECT close FROM {table_name}
                                            ORDER BY date DESC LIMIT 1) - close)
            """)
        elif self.params.get("candle_price_point") == "high_low":
            self.con.sql(f"""
                UPDATE {table_name}
                SET last_candle_price = (SELECT (high + low) / 2 FROM {table_name}
                                         ORDER BY date DESC LIMIT 1),
                    dist_last_candle = abs((SELECT (high + low) / 2 FROM
                                            {table_name} ORDER BY date DESC
                                            LIMIT 1) - (high + low) / 2)
            """)

        self._drop_fractal_table(f"{table_name}_temp")

        self.con.sql(f"""
            CREATE TABLE {table_name}_temp AS
            SELECT *,
                   row_number() OVER (ORDER BY date) - 1 AS idx_temp,
                   power((row_number() OVER (ORDER BY date) /
                          (count(*) OVER () + 1)), {math.e * 2}) AS idxExp_temp
            FROM {table_name}
        """)

        self.con.sql(f"""
            UPDATE {table_name}
            SET idx = {table_name}_temp.idx_temp,
                idxExp = {table_name}_temp.idxExp_temp
            FROM {table_name}_temp
            WHERE {table_name}.date = {table_name}_temp.date
        """)

        self._drop_fractal_table(f"{table_name}_temp")

        self.con.sql(f"""
            CREATE TABLE {table_name}_temp AS
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
                            WHEN '{self.params.get('candle_price_point')}' =
                                'high_low' THEN high
                            ELSE close
                        END) OVER (
                            ORDER BY date
                            ROWS BETWEEN {self.params.get('fractal_period')}
                                PRECEDING AND {self.params.get('fractal_period')}
                                FOLLOWING
                        ) as window_max,
                        MIN(CASE
                            WHEN '{self.params.get('candle_price_point')}' =
                                'high_low' THEN low
                            ELSE close
                        END) OVER (
                            ORDER BY date
                            ROWS BETWEEN {self.params.get('fractal_period')}
                                PRECEDING AND {self.params.get('fractal_period')}
                                FOLLOWING
                        ) as window_min,
                        CASE
                            WHEN '{self.params.get('candle_price_point')}' =
                                'high_low' THEN high
                            ELSE close
                        END as current_high,
                        CASE
                            WHEN '{self.params.get('candle_price_point')}' =
                                'high_low' THEN low
                            ELSE close
                        END as current_low
                    FROM {table_name}
                ) AS subq
            )
            SELECT
                t.*,
                f.uf AS uf_temp,
                f.lf AS lf_temp
            FROM {table_name} t
            LEFT JOIN fractals f ON t.datetime = f.datetime
            ORDER BY t.datetime;
        """)

        self.con.sql(f"""
            UPDATE {table_name}
            SET uf = {table_name}_temp.uf_temp,
                lf = {table_name}_temp.lf_temp
            FROM {table_name}_temp
            WHERE {table_name}.datetime = {table_name}_temp.datetime
        """)

        self._drop_fractal_table(f"{table_name}_temp")


params = {
    "data_source": "EOD",
    "instrument_name": "EURAUD",
    "timeframe": "d",
    "candle_price_point": "close",
    "fractal_period": 3,
    "cluster_count": 10,
}


data_foundation_builder = DataFoundationBuilder("./database/clarity.db", params)
data_foundation_builder.create_fractal_cluster_data("tbl_EOD_EURAUD_d_fractals")
data = data_foundation_builder.get_table("tbl_EOD_EURAUD_d_fractals")
print(data)
