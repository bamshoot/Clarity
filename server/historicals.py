from indicators.Summary import Summary
from indicators.Cluster import Cluster
from indicators.Fractal import Fractal
from indicators.SourcePrep import SourcePrep
from indicators.RSI import RSI
from indicators.Trend import Trend
from indicators.Timestamps import Timestamps
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
        self.timestamps_in_raw_not_in_summary = {}

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

    def build_fractal(self):
        self.logger.logger.info("Starting - Fractal")
        fractal = Fractal(self.db, self.params["candle_price_point"])
        fractal.set_data_source(self.params["data_source"])
        fractal.set_output_folder("fractals")

        for instrument in self.params["instruments"]:
            for timeframe in self.params["timeframes"]:
                for fractal_period in self.params["fractal_period"][timeframe]:
                    self.logger.logger.info(
                        f"Building Fractal - {instrument} {timeframe} {fractal_period}")

                    fractal.set_instrument_name(instrument)
                    fractal.set_timeframe(timeframe)
                    fractal.set_fractal_period(fractal_period)

                    fractal.set_source_table_name(
                        f"tbl_{self.params['data_source']}_"
                        f"{instrument}_"
                        f"{timeframe}")

                    fractal.set_working_table_name(
                        f"tbl_{self.params['data_source']}_"
                        f"{instrument}_"
                        f"{timeframe}_"
                        f"f{fractal_period}")

                    fractal.reset_table()
                    fractal.generate_input_data()
                    fractal.generate_fractal_data()

                    if self.params["to_csv"]:
                        fractal.to_csv(fractal.working_table_name)

        self.logger.logger.info("Finished - Fractal")

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
                # summary.delete_all_rows()

                self.timestamps_in_raw_not_in_summary[f'{instrument}_{timeframe}'] = \
                    summary.get_timestamps_in_raw_not_in_summary()

                print(self.timestamps_in_raw_not_in_summary)

                summary.append_rows_to_summary_table()

        self.logger.logger.info("Finished - Summary")

    def build_cluster(self):
        self.logger.logger.info("Starting - Cluster")
        cluster = Cluster(self.db,
                          300,
                          self.params["cluster_count"],
                          self.params["outlier_threshold"],
                          self.params["candle_price_point"])
        cluster.set_data_source(self.params["data_source"])
        cluster.set_output_folder("clusters")

        for instrument in self.params["instruments"]:
            for timeframe in self.params["timeframes"]:
                for fractal_period in self.params["fractal_period"][timeframe]:
                    self.logger.logger.info(
                        f"Building Cluster - {instrument} {timeframe} {fractal_period}")

                    for window_position, timestamp in \
                            self.timestamps_in_raw_not_in_summary[f"{instrument}"
                                                                  f"_{timeframe}"]:

                        print(f"{window_position}: {timestamp}")

                        cluster.set_instrument_name(instrument)
                        cluster.set_timeframe(timeframe)
                        cluster.set_fractal_period(fractal_period)

                        cluster.set_source_table_name(
                            f"tbl_{self.params['data_source']}_"
                            f"{instrument}_"
                            f"{timeframe}")

                        cluster.set_working_table_name(
                            f"tbl_{self.params['data_source']}_"
                            f"{instrument}_"
                            f"{timeframe}_"
                            f"f{fractal_period}_"
                            f"k{self.params['cluster_count']}")

                        cluster.set_summary_table_name(
                            f"tbl_{self.params['data_source']}_"
                            f"{instrument}_"
                            f"{timeframe}_"
                            f"summary")

                        cluster.add_columns_to_summary_table()
                        cluster.set_threshold()
                        cluster.set_window_position(window_position)
                        cluster.reset_table()
                        cluster.generate_input_data()
                        cluster.generate_cluster_data()
                        cluster.set_indicator_data()
                        cluster.generate_cent_dist()
                        cluster.remove_outliers()
                        cluster.generate_cent_dist_lst_candle()
                        cluster.generate_cent_count()
                        cluster.generate_score()
                        cluster.generate_rank()
                        cluster.generate_historical_sr()

        self.logger.logger.info("Finished - Cluster")

    def build_timestamps(self):
        self.logger.logger.info("Starting - Timestamps")
        timestamps = Timestamps(self.db)

        for instrument in self.params["instruments"]:
            for timeframe in self.params["timeframes"]:
                self.logger.logger.info(
                    f"Building Timestamps - {instrument} {timeframe}")

                timestamps.set_instrument_name(instrument)
                timestamps.set_timeframe(timeframe)

                timestamps.set_data_source(self.params["data_source"])
                timestamps.set_working_table_name(
                    f"tbl_{self.params['data_source']}_"
                    f"{instrument}_"
                    f"{timeframe}")

                timestamps.set_timestamp_ref_table()

        self.logger.logger.info("Finished - Timestamps")

        return timestamps

    def build_rsi(self, timestamps):
        self.logger.logger.info("Starting - RSI")
        rsi = RSI(self.db)
        rsi.set_data_source(self.params["data_source"])

        for timeframe in self.params["timeframes"]:
            self.logger.logger.info(
                f"Building RSI - {timeframe}")

            rsi.set_timeframe(timeframe)

            for instrument in self.params["instruments"]:
                rsi.set_instrument_name(instrument)
                rsi.set_working_table_name(
                    f"tbl_{self.params['data_source']}_"
                    f"{instrument}_"
                    f"{timeframe}_"
                    f"summary")
                rsi.reset_rsi_data()

            if timeframe == "1h":
                for timestamp in timestamps.timestamp_ref_table_1h_timestamp:
                    rsi.build_rsi_data(timestamp[0])
                    for instrument in self.params["instruments"]:
                        self.logger.logger.info(
                            f"Building RSI - {instrument} {timeframe} {timestamp[0]}")
                        rsi.set_instrument_name(instrument)
                        rsi.set_working_table_name(
                            f"tbl_{self.params['data_source']}_"
                            f"{instrument}_"
                            f"{timeframe}_"
                            f"summary")
                        rsi.insert_rsi_data(instrument, timestamp[0])
            elif timeframe == "d":
                for timestamp in timestamps.timestamp_ref_table_d_timestamp:
                    rsi.build_rsi_data(timestamp[0])
                    for instrument in self.params["instruments"]:
                        self.logger.logger.info(
                            f"Building RSI - {instrument} {timeframe} {timestamp[0]}")
                        rsi.set_instrument_name(instrument)
                        rsi.set_working_table_name(
                            f"tbl_{self.params['data_source']}_"
                            f"{instrument}_"
                            f"{timeframe}_"
                            f"summary")
                        rsi.insert_rsi_data(instrument, timestamp[0])

        self.logger.logger.info("Finished - RSI")

    def build_trend(self, timestamps):
        self.logger.logger.info("Starting - Trends")
        trend = Trend(self.db, self.trend_length_threshold, self.trends_status_rank)
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

                trend.reset_trends_fields_to_table()

                if timeframe == "1h":
                    for timestamp in timestamps.timestamp_ref_table_1h_timestamp:
                        print(f"Building Trends - {instrument} {timeframe} "
                              f"{timestamp[0]}")
                        trend.generate_trends(timestamp[0])

                if timeframe == "d":
                    for timestamp in timestamps.timestamp_ref_table_d_timestamp:
                        print(f"Building Trends - {instrument} {timeframe} "
                              f"{timestamp[0]}")
                        trend.generate_trends(timestamp[0])

        self.logger.logger.info("Finished - Trends")

    def build_candle_pattern(self, timestamps):
        self.logger.logger.info("Starting - Candle Pattern")
        candle_pattern = CandlePattern(self.db, self.candle_patterns)
        candle_pattern.set_data_source(self.params["data_source"])

        # Set up the parameters table
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

                # Generate candle pattern data for all timestamps
                candle_pattern.reset_candle_pattern_table()
                candle_pattern.generate_candle_patterns()

                # Add candle pattern fields to summary table
                candle_pattern.set_summary_table_name(
                    f"tbl_{self.params['data_source']}_"
                    f"{instrument}_"
                    f"{timeframe}_"
                    f"summary")
                candle_pattern.add_candle_pattern_fields_to_summary_table()

                # Process each timestamp
                if timeframe == "1h":
                    for timestamp in timestamps.timestamp_ref_table_1h_timestamp:
                        print(f"Building Candle Pattern - {instrument} {timeframe} "
                              f"{timestamp[0]}")
                        candle_pattern.reset_candle_pattern_last_n_rows()
                        candle_pattern.generate_candle_pattern_last_n_rows(
                            10, timestamp[0])
                        candle_pattern.generate_candle_pattern_aggregated_data_for_timestamp(
                            timestamp[0])

                if timeframe == "d":
                    for timestamp in timestamps.timestamp_ref_table_d_timestamp:
                        print(f"Building Candle Pattern - {instrument} {timeframe} "
                              f"{timestamp[0]}")
                        candle_pattern.reset_candle_pattern_last_n_rows()
                        candle_pattern.generate_candle_pattern_last_n_rows(
                            10, timestamp[0])
                        candle_pattern.generate_candle_pattern_aggregated_data_for_timestamp(
                            timestamp[0])

        self.logger.logger.info("Finished - Candle Pattern")


if __name__ == "__main__":
    start_time = time.time()
    config = Config()
    db = DB(config.DB_PATH)

    h = Historicals(config, db)
    timestamps = h.build_timestamps()

    # h.build_source_prep()
    # h.build_fractal()
    # h.build_summary()
    h.build_cluster()
    # h.build_rsi(timestamps)
    # h.build_trend(timestamps)
    # h.build_candle_pattern(timestamps)

    # print(timestamps.min_timestamp_1h)
    # print(timestamps.min_timestamp_d)
    # print(timestamps.min_timestamp_w)
    # print(timestamps.min_timestamp_m)

    # print(timestamps.timestamp_ref_table_1h_timestamp[0][0])

    end_time = time.time()
    execution_time = end_time - start_time
    print(f"Time taken: {execution_time} seconds")
