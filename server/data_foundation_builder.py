import kmeans1d
import duckdb
import time


class DataFoundationBuilder:
    def __init__(self,
                 db_path: str,
                 data_source: str,
                 instrument_name: str,
                 timeframe: str,
                 max_bars: int,
                 fractal_period: int,
                 cluster_count: int,
                 outlier_threshold: float,
                 candle_price_point: str,
                 to_csv: bool = False):
        self.db_path = db_path
        self.con = duckdb.connect(self.db_path)
        self.data_source = data_source
        self.instrument_name = instrument_name
        self.timeframe = timeframe
        self.max_bars = max_bars
        self.fractal_period = fractal_period
        self.cluster_count = cluster_count
        self.outlier_threshold = outlier_threshold
        self.candle_price_point = candle_price_point
        self.to_csv = to_csv
        self.table_name = (f"tbl_{self.data_source}"
                           f"_{self.instrument_name}"
                           f"_{self.timeframe}")
        self.fractal_table_name = (f"{self.table_name}_"
                                   f"f{self.fractal_period}_"
                                   f"k{self.cluster_count}")
        self._reset_table(self.table_name, self.fractal_table_name)
        self.threshold = self.con.sql(f"""
            SELECT (MAX(close) - MIN(close)) * {self.outlier_threshold}
            FROM {self.table_name}
        """).fetchone()[0]

    def __del__(self):
        if hasattr(self, 'con'):
            self.con.close()

    def _to_csv(self, table_name: str):
        self.con.sql(f"""
            SELECT * FROM {table_name} ORDER BY datetime
        """).write_csv(f"./outputs/{table_name}.csv")

    def _get_table_from_db(self, table_name: str):
        return self.con.sql(f"SELECT * FROM {table_name} ORDER BY datetime")

    def _drop_fractal_table(self, table_name: str):
        self.con.sql(f"DROP TABLE IF EXISTS {table_name}")

    def _create_fractal_table(self, table_name: str, fractal_table_name: str):
        self.con.sql(
            f"CREATE TABLE {fractal_table_name} AS SELECT * FROM {table_name}")

    def _limit_bars(self, fractal_table_name: str, max_bars: int):
        self.con.sql(f"""
            CREATE TABLE {fractal_table_name}_temp AS
            SELECT * FROM {fractal_table_name}
            ORDER BY datetime DESC
            LIMIT {max_bars}
        """)

        self._drop_fractal_table(fractal_table_name)

        self.con.sql(f"""
            CREATE TABLE {fractal_table_name} AS
            SELECT * FROM {fractal_table_name}_temp
        """)
        self._drop_fractal_table(f"{fractal_table_name}_temp")

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
            ADD COLUMN centDistMean DOUBLE
        """)
        self.con.sql(f"""
            ALTER TABLE {fractal_table_name}
            ADD COLUMN centDistMeanInv DOUBLE
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
            ADD COLUMN centDistMeanRank DOUBLE
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
            ADD COLUMN score DOUBLE
        """)
        self.con.sql(f"""
            ALTER TABLE {fractal_table_name}
            ADD COLUMN overallRank DOUBLE
        """)

    def _reset_table(self, table_name: str, fractal_table_name: str):
        self._drop_fractal_table(fractal_table_name)
        self._create_fractal_table(table_name, fractal_table_name)
        self._limit_bars(fractal_table_name, self.max_bars)
        self._add_columns_to_fractal_table(fractal_table_name)

    def _generate_input_data(self, fractal_table_name: str):
        self.con.sql(f"""
            UPDATE {fractal_table_name}
            SET f = {self.fractal_period}
        """)
        self.con.sql(f"""
            UPDATE {fractal_table_name}
            SET k = {self.cluster_count}
        """)
        self.con.sql(f"""
            UPDATE {fractal_table_name}
            SET o = {self.outlier_threshold}
        """)

    def _generate_last_candle_price(self, fractal_table_name: str):
        if self.candle_price_point == "close":
            self.con.sql(f"""
                UPDATE {fractal_table_name}
                SET lstCandlePrice = (SELECT close FROM {fractal_table_name}
                                         ORDER BY date DESC LIMIT 1),
                    distLstCandle = abs((SELECT close FROM {fractal_table_name}
                                            ORDER BY date DESC LIMIT 1) - close)
            """)
        elif self.candle_price_point == "high_low":
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
                   row_number() OVER (ORDER BY date) - 1 AS idx_temp
            FROM {fractal_table_name}
        """)

        self.con.sql(f"""
            UPDATE {fractal_table_name}
            SET idx = {fractal_table_name}_temp.idx_temp,
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

        self.con.sql(f"""
            UPDATE {fractal_table_name}
            SET centDistMean = sub.cent_dist_mean,
                centDistMeanInv = sub.cent_dist_mean_inv
            FROM (
                SELECT
                    datetime,
                    AVG(centDist) OVER (PARTITION BY clust) as cent_dist_mean,
                    AVG(1 / centDist) OVER (PARTITION BY clust) as cent_dist_mean_inv
                FROM {fractal_table_name}
            ) sub
            WHERE {fractal_table_name}.datetime = sub.datetime
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
            SET centCount = sub.cnt,
            FROM (
                SELECT
                    datetime,
                    COUNT(*) OVER (PARTITION BY clust) as cnt,
                FROM {fractal_table_name}
            ) sub
            WHERE {fractal_table_name}.datetime = sub.datetime
        """)

    def _generate_score(self, fractal_table_name: str):
        self.con.sql(f"""
            UPDATE {fractal_table_name}
            SET score = (centCount * centDistMeanInv)
        """)

    def _generate_rank(self, fractal_table_name: str):
        self.con.sql(f"""
            UPDATE {fractal_table_name}
            SET centDistMeanRank = sub.cent_dist_mean_rank,
                centCountRank = sub.cent_count_rank
            FROM (
                SELECT
                    datetime,
                    DENSE_RANK() OVER (
                        ORDER BY centDistMean ASC) as cent_dist_mean_rank,
                    DENSE_RANK() OVER (
                        ORDER BY centCount DESC) as cent_count_rank,
                FROM {fractal_table_name}
            ) sub
            WHERE {fractal_table_name}.datetime = sub.datetime
        """)

        self.con.sql(f"""
            WITH pos AS (
                SELECT
                    datetime,
                    /* Rank positive values by ascending |centDistLstCandle| */
                    DENSE_RANK() OVER (ORDER BY ABS(centDistLstCandle)) AS rank_val
                FROM {fractal_table_name}
                WHERE centDistLstCandle > 0
            ),
            neg AS (
                SELECT
                    datetime,
                    /* Rank negative values by ascending |centDistLstCandle|,
                    then make it negative */
                    -DENSE_RANK() OVER (ORDER BY ABS(centDistLstCandle)) AS rank_val
                FROM {fractal_table_name}
                WHERE centDistLstCandle < 0
            ),
            all_ranks AS (
                /* Combine positive and negative ranks into one resultset */
                SELECT datetime, rank_val AS cent_dist_lst_candle_rank FROM pos
                UNION ALL
                SELECT datetime, rank_val AS cent_dist_lst_candle_rank FROM neg
            )
            UPDATE {fractal_table_name}
            SET centDistLstCandleRank = all_ranks.cent_dist_lst_candle_rank
            FROM all_ranks
            WHERE {fractal_table_name}.datetime = all_ranks.datetime;
        """)

        self.con.sql(f"""
            UPDATE {fractal_table_name}
            SET overallRank = (centDistMeanRank + centCountRank) / 2
        """)

    def get_table(self, table_name: str):
        return self.con.sql(f"SELECT * FROM {table_name}")

    def build_fractal_clusters(self, fractal_table_name: str):

        self._generate_input_data(fractal_table_name)
        self._generate_last_candle_price(fractal_table_name)
        self._generate_index_data(fractal_table_name)
        self._generate_fractal_data(fractal_table_name)
        self._generate_cluster_data(fractal_table_name,
                                    self.candle_price_point,
                                    self.cluster_count)
        self._generate_cent_dist(fractal_table_name)
        self._remove_outliers(fractal_table_name)
        self._generate_cent_dist_lst_candle(fractal_table_name)
        self._generate_cent_count(fractal_table_name)
        self._generate_score(fractal_table_name)
        self._generate_rank(fractal_table_name)
        if self.to_csv:
            self._to_csv(fractal_table_name)


params = {
    "data_source": "EOD",
    "instruments": [
        "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCHF", "USDCAD", "NZDUSD",
        "EURGBP", "EURJPY", "EURAUD", "EURCHF", "EURCAD", "EURNZD", "GBPJPY",
        "GBPAUD", "GBPCHF", "GBPCAD", "GBPNZD", "AUDJPY", "AUDCHF", "AUDCAD",
        "AUDNZD", "CHFJPY", "CADJPY", "NZDJPY", "CADCHF", "NZDCHF", "NZDCAD"],
    "timeframes": ["1h", "d", "w", "m"],
    "max_bars": 730,
    "candle_price_point": "close",
    "fractal_period": 2,
    "cluster_count": 10,
    "outlier_threshold": 0.02,
    "to_csv": True
}


start_time = time.time()

for instrument in params["instruments"]:

    for timeframe in params["timeframes"]:

        fractal_table_name = (f"tbl_EOD_{instrument}_"
                              f"{timeframe}_"
                              f"f{params['fractal_period']}_"
                              f"k{params['cluster_count']}")

        print(f"Building {fractal_table_name}")

        data_foundation_builder = DataFoundationBuilder(
                    "./database/clarity.db",
                    "EOD",
                    instrument,
                    timeframe,
                    params["max_bars"],
                    params["fractal_period"],
                    params["cluster_count"],
                    params["outlier_threshold"],
                    params["candle_price_point"],
                    params["to_csv"])

        data_foundation_builder.build_fractal_clusters(fractal_table_name)

end_time = time.time()
print(f"Time taken: {end_time - start_time} seconds")
