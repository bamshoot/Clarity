from ..utils.db import get_table
import pandas as pd
from ..indicators.williams_fractal import williams_fractal
import kmeans1d
import duckdb


class DataFoundationBuilder:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def get_candles_from_db(self, table_name: str):
        return get_table(self.db_path, table_name)

    def create_close_data(self, df: pd.DataFrame):
        last_close = df.iloc[-1].close
        df['disLstClose'] = abs(df.close - last_close)
        return df

    def create_fractal_data(
            self, df: pd.DataFrame, candle_price_point: str, period: int = 2):
        fractal = williams_fractal(df, candle_price_point, period)
        fractal = df.join(fractal).sort_index()
        fractal = fractal[(fractal['uf'] == 1) | (fractal['lf'] == 1)]
        fractal['f'] = period
        return fractal

    def create_cluster_data(
            self, df: pd.DataFrame, candle_price_point: str, k: int = 5):
        clusters, centroids = kmeans1d.cluster(df[candle_price_point], k)
        cent_clust = []
        for clust in clusters:
            cent_clust.append(centroids[clust])
        df['clust'] = clusters
        df['cent'] = cent_clust
        df["k"] = k
        return df

    def create_centroid_dist_close(self, df: pd.DataFrame):
        df['centDistClose'] = abs(df['cent'] - df['close'])
        return df

    def create_cluster_agg_data(self, df: pd.DataFrame):
        df['centCount'] = df.groupby('clust')['cent'].transform('count')
        df['centMean'] = df.groupby('clust')['centDistClose'].transform('mean')
        df['idxExpMean'] = df.groupby('clust')['idxExp'].transform('mean')
        return df

    def create_cluster_rank_data(self, df: pd.DataFrame):
        df['cenCountRank'] = df.groupby(
            'clust')['cent'].rank(ascending=False)
        df['centMeanRank'] = df.groupby(
            'clust')['centDistClose'].rank(ascending=False)
        df['idxExpMeanRank'] = df.groupby(
            'clust')['idxExp'].rank(ascending=False)
        df['centDistCloseRank'] = df.groupby(
            'clust')['centDistClose'].rank(method='max')
        df['disLstCloseRank'] = df['disLstClose'].rank()
        return df

    def get_top_dis_lst_close(self, df: pd.DataFrame, n: int = 1):
        df = df.sort_values(by=['disLstClose'], ascending=True)
        df = df.head(n)
        return df
