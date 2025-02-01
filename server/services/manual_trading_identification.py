import time
from .eod_data import EODData
from ..config.config import Config
from ..indicators.SourcePrep import SourcePrep
from ..indicators.Fractal import Fractal
from ..indicators.Cluster import Cluster
from ..indicators.CandlePattern import CandlePattern
from ..indicators.MACDPriceCD import MACDPriceCD
from ..indicators.RSI import RSI
from ..indicators.Trend import Trend
from ..indicators.Pinescript import Pinescript
from ..indicators.Summary import Summary
from ..indicators.Watchlist import Watchlist
from ..utils.logger import Logger
import asyncio


class ManualTradingIdentification:
    def __init__(self, config: Config,
                 eod_data_service: EODData = None,
                 db_connection=None):
        self.config = config
        self.eod_data_service = (eod_data_service or
                                 EODData(config.EOD_URL,
                                         config.EOD_API_KEY,
                                         db_connection))
        self.params = config.EOD_MnTrd_PARAMS
        self.trends = config.Trends
        self.candle_patterns = config.Candle_Patterns
        self.logger = Logger("manual_trading_identification")
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

    def build_fractal(self):
        self.logger.logger.info("Starting - Fractal")
        fractal = Fractal(self.db, self.params["candle_price_point"])

        fractal.set_data_source(self.params["data_source"])
        fractal.set_output_folder("fractals")

        for instrument in self.params["instruments"]:
            for timeframe in self.params["timeframes"]:
                for fractal_period in self.params["fractal_period"][timeframe]:
                    self.logger.logger.info(f"Building - Fractal - "
                                            f"{instrument} {timeframe} "
                                            f"{fractal_period}")
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

        self.logger.logger.info("Finished - Fractal")

        if self.params["to_csv"]:
            fractal.to_csv(fractal.working_table_name)

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
                    self.logger.logger.info(f"Building - Cluster - "
                                            f"{instrument} {timeframe} "
                                            f"{fractal_period}")
                    cluster.set_instrument_name(instrument)
                    cluster.set_timeframe(timeframe)
                    cluster.set_fractal_period(fractal_period)
                    cluster.set_source_table_name(
                        f"tbl_{self.params['data_source']}_"
                        f"{instrument}_"
                        f"{timeframe}_"
                        f"f{fractal_period}")
                    cluster.set_working_table_name(
                        f"tbl_{self.params['data_source']}_"
                        f"{instrument}_"
                        f"{timeframe}_"
                        f"f{fractal_period}_"
                        f"k{self.params['cluster_count']}")
                    cluster.set_threshold()
                    cluster.set_window_position(1)
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

        self.logger.logger.info("Finished - Cluster")

        if self.params["to_csv"]:
            cluster.to_csv(cluster.working_table_name)

    def build_trend(self):
        self.logger.logger.info("Starting - Trend")
        trend = Trend(self.db, self.trends)
        trend.set_data_source(self.params["data_source"])
        trend.set_output_folder("trends")
        trend.set_source_table_name("tbl_trend_params")
        trend.set_working_table_name(f"tbl_{self.params['data_source']}_Trends")
        trend.reset_trends_table()

        for instrument in self.params["instruments"]:
            for timeframe in self.params["timeframes"]:
                trend.set_instrument_name(instrument)
                trend.set_timeframe(timeframe)
                trend.set_source_table_name(f"tbl_{self.params['data_source']}_"
                                            f"{instrument}_"
                                            f"{timeframe}")
                self.logger.logger.info(f"Building - Trend - "
                                        f"{trend.source_table_name}")
                trend.generate_trends()

        if self.params["to_csv"]:
            trend.to_csv(trend.working_table_name)

        self.logger.logger.info("Finished - Trend")

    def build_rsi(self):
        self.logger.logger.info("Starting - RSI")
        rsi = RSI(self.db)
        rsi.set_data_source(self.params["data_source"])
        rsi.set_pair_table_name(f"tbl_{self.params['data_source']}_pair_RSI_Rank")
        rsi.set_currency_table_name(f"tbl_{self.params['data_source']}_"
                                    f"currency_RSI_Rank")
        rsi.reset_rsi_ranks_table()
        rsi.set_output_folder("rsi")

        for instrument in self.params["instruments"]:
            for timeframe in self.params["timeframes"]:
                self.logger.logger.info(f"Building - RSI - {instrument} {timeframe}")
                rsi.set_instrument_name(instrument)
                rsi.set_timeframe(timeframe)
                rsi.set_source_table_name(f"tbl_{self.params['data_source']}_"
                                          f"{instrument}_"
                                          f"{timeframe}")
                rsi.generate_rsi()

        rsi.generate_pair_timeframe_rank()
        rsi.generate_currency_rsi()
        rsi.generate_base_quote_timeframe_rank()

        if self.params["to_csv"]:
            rsi.to_csv(rsi.pair_table_name)
            rsi.to_csv(rsi.currency_table_name)

        self.logger.logger.info("Finished - RSI")

    def build_macd_price_cd(self):
        self.logger.logger.info("Starting - MACD Price Convergence Divergence")
        macdpcd = MACDPriceCD(self.db)
        macdpcd.set_output_folder("macd_price_cd")
        macdpcd.set_data_source(self.params["data_source"])
        macdpcd.set_working_table_name(f"tbl_{self.params['data_source']}_"
                                       f"macd_price_cd")
        macdpcd.reset_macd_convergence_divergence_table()

        for instrument in self.params["instruments"]:
            for timeframe in self.params["timeframes"]:
                self.logger.logger.info(f"Building - "
                                        f"MACD Price Convergence Divergence - "
                                        f"{instrument} {timeframe}")
                macdpcd.set_instrument_name(instrument)
                macdpcd.set_timeframe(timeframe)
                macdpcd.set_source_table_name(f"tbl_{self.params['data_source']}_"
                                              f"{instrument}_"
                                              f"{timeframe}")
                macdpcd.generate_macd_convergence_divergence()

        if self.params["to_csv"]:
            macdpcd.to_csv(macdpcd.working_table_name)

    def build_candle_pattern(self):
        self.logger.logger.info("Starting - Candle Patterns")
        candle_pattern = CandlePattern(self.db, self.candle_patterns)
        candle_pattern.set_data_source(self.params["data_source"])
        candle_pattern.set_output_folder("candle_patterns")
        candle_pattern.set_candle_pattern_params_table_name(
            "tbl_candle_patterns_params")
        candle_pattern.reset_candle_pattern_params_table()
        candle_pattern.set_last_n_aggregated_table_name(
            f"tbl_{self.params['data_source']}_candle_patterns_last_n_aggregated")
        candle_pattern.reset_last_n_aggregated_table()

        for instrument in self.params["instruments"]:
            for timeframe in self.params["timeframes"]:
                self.logger.logger.info(f"Building - Candle Patterns - "
                                        f"{instrument} {timeframe}")
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
                    f"last_n_rows")
                candle_pattern.reset_candle_pattern_table()
                candle_pattern.generate_candle_patterns()
                candle_pattern.reset_candle_pattern_last_n_rows()
                candle_pattern.generate_candle_pattern_last_n_rows(10)
                candle_pattern.generate_last_n_aggregated_data()

                if self.params["to_csv"]:
                    candle_pattern.to_csv(candle_pattern.working_table_name)
                    candle_pattern.to_csv(candle_pattern.last_n_rows_table_name)

        if self.params["to_csv"]:
            candle_pattern.to_csv(candle_pattern.last_n_aggregated_table_name)

        self.logger.logger.info("Finished - Candle Patterns")

    def build_summary(self):
        self.logger.logger.info("Starting - Summary")
        summary = Summary(self.db)
        summary.set_data_source(self.params["data_source"])
        summary.set_output_folder("summary")
        summary.set_working_table_name(f"tbl_{self.params['data_source']}_summary")
        summary.drop_table(summary.working_table_name)
        summary.create_summary_table()

        if self.params["to_csv"]:
            summary.to_csv(summary.working_table_name)

        self.logger.logger.info("Finished - Summary")

    def build_watchlist(self):
        self.logger.logger.info("Starting - Watchlist")
        watchlist = Watchlist(self.db)
        watchlist.set_source_table_name(f"tbl_{self.params['data_source']}_summary")
        watchlist.build_watchlist()

        self.logger.logger.info("Finished - Watchlist")

    def build_pinescript(self):
        self.logger.logger.info("Starting - Pinescript")
        pinescript = Pinescript(self.db)
        pinescript.set_data_source(self.params["data_source"])
        pinescript.set_output_folder("pinescript")
        pinescript.set_source_table_name(f"tbl_{self.params['data_source']}_"
                                         f"Support_Resistance")
        pinescript.build_pinescript(pinescript.source_table_name)

        self.logger.logger.info("Finished - Pinescript")

    async def run_analysis(self):
        """Main method to run all analysis steps"""
        try:
            start_time = time.time()
            self.logger.logger.info("Starting - Manual Trading Identification")

            # self.build_source_prep()
            # self.build_fractal()
            # self.build_cluster()
            # self.build_trend()
            # self.build_rsi()
            # self.build_macd_price_cd()
            # self.build_candle_pattern()
            # self.build_summary()
            # self.build_watchlist()
            # self.build_pinescript()

            end_time = time.time()
            execution_time = end_time - start_time
            self.logger.logger.info("Finished - Manual Trading Identification")
            self.logger.logger.info(f"Time taken: {execution_time} seconds")

            return {
                "status": "success",
                "execution_time": execution_time
            }

        except Exception as e:
            self.logger.logger.error(
                f"Error in manual trading identification: {str(e)}")
            raise


if __name__ == "__main__":
    config = Config()
    mti = ManualTradingIdentification(config)
    asyncio.run(mti.run_analysis())
