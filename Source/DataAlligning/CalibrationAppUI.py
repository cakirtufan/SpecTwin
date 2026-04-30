# -*- coding: utf-8 -*-
"""
Created on Mon May  5 11:37:21 2025

@author: ccakir
"""

import dearpygui.dearpygui as dpg
import os
import numpy as np
import XRFAnalyzer
from HDF5Reader import HDF5Reader
from scipy.optimize import curve_fit

class CalibrationUI:
    def __init__(self, parent_tag, parent_app=None):
        self.parent_tag = parent_tag
        self.parent_app = parent_app

        self.calibration_file = ""
        self.selected_element = ""
        self.chosen_line = ""
        self.detector_channel_range = ""

        self.intensity = None
        self.pixel_indices = None
        self.data_x = []  # Added to store x-data
        self.data_y = []  # Added to store y-data
        self.selected_points = []
        self.is_selecting = False  # Renamed for consistency
        
        
        self.params_a = None
        self.params_b = None
        
        self.hdf5_reader = None
        self.analyzer = XRFAnalyzer.XRFAnalyzer()

        for tag in ["selected_scatter_theme", "align_green_theme", "plot_handler_registry"]:
            if dpg.does_item_exist(tag):
                dpg.delete_item(tag)

        self._build_layout()

    def _build_layout(self):
        with dpg.group(parent=self.parent_tag):
            with dpg.group(horizontal=True):
                # === File Selection Panel ===
                with dpg.child_window(width=300, height=190):
                    dpg.add_text("Calibration File")
                    dpg.add_button(label="Select File", callback=self.select_calibration_file)
                    self.file_label = dpg.add_text(default_value="No file selected", wrap=280)
                    dpg.add_text("Detector Channel Range")
                    self.channel_display = dpg.add_input_text(default_value="", readonly=True, width=200)

                # === Parameters Panel ===
                with dpg.child_window(width=300, height=190):
                    dpg.add_text("Element")
                    self.element_input = dpg.add_input_text(hint="e.g., Fe", width=100)

                    dpg.add_text("Emission Line")
                    self.emission_combo = dpg.add_combo(
                        items=["K_alpha", "K_beta", "K_alpha + K_beta"],
                        default_value="K_alpha",
                        width=150
                    )

                    dpg.add_button(label="Calculate & Read Data", callback=self.process_data)

                # === Peak Table ===
                with dpg.child_window(width=-1, height=190):
                    with dpg.table(header_row=True, resizable=True, policy=dpg.mvTable_SizingStretchProp,
                                   borders_innerH=True, borders_innerV=True, borders_outerH=True, borders_outerV=True,
                                   row_background=True, tag="peak_table"):
                        dpg.add_table_column(label="Pixel")
                        dpg.add_table_column(label="Intensity")
                        dpg.add_table_column(label="Element")
                        dpg.add_table_column(label="Emission Line")
                        dpg.add_table_column(label="Emission Energy (eV)")
                        dpg.add_table_column(label="Align")
                        dpg.add_table_column(label="Remove")

            with dpg.group(horizontal=True):
                dpg.add_button(label="Get Calibration Point", callback=self._enable_pick)
                dpg.add_button(label="Stop Selecting", callback=self._disable_pick)
                dpg.add_button(label="Confirm Peaks", callback=self._confirm_peaks)

        # --- Plot Window ---
        with dpg.child_window(parent=self.parent_tag, width=-1, height=-1, tag="plot_window"):
            with dpg.plot(label="XRF Data", no_menus=True, no_box_select=True, anti_aliased=True,
                          height=-1, width=-1, tag="xrf_plot"):
                dpg.add_plot_legend()
                dpg.add_plot_axis(dpg.mvXAxis, label="Pixel", tag="x_axis")
                with dpg.plot_axis(dpg.mvYAxis, label="Intensity", tag="y_axis"):
                    
                    self.main_series = dpg.add_scatter_series([], [], label="Raw Data", tag="main_scatter")
                    self.selected_series = dpg.add_scatter_series([], [], label="Selected Points", tag="selected_scatter")
                    self.line_series = dpg.add_line_series([],[], tag="main_line")    

                    with dpg.theme(tag="selected_scatter_theme"):
                        with dpg.theme_component(dpg.mvScatterSeries):
                            dpg.add_theme_color(dpg.mvPlotCol_Line, (255, 165, 0, 255), category=dpg.mvThemeCat_Plots)
                            dpg.add_theme_color(dpg.mvPlotCol_Fill, (255, 165, 0, 255), category=dpg.mvThemeCat_Plots)

                    dpg.bind_item_theme(self.selected_series, "selected_scatter_theme")

            # Handler for mouse clicks
            with dpg.handler_registry(tag="plot_handler_registry"):
                dpg.add_mouse_down_handler(callback=self._mouse_click_handler)

        # Theme for Align button
        with dpg.theme(tag="align_green_theme"):
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (0, 200, 0, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (0, 220, 0, 255))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (0, 180, 0, 255))

    # === File handling ===
    def select_calibration_file(self):
        if hasattr(self, "file_dialog_id"):
            dpg.delete_item(self.file_dialog_id)

        with dpg.file_dialog(directory_selector=False, show=True, callback=self._file_selected, tag="file_dialog_id",
                             width=600, height=400):
            dpg.add_file_extension(".h5", color=(150, 255, 150, 255))
            dpg.add_file_extension(".*")

    def _file_selected(self, sender, app_data):
        self.calibration_file = app_data['file_path_name']
        filename = os.path.basename(self.calibration_file)
        dpg.set_value(self.file_label, filename)
        self.hdf5_reader = HDF5Reader(self.calibration_file)


    def calculate_energy_scale(self):
        """
        Compute and apply linear calibration E = a*pixel + b
        using aligned peaks. Updates DPG plot with calibrated energy scale.
        """
        # Get aligned peaks
        aligned_points = [p for p in self.selected_points if p.get("aligned")]
        if len(aligned_points) < 2:
            dpg.add_text("⚠️ Need at least 2 aligned peaks for calibration", parent=self.parent_tag)
            return

        pixels = []
        energies = []
        for p in aligned_points:
            if p.get("energy") is not None:
                pixels.append(float(p["pixel"]))
                energies.append(float(p["energy"]))

        if len(pixels) < 2:
            dpg.add_text("⚠️ Calibration Error: invalid peak data", parent=self.parent_tag)
            return

        # Linear fit
        def linear_func(x, a, b):
            return a * x + b

        params, _ = curve_fit(linear_func, pixels, energies)
        a, b = params
        self.params_a, self.params_b = a, b

        # Apply calibration to the whole dataset
        calibrated_energy = a * np.array(self.data_x) + b
        
        # Update plot with calibrated data
        
        dpg.set_value(self.line_series, [calibrated_energy.tolist(), self.data_y])
        dpg.set_value(self.main_series, [calibrated_energy.tolist(), self.data_y])
        
        
        # 🔥 Clear selected points display
        dpg.set_value("main_line", [[],[]])
        dpg.set_value("selected_scatter", [[], []])
        
        
        # Remove old calibration lines
        if hasattr(self, "calibration_lines"):
            for line in self.calibration_lines:
                if dpg.does_item_exist(line):
                    dpg.delete_item(line)
        self.calibration_lines = []
        
        # Add vlines at reference energies
        for en in energies:
            line_id = dpg.add_inf_line_series(
                [en], parent="x_axis", label=f"{en:.2f} eV"
            )
            self.calibration_lines.append(line_id)
        
        # Update axis labels
        dpg.configure_item("x_axis", label="Energy (eV)")
        dpg.fit_axis_data("x_axis")
        dpg.fit_axis_data("y_axis")

        # Feedback
        dpg.add_text(
            f"✅ Calibration complete: E = {a:.3f} * Pixel + {b:.3f}",
            parent=self.parent_tag
        )


    # === Data handling ===
    def process_data(self):
        self.selected_element = dpg.get_value(self.element_input).strip()
        emission_line = dpg.get_value(self.emission_combo)
        self.chosen_line = emission_line

        if emission_line == "K_alpha":
            line_code = "Ka1"
        elif emission_line == "K_beta":
            line_code = "Kb1"
        else:
            line_code = "Ka1 + Kb1"

        if not self.selected_element:
            dpg.add_text("Missing element input!", parent=self.parent_tag)
            return

        if not self.hdf5_reader:
            dpg.add_text("No calibration file selected!", parent=self.parent_tag)
            return

        try:
            if line_code == "Ka1 + Kb1":
                chan1 = self.analyzer.run_find_channel(self.selected_element, "Ka1")
                chan2 = self.analyzer.run_find_channel(self.selected_element, "Kb1")
                ch_range = f"{int(chan1 - 10)} - {int(chan2 + 10)}"
            else:
                chan = self.analyzer.run_find_channel(self.selected_element, line_code)
                ch_range = f"{int(chan - 10)} - {int(chan + 10)}"

            dpg.set_value(self.channel_display, ch_range)
            self.detector_channel_range = ch_range

            start, end = map(int, ch_range.split("-"))
            data = self.hdf5_reader.read_data(start, end)
            y = list(map(float, data))
            x = list(range(len(y)))

            self.data_y = y
            self.data_x = x

            self.selected_points = []
            self.update_ui()
            
            
            dpg.set_value(self.line_series, [self.data_x, self.data_y])
            dpg.set_value(self.main_series, [self.data_x, self.data_y])
            
            
            dpg.fit_axis_data("x_axis")
            dpg.fit_axis_data("y_axis")

        except Exception as e:
            dpg.add_text(f"Error: {str(e)}", parent=self.parent_tag)

    # === Interaction ===
    def _enable_pick(self):
        self.is_selecting = True
        print("Peak selection enabled")

    def _disable_pick(self):
        self.is_selecting = False
        print("Peak selection disabled")

    def _confirm_peaks(self):
        
        
        if not self.selected_points:
            print("No peaks selected.")
            return
        
        
        self.calculate_energy_scale()
        
        # Take only aligned points
        aligned_points = [p for p in self.selected_points if p.get("aligned")]
        if not aligned_points:
            print("No aligned points selected.")
            return
    
        # Build align_peaks list
        allign_peaks = []
        for p in aligned_points:
            allign_peaks.append((
                p["pixel"], 
                p.get("energy", None), 
                p["line"]
            ))
    
        calibration_data = {
            "ref_data": self.calibration_file,
            "selected_element": self.selected_element,
            "channel_start": int(self.detector_channel_range.split("-")[0].strip()),
            "channel_end": int(self.detector_channel_range.split("-")[1].strip()),
            "allign_peaks": allign_peaks,
            "params_a": self.params_a,
            "params_b": self.params_b
        }
    
        print("Calibration data ready:", calibration_data)
    
        if self.parent_app:
            self.parent_app.calibration_data = calibration_data
            print("Saved into parent_app:", self.parent_app.calibration_data)
            self.parent_app.enable_aligning_tab()

    def _mouse_click_handler(self, sender, app_data):
        if not self.is_selecting:
            return
        if not self.data_x:
            return

        mx, my = dpg.get_mouse_pos(local=False)
        win_min = dpg.get_item_rect_min("xrf_plot")
        win_max = dpg.get_item_rect_max("xrf_plot")
        if not (win_min[0] <= mx <= win_max[0] and win_min[1] <= my <= win_max[1]):
            return

        px, py = dpg.get_plot_mouse_pos()
        if np.isnan(px) or np.isnan(py):
            return

        idx = min(range(len(self.data_x)), key=lambda i: abs(self.data_x[i] - px))
        selected_x = self.data_x[idx]
        selected_y = self.data_y[idx]

        if not any(p['pixel'] == selected_x for p in self.selected_points):
            self.selected_points.append({
                'pixel': selected_x,
                'intensity': selected_y,
                'element': self.selected_element,
                'line': self.chosen_line,
                'energy': None,
                'aligned': False
            })
            self.update_ui()

    # === Table population ===
    def _populate_table(self):
        dpg.delete_item("peak_table", children_only=True, slot=1)

        for point in self.selected_points:
            with dpg.table_row(parent="peak_table"):
                dpg.add_text(str(point['pixel']))
                dpg.add_text(f"{point['intensity']:.2f}")
                dpg.add_text(point['element'])

                # Emission lines list
                lines = []
                if point['element']:
                    try:
                        lines = self.analyzer.get_emission_lines(point['element']) or []
                    except Exception:
                        lines = []
                default_line = point['line'] if point['line'] in lines else (lines[0] if lines else "")

                dpg.add_combo(
                    items=lines,
                    default_value=default_line,
                    width=120,
                    callback=self._update_line_selection,
                    user_data=point
                )

                energy_text = f"{point['energy']:.2f}" if point.get('energy') else ""
                point['energy_cell'] = dpg.add_text(energy_text)

                # Align button
                align_btn = dpg.add_button(label="Align", callback=self._toggle_align, user_data=point)
                point['align_button'] = align_btn
                if point.get('aligned'):
                    dpg.bind_item_theme(align_btn, "align_green_theme")

                # Remove button
                dpg.add_button(label="Remove", callback=self._remove_point, user_data=point)

    # === Callbacks ===
    def _update_line_selection(self, sender, app_data, user_data):
        point = user_data
        point['line'] = app_data
        try:
            result = self.analyzer.find_emission_line(point['element'], app_data)
            if hasattr(result, "energy"):
                energy = result.energy
            elif isinstance(result, (tuple, list)):
                energy = result[0]
            else:
                energy = float(result)
            point['energy'] = energy
            dpg.set_value(point['energy_cell'], f"{energy:.2f}")
        except Exception as e:
            print(f"Could not fetch energy for {point['element']} {app_data}: {e}")
            point['energy'] = None
            dpg.set_value(point['energy_cell'], "")

    def _toggle_align(self, sender, app_data, user_data):
        point = user_data
        point['aligned'] = not point.get('aligned', False)
        if point['aligned']:
            dpg.bind_item_theme(point['align_button'], "align_green_theme")
        else:
            dpg.bind_item_theme(point['align_button'], 0)

    def _remove_point(self, sender, app_data, user_data):
        point_to_remove = user_data
        self.selected_points = [
            p for p in self.selected_points
            if p['pixel'] != point_to_remove['pixel']
        ]
        self.update_ui()

    def update_ui(self):
        if self.selected_points:
            xs = [p['pixel'] for p in self.selected_points]
            ys = [p['intensity'] for p in self.selected_points]
            dpg.set_value("selected_scatter", [xs, ys])
        else:
            dpg.set_value("selected_scatter", [[], []])

        self._populate_table()
