from indicators.Fractal import Fractal
from database.db import DB
from config.config import Config
from utils.logger import Logger


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
            self.params["max_bars"],
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

        print(source_table_name)
        src_tbl = fractal.get_table_from_db(source_table_name)
        print(src_tbl)

        print(working_table_name)
        wrk_tbl = fractal.get_table_from_db(working_table_name)
        fractal.reset_table()
        fractal.generate_input_data()
        fractal.generate_last_candle_price()
        fractal.generate_index_data()
        fractal.generate_fractal_data()
        print(wrk_tbl)

        self.logger.logger.info("Finished - Fractal")


if __name__ == "__main__":
    config = Config()
    db = DB(config.DB_PATH)
    h = Historicals(config, db)
    h.build_fractal()
