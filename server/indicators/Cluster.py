import kmeans1d
from collections import Counter
import pandas as pd

from .DataFoundationBuilder import DataFoundationBuilder


class Cluster(DataFoundationBuilder):
    def __init__(self,
                 db_connection,
                 max_bars: int,
                 cluster_count: int,
                 outlier_threshold: float,
                 candle_price_point: str):
        super().__init__(db_connection)
        self.max_bars = max_bars
        self.window_position = None
        self.timestamp = None
        self.date = None
        self.datetime = None
        self.cluster_count = cluster_count
        self.candle_price_point = candle_price_point
        self.summary_table_name = None
        self.threshold = None
        self.last_close = None
        self.mxTimestamp = None
        self.mnTimestamp = None
        self.previous_mxTimestamp = None
        self.result_df = None

    def set_summary_table_name(self, summary_table_name: str):
        self.summary_table_name = summary_table_name

    def get_fractal_timestamps(self):
        return self.con.sql(f"""
            SELECT timestamp
            FROM {self.source_table_name}
            ORDER BY timestamp ASC
        """).fetchall()

    def _set_fractal_timestamps(self, mxTimestamp, mnTimestamp):
        self.mxTimestamp = mxTimestamp
        self.mnTimestamp = mnTimestamp

    def _set_previous_mxTimestamp(self, mxTimestamp):
        self.previous_mxTimestamp = mxTimestamp

    def set_window_position(self, index: int):
        self.window_position = index

    def _create_cluster_table(self):

        self.con.sql(f"""
            CREATE TABLE {self.working_table_name} AS
                SELECT *
                FROM {self.source_table_name}
        """)

        self.con.sql(f"""
            DELETE FROM {self.working_table_name}
        """)

        columns = [
            'k INTEGER',
            'o DOUBLE',
            'lstClose DOUBLE',
            'clust INTEGER',
            'cent DOUBLE',
            'centDist DOUBLE',
            'centDistMean DOUBLE',
            'centDistMeanInv DOUBLE',
            'centDistLstClose DOUBLE',
            'centCount DOUBLE',
            'centDistMeanRank DOUBLE',
            'centCountRank DOUBLE',
            'centDistLstCloseRank DOUBLE',
            'score DOUBLE',
            'overallRank DOUBLE'
        ]

        for column_def in columns:
            self.con.sql(f"""
                ALTER TABLE {self.working_table_name}
                ADD COLUMN {column_def}
            """)

    def reset_table(self):
        self.drop_table(self.working_table_name)
        self._create_cluster_table()

    def add_columns_to_summary_table(self):
        columns = []

        for i in range(1, 11):
            columns.extend([
                f'cent_p{i} DOUBLE',
                f'overallRank_p{i} DOUBLE',
                f'cent_n{i} DOUBLE',
                f'overallRank_n{i} DOUBLE'
            ])

        for column_def in columns:
            self.con.sql(f"""
                ALTER TABLE {self.summary_table_name}
                ADD COLUMN IF NOT EXISTS {column_def}
            """)

    def count_cluster_occurrences(self, clusters):
        """Count occurrences of each cluster"""
        cluster_counts = Counter(clusters)
        return dict(cluster_counts)

    def create_cluster_summary_df(self, clusters, centroids, close):
        """Create a DataFrame with cluster, centroid, and count columns"""
        cluster_counts = self.count_cluster_occurrences(clusters)

        cluster_data = []
        for cluster_id in range(len(centroids)):
            count = cluster_counts.get(cluster_id, 0)
            centDist = centroids[cluster_id] - close
            centDistAbs = abs(centroids[cluster_id] - close)
            centDistMean = (abs(centroids[cluster_id] - close) / count
                            if count > 0 else 0)
            centDistMeanInv = 1 / centDistMean if centDistMean > 0 else 0
            centDistLstClose = centroids[cluster_id] - close
            score = count * centDistMeanInv

            cluster_data.append({
                'cluster': cluster_id,
                'centroid': centroids[cluster_id],
                'count': count,
                'lstClose': close,
                'centDist': centDist,
                'centDistAbs': centDistAbs,
                'centDistMean': centDistMean,
                'centDistMeanInv': centDistMeanInv,
                'centDistLstClose': centDistLstClose,
                'score': score
            })

        return pd.DataFrame(cluster_data)

    def generate_cluster_data(self):
        df = self.con.sql(f"""
            SELECT *
            FROM {self.source_table_name}
            ORDER BY datetime ASC
            LIMIT {self.max_bars}
            OFFSET {self.window_position}
        """).to_df()

        df = df[df[self.candle_price_point] <=
                df[self.candle_price_point].quantile(0.95)]
        df = df[df[self.candle_price_point] >=
                df[self.candle_price_point].quantile(0.05)]

        clusters, centroids = kmeans1d.cluster(df[self.candle_price_point],
                                               self.cluster_count)

        close = df[self.candle_price_point].iloc[-1]

        cluster_summary_df = self.create_cluster_summary_df(clusters, centroids, close)

        cluster_summary_df['centDistMeanRank'] = (
            cluster_summary_df['centDistMean'].rank(method='min', ascending=True)
        )
        cluster_summary_df['centCountRank'] = (
            cluster_summary_df['count'].rank(method='min', ascending=False)
        )
        cluster_summary_df['overallRank'] = (
            cluster_summary_df['centDistMeanRank'] + cluster_summary_df['centCountRank']
        ) / 2

        pos_df = cluster_summary_df[cluster_summary_df['centDistLstClose'] > 0].copy()
        neg_df = cluster_summary_df[cluster_summary_df['centDistLstClose'] < 0].copy()

        if not pos_df.empty:
            pos_df['centDistLstCloseRank'] = pos_df['centDistLstClose'].abs().rank(
                method='dense', ascending=True
            )

        if not neg_df.empty:
            neg_df['centDistLstCloseRank'] = -neg_df['centDistLstClose'].abs().rank(
                method='dense', ascending=True
            )

        result_df = pd.concat([pos_df, neg_df])

        # Only merge if result_df has the required columns
        if not result_df.empty and 'centDistLstCloseRank' in result_df.columns:
            cluster_summary_df = pd.merge(
                cluster_summary_df,
                result_df[['centroid', 'centDistLstCloseRank']],
                on='centroid',
                how='left'
            )
        else:
            # Add empty centDistLstCloseRank column if it doesn't exist
            cluster_summary_df['centDistLstCloseRank'] = None

        self._set_fractal_timestamps(df['timestamp'].max(), df['timestamp'].min())

        cluster_summary_df['mxTimestamp'] = self.mxTimestamp
        cluster_summary_df['mnTimestamp'] = self.mnTimestamp

        cluster_summary_df['k'] = self.cluster_count

        result_data = {
            'mxTimestamp': [self.mxTimestamp],
            'mnTimestamp': [self.mnTimestamp]
        }

        # Initialize all columns with None values
        for i in range(1, 11):
            result_data[f'cent_p{i}'] = [None]
            result_data[f'overallRank_p{i}'] = [None]
            result_data[f'cent_n{i}'] = [None]
            result_data[f'overallRank_n{i}'] = [None]

        pos_ranks = (cluster_summary_df[
            cluster_summary_df['centDistLstCloseRank'] > 0
        ].sort_values('centDistLstCloseRank'))
        neg_ranks = (cluster_summary_df[
            cluster_summary_df['centDistLstCloseRank'] < 0
        ].sort_values('centDistLstCloseRank', ascending=False))

        if not pos_ranks.empty:
            max_pos_rank = pos_ranks['centDistLstCloseRank'].max()
        else:
            max_pos_rank = 0
        if not neg_ranks.empty:
            max_neg_rank = abs(neg_ranks['centDistLstCloseRank'].min())
        else:
            max_neg_rank = 0
        max_rank = max(max_pos_rank, max_neg_rank)

        for rank in range(1, int(max_rank) + 1):
            if rank <= 10:  # Only process up to rank 10
                pos_cluster = pos_ranks[
                    pos_ranks['centDistLstCloseRank'] == rank
                ]
                if not pos_cluster.empty:
                    result_data[f'cent_p{rank}'] = [pos_cluster.iloc[0]['centroid']]
                    result_data[f'overallRank_p{rank}'] = [
                        pos_cluster.iloc[0]['overallRank']
                    ]

                neg_cluster = neg_ranks[
                    neg_ranks['centDistLstCloseRank'] == -rank
                ]
                if not neg_cluster.empty:
                    result_data[f'cent_n{rank}'] = [neg_cluster.iloc[0]['centroid']]
                    result_data[f'overallRank_n{rank}'] = [
                        neg_cluster.iloc[0]['overallRank']
                    ]

        result_df = pd.DataFrame(result_data)

        # print("Cluster summary:")
        # print(cluster_summary_df)
        # print("\nRanked cluster summary:")
        # print(result_df)

        self.result_df = result_df

    def clear_summary_table(self):
        self.con.sql(f"""
            UPDATE {self.summary_table_name}
            SET cent_p1 = NULL, overallRank_p1 = NULL,
                cent_n1 = NULL, overallRank_n1 = NULL,
                cent_p2 = NULL, overallRank_p2 = NULL,
                cent_n2 = NULL, overallRank_n2 = NULL,
                cent_p3 = NULL, overallRank_p3 = NULL,
                cent_n3 = NULL, overallRank_n3 = NULL,
                cent_p4 = NULL, overallRank_p4 = NULL,
                cent_n4 = NULL, overallRank_n4 = NULL,
                cent_p5 = NULL, overallRank_p5 = NULL,
                cent_n5 = NULL, overallRank_n5 = NULL,
                cent_p6 = NULL, overallRank_p6 = NULL,
                cent_n6 = NULL, overallRank_n6 = NULL,
                cent_p7 = NULL, overallRank_p7 = NULL,
                cent_n7 = NULL, overallRank_n7 = NULL,
                cent_p8 = NULL, overallRank_p8 = NULL,
                cent_n8 = NULL, overallRank_n8 = NULL,
                cent_p9 = NULL, overallRank_p9 = NULL,
                cent_n9 = NULL, overallRank_n9 = NULL,
                cent_p10 = NULL, overallRank_p10 = NULL,
                cent_n10 = NULL, overallRank_n10 = NULL
        """)

    def update_summary_table(self):
        # Register the DataFrame as a temporary table
        temp_table_name = f"temp_result_{self.mxTimestamp}"
        self.con.register(temp_table_name, self.result_df)

        # Use UPDATE instead of INSERT to update existing rows
        self.con.sql(f"""
            UPDATE {self.summary_table_name}
            SET cent_p1 = t.cent_p1, overallRank_p1 = t.overallRank_p1,
                cent_n1 = t.cent_n1, overallRank_n1 = t.overallRank_n1,
                cent_p2 = t.cent_p2, overallRank_p2 = t.overallRank_p2,
                cent_n2 = t.cent_n2, overallRank_n2 = t.overallRank_n2,
                cent_p3 = t.cent_p3, overallRank_p3 = t.overallRank_p3,
                cent_n3 = t.cent_n3, overallRank_n3 = t.overallRank_n3,
                cent_p4 = t.cent_p4, overallRank_p4 = t.overallRank_p4,
                cent_n4 = t.cent_n4, overallRank_n4 = t.overallRank_n4,
                cent_p5 = t.cent_p5, overallRank_p5 = t.overallRank_p5,
                cent_n5 = t.cent_n5, overallRank_n5 = t.overallRank_n5,
                cent_p6 = t.cent_p6, overallRank_p6 = t.overallRank_p6,
                cent_n6 = t.cent_n6, overallRank_n6 = t.overallRank_n6,
                cent_p7 = t.cent_p7, overallRank_p7 = t.overallRank_p7,
                cent_n7 = t.cent_n7, overallRank_n7 = t.overallRank_n7,
                cent_p8 = t.cent_p8, overallRank_p8 = t.overallRank_p8,
                cent_n8 = t.cent_n8, overallRank_n8 = t.overallRank_n8,
                cent_p9 = t.cent_p9, overallRank_p9 = t.overallRank_p9,
                cent_n9 = t.cent_n9, overallRank_n9 = t.overallRank_n9,
                cent_p10 = t.cent_p10, overallRank_p10 = t.overallRank_p10,
                cent_n10 = t.cent_n10, overallRank_n10 = t.overallRank_n10
            FROM {temp_table_name} t
            WHERE {self.summary_table_name}.timestamp > {self.previous_mxTimestamp}
                AND {self.summary_table_name}.timestamp <= {self.mxTimestamp}
        """)

        # Clean up the temporary table
        self.con.sql(f"DROP VIEW IF EXISTS {temp_table_name}")

    def process_fractal_timestamps(self):

        self.clear_summary_table()
        """Main method to process fractal timestamps with increasing window size"""
        fractal_timestamps = self.get_fractal_timestamps()

        # print(f"Found {len(fractal_timestamps)} fractal timestamps")

        self._set_previous_mxTimestamp(fractal_timestamps[self.max_bars-1][0])
        # print(f"Previous mxTimestamp: {self.previous_mxTimestamp}")

        for i, (timestamp,) in enumerate(fractal_timestamps):

            print(f"Timestamp: {timestamp}")
            print(f"Window size: {self.max_bars}")
            print(f"Window position: {self.window_position}")

            self.set_window_position(i)
            self.reset_table()
            self.generate_cluster_data()
            self.update_summary_table()

            self._set_previous_mxTimestamp(self.mxTimestamp)
