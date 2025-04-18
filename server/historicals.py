from indicators.Summary import Summary
from indicators.Cluster import Cluster
from indicators.Fractal import Fractal
from database.db import DB
from config.config import Config
from utils.logger import Logger
import time


class Historicals:
    def __init__(self, config: Config, db_connection=None):
        self.config = config
        self.params = config.EOD_MnTrd_PARAMS
        self.logger = Logger("historicals")
        self.db = db_connection
        self.timestamps_in_raw_not_in_summary = {}

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
                summary.delete_all_rows()

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


if __name__ == "__main__":

    start_time = time.time()
    config = Config()
    db = DB(config.DB_PATH)

    h = Historicals(config, db)

    h.build_fractal()
    h.build_summary()
    h.build_cluster()
    end_time = time.time()
    execution_time = end_time - start_time
    print(f"Time taken: {execution_time} seconds")
