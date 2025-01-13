import kmeans1d
import duckdb
import time
import os
import talib as ta
import json
from services.eod_data import EODData
from config.config import Config
import asyncio


class DataFoundationBuilder:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.con = duckdb.connect(self.db_path)
        self.data_source = None
        self.instrument_name = None
        self.timeframe = None
        self.source_table_name = None
        self.working_table_name = None
        self.output_folder = None

    def __del__(self):
        if hasattr(self, 'con'):
            self.con.close()

    def get_table_from_db(self, table_name: str):
        return self.con.sql(f"SELECT * FROM {table_name}")

    def drop_table(self, table_name: str):
        self.con.sql(f"DROP TABLE IF EXISTS {table_name}")

    def set_data_source(self, data_source: str):
        self.data_source = data_source

    def set_instrument_name(self, instrument_name: str):
        self.instrument_name = instrument_name

    def set_timeframe(self, timeframe: str):
        self.timeframe = timeframe

    def set_source_table_name(self, source_table_name: str):
        self.source_table_name = source_table_name

    def set_working_table_name(self, working_table_name: str):
        self.working_table_name = working_table_name

    def set_output_folder(self, output_folder: str):
        self.output_folder = output_folder

    def to_csv(self, table_name: str):
        self.con.sql(f"""
            SELECT * FROM {table_name}
        """).write_csv(f"outputs/{self.output_folder}/{table_name}.csv")


class FractalClusterBuilder(DataFoundationBuilder):
    def __init__(self,
                 db_path: str,
                 max_bars: int,
                 cluster_count: int,
                 outlier_threshold: float,
                 candle_price_point: str):
        super().__init__(db_path)
        self.fractal_period = None
        self.max_bars = max_bars
        self.cluster_count = cluster_count
        self.outlier_threshold = outlier_threshold
        self.candle_price_point = candle_price_point
        self.threshold = None

    def get_table_from_db(self, table_name: str):
        return self.con.sql(f"SELECT * FROM {table_name} ORDER BY datetime")

    def create_fractal_table(self):
        self.con.sql(
            f"""
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

        # print(self.con.sql(f"""
        #     SELECT COUNT(*) FROM {self.working_table_name}_temp
        # """).fetchone()[0])

        self.drop_table(f"{self.working_table_name}")

        self.con.sql(f"""
            CREATE TABLE {self.working_table_name} AS
            SELECT * FROM {self.working_table_name}_temp
        """)

        self.drop_table(f"{self.working_table_name}_temp")

    def generate_cluster_data(self):

        df = self.get_table_from_db(self.working_table_name).to_df()

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


class SupportResistanceBuilder(DataFoundationBuilder):
    def __init__(self, db_path: str):
        super().__init__(db_path)
        self.fractal_period = None
        self.cluster_count = None
        self.working_table_name = (f"tbl_{self.data_source}_SupportResistance")

    def create_table(self):
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

    def set_fractal_period(self, fractal_period: int):
        self.fractal_period = fractal_period

    def set_cluster_count(self, cluster_count: int):
        self.cluster_count = cluster_count

    def append_data_to_table(self):
        query = f"""
            INSERT INTO {self.working_table_name}
            SELECT DISTINCT
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
            FROM {self.source_table_name}
        """
        self.con.execute(query)


class PinescriptBuilder(DataFoundationBuilder):
    def __init__(self, db_path: str):
        super().__init__(db_path)

    def _reset_pinescript_file(self):
        for file in os.listdir(f"./outputs/{self.output_folder}"):
            with open(f"./outputs/{self.output_folder}/{file}", "w") as f:
                instrument_name = file.split("_")[1]
                instrument_name = instrument_name.replace(".txt", "")
                f.write(f"""
// This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0
// at https://mozilla.org/MPL/2.0/
// © bamshoot

//@version=6
indicator("{instrument_name} Support And Resistance", overlay = true)

show_1h = input(defval = true, title = "Show 1 Hour SR")
show_d = input(defval = true, title = "Show Daily SR")
show_w = input(defval = true, title = "Show Weekly SR")
show_m = input(defval = true, title = "Show Monthly SR")
show_label = input(defval = true, title = "Show Labels")
label_position = input(defval = 400, title ="Label Back Position")

symbol = syminfo.ticker

""")

    def build_pinescript(self, table_name: str):
        self._reset_pinescript_file()

        sr = self.get_table_from_db(table_name).fetchall()

        show_timeframe = None
        color = None

        for row in sr:

            instrument_name = row[0]

            if row[1] == "1h":
                show_timeframe = "show_1h"
                color = "color.yellow"
            elif row[1] == "d":
                show_timeframe = "show_d"
                color = "color.blue"
            elif row[1] == "w":
                show_timeframe = "show_w"
                color = "color.orange"
            elif row[1] == "m":
                show_timeframe = "show_m"
                color = "color.red"

            file_name = f"{self.data_source}_{instrument_name}"

            with open(f"./outputs/{self.output_folder}/{file_name}.txt", "a") as f:
                f.write(f"""plot({show_timeframe} and"""
                        f""" symbol == '{row[0]}'?{row[3]:.4f}:na,"""
                        f""" "Cluster = {row[2]}","""
                        f""" color = {color},"""
                        f""" editable = true)\n"""
                        f"""if (bar_index == last_bar_index) and show_label"""
                        f""" and {show_timeframe}\n"""
                        f"""    label.new(x=bar_index-label_position, """
                        f"""y={row[3]:.4f}, """
                        f"""text = str.tostring({row[3]:.4f}), color={color}, """
                        f"""textcolor=color.white, tooltip = "Cent Distance Mean = """
                        f"""{row[4]:.4f}\\nCent Count = {row[5]}\\nCent """
                        f"""Distance Mean Rank = {row[8]}\\nCent Count Rank = """
                        f"""{row[9]}\\nScore = {row[10]:.4f}\\n"""
                        f"""Overall Rank = {row[11]}")\n""")


class TrendIndicatorBuilder(DataFoundationBuilder):
    def __init__(self, db_path: str):
        super().__init__(db_path)
        self.params_table_name = "tbl_trend_params"

    def reset_trends_table(self):
        self.drop_table(self.params_table_name)
        self.drop_table(self.working_table_name)
        self._create_trend_params_table_from_json()
        self._create_trends_table()

    def _create_trend_params_table_from_json(self):
        with open("./config/settings/trends.json", "r") as f:
            trend_params = json.load(f)

        self.con.sql(f"""
            CREATE TABLE {self.params_table_name}
            (
                trend_id VARCHAR,
                major_trend_slope_type VARCHAR,
                trend_slope_type VARCHAR,
                run_slope_type VARCHAR,
                major_trend_to_trend VARCHAR,
                trend_to_run VARCHAR,
                status VARCHAR,
                bias VARCHAR,
                objective_status VARCHAR,
                rank_bias VARCHAR,
                rank_major_trend_to_trend VARCHAR,
                rank_trend_to_run VARCHAR,
                overall_rank VARCHAR
            )
        """)

        for trend_id, trend_params in trend_params.items():
            self.con.sql(f"""
                INSERT INTO {self.params_table_name}
                VALUES ('{trend_id}',
                        '{trend_params['major_trend_slope_type']}',
                        '{trend_params['trend_slope_type']}',
                        '{trend_params['run_slope_type']}',
                        '{trend_params['major_trend_to_trend']}',
                        '{trend_params['trend_to_run']}',
                        '{trend_params['status']}',
                        '{trend_params['bias']}',
                        '{trend_params['objective_status']}',
                        '{trend_params['rank_bias']}',
                        '{trend_params['rank_major_trend_to_trend']}',
                        '{trend_params['rank_trend_to_run']}',
                        '{trend_params['overall_rank']}')
            """)

    def _create_trends_table(self):
        self.con.sql(f"""
            CREATE TABLE {self.working_table_name}
            (
                instrument_name VARCHAR,
                timeframe VARCHAR,
                trend_id VARCHAR,
                major_trend_slope_value DOUBLE,
                trend_slope_value DOUBLE,
                run_slope_value DOUBLE,
                major_trend_slope_type VARCHAR,
                trend_slope_type VARCHAR,
                run_slope_type VARCHAR,
                major_trend_to_trend VARCHAR,
                trend_to_run VARCHAR,
                status VARCHAR,
                bias VARCHAR,
                objective_status VARCHAR,
                rank_bias VARCHAR,
                rank_major_trend_to_trend VARCHAR,
                rank_trend_to_run VARCHAR,
                overall_rank VARCHAR
            )
        """)

    def set_working_table_name(self, working_table_name: str):
        self.working_table_name = working_table_name

    def _append_instrument_trends(self,
                                  trend_id,
                                  major_trend_slope_value,
                                  trend_slope_value,
                                  run_slope_value):
        self.con.sql(f"""
            WITH trend_params AS (
                SELECT major_trend_slope_type, trend_slope_type, run_slope_type,
                       major_trend_to_trend, trend_to_run, status, bias,
                       objective_status, rank_bias, rank_major_trend_to_trend,
                       rank_trend_to_run, overall_rank
                FROM tbl_trend_params
                WHERE trend_id = '{trend_id}'
            )
            INSERT INTO {self.working_table_name}
            SELECT '{self.instrument_name}' as instrument_name,
                   '{self.timeframe}' as timeframe,
                   '{trend_id}' as trend_id,
                   {major_trend_slope_value}, {trend_slope_value}, {run_slope_value},
                   major_trend_slope_type, trend_slope_type, run_slope_type,
                   major_trend_to_trend, trend_to_run, status, bias,
                   objective_status, rank_bias, rank_major_trend_to_trend,
                   rank_trend_to_run, overall_rank
            FROM trend_params
        """)

    def generate_trends(self):

        run_length = 9
        trend_length = 20
        major_trend_length = 50
        run_threshold = 15
        trend_threshold = 5
        major_trend_threshold = 5

        data = self.get_table_from_db(self.source_table_name).fetchnumpy()

        close_prices = data['close']
        high_prices = data['high']
        low_prices = data['low']

        atr = ta.ATR(high_prices, low_prices, close_prices, 14)

        sma_major_trend = ta.SMA(close_prices, major_trend_length)
        sma_trend = ta.SMA(close_prices, trend_length)
        sma_run = ta.SMA(close_prices, run_length)

        slope_major_trend = round((ta.LINEARREG_SLOPE(
            sma_major_trend, 2)[-1]/atr[-1])*100, 2)
        slope_trend = round((ta.LINEARREG_SLOPE(
            sma_trend, 2)[-1]/atr[-1])*100, 2)
        slope_run = round((ta.LINEARREG_SLOPE(
            sma_run, 2)[-1]/atr[-1])*100, 2)

        major_trend_slope_type = None
        trend_slope_type = None
        run_slope_type = None

        if slope_major_trend > major_trend_threshold:
            major_trend_slope_type = "Up"
        elif slope_major_trend < -major_trend_threshold:
            major_trend_slope_type = "Down"

        if slope_trend > trend_threshold:
            trend_slope_type = "Up"
        elif slope_trend < -trend_threshold:
            trend_slope_type = "Down"

        if slope_run > run_threshold:
            run_slope_type = "Up"
        elif slope_run < -run_threshold:
            run_slope_type = "Down"

        trend_id = f"{major_trend_slope_type}{trend_slope_type}{run_slope_type}"

        self._append_instrument_trends(trend_id,
                                       slope_major_trend,
                                       slope_trend,
                                       slope_run)


class PriceProximityBuilder:
    def __init__(self, db_path: str, data_source: str):
        self.db_path = db_path
        self.con = duckdb.connect(self.db_path)
        self.data_source = data_source
        self.instrument_name = None
        self.exchange = None
        self.timeframe = None
        self.source_table_name = None
        self.sr_table_name = f"tbl_{self.data_source}_SupportResistance"
        self.table_name = (f"tbl_{self.data_source}_PriceProximity")
        self._reset_price_proximity_table()
        config = Config()
        self.eod_data_service = EODData(config.EOD_URL, config.EOD_API_KEY)

    def __del__(self):
        if hasattr(self, 'con'):
            self.con.close()

    def _get_table_from_db(self, table_name: str):
        return self.con.sql(f"SELECT * FROM {table_name}")

    def _reset_price_proximity_table(self):
        self._drop_table(self.table_name)
        self._create_price_proximity_table()

    def set_instrument_name(self, instrument_name: str):
        self.instrument_name = instrument_name

    def set_exchange(self, exchange: str):
        self.exchange = exchange

    def set_timeframe(self, timeframe: str):
        self.timeframe = timeframe

    def set_source_table_name(self):
        self.source_table_name = (f"tbl_{self.data_source}_"
                                  f"{self.instrument_name}_"
                                  f"{self.timeframe}")

    def _drop_table(self, table_name: str):
        self.con.sql(f"DROP TABLE IF EXISTS {table_name}")

    def _create_price_proximity_table(self):

        self.con.sql(f"""
            CREATE TABLE {self.table_name}
            AS SELECT * FROM {self.sr_table_name}
        """)
        self.con.sql(f"""
            ALTER TABLE {self.table_name} ADD COLUMN lst_price_timestamp BIGINT
        """)
        self.con.sql(f"""
            ALTER TABLE {self.table_name} ADD COLUMN lst_price DOUBLE
        """)
        self.con.sql(f"""
            ALTER TABLE {self.table_name} ADD COLUMN lst_price_cent_dist DOUBLE
        """)
        self.con.sql(f"""
            ALTER TABLE {self.table_name} ADD COLUMN atr DOUBLE
        """)
        self.con.sql(f"""
            ALTER TABLE {self.table_name} ADD COLUMN proximity DOUBLE
        """)

    async def _get_last_price(self):
        last_price = await self.eod_data_service.get_last_price(
            self.instrument_name,
            self.exchange)

        return last_price["timestamp"], last_price["close"]

    def _get_atr(self):
        data = self._get_table_from_db(self.source_table_name).fetchnumpy()
        atr = ta.ATR(data["high"], data["low"], data["close"], 14)
        return atr[-1]

    async def append_price_atr(self):

        timestamp, price = await self._get_last_price()
        atr = self._get_atr()

        self.con.sql(f"""
            UPDATE {self.table_name}
            SET lst_price_timestamp = {timestamp},
                lst_price = {price},
                atr = {atr}
            WHERE instrument_name = '{self.instrument_name}'
            AND timeframe = '{self.timeframe}'
        """)

    def calculate_price_proximity(self):

        self.con.sql(f"""
            UPDATE {self.table_name}
            SET lst_price_cent_dist = lst_price - cent,
                proximity = lst_price_cent_dist / atr
        """)

    def get_proximity_table(self):
        return self.con.sql(f"""
            SELECT * FROM {self.table_name}
        """)

    def to_csv(self, table_name: str):
        self.con.sql(f"""
            SELECT * FROM {table_name} ORDER BY instrument_name, timeframe
        """).write_csv(f"./outputs/price_proximity/{table_name}.csv")


class RSIRankBuilder:
    def __init__(self, db_path: str, data_source: str):
        self.db_path = db_path
        self.con = duckdb.connect(self.db_path)
        self.data_source = data_source
        self.instrument_name = None
        self.timeframe = None
        self.source_table_name = None
        self.pair_table_name = (f"tbl_{self.data_source}_pair_RSI_Rank")
        self.currency_table_name = (f"tbl_{self.data_source}_currency_RSI_Rank")
        self.currency_rsi_values = {
            'AUD': {'1h': [], 'd': [], 'w': [], 'm': []},
            'NZD': {'1h': [], 'd': [], 'w': [], 'm': []},
            'CAD': {'1h': [], 'd': [], 'w': [], 'm': []},
            'CHF': {'1h': [], 'd': [], 'w': [], 'm': []},
            'JPY': {'1h': [], 'd': [], 'w': [], 'm': []},
            'GBP': {'1h': [], 'd': [], 'w': [], 'm': []},
            'EUR': {'1h': [], 'd': [], 'w': [], 'm': []},
            'USD': {'1h': [], 'd': [], 'w': [], 'm': []}
        }
        self.currency_rsi_avg = {
            'AUD': {'1h': None, 'd': None, 'w': None, 'm': None},
            'NZD': {'1h': None, 'd': None, 'w': None, 'm': None},
            'CAD': {'1h': None, 'd': None, 'w': None, 'm': None},
            'CHF': {'1h': None, 'd': None, 'w': None, 'm': None},
            'JPY': {'1h': None, 'd': None, 'w': None, 'm': None},
            'GBP': {'1h': None, 'd': None, 'w': None, 'm': None},
            'EUR': {'1h': None, 'd': None, 'w': None, 'm': None},
            'USD': {'1h': None, 'd': None, 'w': None, 'm': None}
        }

    def __del__(self):
        if hasattr(self, 'con'):
            self.con.close()

    def _get_table_from_db(self, table_name: str):
        return self.con.sql(f"SELECT * FROM {table_name}")

    def reset_rsi_ranks_table(self):
        self._drop_table(self.pair_table_name)
        self._drop_table(self.currency_table_name)
        self._create_pair_rsi_ranks_table()
        self._create_currency_rsi_ranks_table()

    def _drop_table(self, table_name: str):
        self.con.sql(f"DROP TABLE IF EXISTS {table_name}")

    def set_instrument_name(self, instrument_name: str):
        self.instrument_name = instrument_name

    def set_timeframe(self, timeframe: str):
        self.timeframe = timeframe

    def set_source_table_name(self):
        self.source_table_name = (f"tbl_{self.data_source}_"
                                  f"{self.instrument_name}_"
                                  f"{self.timeframe}")

    def _create_pair_rsi_ranks_table(self):
        self.con.sql(f"""
            CREATE TABLE {self.pair_table_name}
            (
                instrument_name VARCHAR,
                base_currency VARCHAR,
                quote_currency VARCHAR,
                timeframe VARCHAR,
                lst_price_datetime DATETIME,
                pair_rsi DOUBLE,
                base_rsi DOUBLE,
                quote_rsi DOUBLE,
                pair_timeframe_rank INTEGER,
                base_timeframe_rank INTEGER,
                quote_timeframe_rank INTEGER
            )
        """)

    def _create_currency_rsi_ranks_table(self):
        self.con.sql(f"""
            CREATE TABLE {self.currency_table_name}
            (
                currency VARCHAR,
                timeframe VARCHAR,
                rsi DOUBLE,
                rank INTEGER
            )
        """)

    def generate_rsi(self):
        data = self._get_table_from_db(self.source_table_name).fetchnumpy()
        rsi = ta.RSI(data["close"], 14)
        lst_price_datetime = data["datetime"][-1]

        base_currency = self.instrument_name[:3]
        quote_currency = self.instrument_name[3:]

        if base_currency in self.currency_rsi_values:
            if self.timeframe in self.currency_rsi_values[base_currency]:
                self.currency_rsi_values[base_currency][self.timeframe].append(rsi[-1])

        if quote_currency in self.currency_rsi_values:
            if self.timeframe in self.currency_rsi_values[quote_currency]:
                self.currency_rsi_values[quote_currency][self.timeframe].append(rsi[-1])

        self.con.sql(f"""
            INSERT INTO {self.pair_table_name}
            (instrument_name, base_currency, quote_currency, timeframe,
             lst_price_datetime, pair_rsi)
            VALUES
            ('{self.instrument_name}', '{base_currency}', '{quote_currency}',
             '{self.timeframe}', '{lst_price_datetime}', {rsi[-1]})
        """)

    def generate_pair_timeframe_rank(self):
        self.con.sql(f"""
            UPDATE {self.pair_table_name} t1
            SET pair_timeframe_rank = (
                SELECT rank
                FROM (
                    SELECT
                        instrument_name,
                        timeframe,
                        DENSE_RANK() OVER (
                            PARTITION BY timeframe
                            ORDER BY pair_rsi DESC
                        ) as rank
                    FROM {self.pair_table_name}
                ) rankings
                WHERE rankings.instrument_name = t1.instrument_name
                AND rankings.timeframe = t1.timeframe
            )
        """)

    def generate_currency_rsi(self):
        for currency in self.currency_rsi_values:
            for timeframe in self.currency_rsi_values[currency]:
                try:
                    self.currency_rsi_avg[currency][timeframe] = (
                        sum(self.currency_rsi_values[currency][timeframe]) /
                        len(self.currency_rsi_values[currency][timeframe]))
                    self.con.sql(f"""
                        INSERT INTO {self.currency_table_name}
                        (currency, timeframe, rsi)
                        VALUES
                        ('{currency}',
                        '{timeframe}',
                        {self.currency_rsi_avg[currency][timeframe]})
                    """)
                except ZeroDivisionError:
                    self.currency_rsi_avg[currency][timeframe] = None

        self.con.sql(f"""
            UPDATE {self.currency_table_name} t1
            SET rank = (
                SELECT rank
                FROM (
                    SELECT currency,
                           timeframe,
                           DENSE_RANK() OVER (
                               PARTITION BY timeframe ORDER BY rsi DESC) as rank
                    FROM {self.currency_table_name}
                ) rankings
                WHERE rankings.currency = t1.currency
                    AND rankings.timeframe = t1.timeframe
            )
        """)

    def generate_base_quote_timeframe_rank(self):
        self.con.sql(f"""
            UPDATE {self.pair_table_name} t1
            SET base_rsi = (
                SELECT rsi
                FROM {self.currency_table_name}
                WHERE currency = t1.base_currency AND timeframe = t1.timeframe
            )
        """)
        self.con.sql(f"""
            UPDATE {self.pair_table_name} t1
            SET quote_rsi = (
                SELECT rsi
                FROM {self.currency_table_name}
                WHERE currency = t1.quote_currency AND timeframe = t1.timeframe
            )
        """)
        self.con.sql(f"""
            UPDATE {self.pair_table_name} t1
            SET base_timeframe_rank = (
                SELECT rank
                FROM {self.currency_table_name}
                WHERE currency = t1.base_currency AND timeframe = t1.timeframe
            )
        """)
        self.con.sql(f"""
            UPDATE {self.pair_table_name} t1
            SET quote_timeframe_rank = (
                SELECT rank
                FROM {self.currency_table_name}
                WHERE currency = t1.quote_currency AND timeframe = t1.timeframe
            )
        """)

    def get_table(self, table_name: str):
        return self.con.sql(f"""
            SELECT * FROM {table_name}
        """)

    def to_csv(self, table_name: str):
        self.con.sql(f"""
            SELECT * FROM {table_name}""").write_csv(f"./outputs/rsi/{table_name}.csv")


class MACDPriceConvergenceDivergenceBuilder:
    def __init__(self, db_path: str, data_source: str):
        self.db_path = db_path
        self.con = duckdb.connect(self.db_path)
        self.data_source = data_source
        self.instrument_name = None
        self.timeframe = None
        self.source_table_name = None
        self.table_name = (f"tbl_{self.data_source}_"
                           f"macd_price_convergence_divergence")
        self.reset_macd_convergence_divergence_table()

    def __del__(self):
        if hasattr(self, 'con'):
            self.con.close()

    def _get_table_from_db(self, table_name: str):
        return self.con.sql(f"SELECT * FROM {table_name}")

    def reset_macd_convergence_divergence_table(self):
        self._drop_table(self.table_name)
        self._create_macd_convergence_divergence_table()

    def _drop_table(self, table_name: str):
        self.con.sql(f"DROP TABLE IF EXISTS {table_name}")

    def _create_macd_convergence_divergence_table(self):
        self.con.sql(f"""
            CREATE TABLE {self.table_name}
            (
                instrument_name VARCHAR,
                timeframe VARCHAR,
                macd_price_cd DOUBLE,
                status VARCHAR
            )
        """)

    def set_instrument_name(self, instrument_name: str):
        self.instrument_name = instrument_name

    def set_timeframe(self, timeframe: str):
        self.timeframe = timeframe

    def set_source_table_name(self):
        self.source_table_name = (f"tbl_{self.data_source}_"
                                  f"{self.instrument_name}_"
                                  f"{self.timeframe}")

    def generate_macd_convergence_divergence(self):
        data = self._get_table_from_db(self.source_table_name).fetchnumpy()

        slope_length = 5

        close = data["close"]
        smoothed_close = ta.EMA(close, 20)
        macd, macd_signal, macd_hist = ta.MACD(close, 12, 26, 9)

        atr = ta.ATR(data["high"], data["low"], data["close"], 14)
        slope_close = (ta.LINEARREG_SLOPE(smoothed_close, slope_length)[-1]/atr[-1])*100
        slope_macd = (ta.LINEARREG_SLOPE(macd, slope_length)[-1]/atr[-1])*100

        macd_price_cd = slope_close - slope_macd

        if macd_price_cd > 5:
            status = "bullish divergence"
        elif macd_price_cd < -5:
            status = "bearish divergence"
        else:
            status = "convergence"

        self.con.sql(f"""
            INSERT INTO {self.table_name}
                (instrument_name, timeframe, macd_price_cd, status)
            VALUES ('{self.instrument_name}',
                    '{self.timeframe}',
                     {macd_price_cd},
                    '{status}')
        """)

    def get_table(self, table_name: str):
        return self.con.sql(f"""
            SELECT * FROM {table_name}
        """)

    def to_csv(self, table_name: str):
        self.con.sql(f"""
            SELECT * FROM {table_name}""").write_csv(
                f"./outputs/macd_price_cd/{table_name}.csv")


class PatternConvergenceDivergenceBuilder:

    def __init__(self, db_path: str, data_source: str):
        self.db_path = db_path
        self.con = duckdb.connect(self.db_path)
        self.data_source = data_source
        self.instrument_name = None
        self.timeframe = None
        self.fractal_period = None
        self.cluster_count = None
        self.atr_threshold = None
        self.source_table_name = None
        self.table_name = (f"tbl_{self.data_source}_"
                           f"pattern_convergence_divergence")

    def __del__(self):
        if hasattr(self, 'con'):
            self.con.close()

    def _get_table_from_db(self, table_name: str):
        return self.con.sql(f"SELECT * FROM {table_name}")

    def _drop_table(self, table_name: str):
        self.con.sql(f"DROP TABLE IF EXISTS {table_name}")

    def reset_pattern_convergence_divergence_table(self):
        self._drop_table(self.table_name)
        self._create_pattern_convergence_divergence_table()

    def set_instrument_name(self, instrument_name: str):
        self.instrument_name = instrument_name

    def set_timeframe(self, timeframe: str):
        self.timeframe = timeframe

    def set_fractal_period(self, fractal_period: int):
        self.fractal_period = fractal_period

    def set_cluster_count(self, cluster_count: int):
        self.cluster_count = cluster_count

    def set_atr_threshold(self, atr_threshold: float):
        self.atr_threshold = atr_threshold

    def set_source_table_name(self):
        self.source_table_name = (f"tbl_{self.data_source}_"
                                  f"{self.instrument_name}_"
                                  f"{self.timeframe}_"
                                  f"f{self.fractal_period}_"
                                  f"k{self.cluster_count}")

    def _create_pattern_convergence_divergence_table(self):
        self.con.sql(f"""
            CREATE TABLE {self.table_name}
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

        data = self._get_table_from_db(self.source_table_name).fetchnumpy()
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
            INSERT INTO {self.table_name}
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
            UPDATE {self.table_name}
            SET
                first_lower_x = temp.first_lower_x,
                first_lower_y = temp.first_lower_y,
                second_lower_x = temp.second_lower_x,
                second_lower_y = temp.second_lower_y,
                third_lower_x = temp.third_lower_x,
                third_lower_y = temp.third_lower_y
            FROM temp_lf_transposed temp
            WHERE {self.table_name}.instrument_name = '{self.instrument_name}'
            AND {self.table_name}.timeframe = '{self.timeframe}'
            AND {self.table_name}.f = {self.fractal_period}
        """)

        self.con.sql(f"""
            UPDATE {self.table_name}
            SET max_first_x = GREATEST(first_upper_x, first_lower_x),
                min_third_x = LEAST(third_upper_x, third_lower_x)
            WHERE instrument_name = '{self.instrument_name}'
            AND timeframe = '{self.timeframe}'
            AND f = {self.fractal_period}
        """)

        self.con.sql(f"""
            UPDATE {self.table_name}
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
            UPDATE {self.table_name}
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
            UPDATE {self.table_name}
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
            UPDATE {self.table_name}
            SET
               max_first_y = GREATEST(max_price, min_price),
            FROM temp_union
            WHERE timestamp = max_first_x
        """)

        self.con.sql(f"""
            UPDATE {self.table_name}
            SET
               min_third_y = GREATEST(max_price, min_price),
            FROM temp_union
            WHERE timestamp = min_third_x
        """)

        self.con.sql(f"""
            UPDATE {self.table_name}
            SET
                dist_first = ABS(y_at_max_first_x - max_first_y),
                dist_third = ABS(y_at_min_third_x - min_third_y),
            WHERE instrument_name = '{self.instrument_name}'
            AND timeframe = '{self.timeframe}'
            AND f = {self.fractal_period}
        """)

        self.con.sql(f"""
            UPDATE {self.table_name}
            SET
                dist_upper_second = ABS(y_at_upper_second_x - second_upper_y),
                dist_lower_second = ABS(y_at_lower_second_x - second_lower_y),
            WHERE instrument_name = '{self.instrument_name}'
            AND timeframe = '{self.timeframe}'
            AND f = {self.fractal_period}
        """)

        self.con.sql(f"""
            UPDATE {self.table_name}
            SET
                upper_second_atr = dist_upper_second / atr *100,
                lower_second_atr = dist_lower_second / atr *100,
            WHERE instrument_name = '{self.instrument_name}'
            AND timeframe = '{self.timeframe}'
            AND f = {self.fractal_period}
        """)

        self.con.sql(f"""
            UPDATE {self.table_name}
            SET
                dist_third_lt_first = dist_third < dist_first,
                upper_second_within_atr = upper_second_atr < {self.atr_threshold},
                lower_second_within_atr = lower_second_atr < {self.atr_threshold}
            WHERE instrument_name = '{self.instrument_name}'
            AND timeframe = '{self.timeframe}'
            AND f = {self.fractal_period}
        """)

        self.con.sql(f"""
            UPDATE {self.table_name}
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

    def to_csv(self, table_name: str):
        self.con.sql(f"""
            SELECT * FROM {table_name}""").write_csv(
                f"./outputs/pattern_cd/{table_name}.csv")


class CandlePatternBuilder:
    def __init__(self, db_path: str, data_source: str, candle_patterns: dict):
        self.db_path = db_path
        self.con = duckdb.connect(self.db_path)
        self.data_source = data_source
        self.instrument_name = None
        self.timeframe = None
        self.source_table_name = None
        self.table_name = None
        self.candle_patterns = candle_patterns

    def __del__(self):
        if hasattr(self, 'con'):
            self.con.close()

    def get_table_from_db(self, table_name: str):
        return self.con.sql(f"SELECT * FROM {table_name}")

    def reset_candle_pattern_table(self):
        self._drop_table(self.table_name)
        self._create_candle_pattern_table()

    def _drop_table(self, table_name: str):
        self.con.sql(f"DROP TABLE IF EXISTS {table_name}")

    def _create_candle_pattern_table(self):
        self.con.sql(f"""
            CREATE TABLE {self.table_name} AS
            SELECT * FROM {self.source_table_name}
        """)

        self.con.sql(f"""
            ALTER TABLE {self.table_name}
            ADD COLUMN instrument_name VARCHAR
        """)
        self.con.sql(f"""
            ALTER TABLE {self.table_name}
            ADD COLUMN timeframe VARCHAR
        """)

        for pattern in self.candle_patterns:
            self.con.sql(f"""
                ALTER TABLE {self.table_name}
                ADD COLUMN {pattern} INTEGER
            """)

    def set_instrument_name(self, instrument_name: str):
        self.instrument_name = instrument_name

    def set_timeframe(self, timeframe: str):
        self.timeframe = timeframe

    def set_table_name(self):
        self.table_name = (f"tbl_{self.data_source}_{self.instrument_name}_"
                           f"{self.timeframe}_"
                           f"candle_patterns")

    def set_source_table_name(self):
        self.source_table_name = (f"tbl_{self.data_source}_"
                                  f"{self.instrument_name}_"
                                  f"{self.timeframe}")

    def generate_candle_patterns(self):
        data = self.get_table_from_db(self.table_name).fetchnumpy()

        for pattern_name, (_, func) in self.candle_patterns.items():
            print(f"Generating {pattern_name} "
                  f"for {self.instrument_name} "
                  f"{self.timeframe}")
            pattern_result = func(data['open'],
                                  data['high'],
                                  data['low'],
                                  data['close'])

            # Create a temporary table with the pattern values
            self.con.execute(f"""
                CREATE TEMP TABLE temp_patterns AS
                SELECT datetime,
                       UNNEST(?) as pattern_value
                FROM {self.table_name}
            """, [pattern_result.tolist()])

            # Update the main table using the temporary table
            self.con.execute(f"""
                UPDATE {self.table_name} t
                SET {pattern_name} = tp.pattern_value,
                    instrument_name = '{self.instrument_name}',
                    timeframe = '{self.timeframe}'
                FROM temp_patterns tp
                WHERE t.datetime = tp.datetime
            """)

            # Clean up temporary table
            self.con.execute("DROP TABLE IF EXISTS temp_patterns")

    def to_csv(self, table_name: str):
        self.con.sql(f"""
            SELECT * FROM {table_name}""").write_csv(
                f"./outputs/candle_patterns/{table_name}.csv")


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
    "fractal_period": {"1h": [2, 8], "d": [2], "w": [2], "m": [2]},
    "cluster_count": 10,
    "outlier_threshold": 0.02,
    "atr_threshold": 10,
    "to_csv": True
}

candlestick_patterns = {
    "CDL2CROWS": {"name": "Two Crows",
                  "type": "reversal",
                  "direction": "bear",
                  "func": ta.CDL2CROWS},
    "CDL3BLACKCROWS": {"name": "Three Black Crows",
                       "type": "reversal",
                       "direction": "bear",
                       "func": ta.CDL3BLACKCROWS},
    "CDL3INSIDE": {"name": "Three Inside Up/Down",
                   "type": "reversal",
                   "direction": "bull/bear",
                   "func": ta.CDL3INSIDE},
    "CDL3LINESTRIKE": {"name": "Three-Line Strike",
                       "type": "reversal",
                       "direction": "bull/bear",
                       "func": ta.CDL3LINESTRIKE},
    "CDL3OUTSIDE": {"name": "Three Outside Up/Down",
                    "type": "reversal",
                    "direction": "bull/bear",
                    "func": ta.CDL3OUTSIDE},
    "CDL3STARSINSOUTH": {"name": "Three Stars In The South",
                         "type": "reversal",
                         "direction": "bull",
                         "func": ta.CDL3STARSINSOUTH},
    "CDL3WHITESOLDIERS": {"name": "Three Advancing White Soldiers",
                          "type": "continuation",
                          "direction": "bull",
                          "func": ta.CDL3WHITESOLDIERS},
    "CDLABANDONEDBABY": {"name": "Abandoned Baby",
                         "type": "reversal",
                         "direction": "bull/bear",
                         "func": ta.CDLABANDONEDBABY},
    "CDLADVANCEBLOCK": {"name": "Advance Block",
                        "type": "continuation",
                        "direction": "bear",
                        "func": ta.CDLADVANCEBLOCK},
    "CDLBELTHOLD": {"name": "Belt-hold",
                    "type": "reversal",
                    "direction": "bull/bear",
                    "func": ta.CDLBELTHOLD},
    "CDLBREAKAWAY": {"name": "Breakaway",
                     "type": "reversal",
                     "direction": "bull/bear",
                     "func": ta.CDLBREAKAWAY},
    "CDLCLOSINGMARUBOZU": {"name": "Closing Marubozu",
                           "type": "continuation",
                           "direction": "bull/bear",
                           "func": ta.CDLCLOSINGMARUBOZU},
    "CDLCONCEALBABYSWALL": {"name": "Concealing Baby Swallow",
                            "type": "continuation",
                            "direction": "bear",
                            "func": ta.CDLCONCEALBABYSWALL},
    "CDLCOUNTERATTACK": {"name": "Counterattack",
                         "type": "reversal",
                         "direction": "bull/bear",
                         "func": ta.CDLCOUNTERATTACK},
    "CDLDARKCLOUDCOVER": {"name": "Dark Cloud Cover",
                          "type": "reversal",
                          "direction": "bear",
                          "func": ta.CDLDARKCLOUDCOVER},
    "CDLDOJI": {"name": "Doji",
                "type": "indecisive",
                "direction": "neutral",
                "func": ta.CDLDOJI},
    "CDLDOJISTAR": {"name": "Doji Star",
                    "type": "indecisive",
                    "direction": "neutral",
                    "func": ta.CDLDOJISTAR},
    "CDLDRAGONFLYDOJI": {"name": "Dragonfly Doji",
                         "type": "indecisive",
                         "direction": "neutral",
                         "func": ta.CDLDRAGONFLYDOJI},
    "CDLENGULFING": {"name": "Engulfing Pattern",
                     "type": "reversal",
                     "direction": "bull/bear",
                     "func": ta.CDLENGULFING},
    "CDLEVENINGDOJISTAR": {"name": "Evening Doji Star",
                           "type": "reversal",
                           "direction": "bear",
                           "func": ta.CDLEVENINGDOJISTAR},
    "CDLEVENINGSTAR": {"name": "Evening Star",
                       "type": "reversal",
                       "direction": "bear",
                       "func": ta.CDLEVENINGSTAR},
    "CDLGAPSIDESIDEWHITE": {"name": "Up/Down-gap side-by-side white lines",
                            "type": "continuation",
                            "direction": "bull/bear",
                            "func": ta.CDLGAPSIDESIDEWHITE},
    "CDLGRAVESTONEDOJI": {"name": "Gravestone Doji",
                          "type": "indecisive",
                          "direction": "neutral",
                          "func": ta.CDLGRAVESTONEDOJI},
    "CDLHAMMER": {"name": "Hammer",
                  "type": "reversal",
                  "direction": "bull",
                  "func": ta.CDLHAMMER},
    "CDLHANGINGMAN": {"name": "Hanging Man",
                      "type": "reversal",
                      "direction": "bear",
                      "func": ta.CDLHANGINGMAN},
    "CDLHARAMI": {"name": "Harami Pattern",
                  "type": "reversal",
                  "direction": "bull/bear",
                  "func": ta.CDLHARAMI},
    "CDLHARAMICROSS": {"name": "Harami Cross Pattern",
                       "type": "reversal",
                       "direction": "bull/bear",
                       "func": ta.CDLHARAMICROSS},
    "CDLHIGHWAVE": {"name": "High-Wave Candle",
                    "type": "indecisive",
                    "direction": "neutral",
                    "func": ta.CDLHIGHWAVE},
    "CDLHIKKAKE": {"name": "Hikkake Pattern",
                   "type": "continuation",
                   "direction": "bear",
                   "func": ta.CDLHIKKAKE},
    "CDLHIKKAKEMOD": {"name": "Modified Hikkake Pattern",
                      "type": "continuation",
                      "direction": "bear",
                      "func": ta.CDLHIKKAKEMOD},
    "CDLHOMINGPIGEON": {"name": "Homing Pigeon",
                        "type": "reversal",
                        "direction": "bull",
                        "func": ta.CDLHOMINGPIGEON},
    "CDLIDENTICAL3CROWS": {"name": "Identical Three Crows",
                           "type": "reversal",
                           "direction": "bear",
                           "func": ta.CDLIDENTICAL3CROWS},
    "CDLINNECK": {"name": "In-Neck Pattern",
                  "type": "continuation",
                  "direction": "bear",
                  "func": ta.CDLINNECK},
    "CDLINVERTEDHAMMER": {"name": "Inverted Hammer",
                          "type": "reversal",
                          "direction": "bull",
                          "func": ta.CDLINVERTEDHAMMER},
    "CDLKICKING": {"name": "Kicking",
                   "type": "continuation",
                   "direction": "bull/bear",
                   "func": ta.CDLKICKING},
    "CDLKICKINGBYLENGTH": {"name": "Kicking by Length",
                           "type": "continuation",
                           "direction": "bull/bear",
                           "func": ta.CDLKICKINGBYLENGTH},
    "CDLLADDERBOTTOM": {"name": "Ladder Bottom",
                        "type": "reversal",
                        "direction": "bull",
                        "func": ta.CDLLADDERBOTTOM},
    "CDLLONGLEGGEDDOJI": {"name": "Long Legged Doji",
                          "type": "indecisive",
                          "direction": "neutral",
                          "func": ta.CDLLONGLEGGEDDOJI},
    "CDLLONGLINE": {"name": "Long Line Candle",
                    "type": "continuation",
                    "direction": "bull/bear",
                    "func": ta.CDLLONGLINE},
    "CDLMARUBOZU": {"name": "Marubozu",
                    "type": "continuation",
                    "direction": "bull/bear",
                    "func": ta.CDLMARUBOZU},
    "CDLMATCHINGLOW": {"name": "Matching Low",
                       "type": "reversal",
                       "direction": "bull",
                       "func": ta.CDLMATCHINGLOW},
    "CDLMATHOLD": {"name": "Mat Hold",
                   "type": "continuation",
                   "direction": "bull",
                   "func": ta.CDLMATHOLD},
    "CDLMORNINGDOJISTAR": {"name": "Morning Doji Star",
                           "type": "reversal",
                           "direction": "bull",
                           "func": ta.CDLMORNINGDOJISTAR},
    "CDLMORNINGSTAR": {"name": "Morning Star",
                       "type": "reversal",
                       "direction": "bull",
                       "func": ta.CDLMORNINGSTAR},
    "CDLONNECK": {"name": "On-Neck Pattern",
                  "type": "continuation",
                  "direction": "bear",
                  "func": ta.CDLONNECK},
    "CDLPIERCING": {"name": "Piercing Pattern",
                    "type": "continuation",
                    "direction": "bull",
                    "func": ta.CDLPIERCING},
    "CDLRICKSHAWMAN": {"name": "Rickshaw Man",
                       "type": "indecisive",
                       "direction": "neutral",
                       "func": ta.CDLRICKSHAWMAN},
    "CDLRISEFALL3METHODS": {"name": "Rising/Falling Three Methods",
                            "type": "continuation",
                            "direction": "bull/bear",
                            "func": ta.CDLRISEFALL3METHODS},
    "CDLSEPARATINGLINES": {"name": "Separating Lines",
                           "type": "continuation",
                           "direction": "bull/bear",
                           "func": ta.CDLSEPARATINGLINES},
    "CDLSHOOTINGSTAR": {"name": "Shooting Star",
                        "type": "reversal",
                        "direction": "bear",
                        "func": ta.CDLSHOOTINGSTAR},
    "CDLSHORTLINE": {"name": "Short Line Candle",
                     "type": "indecisive",
                     "direction": "neutral",
                     "func": ta.CDLSHORTLINE},
    "CDLSPINNINGTOP": {"name": "Spinning Top",
                       "type": "indecisive",
                       "direction": "neutral",
                       "func": ta.CDLSPINNINGTOP},
    "CDLSTICKSANDWICH": {"name": "Stick Sandwich",
                         "type": "reversal",
                         "direction": "bull",
                         "func": ta.CDLSTICKSANDWICH},
    "CDLTAKURI": {"name": "Takuri",
                  "type": "reversal",
                  "direction": "bull",
                  "func": ta.CDLTAKURI},
    "CDLTASUKIGAP": {"name": "Tasuki Gap",
                     "type": "continuation",
                     "direction": "bull/bear",
                     "func": ta.CDLTASUKIGAP},
    "CDLTHRUSTING": {"name": "Thrusting Pattern",
                     "type": "continuation",
                     "direction": "bear",
                     "func": ta.CDLTHRUSTING},
    "CDLTRISTAR": {"name": "Tristar Pattern",
                   "type": "indecisive",
                   "direction": "neutral",
                   "func": ta.CDLTRISTAR},
    "CDLUNIQUE3RIVER": {"name": "Unique 3 River",
                        "type": "reversal",
                        "direction": "bull",
                        "func": ta.CDLUNIQUE3RIVER},
    "CDLUPSIDEGAP2CROWS": {"name": "Upside Gap Two Crows",
                           "type": "reversal",
                           "direction": "bear",
                           "func": ta.CDLUPSIDEGAP2CROWS},
    "CDLXSIDEGAP3METHODS": {"name": "Upside/Downside Gap Three Methods",
                            "type": "continuation",
                            "direction": "bull/bear",
                            "func": ta.CDLXSIDEGAP3METHODS}
}

start_time = time.time()

# print("Building data foundation")

# fractal_cluster_builder = FractalClusterBuilder(
#     "./database/clarity.db",
#     params["max_bars"],
#     params["cluster_count"],
#     params["outlier_threshold"],
#     params["candle_price_point"])

# for instrument in params["instruments"]:

#     for timeframe in params["timeframes"]:

#         for fractal_period in params["fractal_period"][timeframe]:

#             source_table_name = (f"tbl_{params['data_source']}_"
#                                  f"{instrument}_"
#                                  f"{timeframe}")

#             fractal_cluster_builder.set_source_table_name(source_table_name)

#             working_table_name = (f"tbl_{params['data_source']}_"
#                                   f"{instrument}_"
#                                   f"{timeframe}_"
#                                   f"f{fractal_period}_"
#                                   f"k{params['cluster_count']}")

#             fractal_cluster_builder.set_working_table_name(working_table_name)

#             print(f"Building {working_table_name}")

#             fractal_cluster_builder.reset_table()
#             fractal_cluster_builder.set_instrument_name(instrument)
#             fractal_cluster_builder.set_timeframe(timeframe)
#             fractal_cluster_builder.set_fractal_period(fractal_period)
#             fractal_cluster_builder.set_output_folder("fractals")
#             fractal_cluster_builder.set_threshold()
#             fractal_cluster_builder.generate_input_data()
#             fractal_cluster_builder.generate_last_candle_price()
#             fractal_cluster_builder.generate_index_data()
#             fractal_cluster_builder.generate_fractal_data()
#             fractal_cluster_builder.generate_cluster_data()
#             fractal_cluster_builder.generate_cent_dist()
#             fractal_cluster_builder.remove_outliers()
#             fractal_cluster_builder.generate_cent_dist_lst_candle()
#             fractal_cluster_builder.generate_cent_count()
#             fractal_cluster_builder.generate_score()
#             fractal_cluster_builder.generate_rank()

#             if params["to_csv"]:
#                 fractal_cluster_builder.to_csv(working_table_name)

# print("Building support resistance table")

# support_resistance_builder = SupportResistanceBuilder("./database/clarity.db")

# support_resistance_builder.set_data_source(params["data_source"])
# support_resistance_builder.set_working_table_name(f"tbl_{params['data_source']}_"
#                                                   f"Support_Resistance")
# support_resistance_builder.drop_table(support_resistance_builder.working_table_name)
# support_resistance_builder.create_table()

# for instrument in params["instruments"]:
#     for timeframe in params["timeframes"]:
#         source_table_name = (f"tbl_{params['data_source']}_"
#                              f"{instrument}_"
#                              f"{timeframe}_"
#                              f"f2_"
#                              f"k{params['cluster_count']}")

#         support_resistance_builder.set_source_table_name(source_table_name)
#         support_resistance_builder.set_instrument_name(instrument)
#         support_resistance_builder.set_timeframe(timeframe)
#         support_resistance_builder.set_output_folder("sr")
#         support_resistance_builder.set_fractal_period(2)
#         support_resistance_builder.set_cluster_count(params["cluster_count"])
#         support_resistance_builder.append_data_to_table()

# if params["to_csv"]:
#     support_resistance_builder.to_csv(support_resistance_builder.working_table_name)


# print("Building pinescript")

# pinescript_builder = PinescriptBuilder("./database/clarity.db")

# pinescript_builder.set_data_source(params["data_source"])
# pinescript_builder.set_output_folder("pinescript")
# pinescript_builder.set_source_table_name(f"tbl_{params['data_source']}_"
#                                          f"Support_Resistance")

# pinescript_builder.build_pinescript(pinescript_builder.source_table_name)

# print("Building trend indicator")

# trend_indicator_builder = TrendIndicatorBuilder("./database/clarity.db")
# trend_indicator_builder.set_data_source(params["data_source"])
# trend_indicator_builder.set_output_folder("trends")
# trend_indicator_builder.set_source_table_name("tbl_trend_params")
# trend_indicator_builder.set_working_table_name(f"tbl_{params['data_source']}_Trends")
# trend_indicator_builder.reset_trends_table()

# for instrument in params["instruments"]:
#     for timeframe in params["timeframes"]:
#         trend_indicator_builder.set_instrument_name(instrument)
#         trend_indicator_builder.set_timeframe(timeframe)
#         trend_indicator_builder.set_source_table_name(f"tbl_{params['data_source']}_"
#                                                       f"{instrument}_"
#                                                       f"{timeframe}")
#         trend_indicator_builder.generate_trends()

# if params["to_csv"]:
#     trend_indicator_builder.to_csv(trend_indicator_builder.working_table_name)

print("Building price proximity")


async def process_all_instruments():
    price_proximity_builder = PriceProximityBuilder("./database/clarity.db", "EOD")

    for instrument in params["instruments"]:
        for timeframe in params["timeframes"]:
            print(f"Building {instrument} {timeframe}")
            price_proximity_builder.set_instrument_name(instrument)
            price_proximity_builder.set_exchange("FOREX")
            price_proximity_builder.set_timeframe(timeframe)
            price_proximity_builder.set_source_table_name()
            await price_proximity_builder.append_price_atr()
            price_proximity_builder.calculate_price_proximity()

    if params["to_csv"]:
        price_proximity_builder.to_csv(price_proximity_builder.table_name)

# Replace the loop with:
asyncio.run(process_all_instruments())

# print("Building RSI ranks")

# rsi_rank_builder = RSIRankBuilder("./database/clarity.db", "EOD")
# rsi_rank_builder.reset_rsi_ranks_table()

# for instrument in params["instruments"]:
#     for timeframe in params["timeframes"]:
#         print(f"Building {instrument} {timeframe}")
#         rsi_rank_builder.set_instrument_name(instrument)
#         rsi_rank_builder.set_timeframe(timeframe)
#         rsi_rank_builder.set_source_table_name()
#         rsi_rank_builder.generate_rsi()

# rsi_rank_builder.generate_pair_timeframe_rank()
# rsi_rank_builder.generate_currency_rsi()
# rsi_rank_builder.generate_base_quote_timeframe_rank()

# if params["to_csv"]:
#     rsi_rank_builder.to_csv(rsi_rank_builder.pair_table_name)
#     rsi_rank_builder.to_csv(rsi_rank_builder.currency_table_name)

# print("Building MACD Price Convergence Divergence")

# macd_price_cd_builder = MACDPriceConvergenceDivergenceBuilder(
#     "./database/clarity.db", "EOD")
# for instrument in params["instruments"]:
#     for timeframe in params["timeframes"]:
#         macd_price_cd_builder.set_instrument_name(instrument)
#         macd_price_cd_builder.set_timeframe(timeframe)
#         macd_price_cd_builder.set_source_table_name()
#         macd_price_cd_builder.generate_macd_convergence_divergence()

# if params["to_csv"]:
#     macd_price_cd_builder.to_csv(macd_price_cd_builder.table_name)


# print("Building candle patterns")
# candle_pattern_builder = CandlePatternBuilder(
#     "./database/clarity.db", "EOD", candle_patterns)

# for instrument in params["instruments"]:
#     for timeframe in params["timeframes"]:
#         print(f"Building {instrument} {timeframe} candle patterns")
#         candle_pattern_builder.set_instrument_name(instrument)
#         candle_pattern_builder.set_timeframe(timeframe)
#         candle_pattern_builder.set_table_name()
#         candle_pattern_builder.set_source_table_name()
#         candle_pattern_builder.reset_candle_pattern_table()
#         candle_pattern_builder.generate_candle_patterns()
#         if params["to_csv"]:
#             print(f"Writing {instrument} {timeframe} candle patterns to CSV")
#             candle_pattern_builder.to_csv(candle_pattern_builder.table_name)


# pattern_convergence_divergence_builder = PatternConvergenceDivergenceBuilder(
#     "./database/clarity_copy.db", "EOD")

# pattern_convergence_divergence_builder.reset_pattern_convergence_divergence_table()
# for instrument in params["instruments"]:
#     for timeframe in params["timeframes"]:
#         for fractal_period in params["fractal_period"][timeframe]:
#             pattern_convergence_divergence_builder.set_instrument_name(instrument)
#             pattern_convergence_divergence_builder.set_timeframe(timeframe)
#             pattern_convergence_divergence_builder.set_fractal_period(fractal_period)
#             pattern_convergence_divergence_builder.set_cluster_count(
#                 params["cluster_count"])
#             pattern_convergence_divergence_builder.set_atr_threshold(
#                 params["atr_threshold"])
#             pattern_convergence_divergence_builder.set_source_table_name()
#             pattern_convergence_divergence_builder \
#                 .generate_pattern_convergence_divergence()

# pattern_convergence_divergence_builder.to_csv(
#     pattern_convergence_divergence_builder.table_name)
end_time = time.time()
print(f"Time taken: {end_time - start_time} seconds")
