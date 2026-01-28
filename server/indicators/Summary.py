from .DataFoundationBuilder import DataFoundationBuilder


class Summary(DataFoundationBuilder):
    def __init__(self, db_connection):
        super().__init__(db_connection)

    def create_summary_table(self):
        self.con.sql(f"""
            CREATE TABLE IF NOT EXISTS {self.working_table_name} AS
            SELECT *
            FROM
                {self.source_table_name}
        """)

    def add_columns_ensure_correct_types(self):

        big_int_columns = [
            "timestamp"
        ]

        int_columns = [
            "gmtoffset",
            "idx",
            "reversal",
            "indecisive",
            "continuation",
            "rsi_rank"
        ]

        timestamp_columns = [
            "datetime",
            "date"
        ]

        double_columns = [
            "open",
            "high",
            "low",
            "close",
            "volume",
            "adjusted_close",
            "lstCandlePrice",
            "distLstCandle",
            "ema20",
            "ema50",
            "atr14",
            "rsi14",
            "macd_12_26_9",
            "sma9",
            "sma20",
            "sma50",
            "cent_p1",
            "overallRank_p1",
            "cent_n1",
            "overallRank_n1",
            "cent_p2",
            "overallRank_p2",
            "cent_n2",
            "overallRank_n2",
            "cent_p3",
            "overallRank_p3",
            "cent_n3",
            "overallRank_n3",
            "cent_p4",
            "overallRank_p4",
            "cent_n4",
            "overallRank_n4",
            "cent_p5",
            "overallRank_p5",
            "cent_n5",
            "overallRank_n5",
            "cent_p6",
            "overallRank_p6",
            "cent_n6",
            "overallRank_n6",
            "cent_p7",
            "overallRank_p7",
            "cent_n7",
            "overallRank_n7",
            "cent_p8",
            "overallRank_p8",
            "cent_n8",
            "overallRank_n8",
            "cent_p9",
            "overallRank_p9",
            "cent_n9",
            "overallRank_n9",
            "cent_p10",
            "overallRank_p10",
            "cent_n10",
            "overallRank_n10",
            "rsi_diff",
            "major_trend_slope_value",
            "trend_slope_value",
            "run_slope_value"
        ]

        varchar_columns = [
            "rsi_status",
            "major_trend_slope_type",
            "trend_slope_type",
            "run_slope_type",
            "major_trend_to_trend",
            "trend_to_run",
            "status",
            "bias",
            "objective_status",
            "rank_bias",
            "rank_major_trend_to_trend",
            "rank_trend_to_run",
            "overall_rank"
        ]

        db_types = ["BIGINT", "INTEGER", "TIMESTAMP", "DOUBLE", "VARCHAR"]

        for types, db_type in zip(
            [big_int_columns,
             int_columns,
             timestamp_columns,
             double_columns,
             varchar_columns],
            db_types
        ):

            for column in types:
                print(f"Adding column {column} with type {db_type}")
                self.con.sql(f"""
                    ALTER TABLE {self.working_table_name}
                    ADD COLUMN IF NOT EXISTS {column} {db_type}
                """)

                print(f"Altering column {column} to type {db_type}")
                self.con.sql(f"""
                    ALTER TABLE {self.working_table_name}
                    ALTER COLUMN {column} SET DATA TYPE {db_type}
                """)

    def get_column_names(self, table_name: str):
        result = self.con.sql(f"""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = '{table_name}'
        """).fetchall()
        return [row[0] for row in result]

    def delete_last_5_rows(self):
        self.con.sql(f"""
            DELETE FROM {self.working_table_name}
            WHERE timestamp IN (
                SELECT timestamp
                FROM {self.working_table_name}
                ORDER BY timestamp DESC
                LIMIT 5
            )
        """)

    def delete_all_rows(self):
        self.con.sql(f"""
            DELETE FROM {self.working_table_name}
        """)

    def get_timestamps_in_raw_not_in_summary(self):
        return self.con.sql(f"""
            SELECT
                ROW_NUMBER() OVER (ORDER BY timestamp DESC) - 1 as row_num,
                timestamp
            FROM {self.source_table_name}
            WHERE timestamp NOT IN (
                SELECT timestamp FROM {self.working_table_name}
            )
            ORDER BY timestamp DESC
        """).fetchall()

    def append_rows_to_summary_table(self):
        source_columns = self.get_column_names(self.source_table_name)
        working_columns = self.get_column_names(self.working_table_name)

        common_columns = [col for col in source_columns if col in working_columns]

        self.con.sql(f"""
            INSERT INTO {self.working_table_name} ({', '.join(common_columns)})
            SELECT {', '.join(common_columns)}
            FROM {self.source_table_name}
            WHERE timestamp NOT IN (
                SELECT timestamp FROM {self.working_table_name}
            )
        """)


# from .DataFoundationBuilder import DataFoundationBuilder


# class Summary(DataFoundationBuilder):
#     def __init__(self, db_connection):
#         super().__init__(db_connection)
#         self.candle_pattern_table_name = "tbl_EOD_candle_patterns_last_n_aggregated"
#         self.support_resistance_table_name = "tbl_EOD_Support_Resistance"
#         self.trend_table_name = "tbl_EOD_Trends"
#         self.rsi_pair_table_name = "tbl_EOD_pair_RSI_Rank"
#         self.price_proximity_table_name = "tbl_EOD_PriceProximity"
#         self.macd_price_cd_table_name = "tbl_EOD_macd_price_cd"

#     def create_summary_table(self):
#         self.con.sql(f"""
#             CREATE TABLE IF NOT EXISTS {self.working_table_name} AS
#             WITH
#             cd_last_ag AS (
#                 SELECT
#                     instrument_name,
#                     reversal
#                 FROM
#                     {self.candle_pattern_table_name}
#                 WHERE
#                     timeframe = '1h'
#             ),
#             trend AS (
#                 SELECT
#                     instrument_name,
#                     trend_slope_type,
#                     bias
#                 FROM
#                     {self.trend_table_name}
#                 WHERE
#                     timeframe = 'd'
#             ),
#             rsi_pair AS (
#                 SELECT
#                     instrument_name,
#                     pair_timeframe_rank,
#                     pair_status
#                 FROM
#                     {self.rsi_pair_table_name}
#                 WHERE
#                     timeframe = 'd'
#             ),
#             price_prox_a AS (
#                 SELECT
#                     instrument_name,
#                     ROUND(cent, 4) AS cent,
#                     centDistLstCandleRank,
#                     ROUND(proximity, 4) AS proximity
#                 FROM
#                     {self.price_proximity_table_name}
#                 WHERE
#                     timeframe = 'd' AND centDistLstCandleRank = 1
#             ),
#             price_prox_b AS (
#                 SELECT
#                     instrument_name,
#                     ROUND(cent, 4) as cent,
#                     centDistLstCandleRank,
#                     ROUND(proximity, 4) as proximity
#                 FROM
#                     {self.price_proximity_table_name}
#                 WHERE
#                     timeframe = 'd' AND centDistLstCandleRank = -1
#             ),
#             macd_data AS (
#                 SELECT
#                     instrument_name,
#                     ROUND(macd_price_cd, 2) AS macd_price_cd,
#                     status
#                 FROM
#                     {self.macd_price_cd_table_name}
#                 WHERE
#                     timeframe = '1h'
#             )
#             SELECT
#                 cd.instrument_name AS inst,
#                 rsi.pair_timeframe_rank AS rsi_rank,
#                 rsi.pair_status rsi_status,
#                 trend.trend_slope_type AS trend_slope,
#                 trend.bias AS bias,
#                 prox_a.cent as sr_above,
#                 prox_a.proximity as prox_above,
#                 prox_b.cent as sr_below,
#                 prox_b.proximity as prox_below,
#                 macd.macd_price_cd AS macdpcd,
#                 macd.status AS macdpcd_status,
#                 cd.reversal,
#                 -- Buy Identification Logic
#                 CASE
#                     WHEN rsi.pair_status = 'buy' THEN 1
#                     WHEN rsi.pair_status = 'sell' THEN -1
#                     ELSE 0
#                 END AS rsi,
#                 CASE
#                     WHEN trend.trend_slope_type = 'Down' THEN 1
#                     WHEN trend.trend_slope_type = 'Up' THEN -1
#                     ELSE 0
#                 END AS trend,
#                 CASE
#                     WHEN prox_a.proximity > -3
#                             AND trend.trend_slope_type = 'Down' THEN 1
#                     WHEN prox_b.proximity < 3
#                             AND trend.trend_slope_type = 'Up' THEN -1
#                     ELSE 0
#                 END AS prox,
#                 CASE
#                     WHEN macd.status = 'convergence'
#                             AND trend.trend_slope_type = 'Down' THEN 1
#                     WHEN macd.status = 'convergence'
#                             AND trend.trend_slope_type = 'Up' THEN -1
#                     ELSE 0
#                 END AS macdpcd,
#                 CASE
#                     WHEN cd.reversal > 300 THEN 1
#                     WHEN cd.reversal < -300 THEN -1
#                     ELSE 0
#                 END AS cs,
#                 (
#                     CASE
#                         WHEN rsi.pair_status = 'buy' THEN 1
#                         WHEN rsi.pair_status = 'sell' THEN -1
#                         ELSE 0
#                     END +
#                     CASE
#                         WHEN trend.trend_slope_type = 'Down' THEN 1
#                         WHEN trend.trend_slope_type = 'Up' THEN -1
#                         ELSE 0
#                     END +
#                     CASE
#                         WHEN prox_a.proximity > -3
#                             AND trend.trend_slope_type = 'Down' THEN 1
#                         WHEN prox_b.proximity < 3
#                             AND trend.trend_slope_type = 'Up' THEN -1
#                         ELSE 0
#                     END +
#                     CASE
#                         WHEN macd.status = 'convergence'
#                             AND trend.trend_slope_type = 'Down' THEN 1
#                         WHEN macd.status = 'convergence'
#                             AND trend.trend_slope_type = 'Up' THEN -1
#                         ELSE 0
#                     END +
#                     CASE
#                         WHEN cd.reversal > 300 THEN 1
#                         WHEN cd.reversal < -300 THEN -1
#                         ELSE 0
#                     END
#                 ) AS total,
#                 ABS(
#                     CASE
#                         WHEN rsi.pair_status = 'buy' THEN 1
#                         WHEN rsi.pair_status = 'sell' THEN -1
#                         ELSE 0
#                     END +
#                     CASE
#                         WHEN trend.trend_slope_type = 'Down' THEN 1
#                         WHEN trend.trend_slope_type = 'Up' THEN -1
#                         ELSE 0
#                     END +
#                     CASE
#                         WHEN prox_a.proximity > -3
#                             AND trend.trend_slope_type = 'Down' THEN 1
#                         WHEN prox_b.proximity < 3
#                             AND trend.trend_slope_type = 'Up' THEN -1
#                         ELSE 0
#                     END +
#                     CASE
#                         WHEN macd.status = 'convergence'
#                             AND trend.trend_slope_type = 'Down' THEN 1
#                         WHEN macd.status = 'convergence'
#                             AND trend.trend_slope_type = 'Up' THEN -1
#                         ELSE 0
#                     END +
#                     CASE
#                         WHEN cd.reversal > 300 THEN 1
#                         WHEN cd.reversal < -300 THEN -1
#                         ELSE 0
#                     END
#                 ) AS abs_total
#             FROM
#                 cd_last_ag AS cd
#             JOIN
#                 rsi_pair AS rsi
#             ON
#                 cd.instrument_name = rsi.instrument_name
#             LEFT OUTER JOIN
#                 price_prox_a AS prox_a
#             ON
#                 cd.instrument_name = prox_a.instrument_name
#             LEFT OUTER JOIN
#                 price_prox_b AS prox_b
#             ON
#                 cd.instrument_name = prox_b.instrument_name
#             JOIN
#                 macd_data AS macd
#             ON
#                 cd.instrument_name = macd.instrument_name
#             JOIN
#                 trend AS trend
#             ON
#                 cd.instrument_name = trend.instrument_name
#             ORDER BY abs_total DESC;
#         """)
