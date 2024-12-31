# import pandas as pd
import kmeans1d
import duckdb
import math
import time


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
        return self.con.sql(f"SELECT * FROM {table_name} ORDER BY datetime")

    def _drop_fractal_table(self, table_name: str):
        self.con.sql(f"DROP TABLE IF EXISTS {table_name}")

    def _create_fractal_table(self, table_name: str, fractal_table_name: str):
        self.con.sql(
            f"CREATE TABLE {fractal_table_name} AS SELECT * FROM {table_name}")

    def _add_columns_to_fractal_table(self, fractal_table_name: str):
        self.con.sql(f"""
            ALTER TABLE {fractal_table_name}
            ADD COLUMN lastCandlePrice DOUBLE
        """)
        self.con.sql(f"""
            ALTER TABLE {fractal_table_name}
            ADD COLUMN distLstCandle DOUBLE
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
        self.con.sql(f"""
            ALTER TABLE {fractal_table_name}
            ADD COLUMN clust INTEGER
        """)
        self.con.sql(f"""
            ALTER TABLE {fractal_table_name}
            ADD COLUMN cent DOUBLE
        """)
        self.con.sql(f"""
            ALTER TABLE {fractal_table_name}
            ADD COLUMN centDist DOUBLE
        """)
        self.con.sql(f"""
            ALTER TABLE {fractal_table_name}
            ADD COLUMN centDistLastCandle DOUBLE
        """)
        self.con.sql(f"""
            ALTER TABLE {fractal_table_name}
            ADD COLUMN centCount DOUBLE
        """)
        self.con.sql(f"""
            ALTER TABLE {fractal_table_name}
            ADD COLUMN idxExpMean DOUBLE
        """)
        self.con.sql(f"""
            ALTER TABLE {fractal_table_name}
            ADD COLUMN centCountRank DOUBLE
        """)
        self.con.sql(f"""
            ALTER TABLE {fractal_table_name}
            ADD COLUMN centDistLstCandleRank DOUBLE
        """)
        self.con.sql(f"""
            ALTER TABLE {fractal_table_name}
            ADD COLUMN idxExpMeanRank DOUBLE
        """)
        self.con.sql(f"""
            ALTER TABLE {fractal_table_name}
            ADD COLUMN distLstCandleRank DOUBLE
        """)

    def _reset_table(self, table_name: str, fractal_table_name: str):
        self._drop_fractal_table(fractal_table_name)
        self._create_fractal_table(table_name, fractal_table_name)
        self._add_columns_to_fractal_table(fractal_table_name)

    def generate_cluster_data(self,
                              table_name: str,
                              candle_price_point: str,
                              cluster_count: int = 5):

        df = self._get_table_from_db(table_name).to_df()

        clusters, centroids = kmeans1d.cluster(df[candle_price_point],
                                               cluster_count)

        cent_clust = [centroids[clust] for clust in clusters]

        df['cent'] = cent_clust
        df['clust'] = clusters

        self.con.execute(f"DROP TABLE IF EXISTS {table_name}")
        self.con.execute(f"""
            CREATE TABLE {table_name} AS
            SELECT * FROM df
        """)

    def get_table(self, table_name: str):
        return self.con.sql(f"SELECT * FROM {table_name}")

    def create_fractal_cluster_data(self, table_name: str):

        if self.params.get("candle_price_point") == "close":
            self.con.sql(f"""
                UPDATE {table_name}
                SET lastCandlePrice = (SELECT close FROM {table_name}
                                         ORDER BY date DESC LIMIT 1),
                    distLstCandle = abs((SELECT close FROM {table_name}
                                            ORDER BY date DESC LIMIT 1) - close)
            """)
        elif self.params.get("candle_price_point") == "high_low":
            self.con.sql(f"""
                UPDATE {table_name}
                SET lastCandlePrice = (SELECT (high + low) / 2 FROM {table_name}
                                         ORDER BY date DESC LIMIT 1),
                    distLstCandle = abs((SELECT (high + low) / 2 FROM
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
            UPDATE {table_name} t
            SET uf = temp.uf_temp,
                lf = temp.lf_temp
            FROM {table_name}_temp temp
            WHERE t.datetime = temp.datetime
        """)

        self._drop_fractal_table(f"{table_name}_temp")

        self.con.sql(f"""
            CREATE TABLE {table_name}_temp AS
            SELECT * FROM {table_name}
            WHERE uf = true OR lf = true
            ORDER BY idx
        """)

        self._drop_fractal_table(f"{table_name}")

        self.con.sql(f"""
            CREATE TABLE {table_name} AS
            SELECT * FROM {table_name}_temp
        """)

        self._drop_fractal_table(f"{table_name}_temp")

        self.generate_cluster_data(table_name,
                                   self.params.get("candle_price_point"),
                                   self.params.get("cluster_count"))

        self.con.sql(f"""
            UPDATE {table_name}
            SET centDist = abs(cent - close)
        """)

        self.con.sql(f"""
            DELETE FROM {table_name}
            WHERE centDist > (
                SELECT * FROM (
                    SELECT (MAX(close) - MIN(close))* {
                        self.params.get('outlier_threshold')}
                    FROM {table_name}
                )
            )
        """)

        self.con.sql(f"""
            UPDATE {table_name}
            SET centDistLastCandle = abs(cent - lastCandlePrice)
        """)

        self.con.sql(f"""
            UPDATE {table_name} t
            SET centCount = sub.cnt,
                idxExpMean = sub.i_mean
            FROM (
                SELECT
                    datetime,
                    COUNT(*) OVER (PARTITION BY clust) as cnt,
                    AVG(idxExp) OVER (PARTITION BY clust) as i_mean
                FROM {table_name}
            ) sub
            WHERE t.datetime = sub.datetime
        """)

        self.con.sql(f"""
            UPDATE {table_name} t
            SET centCountRank = sub.cnt_rank,
                centDistLstCandleRank = sub.cent_dist_last_candle_rank,
                idxExpMeanRank = sub.idx_exp_mean_rank,
                distLstCandleRank = sub.dist_last_candle_rank

            FROM (
                SELECT
                    datetime,
                    DENSE_RANK()
                        OVER (ORDER BY centCount DESC)
                        AS cnt_rank,
                    DENSE_RANK()
                        OVER (ORDER BY centDistLastCandle ASC)
                        AS cent_dist_last_candle_rank,
                    DENSE_RANK()
                        OVER (ORDER BY idxExpMean DESC)
                        AS idx_exp_mean_rank,
                    DENSE_RANK()
                        OVER (
                            PARTITION BY clust
                            ORDER BY distLstCandle ASC
                        )
                        AS dist_last_candle_rank
                FROM {table_name}
            ) sub
            WHERE t.datetime = sub.datetime
        """)


params = {
    "data_source": "EOD",
    "instrument_name": "EURAUD",
    "timeframe": "d",
    "candle_price_point": "close",
    "fractal_period": 3,
    "cluster_count": 10,
    "outlier_threshold": 0.02
}


start_time = time.time()

data_foundation_builder = DataFoundationBuilder("./database/clarity.db", params)
data_foundation_builder.create_fractal_cluster_data("tbl_EOD_EURAUD_d_fractals")
data = data_foundation_builder.get_table("tbl_EOD_EURAUD_d_fractals")
print(data)
data.write_csv("./outputs/fractal_data.csv")

end_time = time.time()
print(f"Time taken: {end_time - start_time} seconds")
