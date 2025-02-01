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

    def append_rows_to_summary_table(self):
        self.con.sql(f"""
            INSERT INTO {self.working_table_name}
            SELECT *
            FROM {self.source_table_name}
            WHERE timestamp NOT IN (
                SELECT timestamp FROM {self.working_table_name}
            )
        """)
