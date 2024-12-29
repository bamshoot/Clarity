# import pandas as pd
from indicators.williams_fractal import williams_fractal
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

        df = self.con.sql(f"SELECT * FROM {table_name}").df()

        fractal = williams_fractal(df,
                                   self.params["candle_price_point"],
                                   self.params["fractal_period"])

        temp_table = f"temp_{table_name}_fractals"
        self.con.execute(f"DROP TABLE IF EXISTS {temp_table}")
        self.con.execute(f"""
            CREATE TABLE {temp_table} AS
            SELECT
                row_number() OVER () - 1 as idx,
                lf as fractal_lf,
                uf as fractal_uf
            FROM fractal
        """)

        # Join with renamed columns
        df = self.con.sql(f"""
            SELECT a.*, b.fractal_lf, b.fractal_uf
            FROM df a
            LEFT JOIN {temp_table} b ON a.idx = b.idx
        """).df()

        # Filter fractals and continue processing
        df = df[(df['fractal_uf'] == 1) | (df['fractal_lf'] == 1)]
        df['fractal_period'] = self.params["fractal_period"]


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


