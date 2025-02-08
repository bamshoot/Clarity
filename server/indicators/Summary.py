from .DataFoundationBuilder import DataFoundationBuilder


class Summary(DataFoundationBuilder):
    def __init__(self, db_connection):
        super().__init__(db_connection)

    def create_summary_table(self):
        self.con.sql(f"""
            CREATE TABLE IF NOT EXISTS {self.working_table_name} AS
            SELECT *
            FROM
                {self.source_table_name}
        """)

    def get_column_names(self, table_name: str):
        result = self.con.sql(f"""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = '{table_name}'
        """).fetchall()
        # Extract column names from the result tuples
        return [row[0] for row in result]

    def delete_last_5_rows(self):
        self.con.sql(f"""
            DELETE FROM {self.working_table_name}
            WHERE timestamp IN (
                SELECT timestamp
                FROM {self.working_table_name}
                ORDER BY timestamp DESC
                LIMIT 5
            )
        """)

    def get_timestamps_in_raw_not_in_summary(self):
        return self.con.sql(f"""
            SELECT
                ROW_NUMBER() OVER (ORDER BY timestamp DESC) - 1 as row_num,
                timestamp
            FROM {self.source_table_name}
            WHERE timestamp NOT IN (
                SELECT timestamp FROM {self.working_table_name}
            )
            ORDER BY timestamp DESC
        """).fetchall()

    def append_rows_to_summary_table(self):
        source_columns = self.get_column_names(self.source_table_name)
        working_columns = self.get_column_names(self.working_table_name)

        common_columns = [col for col in source_columns if col in working_columns]

        self.con.sql(f"""
            INSERT INTO {self.working_table_name} ({', '.join(common_columns)})
            SELECT {', '.join(common_columns)}
            FROM {self.source_table_name}
            WHERE timestamp NOT IN (
                SELECT timestamp FROM {self.working_table_name}
            )
        """)
