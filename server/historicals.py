from indicators.Fractal import Fractal
from indicators.Cluster import Cluster
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

    def build_fractal(self):
        self.logger.logger.info("Starting - Fractal")
        fractal = Fractal(
            self.db,
            self.params["candle_price_point"])

        fractal.set_data_source(self.params["data_source"])
        fractal.set_instrument_name(self.params["instruments"][0])
        fractal.set_timeframe(self.params["timeframes"][0])
        fractal.set_fractal_period(
            self.params["fractal_period"][self.params["timeframes"][0]][0])
        fractal.set_output_folder("fractals")

        source_table_name = (f"tbl_{self.params['data_source']}_"
                             f"{self.params['instruments'][0]}_"
                             f"{self.params['timeframes'][0]}")

        working_table_name = (
                f"tbl_{self.params['data_source']}_"
                f"{self.params['instruments'][0]}_"
                f"{self.params['timeframes'][0]}_"
                f"f{self.params['fractal_period'][self.params['timeframes'][0]][0]}_"
                f"temp")

        fractal.set_source_table_name(source_table_name)
        fractal.set_working_table_name(working_table_name)
        fractal.reset_table()
        fractal.generate_input_data()
        fractal.generate_fractal_data()

        self.logger.logger.info("Finished - Fractal")

    def build_cluster(self):
        self.logger.logger.info("Starting - Cluster")
        cluster = Cluster(self.db,
                          300,
                          self.params["cluster_count"],
                          self.params["outlier_threshold"],
                          self.params["candle_price_point"])
        cluster.set_data_source(self.params["data_source"])
        cluster.set_instrument_name(self.params["instruments"][0])
        cluster.set_timeframe(self.params["timeframes"][0])
        cluster.set_fractal_period(
            self.params["fractal_period"][self.params["timeframes"][0]][0])
        cluster.set_output_folder("clusters")

        source_table_name = (f"tbl_{self.params['data_source']}_"
                             f"{self.params['instruments'][0]}_"
                             f"{self.params['timeframes'][0]}")

        working_table_name = (
                f"tbl_{self.params['data_source']}_"
                f"{self.params['instruments'][0]}_"
                f"{self.params['timeframes'][0]}_"
                f"f{self.params['fractal_period'][self.params['timeframes'][0]][0]}_"
                f"temp")

        cluster.set_source_table_name(source_table_name)
        cluster.set_working_table_name(working_table_name)
        cluster.set_threshold()
        cluster.set_window_position(1)
        cluster.set_window_end()
        cluster.set_window_start()
        cluster.alter_table()
        cluster.generate_input_data()
        cluster.generate_cluster_data()
        cluster.generate_cent_dist()
        cluster.remove_outliers()
        cluster.generate_cent_dist_lst_candle()
        cluster.generate_cent_count()
        cluster.generate_score()
        cluster.generate_rank()
        print(cluster.select_data())

        # wrk_tbl = cluster.get_table_from_db(working_table_name)
        # print(wrk_tbl)

        self.logger.logger.info("Finished - Cluster")


if __name__ == "__main__":

    start_time = time.time()
    config = Config()
    db = DB(config.DB_PATH)

    h = Historicals(config, db)
    h.build_fractal()
    h.build_cluster()

    end_time = time.time()
    execution_time = end_time - start_time
    print(f"Time taken: {execution_time} seconds")
