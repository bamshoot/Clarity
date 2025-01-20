import time
from services.eod_data import EODData
from config.config import Config
from indicators.FractalCluster import FractalCluster
from indicators.CandlePattern import CandlePattern
from indicators.PatternCD import PatternCD
from indicators.MACDPriceCD import MACDPriceCD
from indicators.RSI import RSI
from indicators.Trend import Trend
from indicators.SupportResistance import SupportResistance
from indicators.Pinescript import Pinescript
from indicators.PriceProximity import PriceProximity
from indicators.Summary import Summary
from indicators.Watchlist import Watchlist
from utils.logger import Logger
import asyncio


def build_fractal_cluster(config: Config):
    logger.logger.info("Starting - Fractal/Cluster")
    fc = FractalCluster(
        config.DB_PATH,
        params["max_bars"],
        params["cluster_count"],
        params["outlier_threshold"],
        params["candle_price_point"])

    for instrument in params["instruments"]:
        for timeframe in params["timeframes"]:
            for fractal_period in params["fractal_period"][timeframe]:

                source_table_name = (f"tbl_{params['data_source']}_"
                                     f"{instrument}_"
                                     f"{timeframe}")

                fc.set_source_table_name(source_table_name)

                working_table_name = (f"tbl_{params['data_source']}_"
                                      f"{instrument}_"
                                      f"{timeframe}_"
                                      f"f{fractal_period}_"
                                      f"k{params['cluster_count']}")

                fc.set_working_table_name(working_table_name)

                logger.logger.info(f"Building - Fractal/Cluster - {working_table_name}")

                fc.reset_table()
                fc.set_instrument_name(instrument)
                fc.set_timeframe(timeframe)
                fc.set_fractal_period(fractal_period)
                fc.set_output_folder("fractals")
                fc.set_threshold()
                fc.generate_input_data()
                fc.generate_last_candle_price()
                fc.generate_index_data()
                fc.generate_fractal_data()
                fc.generate_cluster_data()
                fc.generate_cent_dist()
                fc.remove_outliers()
                fc.generate_cent_dist_lst_candle()
                fc.generate_cent_count()
                fc.generate_score()
                fc.generate_rank()

                if params["to_csv"]:
                    fc.to_csv(working_table_name)

    logger.logger.info("Finished - Fractal/Cluster")


def build_support_resistance(config: Config):
    logger.logger.info("Starting - Support Resistance")
    sr = SupportResistance(config.DB_PATH)
    sr.set_data_source(params["data_source"])
    sr.set_working_table_name(f"tbl_{params['data_source']}_"
                              f"Support_Resistance")
    sr.drop_table(sr.working_table_name)
    sr.create_table()

    for instrument in params["instruments"]:
        for timeframe in params["timeframes"]:
            source_table_name = (f"tbl_{params['data_source']}_"
                                 f"{instrument}_"
                                 f"{timeframe}_"
                                 f"f2_"
                                 f"k{params['cluster_count']}")

            logger.logger.info(f"Building - Support Resistance - {source_table_name}")

            sr.set_source_table_name(source_table_name)
            sr.set_instrument_name(instrument)
            sr.set_timeframe(timeframe)
            sr.set_output_folder("sr")
            sr.set_fractal_period(2)
            sr.set_cluster_count(params["cluster_count"])
            sr.append_data_to_table()

    if params["to_csv"]:
        sr.to_csv(sr.working_table_name)

    logger.logger.info("Finished - Support Resistance")


def build_pinescript(config: Config):
    logger.logger.info("Starting - Pinescript")
    pinescript = Pinescript(config.DB_PATH)
    pinescript.set_data_source(params["data_source"])
    pinescript.set_output_folder("pinescript")
    pinescript.set_source_table_name(f"tbl_{params['data_source']}_"
                                     f"Support_Resistance")
    pinescript.build_pinescript(pinescript.source_table_name)

    logger.logger.info("Finished - Pinescript")


def build_trend(config: Config, trends: dict):
    logger.logger.info("Starting - Trend")
    trend = Trend(config.DB_PATH, trends)
    trend.set_data_source(params["data_source"])
    trend.set_output_folder("trends")
    trend.set_source_table_name("tbl_trend_params")
    trend.set_working_table_name(f"tbl_{params['data_source']}_Trends")
    trend.reset_trends_table()

    for instrument in params["instruments"]:
        for timeframe in params["timeframes"]:
            trend.set_instrument_name(instrument)
            trend.set_timeframe(timeframe)
            trend.set_source_table_name(f"tbl_{params['data_source']}_"
                                        f"{instrument}_"
                                        f"{timeframe}")
            logger.logger.info(f"Building - Trend - {trend.source_table_name}")
            trend.generate_trends()

    if params["to_csv"]:
        trend.to_csv(trend.working_table_name)

    logger.logger.info("Finished - Trend")


async def build_price_proximity(config: Config, eod_data_service: EODData):
    logger.logger.info("Starting - Price Proximity")
    pp = PriceProximity(config.DB_PATH)
    pp.set_output_folder("price_proximity")
    pp.set_data_source(params["data_source"])
    pp.set_data_service(eod_data_service)
    pp.set_source_table_name(f"tbl_{params['data_source']}_"
                             f"Support_Resistance")
    pp.set_working_table_name(f"tbl_{params['data_source']}_"
                              f"PriceProximity")
    pp.reset_price_proximity_table()

    for instrument in params["instruments"]:
        for timeframe in params["timeframes"]:
            logger.logger.info(f"Building - Price Proximity - {instrument} {timeframe}")
            pp.set_exchange("FOREX")
            pp.set_instrument_name(instrument)
            pp.set_timeframe(timeframe)
            pp.set_source_table_name(
                f"tbl_{params['data_source']}_"
                f"{instrument}_"
                f"{timeframe}")
            await pp.append_price_atr()
            pp.calculate_price_proximity()

    if params["to_csv"]:
        pp.to_csv(pp.working_table_name)

    logger.logger.info("Finished - Price Proximity")


def build_rsi(config: Config):
    logger.logger.info("Starting - RSI")
    rsi = RSI(config.DB_PATH)
    rsi.set_data_source(params["data_source"])
    rsi.set_pair_table_name(f"tbl_{params['data_source']}_pair_RSI_Rank")
    rsi.set_currency_table_name(f"tbl_{params['data_source']}_currency_RSI_Rank")
    rsi.reset_rsi_ranks_table()
    rsi.set_output_folder("rsi")

    for instrument in params["instruments"]:
        for timeframe in params["timeframes"]:
            logger.logger.info(f"Building - RSI - {instrument} {timeframe}")
            rsi.set_instrument_name(instrument)
            rsi.set_timeframe(timeframe)
            rsi.set_source_table_name(f"tbl_{params['data_source']}_"
                                      f"{instrument}_"
                                      f"{timeframe}")
            rsi.generate_rsi()

    rsi.generate_pair_timeframe_rank()
    rsi.generate_currency_rsi()
    rsi.generate_base_quote_timeframe_rank()

    if params["to_csv"]:
        rsi.to_csv(rsi.pair_table_name)
        rsi.to_csv(rsi.currency_table_name)

    logger.logger.info("Finished - RSI")


def build_macd_price_cd(config: Config):
    logger.logger.info("Starting - MACD Price Convergence Divergence")
    macdpcd = MACDPriceCD(config.DB_PATH)
    macdpcd.set_output_folder("macd_price_cd")
    macdpcd.set_data_source(params["data_source"])
    macdpcd.set_working_table_name(f"tbl_{params['data_source']}_"
                                   f"macd_price_cd")
    macdpcd.reset_macd_convergence_divergence_table()

    for instrument in params["instruments"]:
        for timeframe in params["timeframes"]:
            logger.logger.info(f"Building - MACD Price Convergence Divergence - "
                               f"{instrument} {timeframe}")
            macdpcd.set_instrument_name(instrument)
            macdpcd.set_timeframe(timeframe)
            macdpcd.set_source_table_name(f"tbl_{params['data_source']}_"
                                          f"{instrument}_"
                                          f"{timeframe}")
            macdpcd.generate_macd_convergence_divergence()

    if params["to_csv"]:
        macdpcd.to_csv(macdpcd.working_table_name)


def build_pattern_cd(config: Config):
    logger.logger.info("Starting - Pattern Convergence Divergence")
    pcd = PatternCD(config.DB_PATH)
    pcd.set_output_folder("pattern_cd")
    pcd.set_data_source(params["data_source"])
    pcd.set_working_table_name(f"tbl_{params['data_source']}_"
                               f"pattern_cd")

    pcd.reset_pattern_convergence_divergence_table()
    for instrument in params["instruments"]:
        for timeframe in params["timeframes"]:
            for fractal_period in params["fractal_period"][timeframe]:
                logger.logger.info(f"Building - Pattern Convergence Divergence - "
                                   f"{instrument} {timeframe} {fractal_period}")
                pcd.set_instrument_name(instrument)
                pcd.set_timeframe(timeframe)
                pcd.set_fractal_period(fractal_period)
                pcd.set_cluster_count(params["cluster_count"])
                pcd.set_atr_threshold(params["atr_threshold"])
                pcd.set_source_table_name(
                    f"tbl_{params['data_source']}_"
                    f"{instrument}_"
                    f"{timeframe}_"
                    f"f{fractal_period}_"
                    f"k{params['cluster_count']}")
                pcd.generate_pattern_convergence_divergence()

    if params["to_csv"]:
        pcd.to_csv(pcd.working_table_name)

    logger.logger.info("Finished - Pattern Convergence Divergence")


def build_candle_pattern(config: Config):
    logger.logger.info("Starting - Candle Patterns")
    candle_pattern = CandlePattern(config.DB_PATH, candle_patterns)
    candle_pattern.set_data_source(params["data_source"])
    candle_pattern.set_output_folder("candle_patterns")
    candle_pattern.set_candle_pattern_params_table_name(
        "tbl_candle_patterns_params")
    candle_pattern.reset_candle_pattern_params_table()
    candle_pattern.set_last_n_aggregated_table_name(
        f"tbl_{params['data_source']}_candle_patterns_last_n_aggregated")
    candle_pattern.reset_last_n_aggregated_table()

    for instrument in params["instruments"]:
        for timeframe in params["timeframes"]:
            logger.logger.info(f"Building - Candle Patterns - {instrument} {timeframe}")
            candle_pattern.set_instrument_name(instrument)
            candle_pattern.set_timeframe(timeframe)
            candle_pattern.set_source_table_name(f"tbl_{params['data_source']}_"
                                                 f"{instrument}_"
                                                 f"{timeframe}")
            candle_pattern.set_working_table_name(f"tbl_{params['data_source']}_"
                                                  f"{instrument}_"
                                                  f"{timeframe}_"
                                                  f"candle_patterns")
            candle_pattern.set_last_n_rows_table_name(f"tbl_{params['data_source']}_"
                                                      f"{instrument}_"
                                                      f"{timeframe}_"
                                                      f"last_n_rows")
            candle_pattern.reset_candle_pattern_table()
            candle_pattern.generate_candle_patterns()
            candle_pattern.reset_candle_pattern_last_n_rows()
            candle_pattern.generate_candle_pattern_last_n_rows(10)
            candle_pattern.generate_last_n_aggregated_data()

            if params["to_csv"]:
                candle_pattern.to_csv(candle_pattern.working_table_name)
                candle_pattern.to_csv(candle_pattern.last_n_rows_table_name)

    if params["to_csv"]:
        candle_pattern.to_csv(candle_pattern.last_n_aggregated_table_name)

    logger.logger.info("Finished - Candle Patterns")


def build_summary(config: Config):
    logger.logger.info("Starting - Summary")
    summary = Summary(config.DB_PATH)
    summary.set_data_source(params["data_source"])
    summary.set_output_folder("summary")
    summary.set_working_table_name(f"tbl_{params['data_source']}_summary")
    summary.drop_table(summary.working_table_name)
    summary.create_summary_table()

    if params["to_csv"]:
        summary.to_csv(summary.working_table_name)

    logger.logger.info("Finished - Summary")


def build_watchlist(config: Config):
    logger.logger.info("Starting - Watchlist")
    watchlist = Watchlist(config.DB_PATH)
    watchlist.set_source_table_name(f"tbl_{params['data_source']}_summary")
    watchlist.build_watchlist()

    logger.logger.info("Finished - Watchlist")


if __name__ == "__main__":

    config = Config()
    eod_data_service = EODData(config.EOD_URL, config.EOD_API_KEY)
    params = config.EOD_MnTrd_PARAMS
    trends = config.Trends
    candle_patterns = config.Candle_Patterns

    logger = Logger("manual_trading_identification")

    start_time = time.time()

    logger.logger.info("Starting - Manual Trading Identification")
    build_fractal_cluster(config)
    build_support_resistance(config)
    build_trend(config, trends)
    asyncio.run(build_price_proximity(config, eod_data_service))
    build_rsi(config)
    build_macd_price_cd(config)
    build_pattern_cd(config)
    build_candle_pattern(config)
    build_summary(config)
    build_watchlist(config)
    build_pinescript(config)

    logger.logger.info("Finished - Manual Trading Identification")
    end_time = time.time()
    logger.logger.info(f"Time taken: {end_time - start_time} seconds")
