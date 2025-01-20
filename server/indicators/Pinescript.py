from .DataFoundationBuilder import DataFoundationBuilder
import os
import datetime


class Pinescript(DataFoundationBuilder):
    def __init__(self, db_path: str):
        super().__init__(db_path)

    def _reset_pinescript_file(self):
        for file in os.listdir(f"./outputs/{self.output_folder}"):
            with open(f"./outputs/{self.output_folder}/{file}", "w") as f:
                instrument_name = file.split("_")[1]
                instrument_name = instrument_name.replace(".txt", "")
                f.write(f"""
// This Pine Script™ code is subject to the terms of the Mozilla Public License 2.0
// at https://mozilla.org/MPL/2.0/
// © bamshoot

//@version=6
indicator("{instrument_name} Support And Resistance - {
    datetime.datetime.now().strftime('%Y-%m-%d')}", overlay = true)

show_1h = input(defval = true, title = "Show 1 Hour SR")
show_d = input(defval = true, title = "Show Daily SR")
show_w = input(defval = true, title = "Show Weekly SR")
show_m = input(defval = true, title = "Show Monthly SR")
show_label = input(defval = true, title = "Show Labels")
label_position = input(defval = -100, title ="Label Back Position")

symbol = syminfo.ticker

""")

    def build_pinescript(self, table_name: str):
        self._reset_pinescript_file()

        sr = self.get_table_from_db(table_name).fetchall()

        show_timeframe = None
        color = None

        for row in sr:

            instrument_name = row[0]

            if row[1] == "1h":
                show_timeframe = "show_1h"
                color = "color.new(color.green, 70)"
            elif row[1] == "d":
                show_timeframe = "show_d"
                color = "color.new(color.blue, 70)"
            elif row[1] == "w":
                show_timeframe = "show_w"
                color = "color.new(color.orange, 70)"
            elif row[1] == "m":
                show_timeframe = "show_m"
                color = "color.new(color.red, 70)"

            if abs(row[7]) < 2 or row[11] < 4:
                show = "display = display.all"
            else:
                show = "display = display.none"

            file_name = f"{self.data_source}_{instrument_name}"

            with open(f"./outputs/{self.output_folder}/{file_name}.txt", "a") as f:
                f.write(f"""plot({show_timeframe} and"""
                        f""" symbol == '{row[0]}'?{row[3]:.4f}:na,"""
                        f""" "Proximity Rank = {row[7]}","""
                        f""" color = {color}, linewidth = 4,"""
                        f""" editable = true, {show})\n"""
                        f"""if (bar_index == last_bar_index) and show_label"""
                        f""" and {show_timeframe}\n"""
                        f"""    label.new(x=bar_index-label_position, """
                        f"""y={row[3]:.4f}, """
                        f"""text = str.tostring({row[3]:.4f}), color={color}, """
                        f"""textcolor=color.white, """
                        f"""tooltip = "Cent Distance Mean = """
                        f"""{row[4]:.4f}\\nCent Count = {row[5]}\\nCent """
                        f"""Distance Mean Rank = {row[8]}\\nCent Count Rank = """
                        f"""{row[9]}\\nScore = {row[10]:.4f}\\n"""
                        f"""Overall Rank = {row[11]}")\n""")
