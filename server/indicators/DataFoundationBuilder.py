class DataFoundationBuilder:
    def __init__(self, db):
        if hasattr(db, 'get_connection'):
            # If passed a DB instance
            self.con = db.get_connection()
        else:
            # If passed a direct connection
            self.con = db

        if self.con is None:
            raise ValueError("Failed to initialize database connection")

        self.data_source = None
        self.instrument_name = None
        self.timeframe = None
        self.source_table_name = None
        self.working_table_name = None
        self.output_folder = None

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

    def set_output_folder(self, output_folder: str):
        self.output_folder = output_folder

    def to_csv(self, table_name: str):
        self.con.sql(f"""
            SELECT * FROM {table_name}
        """).write_csv(f"outputs/{self.output_folder}/{table_name}.csv")
