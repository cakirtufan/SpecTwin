# -*- coding: utf-8 -*-
"""
Created on Mon Apr 14 11:38:58 2025

@author: cakir
"""


import os
import sys
from pathlib import Path

source_dir = Path(__file__).resolve().parents[1]
utils_path = str(source_dir / "Utils")
if utils_path not in sys.path:
    sys.path.append(utils_path)
    
from HDF5Reader import HDF5Reader
from XRFAnalyzer import XRFAnalyzer

import dearpygui.dearpygui as dpg

class DataVisualizationUI:
    def __init__(self, parent):
        self.parent = parent
        self.prefix = "datavisu"
        self.analyzer = XRFAnalyzer()
        self.hdf5_readers = {}
        self.file_list = []     # basenames for UI
        self.file_map = {}      # basename -> fullpath
        self.plotted_data = set()
        self.series_count = 0

        self.plot_tag = f"{self.prefix}_plot"
        self.x_axis_tag = f"{self.prefix}_xaxis"
        self.y_axis_tag = f"{self.prefix}_yaxis"
        self.file_dialog_tag = f"{self.prefix}_file_dialog"
        self.file_listbox_tag = f"{self.prefix}_file_listbox"
        self.element_entry_tag = f"{self.prefix}_element_entry"
        self.emission_combo_tag = f"{self.prefix}_emission_combo"
        self.channel_display_tag = f"{self.prefix}_channel_display"

        # Delete previous widgets in parent
        dpg.delete_item(self.parent, children_only=True)

        self._setup_ui()

    def _setup_ui(self):        
        with dpg.group(parent=self.parent):
            with dpg.group(horizontal=True):

                # === Left panel ===
                with dpg.child_window(width=380, height=-1):
                    dpg.add_input_text(label="Element", tag=self.element_entry_tag, width=200)

                    dpg.add_combo(
                        label="Emission Line",
                        items=["K_alpha", "K_beta", "K_alpha + K_beta"],
                        default_value="K_alpha", width=200,
                        tag=self.emission_combo_tag
                    )

                    dpg.add_input_text(label="Detector Channel", tag=self.channel_display_tag, readonly=True, width=200)

                    dpg.add_listbox(
                        tag=self.file_listbox_tag,
                        items=self.file_list,
                        width=-1,
                        num_items=38
                    )

                    with dpg.group(horizontal=True):
                        dpg.add_button(label="Select .h5 File", callback=lambda: dpg.show_item(self.file_dialog_tag))
                        dpg.add_button(label="Read Data", callback=self.read_and_plot_data)
                        dpg.add_button(label="Clear Canvas", callback=self.clear_canvas)

                # === Right panel (plot) ===
                with dpg.child_window(width=-1, height=-1):
                    with dpg.plot(label="Pixel vs Intensity", height=-1, width=-1, tag=self.plot_tag):
                        dpg.add_plot_axis(dpg.mvXAxis, label="Pixel", tag=self.x_axis_tag)
                        dpg.add_plot_axis(dpg.mvYAxis, label="Intensity", tag=self.y_axis_tag)

                # File dialog (only create once)
                if not dpg.does_item_exist(self.file_dialog_tag):
                    with dpg.file_dialog(
                        directory_selector=False, show=False,
                        callback=self.select_file_callback,
                        tag=self.file_dialog_tag,
                        width=700, height=400
                    ):
                        dpg.add_file_extension(".h5", color=(150, 255, 150, 255))
                        dpg.add_file_extension(".*", color=(255, 255, 255, 255))

    # ==============================
    # === File Handling ============
    # ==============================
    def select_file_callback(self, sender, app_data, user_data):
        file_path = app_data['file_path_name']
        if not file_path or not os.path.exists(file_path):
            return

        basename = os.path.basename(file_path)

        if basename not in self.file_list:
            self.file_list.append(basename)
            self.file_map[basename] = file_path
            self.hdf5_readers[file_path] = HDF5Reader(file_path)

            # Update listbox
            dpg.configure_item(self.file_listbox_tag, items=self.file_list)
            dpg.set_value(self.file_listbox_tag, basename)

    # ==============================
    # === Channel calculation ======
    # ==============================
    def calculate_channel(self):
        element = dpg.get_value(self.element_entry_tag).strip()
        emission_line = dpg.get_value(self.emission_combo_tag).strip()

        if emission_line == "K_alpha": emission_line = "Ka1"
        if emission_line == "K_beta": emission_line = "Kb1"

        if not element:
            dpg.set_value(self.channel_display_tag, "Missing element")
            return None

        try:
            if emission_line == "K_alpha + K_beta":
                ch1 = self.analyzer.run_find_channel(element, "Ka1")
                ch2 = self.analyzer.run_find_channel(element, "Kb1")
                return f"{int(ch1 - 10)}-{int(ch2 + 10)}"
            else:
                ch = self.analyzer.run_find_channel(element, emission_line)
                return f"{int(ch - 10)}-{int(ch + 10)}"
        except ValueError as e:
            return str(e)

    # ==============================
    # === Data reading & plotting ==
    # ==============================
    def read_and_plot_data(self):
        basename = dpg.get_value(self.file_listbox_tag)
        if not basename or basename not in self.file_map:
            dpg.set_value(self.channel_display_tag, "Invalid file")
            return

        selected_file = self.file_map[basename]
        element = dpg.get_value(self.element_entry_tag).strip()
        emission_line = dpg.get_value(self.emission_combo_tag).strip()
        channel_range = self.calculate_channel()

        # Validate channel_range
        if not channel_range or "-" not in channel_range:
            dpg.set_value(self.channel_display_tag, f"Invalid range: {channel_range}")
            return

        dpg.set_value(self.channel_display_tag, channel_range)

        plot_key = (selected_file, element, emission_line)
        if plot_key in self.plotted_data:
            return

        if selected_file in self.hdf5_readers:
            try:
                start, end = map(int, channel_range.split('-'))
                raw_data = self.hdf5_readers[selected_file].read_data(start, end)
                if raw_data is None or len(raw_data) == 0:
                    dpg.set_value(self.channel_display_tag, "No data returned.")
                    return

                y_values = list(map(float, raw_data))
                x_values = list(range(len(y_values)))

                label = f"{os.path.basename(selected_file)} ({element}, {emission_line})"
                series_tag = f"{self.prefix}_series_{self.series_count}"
                self.series_count += 1

                dpg.add_line_series(
                    x_values, y_values,
                    label=label,
                    parent=self.y_axis_tag,
                    tag=series_tag
                )
                dpg.fit_axis_data(self.x_axis_tag)
                dpg.fit_axis_data(self.y_axis_tag)

                self.plotted_data.add(plot_key)

            except Exception as e:
                dpg.set_value(self.channel_display_tag, str(e))

    # ==============================
    # === Clear plot ===============
    # ==============================
    def clear_canvas(self):
        children = dpg.get_item_children(self.y_axis_tag)
        if children and len(children) > 1:
            for child in children[1]:
                dpg.delete_item(child)
        self.plotted_data.clear()
        self.series_count = 0
