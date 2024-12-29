import pandas as pd
from indicators.williams_fractal import williams_fractal
import kmeans1d
import duckdb


class DataFoundationBuilder:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.con = duckdb.connect(self.db_path)

    def __del__(self):
        if hasattr(self, 'con'):
            self.con.close()

    def get_table_from_db(self, table_name: str):
        return self.con.sql(f"SELECT * FROM {table_name}").df()

    def create_close_data(self, df: pd.DataFrame):
        last_close = df.iloc[-1].close
        return self.con.execute("""
            SELECT *, ABS(close - ?) as disLstClose
            FROM df
        """, [last_close]).df()

    def create_fractal_data(
            self,
            df: pd.DataFrame,
            candle_price_point: str,
            instrument_name: str,
            period: int = 2):

        table_name = f"tbl_{instrument_name}_fractals"

        fractal = williams_fractal(df, candle_price_point, period)
        print(fractal)
        fractal = df.join(fractal).sort_index()
        fractal = fractal[(fractal['uf'] == 1) | (fractal['lf'] == 1)]
        fractal['f'] = period

        self.con.execute(f"DROP TABLE IF EXISTS {table_name}")
        self.con.execute(f"""
            CREATE TABLE {table_name} AS
            SELECT * FROM fractal
        """)

        return self.con.sql(f"SELECT * FROM {table_name}").df()

    def create_cluster_data(
            self, df: pd.DataFrame, candle_price_point: str, k: int = 5):
        clusters, centroids = kmeans1d.cluster(df[candle_price_point], k)
        cent_clust = [centroids[clust] for clust in clusters]

        duckdb.register("temp_df", df)
        duckdb.register("temp_clusters", pd.DataFrame({
            'row_num': range(len(clusters)),
            'clust': clusters,
            'cent': cent_clust
        }))

        return duckdb.sql("""
            SELECT t.*, c.clust, c.cent, ? as k
            FROM temp_df t
            JOIN temp_clusters c ON c.row_num = ROW_NUMBER() OVER () - 1
        """, [k]).df()

    def create_centroid_dist_close(self, df: pd.DataFrame):
        return duckdb.sql("""
            SELECT *, ABS(cent - close) as centDistClose
            FROM df
        """).df()

    def create_cluster_agg_data(self, df: pd.DataFrame):
        return duckdb.sql("""
            SELECT *,
                COUNT(cent) OVER (PARTITION BY clust) as centCount,
                AVG(centDistClose) OVER (PARTITION BY clust) as centMean,
                AVG(idxExp) OVER (PARTITION BY clust) as idxExpMean
            FROM df
        """).df()

    def create_cluster_rank_data(self, df: pd.DataFrame):
        return duckdb.sql("""
            SELECT *,
                RANK() OVER (
                    PARTITION BY clust ORDER BY cent DESC
                ) as cenCountRank,
                RANK() OVER (
                    PARTITION BY clust ORDER BY centDistClose DESC
                ) as centMeanRank,
                RANK() OVER (
                    PARTITION BY clust ORDER BY idxExp DESC
                ) as idxExpMeanRank,
                RANK() OVER (
                    PARTITION BY clust ORDER BY centDistClose
                ) as centDistCloseRank,
                RANK() OVER (ORDER BY disLstClose) as disLstCloseRank
            FROM df
        """).df()

    def get_top_dis_lst_close(self, df: pd.DataFrame, n: int = 1):
        return duckdb.sql("""
            SELECT *
            FROM df
            ORDER BY disLstClose ASC
            LIMIT ?
        """, [n]).df()


data_foundation_builder = DataFoundationBuilder("database/clarity.db")
data = data_foundation_builder.get_table_from_db("tbl_EOD_AUDCAD_d")
close_data = data_foundation_builder.create_close_data(data)
fractal_data = data_foundation_builder.create_fractal_data(
    close_data, "close", "EOD_AUDCAD_d")
print(fractal_data)
