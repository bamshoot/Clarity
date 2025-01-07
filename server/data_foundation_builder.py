import kmeans1d
import duckdb
import time
import os
import talib as ta
import json


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
        """).write_csv(f"./outputs/fractals/{table_name}.csv")

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


class SupportResistanceBuilder:
    def __init__(self,
                 db_path: str,
                 data_source: str):
        self.db_path = db_path
        self.con = duckdb.connect(self.db_path)
        self.data_source = data_source
        self.instrument_name = None
        self.timeframe = None
        self.fractal_period = None
        self.cluster_count = None
        self.table_name = (f"tbl_{self.data_source}_SupportResistance")
        self.fractal_table_name = (f"{self.table_name}_"
                                   f"f{self.fractal_period}_"
                                   f"k{self.cluster_count}")

    def __del__(self):
        if hasattr(self, 'con'):
            self.con.close()

    def get_table_from_db(self, table_name: str):
        return self.con.sql(f"SELECT * FROM {table_name}")

    def drop_table(self, table_name: str):
        self.con.sql(f"DROP TABLE IF EXISTS {table_name}")

    def create_table(self, table_name: str):
        self.con.sql(f"""
            CREATE TABLE {table_name}
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

    def set_instrument_name(self, instrument_name: str):
        self.instrument_name = instrument_name

    def set_timeframe(self, timeframe: str):
        self.timeframe = timeframe

    def set_fractal_period(self, fractal_period: int):
        self.fractal_period = fractal_period

    def set_cluster_count(self, cluster_count: int):
        self.cluster_count = cluster_count

    def append_data_to_table(self, table_name: str, fractal_table_name: str):
        self.con.sql(f"""
            INSERT INTO {table_name}
            SELECT DISTINCT '{self.instrument_name}' as instrument_name,
                   '{self.timeframe}' as timeframe,
                   clust, cent, centDistMean, centCount, centDistLstCandle,
                   centDistLstCandleRank, centDistMeanRank, centCountRank,
                   score, overallRank
            FROM {fractal_table_name}
        """)

    def to_csv(self, table_name: str):
        self.con.sql(f"""
            SELECT * FROM {table_name} ORDER BY instrument_name, timeframe, clust
        """).write_csv(f"./outputs/sr/{table_name}.csv")


class PinescriptBuilder:
    def __init__(self, db_path: str, data_source: str):
        self.db_path = db_path
        self.con = duckdb.connect(self.db_path)
        self.data_source = data_source
        self.table_name = (f"tbl_{self.data_source}_SupportResistance")

    def __del__(self):
        if hasattr(self, 'con'):
            self.con.close()

    def _get_table_from_db(self, table_name: str):
        return self.con.sql(f"SELECT * FROM {table_name}")

    def _reset_pinescript_file(self):
        for file in os.listdir("./outputs/pinescript"):
            with open(f"./outputs/pinescript/{file}", "w") as f:
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

        sr = self._get_table_from_db(table_name).fetchall()

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

            with open(f"./outputs/pinescript/{file_name}.txt", "a") as f:
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


class TrendIndicatorBuilder:
    def __init__(self, db_path: str, data_source: str):
        self.db_path = db_path
        self.con = duckdb.connect(self.db_path)
        self.data_source = data_source
        self.instrument_name = None
        self.timeframe = None
        self.source_table_name = None
        self.table_name = (f"tbl_{self.data_source}_Trends")
        self._reset_trends_table()

    def __del__(self):
        if hasattr(self, 'con'):
            self.con.close()

    def _get_table_from_db(self, table_name: str):
        return self.con.sql(f"SELECT * FROM {table_name}")

    def _reset_trends_table(self):
        self._drop_table(self.table_name)
        self._drop_table("tbl_trend_params")
        self._create_trend_params_table_from_json()
        self._create_trends_table()

    def _drop_table(self, table_name: str):
        self.con.sql(f"DROP TABLE IF EXISTS {table_name}")

    def _create_trend_params_table_from_json(self):
        with open("./config/settings/trends.json", "r") as f:
            trend_params = json.load(f)

        self.con.sql("""
            CREATE TABLE tbl_trend_params
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
                INSERT INTO tbl_trend_params
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
            CREATE TABLE {self.table_name}
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

    def set_instrument_name(self, instrument_name: str):
        self.instrument_name = instrument_name

    def set_timeframe(self, timeframe: str):
        self.timeframe = timeframe

    def set_source_table_name(self):
        self.source_table_name = (f"tbl_{self.data_source}_"
                                  f"{self.instrument_name}_"
                                  f"{self.timeframe}")

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
            INSERT INTO {self.table_name}
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

    def get_table(self, table_name: str):
        return self.con.sql(f"SELECT * FROM {table_name}")

    def to_csv(self, table_name: str):
        self.con.sql(f"""
            SELECT * FROM {table_name} ORDER BY instrument_name, timeframe
        """).write_csv(f"./outputs/trends/{table_name}.csv")

    def generate_trends(self):

        run_length = 9
        trend_length = 20
        major_trend_length = 50
        threshold = 10

        data = self._get_table_from_db(self.source_table_name).fetchnumpy()

        close_prices = data['close']

        sma_run = ta.SMA(close_prices, run_length)
        sma_trend = ta.SMA(close_prices, trend_length)
        sma_major_trend = ta.SMA(close_prices, major_trend_length)

        slope_run = round(ta.LINEARREG_SLOPE(
            sma_run, 2)[-1]*100, 2)
        slope_trend = round(ta.LINEARREG_SLOPE(
            sma_trend, 2)[-1]*100, 2)
        slope_major_trend = round(ta.LINEARREG_SLOPE(
            sma_major_trend, 2)[-1]*100, 2)

        run_slope_type = None
        trend_slope_type = None
        major_trend_slope_type = None

        if slope_run > threshold:
            run_slope_type = "Up"
        elif slope_run < -threshold:
            run_slope_type = "Down"

        if slope_trend > threshold:
            trend_slope_type = "Up"
        elif slope_trend < -threshold:
            trend_slope_type = "Down"

        if slope_major_trend > threshold:
            major_trend_slope_type = "Up"
        elif slope_major_trend < -threshold:
            major_trend_slope_type = "Down"

        trend_id = f"{run_slope_type}{trend_slope_type}{major_trend_slope_type}"

        self._append_instrument_trends(trend_id,
                                       slope_run,
                                       slope_trend,
                                       slope_major_trend)


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

# print("Building data foundation")

# for instrument in params["instruments"]:

#     for timeframe in params["timeframes"]:

#         fractal_table_name = (f"tbl_EOD_{instrument}_"
#                               f"{timeframe}_"
#                               f"f{params['fractal_period']}_"
#                               f"k{params['cluster_count']}")

#         print(f"Building {fractal_table_name}")

#         data_foundation_builder = DataFoundationBuilder(
#                     "./database/clarity.db",
#                     "EOD",
#                     instrument,
#                     timeframe,
#                     params["max_bars"],
#                     params["fractal_period"],
#                     params["cluster_count"],
#                     params["outlier_threshold"],
#                     params["candle_price_point"],
#                     params["to_csv"])

#         data_foundation_builder.build_fractal_clusters(fractal_table_name)

# print("Appending data to support resistance table")

# support_resistance_builder = SupportResistanceBuilder(
#     "./database/clarity.db",
#     "EOD")

# support_resistance_builder.drop_table(support_resistance_builder.table_name)
# support_resistance_builder.create_table(support_resistance_builder.table_name)

# for instrument in params["instruments"]:
#     for timeframe in params["timeframes"]:
#         fractal_table_name = (f"tbl_EOD_{instrument}_"
#                               f"{timeframe}_"
#                               f"f{params['fractal_period']}_"
#                               f"k{params['cluster_count']}")

#         support_resistance_builder.set_instrument_name(instrument)
#         support_resistance_builder.set_timeframe(timeframe)
#         support_resistance_builder.set_fractal_period(params["fractal_period"])
#         support_resistance_builder.set_cluster_count(params["cluster_count"])

#         support_resistance_builder.append_data_to_table(
#             support_resistance_builder.table_name,
#             fractal_table_name)

# if params["to_csv"]:
#     support_resistance_builder.to_csv(support_resistance_builder.table_name)


# print("Building pinescript")

# pinescript_builder = PinescriptBuilder("./database/clarity.db", "EOD")

# pinescript_builder.build_pinescript(pinescript_builder.table_name)


trend_indicator_builder = TrendIndicatorBuilder("./database/clarity.db", "EOD")

for instrument in params["instruments"]:
    for timeframe in params["timeframes"]:
        trend_indicator_builder.set_instrument_name(instrument)
        trend_indicator_builder.set_timeframe(timeframe)
        trend_indicator_builder.set_source_table_name()
        trend_indicator_builder.generate_trends()

if params["to_csv"]:
    trend_indicator_builder.to_csv(trend_indicator_builder.table_name)

end_time = time.time()
print(f"Time taken: {end_time - start_time} seconds")
