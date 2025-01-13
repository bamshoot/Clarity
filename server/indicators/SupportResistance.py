
from server.indicators.DataFoundationBuilder import DataFoundationBuilder


class SupportResistance(DataFoundationBuilder):
    def __init__(self, db_path: str):
        super().__init__(db_path)
        self.fractal_period = None
        self.cluster_count = None
        self.working_table_name = (f"tbl_{self.data_source}_SupportResistance")

    def create_table(self):
        self.con.sql(f"""
            CREATE TABLE {self.working_table_name}
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

    def set_fractal_period(self, fractal_period: int):
        self.fractal_period = fractal_period

    def set_cluster_count(self, cluster_count: int):
        self.cluster_count = cluster_count

    def append_data_to_table(self):
        query = f"""
            INSERT INTO {self.working_table_name}
            SELECT DISTINCT
                '{self.instrument_name}' as instrument_name,
                '{self.timeframe}' as timeframe,
                clust,
                cent,
                centDistMean,
                centCount,
                centDistLstCandle,
                centDistLstCandleRank,
                centDistMeanRank,
                centCountRank,
                score,
                overallRank
            FROM {self.source_table_name}
        """
        self.con.execute(query)
