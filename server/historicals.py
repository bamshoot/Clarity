from indicators.Summary import Summary
from indicators.Cluster import Cluster
from indicators.Fractal import Fractal
from indicators.SourcePrep import SourcePrep
from indicators.RSI import RSI
from indicators.Trend import Trend
from database.db import DB
from config.config import Config
from utils.logger import Logger
import time
from indicators.CandlePattern import CandlePattern


class Historicals:
    def __init__(self, config: Config, db_connection=None):
        self.config = config
        self.params = config.EOD_MnTrd_PARAMS
        self.trends_status_rank = config.Trends_Status_Rank
        self.trend_length_threshold = config.Trends_Length_Threshold
        self.candle_patterns = config.Candle_Patterns
        self.logger = Logger("historicals")
        self.db = db_connection

    def build_source_prep(self):
        self.logger.logger.info("Starting - Source Prep")
        src_prep = SourcePrep(self.db)
        src_prep.set_candle_price_point("close")
        for instrument in self.params["instruments"]:
            for timeframe in self.params["timeframes"]:
                self.logger.logger.info(f"Building - Source Prep - "
                                        f"{instrument} {timeframe}")
                src_prep.set_source_table_name(
                    f"tbl_{self.params['data_source']}_"
                    f"{instrument}_"
                    f"{timeframe}")
                src_prep.add_columns()
                src_prep.generate_last_candle_price()
                src_prep.generate_index_data()
                src_prep.generate_sma(9)
                src_prep.generate_sma(20)
                src_prep.generate_sma(50)
                src_prep.generate_ema(20)
                src_prep.generate_ema(50)
                src_prep.generate_atr(14)
                src_prep.generate_rsi(14)
                src_prep.generate_macd(12, 26, 9)

        self.logger.logger.info("Finished - Source Prep")

    def build_summary(self):
        self.logger.logger.info("Starting - Summary")
        summary = Summary(self.db)
        summary.set_data_source(self.params["data_source"])

        for instrument in self.params["instruments"]:
            for timeframe in self.params["timeframes"]:
                self.logger.logger.info(
                    f"Building Summary - {instrument} {timeframe}")

                summary.set_instrument_name(instrument)
                summary.set_timeframe(timeframe)
                summary.set_source_table_name(
                    f"tbl_{self.params['data_source']}_"
                    f"{instrument}_"
                    f"{timeframe}")
                summary.set_working_table_name(
                    f"tbl_{self.params['data_source']}_"
                    f"{instrument}_"
                    f"{timeframe}_"
                    f"summary")

                summary.create_summary_table()

                summary.append_rows_to_summary_table()

        self.logger.logger.info("Finished - Summary")

    def build_fractal(self):
        self.logger.logger.info("Starting - Fractal")
        fractal = Fractal(self.db, self.params["candle_price_point"])
        fractal.set_data_source(self.params["data_source"])
        fractal.set_output_folder("fractals")

        for instrument in self.params["instruments"]:
            for timeframe in self.params["timeframes"]:

                self.logger.logger.info(
                    f"Building Fractal - {instrument} {timeframe}")

                fractal.set_instrument_name(instrument)
                fractal.set_timeframe(timeframe)
                fractal.set_fractal_period(self.params["fractal_period"])

                fractal.set_source_table_name(
                    f"tbl_{self.params['data_source']}_"
                    f"{instrument}_"
                    f"{timeframe}")

                fractal.set_working_table_name(
                    f"tbl_{self.params['data_source']}_"
                    f"{instrument}_"
                    f"{timeframe}_"
                    f"f{self.params['fractal_period']}")

                fractal.reset_table()
                fractal.generate_input_data()
                fractal.generate_fractal_data()

                if self.params["to_csv"]:
                    fractal.to_csv(fractal.working_table_name)

        self.logger.logger.info("Finished - Fractal")

    def build_cluster(self):
        self.logger.logger.info("Starting - Cluster")
        cluster = Cluster(self.db,
                          max_fractals=300,
                          cluster_count=self.params["cluster_count"],
                          outlier_threshold=self.params["outlier_threshold"],
                          candle_price_point=self.params["candle_price_point"])
        cluster.set_data_source(self.params["data_source"])
        cluster.set_output_folder("clusters")

        for instrument in self.params["instruments"]:
            for timeframe in self.params["timeframes"]:
                self.logger.logger.info(
                    f"Building Cluster - {instrument} {timeframe}")

                cluster.set_instrument_name(instrument)
                cluster.set_timeframe(timeframe)

                cluster.set_source_table_name(
                    f"tbl_{self.params['data_source']}_"
                    f"{instrument}_"
                    f"{timeframe}_"
                    f"f{self.params['fractal_period']}")

                cluster.set_summary_table_name(
                    f"tbl_{self.params['data_source']}_"
                    f"{instrument}_"
                    f"{timeframe}_"
                    f"summary")

                cluster.add_columns_to_summary_table()

                missing_records = cluster.get_missing_records(
                    source_table=None,
                    working_table=(
                        f"tbl_{self.params['data_source']}_"
                        f"{instrument}_"
                        f"{timeframe}_"
                        f"summary"
                    ),
                    reference_fields=["cent_p1", "overallRank_p1",
                                      "cent_p2", "overallRank_p2",
                                      "cent_p3", "overallRank_p3",
                                      "cent_p4", "overallRank_p4",
                                      "cent_p5", "overallRank_p5",
                                      "cent_p6", "overallRank_p6",
                                      "cent_p7", "overallRank_p7",
                                      "cent_p8", "overallRank_p8",
                                      "cent_p9", "overallRank_p9",
                                      "cent_p10", "overallRank_p10",
                                      "cent_n1", "overallRank_n1",
                                      "cent_n2", "overallRank_n2",
                                      "cent_n3", "overallRank_n3",
                                      "cent_n4", "overallRank_n4",
                                      "cent_n5", "overallRank_n5",
                                      "cent_n6", "overallRank_n6",
                                      "cent_n7", "overallRank_n7",
                                      "cent_n8", "overallRank_n8",
                                      "cent_n9", "overallRank_n9",
                                      "cent_n10", "overallRank_n10"],
                    trim_rows=0,
                )

                cluster.process_fractal_timestamps(missing_records)

        self.logger.logger.info("Finished - Cluster")

    def build_rsi(self):
        self.logger.logger.info("Starting - RSI")
        rsi = RSI(self.db)
        rsi.set_data_source(self.params["data_source"])

        for instrument in self.params["instruments"]:
            for timeframe in self.params["timeframes"]:
                self.logger.logger.info(
                    f"Building RSI - {instrument} {timeframe}")

                rsi.set_instrument_name(instrument)
                rsi.set_timeframe(timeframe)
                rsi.set_working_table_name(
                    f"tbl_{self.params['data_source']}_"
                    f"{instrument}_"
                    f"{timeframe}_"
                    f"summary")

                missing_records = rsi.get_missing_records(
                    source_table=None,
                    working_table=(
                        f"tbl_{self.params['data_source']}_"
                        f"{instrument}_"
                        f"{timeframe}_"
                        f"summary"
                    ),
                    reference_fields=["rsi_diff", "rsi_rank"],
                    trim_rows=0,
                )

                for timestamp in missing_records:
                    self.logger.logger.info(
                        f"Building RSI - {instrument} {timeframe} "
                        f"{timestamp[0]}")
                    rsi.build_rsi_data(timestamp[0])
                    rsi.insert_rsi_data(instrument, timestamp[0])

        self.logger.logger.info("Finished - RSI")

    def build_trend(self):
        self.logger.logger.info("Starting - Trends")
        trend = Trend(self.db, self.trend_length_threshold,
                      self.trends_status_rank)
        trend.reset_params_table()
        trend.set_data_source(self.params["data_source"])

        for instrument in self.params["instruments"]:
            for timeframe in self.params["timeframes"]:
                self.logger.logger.info(
                    f"Building Trends - {instrument} {timeframe}")
                trend.set_instrument_name(instrument)
                trend.set_timeframe(timeframe)
                trend.set_working_table_name(
                    f"tbl_{self.params['data_source']}_"
                    f"{instrument}_"
                    f"{timeframe}_"
                    f"summary")

                # trend.reset_trends_fields_to_table()

                missing_records = trend.get_missing_records(
                    working_table=f"tbl_{self.params['data_source']}_"
                                  f"{instrument}_"
                                  f"{timeframe}_"
                                  f"summary",
                    reference_fields=["status"],
                    trim_rows=100
                )

                for timestamp in missing_records:
                    self.logger.logger.info(
                        f"Building Trends - {instrument} {timeframe} "
                        f"{timestamp[0]}")
                    trend.generate_trends(timestamp[0])

        self.logger.logger.info("Finished - Trends")

    def build_candle_pattern(self):
        self.logger.logger.info("Starting - Candle Pattern")
        candle_pattern = CandlePattern(self.db, self.candle_patterns)
        candle_pattern.set_data_source(self.params["data_source"])
        candle_pattern.set_candle_pattern_params_table_name(
            "tbl_candle_patterns_params")
        candle_pattern.reset_candle_pattern_params_table()

        for instrument in self.params["instruments"]:
            for timeframe in self.params["timeframes"]:
                self.logger.logger.info(
                    f"Building Candle Pattern - {instrument} {timeframe}")

                candle_pattern.set_instrument_name(instrument)
                candle_pattern.set_timeframe(timeframe)

                candle_pattern.set_source_table_name(
                    f"tbl_{self.params['data_source']}_"
                    f"{instrument}_"
                    f"{timeframe}")

                candle_pattern.set_working_table_name(
                    f"tbl_{self.params['data_source']}_"
                    f"{instrument}_"
                    f"{timeframe}_"
                    f"candle_patterns")

                candle_pattern.set_last_n_rows_table_name(
                    f"tbl_{self.params['data_source']}_"
                    f"{instrument}_"
                    f"{timeframe}_"
                    f"candle_patterns_last_n_rows")

                candle_pattern.reset_candle_pattern_table()
                candle_pattern.generate_candle_patterns()

                candle_pattern.set_summary_table_name(
                    f"tbl_{self.params['data_source']}_"
                    f"{instrument}_"
                    f"{timeframe}_"
                    f"summary")

                # candle_pattern.add_candle_pattern_fields_to_summary_table()

                missing_records = candle_pattern.get_missing_records(
                    source_table=None,
                    working_table=(
                        f"tbl_{self.params['data_source']}_"
                        f"{instrument}_"
                        f"{timeframe}_"
                        f"summary"
                    ),
                    reference_fields=["reversal"],
                    trim_rows=0,
                )

                print(missing_records)

                for ts_row in missing_records:
                    ts_value = ts_row[0]
                    self.logger.logger.info(
                        f"Building Candle Pattern - {instrument} {timeframe} "
                        f"{ts_value}")
                    candle_pattern.reset_candle_pattern_last_n_rows()
                    candle_pattern.generate_candle_pattern_last_n_rows(
                        10, ts_value)
                    candle_pattern.generate_candle_pattern_agg_data_for_timestamp(
                        ts_value)

        self.logger.logger.info("Finished - Candle Pattern")


if __name__ == "__main__":
    start_time = time.time()
    config = Config()
    db = DB(config.DB_PATH)

    h = Historicals(config, db)

    h.build_source_prep()
    h.build_summary()
    h.build_fractal()
    h.build_cluster()
    h.build_rsi()
    h.build_trend()
    h.build_candle_pattern()

    end_time = time.time()
    execution_time = end_time - start_time
    print(f"Time taken: {execution_time} seconds")
