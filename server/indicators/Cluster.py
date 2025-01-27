import kmeans1d

from .DataFoundationBuilder import DataFoundationBuilder


class Cluster(DataFoundationBuilder):
    def __init__(self,
                 db_connection,
                 max_bars: int,
                 cluster_count: int,
                 outlier_threshold: float,
                 candle_price_point: str):
        super().__init__(db_connection)
        self.sr_table_name = None
        self.fractal_period = None
        self.max_bars = max_bars
        self.window_position = None
        self.window_end = None
        self.date = None
        self.datetime = None
        self.window_start = None
        self.cluster_count = cluster_count
        self.outlier_threshold = outlier_threshold
        self.candle_price_point = candle_price_point
        self.threshold = None

    def create_sr_table(self):
        self.con.sql(f"""
            CREATE TABLE {self.working_table_name}
            (
                instrument_name VARCHAR,
                timeframe VARCHAR,
                clust INTEGER,
                cent DOUBLE,
                centDistMean DOUBLE,
                centCount DOUBLE,
                centDistLstCandle DOUBLE,
                centDistLstCandleRank DOUBLE,
                centDistMeanRank DOUBLE,
                centCountRank DOUBLE,
                score DOUBLE,
                overallRank DOUBLE
            )
        """)

    def create_cluster_table(self):
        self.con.sql(f"""
            CREATE TABLE {self.working_table_name} AS
            SELECT *
            FROM {self.source_table_name}
            ORDER BY datetime DESC
        """)
        self.con.sql(f"""
            ALTER TABLE {self.working_table_name}
            ADD COLUMN k INTEGER
        """)
        self.con.sql(f"""
            ALTER TABLE {self.working_table_name}
            ADD COLUMN o DOUBLE
        """)
        self.con.sql(f"""
            ALTER TABLE {self.working_table_name}
            ADD COLUMN clust INTEGER
        """)
        self.con.sql(f"""
            ALTER TABLE {self.working_table_name}
            ADD COLUMN cent DOUBLE
        """)
        self.con.sql(f"""
            ALTER TABLE {self.working_table_name}
            ADD COLUMN centDist DOUBLE
        """)
        self.con.sql(f"""
            ALTER TABLE {self.working_table_name}
            ADD COLUMN centDistMean DOUBLE
        """)
        self.con.sql(f"""
            ALTER TABLE {self.working_table_name}
            ADD COLUMN centDistMeanInv DOUBLE
        """)
        self.con.sql(f"""
            ALTER TABLE {self.working_table_name}
            ADD COLUMN centDistLstCandle DOUBLE
        """)
        self.con.sql(f"""
            ALTER TABLE {self.working_table_name}
            ADD COLUMN centCount DOUBLE
        """)
        self.con.sql(f"""
            ALTER TABLE {self.working_table_name}
            ADD COLUMN centDistMeanRank DOUBLE
        """)
        self.con.sql(f"""
            ALTER TABLE {self.working_table_name}
            ADD COLUMN centCountRank DOUBLE
        """)
        self.con.sql(f"""
            ALTER TABLE {self.working_table_name}
            ADD COLUMN centDistLstCandleRank DOUBLE
        """)
        self.con.sql(f"""
            ALTER TABLE {self.working_table_name}
            ADD COLUMN score DOUBLE
        """)
        self.con.sql(f"""
            ALTER TABLE {self.working_table_name}
            ADD COLUMN overallRank DOUBLE
        """)

    def reset_table(self):
        self.drop_table(self.working_table_name)
        self.create_cluster_table()

    def set_sr_table_name(self, sr_table_name: str):
        self.sr_table_name = sr_table_name

    def set_fractal_period(self, fractal_period: int):
        self.fractal_period = fractal_period

    def set_window_position(self, window_position: int):
        self.window_position = window_position

    def set_window_end(self):

        self.window_end = self.con.sql(f"""
            SELECT timestamp
            FROM {self.working_table_name}
            ORDER BY timestamp DESC
            LIMIT 1 OFFSET {self.window_position - 1}
        """).fetchone()[0]

        self.date = self.con.sql(f"""
            SELECT date
            FROM {self.working_table_name}
            ORDER BY timestamp DESC
            LIMIT 1 OFFSET {self.window_position - 1}
        """).fetchone()[0]

        self.datetime = self.con.sql(f"""
            SELECT datetime
            FROM {self.working_table_name}
            ORDER BY timestamp DESC
            LIMIT 1 OFFSET {self.window_position - 1}
        """).fetchone()[0]

    def set_window_start(self):

        table_length = self.con.sql(f"""
            SELECT COUNT(*)
            FROM {self.working_table_name}
        """).fetchone()[0]

        min_table_length_or_max_bars = min(table_length, self.max_bars)
        print(min_table_length_or_max_bars)

        self.window_start = self.con.sql(f"""
            SELECT timestamp
            FROM {self.working_table_name}
            ORDER BY timestamp DESC
            LIMIT 1
            OFFSET {(self.window_position - 1) + (min_table_length_or_max_bars - 1)}
        """).fetchone()[0]

    def set_threshold(self):
        self.threshold = self.con.sql(f"""
            SELECT (MAX(close) - MIN(close)) * {self.outlier_threshold}
            FROM {self.source_table_name}
        """).fetchone()[0]

    def generate_input_data(self):
        self.con.sql(f"""
            UPDATE {self.working_table_name}
            SET k = {self.cluster_count}
        """)
        self.con.sql(f"""
            UPDATE {self.working_table_name}
            SET o = {self.outlier_threshold}
        """)

    def generate_cluster_data(self):

        df = self.con.sql(f"""
            SELECT *
            FROM {self.working_table_name}
            WHERE timestamp >= {self.window_start} AND timestamp <= {self.window_end}
            ORDER BY timestamp ASC

        """).to_df()

        clusters, centroids = kmeans1d.cluster(df[self.candle_price_point],
                                               self.cluster_count)

        cent_clust = [centroids[clust] for clust in clusters]

        df['cent'] = cent_clust
        df['clust'] = clusters

        self.con.execute(f"DROP TABLE IF EXISTS {self.working_table_name}")
        self.con.execute(f"""
            CREATE TABLE {self.working_table_name} AS
            SELECT * FROM df
        """)

    def generate_cent_dist(self):
        self.con.sql(f"""
            UPDATE {self.working_table_name}
            SET centDist = abs(cent - close)
        """)

        self.con.sql(f"""
            UPDATE {self.working_table_name}
            SET centDistMean = sub.cent_dist_mean,
                centDistMeanInv = sub.cent_dist_mean_inv
            FROM (
                SELECT
                    datetime,
                    AVG(centDist) OVER (PARTITION BY clust) as cent_dist_mean,
                    AVG(1 / centDist) OVER (PARTITION BY clust) as cent_dist_mean_inv
                FROM {self.working_table_name}
            ) sub
            WHERE {self.working_table_name}.datetime = sub.datetime
        """)

    def remove_outliers(self):

        self.con.sql(f"""
            CREATE TABLE {self.working_table_name}_temp AS
            SELECT * FROM {self.working_table_name}
            WHERE centDist <= {self.threshold}
        """)

        self.drop_table(self.working_table_name)

        self.con.sql(f"""
            CREATE TABLE {self.working_table_name} AS
            SELECT * FROM {self.working_table_name}_temp
        """)

        self.drop_table(f"{self.working_table_name}_temp")

    def generate_cent_dist_lst_candle(self):
        self.con.sql(f"""
            UPDATE {self.working_table_name}
            SET centDistLstCandle = cent - lstCandlePrice
        """)

    def generate_cent_count(self):
        self.con.sql(f"""
            UPDATE {self.working_table_name}
            SET centCount = sub.cnt,
            FROM (
                SELECT
                    datetime,
                    COUNT(*) OVER (PARTITION BY clust) as cnt,
                FROM {self.working_table_name}
            ) sub
            WHERE {self.working_table_name}.datetime = sub.datetime
        """)

    def generate_score(self):
        self.con.sql(f"""
            UPDATE {self.working_table_name}
            SET score = (centCount * centDistMeanInv)
        """)

    def generate_rank(self):
        self.con.sql(f"""
            UPDATE {self.working_table_name}
            SET centDistMeanRank = sub.cent_dist_mean_rank,
                centCountRank = sub.cent_count_rank
            FROM (
                SELECT
                    datetime,
                    DENSE_RANK() OVER (
                        ORDER BY centDistMean ASC) as cent_dist_mean_rank,
                    DENSE_RANK() OVER (
                        ORDER BY centCount DESC) as cent_count_rank,
                FROM {self.working_table_name}
            ) sub
            WHERE {self.working_table_name}.datetime = sub.datetime
        """)

        self.con.sql(f"""
            WITH pos AS (
                SELECT
                    datetime,
                    /* Rank positive values by ascending |centDistLstCandle| */
                    DENSE_RANK() OVER (ORDER BY ABS(centDistLstCandle)) AS rank_val
                FROM {self.working_table_name}
                WHERE centDistLstCandle > 0
            ),
            neg AS (
                SELECT
                    datetime,
                    /* Rank negative values by ascending |centDistLstCandle|,
                    then make it negative */
                    -DENSE_RANK() OVER (ORDER BY ABS(centDistLstCandle)) AS rank_val
                FROM {self.working_table_name}
                WHERE centDistLstCandle < 0
            ),
            all_ranks AS (
                /* Combine positive and negative ranks into one resultset */
                SELECT datetime, rank_val AS cent_dist_lst_candle_rank FROM pos
                UNION ALL
                SELECT datetime, rank_val AS cent_dist_lst_candle_rank FROM neg
            )
            UPDATE {self.working_table_name}
            SET centDistLstCandleRank = all_ranks.cent_dist_lst_candle_rank
            FROM all_ranks
            WHERE {self.working_table_name}.datetime = all_ranks.datetime;
        """)

        self.con.sql(f"""
            UPDATE {self.working_table_name}
            SET overallRank = (centDistMeanRank + centCountRank) / 2
        """)

    def select_data(self):
        return self.con.sql(f"""
            SELECT DISTINCT
                    '{self.date}' as date,
                    '{self.datetime}' as datetime,
                    {self.window_end} as window_end,
                    {self.window_start} as window_start,
                    '{self.instrument_name}' as instrument_name,
                    '{self.timeframe}' as timeframe,
                    clust,
                    cent,
                    centDistMean,
                    centCount,
                    centDistLstCandle,
                    centDistLstCandleRank,
                    centDistMeanRank,
                    centCountRank,
                    score,
                    overallRank
                FROM {self.working_table_name}
                WHERE ABS(centDistLstCandleRank) = 1

        """)
