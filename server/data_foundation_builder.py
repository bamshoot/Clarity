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
        self.fractal_table_name = (f"{self.table_name}_"
                                   f"f{self.params.get('fractal_period')}_"
                                   f"k{self.params.get('cluster_count')}")
        self._reset_table(self.table_name, self.fractal_table_name)
        self.threshold = self.con.sql(f"""
            SELECT (MAX(close) - MIN(close)) * {self.params.get('outlier_threshold')}
            FROM {self.table_name}
        """).fetchone()[0]

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
            ADD COLUMN f INTEGER
        """)
        self.con.sql(f"""
            ALTER TABLE {fractal_table_name}
            ADD COLUMN k INTEGER
        """)
        self.con.sql(f"""
            ALTER TABLE {fractal_table_name}
            ADD COLUMN o DOUBLE
        """)
        self.con.sql(f"""
            ALTER TABLE {fractal_table_name}
            ADD COLUMN lstCandlePrice DOUBLE
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
            ADD COLUMN centDistLstCandle DOUBLE
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
            ADD COLUMN score DOUBLE
        """)

    def _reset_table(self, table_name: str, fractal_table_name: str):
        self._drop_fractal_table(fractal_table_name)
        self._create_fractal_table(table_name, fractal_table_name)
        self._add_columns_to_fractal_table(fractal_table_name)

    def _generate_input_data(self, fractal_table_name: str):
        self.con.sql(f"""
            UPDATE {fractal_table_name}
            SET f = {self.params.get('fractal_period')}
        """)
        self.con.sql(f"""
            UPDATE {fractal_table_name}
            SET k = {self.params.get('cluster_count')}
        """)
        self.con.sql(f"""
            UPDATE {fractal_table_name}
            SET o = {self.params.get('outlier_threshold')}
        """)

    def _generate_last_candle_price(self, fractal_table_name: str):
        if self.params.get("candle_price_point") == "close":
            self.con.sql(f"""
                UPDATE {fractal_table_name}
                SET lstCandlePrice = (SELECT close FROM {fractal_table_name}
                                         ORDER BY date DESC LIMIT 1),
                    distLstCandle = abs((SELECT close FROM {fractal_table_name}
                                            ORDER BY date DESC LIMIT 1) - close)
            """)
        elif self.params.get("candle_price_point") == "high_low":
            self.con.sql(f"""
                UPDATE {fractal_table_name}
                SET lstCandlePrice = (SELECT (high + low) / 2 FROM {fractal_table_name}
                                         ORDER BY date DESC LIMIT 1),
                    distLstCandle = abs((SELECT (high + low) / 2 FROM
                                            {fractal_table_name} ORDER BY date DESC
                                            LIMIT 1) - (high + low) / 2)
            """)

    def _generate_index_data(self, fractal_table_name: str):

        self.con.sql(f"""
            CREATE TABLE {fractal_table_name}_temp AS
            SELECT *,
                   row_number() OVER (ORDER BY date) - 1 AS idx_temp,
                   power((row_number() OVER (ORDER BY date) /
                          (count(*) OVER () + 1)), {math.e * 2}) AS idxExp_temp
            FROM {fractal_table_name}
        """)

        self.con.sql(f"""
            UPDATE {fractal_table_name}
            SET idx = {fractal_table_name}_temp.idx_temp,
                idxExp = {fractal_table_name}_temp.idxExp_temp
            FROM {fractal_table_name}_temp
            WHERE {fractal_table_name}.date = {fractal_table_name}_temp.date
        """)

        self._drop_fractal_table(f"{fractal_table_name}_temp")

    def _generate_fractal_data(self, fractal_table_name: str):

        self.con.sql(f"""
            CREATE TABLE {fractal_table_name}_temp AS
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
                    FROM {fractal_table_name}
                ) AS subq
            )
            SELECT
                t.*,
                f.uf AS uf_temp,
                f.lf AS lf_temp
            FROM {fractal_table_name} t
            LEFT JOIN fractals f ON t.datetime = f.datetime
            ORDER BY t.datetime;
        """)

        self.con.sql(f"""
            UPDATE {fractal_table_name} t
            SET uf = temp.uf_temp,
                lf = temp.lf_temp
            FROM {fractal_table_name}_temp temp
            WHERE t.datetime = temp.datetime
        """)

        self._drop_fractal_table(f"{fractal_table_name}_temp")

        self.con.sql(f"""
            CREATE TABLE {fractal_table_name}_temp AS
            SELECT * FROM {fractal_table_name}
            WHERE uf = true OR lf = true
            ORDER BY idx
        """)

        self._drop_fractal_table(f"{fractal_table_name}")

        self.con.sql(f"""
            CREATE TABLE {fractal_table_name} AS
            SELECT * FROM {fractal_table_name}_temp
        """)

        self._drop_fractal_table(f"{fractal_table_name}_temp")

    def _generate_cluster_data(self,
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

    def _generate_cent_dist(self, fractal_table_name: str):
        self.con.sql(f"""
            UPDATE {fractal_table_name}
            SET centDist = abs(cent - close)
        """)

    def _remove_outliers(self, fractal_table_name: str):

        self.con.sql(f"""
            CREATE TABLE {fractal_table_name}_temp AS
            SELECT * FROM {fractal_table_name}
            WHERE centDist <= {self.threshold}
        """)

        self._drop_fractal_table(fractal_table_name)

        self.con.sql(f"""
            CREATE TABLE {fractal_table_name} AS
            SELECT * FROM {fractal_table_name}_temp
        """)

        self._drop_fractal_table(f"{fractal_table_name}_temp")

    def _generate_cent_dist_lst_candle(self, fractal_table_name: str):
        self.con.sql(f"""
            UPDATE {fractal_table_name}
            SET centDistLstCandle = cent - lstCandlePrice
        """)

    def _generate_cent_count(self, fractal_table_name: str):
        self.con.sql(f"""
            UPDATE {fractal_table_name}
            SET centCount = sub.cnt
            FROM (
                SELECT
                    datetime,
                    COUNT(*) OVER (PARTITION BY clust) as cnt
                FROM {fractal_table_name}
            ) sub
            WHERE {fractal_table_name}.datetime = sub.datetime
        """)

    def _generate_idx_exp_mean(self, fractal_table_name: str):
        self.con.sql(f"""
            UPDATE {fractal_table_name}
            SET idxExpMean = sub.i_mean
            FROM (
                SELECT
                    datetime,
                    AVG(idxExp) OVER (PARTITION BY clust) as i_mean
                FROM {fractal_table_name}
            ) sub
            WHERE {fractal_table_name}.datetime = sub.datetime
        """)

    def _generate_score(self, fractal_table_name: str):
        self.con.sql(f"""
            UPDATE {fractal_table_name}
            SET score = (centCount * idxExpMean)
        """)

    def get_table(self, table_name: str):
        return self.con.sql(f"SELECT * FROM {table_name}")

    def build_fractal_clusters(self, fractal_table_name: str):

        self._generate_input_data(fractal_table_name)
        self._generate_last_candle_price(fractal_table_name)
        self._generate_index_data(fractal_table_name)
        self._generate_fractal_data(fractal_table_name)
        self._generate_cluster_data(fractal_table_name,
                                    self.params.get("candle_price_point"),
                                    self.params.get("cluster_count"))
        self._generate_cent_dist(fractal_table_name)
        self._remove_outliers(fractal_table_name)
        self._generate_cent_dist_lst_candle(fractal_table_name)
        self._generate_cent_count(fractal_table_name)
        self._generate_idx_exp_mean(fractal_table_name)
        self._generate_score(fractal_table_name)


instrument_params = {
    "data_source": "EOD",
    "instrument_name": "EURAUD",
    "timeframe": "d",
    "candle_price_point": "close",
    "fractal_period": 3,
    "cluster_count": 10,
    "outlier_threshold": 0.02
}
params = {
    "data_source": "EOD",
    "instruments": ["EURAUD"],
    "timeframes": ["d"],
    "candle_price_point": "close",
}

fractal_params = {
    "h": {
        "fractal_min": 2,
        "fractal_max": 72,
        "fractal_step": 7,
    },
    "d": {
        "fractal_min": 2,
        "fractal_max": 22,
        "fractal_step": 2,
    },
    "w": {
        "fractal_min": 2,
        "fractal_max": 12,
        "fractal_step": 1,
    },
    "m": {
        "fractal_min": 2,
        "fractal_max": 22,
        "fractal_step": 2,
    }
}

sr_params = {
    "h": {
        "sr_max": 50
    },
    "d": {
        "sr_max": 50
    },
    "w": {
        "sr_max": 20
    },
    "m": {
        "sr_max": 10
    }
}

cluster_params = {
    "cluster_min": 5,
    "cluster_max": 55,
    "cluster_step": 5,
    "outlier_threshold": 0.02
}


start_time = time.time()

data_foundation_builder = DataFoundationBuilder("./database/clarity.db",
                                                instrument_params)
data_foundation_builder.build_fractal_clusters("tbl_EOD_EURAUD_d_f3_k10")
data = data_foundation_builder.get_table("tbl_EOD_EURAUD_d_f3_k10")
print(data)
# data.write_csv("./outputs/fractal_data.csv")

end_time = time.time()
print(f"Time taken: {end_time - start_time} seconds")
