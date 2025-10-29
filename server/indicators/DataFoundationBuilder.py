class DataFoundationBuilder:
    def __init__(self, db):
        if hasattr(db, 'get_connection'):
            self.con = db.get_connection()
        else:
            self.con = db

        if self.con is None:
            raise ValueError("Failed to initialize database connection")

        self.data_source = None
        self.instrument_name = None
        self.timeframe = None
        self.source_table_name = None
        self.working_table_name = None
        self.output_folder = None
        self.summary_table_name = None

    def get_table_from_db(self, table_name: str):
        return self.con.sql(f"SELECT * FROM {table_name}")

    def drop_table(self, table_name: str):
        self.con.execute(f"DROP TABLE IF EXISTS {table_name}")

    def set_data_source(self, data_source: str):
        self.data_source = data_source

    def set_instrument_name(self, instrument_name: str):
        self.instrument_name = instrument_name

    def set_timeframe(self, timeframe: str):
        self.timeframe = timeframe

    def set_source_table_name(self, source_table_name: str):
        self.source_table_name = source_table_name

    def set_working_table_name(self, working_table_name: str):
        self.working_table_name = working_table_name

    def set_summary_table_name(self, summary_table_name: str):
        self.summary_table_name = summary_table_name

    def set_output_folder(self, output_folder: str):
        self.output_folder = output_folder

    def to_csv(self, table_name: str):
        self.con.sql(f"""
            SELECT * FROM {table_name}
        """).write_csv(f"outputs/{self.output_folder}/{table_name}.csv")

    def get_missing_records(self, source_table: str = None,
                            working_table: str = None,
                            reference_field: str = "timestamp",
                            trim_rows: int = 0) -> list[str]:

        if not working_table:
            raise ValueError("Working table must be specified")

        if source_table:
            working_subquery = f"SELECT timestamp FROM {working_table}"
            if trim_rows > 0:
                working_subquery += f" ORDER BY timestamp ASC OFFSET {trim_rows}"

            return self.con.sql(f"""
                SELECT timestamp
                FROM {source_table}
                WHERE timestamp NOT IN (
                    {working_subquery}
                )
                ORDER BY timestamp ASC
            """).fetchall()

        else:
            query = f"""
                SELECT timestamp
                FROM {working_table}
                WHERE {reference_field} IS NULL
            """
            if trim_rows > 0:
                query += f" ORDER BY timestamp ASC OFFSET {trim_rows}"
            else:
                query += " ORDER BY timestamp ASC"

            result = self.con.sql(query).fetchall()

            print(result)

            return result
