from .DataFoundationBuilder import DataFoundationBuilder
import datetime


class Watchlist(DataFoundationBuilder):
    def __init__(self, db_path: str):
        super().__init__(db_path)

    def build_watchlist(self):

        con5 = self.con.sql(f"""
                            SELECT *
                            FROM {self.source_table_name}
                            WHERE abs_total = 5
                            """).fetchall()

        con4 = self.con.sql(f"""
                            SELECT *
                            FROM {self.source_table_name}
                            WHERE abs_total = 4
                            """).fetchall()

        con3 = self.con.sql(f"""
                            SELECT *
                            FROM {self.source_table_name}
                            WHERE abs_total = 3
                            """).fetchall()

        con2 = self.con.sql(f"""
                            SELECT *
                            FROM {self.source_table_name}
                            WHERE abs_total = 2
                            """).fetchall()

        con1 = self.con.sql(f"""
                            SELECT *
                            FROM {self.source_table_name}
                            WHERE abs_total = 1
                            """).fetchall()

        con0 = self.con.sql(f"""
                            SELECT *
                            FROM {self.source_table_name}
                            WHERE abs_total = 0
                            """).fetchall()

        output = ""

        if con5:
            output += "###Confluence = 5,"
            for row in con5:
                output += f"OANDA:{row[0]},"

        if con4:
            output += "###Confluence = 4,"
            for row in con4:
                output += f"OANDA:{row[0]},"

        if con3:
            output += "###Confluence = 3,"
            for row in con3:
                output += f"OANDA:{row[0]},"

        if con2:
            output += "###Confluence = 2,"
            for row in con2:
                output += f"OANDA:{row[0]},"

        if con1:
            output += "###Confluence = 1,"
            for row in con1:
                output += f"OANDA:{row[0]},"

        if con0:
            output += "###Confluence = 0,"
            for row in con0:
                output += f"OANDA:{row[0]},"

        with open(
            f"./outputs/watchlist/watchlist_"
            f"{datetime.datetime.now().strftime('%Y-%m-%d')}.txt",
            "w",
        ) as f:
            f.write(output)
