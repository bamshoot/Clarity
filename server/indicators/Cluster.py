import kmeans1d

from .DataFoundationBuilder import DataFoundationBuilder


class FractalCluster(DataFoundationBuilder):
    def __init__(self,
                 db_connection,
                 max_bars: int,
                 cluster_count: int,
                 outlier_threshold: float,
                 candle_price_point: str):
        super().__init__(db_connection)
        self.fractal_period = None
        self.max_bars = max_bars
        self.cluster_count = cluster_count
        self.outlier_threshold = outlier_threshold
        self.candle_price_point = candle_price_point
        self.threshold = None

    def create_fractal_table(self):
        self.con.sql(f"""
                CREATE TABLE {self.working_table_name} AS
                SELECT *
                FROM {self.source_table_name}
            """)

        self.con.sql(f"""
            CREATE TABLE {self.working_table_name}_temp AS
            SELECT * FROM {self.working_table_name}
            ORDER BY datetime DESC
            LIMIT {self.max_bars}
        """)

        self.drop_table(self.working_table_name)

        self.con.sql(f"""
            CREATE TABLE {self.working_table_name} AS
            SELECT * FROM {self.working_table_name}_temp
        """)

        self.drop_table(f"{self.working_table_name}_temp")

        self.con.sql(f"""
            ALTER TABLE {self.working_table_name}
            ADD COLUMN f INTEGER
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
        self.create_fractal_table()

    def set_fractal_period(self, fractal_period: int):
        self.fractal_period = fractal_period

    def set_threshold(self):
        self.threshold = self.con.sql(f"""
            SELECT (MAX(close) - MIN(close)) * {self.outlier_threshold}
            FROM {self.source_table_name}
        """).fetchone()[0]

    def generate_input_data(self):
        self.con.sql(f"""
            UPDATE {self.working_table_name}
            SET f = {self.fractal_period}
        """)
        self.con.sql(f"""
            UPDATE {self.working_table_name}
            SET k = {self.cluster_count}
        """)
        self.con.sql(f"""
            UPDATE {self.working_table_name}
            SET o = {self.outlier_threshold}
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

    def generate_cluster_data(self):

        df = self.con.sql(f"""
            SELECT *
            FROM {self.working_table_name}
            ORDER BY datetime
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
