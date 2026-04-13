# -*- coding: utf-8 -*-
"""
Created on Mon May  5 15:56:30 2025

@author: ccakir
"""

import dearpygui.dearpygui as dpg
import pandas as pd
import numpy as np
import re
import itertools
import os

# --- Parsing function ---
def parse_evt_to_dataframe(filename, n=None):
    data_list = []
    keys_to_extract = ['cE', 'cx', 'cy', 'E', 'x', 'y']
    header = None

    try:
        with open(filename, 'r', encoding='utf-8') as f:
            try:
                header = next(f).strip()
            except StopIteration:
                return pd.DataFrame(columns=keys_to_extract), None

            line_iterator = f if n is None else itertools.islice(f, n)

            for line in line_iterator:
                line_data = {key: None for key in keys_to_extract}
                pairs = re.findall(r'(\w+)=\s*([-\d.]+)', line)
                temp_dict = dict(pairs)

                for key in keys_to_extract:
                    value_str = temp_dict.get(key)
                    if value_str is not None:
                        try:
                            if key in ['cE', 'E', 'x', 'y']:
                                line_data[key] = int(float(value_str))
                            elif key in ['cx', 'cy']:
                                line_data[key] = float(value_str)
                        except ValueError:
                            pass

                if temp_dict:
                    data_list.append(line_data)

    except Exception as e:
        return pd.DataFrame(columns=keys_to_extract), None

    if not data_list:
        return pd.DataFrame(columns=keys_to_extract), header

    return pd.DataFrame(data_list), header


# --- Main GUI Class ---
class EvtAnalyzerDPG:
    def __init__(self, parent):
        self.dataframe = pd.DataFrame()
        self.filtered_dataframe = pd.DataFrame()
        self.filepath = ""
        self.parent = parent
        self._build_ui()

    def _build_ui(self):
        with dpg.child_window(parent=self.parent, autosize_x=True, autosize_y=True):
            dpg.add_button(label="Select .evt file...", callback=self._select_file)
            self.file_display = dpg.add_text(default_value="No .evt file selected...")

            with dpg.group(horizontal=True):
                self.e_min = dpg.add_input_float(label="E Min", default_value=4000.0, width=200)
                self.e_max = dpg.add_input_float(label="E Max", default_value=5000.0, width=200)
                self.bin_width = dpg.add_input_float(label="Bin-Width (cx/cy)", default_value=1.0, width=200)
                self.max_lines = dpg.add_input_int(label="Max Lines (all lines = -1)", default_value=10000, width=200)
                
            with dpg.group(horizontal=True):  
            
                dpg.add_button(label="Update Graphs", callback=self._update_plots)
                dpg.add_button(label="Save Graphs", callback=self._export_histogram_csv)

            with dpg.group(horizontal=True):
                with dpg.group():
                    with dpg.plot(label="x vs y Histogram", height=600, width=600) as self.plot_xy:
                        self.ax_xy_x = dpg.add_plot_axis(dpg.mvXAxis, label="x", tag = "x_x_axis")
                        self.ax_xy_y = dpg.add_plot_axis(dpg.mvYAxis, label="y", tag = "y_y_axis")
                    with dpg.plot(label="x-Histogram (1D)", height=250, width=600) as self.plot_xy_proj:
                        self.ax_xy_proj_x = dpg.add_plot_axis(dpg.mvXAxis, label="x", tag = "x_x_axis1D")
                        self.ax_xy_proj_y = dpg.add_plot_axis(dpg.mvYAxis, label="Counts", tag = "y_y_axis1D")

                with dpg.group():
                    with dpg.plot(label="cx vs cy Histogram", height=600, width=600) as self.plot_cxcy:
                        self.ax_cxcy_x = dpg.add_plot_axis(dpg.mvXAxis, label="cx", tag = "cx_cx_axis")
                        self.ax_cxcy_y = dpg.add_plot_axis(dpg.mvYAxis, label="cy", tag = "cy_cy_axis")
                    with dpg.plot(label="cx-Histogram (1D)", height=250, width=600) as self.plot_cxcy_proj:
                        self.ax_cxcy_proj_x = dpg.add_plot_axis(dpg.mvXAxis, label="cx", tag = "cx_cx_axis1D")
                        self.ax_cxcy_proj_y = dpg.add_plot_axis(dpg.mvYAxis, label="Counts", tag = "cy_cy_axis1D")

    def _select_file(self):
        def callback(sender, app_data):
            self.filepath = app_data['file_path_name']
            dpg.set_value(self.file_display, self.filepath)
            # dpg.close_popup("file_dialog")

        with dpg.file_dialog(directory_selector=False, show=True, callback=callback, tag="file_dialog", width=700, height=400):
            dpg.add_file_extension(".evt", color=(150, 255, 150, 255))
            dpg.add_file_extension(".*")

    def _update_plots(self):
        if not os.path.exists(self.filepath):
            dpg.log_error("Datei not founded.")
            return

        e_min = dpg.get_value(self.e_min)
        e_max = dpg.get_value(self.e_max)
        bin_width = dpg.get_value(self.bin_width)
        max_lines = dpg.get_value(self.max_lines)
        n_lines = None if max_lines == -1 else max_lines

        self.dataframe, _ = parse_evt_to_dataframe(self.filepath, n=n_lines)

        if self.dataframe.empty:
            dpg.log_warning("Data not loaded.")
            return

        self.dataframe['E'] = pd.to_numeric(self.dataframe['E'], errors='coerce')
        self.dataframe.dropna(subset=['E'], inplace=True)
        self.filtered_dataframe = self.dataframe[
            (self.dataframe['E'] >= e_min) & (self.dataframe['E'] <= e_max)
        ].copy()

        self._plot_histogram_xy()
        self._plot_histogram_cxcy(bin_width)

    def _plot_histogram_xy(self):
        # 1) clear old plots
        dpg.delete_item(self.ax_xy_y, children_only=True)
        dpg.delete_item(self.ax_xy_proj_y, children_only=True)
    
        # 2) prepare data
        df = self.filtered_dataframe.dropna(subset=['x','y'])
        if df.empty:
            dpg.add_text("No valid (x, y) data", parent=self.ax_xy_y)
            return
    
        x = df['x'].to_numpy()
        y = df['y'].to_numpy()
    
        # 3) compute bins & histograms
        x_min, x_max = int(np.floor(x.min())), int(np.ceil(x.max()))
        y_min, y_max = int(np.floor(y.min())), int(np.ceil(y.max()))
        x_bins = np.arange(x_min, x_max + 2, 1)
        y_bins = np.arange(y_min, y_max + 2, 1)
    
        hist2d, x_edges, y_edges = np.histogram2d(x, y, bins=[x_bins, y_bins])
        # note: hist2d.shape == (len(x_bins)-1, len(y_bins)-1)
        
        flat_data = hist2d.T.flatten().tolist()
        
        # 4) heatmap
        heat_data = hist2d.T.tolist()  
             # list of rows
        n_rows, n_cols = len(heat_data), len(heat_data[0])
    
        dpg.add_heat_series(
            flat_data,                             # 1) data array
            n_rows,                                # 2) rows
            n_cols,                                # 3) cols
            parent=self.ax_xy_y,                   # attach to your plot axis
            bounds_min=(x_edges[0], y_edges[0]),   # float tuple
            bounds_max=(x_edges[-1], y_edges[-1]), # float tuple
            scale_min=0,
            scale_max=hist2d.max()
        )
    
        # 5) 1D projection on x
        hist1d, edges1d = np.histogram(x, bins=x_bins)
        centers = ((edges1d[:-1] + edges1d[1:]) / 2).tolist()
    
        dpg.add_line_series(
            centers,
            hist1d.tolist(),
            parent=self.ax_xy_proj_y
        )
        dpg.fit_axis_data('x_x_axis')
        dpg.fit_axis_data('y_y_axis')
        dpg.fit_axis_data('x_x_axis1D')
        dpg.fit_axis_data('y_y_axis1D')

    def _plot_histogram_cxcy(self, bin_width):
        
        dpg.delete_item(self.ax_cxcy_y, children_only=True)
        dpg.delete_item(self.ax_cxcy_proj_y, children_only=True)
    
        df = self.filtered_dataframe.dropna(subset=['cx','cy'])
        if df.empty:
            dpg.add_text("No valid (cx, cy) data", parent=self.ax_cxcy_y)
            return
    
        cx = df['cx'].to_numpy()
        cy = df['cy'].to_numpy()
    
        cx_bins = np.arange(np.floor(cx.min()), np.ceil(cx.max()) + bin_width, bin_width)
        cy_bins = np.arange(np.floor(cy.min()), np.ceil(cy.max()) + bin_width, bin_width)
    
        hist2d, cx_edges, cy_edges = np.histogram2d(cx, cy, bins=[cx_bins, cy_bins])
        
        flat_data = hist2d.T.flatten().tolist()
        
        heat_data = hist2d.T.tolist()
        n_rows, n_cols = len(heat_data), len(heat_data[0])
    
        dpg.add_heat_series(
            flat_data,
            n_rows,
            n_cols,
            parent=self.ax_cxcy_y,
            bounds_min=(cx_edges[0], cy_edges[0]),
            bounds_max=(cx_edges[-1], cy_edges[-1]),
            scale_min=0,
            scale_max=hist2d.max()
        )
        
            
        hist1d, edges1d = np.histogram(cx, bins=cx_bins)
        centers = ((edges1d[:-1] + edges1d[1:]) / 2).tolist()
    
        dpg.add_line_series(
            centers,
            hist1d.tolist(),
            parent=self.ax_cxcy_proj_y
        )
        
        dpg.fit_axis_data('cx_cx_axis')
        dpg.fit_axis_data('cy_cy_axis')
        dpg.fit_axis_data('cx_cx_axis1D')
        dpg.fit_axis_data('cy_cy_axis1D')



    def calc_energy(self, pixel):
        return [3.278 * i + 6328.186 for i in pixel]

    def _export_histogram_csv(self):
        if self.filtered_dataframe.empty:
            dpg.log_warning("Keine gefilterten Daten vorhanden.")
            return

        def on_choice(sender, app_data):
            which = app_data
            if which == "x":
                x_data = self.filtered_dataframe['x'].dropna()
                bins = np.arange(int(np.floor(x_data.min())), int(np.ceil(x_data.max()) + 2), 1)
                hist, edges = np.histogram(x_data, bins=bins)
                centers = (edges[:-1] + edges[1:]) / 2
                df_hist = pd.DataFrame({'x_bin_center': centers, 'counts': hist})
            else:
                cx_data = self.filtered_dataframe['cx'].dropna()
                bin_width = dpg.get_value(self.bin_width)
                bins = np.arange(np.floor(cx_data.min()), np.ceil(cx_data.max()) + bin_width, bin_width)
                hist, edges = np.histogram(cx_data, bins=bins)
                centers = (edges[:-1] + edges[1:]) / 2
                df_hist = pd.DataFrame({'cx_bin_center': centers, 'counts': hist})

            def file_callback(sender, file_data):
                path = file_data['file_path_name']
                df_hist.to_csv(path, index=False)
                dpg.log_info(f"Histogramm gespeichert: {path}")

            with dpg.file_dialog(directory_selector=False, show=True, callback=file_callback, tag="save_hist_csv"):
                dpg.add_file_extension(".csv")

        with dpg.window(label="Histogramm speichern", modal=True, no_close=True, no_resize=True, width=400, height=150, tag="save_choice_popup"):
            dpg.add_text("Möchten Sie speichern:")
            dpg.add_button(label="x-Histogramm (Bin=1)", callback=lambda: [dpg.delete_item("save_choice_popup"), on_choice(None, "x")])
            dpg.add_button(label="cx-Histogramm (benutzerdefiniert)", callback=lambda: [dpg.delete_item("save_choice_popup"), on_choice(None, "cx")])
