import time
from .eod_data import EODData
from ..config.config import Config
from ..indicators.SourcePrep import SourcePrep
from ..indicators.FractalCluster import FractalCluster
from ..indicators.CandlePattern import CandlePattern
from ..indicators.PatternCD import PatternCD
from ..indicators.MACDPriceCD import MACDPriceCD
from ..indicators.RSI import RSI
from ..indicators.Trend import Trend
from ..indicators.SupportResistance import SupportResistance
from ..indicators.Pinescript import Pinescript
from ..indicators.PriceProximity import PriceProximity
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
                src_prep.generate_ema(20)
                src_prep.generate_ema(50)
                src_prep.generate_atr(14)
                src_prep.generate_rsi(14)
                src_prep.generate_macd(12, 26, 9)

        self.logger.logger.info("Finished - Source Prep")

    def build_fractal_cluster(self):
        self.logger.logger.info("Starting - Fractal/Cluster")
        fc = FractalCluster(
            self.db,
            self.params["max_bars"],
            self.params["cluster_count"],
            self.params["outlier_threshold"],
            self.params["candle_price_point"])

        for instrument in self.params["instruments"]:
            for timeframe in self.params["timeframes"]:
                for fractal_period in self.params["fractal_period"][timeframe]:

                    source_table_name = (f"tbl_{self.params['data_source']}_"
                                         f"{instrument}_"
                                         f"{timeframe}")

                    fc.set_source_table_name(source_table_name)

                    working_table_name = (f"tbl_{self.params['data_source']}_"
                                          f"{instrument}_"
                                          f"{timeframe}_"
                                          f"f{fractal_period}_"
                                          f"k{self.params['cluster_count']}")

                    fc.set_working_table_name(working_table_name)

                    self.logger.logger.info(f"Building - Fractal/Cluster - "
                                            f"{working_table_name}")

                    fc.reset_table() # Both
                    fc.set_instrument_name(instrument) # Both
                    fc.set_timeframe(timeframe) # Both
                    fc.set_fractal_period(fractal_period) # Both
                    fc.set_output_folder("fractals") # Both
                    fc.set_threshold() #cluster
                    fc.generate_input_data() # Both f fractal k cluster o outlier
                    fc.generate_fractal_data() # fractal
                    fc.generate_cluster_data() # cluster
                    fc.generate_cent_dist() # cluster
                    fc.remove_outliers() # cluster
                    fc.generate_cent_dist_lst_candle() # cluster
                    fc.generate_cent_count() # cluster
                    fc.generate_score() # cluster
                    fc.generate_rank() # cluster

                    if self.params["to_csv"]:
                        fc.to_csv(working_table_name)

        self.logger.logger.info("Finished - Fractal/Cluster")

    def build_support_resistance(self):
        self.logger.logger.info("Starting - Support Resistance")
        sr = SupportResistance(self.db)
        sr.set_data_source(self.params["data_source"])
        sr.set_working_table_name(f"tbl_{self.params['data_source']}_"
                                  f"Support_Resistance")
        sr.drop_table(sr.working_table_name)
        sr.create_table()

        for instrument in self.params["instruments"]:
            for timeframe in self.params["timeframes"]:
                source_table_name = (f"tbl_{self.params['data_source']}_"
                                     f"{instrument}_"
                                     f"{timeframe}_"
                                     f"f2_"
                                     f"k{self.params['cluster_count']}")

                self.logger.logger.info(f"Building - Support Resistance - "
                                        f"{source_table_name}")

                sr.set_source_table_name(source_table_name)
                sr.set_instrument_name(instrument)
                sr.set_timeframe(timeframe)
                sr.set_output_folder("sr")
                sr.set_fractal_period(2)
                sr.set_cluster_count(self.params["cluster_count"])
                sr.append_data_to_table()

        if self.params["to_csv"]:
            sr.to_csv(sr.working_table_name)

        self.logger.logger.info("Finished - Support Resistance")

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

    async def build_price_proximity(self):
        self.logger.logger.info("Starting - Price Proximity")
        pp = PriceProximity(self.db)
        pp.set_output_folder("price_proximity")
        pp.set_data_source(self.params["data_source"])
        pp.set_data_service(self.eod_data_service)
        pp.set_source_table_name(f"tbl_{self.params['data_source']}_"
                                 f"Support_Resistance")
        pp.set_working_table_name(f"tbl_{self.params['data_source']}_"
                                  f"PriceProximity")
        pp.reset_price_proximity_table()

        for instrument in self.params["instruments"]:
            for timeframe in self.params["timeframes"]:
                self.logger.logger.info(f"Building - Price Proximity - "
                                        f"{instrument} {timeframe}")
                pp.set_exchange("FOREX")
                pp.set_instrument_name(instrument)
                pp.set_timeframe(timeframe)
                pp.set_source_table_name(
                    f"tbl_{self.params['data_source']}_"
                    f"{instrument}_"
                    f"{timeframe}")
                await pp.append_price_atr()
                pp.calculate_price_proximity()

        if self.params["to_csv"]:
            pp.to_csv(pp.working_table_name)

        self.logger.logger.info("Finished - Price Proximity")

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

    def build_pattern_cd(self):
        self.logger.logger.info("Starting - Pattern Convergence Divergence")
        pcd = PatternCD(self.db)
        pcd.set_output_folder("pattern_cd")
        pcd.set_data_source(self.params["data_source"])
        pcd.set_working_table_name(f"tbl_{self.params['data_source']}_"
                                   f"pattern_cd")

        pcd.reset_pattern_convergence_divergence_table()
        for instrument in self.params["instruments"]:
            for timeframe in self.params["timeframes"]:
                for fractal_period in self.params["fractal_period"][timeframe]:
                    self.logger.logger.info(f"Building - "
                                            f"Pattern Convergence Divergence - "
                                            f"{instrument} {timeframe} "
                                            f"{fractal_period}")
                    pcd.set_instrument_name(instrument)
                    pcd.set_timeframe(timeframe)
                    pcd.set_fractal_period(fractal_period)
                    pcd.set_cluster_count(self.params["cluster_count"])
                    pcd.set_atr_threshold(self.params["atr_threshold"])
                    pcd.set_source_table_name(
                        f"tbl_{self.params['data_source']}_"
                        f"{instrument}_"
                        f"{timeframe}_"
                        f"f{fractal_period}_"
                        f"k{self.params['cluster_count']}")
                    pcd.generate_pattern_convergence_divergence()

        if self.params["to_csv"]:
            pcd.to_csv(pcd.working_table_name)

        self.logger.logger.info("Finished - Pattern Convergence Divergence")

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

            self.build_source_prep()
            self.build_fractal_cluster()
            self.build_support_resistance()
            self.build_trend()
            await self.build_price_proximity()
            self.build_rsi()
            self.build_macd_price_cd()
            self.build_pattern_cd()
            self.build_candle_pattern()
            self.build_summary()
            self.build_watchlist()
            self.build_pinescript()

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
