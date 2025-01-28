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
        self.timestamp = None
        self.date = None
        self.datetime = None
        self.cluster_count = cluster_count
        self.outlier_threshold = outlier_threshold
        self.candle_price_point = candle_price_point
        self.threshold = None
        self.last_close = None
        self.last_ema20 = None
        self.last_ema50 = None
        self.last_atr14 = None
        self.last_rsi14 = None
        self.last_macd_12_26_9 = None

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
                LIMIT {self.max_bars}
                OFFSET {self.window_position}
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
        self.window_position = window_position - 1

    def set_indicator_data(self):
        self.timestamp = self.con.sql(f"""
            SELECT timestamp
            FROM {self.working_table_name}
            ORDER BY timestamp DESC
            LIMIT 1
        """).fetchone()[0]

        self.date = self.con.sql(f"""
            SELECT date
            FROM {self.working_table_name}
            ORDER BY timestamp DESC
            LIMIT 1
        """).fetchone()[0]

        self.datetime = self.con.sql(f"""
            SELECT datetime
            FROM {self.working_table_name}
            ORDER BY timestamp DESC
            LIMIT 1
        """).fetchone()[0]

        self.last_close = self.con.sql(f"""
            SELECT close
            FROM {self.working_table_name}
            ORDER BY timestamp DESC
            LIMIT 1
        """).fetchone()[0]

        self.last_ema20 = self.con.sql(f"""
            SELECT ema20
            FROM {self.working_table_name}
            ORDER BY timestamp DESC
            LIMIT 1
        """).fetchone()[0]

        self.last_ema50 = self.con.sql(f"""
            SELECT ema50
            FROM {self.working_table_name}
            ORDER BY timestamp DESC
            LIMIT 1
        """).fetchone()[0]

        self.last_atr14 = self.con.sql(f"""
            SELECT atr14
            FROM {self.working_table_name}
            ORDER BY timestamp DESC
            LIMIT 1
        """).fetchone()[0]

        self.last_rsi14 = self.con.sql(f"""
            SELECT rsi14
            FROM {self.working_table_name}
            ORDER BY timestamp DESC
            LIMIT 1
        """).fetchone()[0]

        self.last_macd_12_26_9 = self.con.sql(f"""
            SELECT macd_12_26_9
            FROM {self.working_table_name}
            ORDER BY timestamp DESC
            LIMIT 1
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

    def generate_historical_sr(self):
        return self.con.sql(f"""
            WITH base_data AS (
                SELECT DISTINCT
                    '{self.instrument_name}' as instrument_name,
                    '{self.timeframe}' as timeframe,
                    {self.timestamp} as timestamp,
                    '{self.datetime}' as datetime,
                    {self.last_close} as close,
                FROM {self.working_table_name}
            ),
            positive_levels AS (
                SELECT DISTINCT
                    cent as cent_p1,
                    overallRank as overallRank_p1
                FROM {self.working_table_name}
                WHERE centDistLstCandleRank = 1
            ),
            negative_levels AS (
                SELECT DISTINCT
                    cent as cent_n1,
                    overallRank as overallRank_n1
                FROM {self.working_table_name}
                WHERE centDistLstCandleRank = -1
            )
            SELECT
                b.*,
                p.cent_p1,
                p.overallRank_p1,
                n.cent_n1,
                n.overallRank_n1
            FROM base_data b
            CROSS JOIN positive_levels p
            CROSS JOIN negative_levels n
        """)
